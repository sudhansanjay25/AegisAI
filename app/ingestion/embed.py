"""
Local embedding via fastembed (ONNX) — no API key needed, low memory footprint.
Uses all-MiniLM-L6-v2 (384 dims, fast, good quality for paraphrase detection).
"""

from fastembed import TextEmbedding

_model = None

def get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        # Loads on first request — ONNX model, ~60MB, runs on CPU efficiently
        _model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts locally using ONNX runtime.

    Same call shape as before (chunks in → vectors out),
    so nothing in the vault ingestion route needs to change.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each 384 floats for all-MiniLM-L6-v2).
    """
    model = get_model()
    # fastembed returns a generator, convert to list of lists
    embeddings = list(model.embed(texts))
    return [emb.tolist() for emb in embeddings]
