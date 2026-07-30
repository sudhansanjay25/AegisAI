"""
Similarity search — compares output embeddings to vault chunks via pgvector.
"""

from sqlalchemy import select
from app.models import VaultChunk

async def find_similar_chunks(session, query_embedding: list[float], top_k: int = 5):
    """Find the top_k most similar vault chunks to the query_embedding.
    
    Uses cosine distance from pgvector. 
    1 - cosine_distance = cosine similarity (higher is more similar).
    """
    result = await session.execute(
        select(
            VaultChunk.id,
            VaultChunk.document_id,
            VaultChunk.text,
            (1 - VaultChunk.embedding.cosine_distance(query_embedding)).label("similarity")
        )
        .order_by(VaultChunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    return result.all()
