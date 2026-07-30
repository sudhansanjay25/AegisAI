"""
Local embedding via sentence-transformers — no API key needed.
Uses all-MiniLM-L6-v2 (384 dims, fast, good quality for paraphrase detection).
"""

from sentence_transformers import SentenceTransformer

# Loads once at process start — ~80MB model, cached by HuggingFace
_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts locally.

    Same call shape as the old OpenAI version (chunks in → vectors out),
    so nothing in the vault ingestion route needs to change.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each 384 floats for all-MiniLM-L6-v2).
    """
    return _model.encode(texts, normalize_embeddings=True).tolist()
