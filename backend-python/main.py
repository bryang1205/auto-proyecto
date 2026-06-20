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
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Cargar .env antes de cualquier import del proyecto ────────────────────────
load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("helena-backend")

# ── Imports del proyecto (después del load_dotenv) ────────────────────────────
from tracing.langsmith_config import configure_langsmith, get_langsmith_status, build_run_config
from models.schemas import (
    AgentState,
    CartItem,
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

    # 1. Configurar LangSmith
    ls_ok = configure_langsmith()

    # 2. Pre-cargar el índice FAISS (evita latencia en primera petición)
    logger.info("📚 Cargando base de conocimiento FAISS...")
    try:
        build_vector_store()
        logger.info("✅ Vector store FAISS listo")
    except Exception as e:
        logger.warning(f"⚠️ FAISS no disponible: {e}. El RAG estará desactivado.")

    # 3. Pre-compilar el grafo LangGraph
    logger.info("🔗 Compilando grafo LangGraph...")
    try:
        get_graph()
        logger.info("✅ Grafo LangGraph compilado")
    except Exception as e:
        logger.warning(f"⚠️ Grafo no disponible: {e}")

    logger.info("🚀 Servidor listo en http://localhost:8000")
    logger.info("📋 Docs: http://localhost:8000/docs")
    if ls_ok:
        ls = get_langsmith_status()
        logger.info(f"🔭 LangSmith: {ls['dashboard']}")

    yield

    # Cierre
    logger.info("👋 Servidor detenido")


# ── Aplicación FastAPI ────────────────────────────────────────────────────────

app = FastAPI(
    title="Chocolates Helena — API de Agentes",
    description=(
        "Backend con LangChain + LangGraph + RAG (FAISS) + LangSmith\n\n"
        "Perfiles de usuario: visitante | comprador | admin\n"
        "Trazabilidad completa en smith.langchain.com"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:5500",   # Live Server VS Code
    "http://127.0.0.1:5500",
    os.getenv("FRONTEND_ORIGIN", ""),
]
origins = [o for o in origins if o]  # Limpiar vacíos

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed}ms)")
    return response


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/agent/health", tags=["Sistema"])
async def health_check() -> dict[str, Any]:
    """
    Estado del sistema.
    Verifica: servidor, FAISS, grafo LangGraph, LangSmith.
    """
    # Verificar FAISS
    faiss_ok = False
    try:
        from rag.knowledge_base import get_vector_store
        vs = get_vector_store()
        faiss_ok = vs is not None
    except Exception:
        pass

    # Verificar Gemini key
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    gemini_ok  = bool(gemini_key and "TU_CLAVE" not in gemini_key)

    return {
        "status":        "ok",
        "app":           "Chocolates Helena — Backend Python",
        "version":       "2.0.0",
        "framework":     "LangChain + LangGraph + FastAPI",
        "components": {
            "gemini_llm":  gemini_ok,
            "faiss_rag":   faiss_ok,
            "langgraph":   True,
            "langsmith":   get_langsmith_status(),
        },
        "pedidos_en_sesion": len(PEDIDOS_DB),
        "stock_items":       len(STOCK_DB),
        "docs": "http://localhost:8000/docs",
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
    logger.info(f"[API] /chat → session={request.session_id} | profile={request.user_type} | msg={request.message[:50]}")

    # Construir estado inicial del grafo
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

    # Añadir ítems del carrito si los hay
    if request.cart:
        items = [item.model_dump() for item in request.cart]
        initial_state["order"] = {
            "items": items,
            "total": sum(i["price"] * i["quantity"] for i in items),
        }

    # Ejecutar grafo
    try:
        graph  = get_graph()
        result = graph.invoke(
            initial_state,
            config=build_run_config(
                run_name  = f"chat-{request.session_id[:8]}",
                session_id= request.session_id,
                profile   = request.user_type or "visitante",
                tags      = ["chat"],
                metadata  = {"message_preview": request.message[:80]},
            ),
        )
    except Exception as e:
        logger.error(f"[API] /chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en el agente: {str(e)}")

    return ChatResponse(
        message=    result.get("agent_response", "Lo siento, hubo un error procesando tu mensaje."),
        session_id= request.session_id,
        profile=    result.get("profile", request.user_type),
        node_path=  result.get("node_path", []),
        rag_used=   result.get("rag_used", False),
        sources=    result.get("rag_sources", []),
        metadata={
            "flow_stage": result.get("flow_stage"),
            "error":      result.get("error"),
        },
    )


@app.post("/api/agent/checkout", response_model=CheckoutResponse, tags=["Agentes"])
async def checkout(request: CheckoutRequest) -> CheckoutResponse:
    """
    Flujo completo de compra con el enjambre de agentes.
    
    Ejecuta en secuencia:
    1. **classify_profile** → detecta comprador
    2. **order_agent** → verifica stock e inserta pedido
    3. **payment_agent** → procesa pago con tarjeta
    4. **logistics_agent** → calcula ruta y confirma entrega
    
    Todas las etapas quedan trazadas en LangSmith.
    """
    logger.info(f"[API] /checkout → session={request.session_id} | cliente={request.customer.nombre}")

    items = [item.model_dump() for item in request.cart]
    total = sum(i["price"] * i["quantity"] for i in items)

    # Estado inicial con datos de checkout
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
        graph  = get_graph()
        result = graph.invoke(
            initial_state,
            config=build_run_config(
                run_name  = f"checkout-{request.session_id[:8]}",
                session_id= request.session_id,
                profile   = "comprador",
                tags      = ["checkout"],
                metadata  = {
                    "cliente":    request.customer.nombre,
                    "num_items":  len(items),
                    "total_cop":  total,
                },
            ),
        )
    except Exception as e:
        logger.error(f"[API] /checkout error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en el flujo de compra: {str(e)}")

    stage      = result.get("flow_stage", FlowStage.ERROR.value)
    error      = result.get("error")
    order_data = result.get("order", {})
    ruta       = result.get("route_result", {})
    success    = stage == FlowStage.COMPLETED.value and not error

    return CheckoutResponse(
        success=     success,
        stage=       stage,
        message=     result.get("agent_response", ""),
        order_id=    order_data.get("pedido_id"),
        tracking_id= order_data.get("tracking_id") or ruta.get("tracking_id"),
        eta=         ruta.get("tiempoEstimadoTexto"),
        distancia_km= ruta.get("distanciaKm"),
        node_path=   result.get("node_path", []),
        error=       error,
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


# ── Manejo de errores ─────────────────────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"error": "Ruta no encontrada", "path": str(request.url.path)},
    )

@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.error(f"Error no manejado: {exc}", exc_info=True)
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
