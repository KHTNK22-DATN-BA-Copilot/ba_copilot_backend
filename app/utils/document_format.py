import re
import codecs
import os
from fastapi import HTTPException, UploadFile

from sqlalchemy.orm import Session

from app.models.custom_document_format import (
    CustomDocumentFormat,
)

ALLOWED_EXTENSIONS = [".md", ".txt"]
CHUNK_SIZE = 64 * 1024


async def extract_text_from_upload_file(file: UploadFile) -> tuple[str, str]:
    extension = os.path.splitext(file.filename)[1].lower() if file.filename else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(ALLOWED_EXTENSIONS)} files are supported",
        )

    try:
        text_chunks = []
        decoder = codecs.getincrementaldecoder("utf-8")()

        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break

            text_piece = decoder.decode(chunk, final=False)
            text_chunks.append(text_piece)

        text_chunks.append(decoder.decode(b"", final=True))

        content = "".join(text_chunks)
        return content, extension

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be UTF-8 encoded",
        )
    finally:
        await file.close()


def get_unique_document_format_name(
    db: Session,
    project_id: int,
    document_type: str,
    title: str,
) -> str:
    """
    Example:
        SRS Template
        SRS Template (1)
        SRS Template (2)
    """

    base_title = title.strip()

    existing_documents = (
        db.query(CustomDocumentFormat.format_name)
        .filter(
            CustomDocumentFormat.project_id == project_id,
            CustomDocumentFormat.document_type == document_type,
            CustomDocumentFormat.format_name.like(f"{base_title}%"),
        )
        .all()
    )

    max_suffix = 0

    safe_base_title = re.escape(base_title)

    suffix_pattern = re.compile(rf"^{safe_base_title}\s*\((?P<suffix>\d+)\)$")

    is_exact_match = False

    for doc_name_tuple in existing_documents:
        doc_name = doc_name_tuple[0]

        if doc_name == base_title:
            is_exact_match = True
            continue

        match = suffix_pattern.match(doc_name)

        if match:
            suffix = int(match.group("suffix"))

            if suffix > max_suffix:
                max_suffix = suffix

    if not existing_documents or not (is_exact_match or max_suffix > 0):
        return base_title

    return f"{base_title} ({max_suffix + 1})"
