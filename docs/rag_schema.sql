-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Table for RAG chunks
CREATE TABLE IF NOT EXISTS rag_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL,
    project_id INTEGER NOT NULL,
    document_type TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER,
    embedding VECTOR(3072) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rag_chunks_project_id_idx
    ON rag_chunks (project_id);

CREATE INDEX IF NOT EXISTS rag_chunks_file_id_idx
    ON rag_chunks (file_id);

CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
    ON rag_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- RPC for similarity search
CREATE OR REPLACE FUNCTION match_rag_chunks(
    query_embedding VECTOR(3072),
    match_count INT,
    project_id_filter INTEGER DEFAULT NULL,
    min_similarity FLOAT DEFAULT 0.0
)
RETURNS TABLE (
    id UUID,
    file_id UUID,
    project_id INTEGER,
    document_type TEXT,
    chunk_index INTEGER,
    content TEXT,
    token_count INTEGER,
    similarity FLOAT
)
LANGUAGE plpgsql STABLE AS $$
BEGIN
    RETURN QUERY
    SELECT
        rag_chunks.id,
                rag_chunks.file_id,
        rag_chunks.project_id,
            rag_chunks.document_type,
        rag_chunks.chunk_index,
        rag_chunks.content,
        rag_chunks.token_count,
        1 - (rag_chunks.embedding <=> query_embedding) AS similarity
    FROM rag_chunks
        WHERE (project_id_filter IS NULL OR rag_chunks.project_id = project_id_filter)
      AND (1 - (rag_chunks.embedding <=> query_embedding)) >= min_similarity
    ORDER BY rag_chunks.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
