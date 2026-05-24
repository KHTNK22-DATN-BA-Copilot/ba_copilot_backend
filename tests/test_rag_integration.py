import io
from unittest.mock import patch, MagicMock


def test_upload_triggers_indexing_chain(authenticated_client, db_session):
    client, user = authenticated_client

    # Create a project and folder so FK constraints are satisfied
    from app.models.project import Project
    from app.models.folder import Folder

    project = Project(user_id=user.id, name="Test Project")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    folder = Folder(project_id=project.id, name="default", created_by=user.id)
    db_session.add(folder)
    db_session.commit()
    db_session.refresh(folder)

    # Prepare a small text file to upload
    file_content = b"Hello world. This is a test file for RAG indexing."
    files = {"files": ("test.txt", io.BytesIO(file_content), "text/plain")}

    # Patch upload_to_supabase to return a fake URL and patch chain.apply_async
    with patch("app.api.v1.files.upload_to_supabase", return_value="uploads/test.txt") as mock_upload:
        with patch("app.api.v1.files.chain.apply_async") as mock_chain:
            response = client.post(f"/api/v1/files/upload/{project.id}/{folder.id}", files=files, data={"path": "uploads"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["files"]) == 1

    # Ensure the upload helper was called and chain was scheduled
    assert mock_upload.called
    assert mock_chain.called
