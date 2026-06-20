"""
══════════════════════════════════════════════════════════════════
Chocolates Helena — Herramientas LangChain
Tools que los agentes pueden invocar durante el flujo de compra.
Simulan los mismos servicios MCP del frontend JS.
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import logging
import math
import random
import uuid
from datetime import datetime
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Inventario Simulado (equivalente a postgresMCP.js) ───────────────────────

STOCK_DB: dict[str, dict] = {
    "trufa_negra":       {"disponible": True,  "cantidad": 48, "precio": 45000},
    "bombon_maracuya":   {"disponible": True,  "cantidad": 35, "precio": 38000},
    "tableta_leche":     {"disponible": True,  "cantidad": 60, "precio": 32000},
    "chocolate_blanco":  {"disponible": True,  "cantidad": 22, "precio": 42000},
    "caja_regalo":       {"disponible": True,  "cantidad": 15, "precio": 120000},
    "chocolate_picante": {"disponible": True,  "cantidad": 30, "precio": 36000},
}

PEDIDOS_DB: dict[str, dict] = {}

# Coordenadas de ciudades peruanas (equivalente a mapsMCP.js)
GEO_BASE: dict[str, dict] = {
    "lima":       {"lat": -12.0464, "lng": -77.0428},
    "miraflores": {"lat": -12.1191, "lng": -77.0299},
    "san isidro": {"lat": -12.0989, "lng": -77.0369},
    "surco":      {"lat": -12.1397, "lng": -76.9976},
    "callao":     {"lat": -12.0565, "lng": -77.1181},
    "arequipa":   {"lat": -16.4090, "lng": -71.5375},
    "cusco":      {"lat": -13.5319, "lng": -71.9675},
    "trujillo":   {"lat": -8.1091,  "lng": -79.0215},
    "piura":      {"lat": -5.1945,  "lng": -80.6328},
    "chiclayo":   {"lat": -6.7714,  "lng": -79.8409},
}

ORIGEN = {"lat": -12.1191, "lng": -77.0299, "nombre": "Bodega Helena — Miraflores"}

# Tarjetas de prueba (equivalente a payment.js)
TEST_CARDS = {
    "4242424242424242": {"status": "approved", "bank": "Helena Test Bank"},
    "4000000000000002": {"status": "rejected", "motivo": "Fondos insuficientes"},
    "4000000000009995": {"status": "rejected", "motivo": "Tarjeta vencida"},
}


# ── Inputs Pydantic para las Tools ────────────────────────────────────────────

class StockInput(BaseModel):
    producto_id: str = Field(description="ID del producto, ej: 'trufa_negra'")
    cantidad:    int = Field(description="Cantidad solicitada", ge=1)


class OrderInput(BaseModel):
    cliente_nombre:   str   = Field(description="Nombre completo del cliente")
    cliente_email:    str   = Field(description="Email del cliente")
    cliente_telefono: str   = Field(description="Teléfono del cliente")
    direccion:        str   = Field(description="Dirección de entrega")
    items:            str   = Field(description="Items como JSON string: [{'product_id':'trufa_negra','quantity':2,'price':45000}]")
    total:            float = Field(description="Total del pedido en COP")


class PaymentInput(BaseModel):
    card_number: str   = Field(description="Número de tarjeta sin espacios")
    card_holder: str   = Field(description="Nombre del titular")
    expiry:      str   = Field(description="Fecha de expiración MM/YY")
    cvv:         str   = Field(description="CVV de la tarjeta")
    monto:       float = Field(description="Monto a cobrar en COP")


class RouteInput(BaseModel):
    direccion_destino: str = Field(description="Dirección de entrega completa")


# ── Herramientas LangChain ────────────────────────────────────────────────────

@tool("verificar_stock", args_schema=StockInput)
def verificar_stock(producto_id: str, cantidad: int) -> dict[str, Any]:
    """
    Verifica disponibilidad de stock para un producto.
    Equivale a postgresMCP.verificar_stock() del frontend JS.
    """
    logger.info(f"[Tool] verificar_stock: {producto_id} x{cantidad}")

    stock = STOCK_DB.get(producto_id)
    if not stock:
        return {"error": f"Producto '{producto_id}' no encontrado", "disponible": False}

    disponible = stock["disponible"] and stock["cantidad"] >= cantidad
    result = {
        "disponible":    disponible,
        "stock_actual":  stock["cantidad"],
        "solicitado":    cantidad,
        "producto_id":   producto_id,
        "precio_unitario": stock["precio"],
    }
    if not disponible:
        result["motivo"] = (
            "Sin stock suficiente"
            if stock["cantidad"] > 0
            else "Producto agotado"
        )
    logger.info(f"[Tool] Stock result: {result}")
    return result


@tool("insertar_pedido", args_schema=OrderInput)
def insertar_pedido(
    cliente_nombre: str,
    cliente_email: str,
    cliente_telefono: str,
    direccion: str,
    items: str,
    total: float,
) -> dict[str, Any]:
    """
    Inserta un nuevo pedido en la base de datos simulada.
    Equivale a postgresMCP.insertar_pedido() del frontend JS.
    """
    import json
    logger.info(f"[Tool] insertar_pedido: {cliente_nombre} | ${total:,.0f}")

    try:
        items_list = json.loads(items) if isinstance(items, str) else items
    except Exception:
        items_list = []

    pedido_id = f"PED-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    pedido = {
        "pedido_id":         pedido_id,
        "cliente_nombre":    cliente_nombre,
        "cliente_email":     cliente_email,
        "cliente_telefono":  cliente_telefono,
        "direccion_entrega": direccion,
        "items":             items_list,
        "total":             total,
        "status":            "Pendiente de Pago",
        "fecha_creacion":    datetime.now().isoformat(),
    }
    PEDIDOS_DB[pedido_id] = pedido

    # Descontar stock
    for item in items_list:
        pid = item.get("product_id") or item.get("type", "")
        qty = item.get("quantity", 1)
        if pid in STOCK_DB and STOCK_DB[pid]["cantidad"] >= qty:
            STOCK_DB[pid]["cantidad"] -= qty
            if STOCK_DB[pid]["cantidad"] <= 0:
                STOCK_DB[pid]["disponible"] = False

    logger.info(f"[Tool] Pedido creado: {pedido_id}")
    return {"pedido_id": pedido_id, "status": "Pendiente de Pago", "success": True}


@tool("procesar_pago", args_schema=PaymentInput)
def procesar_pago(
    card_number: str,
    card_holder: str,
    expiry: str,
    cvv: str,
    monto: float,
) -> dict[str, Any]:
    """
    Procesa un pago con tarjeta de crédito/débito.
    Equivale a paymentMCP del frontend JS.
    Tarjetas de prueba: 4242... aprueba, 4000...0002 rechaza.
    """
    logger.info(f"[Tool] procesar_pago: ${monto:,.0f} | {card_number[-4:]} | {card_holder}")

    clean = card_number.replace(" ", "").replace("-", "")

    # Tarjetas de prueba
    test = TEST_CARDS.get(clean)
    if test:
        if test["status"] == "approved":
            return {
                "aprobado":   True,
                "token":      f"tok_{uuid.uuid4().hex[:12]}",
                "banco":      test["bank"],
                "ultimos4":   clean[-4:],
                "monto":      monto,
            }
        else:
            return {
                "aprobado":   False,
                "motivo":     test["motivo"],
                "ultimos4":   clean[-4:],
            }

    # Validación básica
    if len(clean) < 13 or len(clean) > 19:
        return {"aprobado": False, "motivo": "Número de tarjeta inválido"}

    # Aprobación aleatoria para tarjetas no reconocidas (80% éxito)
    if random.random() > 0.2:
        return {
            "aprobado": True,
            "token":    f"tok_{uuid.uuid4().hex[:12]}",
            "banco":    "Banco Procesador",
            "ultimos4": clean[-4:],
            "monto":    monto,
        }
    return {"aprobado": False, "motivo": "Error de procesamiento bancario"}


@tool("calcular_ruta_entrega", args_schema=RouteInput)
def calcular_ruta_entrega(direccion_destino: str) -> dict[str, Any]:
    """
    Calcula la ruta de entrega desde la bodega Helena hasta el destino.
    Equivale a mapsMCP.calcular_ruta_entrega() del frontend JS.
    """
    logger.info(f"[Tool] calcular_ruta: {direccion_destino}")

    lower = direccion_destino.lower()
    dest_geo = GEO_BASE.get("lima")  # default

    for key, coords in GEO_BASE.items():
        if key in lower:
            dest_geo = coords
            break

    # Calcular distancia Haversine
    def haversine(lat1, lng1, lat2, lng2) -> float:
        R = 6371
        d_lat = math.radians(lat2 - lat1)
        d_lng = math.radians(lng2 - lng1)
        a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    dest_lat = dest_geo["lat"] + (random.random() - 0.5) * 0.05
    dest_lng = dest_geo["lng"] + (random.random() - 0.5) * 0.05

    distancia_km = round(
        haversine(ORIGEN["lat"], ORIGEN["lng"], dest_lat, dest_lng) * 10
    ) / 10

    tiempo_base = round((distancia_km / 25) * 60)
    tiempo_min  = tiempo_base + 20 + random.randint(0, 15)

    eta_texto = (
        f"{tiempo_min} minutos"
        if tiempo_min < 60
        else f"{tiempo_min // 60}h {tiempo_min % 60}min"
    )

    tracking_id = f"TRK-{uuid.uuid4().hex[:8].upper()}"

    result = {
        "origen":             ORIGEN["nombre"],
        "destino":            direccion_destino,
        "destino_lat":        round(dest_lat, 6),
        "destino_lng":        round(dest_lng, 6),
        "distanciaKm":        distancia_km,
        "tiempoEstimadoMin":  tiempo_min,
        "tiempoEstimadoTexto": eta_texto,
        "tracking_id":        tracking_id,
        "vehiculo":           "Moto de Delivery Helena",
        "calculado_en":       datetime.now().isoformat(),
    }
    logger.info(f"[Tool] Ruta: {distancia_km}km, ETA: {eta_texto}")
    return result


@tool
def actualizar_pedido_produccion(pedido_id: str) -> dict[str, Any]:
    """Actualiza el estado del pedido a 'Pagado - En Preparación'."""
    logger.info(f"[Tool] actualizar_pedido_produccion: {pedido_id}")
    if pedido_id in PEDIDOS_DB:
        PEDIDOS_DB[pedido_id]["status"] = "Pagado - En Preparación"
        PEDIDOS_DB[pedido_id]["fecha_actualizacion"] = datetime.now().isoformat()
        return {"pedido_id": pedido_id, "status": "Pagado - En Preparación", "success": True}
    return {"error": f"Pedido {pedido_id} no encontrado"}


@tool
def actualizar_pedido_entrega(pedido_id: str, ruta_info: str) -> dict[str, Any]:
    """Actualiza el pedido con la ruta de entrega y lo pone 'En Camino'."""
    import json
    logger.info(f"[Tool] actualizar_pedido_entrega: {pedido_id}")
    if pedido_id in PEDIDOS_DB:
        try:
            ruta = json.loads(ruta_info) if isinstance(ruta_info, str) else ruta_info
        except Exception:
            ruta = {"info": ruta_info}
        PEDIDOS_DB[pedido_id]["status"] = "En Camino"
        PEDIDOS_DB[pedido_id]["ruta_entrega"] = ruta
        PEDIDOS_DB[pedido_id]["fecha_actualizacion"] = datetime.now().isoformat()
        return {"pedido_id": pedido_id, "status": "En Camino", "success": True}
    return {"error": f"Pedido {pedido_id} no encontrado"}


@tool
def cancelar_pedido(pedido_id: str, motivo: str = "Pago rechazado") -> dict[str, Any]:
    """Cancela un pedido y restaura el stock."""
    logger.info(f"[Tool] cancelar_pedido: {pedido_id} | {motivo}")
    if pedido_id not in PEDIDOS_DB:
        return {"error": f"Pedido {pedido_id} no encontrado"}

    pedido = PEDIDOS_DB[pedido_id]
    pedido["status"] = "Cancelado - Pago Rechazado"
    pedido["fecha_actualizacion"] = datetime.now().isoformat()

    # Restaurar stock
    for item in pedido.get("items", []):
        pid = item.get("product_id") or item.get("type", "")
        qty = item.get("quantity", 1)
        if pid in STOCK_DB:
            STOCK_DB[pid]["cantidad"] += qty
            STOCK_DB[pid]["disponible"] = True

    return {"pedido_id": pedido_id, "status": "Cancelado", "success": True}


@tool
def obtener_todos_pedidos() -> list[dict]:
    """Retorna todos los pedidos (para el agente admin)."""
    return list(PEDIDOS_DB.values())


@tool
def obtener_stock_actual() -> dict[str, Any]:
    """Retorna el stock actual de todos los productos (para el agente admin)."""
    return {
        pid: {
            "disponible": data["disponible"],
            "cantidad":   data["cantidad"],
            "precio":     data["precio"],
        }
        for pid, data in STOCK_DB.items()
    }


# ── Conjuntos de tools por agente ─────────────────────────────────────────────

COMPRADOR_TOOLS = [
    verificar_stock,
    insertar_pedido,
    procesar_pago,
    calcular_ruta_entrega,
    actualizar_pedido_produccion,
    actualizar_pedido_entrega,
    cancelar_pedido,
]

ADMIN_TOOLS = [
    obtener_todos_pedidos,
    obtener_stock_actual,
    verificar_stock,
]

ALL_TOOLS = COMPRADOR_TOOLS + ADMIN_TOOLS
