"""
Document and DocumentChunk models for the RAG (Retrieval Augmented Generation) system.
Stores uploaded documents and their processed embeddings.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.session import Base


class Document(Base):
    """
    Uploaded document for the knowledge base / RAG system.
    Documents are processed into chunks and embedded for semantic search.
    """
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    
    # Document info
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, txt, docx
    file_size = Column(Integer, default=0)  # in bytes
    file_path = Column(String(500), nullable=False)
    
    # Processing status
    status = Column(String(50), default="uploaded")  # uploaded, processing, processed, failed
    chunk_count = Column(Integer, default=0)
    
    # Content
    raw_text = Column(Text, nullable=True)
    
    # Metadata
    extra_info = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    business = relationship("Business", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document {self.title}>"


class DocumentChunk(Base):
    """
    A chunk of a processed document with its embedding.
    Used for semantic search in the RAG system.
    """
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    
    # Chunk content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position in document
    
    # Embedding stored as JSON (list of floats)
    # In production, use pgvector or store in FAISS index
    embedding = Column(JSON, nullable=True)
    
    # Metadata
    token_count = Column(Integer, default=0)
    extra_info = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<DocumentChunk {self.document_id}:{self.chunk_index}>"
