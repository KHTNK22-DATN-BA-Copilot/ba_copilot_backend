from app.utils.rag_indexer import _chunk_text


def test_chunk_text_basic():
    text = (
        "Paragraph one. Sentence a. Sentence b.\n\n"
        "Paragraph two has more content and should be included.\n\n"
        "Paragraph three short."
    )

    # Small chunk size (approx chars/tokens) to force multiple chunks
    chunks = _chunk_text(text, chunk_size=20, overlap=5)

    # Expect multiple chunks and some overlap
    assert isinstance(chunks, list)
    assert len(chunks) >= 2

    # Overlap check: last tokens of first chunk should appear at start of second when trimmed
    first = chunks[0]
    second = chunks[1]
    assert len(first) <= 20
    assert len(second) <= 20
    # Basic textual overlap: some word from end of first should be in second
    assert any(w for w in first.split()[-3:] if w in second)
