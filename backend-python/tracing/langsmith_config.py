"""
══════════════════════════════════════════════════════════════════
Chocolates Helena — Configuración LangSmith
Trazabilidad y monitoreo de todas las ejecuciones del sistema.
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import logging
from typing import Any

logger = logging.getLogger(__name__)


def configure_langsmith() -> bool:
    """
    Configura LangSmith para trazabilidad automática.

    LangSmith captura automáticamente:
    - Todas las llamadas a LLMs (Gemini)
    - Ejecuciones del grafo LangGraph (nodo a nodo)
    - Búsquedas vectoriales RAG
    - Latencia, tokens y errores de cada operación

    Returns:
        True si LangSmith está configurado correctamente, False si falta la key.
    """
    api_key  = os.getenv("LANGCHAIN_API_KEY", "")
    project  = os.getenv("LANGCHAIN_PROJECT", "chocolates-helena")
    endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    tracing  = os.getenv("LANGCHAIN_TRACING_V2", "false").lower()

    if not api_key or api_key.startswith("lsv2_pt_TU_CLAVE"):
        logger.warning(
            "⚠️  LangSmith no configurado. "
            "Las trazas no serán enviadas a smith.langchain.com. "
            "Para activar: añade LANGCHAIN_API_KEY en .env"
        )
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return False

    # Activar tracing y propagar todas las variables de entorno
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"]    = project
    os.environ["LANGCHAIN_API_KEY"]    = api_key
    os.environ["LANGCHAIN_ENDPOINT"]   = endpoint

    logger.info(f"✅ LangSmith activado. Proyecto: '{project}'")
    logger.info(f"   Dashboard: https://smith.langchain.com/projects/{project}")
    return True


def get_langsmith_status() -> dict[str, Any]:
    """Retorna el estado actual de la configuración LangSmith."""
    api_key   = os.getenv("LANGCHAIN_API_KEY", "")
    project   = os.getenv("LANGCHAIN_PROJECT", "chocolates-helena")
    is_active = (
        os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        and bool(api_key)
        and not api_key.startswith("lsv2_pt_TU_CLAVE")
    )
    return {
        "active":         is_active,
        "project":        project,
        "endpoint":       os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
        "dashboard":      f"https://smith.langchain.com/projects/{project}" if is_active else None,
        "key_configured": bool(api_key and not api_key.startswith("lsv2_pt_TU_CLAVE")),
    }


def build_run_config(
    run_name: str,
    session_id: str,
    profile: str,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Construye el dict `config` que se pasa a graph.invoke().

    Cada ejecución del grafo aparece en LangSmith con:
    - run_name  : identificador legible (ej. "chat-abc123")
    - tags      : perfil del usuario + tipo de flujo
    - metadata  : sesión, perfil, versión del sistema

    Args:
        run_name:   Nombre del run visible en el dashboard de LangSmith.
        session_id: ID de sesión del usuario.
        profile:    Perfil detectado (visitante / comprador / admin).
        tags:       Tags adicionales opcionales.
        metadata:   Metadata adicional opcional.

    Returns:
        Dict listo para pasar como `config=` a graph.invoke().
    """
    base_tags = [f"profile:{profile}", "helena-backend", "langgraph"]
    if tags:
        base_tags.extend(tags)

    base_metadata: dict[str, Any] = {
        "session_id":     session_id,
        "profile":        profile,
        "system_version": "2.0.0",
        "project":        os.getenv("LANGCHAIN_PROJECT", "chocolates-helena"),
    }
    if metadata:
        base_metadata.update(metadata)

    return {
        "run_name": run_name,
        "tags":     base_tags,
        "metadata": base_metadata,
    }
