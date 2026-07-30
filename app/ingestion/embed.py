"""
Local embedding via fastembed (ONNX) — no API key needed, low memory footprint.
Uses all-MiniLM-L6-v2 (384 dims, fast, good quality for paraphrase detection).
"""

from fastembed import TextEmbedding

# Loads once at process start — ONNX model, ~60MB, runs on CPU efficiently
_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts locally using ONNX runtime.

    Same call shape as before (chunks in → vectors out),
    so nothing in the vault ingestion route needs to change.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each 384 floats for all-MiniLM-L6-v2).
    """
    # fastembed returns a generator, convert to list of lists
    embeddings = list(_model.embed(texts))
    return [emb.tolist() for emb in embeddings]
