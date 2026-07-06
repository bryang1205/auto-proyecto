"""
══════════════════════════════════════════════════════════════════
Chocolates Helena — Clasificador de Perfiles de Usuario
Detecta si el usuario es: visitante | comprador | admin
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import re
import logging
from typing import Any, Literal
from pydantic import BaseModel, Field

from models.schemas import UserProfile, AgentState

logger = logging.getLogger(__name__)


class ProfileClassification(BaseModel):
    """Esquema de respuesta para la clasificación del perfil de usuario."""
    profile: Literal["visitante", "comprador", "admin"] = Field(
        description="El perfil clasificado del usuario basado en su mensaje e intención."
    )
    explanation: str = Field(
        description="Breve explicación de la razón de la clasificación."
    )


from langchain_core.prompts import ChatPromptTemplate

_PROFILE_SYSTEM = (
    "Eres un clasificador de perfiles experto para el sistema Chocolates Helena.\n"
    "Debes clasificar la intención del usuario basándote en su mensaje."
)

_PROFILE_HUMAN = (
    "Analiza el siguiente mensaje del usuario y clasifica su perfil en uno de estos tres valores:\n"
    "- 'visitante': Si el usuario saluda, pregunta información general, historia del cacao, maridaje, etc., sin intención de compra inmediata.\n"
    "- 'comprador': Si el usuario quiere comprar, ordenar, agregar al carrito, cotizar para comprar, o proceder al pago.\n"
    "- 'admin': Si el usuario solicita stock, inventario, reportes de ventas, ver pedidos del sistema o gestionar el dashboard.\n\n"
    "Mensaje del usuario: \"{user_message}\""
)

_PROFILE_CLASSIFIER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _PROFILE_SYSTEM),
    ("human", _PROFILE_HUMAN),
])


# ── Señales de detección para cada perfil ────────────────────────────────────

_COMPRADOR_SIGNALS = re.compile(
    r"\b(comprar|pagar|checkout|carrito|pedido|tarjeta|envio|entrega|"
    r"quiero|cuanto|precio|orden|agregar|caja|regalo)\b",
    re.IGNORECASE | re.UNICODE,
)

_ADMIN_SIGNALS = re.compile(
    r"\b(admin|administrador|panel|stock|inventario|pedidos|reportes|"
    r"estadisticas|gestion|dashboard|ventas|administracion)\b",
    re.IGNORECASE | re.UNICODE,
)

_ADMIN_TOKEN = "helena-admin-2026"  # Token simple para el perfil admin


def classify_user_profile(
    user_message: str,
    cart_items: list | None = None,
    explicit_type: str | None = None,
    admin_token: str | None = None,
    llm: Any | None = None,
) -> UserProfile:
    """
    Clasifica el perfil del usuario basado en:
    1. Tipo explícito enviado por el frontend (mayor prioridad)
    2. Token de admin
    3. Si tiene ítems en el carrito → comprador
    4. Clasificación semántica con LLM Structured Output
    5. Fallback: Análisis léxico del mensaje (regex)

    Args:
        user_message:  Mensaje del usuario
        cart_items:    Lista de ítems en el carrito
        explicit_type: Tipo enviado explícitamente por el frontend
        admin_token:   Token de acceso admin (opcional)
        llm:           Instancia del LLM de LangChain (opcional)

    Returns:
        UserProfile enum value
    """
    # 1. Admin por token
    if admin_token and admin_token == _ADMIN_TOKEN:
        logger.info("[Profiles] Perfil: ADMIN (token válido)")
        return UserProfile.ADMIN

    # 2. Tipo explícito del frontend (ya validado por Pydantic, ignorando default 'visitante' para permitir clasificación por mensaje)
    if explicit_type and explicit_type != UserProfile.VISITANTE.value:
        try:
            profile = UserProfile(explicit_type)
            logger.info(f"[Profiles] Perfil explícito del frontend: {profile.value}")
            return profile
        except ValueError:
            pass

    # 3. Tiene ítems en carrito → comprador
    if cart_items and len(cart_items) > 0:
        logger.info(f"[Profiles] Perfil: COMPRADOR (carrito con {len(cart_items)} ítems)")
        return UserProfile.COMPRADOR

    # 4. Clasificación semántica con LLM
    if llm:
        try:
            logger.info("[Profiles] Intentando clasificar perfil con LLM Structured Output...")
            structured_llm = llm.with_structured_output(ProfileClassification)
            classifier_chain = _PROFILE_CLASSIFIER_PROMPT | structured_llm
            classification = classifier_chain.invoke({"user_message": user_message})
            profile_val = classification.profile
            logger.info(f"[Profiles] Clasificación LLM exitosa: '{profile_val}' | Explicación: {classification.explanation}")
            return UserProfile(profile_val)
        except Exception as e:
            logger.warning(f"[Profiles] Error al clasificar con LLM: {e}. Activando fallback de regex.")

    # 5. Fallback: Análisis léxico del mensaje (regex)
    if _ADMIN_SIGNALS.search(user_message):
        logger.info(f"[Profiles] Perfil (fallback): ADMIN (señales en mensaje)")
        return UserProfile.ADMIN

    if _COMPRADOR_SIGNALS.search(user_message):
        logger.info(f"[Profiles] Perfil (fallback): COMPRADOR (señales en mensaje)")
        return UserProfile.COMPRADOR

    # Default: visitante
    logger.info(f"[Profiles] Perfil (fallback): VISITANTE (default)")
    return UserProfile.VISITANTE

