import asyncio
import logging
import uuid
import httpx
from fastapi import HTTPException, status, UploadFile
from app.utils.supabase_client import supabase

logger = logging.getLogger(__name__)

AI_SERVICE_URL = "http://ai:8000/v1/srs/generate"
SUPABASE_BUCKET = "uploads"


async def upload_to_supabase(file: UploadFile) -> str | None:
    """Upload file lên Supabase và trả về public URL."""
    try:
        file_name = f"{uuid.uuid4()}_{file.filename}"
        file_data = await file.read()

        res = supabase.storage.from_(SUPABASE_BUCKET).upload(file_name, file_data)

        if not res.path:
            logger.error(f"Failed to upload {file.filename}")
            return None

        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(file_name)
        logger.info(f"Uploaded {file.filename} to Supabase → {public_url}")
        return public_url

    except Exception as e:
        logger.exception(f"Upload failed for {file.filename}: {e}")
        return None


async def call_ai_service(payload: dict, retries: int = 3, timeout: int = 120):
    """Gọi AI service với retry & timeout logic."""
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(AI_SERVICE_URL, json=payload)

            if response.status_code == 200:
                return response.json()

            logger.warning(
                f"AI service returned {response.status_code} (attempt {attempt}/{retries})"
            )
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.warning(f"AI request failed (attempt {attempt}/{retries}): {e}")
            await asyncio.sleep(2 * attempt)

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI service unavailable after multiple retries",
    )


def format_srs_to_markdown(document: dict) -> str:
    """Chuyển dữ liệu document SRS sang định dạng Markdown."""
    lines = []
    lines.append(f"# {document.get('title', 'Untitled Document')}")
    lines.append(f"**Version:** {document.get('version', 'N/A')}")
    lines.append(f"**Date:** {document.get('date', 'N/A')}")
    lines.append(f"**Author:** {document.get('author', 'Unknown')}\n")

    lines.append("## Project Overview")
    lines.append(document.get("project_overview", "No overview provided."))

    lines.append("\n## Functional Requirements")
    for i, fr in enumerate(document.get("functional_requirements", []), 1):
        if isinstance(fr, dict):
            lines.append(f"- **{fr.get('id', f'FR{i}')}**: {fr.get('description', '')}")
        else:
            lines.append(f"- {fr}")

    lines.append("\n## Non-Functional Requirements")
    for nf in document.get("non_functional_requirements", []):
        if isinstance(nf, dict):
            lines.append(
                f"- **{nf.get('category', 'General')}**: {nf.get('requirement', '')}"
            )
        else:
            lines.append(f"- {nf}")

    lines.append("\n## System Architecture")
    lines.append(document.get("system_architecture", "Not defined."))

    lines.append("\n## User Stories")
    for story in document.get("user_stories", []):
        if isinstance(story, dict):
            lines.append(f"- **Story:** {story.get('story', '')}")
            lines.append(
                f"  - **Acceptance Criteria:** {story.get('acceptance_criteria', '')}"
            )
        else:
            lines.append(f"- {story}")

    lines.append("\n## Constraints")
    for c in document.get("constraints", []):
        lines.append(f"- {c}")

    lines.append("\n## Assumptions")
    for a in document.get("assumptions", []):
        lines.append(f"- {a}")

    lines.append("\n## Glossary")
    for key, value in document.get("glossary", {}).items():
        lines.append(f"- **{key}**: {value}")

    return "\n".join(lines)
