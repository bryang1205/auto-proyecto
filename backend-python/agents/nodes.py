"""
══════════════════════════════════════════════════════════════════
Chocolates Helena — Nodos del Grafo LangGraph
Cada función es un nodo que recibe AgentState y retorna
un dict parcial que actualiza el estado compartido.
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langsmith import traceable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from models.schemas import AgentState, FlowStage
from rag.retriever import get_retriever
from agents.profiles import classify_user_profile
from agents.tools import (
    STOCK_DB,
    PEDIDOS_DB,
    verificar_stock,
    insertar_pedido,
    procesar_pago,
    calcular_ruta_entrega,
    actualizar_pedido_produccion,
    actualizar_pedido_entrega,
    cancelar_pedido,
    obtener_todos_pedidos,
    obtener_stock_actual,
)

logger = logging.getLogger(__name__)


# ── LLM Singleton ─────────────────────────────────────────────────────────────

_llm: ChatGoogleGenerativeAI | None = None

def get_llm() -> ChatGoogleGenerativeAI:
    """Devuelve la instancia del LLM Gemini (singleton)."""
    global _llm
    if _llm is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key or "TU_CLAVE" in api_key:
            raise RuntimeError(
                "GEMINI_API_KEY no configurada. "
                "Añade tu clave en backend-python/.env"
            )
        model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
        _llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.7,
            max_output_tokens=512,
            max_retries=1,  # Evita bloqueos prolongados por cuotas excedidas
        )
        logger.info(f"✅ LLM Gemini ({model_name}) inicializado")
    return _llm


def _append_path(state: AgentState, node_name: str) -> list[str]:
    path = list(state.get("node_path", []))
    path.append(node_name)
    return path


def _extract_text(content: Any) -> str:
    """Extrae el contenido de texto si `content` viene como una lista de partes."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif hasattr(part, "text"):
                text_parts.append(part.text)
        return "".join(text_parts)
    return str(content)


def _convert_history(messages_list: list[dict[str, str]]) -> list[AIMessage | HumanMessage]:
    """Convierte el historial de mensajes a objetos de mensaje de LangChain."""
    converted: list[AIMessage | HumanMessage] = []
    for msg in messages_list:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            converted.append(HumanMessage(content=content))
        elif role in ("assistant", "ai"):
            converted.append(AIMessage(content=content))
    return converted


# ── Prompts Oficiales de LangChain ────────────────────────────────────────────

_INFO_SYSTEM = """Eres el asistente premium de "Chocolates Helena", chocolatería artesanal peruana.
Tu personalidad: cálida, elegante, apasionada por el chocolate. Siempre en español latinoamericano.
Usa el contexto proporcionado para responder con precisión. Si no sabes algo, sé honesto.
Máximo 3-4 oraciones. Usa ocasionalmente emojis de chocolate 🍫."""

_INFO_HUMAN = """Contexto de Chocolates Helena:
{rag_context}

---
Pregunta del cliente: {user_message}

Responde usando el contexto anterior cuando sea relevante."""

_INFO_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _INFO_SYSTEM),
    ("human", _INFO_HUMAN),
])

_COMPRADOR_SYSTEM = """Eres el asistente premium de "Chocolates Helena", chocolatería artesanal peruana.
Tu personalidad: cálida, elegante, apasionada por el chocolate. Siempre en español latinoamericano.
El cliente tiene productos en su carrito o intención de comprar.
Catálogo disponible:
• Trufa Negra Intenso — $45.000 COP (70% cacao, oro comestible)
• Bombón de Maracuyá — $38.000 COP (relleno tropical fresco)
• Tableta de Leche Premium — $32.000 COP (caramelo salado artesanal)
• Chocolate Blanco con Rosa — $42.000 COP (pétalos de rosa + frambuesa)
• Caja de Regalo Especial — $120.000 COP (20 piezas seleccionadas)
• Chocolate Negro Picante — $36.000 COP (75% cacao + ají colombiano)
Envíos gratuitos a todo el Perú. Pago con tarjeta en checkout seguro.
Máximo 3-4 oraciones. Usa ocasionalmente emojis de chocolate 🍫.
Si el cliente quiere comprar, indícale que agregue al carrito y proceda al checkout."""

_COMPRADOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _COMPRADOR_SYSTEM),
    MessagesPlaceholder(variable_name="history"),
    ("human", "Contexto del catálogo:\n{rag_context}\n\n---\nMensaje del cliente: {user_message}")
])

_ADMIN_SYSTEM = """Eres el asistente de administración de Chocolates Helena.
Tienes acceso al panel de pedidos, stock e inventario.
Responde con datos precisos y formato estructurado. Siempre en español."""

_ADMIN_HUMAN = """Datos del sistema:
{admin_context}

Pregunta del administrador: {user_message}

Responde de forma clara y estructurada."""

_ADMIN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _ADMIN_SYSTEM),
    ("human", _ADMIN_HUMAN)
])



# ══════════════════════════════════════════════════════════════════════════════
# NODO 0: Validación de Input
# ══════════════════════════════════════════════════════════════════════════════

@traceable(name="validate_input", tags=["validation"])
def node_validate_input(state: AgentState) -> dict:
    """
    Nodo de validación: verifica que el input del usuario sea válido
    antes de continuar con la clasificación de perfil.

    Validaciones:
        - user_message no vacío
        - session_id presente
        - Registra cart y metadata en el estado si existen

    Returns:
        Estado parcial con validated=True/False y campos adicionales.
    """
    logger.info("[Node] validate_input")

    user_message = state.get("user_message", "").strip()
    session_id = state.get("session_id", "").strip()

    # Validación: mensaje requerido
    if not user_message:
        logger.warning("[Node] validate_input: user_message vacío")
        return {
            "validated":      False,
            "error":          "El mensaje del usuario es requerido.",
            "agent_response": "❌ Por favor, escribe un mensaje para que pueda ayudarte.",
            "flow_stage":     FlowStage.ERROR.value,
            "node_path":      _append_path(state, "validate_input"),
        }

    # Validación: session_id requerido
    if not session_id:
        logger.warning("[Node] validate_input: session_id vacío")
        return {
            "validated":      False,
            "error":          "El session_id es requerido.",
            "agent_response": "❌ Error de sesión. Por favor, recarga la página.",
            "flow_stage":     FlowStage.ERROR.value,
            "node_path":      _append_path(state, "validate_input"),
        }

    # Registrar cart en el estado si viene en el input
    cart = state.get("cart")
    if not cart:
        order = state.get("order")
        cart = order.get("items", []) if order else None

    # Registrar metadata en el estado si viene en el input
    metadata = state.get("metadata") or {}

    logger.info(
        f"[Node] validate_input: OK | session={session_id[:12]}... "
        f"| msg_len={len(user_message)} | cart_items={len(cart) if cart else 0}"
    )

    return {
        "validated":  True,
        "cart":       cart,
        "metadata":   metadata,
        "flow_stage": FlowStage.IDLE.value,
        "node_path":  _append_path(state, "validate_input"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODO 1: Clasificar Perfil
# ══════════════════════════════════════════════════════════════════════════════

@traceable(name="classify_profile", tags=["routing"])
def node_classify_profile(state: AgentState) -> dict:
    """
    Nodo de clasificación: determina el perfil del usuario.
    Este es el primer nodo del grafo — decide el flujo a seguir.
    """
    logger.info("[Node] node_classify_profile")

    message     = state.get("user_message", "")
    cart_items  = state.get("order", {}).get("items", []) if state.get("order") else []
    explicit    = state.get("profile", "")

    # Obtener LLM para clasificación semántica (o None si falla)
    llm = None
    try:
        llm = get_llm()
    except Exception as e:
        logger.warning(f"[Node] No se pudo inicializar LLM para clasificación de perfil: {e}. Usando fallback.")

    profile = classify_user_profile(
        user_message=message,
        cart_items=cart_items,
        explicit_type=explicit,
        llm=llm,
    )

    return {
        "profile":   profile.value,
        "node_path": _append_path(state, "classify_profile"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODO 2: Agente Visitante (RAG + Info)
# ══════════════════════════════════════════════════════════════════════════════

_VISITANTE_SYSTEM = """Eres el asistente premium de "Chocolates Helena", chocolatería artesanal peruana.
Tu personalidad: cálida, elegante, apasionada por el chocolate. Siempre en español latinoamericano.
Usa el contexto proporcionado para responder con precisión. Si no sabes algo, sé honesto.
Máximo 3-4 oraciones. Usa ocasionalmente emojis de chocolate 🍫."""

@traceable(name="info_agent", tags=["visitante", "rag"])
def node_info_agent(state: AgentState) -> dict:
    """
    Nodo para usuarios visitantes.
    Usa RAG para recuperar información relevante y responde con Gemini.
    """
    logger.info("[Node] info_agent (visitante)")

    message = state.get("user_message", "")
    retriever = get_retriever(k=3)

    # Búsqueda RAG
    rag_result = retriever.search(message)
    rag_context = rag_result.context
    rag_sources = rag_result.sources

    try:
        llm = get_llm()
        # Pipeline LCEL oficial de LangChain
        info_chain = _INFO_PROMPT | llm | StrOutputParser()
        agent_response = info_chain.invoke({
            "rag_context":  rag_context,
            "user_message": message,
        })
    except Exception as e:
        logger.error(f"[Node] info_agent LLM error: {e}")
        # Fallback inteligente
        agent_response = _fallback_visitante(message, rag_context)

    return {
        "agent_response": agent_response,
        "rag_context":   rag_context,
        "rag_sources":   rag_sources,
        "rag_used":      rag_result.num_results > 0,
        "flow_stage":    FlowStage.COMPLETED.value,
        "node_path":     _append_path(state, "info_agent"),
    }


def _fallback_visitante(message: str, context: str = "") -> str:
    """Respuesta de fallback cuando el LLM no está disponible."""
    msg_lower = message.lower()
    if any(w in msg_lower for w in ["precio", "cuánto", "cuesta", "vale"]):
        return "💰 Nuestros precios van desde **$32.000** (Tableta de Leche) hasta **$120.000** (Caja de Regalo 20 piezas) COP. ¡Todos incluyen envío gratis! 🎁"
    if any(w in msg_lower for w in ["chocolate", "catálogo", "producto", "variedad"]):
        return "🍫 Tenemos 6 variedades premium: Trufa Negra Intenso, Bombón de Maracuyá, Tableta de Leche, Chocolate Blanco con Rosa, Caja de Regalo Especial y Chocolate Negro Picante. ¡Todos artesanales!"
    if any(w in msg_lower for w in ["envío", "entrega", "demora", "tiempo"]):
        return "🚚 Entregamos en toda Lima en 30-90 minutos y en provincias en 24-48 horas. ¡Envío completamente GRATIS sin mínimo de compra!"
    return "¡Hola! 🍫 Soy el asistente de Chocolates Helena. Puedo ayudarte con información del catálogo, precios, envíos y más. ¿En qué te puedo ayudar?"


# ══════════════════════════════════════════════════════════════════════════════
# NODO 3: Agente Comprador — Chat
# ══════════════════════════════════════════════════════════════════════════════

_COMPRADOR_SYSTEM = """Eres el asistente premium de "Chocolates Helena", chocolatería artesanal peruana.
Tu personalidad: cálida, elegante, apasionada por el chocolate. Siempre en español latinoamericano.
El cliente tiene productos en su carrito o intención de comprar.
Catálogo disponible:
• Trufa Negra Intenso — $45.000 COP (70% cacao, oro comestible)
• Bombón de Maracuyá — $38.000 COP (relleno tropical fresco)
• Tableta de Leche Premium — $32.000 COP (caramelo salado artesanal)
• Chocolate Blanco con Rosa — $42.000 COP (pétalos de rosa + frambuesa)
• Caja de Regalo Especial — $120.000 COP (20 piezas seleccionadas)
• Chocolate Negro Picante — $36.000 COP (75% cacao + ají colombiano)
Envíos gratuitos a todo el Perú. Pago con tarjeta en checkout seguro.
Máximo 3-4 oraciones. Usa ocasionalmente emojis de chocolate 🍫.
Si el cliente quiere comprar, indícale que agregue al carrito y proceda al checkout."""

@traceable(name="front_agent", tags=["comprador", "rag"])
def node_front_agent(state: AgentState) -> dict:
    """
    Nodo para usuarios compradores — chat e información.
    Usa RAG + Gemini con contexto de compra y memoria conversacional.
    """
    logger.info("[Node] front_agent (comprador)")

    message   = state.get("user_message", "")
    retriever = get_retriever(k=2)

    # RAG específico para compradores
    rag_result = retriever.search_catalog(message)
    rag_context = rag_result.context

    try:
        llm = get_llm()
        history = state.get("messages", [])[-6:]  # Últimos 3 intercambios
        
        # Pipeline LCEL oficial de LangChain con MessagesPlaceholder para el historial
        comprador_chain = _COMPRADOR_PROMPT | llm | StrOutputParser()
        agent_response = comprador_chain.invoke({
            "history":      _convert_history(history),
            "rag_context":  rag_context,
            "user_message": message,
        })
    except Exception as e:
        logger.error(f"[Node] front_agent LLM error: {e}")
        agent_response = _fallback_visitante(message, rag_context)

    # Actualizar historial
    messages = list(state.get("messages", []))
    messages.append({"role": "user",      "content": message})
    messages.append({"role": "assistant", "content": agent_response})

    return {
        "agent_response": agent_response,
        "messages":       messages,
        "rag_context":    rag_result.context,
        "rag_sources":    rag_result.sources,
        "rag_used":       rag_result.num_results > 0,
        "flow_stage":     FlowStage.TRIAGE.value,
        "node_path":      _append_path(state, "front_agent"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODO 4: Agente de Pedidos
# ══════════════════════════════════════════════════════════════════════════════

@traceable(name="order_agent", tags=["comprador", "checkout", "stock"])
def node_order_agent(state: AgentState) -> dict:
    """
    Nodo de validación y registro del pedido.
    Verifica stock e inserta el pedido en la BD simulada.
    """
    logger.info("[Node] order_agent")

    order_data  = state.get("order", {})
    customer    = state.get("customer", {})
    items       = order_data.get("items", [])

    if not items:
        logger.info("[order_agent]\nerror=Carrito vacio\nflow=error")
        return {
            "agent_response": "❌ No hay productos en el carrito. Por favor agrega chocolates antes de continuar.",
            "flow_stage":     FlowStage.ERROR.value,
            "error":          "Carrito vacío",
            "node_path":      _append_path(state, "order_agent"),
        }

    # Verificar stock de cada ítem
    stock_errors = []
    for item in items:
        pid = item.get("product_id") or item.get("type", "")
        qty = item.get("quantity", 1)
        result = verificar_stock.invoke({"producto_id": pid, "cantidad": qty})
        if not result.get("disponible", False):
            stock_errors.append(f"{item.get('name', pid)} (Solicitado: {qty}, Disponible: {result.get('stock_actual', 0)})")

    if stock_errors:
        logger.info("[order_agent]\nerror=Stock insuficiente\nflow=error")
        return {
            "agent_response": f"⚠️ Algunos productos no tienen stock suficiente: {', '.join(stock_errors)}",
            "flow_stage":     FlowStage.ERROR.value,
            "error":          "Stock insuficiente",
            "node_path":      _append_path(state, "order_agent"),
        }

    # Insertar pedido
    total = order_data.get("total", sum(
        item.get("price", 0) * item.get("quantity", 1) for item in items
    ))

    pedido_result = insertar_pedido.invoke({
        "cliente_nombre":   customer.get("nombre", ""),
        "cliente_email":    customer.get("email", ""),
        "cliente_telefono": customer.get("telefono", ""),
        "direccion":        customer.get("direccion", ""),
        "items":            json.dumps(items),
        "total":            total,
    })

    if not pedido_result.get("success"):
        logger.info("[order_agent]\nerror=Error insercion pedido\nflow=error")
        return {
            "agent_response": "❌ Error al registrar el pedido. Por favor intenta nuevamente.",
            "flow_stage":     FlowStage.ERROR.value,
            "error":          "Error inserción pedido",
            "node_path":      _append_path(state, "order_agent"),
        }

    # Actualizar estado con el ID del pedido
    updated_order = dict(order_data)
    updated_order["pedido_id"] = pedido_result["pedido_id"]
    updated_order["status"]    = "Pendiente de Pago"

    logger.info(f"[Node] order_agent: Pedido {pedido_result['pedido_id']} creado")
    logger.info("[order_agent]\nerror=None\nflow=order")
    return {
        "order":          updated_order,
        "agent_response": f"✅ Pedido {pedido_result['pedido_id']} registrado. Procesando pago...",
        "flow_stage":     FlowStage.ORDER.value,
        "error":          None,
        "node_path":      _append_path(state, "order_agent"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODO 5: Agente de Pagos
# ══════════════════════════════════════════════════════════════════════════════

@traceable(name="payment_agent", tags=["comprador", "checkout", "pago"])
def node_payment_agent(state: AgentState) -> dict:
    """
    Nodo de procesamiento de pagos.
    Llama a la herramienta procesar_pago y determina el siguiente nodo.
    """
    logger.info("[Node] payment_agent")

    payment_data = state.get("payment", {})
    order_data   = state.get("order", {})

    if not payment_data:
        logger.info("[payment_agent]\nerror=Datos de pago faltantes\nflow=error")
        return {
            "agent_response": "❌ No se recibieron datos de pago.",
            "flow_stage":     FlowStage.ERROR.value,
            "error":          "Datos de pago faltantes",
            "node_path":      _append_path(state, "payment_agent"),
        }

    # Procesar pago
    pay_result = procesar_pago.invoke({
        "card_number": payment_data.get("card_number", ""),
        "card_holder": payment_data.get("card_holder", ""),
        "expiry":      payment_data.get("expiry", ""),
        "cvv":         payment_data.get("cvv", ""),
        "monto":       order_data.get("total", 0),
    })

    if pay_result.get("aprobado"):
        updated_order = dict(order_data)
        updated_order["payment_token"]  = pay_result.get("token")
        updated_order["payment_status"] = "approved"
        updated_order["banco"]          = pay_result.get("banco", "")

        logger.info(f"[Node] payment_agent: PAGO APROBADO — token {pay_result.get('token')}")
        logger.info("[payment_agent]\nerror=None\nflow=payment")
        return {
            "order":          updated_order,
            "payment_result": pay_result,
            "agent_response": f"✅ ¡Pago aprobado! Token: {pay_result.get('token', '')}",
            "flow_stage":     FlowStage.PAYMENT.value,
            "error":          None,
            "node_path":      _append_path(state, "payment_agent"),
        }
    else:
        # Pago rechazado — cancelar pedido
        pedido_id = order_data.get("pedido_id", "")
        if pedido_id:
            cancelar_pedido.invoke({
                "pedido_id": pedido_id,
                "motivo":    pay_result.get("motivo", "Pago rechazado"),
            })

        motivo = pay_result.get("motivo", "El banco no autorizó la transacción")
        logger.info(f"[Node] payment_agent: PAGO RECHAZADO — {motivo}")
        logger.info(f"[payment_agent]\nerror={motivo}\nflow=error")
        return {
            "payment_result": pay_result,
            "agent_response": (
                f"😔 Tu pago no pudo procesarse.\n\n"
                f"**Motivo:** {motivo}\n\n"
                f"Puedes intentar con otra tarjeta. "
                f"Tarjeta de prueba: 4242 4242 4242 4242"
            ),
            "flow_stage":     FlowStage.ERROR.value,
            "error":          motivo,
            "node_path":      _append_path(state, "payment_agent"),
        }


# ══════════════════════════════════════════════════════════════════════════════
# NODO 6: Agente de Logística
# ══════════════════════════════════════════════════════════════════════════════

@traceable(name="logistics_agent", tags=["comprador", "checkout", "logistica"])
def node_logistics_agent(state: AgentState) -> dict:
    """
    Nodo de logística y entrega.
    Actualiza el pedido a 'En Preparación' y calcula la ruta de entrega.
    """
    logger.info("[Node] logistics_agent")

    order_data = state.get("order", {})
    customer   = state.get("customer", {})
    pedido_id  = order_data.get("pedido_id", "")
    direccion  = customer.get("direccion", order_data.get("direccion_entrega", "Lima"))

    # Paso 1: Actualizar a "En Preparación"
    prod_result = actualizar_pedido_produccion.invoke({"pedido_id": pedido_id})
    if not prod_result.get("success"):
        logger.warning(f"[Node] logistics_agent: No se pudo actualizar pedido {pedido_id}")

    # Paso 2: Calcular ruta
    ruta = calcular_ruta_entrega.invoke({"direccion_destino": direccion})

    # Paso 3: Actualizar pedido con ruta
    actualizar_pedido_entrega.invoke({
        "pedido_id": pedido_id,
        "ruta_info": json.dumps(ruta),
    })

    # Respuesta final rica
    eta_texto    = ruta.get("tiempoEstimadoTexto", "30-45 minutos")
    distancia_km = ruta.get("distanciaKm", 0)
    tracking_id  = ruta.get("tracking_id", "")
    nombre       = customer.get("nombre", "cliente")

    agent_response = (
        f"🎉 ¡Tu pedido está confirmado, {nombre}!\n\n"
        f"📦 **Pedido:** {pedido_id}\n"
        f"📡 **Tracking:** {tracking_id}\n"
        f"📍 **Destino:** {direccion}\n"
        f"📏 **Distancia:** {distancia_km} km\n"
        f"⏱️ **Tiempo estimado:** {eta_texto}\n\n"
        f"🚴 Tu mensajero Helena está en camino. ¡Disfruta tus chocolates! 🍫"
    )

    updated_order = dict(order_data)
    updated_order["status"]       = "En Camino"
    updated_order["ruta_entrega"] = ruta
    updated_order["tracking_id"]  = tracking_id

    logger.info(f"[Node] logistics_agent: Pedido {pedido_id} → En Camino. ETA: {eta_texto}")
    logger.info(f"[logistics_agent]\ntracking={tracking_id}\nflow=completed")
    return {
        "order":          updated_order,
        "route_result":   ruta,
        "agent_response": agent_response,
        "flow_stage":     FlowStage.COMPLETED.value,
        "error":          None,
        "node_path":      _append_path(state, "logistics_agent"),
    }


@traceable(name="admin_agent", tags=["admin"])
def node_admin_agent(state: AgentState) -> dict:
    """
    Nodo para administradores.
    Consulta pedidos y stock, responde con Gemini.
    """
    logger.info("[Node] admin_agent")

    message = state.get("user_message", "")
    msg_lower = message.lower()

    # Determinar qué datos necesita
    context_parts = []

    if any(w in msg_lower for w in ["pedido", "orden", "venta", "compra"]):
        pedidos = obtener_todos_pedidos.invoke({})
        context_parts.append(f"PEDIDOS ACTUALES:\n{json.dumps(pedidos, indent=2, ensure_ascii=False)}")

    if any(w in msg_lower for w in ["stock", "inventario", "producto", "disponible"]):
        stock = obtener_stock_actual.invoke({})
        context_parts.append(f"STOCK ACTUAL:\n{json.dumps(stock, indent=2, ensure_ascii=False)}")

    if not context_parts:
        pedidos = obtener_todos_pedidos.invoke({})
        stock   = obtener_stock_actual.invoke({})
        context_parts = [
            f"PEDIDOS ({len(pedidos)} total):\n{json.dumps(pedidos[-5:], indent=2, ensure_ascii=False)}",
            f"STOCK:\n{json.dumps(stock, indent=2, ensure_ascii=False)}",
        ]

    admin_context = "\n\n".join(context_parts)

    try:
        llm = get_llm()
        # Pipeline LCEL oficial de LangChain
        admin_chain = _ADMIN_PROMPT | llm | StrOutputParser()
        agent_response = admin_chain.invoke({
            "admin_context": admin_context,
            "user_message":  message,
        })
    except Exception as e:
        logger.error(f"[Node] admin_agent LLM error: {e}")
        agent_response = f"📊 Panel Admin — {len(PEDIDOS_DB)} pedidos | Stock: {sum(v['cantidad'] for v in STOCK_DB.values())} unidades totales"

    return {
        "agent_response": agent_response,
        "rag_used":       False,
        "flow_stage":     FlowStage.COMPLETED.value,
        "node_path":      _append_path(state, "admin_agent"),
    }
