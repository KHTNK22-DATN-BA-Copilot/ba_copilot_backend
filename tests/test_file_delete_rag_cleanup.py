from sqlalchemy import text
from unittest.mock import patch

from app.models.file import Files


def test_delete_rag_chunks_for_file_removes_matching_rows(db_session):
    from app.utils.rag_indexer import delete_rag_chunks_for_file

    db_session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS rag_chunks (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                project_id INTEGER NOT NULL,
                document_type TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                token_count INTEGER,
                embedding TEXT NOT NULL,
                created_at TEXT
            )
            """
        )
    )
    db_session.execute(
        text(
            "INSERT INTO rag_chunks (id, file_id, project_id, document_type, chunk_index, content, token_count, embedding, created_at) VALUES ('chunk-1', 'file-123', 1, 'user_upload', 0, 'hello', 1, '[0.1]', '2026-06-03T00:00:00Z')"
        )
    )
    db_session.commit()

    deleted = delete_rag_chunks_for_file(db_session, file_id="file-123")
    db_session.commit()

    remaining = db_session.execute(text("SELECT COUNT(*) FROM rag_chunks WHERE file_id = 'file-123'"))
    remaining_count = remaining.scalar_one()

    assert deleted == 1
    assert remaining_count == 0


def test_delete_file_triggers_rag_cleanup(authenticated_client, db_session):
    client, user = authenticated_client

    from app.models.project import Project
    from app.models.folder import Folder

    project = Project(user_id=user.id, name="Delete Cleanup Project")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    folder = Folder(project_id=project.id, name="default", created_by=user.id)
    db_session.add(folder)
    db_session.commit()
    db_session.refresh(folder)

    file_record = Files(
        project_id=project.id,
        folder_id=folder.id,
        created_by=user.id,
        updated_by=user.id,
        name="rag-doc",
        extension=".md",
        storage_path="uploads/rag-doc.md",
        storage_md_path="uploads/rag-doc_convert.md",
        content="hello",
        file_category="user upload",
        file_type=".md",
        file_size=1,
        status="completed",
    )
    db_session.add(file_record)
    db_session.commit()
    db_session.refresh(file_record)

    with patch("app.api.v1.files.delete_rag_chunks_for_file", return_value=2) as mock_delete_rag:
        with patch("app.api.v1.files.delete_file_from_supabase", return_value=True) as mock_delete_storage:
            response = client.delete(f"/api/v1/files/{file_record.id}")

    assert response.status_code == 200
    mock_delete_rag.assert_called_once()
    assert mock_delete_storage.call_count == 2
    assert db_session.query(Files).filter(Files.id == file_record.id).first() is None