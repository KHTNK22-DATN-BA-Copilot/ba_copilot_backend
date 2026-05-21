import logging
import re
from typing import Iterable, List, Optional

from openai import OpenAI
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def _get_token_encoder():
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def _count_tokens(text: str) -> int:
    if not text:
        return 0

    encoder = _get_token_encoder()
    if encoder is not None:
        return len(encoder.encode(text))

    # Fallback approximation: 4 chars per token.
    return max(1, len(text) // 4)


def _trim_to_tokens(text: str, max_tokens: int) -> str:
    if max_tokens <= 0 or not text:
        return ""

    encoder = _get_token_encoder()
    if encoder is not None:
        tokens = encoder.encode(text)
        return encoder.decode(tokens[:max_tokens])

    approx_len = max_tokens * 4
    return text[:approx_len]


def _last_tokens(text: str, token_count: int) -> str:
    if token_count <= 0 or not text:
        return ""

    encoder = _get_token_encoder()
    if encoder is not None:
        tokens = encoder.encode(text)
        return encoder.decode(tokens[-token_count:])

    words = text.split()
    return " ".join(words[-token_count:])


def _split_paragraphs(text: str) -> List[str]:
    return [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]


def _split_sentences(text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _split_words(text: str) -> List[str]:
    return [w for w in re.split(r"\s+", text.strip()) if w]


def _split_units(
    units: List[str],
    *,
    max_tokens: int,
    joiner: str,
    next_splitter: Optional[callable],
    next_joiner: str,
    fallback_splitter: Optional[callable],
) -> List[str]:
    chunks: List[str] = []
    current: List[str] = []

    for unit in units:
        unit_tokens = _count_tokens(unit)

        if unit_tokens > max_tokens and next_splitter is not None:
            sub_units = next_splitter(unit)
            sub_chunks = _split_units(
                sub_units,
                max_tokens=max_tokens,
                joiner=next_joiner,
                next_splitter=fallback_splitter,
                next_joiner=" ",
                fallback_splitter=None,
            )
            chunks.extend(sub_chunks)
            continue

        if unit_tokens > max_tokens and next_splitter is None:
            chunks.append(_trim_to_tokens(unit, max_tokens))
            continue

        candidate = joiner.join(current + [unit]) if current else unit
        if _count_tokens(candidate) <= max_tokens:
            current.append(unit)
            continue

        if current:
            chunks.append(joiner.join(current).strip())
        current = [unit]

    if current:
        chunks.append(joiner.join(current).strip())

    return chunks


def _apply_overlap(chunks: List[str], *, max_tokens: int, overlap_tokens: int) -> List[str]:
    if overlap_tokens <= 0 or not chunks:
        return chunks

    overlapped = [chunks[0]]
    for chunk in chunks[1:]:
        prefix = _last_tokens(overlapped[-1], overlap_tokens)
        merged = f"{prefix} {chunk}".strip() if prefix else chunk
        overlapped.append(_trim_to_tokens(merged, max_tokens))

    return overlapped


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

    paragraphs = _split_paragraphs(normalized)
    chunks = _split_units(
        paragraphs,
        max_tokens=chunk_size,
        joiner="\n\n",
        next_splitter=_split_sentences,
        next_joiner=" ",
        fallback_splitter=_split_words,
    )

    return _apply_overlap(chunks, max_tokens=chunk_size, overlap_tokens=overlap)


def _estimate_tokens(text: str) -> int:
    return _count_tokens(text)


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
    document_type: str,
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
            document_type,
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
            :document_type,
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
                    "document_type": document_type,
                    "chunk_index": chunk_index,
                    "content": chunk_text,
                    "token_count": token_count,
                    "embedding": vector_literal,
                },
            )
            inserted += 1

    return inserted
