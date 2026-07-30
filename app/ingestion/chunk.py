"""
Text chunking — simple fixed-size character chunking with overlap.
"""


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into fixed-size chunks with overlap.

    Character-based, not token-based — fine for a 24h build.
    The overlap ensures context isn't lost at chunk boundaries.

    Args:
        text: The full document text.
        size: Maximum characters per chunk.
        overlap: Characters of overlap between consecutive chunks.

    Returns:
        List of text chunks.
    """
    if not text or not text.strip():
        return []

    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks
