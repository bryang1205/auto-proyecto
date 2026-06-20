"""
══════════════════════════════════════════════════════════════════
Chocolates Helena — Grafo LangGraph
Define la arquitectura de agentes con StateGraph.
Routing condicional por perfil: visitante | comprador | admin
══════════════════════════════════════════════════════════════════

Estructura del grafo:

  START
    │
    ▼
  [classify_profile]
    │
    ├── "visitante" ──▶ [info_agent] ──────────────────────▶ END
    │
    ├── "comprador" (solo chat) ──▶ [front_agent] ─────────▶ END
    │
    ├── "comprador" (checkout) ──▶ [order_agent]
    │                                    │
    │                              [payment_agent]
    │                                    │
    │                         aprobado ──┤
    │                                    ▼
    │                            [logistics_agent] ────────▶ END
    │                         rechazado ──▶ END (error)
    │
    └── "admin" ──▶ [admin_agent] ───────────────────────▶ END
"""
from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from models.schemas import AgentState, FlowStage
from agents.nodes import (
    node_classify_profile,
    node_info_agent,
    node_front_agent,
    node_order_agent,
    node_payment_agent,
    node_logistics_agent,
    node_admin_agent,
)

logger = logging.getLogger(__name__)


# ── Funciones de Routing Condicional ─────────────────────────────────────────

def route_by_profile(state: AgentState) -> Literal[
    "info_agent", "front_agent", "admin_agent"
]:
    """Decide el siguiente nodo según el perfil del usuario."""
    profile    = state.get("profile", "visitante")
    flow_stage = state.get("flow_stage", "")
    order      = state.get("order")
    payment    = state.get("payment")

    logger.info(f"[Graph] route_by_profile: profile={profile}, flow_stage={flow_stage}")

    if profile == "admin":
        return "admin_agent"

    if profile == "comprador":
        # Si hay datos de checkout (customer + payment), va al flujo completo
        if order and payment:
            return "front_agent"   # front_agent luego lleva a order_agent
        return "front_agent"

    # Default: visitante
    return "info_agent"


def route_after_front(state: AgentState) -> Literal[
    "order_agent", "__end__"
]:
    """
    Decide si el comprador va al flujo de checkout o solo al chat.
    Si el estado tiene order + payment → flujo de compra completo.
    """
    order   = state.get("order")
    payment = state.get("payment")

    if order and payment and state.get("flow_stage") != FlowStage.TRIAGE.value:
        logger.info("[Graph] route_after_front → order_agent (flujo checkout)")
        return "order_agent"

    logger.info("[Graph] route_after_front → END (solo chat)")
    return "__end__"


def route_after_payment(state: AgentState) -> Literal[
    "logistics_agent", "__end__"
]:
    """Decide si el pago fue aprobado → logística, o rechazado → END."""
    flow_stage = state.get("flow_stage", "")
    error      = state.get("error")

    if flow_stage == FlowStage.PAYMENT.value and not error:
        logger.info("[Graph] route_after_payment → logistics_agent (pago aprobado)")
        return "logistics_agent"

    logger.info("[Graph] route_after_payment → END (pago rechazado)")
    return "__end__"


# ── Construcción del Grafo ────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Construye y compila el grafo LangGraph completo de Chocolates Helena.
    
    Returns:
        CompiledGraph listo para invocar.
    """
    graph = StateGraph(AgentState)

    # ── Registrar nodos ───────────────────────────────────────
    graph.add_node("classify_profile",  node_classify_profile)
    graph.add_node("info_agent",         node_info_agent)
    graph.add_node("front_agent",        node_front_agent)
    graph.add_node("order_agent",        node_order_agent)
    graph.add_node("payment_agent",      node_payment_agent)
    graph.add_node("logistics_agent",    node_logistics_agent)
    graph.add_node("admin_agent",        node_admin_agent)

    # ── Edge de inicio ────────────────────────────────────────
    graph.add_edge(START, "classify_profile")

    # ── Routing desde classify_profile ────────────────────────
    graph.add_conditional_edges(
        "classify_profile",
        route_by_profile,
        {
            "info_agent":  "info_agent",
            "front_agent": "front_agent",
            "admin_agent": "admin_agent",
        },
    )

    # ── Routing desde front_agent (chat vs checkout) ───────────
    graph.add_conditional_edges(
        "front_agent",
        route_after_front,
        {
            "order_agent": "order_agent",
            "__end__":     END,
        },
    )

    # ── Flujo secuencial: order → payment ──────────────────────
    graph.add_edge("order_agent", "payment_agent")

    # ── Routing desde payment_agent (aprobado vs rechazado) ────
    graph.add_conditional_edges(
        "payment_agent",
        route_after_payment,
        {
            "logistics_agent": "logistics_agent",
            "__end__":         END,
        },
    )

    # ── Nodos terminales ──────────────────────────────────────
    graph.add_edge("info_agent",      END)
    graph.add_edge("logistics_agent", END)
    graph.add_edge("admin_agent",     END)

    logger.info("[Graph] Grafo LangGraph compilado con 7 nodos")
    return graph.compile()


# ── Singleton del grafo compilado ─────────────────────────────────────────────

_compiled_graph = None

def get_graph():
    """Devuelve el grafo compilado (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
