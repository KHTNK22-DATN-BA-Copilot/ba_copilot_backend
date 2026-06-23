from math import ceil
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.models.custom_document_format import CustomDocumentFormat

from app.utils.document_format import (
    extract_text_from_upload_file,
    get_unique_document_format_name,
)

import os

def get_project_document_formats(
    db: Session,
    project_id: int,
    page: int = 1,
    size: int = 10,
    document_type: Optional[str] = None,
):
    query = db.query(CustomDocumentFormat).filter(
        CustomDocumentFormat.project_id == project_id
    )

    if document_type:
        query = query.filter(CustomDocumentFormat.document_type == document_type)

    total = query.count()

    formats = (
        query.order_by(CustomDocumentFormat.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "formats": formats,
        "pages": {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": ceil(total / size) if total else 0,
        },
    }

async def resolve_active_format(
    db: Session,
    project_id: int,
    document_type: str,
):
    custom_format = (
        db.query(CustomDocumentFormat)
        .filter(
            CustomDocumentFormat.project_id == project_id,
            CustomDocumentFormat.document_type == document_type,
            CustomDocumentFormat.is_activated.is_(True),
        )
        .first()
    )

    if not custom_format:
        return None

    
    return {
        "source": "custom",
        "document_type": custom_format.document_type,
        "content": custom_format.content,
        "extension": custom_format.extension,
        "format_id": custom_format.id,
    }

    

    

async def upload_custom_document_format(
    db: Session,
    project_id: int,
    document_type: str,
    file: UploadFile,
):
    content, extension = await extract_text_from_upload_file(file)

    original_name = os.path.splitext(file.filename)[0]

    unique_name = get_unique_document_format_name(
        db=db,
        project_id=project_id,
        document_type=document_type,
        title=original_name,
    )

    db.query(CustomDocumentFormat).filter(
        CustomDocumentFormat.project_id == project_id,
        CustomDocumentFormat.document_type == document_type,
        CustomDocumentFormat.is_activated.is_(True),
    ).update(
        {CustomDocumentFormat.is_activated: False},
        synchronize_session=False,
    )

    new_format = CustomDocumentFormat(
        project_id=project_id,
        format_name=unique_name,
        document_type=document_type,
        content=content,
        extension=extension,
        is_activated=True,
    )

    db.add(new_format)

    return new_format


async def activate_custom_format(
    db: Session,
    project_id: int,
    format_id: int,
):
    format_record = (
        db.query(CustomDocumentFormat)
        .filter(
            CustomDocumentFormat.id == format_id,
            CustomDocumentFormat.project_id == project_id,
        )
        .first()
    )

    if not format_record:
        raise HTTPException(
            status_code=404,
            detail="Custom format not found",
        )

    db.query(CustomDocumentFormat).filter(
        CustomDocumentFormat.project_id == project_id,
        CustomDocumentFormat.document_type == format_record.document_type,
    ).update(
        {CustomDocumentFormat.is_activated: False},
        synchronize_session=False,
    )

    format_record.is_activated = True

    return format_record


async def update_custom_format_content(
    db: Session,
    project_id: int,
    format_id: int,
    content: str,
):
    format_record = (
        db.query(CustomDocumentFormat)
        .filter(
            CustomDocumentFormat.id == format_id,
            CustomDocumentFormat.project_id == project_id,
        )
        .first()
    )

    if not format_record:
        raise HTTPException(
            status_code=404,
            detail="Custom format not found",
        )

    format_record.content = content

    return format_record


async def delete_custom_format(
    db: Session,
    project_id: int,
    format_id: int,
):
    format_record = (
        db.query(CustomDocumentFormat)
        .filter(
            CustomDocumentFormat.id == format_id,
            CustomDocumentFormat.project_id == project_id,
        )
        .first()
    )

    if not format_record:
        raise HTTPException(
            status_code=404,
            detail="Custom format not found",
        )

    db.delete(format_record)

    return True
