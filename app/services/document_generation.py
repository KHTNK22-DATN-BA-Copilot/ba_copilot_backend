import json
import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import Callable, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.rbac import ProjectAccessContext
from app.models.file import Files
from app.models.folder import Folder
from app.models.session import Chat_Session
from app.schemas.folder import CreateFolderRequest
from app.models.project import Project
from app.services.docs_constraint import validate_dependencies
from app.services.document_format_service import resolve_active_format
from app.utils.call_ai_service import call_ai_service
from app.utils.file_handling import update_file_from_supabase, upload_to_supabase
from app.utils.folder_utils import create_default_folder
from app.utils.get_unique_name import get_unique_diagram_name
from app.utils.metadata_utils import create_ai_generated_metadata

FILE_STATUS_COMPLETED = "completed"


async def list_project_file_paths(project_id: int, db: Session):
    file_list = (
        db.query(Files)
        .filter(
            Files.project_id == project_id,
            Files.status == FILE_STATUS_COMPLETED,
        )
        .order_by(Files.created_at.asc())
        .all()
    )

    return [
        (
            file.storage_md_path
            if file.file_category == "user upload"
            else file.storage_path
        )
        for file in file_list
    ]


def resolve_description(
    db: Session,
    project_id: int,
    description: str | None,
) -> str:
    if description and description.strip():
        return description.strip()

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    project_name = project.name or ""
    project_description = project.description or ""

    return f"""
Project Name: {project_name}

Project Description:
{project_description}
""".strip()


def document_response(response_cls, doc: Files, type_field: str):
    payload = {
        "document_id": str(doc.id),
        "project_name": doc.name,
        "content": doc.content,
        "status": doc.status,
        "file_category": doc.file_category,
        "updated_at": doc.updated_at,
        "file_size_kb": doc.file_size,
    }
    payload[type_field] = doc.file_type
    return response_cls(**payload)


def update_response(response_cls, doc: Files, content: str):
    return response_cls(
        document_id=str(doc.id),
        project_name=doc.name,
        content=content,
        updated_at=doc.updated_at,
        file_size_kb=doc.file_size,
    )


def generate_response(
    response_cls,
    doc: Files,
    access: ProjectAccessContext,
    description: str,
    content: str,
    type_field: str,
    recommend_documents: Optional[list[str]] = None,
):
    payload = {
        "document_id": str(doc.id),
        "user_id": str(access.user.id),
        "generated_at": datetime.now(timezone.utc),
        "input_description": description,
        "document": content,
        "status": doc.status,
        "file_size_kb": doc.file_size,
    }
    payload[type_field] = doc.file_type
    if recommend_documents is not None:
        payload["recommend_documents"] = recommend_documents
    return response_cls(**payload)


