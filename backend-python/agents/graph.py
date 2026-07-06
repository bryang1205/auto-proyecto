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
  [validate_input]
    │
    ├── válido ───────────▶ [classify_profile]
    │                          │
    │                          ├── "visitante" ──▶ [info_agent] ──────────▶ END
    │                          │
    │                          ├── "comprador" (solo chat) ──▶ [front_agent] ─▶ END
    │                          │
    │                          ├── "comprador" (checkout) ──▶ [front_agent]
    │                          │                                    │
    │                          │                              [order_agent]
    │                          │                                    │
    │                          │                              [payment_agent]
    │                          │                                    │
    │                          │                         aprobado ──┤
    │                          │                                    ▼
    │                          │                            [logistics_agent] ──▶ END
    │                          │                         rechazado ──▶ END (error)
    │                          │
    │                          └── "admin" ──▶ [admin_agent] ──────▶ END
    │
    └── inválido ─────────▶ END (error)
"""
from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from models.schemas import AgentState
from agents.nodes import (
    node_validate_input,
    node_classify_profile,
    node_info_agent,
    node_front_agent,
    node_order_agent,
    node_payment_agent,
    node_logistics_agent,
    node_admin_agent,
)
from agents.router import (
    route_after_validation,
    route_by_profile,
    route_after_front,
    route_after_payment,
    route_after_order,
)

logger = logging.getLogger(__name__)


# ── Construcción del Grafo ────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Construye y compila el grafo LangGraph completo de Chocolates Helena.

    Flujo:
        START → validate_input → classify_profile → agente específico → END

    Returns:
        CompiledGraph listo para invocar.
    """
    graph = StateGraph(AgentState)

    # ── Registrar nodos ───────────────────────────────────────
    graph.add_node("validate_input",     node_validate_input)
    graph.add_node("classify_profile",   node_classify_profile)
    graph.add_node("info_agent",         node_info_agent)
    graph.add_node("front_agent",        node_front_agent)
    graph.add_node("order_agent",        node_order_agent)
    graph.add_node("payment_agent",      node_payment_agent)
    graph.add_node("logistics_agent",    node_logistics_agent)
    graph.add_node("admin_agent",        node_admin_agent)

    # ── Edge de inicio → validación ───────────────────────────
    graph.add_edge(START, "validate_input")

    # ── Routing desde validate_input ──────────────────────────
    graph.add_conditional_edges(
        "validate_input",
        route_after_validation,
        {
            "classify_profile": "classify_profile",
            "__end__":          END,
        },
    )

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

    # ── Routing desde order_agent (registro exitoso vs error) ─
    graph.add_conditional_edges(
        "order_agent",
        route_after_order,
        {
            "payment_agent": "payment_agent",
            "__end__":       END,
        },
    )

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

    logger.info("[Graph] Grafo LangGraph compilado con 8 nodos (incluye validate_input)")
    return graph.compile()


# ── Singleton del grafo compilado ─────────────────────────────────────────────

_compiled_graph = None

def get_graph():
    """Devuelve el grafo compilado (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
