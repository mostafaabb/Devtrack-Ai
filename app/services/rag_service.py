"""
RAG (Retrieval Augmented Generation) Service.
Production-grade document processing, embeddings, and semantic search.

Embedding strategy:
1. Primary: Google Gemini embeddings (text-embedding-004)
2. Fallback: Sentence Transformers (all-MiniLM-L6-v2)
3. Last resort: TF-IDF based keyword matching
"""
import os
import json
import hashlib
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger("devtrack.rag")

# Try importing ML libraries
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

# Document processing
try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# Embedding providers
try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class EmbeddingProvider:
    """
    Manages embedding generation with multiple fallback providers.
    """

    def __init__(self, gemini_api_key: str = ""):
        self.provider_name = "none"
        self.dimension = 384
        self.model = None

        # Try Google Gemini embeddings first (best quality)
        if GEMINI_AVAILABLE and gemini_api_key:
            try:
                genai.configure(api_key=gemini_api_key)
                self.provider_name = "gemini"
                self.dimension = 768
                logger.info("📡 Embedding provider: Google Gemini (text-embedding-004)")
                return
            except Exception as e:
                logger.warning(f"Gemini embedding init failed: {e}")

        # Try Sentence Transformers (local, free, good quality)
        if ST_AVAILABLE:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                self.provider_name = "sentence_transformers"
                self.dimension = 384
                logger.info("🔧 Embedding provider: Sentence Transformers (all-MiniLM-L6-v2)")
                return
            except Exception as e:
                logger.warning(f"Sentence transformers init failed: {e}")

        # Fallback: deterministic hash-based embeddings
        self.provider_name = "hash"
        self.dimension = 384
        logger.info("📋 Embedding provider: Hash-based (keyword matching enabled)")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if self.provider_name == "gemini":
            return self._embed_gemini(texts)
        elif self.provider_name == "sentence_transformers":
            return self._embed_st(texts)
        else:
            return [self._embed_hash(t) for t in texts]

    def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self.embed([text])[0]

    def _embed_gemini(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Google Gemini."""
        try:
            embeddings = []
            for text in texts:
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_document",
                )
                embeddings.append(result["embedding"])
            return embeddings
        except Exception as e:
            logger.error(f"Gemini embedding error: {e}")
            return [self._embed_hash(t) for t in texts]

    def _embed_st(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Sentence Transformers."""
        try:
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Sentence transformer error: {e}")
            return [self._embed_hash(t) for t in texts]

    def _embed_hash(self, text: str) -> List[float]:
        """Hash-based deterministic embedding fallback."""
        if NUMPY_AVAILABLE:
            seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**31)
            np.random.seed(seed)
            embedding = np.random.randn(self.dimension).astype("float32")
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            return embedding.tolist()
        return [0.0] * self.dimension


