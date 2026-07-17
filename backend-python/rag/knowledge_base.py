"""
Chocolates Helena — Knowledge Base (FAISS + Gemini Embeddings)
Usa Google Gemini para embeddings en lugar de sentence-transformers
para evitar la dependencia de PyTorch (~2GB RAM).
"""
from __future__ import annotations

import logging
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from .documents import get_all_documents

logger = logging.getLogger(__name__)

FAISS_INDEX_PATH = Path(__file__).parent / "faiss_index"

_vector_store: FAISS | None = None
_embeddings: GoogleGenerativeAIEmbeddings | None = None


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        logger.info("Cargando embeddings: Gemini text-embedding-004")
        _embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004"
        )
    return _embeddings


def build_vector_store(force_rebuild: bool = False) -> FAISS:
    global _vector_store

    if _vector_store is not None and not force_rebuild:
        return _vector_store

    embeddings = get_embeddings()

    if FAISS_INDEX_PATH.exists() and not force_rebuild:
        logger.info(f"Cargando índice FAISS desde: {FAISS_INDEX_PATH}")
        try:
            _vector_store = FAISS.load_local(
                str(FAISS_INDEX_PATH),
                embeddings,
                allow_dangerous_deserialization=True,
            )
            logger.info("Índice FAISS cargado con éxito.")
            return _vector_store
        except Exception as e:
            logger.warning(f"No se pudo cargar el índice FAISS: {e}. Reconstruyendo...")

    logger.info("Construyendo nuevo índice FAISS desde documentos...")
    documents = get_all_documents()
    logger.info(f"Indexando {len(documents)} documentos...")

    _vector_store = FAISS.from_documents(documents, embeddings)

    FAISS_INDEX_PATH.mkdir(parents=True, exist_ok=True)
    _vector_store.save_local(str(FAISS_INDEX_PATH))
    logger.info(f"Índice FAISS guardado en: {FAISS_INDEX_PATH}")

    return _vector_store


def get_vector_store() -> FAISS:
    return build_vector_store()
