"""
AegisAI ORM models — vault documents and chunks with pgvector embeddings.
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db import Base


class VaultDocument(Base):
    """A document uploaded to the secure vault."""

    __tablename__ = "vault_documents"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # pdf/docx/csv/txt
    sensitivity_tag = Column(String, default="restricted")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chunks = relationship("VaultChunk", back_populates="document", cascade="all, delete-orphan")


class VaultChunk(Base):
    """A text chunk from a vault document, with its embedding vector."""

    __tablename__ = "vault_chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("vault_documents.id"), nullable=False)
    text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(Vector(384))  # matches all-MiniLM-L6-v2 dimensions

    document = relationship("VaultDocument", back_populates="chunks")
