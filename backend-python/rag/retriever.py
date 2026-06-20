"""
══════════════════════════════════════════════════════════════════
Chocolates Helena — Retriever con Caché Pydantic
Wrapper del retriever FAISS que usa caché para evitar
búsquedas duplicadas en la misma sesión.
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import BaseModel, Field

from .knowledge_base import get_vector_store

logger = logging.getLogger(__name__)


# ── Resultado del Retriever (validado con Pydantic) ───────────────────────────

class RetrievalResult(BaseModel):
    """Resultado de una búsqueda vectorial, validado y cacheado."""
    query:       str
    documents:   list[dict[str, Any]]  = Field(default_factory=list)
    context:     str                   = ""
    sources:     list[str]             = Field(default_factory=list)
    num_results: int                   = 0

    @classmethod
    def from_docs(cls, query: str, docs: list[Document]) -> "RetrievalResult":
        """Construye un RetrievalResult desde una lista de Documents."""
        documents_data = []
        sources = []
        context_parts = []

        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "general")
            tema   = doc.metadata.get("tema", "")
            label  = f"{source}/{tema}" if tema else source

            documents_data.append({
                "content":  doc.page_content,
                "source":   source,
                "metadata": doc.metadata,
            })
            sources.append(label)
            context_parts.append(f"[Fuente: {label}]\n{doc.page_content.strip()}")

        return cls(
            query=query,
            documents=documents_data,
            context="\n\n---\n\n".join(context_parts),
            sources=list(dict.fromkeys(sources)),  # Deduplicar preservando orden
            num_results=len(docs),
        )


# ── Cache de búsquedas (evita re-embeber el mismo query) ─────────────────────

@lru_cache(maxsize=256)
def _cached_search(query: str, k: int = 4) -> tuple[str, ...]:
    """
    Realiza búsqueda vectorial con caché LRU.
    Retorna tupla de page_content (inmutable, cacheable).
    """
    try:
        vs = get_vector_store()
        docs = vs.similarity_search(query, k=k)
        return tuple(
            f"{doc.metadata.get('source','')}\t{doc.metadata.get('tema','')}\t{doc.page_content}"
            for doc in docs
        )
    except Exception as e:
        logger.error(f"Error en búsqueda vectorial: {e}")
        return ()


# ── Retriever Principal ───────────────────────────────────────────────────────

class HelenaRetriever:
    """
    Retriever de Chocolates Helena con caché integrada.
    Busca en el índice FAISS y retorna contexto formateado.
    """

    def __init__(self, k: int = 4):
        self.k = k

    def search(self, query: str) -> RetrievalResult:
        """
        Busca documentos relevantes para el query.
        Usa caché automática — queries idénticos no re-embeben.
        """
        logger.info(f"RAG search: '{query[:60]}...' (k={self.k})")

        # Búsqueda con caché
        raw_results = _cached_search(query, self.k)

        if not raw_results:
            return RetrievalResult(query=query, context="No se encontró información relevante.", sources=[])

        # Reconstruir Documents desde la caché
        docs = []
        for raw in raw_results:
            parts = raw.split("\t", 2)
            source = parts[0] if len(parts) > 0 else ""
            tema   = parts[1] if len(parts) > 1 else ""
            content = parts[2] if len(parts) > 2 else raw
            docs.append(Document(
                page_content=content,
                metadata={"source": source, "tema": tema}
            ))

        result = RetrievalResult.from_docs(query, docs)
        logger.info(f"RAG encontró {result.num_results} documentos. Fuentes: {result.sources}")
        return result

    def search_catalog(self, query: str) -> RetrievalResult:
        """Búsqueda específica en el catálogo de productos."""
        return self.search(f"producto chocolate catálogo: {query}")

    def search_faq(self, query: str) -> RetrievalResult:
        """Búsqueda en FAQs y políticas."""
        return self.search(f"pregunta frecuente política envío: {query}")

    def get_langchain_retriever(self) -> BaseRetriever:
        """Retorna un retriever LangChain estándar para usar en cadenas."""
        vs = get_vector_store()
        return vs.as_retriever(search_kwargs={"k": self.k})


# ── Singleton ─────────────────────────────────────────────────────────────────

_retriever_instance: HelenaRetriever | None = None

def get_retriever(k: int = 4) -> HelenaRetriever:
    """Devuelve la instancia singleton del retriever."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = HelenaRetriever(k=k)
    return _retriever_instance
