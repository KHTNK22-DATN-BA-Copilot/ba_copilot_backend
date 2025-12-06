import re
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.document import Documents


def get_unique_diagram_name(
    db: Session, title: str, project_id: int, diagram_type: str
) -> str:
   
    base_title = title.strip()

    existing_documents = (
        db.query(Documents.document_name)
        .filter(
            Documents.project_id == project_id,
            Documents.document_type == diagram_type,
            Documents.document_name.like(f"{base_title}%"),
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

    # 3. Trả về tên duy nhất
    if not existing_documents or not (is_exact_match or max_suffix > 0):
        # Không tìm thấy tên trùng hoặc hậu tố, trả về tên gốc
        return base_title
    else:
        # Tìm thấy tên trùng, sử dụng số hậu tố lớn nhất + 1
        return f"{base_title} ({max_suffix + 1})"
