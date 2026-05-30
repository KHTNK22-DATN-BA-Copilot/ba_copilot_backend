from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import and_, case, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.custom_document_format import CustomDocumentFormat
from app.models.default_document_format import DefaultDocumentFormat

from app.utils.document_format import (
    extract_text_from_upload_file,
    get_unique_document_format_name,
)

import os


async def resolve_active_format(
    db: AsyncSession,
    project_id: int,
    document_type: str,
):
    is_custom_active = and_(
        CustomDocumentFormat.id.isnot(None), CustomDocumentFormat.is_activated.is_(True)
    )

    stmt = (
        select(
            DefaultDocumentFormat.document_type.label("document_type"),
            case((is_custom_active, "custom"), else_="default").label("source"),
            case(
                (is_custom_active, CustomDocumentFormat.id),
                else_=DefaultDocumentFormat.id,
            ).label("format_id"),
            case(
                (is_custom_active, CustomDocumentFormat.content),
                else_=DefaultDocumentFormat.content,
            ).label("content"),
            case(
                (is_custom_active, CustomDocumentFormat.extension),
                else_=DefaultDocumentFormat.extension,
            ).label("extension"),
        )
        .outerjoin(
            CustomDocumentFormat,
            and_(
                CustomDocumentFormat.document_type
                == DefaultDocumentFormat.document_type,
                CustomDocumentFormat.project_id == project_id,
                CustomDocumentFormat.is_activated.is_(True),
            ),
        )
        .where(DefaultDocumentFormat.document_type == document_type)
        .order_by(CustomDocumentFormat.id.desc())
    )

    query_result = await db.execute(stmt)
    result = query_result.first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Document type '{document_type}' not found in system defaults.",
        )

    return {
        "source": result.source,
        "document_type": result.document_type,
        "content": result.content,
        "extension": result.extension,
        "format_id": result.format_id,
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
