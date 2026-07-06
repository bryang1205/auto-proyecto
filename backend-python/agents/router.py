"""
══════════════════════════════════════════════════════════════════
Chocolates Helena — Router Condicional del Grafo LangGraph
Funciones de routing que determinan el siguiente nodo según
el estado actual del flujo.
══════════════════════════════════════════════════════════════════

Funciones de routing:

    route_after_validation  → decide si el input es válido o no
    route_by_profile        → enruta por perfil (visitante/comprador/admin)
    route_after_front       → decide chat vs checkout
    route_after_payment     → decide aprobado vs rechazado
"""
from __future__ import annotations

import logging
from typing import Literal

from models.schemas import AgentState, FlowStage

logger = logging.getLogger(__name__)


# ── Routing: Validación → Clasificación ──────────────────────────────────────

def route_after_validation(state: AgentState) -> Literal[
    "classify_profile", "__end__"
]:
    """
    Decide si el input pasó la validación y puede continuar al clasificador,
    o si debe terminar con error.

    Args:
        state: Estado actual del grafo.

    Returns:
        "classify_profile" si el input es válido, "__end__" si es inválido.
    """
    validated = state.get("validated", False)
    error = state.get("error")

    if validated and not error:
        logger.info("[Router] route_after_validation → classify_profile (input válido)")
        return "classify_profile"

    logger.info("[Router] route_after_validation → END (input inválido)")
    return "__end__"


# ── Routing: Clasificación → Agente ──────────────────────────────────────────

def route_by_profile(state: AgentState) -> Literal[
    "info_agent", "front_agent", "admin_agent"
]:
    """
    Decide el siguiente nodo según el perfil del usuario.

    Lógica:
        - admin     → admin_agent
        - comprador → front_agent (luego decide checkout vs chat)
        - default   → info_agent (visitante)

    Args:
        state: Estado actual del grafo.

    Returns:
        Nombre del nodo destino.
    """
    profile    = state.get("profile", "visitante")
    flow_stage = state.get("flow_stage", "")
    order      = state.get("order")
    payment    = state.get("payment")

    logger.info(f"[Router] route_by_profile: profile={profile}, flow_stage={flow_stage}")

    if profile == "admin":
        return "admin_agent"

    if profile == "comprador":
        # Si hay datos de checkout (customer + payment), va al flujo completo
        if order and payment:
            return "front_agent"   # front_agent luego lleva a order_agent
        return "front_agent"

    # Default: visitante
    return "info_agent"


# ── Routing: Front Agent → Checkout o Fin ────────────────────────────────────

def route_after_front(state: AgentState) -> Literal[
    "order_agent", "__end__"
]:
    """
    Decide si el comprador va al flujo de checkout o solo al chat.
    Si el estado tiene order + payment → flujo de compra completo.

    Args:
        state: Estado actual del grafo.

    Returns:
        "order_agent" para checkout, "__end__" para solo chat.
    """
    order = state.get("order")
    payment = state.get("payment")
    

    if order and payment:
        logger.info("[Router] route_after_front → order_agent (flujo checkout)")
        return "order_agent"

    logger.info("[Router] route_after_front → END (solo chat)")
    return "__end__"
# ── Routing: Order → Payment o Fin ───────────────────────────────────────────

def route_after_order(state: AgentState) -> Literal[
    "payment_agent", "__end__"
]:
    """
    Decide si el pedido fue registrado exitosamente → procesar pago,
    o si falló la validación o el stock → END.
    """
    flow_stage = state.get("flow_stage", "")
    error      = state.get("error")

    if flow_stage == FlowStage.ORDER.value and not error:
        logger.info("[router]\n-> payment_agent")
        return "payment_agent"

    logger.info(f"[router]\n-> END (order fallido: {error})")
    return "__end__"


# ── Routing: Payment → Logística o Fin ───────────────────────────────────────

def route_after_payment(state: AgentState) -> Literal[
    "logistics_agent", "__end__"
]:
    """
    Decide si el pago fue aprobado → logística, o rechazado → END.

    Args:
        state: Estado actual del grafo.

    Returns:
        "logistics_agent" si aprobado, "__end__" si rechazado.
    """
    flow_stage = state.get("flow_stage", "")
    error      = state.get("error")

    if flow_stage == FlowStage.PAYMENT.value and not error:
        logger.info("[router]\n-> logistics_agent")
        return "logistics_agent"

    logger.info(f"[router]\n-> END (pago fallido: {error})")
    return "__end__"
