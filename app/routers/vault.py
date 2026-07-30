"""
Vault router — document upload, chunking, embedding, and storage.
"""

from fastapi import APIRouter, Depends, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import VaultDocument, VaultChunk
from app.ingestion.extract import extract_text
from app.ingestion.chunk import chunk_text
from app.ingestion.embed import embed_batch

router = APIRouter(tags=["vault"])


@router.post("/v1/vault/documents")
async def upload_document(
    file: UploadFile,
    sensitivity_tag: str = "restricted",
    session: AsyncSession = Depends(get_session),
):
    """Upload a document to the vault.

    Accepts PDF, DOCX, CSV, or TXT files. Extracts text, chunks it,
    embeds each chunk locally via all-MiniLM-L6-v2, and stores
    everything in Postgres with pgvector.

    Returns the document ID and number of chunks created.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("pdf", "docx", "csv", "txt"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Supported: pdf, docx, csv, txt",
        )

    # Extract text
    try:
        text = await extract_text(file)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to extract text: {e}")

    if not text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from the file")

    # Chunk
    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=422, detail="Text produced no chunks")

    # Create document record
    doc = VaultDocument(
        title=file.filename,
        source_type=ext,
        sensitivity_tag=sensitivity_tag,
    )
    session.add(doc)
    await session.flush()  # get doc.id

    # Embed all chunks locally (sentence-transformers, no API call)
    try:
        embeddings = embed_batch(chunks)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Embedding failed: {e}")

    # Store chunks with embeddings
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        session.add(
            VaultChunk(
                document_id=doc.id,
                text=chunk,
                chunk_index=i,
                embedding=emb,
            )
        )

    await session.commit()

    return {
        "document_id": doc.id,
        "title": file.filename,
        "source_type": ext,
        "sensitivity_tag": sensitivity_tag,
        "chunks_created": len(chunks),
    }
