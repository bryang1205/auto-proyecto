"""
══════════════════════════════════════════════════════════════════
Chocolates Helena — Backend Python (FastAPI + LangGraph)
Puerto: 8000

Endpoints:
  GET  /api/agent/health    → Estado del sistema + LangSmith
  POST /api/agent/chat      → Chat con agente (perfil auto-detectado)
  POST /api/agent/checkout  → Flujo completo de compra
  GET  /api/agent/pedidos   → Lista de pedidos (admin)
  GET  /api/agent/stock     → Stock actual (admin)
  GET  /api/agent/debug     → Diagnóstico completo del sistema
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any

# ══════════════════════════════════════════════════════════════════════════════
# PASO 1: Cargar .env ANTES de cualquier import de LangChain/LangGraph.
# Esto es CRÍTICO para que LangSmith capture todas las trazas.
# ══════════════════════════════════════════════════════════════════════════════
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
# PASO 2: Configurar LangSmith INMEDIATAMENTE después de cargar .env.
# DEBE ejecutarse ANTES de importar cualquier módulo de LangChain/LangGraph
# porque langchain-core lee os.environ al momento del import para decidir
# si activa el tracing automático.
# ══════════════════════════════════════════════════════════════════════════════
from tracing.langsmith_config import (
    configure_langsmith,
    get_langsmith_status,
    build_run_config,
)

_langsmith_ok = configure_langsmith()

# ══════════════════════════════════════════════════════════════════════════════
# PASO 3: Logging (después de .env para respetar LOG_LEVEL si existiera).
# ══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("helena-backend")

# ══════════════════════════════════════════════════════════════════════════════
# PASO 4: AHORA importar componentes del proyecto (LangChain ya ve las env vars).
# ══════════════════════════════════════════════════════════════════════════════
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models.schemas import (
    AgentState,
    ChatRequest,
    ChatResponse,
    CheckoutRequest,
    CheckoutResponse,
    FlowStage,
)
from agents.graph import get_graph
from agents.tools import PEDIDOS_DB, STOCK_DB
from rag.knowledge_base import build_vector_store


# ── Startup / Shutdown ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Tareas de inicio y cierre del servidor."""
    logger.info("🍫 ═══════════════════════════════════════════")
    logger.info("🍫  Chocolates Helena — Backend Python")
    logger.info("🍫 ═══════════════════════════════════════════")

    # LangSmith ya fue configurado en el módulo (PASO 2)
    if _langsmith_ok:
        ls = get_langsmith_status()
        logger.info(f"🔭 LangSmith activo: {ls['dashboard']}")
    else:
        logger.warning("⚠️  LangSmith no activo — revisa LANGCHAIN_API_KEY en .env")

    # Pre-cargar el índice FAISS
    logger.info("📚 Cargando base de conocimiento FAISS...")
    try:
        build_vector_store()
        logger.info("✅ Vector store FAISS listo")
    except Exception as e:
        logger.warning(f"⚠️ FAISS no disponible: {e}. El RAG estará desactivado.")

    # Pre-compilar el grafo LangGraph
    logger.info("🔗 Compilando grafo LangGraph...")
    try:
        get_graph()
        logger.info("✅ Grafo LangGraph compilado")
    except Exception as e:
        logger.warning(f"⚠️ Grafo no disponible: {e}")

    logger.info("🚀 Servidor listo en http://localhost:8000")
    logger.info("📋 Docs: http://localhost:8000/docs")

    yield

    logger.info("👋 Servidor detenido")


# ── Aplicación FastAPI ────────────────────────────────────────────────────────

app = FastAPI(
    title="Chocolates Helena — API de Agentes",
    description=(
        "Backend con LangChain + LangGraph + RAG (FAISS) + LangSmith\n\n"
        "Perfiles de usuario: visitante | comprador | admin\n"
        "Trazabilidad completa en smith.langchain.com"
    ),
    version="2.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

_CORS_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://[::1]:8080",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://[::1]:5500",
    "http://localhost:5501",
    "http://127.0.0.1:5501",
    "http://[::1]:5501",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://[::1]:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://[::1]:5173",
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://[::1]:4200",
]
_frontend = os.getenv("FRONTEND_ORIGIN", "")
if _frontend:
    _CORS_ORIGINS.append(_frontend)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware de timing ──────────────────────────────────────────────────────

