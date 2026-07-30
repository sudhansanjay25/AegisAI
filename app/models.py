"""
AegisAI ORM models — vault documents and chunks with pgvector embeddings.
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
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


class ScoredOutput(Base):
    """Audit log of outputs evaluated by the system."""

    __tablename__ = "scored_outputs"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String, nullable=True)
    session_id = Column(String, nullable=True)
    output_text = Column(Text, nullable=False)
    similarity_score = Column(Float, nullable=False)
    matched_chunk_ids = Column(ARRAY(Integer), default=[])
    
    # Populated at Hour 9-13 (Judge Stage)
    judge_verdict = Column(String, nullable=True)
    judge_confidence = Column(Float, nullable=True)
    matched_facts = Column(JSONB, nullable=True)
    
    # Populated at Hour 13-15 (Aggregation/Policy Stage)
    risk_score = Column(Float, nullable=True)
    policy_action = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
