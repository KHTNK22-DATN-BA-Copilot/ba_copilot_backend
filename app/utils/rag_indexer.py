import logging
from typing import Iterable, List

from openai import OpenAI
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be < chunk_size")

    normalized = _normalize_text(text)
    if not normalized:
        return []

    chunks: List[str] = []
    start = 0
    length = len(normalized)

    while start < length:
        end = min(start + chunk_size, length)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0
        if start >= length:
            break

    return chunks


def _estimate_tokens(text: str) -> int:
    return len(text.split())


def _batch(iterable: List[str], batch_size: int) -> Iterable[List[str]]:
    for idx in range(0, len(iterable), batch_size):
        yield iterable[idx : idx + batch_size]


def _embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []

    client = OpenAI(api_key=settings.openai_api_key or None)
    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=texts,
    )

    return [item.embedding for item in response.data]


def index_rag_chunks(
    db,
    *,
    file_id: str,
    project_id: int,
    storage_key: str,
    markdown_text: str,
) -> int:
    chunks = _chunk_text(
        markdown_text,
        chunk_size=settings.rag_chunk_size,
        overlap=settings.rag_chunk_overlap,
    )

    if not chunks:
        return 0

    db.execute(
        text("DELETE FROM rag_chunks WHERE file_id = :file_id"),
        {"file_id": file_id},
    )

    inserted = 0
    insert_sql = text(
        """
        INSERT INTO rag_chunks (
            id,
            file_id,
            project_id,
            storage_key,
            chunk_index,
            content,
            token_count,
            embedding,
            created_at
        )
        VALUES (
            gen_random_uuid(),
            :file_id,
            :project_id,
            :storage_key,
            :chunk_index,
            :content,
            :token_count,
            :embedding::vector,
            NOW()
        )
        """
    )

    for batch_start, batch_texts in enumerate(
        _batch(chunks, settings.rag_embed_batch_size)
    ):
        embeddings = _embed_texts(batch_texts)

        for offset, (chunk_text, embedding) in enumerate(
            zip(batch_texts, embeddings)
        ):
            vector_literal = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
            chunk_index = batch_start * settings.rag_embed_batch_size + offset
            token_count = _estimate_tokens(chunk_text)

            db.execute(
                insert_sql,
                {
                    "file_id": file_id,
                    "project_id": project_id,
                    "storage_key": storage_key,
                    "chunk_index": chunk_index,
                    "content": chunk_text,
                    "token_count": token_count,
                    "embedding": vector_literal,
                },
            )
            inserted += 1

    return inserted
