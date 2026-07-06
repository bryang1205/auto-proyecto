"""
══════════════════════════════════════════════════════════════════
Chocolates Helena — Configuración LangSmith
Trazabilidad y monitoreo de todas las ejecuciones del sistema.

IMPORTANTE: Este módulo NO importa ningún componente de LangChain.
Solo manipula os.environ. Debe ejecutarse ANTES de los imports
de langchain-core, langgraph, etc.
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def configure_langsmith() -> bool:
    """
    Configura LangSmith para trazabilidad automática.

    Establece las variables de entorno que langchain-core leerá
    al momento de su primer import para activar el tracing.

    DEBE ejecutarse ANTES de importar langchain-core, langgraph, etc.

    LangSmith captura automáticamente:
    - Todas las llamadas a LLMs (Gemini)
    - Ejecuciones del grafo LangGraph (nodo a nodo)
    - Búsquedas vectoriales RAG
    - Latencia, tokens y errores de cada operación

    Returns:
        True si LangSmith está configurado correctamente, False si falta la key.
    """
    api_key = os.getenv("LANGCHAIN_API_KEY", "")
    project = os.getenv("LANGCHAIN_PROJECT", "chocolates-helena")
    endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    if not api_key or api_key.startswith("lsv2_pt_TU_CLAVE"):
        logger.warning(
            "LangSmith no configurado. "
            "Las trazas no seran enviadas a smith.langchain.com. "
            "Para activar: anade LANGCHAIN_API_KEY en .env"
        )
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return False

    # Forzar las variables de entorno ANTES de que langchain-core las lea.
    # langchain-core usa os.environ directamente para decidir si activa tracing.
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = project
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_ENDPOINT"] = endpoint

    logger.info("LangSmith activado. Proyecto: '%s'", project)
    logger.info("  Dashboard: https://smith.langchain.com/projects/%s", project)

    return True


def get_langsmith_status() -> dict[str, Any]:
    """Retorna el estado actual de la configuración LangSmith."""
    api_key = os.getenv("LANGCHAIN_API_KEY", "")
    project = os.getenv("LANGCHAIN_PROJECT", "chocolates-helena")
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

    El config incluye la key `callbacks` para LangSmith >= 0.9.x
    que requiere pasar el LangChainTracer explícitamente cuando
    el tracing automático no es suficiente.

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
        "system_version": "2.1.0",
        "project":        os.getenv("LANGCHAIN_PROJECT", "chocolates-helena"),
    }
    if metadata:
        base_metadata.update(metadata)

    config: dict[str, Any] = {
        "run_name": run_name,
        "tags":     base_tags,
        "metadata": base_metadata,
    }

    # Si LangSmith está activo, inyectar el LangChainTracer como callback.
    # En versiones recientes de langsmith (>=0.9), el tracing automático
    # usa os.environ, pero pasar el tracer explícitamente garantiza que
    # las trazas se envíen incluso si el auto-tracing no se activa.
    if os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true":
        try:
            from langsmith import Client
            from langchain_core.tracers import LangChainTracer

            tracer = LangChainTracer(
                client=Client(),
                project_name=os.getenv("LANGCHAIN_PROJECT", "chocolates-helena"),
            )
            config["callbacks"] = [tracer]
        except Exception as e:
            logger.warning("No se pudo crear LangChainTracer: %s", e)

    return config