async def generate_document(
    *,
    project_id: int,
    project_name: str,
    document_type: str,
    description: str,
    valid_types: list[str],
    step: str,
    type_field: str,
    response_cls,
    get_ai_endpoint: Callable[[str], str],
    format_response: Callable,
    access: ProjectAccessContext,
    db: Session,
    content_transform: Optional[Callable] = None,
):
    if document_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type. Must be one of: {valid_types}",
        )

    dependency_result = validate_dependencies(
        project_id, document_type, db, access.user
    )
    if not dependency_result["can_proceed"]:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Cannot generate {document_type}. Missing required documents: "
                f"{dependency_result['missing_required']}"
            ),
        )

    result = await create_default_folder(
        project_id, CreateFolderRequest(name=document_type), access.user.id, db
    )
    if result.error:
        raise HTTPException(status_code=500, detail="Failed to create folder")
    folder = result.folder

    result = await resolve_active_format(
        db=db,
        project_id=project_id,
        document_type=document_type,
    )
    # file_urls = await list_project_file_paths(project_id, db)

    description = resolve_description(
        db=db,
        project_id=project_id,
        description=description,
    )

    ai_payload = {
        "message": description,
        "project_id": project_id,
        # "storage_paths": file_urls,
    }

    if result:
        ai_payload["document_format"] = result["content"]

    ai_data = await call_ai_service(
        get_ai_endpoint(document_type),
        ai_payload,
        db=db,
        user_id=access.user.id,
    )

    ai_inner = ai_data.get("response", {})
    content = (
        content_transform(ai_inner) if content_transform else format_response(ai_inner)
    )
    content = str(content)

    unique_title = get_unique_diagram_name(db, project_name, project_id, document_type)
    upload_buffer = BytesIO(content.encode("utf-8"))
    file_size_kb = round(len(upload_buffer.getvalue()) / 1024, 2)
    file_path = await upload_to_supabase(
        UploadFile(
            filename=(f"{access.user.id}/{project_id}/{folder.name}/{unique_title}.md"),
            file=upload_buffer,
        )
    )
    if not file_path:
        raise HTTPException(status_code=500, detail="Upload failed")

    try:
        file_metadata = create_ai_generated_metadata(
            doc_type=document_type,
            content=content,
            message=description,
            ai_response=ai_data,
            step=step,
        )
        if step == "design":
            file_metadata["design_category"] = document_type.split("-")[0]

        new_file = Files(
            project_id=project_id,
            folder_id=folder.id,
            created_by=access.user.id,
            updated_by=access.user.id,
            name=unique_title,
            extension=".md",
            storage_path=file_path,
            content=content,
            file_category="ai gen",
            file_type=document_type,
            file_metadata=file_metadata,
            file_size=file_size_kb,
        )
        db.add(new_file)
        db.flush()

        db.add_all(
            [
                Chat_Session(
                    project_id=project_id,
                    user_id=access.user.id,
                    content_type=document_type,
                    content_id=new_file.id,
                    role="user",
                    message=description,
                ),
                Chat_Session(
                    project_id=project_id,
                    user_id=access.user.id,
                    content_type=document_type,
                    content_id=new_file.id,
                    role="ai",
                    message=json.dumps(ai_inner),
                ),
            ]
        )
        db.commit()
        db.refresh(new_file)
        return generate_response(
            response_cls,
            new_file,
            access,
            description,
            content,
            type_field,
            dependency_result["missing_recommended"],
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


def list_documents(
    *,
    project_id: int,
    document_type: Optional[str],
    valid_types: list[str],
    response_cls,
    item_response_cls,
    type_field: str,
    db: Session,
):
    query = db.query(Files).filter(
        Files.project_id == project_id,
        Files.status != "deleted",
    )
    if document_type:
        query = query.filter(Files.file_type == document_type)
    else:
        query = query.filter(Files.file_type.in_(valid_types))

    return {
        "documents": [
            document_response(item_response_cls, doc, type_field) for doc in query.all()
        ]
    }


def get_document(
    *,
    project_id: int,
    document_id: str,
    valid_types: list[str],
    response_cls,
    type_field: str,
    db: Session,
):
    doc = (
        db.query(Files)
        .filter(
            Files.id == document_id,
            Files.project_id == project_id,
            Files.status != "deleted",
            Files.file_type.in_(valid_types),
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return document_response(response_cls, doc, type_field)


async def update_document(
    *,
    project_id: int,
    document_id: str,
    content: str,
    valid_types: list[str],
    response_cls,
    access: ProjectAccessContext,
    db: Session,
):
    doc = (
        db.query(Files)
        .filter(
            Files.id == document_id,
            Files.project_id == project_id,
            Files.status != "deleted",
            Files.file_type.in_(valid_types),
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    folder = db.query(Folder).filter(Folder.id == doc.folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    file_like = BytesIO(content.encode("utf-8"))
    file_size_kb = round(len(file_like.getvalue()) / 1024, 2)
    path = await update_file_from_supabase(
        doc.storage_path,
        UploadFile(
            filename=f"{access.user.id}/{project_id}/{folder.name}/{doc.name}.md",
            file=file_like,
        ),
    )

    doc.content = content
    doc.updated_by = access.user.id
    doc.file_size = file_size_kb
    if path:
        doc.storage_path = path

    chat_session = (
        db.query(Chat_Session)
        .filter(
            Chat_Session.project_id == project_id,
            Chat_Session.content_id == doc.id,
            Chat_Session.content_type == doc.file_type,
            Chat_Session.role == "ai",
        )
        .order_by(Chat_Session.created_at.desc())
        .first()
    )
    if chat_session:
        chat_session.message = content

    db.commit()
    db.refresh(doc)
    return update_response(response_cls, doc, content)


async def regenerate_document(
    *,
    project_id: int,
    document_id: str,
    description: str,
    valid_types: list[str],
    type_field: str,
    response_cls,
    get_ai_endpoint: Callable[[str], str],
    format_response: Callable,
    access: ProjectAccessContext,
    db: Session,
):
    doc = (
        db.query(Files)
        .filter(
            Files.id == document_id,
            Files.project_id == project_id,
            Files.status != "deleted",
            Files.file_type.in_(valid_types),
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    description = resolve_description(
        db=db,
        project_id=project_id,
        description=description,
    )

    result = await resolve_active_format(
        db=db,
        project_id=project_id,
        document_type=doc.file_type,
    )

    # file_urls = await list_project_file_paths(project_id, db)

    ai_payload = {
        "message": description,
        "content_id": document_id,
        "project_id": project_id,
        # "storage_paths": file_urls,
    }

    if result:
        ai_payload["document_format"] = result["content"]

    ai_data = await call_ai_service(
        get_ai_endpoint(doc.file_type),
        ai_payload,
        db=db,
        user_id=access.user.id,
    )
    ai_inner = ai_data.get("response", {})
    content = str(format_response(ai_inner))

    folder = db.query(Folder).filter(Folder.id == doc.folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    upload_buffer = BytesIO(content.encode("utf-8"))
    file_size_kb = round(len(upload_buffer.getvalue()) / 1024, 2)
    path = await update_file_from_supabase(
        doc.storage_path,
        UploadFile(
            filename=f"{access.user.id}/{project_id}/{folder.name}/{doc.name}.md",
            file=upload_buffer,
        ),
    )

    try:
        doc.content = content
        doc.updated_by = access.user.id
        doc.file_size = file_size_kb
        if path:
            doc.storage_path = path
        doc.file_metadata = {
            **(doc.file_metadata or {}),
            "message": description,
            "ai_response": ai_data,
        }
        doc.status = "completed"
        db.flush()
        db.add_all(
            [
                Chat_Session(
                    project_id=project_id,
                    user_id=access.user.id,
                    content_type=doc.file_type,
                    content_id=doc.id,
                    role="user",
                    message=description,
                ),
                Chat_Session(
                    project_id=project_id,
                    user_id=access.user.id,
                    content_type=doc.file_type,
                    content_id=doc.id,
                    role="ai",
                    message=json.dumps(ai_inner),
                ),
            ]
        )
        db.commit()
        db.refresh(doc)
        return generate_response(
            response_cls,
            doc,
            access,
            description,
            content,
            type_field,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
