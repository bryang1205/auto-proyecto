"""
══════════════════════════════════════════════════════════════════
Chocolates Helena — Estado Compartido del Grafo LangGraph
Módulo dedicado para la definición y documentación del estado
que fluye entre todos los nodos del grafo.
══════════════════════════════════════════════════════════════════

Mapeo de campos (nombres existentes → nombres solicitados):

    user_message    → message           (mensaje del usuario)
    profile         → user_type         (perfil/tipo de usuario)
    rag_context     → retrieved_context (contexto RAG recuperado)
    agent_response  → response          (respuesta del agente)
    order           → cart              (datos del pedido/carrito)

Los nombres originales se mantienen para no romper los 7 nodos
y 2 endpoints existentes. Los campos nuevos (cart, metadata,
validated) se añaden al TypedDict en models/schemas.py.
"""
from __future__ import annotations

from models.schemas import AgentState

# Re-export para que `agents.state.AgentState` sea accesible
# sin romper el import canónico desde `models.schemas`.
__all__ = ["AgentState"]