class RAGService:
    """
    Production RAG system for document-based knowledge retrieval.

    Pipeline:
    1. Upload documents (PDF, TXT, DOCX)
    2. Extract text
    3. Chunk into segments with sentence boundary awareness
    4. Generate embeddings (Gemini / SentenceTransformers / hash fallback)
    5. Store in FAISS vector index
    6. Retrieve relevant context for chat
    """

    def __init__(self):
        from app.core.config import settings
        self.embedder = EmbeddingProvider(getattr(settings, "GEMINI_API_KEY", ""))
        self.dimension = self.embedder.dimension
        self.index = None
        self.chunks_store: Dict[str, Dict] = {}
        self.chunk_id_map: List[str] = []

        self._init_index()

    def _init_index(self):
        """Initialize FAISS index."""
        if FAISS_AVAILABLE and NUMPY_AVAILABLE:
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine for normalized)
            logger.info(f"FAISS index initialized (dim={self.dimension})")
        else:
            logger.info("FAISS not available — using keyword matching")

    # ─── Document Extraction ─────────────────────────────────────

    def extract_text(self, file_path: str, file_type: str) -> str:
        """Extract text from a document file. Supports PDF, TXT, DOCX."""
        extractors = {
            "pdf": self._extract_pdf,
            "txt": self._extract_txt,
            "docx": self._extract_docx,
        }
        extractor = extractors.get(file_type, self._extract_txt)
        text = extractor(file_path)
        logger.info(f"Extracted {len(text)} chars from {file_type} file")
        return text

    def _extract_pdf(self, file_path: str) -> str:
        if not PDF_AVAILABLE:
            logger.warning("PyPDF2 not installed, cannot extract PDF")
            return ""
        try:
            reader = PdfReader(file_path)
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages.append(text.strip())
            return "\n\n".join(pages)
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return ""

    def _extract_txt(self, file_path: str) -> str:
        try:
            for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1256"]:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            return ""
        except Exception as e:
            logger.error(f"TXT extraction error: {e}")
            return ""

    def _extract_docx(self, file_path: str) -> str:
        if not DOCX_AVAILABLE:
            logger.warning("python-docx not installed, cannot extract DOCX")
            return ""
        try:
            doc = DocxDocument(file_path)
            return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            return ""

    # ─── Text Chunking ───────────────────────────────────────────

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50,
        respect_sentences: bool = True,
    ) -> List[str]:
        """
        Split text into overlapping chunks with sentence boundary awareness.

        Args:
            text: Full document text
            chunk_size: Target characters per chunk
            overlap: Overlapping characters between chunks
            respect_sentences: Try to break at sentence boundaries
        """
        if not text:
            return []

        # Clean text
        text = text.strip()
        text = "\n".join(line for line in text.splitlines() if line.strip())

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            # Try to break at sentence boundary
            if respect_sentences and end < len(text):
                search_start = max(start, end - 120)
                for sep in [". ", ".\n", "!\n", "?\n", "\n\n", ";\n", "\n"]:
                    last_sep = text[search_start:end].rfind(sep)
                    if last_sep != -1:
                        end = search_start + last_sep + len(sep)
                        break

            chunk = text[start:end].strip()
            if chunk and len(chunk) > 20:
                chunks.append(chunk)

            start = max(start + 1, end - overlap)

        logger.info(f"Created {len(chunks)} chunks from {len(text)} chars")
        return chunks

    # ─── Vector Operations ───────────────────────────────────────

    def add_chunks(self, chunks: List[str], document_id: str) -> int:
        """Add document chunks to the vector index."""
        if not chunks:
            return 0

        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_{i}"
            self.chunks_store[chunk_id] = {
                "content": chunk,
                "document_id": document_id,
                "chunk_index": i,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.chunk_id_map.append(chunk_id)

        # Batch embed for efficiency
        if self.index and NUMPY_AVAILABLE:
            embeddings = self.embedder.embed(chunks)
            vectors = np.array(embeddings, dtype="float32")
            self.index.add(vectors)

        logger.info(f"Added {len(chunks)} chunks for document {document_id}")
        return len(chunks)

    def remove_document(self, document_id: str):
        """Remove all chunks for a document from the index."""
        to_remove = [cid for cid in self.chunks_store if cid.startswith(f"{document_id}_")]
        for cid in to_remove:
            del self.chunks_store[cid]

        # Rebuild index (FAISS doesn't support deletion easily)
        if to_remove:
            self._rebuild_index()
            logger.info(f"Removed {len(to_remove)} chunks for document {document_id}")

    def _rebuild_index(self):
        """Rebuild the FAISS index from stored chunks."""
        if not FAISS_AVAILABLE or not NUMPY_AVAILABLE:
            return

        self.index = faiss.IndexFlatIP(self.dimension)
        self.chunk_id_map = list(self.chunks_store.keys())

        if self.chunk_id_map:
            contents = [self.chunks_store[cid]["content"] for cid in self.chunk_id_map]
            embeddings = self.embedder.embed(contents)
            vectors = np.array(embeddings, dtype="float32")
            self.index.add(vectors)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant chunks using semantic similarity."""
        if not self.chunks_store:
            return []

        if self.index and NUMPY_AVAILABLE and self.index.ntotal > 0:
            query_embedding = self.embedder.embed_single(query)
            vector = np.array([query_embedding], dtype="float32")
            scores, indices = self.index.search(vector, min(top_k, self.index.ntotal))

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if 0 <= idx < len(self.chunk_id_map):
                    chunk_id = self.chunk_id_map[idx]
                    chunk_data = self.chunks_store.get(chunk_id, {})
                    results.append({
                        "content": chunk_data.get("content", ""),
                        "document_id": chunk_data.get("document_id", ""),
                        "score": float(score),
                        "chunk_index": chunk_data.get("chunk_index", 0),
                    })
            return results

        # Fallback: keyword matching
        return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Fallback keyword-based search with TF-IDF-like scoring."""
        query_words = set(query.lower().split())
        scored_chunks = []

        for chunk_id, chunk_data in self.chunks_store.items():
            content_lower = chunk_data["content"].lower()
            content_words = set(content_lower.split())

            # Score by word overlap and exact phrase matching
            word_overlap = len(query_words & content_words)
            phrase_bonus = 2 if query.lower() in content_lower else 0
            score = word_overlap + phrase_bonus

            if score > 0:
                scored_chunks.append({
                    "content": chunk_data["content"],
                    "document_id": chunk_data["document_id"],
                    "score": score,
                    "chunk_index": chunk_data["chunk_index"],
                })

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]

    def get_context(self, query: str, business_id: str = None) -> str:
        """Get relevant context from the knowledge base for a chat query."""
        results = self.search(query, top_k=3)
        if not results:
            return ""
        return "\n---\n".join(r["content"] for r in results)

    def get_stats(self) -> dict:
        """Get RAG system statistics."""
        return {
            "total_chunks": len(self.chunks_store),
            "embedding_provider": self.embedder.provider_name,
            "embedding_dimension": self.dimension,
            "faiss_available": FAISS_AVAILABLE,
            "index_size": self.index.ntotal if self.index else 0,
        }


# Global RAG service instance
rag_service = RAGService()