@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Process-Time-Ms"] = str(elapsed)
    logger.info(
        "%s %s -> %s (%.1fms)",
        request.method, request.url.path, response.status_code, elapsed,
    )
    return response


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/agent/health", tags=["Sistema"])
async def health_check() -> dict[str, Any]:
    """
    Estado del sistema.
    Verifica: servidor, FAISS, grafo LangGraph, LangSmith.
    """
    faiss_ok = False
    try:
        from rag.knowledge_base import get_vector_store
        faiss_ok = get_vector_store() is not None
    except Exception:
        pass

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    gemini_ok = bool(gemini_key and "TU_CLAVE" not in gemini_key)

    return {
        "status":            "ok",
        "app":               "Chocolates Helena — Backend Python",
        "version":           "2.1.0",
        "framework":         "LangChain + LangGraph + FastAPI",
        "components": {
            "gemini_llm":    gemini_ok,
            "faiss_rag":     faiss_ok,
            "langgraph":     True,
            "langsmith":     get_langsmith_status(),
        },
        "pedidos_en_sesion": len(PEDIDOS_DB),
        "stock_items":       len(STOCK_DB),
        "docs":              "http://localhost:8000/docs",
    }


@app.post("/api/agent/chat", response_model=ChatResponse, tags=["Agentes"])
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat con el agente de Chocolates Helena.

    Detecta automáticamente el perfil del usuario y enruta al agente correcto:
    - **visitante** → Agente informativo con RAG
    - **comprador** → Agente de atención con historial de conversación
    - **admin** → Agente de administración con acceso a pedidos y stock

    Todas las ejecuciones quedan trazadas en LangSmith.
    """
    logger.info(
        "[API] /chat -> session=%s | profile=%s | msg=%s",
        request.session_id, request.user_type, request.message[:50],
    )

    initial_state: AgentState = {
        "messages":     [],
        "session_id":   request.session_id,
        "profile":      request.user_type,
        "user_message": request.message,
        "rag_context":  "",
        "rag_sources":  [],
        "rag_used":     False,
        "node_path":    [],
        "flow_stage":   FlowStage.IDLE.value,
        "error":        None,
    }

    if request.cart:
        items = [item.model_dump() for item in request.cart]
        initial_state["order"] = {
            "items": items,
            "total": sum(i["price"] * i["quantity"] for i in items),
        }

    try:
        graph = get_graph()
        result = graph.invoke(
            initial_state,
            config=build_run_config(
                run_name=f"chat-{request.session_id[:8]}",
                session_id=request.session_id,
                profile=request.user_type or "visitante",
                tags=["chat"],
                metadata={"message_preview": request.message[:80]},
            ),
        )
    except Exception as e:
        logger.error("[API] /chat error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en el agente: {e}")

    return ChatResponse(
        message=result.get("agent_response", "Lo siento, hubo un error procesando tu mensaje."),
        session_id=request.session_id,
        profile=result.get("profile", request.user_type),
        node_path=result.get("node_path", []),
        rag_used=result.get("rag_used", False),
        sources=result.get("rag_sources", []),
        metadata={
            "flow_stage": result.get("flow_stage"),
            "error": result.get("error"),
        },
    )


@app.post("/api/agent/checkout", response_model=CheckoutResponse, tags=["Agentes"])
async def checkout(request: CheckoutRequest) -> CheckoutResponse:
    """
    Flujo completo de compra con el enjambre de agentes.

    Ejecuta en secuencia:
    1. **validate_input** → valida datos de entrada
    2. **classify_profile** → detecta comprador
    3. **front_agent** → prepara el contexto de compra
    4. **order_agent** → verifica stock e inserta pedido
    5. **payment_agent** → procesa pago con tarjeta
    6. **logistics_agent** → calcula ruta y confirma entrega

    Todas las etapas quedan trazadas en LangSmith.
    """
    logger.info(
        "[API] /checkout -> session=%s | cliente=%s",
        request.session_id, request.customer.nombre,
    )

    items = [item.model_dump() for item in request.cart]
    total = sum(i["price"] * i["quantity"] for i in items)

    initial_state: AgentState = {
        "messages":     [],
        "session_id":   request.session_id,
        "profile":      "comprador",
        "user_message": "procesar checkout",
        "rag_context":  "",
        "rag_sources":  [],
        "rag_used":     False,
        "node_path":    [],
        "flow_stage":   FlowStage.TRIAGE.value,
        "error":        None,
        "customer":     request.customer.model_dump(),
        "payment":      request.payment.model_dump(),
        "order": {
            "items":             items,
            "total":             total,
            "direccion_entrega": request.customer.direccion,
        },
    }

    try:
        graph = get_graph()
        result = graph.invoke(
            initial_state,
            config=build_run_config(
                run_name=f"checkout-{request.session_id[:8]}",
                session_id=request.session_id,
                profile="comprador",
                tags=["checkout"],
                metadata={
                    "cliente":   request.customer.nombre,
                    "num_items": len(items),
                    "total_cop": total,
                },
            ),
        )
    except Exception as e:
        logger.error("[API] /checkout error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en el flujo de compra: {e}")

    stage = result.get("flow_stage", FlowStage.ERROR.value)
    error = result.get("error")
    order_data = result.get("order", {})
    ruta = result.get("route_result", {})
    success = stage == FlowStage.COMPLETED.value and not error

    return CheckoutResponse(
        success=success,
        stage=stage,
        message=result.get("agent_response", ""),
        order_id=order_data.get("pedido_id"),
        tracking_id=order_data.get("tracking_id") or ruta.get("tracking_id"),
        eta=ruta.get("tiempoEstimadoTexto"),
        distancia_km=ruta.get("distanciaKm"),
        node_path=result.get("node_path", []),
        error=error,
    )


@app.get("/api/agent/pedidos", tags=["Admin"])
async def get_pedidos() -> list[dict]:
    """Lista todos los pedidos de la sesión actual."""
    return list(PEDIDOS_DB.values())


@app.get("/api/agent/stock", tags=["Admin"])
async def get_stock() -> dict[str, Any]:
    """Stock actual de todos los productos."""
    return {
        pid: {
            "disponible": data["disponible"],
            "cantidad":   data["cantidad"],
            "precio":     data["precio"],
        }
        for pid, data in STOCK_DB.items()
    }


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT: Debug / Diagnóstico Completo
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/agent/debug", tags=["Sistema"])
async def debug_system() -> dict[str, Any]:
    """
    Diagnóstico completo del sistema.

    Devuelve estado detallado de cada componente:
    Gemini, FAISS, LangGraph, LangSmith, RAG, versiones de librerías.
    """
    from importlib.metadata import version as pkg_version

    # ── Gemini ────────────────────────────────────────────────
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    gemini_connected = False
    gemini_error = None
    try:
        from agents.nodes import get_llm
        llm = get_llm()
        gemini_connected = llm is not None
    except Exception as e:
        gemini_error = str(e)

    # ── FAISS ─────────────────────────────────────────────────
    faiss_loaded = False
    faiss_error = None
    rag_doc_count = 0
    try:
        from rag.knowledge_base import get_vector_store
        vs = get_vector_store()
        faiss_loaded = vs is not None
        if vs:
            rag_doc_count = vs.index.ntotal
    except Exception as e:
        faiss_error = str(e)

    # ── LangGraph ─────────────────────────────────────────────
    graph_compiled = False
    graph_nodes: list[str] = []
    graph_error = None
    try:
        g = get_graph()
        graph_compiled = g is not None
        if g:
            graph_nodes = [n for n in g.nodes.keys() if n != "__start__"]
    except Exception as e:
        graph_error = str(e)

    # ── LangSmith ─────────────────────────────────────────────
    ls_status = get_langsmith_status()

    # Verificar conectividad real con LangSmith
    ls_connectivity = "not_tested"
    try:
        from langsmith import Client
        client = Client()
        # Intentar un request simple para verificar la key
        list(client.list_projects())
        ls_connectivity = "connected"
    except Exception as e:
        ls_connectivity = f"error: {e}"

    # ── Versiones ─────────────────────────────────────────────
    versions = {}
    for pkg in [
        "langchain-core", "langsmith", "langgraph",
        "langchain-google-genai", "fastapi", "pydantic",
        "faiss-cpu", "uvicorn",
    ]:
        try:
            versions[pkg] = pkg_version(pkg)
        except Exception:
            versions[pkg] = "not installed"

    # ── Estado general ────────────────────────────────────────
    all_ok = all([
        gemini_connected,
        faiss_loaded,
        graph_compiled,
        bool(gemini_key and "TU_CLAVE" not in gemini_key),
    ])

    return {
        "status": "healthy" if all_ok else "degraded",
        "gemini": {
            "connected":  gemini_connected,
            "model":      gemini_model,
            "key_set":    bool(gemini_key and "TU_CLAVE" not in gemini_key),
            "error":      gemini_error,
        },
        "faiss": {
            "loaded":       faiss_loaded,
            "documents":    rag_doc_count,
            "error":        faiss_error,
        },
        "langgraph": {
            "compiled":     graph_compiled,
            "nodes":        graph_nodes,
            "node_count":   len(graph_nodes),
            "error":        graph_error,
        },
        "langsmith": {
            **ls_status,
            "connectivity": ls_connectivity,
            "env_vars": {
                "LANGCHAIN_TRACING_V2":  os.getenv("LANGCHAIN_TRACING_V2", "NOT SET"),
                "LANGCHAIN_PROJECT":     os.getenv("LANGCHAIN_PROJECT", "NOT SET"),
                "LANGCHAIN_ENDPOINT":    os.getenv("LANGCHAIN_ENDPOINT", "NOT SET"),
                "LANGCHAIN_API_KEY":     "set" if os.getenv("LANGCHAIN_API_KEY") else "NOT SET",
            },
        },
        "rag": {
            "documents_indexed": rag_doc_count,
            "retriever_ready":   faiss_loaded,
        },
        "versions":  versions,
        "pedidos":   len(PEDIDOS_DB),
        "stock":     len(STOCK_DB),
    }


# ── Manejo de errores ─────────────────────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"error": "Ruta no encontrada", "path": str(request.url.path)},
    )

@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.error("Error no manejado: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Error interno del servidor", "detail": str(exc)},
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )
