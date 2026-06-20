"""
══════════════════════════════════════════════════════════════════
Chocolates Helena — Schemas Pydantic
Validación centralizada + caché de respuestas para evitar
llamadas redundantes a la LLM.
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Annotated, Any, Dict, List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ── Enumeraciones ─────────────────────────────────────────────────────────────

class UserProfile(str, Enum):
    """Perfiles de usuario para el routing en LangGraph."""
    VISITANTE  = "visitante"   # Solo navega, sin intención de compra inmediata
    COMPRADOR  = "comprador"   # Tiene ítems en carrito o quiere comprar
    ADMIN      = "admin"       # Acceso al panel de administración


class FlowStage(str, Enum):
    """Etapas del flujo de compra."""
    IDLE        = "idle"
    TRIAGE      = "triage"
    ORDER       = "order"
    PAYMENT     = "payment"
    LOGISTICS   = "logistics"
    COMPLETED   = "completed"
    ERROR       = "error"


class PaymentStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING  = "pending"


# ── Modelos de Dominio ────────────────────────────────────────────────────────

class CartItem(BaseModel):
    """Un ítem del carrito de compras."""
    model_config = {"frozen": True}  # Inmutable — hasheable para caché

    product_id:   str   = Field(..., description="ID único del producto, ej: 'trufa_negra'")
    name:         str   = Field(..., description="Nombre del producto")
    price:        float = Field(..., gt=0, description="Precio unitario en COP")
    quantity:     int   = Field(..., ge=1, le=100, description="Cantidad solicitada")

    @property
    def subtotal(self) -> float:
        return self.price * self.quantity

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("El precio debe ser mayor a 0")
        return round(v, 2)


class CustomerData(BaseModel):
    """Datos del cliente capturados en el formulario de checkout."""
    nombre:    str      = Field(..., min_length=2, max_length=100)
    email:     EmailStr = Field(...)
    telefono:  str      = Field(..., min_length=7, max_length=20)
    direccion: str      = Field(..., min_length=8, max_length=300)

    @field_validator("telefono")
    @classmethod
    def clean_phone(cls, v: str) -> str:
        cleaned = "".join(c for c in v if c.isdigit() or c in "+-() ")
        if len(cleaned.replace(" ", "").replace("-", "")) < 7:
            raise ValueError("Teléfono inválido")
        return cleaned.strip()


class PaymentData(BaseModel):
    """Datos de pago del formulario de tarjeta."""
    card_number: str = Field(..., min_length=13, max_length=19)
    card_holder: str = Field(..., min_length=2)
    expiry:      str = Field(..., pattern=r"^\d{2}/\d{2}$")
    cvv:         str = Field(..., min_length=3, max_length=4)

    @field_validator("card_number")
    @classmethod
    def clean_card_number(cls, v: str) -> str:
        return v.replace(" ", "").replace("-", "")


class OrderSchema(BaseModel):
    """Orden de compra completa y validada."""
    pedido_id:         Optional[str]       = None
    cliente:           CustomerData
    items:             List[CartItem]       = Field(..., min_length=1)
    total:             float               = Field(default=0.0)
    status:            FlowStage           = FlowStage.IDLE
    payment_status:    PaymentStatus       = PaymentStatus.PENDING
    payment_token:     Optional[str]       = None
    ruta_entrega:      Optional[Dict[str, Any]] = None
    tracking_id:       Optional[str]       = None
    fecha_creacion:    Optional[str]       = None

    @model_validator(mode="after")
    def compute_total(self) -> "OrderSchema":
        """Calcula el total automáticamente desde los ítems."""
        if self.total == 0.0 and self.items:
            self.total = round(sum(item.subtotal for item in self.items), 2)
        return self


# ── Request / Response de la API ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request al endpoint /api/agent/chat."""
    message:    str               = Field(..., min_length=1, max_length=2000)
    session_id: str               = Field(..., description="ID de sesión del navegador")
    cart:       List[CartItem]    = Field(default_factory=list)
    user_type:  str               = Field(default="visitante")

    @field_validator("user_type")
    @classmethod
    def validate_user_type(cls, v: str) -> str:
        valid = {e.value for e in UserProfile}
        if v not in valid:
            return UserProfile.VISITANTE.value
        return v


class CheckoutRequest(BaseModel):
    """Request al endpoint /api/agent/checkout."""
    session_id:   str         = Field(...)
    customer:     CustomerData
    payment:      PaymentData
    cart:         List[CartItem] = Field(..., min_length=1)


class ChatResponse(BaseModel):
    """Respuesta del agente al frontend."""
    message:      str
    session_id:   str
    profile:      str
    node_path:    List[str]             = Field(default_factory=list)
    rag_used:     bool                   = False
    sources:      List[str]             = Field(default_factory=list)
    metadata:     Dict[str, Any]        = Field(default_factory=dict)


class CheckoutResponse(BaseModel):
    """Respuesta del flujo de checkout."""
    success:      bool
    stage:        str
    message:      str
    order_id:     Optional[str]         = None
    tracking_id:  Optional[str]         = None
    eta:          Optional[str]         = None
    distancia_km: Optional[float]       = None
    node_path:    List[str]             = Field(default_factory=list)
    error:        Optional[str]         = None


# ── Caché de Validación (evitar re-validar mismos datos) ─────────────────────

class ValidationCache(BaseModel):
    """
    Caché de resultados de validación.
    Pydantic serializa/deserializa desde dict para evitar recomputar.
    """
    _cache: Dict[str, Any] = {}

    @classmethod
    def get_stock_key(cls, product_id: str, quantity: int) -> str:
        return f"stock:{product_id}:{quantity}"

    @classmethod
    def get_route_key(cls, address: str) -> str:
        # Normalizar dirección para mejorar hit ratio
        return f"route:{address.lower().strip()[:50]}"


# ── Estado del Grafo LangGraph ────────────────────────────────────────────────

from typing import TypedDict

class AgentState(TypedDict, total=False):
    """
    Estado compartido entre todos los nodos del grafo LangGraph.
    Cada nodo puede leer y escribir en este estado.
    """
    # Conversación
    messages:       List[Dict[str, str]]   # Historial del chat
    session_id:     str

    # Perfil del usuario
    profile:        str                    # visitante | comprador | admin
    user_message:   str                    # Último mensaje del usuario

    # Contexto RAG
    rag_context:    str                    # Documentos recuperados
    rag_sources:    List[str]              # Nombres de fuentes usadas
    rag_used:       bool

    # Orden
    order:          Optional[Dict[str, Any]]
    customer:       Optional[Dict[str, Any]]
    payment:        Optional[Dict[str, Any]]

    # Respuesta del agente
    agent_response: str
    node_path:      List[str]              # Ruta recorrida en el grafo

    # Estado del flujo
    flow_stage:     str
    error:          Optional[str]

    # Resultados de herramientas
    stock_result:   Optional[Dict[str, Any]]
    payment_result: Optional[Dict[str, Any]]
    route_result:   Optional[Dict[str, Any]]
