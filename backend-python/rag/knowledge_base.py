"""
══════════════════════════════════════════════════════════════════
Chocolates Helena — Knowledge Base (FAISS + Embeddings Locales)
Crea y persiste el índice vectorial FAISS con los documentos
del catálogo, FAQs, políticas y más.
Usa HuggingFace sentence-transformers (local, sin API extra).
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import logging
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

from .documents import get_all_documents

logger = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────────────────────

# Modelo de embeddings local (no requiere API key)
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Ruta donde se guarda el índice FAISS persistente
FAISS_INDEX_PATH = Path(__file__).parent / "faiss_index"

# Singleton del vector store
_vector_store: FAISS | None = None
_embeddings: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Devuelve el modelo de embeddings (singleton)."""
    global _embeddings
    if _embeddings is None:
        logger.info(f"Cargando modelo de embeddings: {EMBEDDING_MODEL}")
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def build_vector_store(force_rebuild: bool = False) -> FAISS:
    """
    Construye o carga el índice FAISS.
    - Si existe el índice y no se fuerza rebuild, lo carga desde disco.
    - Si no existe o se fuerza rebuild, lo crea desde los documentos.
    """
    global _vector_store

    if _vector_store is not None and not force_rebuild:
        return _vector_store

    embeddings = get_embeddings()

    # Intentar cargar índice existente
    if FAISS_INDEX_PATH.exists() and not force_rebuild:
        logger.info(f"Cargando índice FAISS desde: {FAISS_INDEX_PATH}")
        try:
            _vector_store = FAISS.load_local(
                str(FAISS_INDEX_PATH),
                embeddings,
                allow_dangerous_deserialization=True,
            )
            logger.info(f"Índice FAISS cargado con éxito.")
            return _vector_store
        except Exception as e:
            logger.warning(f"No se pudo cargar el índice FAISS: {e}. Reconstruyendo...")

    # Construir nuevo índice
    logger.info("Construyendo nuevo índice FAISS desde documentos...")
    documents = get_all_documents()
    logger.info(f"Indexando {len(documents)} documentos...")

    _vector_store = FAISS.from_documents(documents, embeddings)

    # Persistir en disco
    FAISS_INDEX_PATH.mkdir(parents=True, exist_ok=True)
    _vector_store.save_local(str(FAISS_INDEX_PATH))
    logger.info(f"Índice FAISS guardado en: {FAISS_INDEX_PATH}")

    return _vector_store


def get_vector_store() -> FAISS:
    """Devuelve el vector store (lo construye si no existe)."""
    return build_vector_store()
