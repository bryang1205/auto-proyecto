/* ── Agente 4: Operaciones y Logística ──────────────────────── */

class LogisticsAgent {
  constructor(orchestrator) {
    this.name = 'Agente de Operaciones y Logística';
    this.icon = '🚚';
    this.orchestrator = orchestrator;
  }

  log(msg, type = 'info') {
    SessionState.addToLog(this.name, msg, type, this.icon);
  }

  async activate() {
    SessionState.setAgent(this.name);
    this.log('Activado. Iniciando secuencia de despacho obligatoria...', 'info');

    // PASO 1: Actualizar estado de producción
    let produccionResult;
    try {
      this.log('PASO 1/3 — Actualizando estado a "Pagado - En Preparación"...', 'info');
      produccionResult = await PostgresMCP.actualizar_pedido_produccion(SessionState.currentOrder.pedidoId);
      SessionState.currentOrder.status = 'Pagado - En Preparación';
      this.log(`✅ Estado actualizado: ${produccionResult.status}`, 'success');
    } catch (err) {
      this.log(`❌ Error en PASO 1 (producción): ${err.message}`, 'error');
      return { success: false, error: `Error actualizar producción: ${err.message}`, step: 1 };
    }

    // PASO 2: Calcular ruta de entrega vía Mapas
    let rutaResult;
    try {
      this.log(`PASO 2/3 — Calculando ruta hacia: "${SessionState.customer.address}"...`, 'info');
      rutaResult = await MapsMCP.calcular_ruta_entrega(SessionState.customer.address);
      SessionState.currentOrder.deliveryInfo = rutaResult;
      this.log(`✅ Ruta calculada: ${rutaResult.distanciaKm}km | ETA: ${rutaResult.tiempoEstimadoTexto} | Tracking: ${rutaResult.tracking_id}`, 'success');
    } catch (err) {
      this.log(`❌ Error en PASO 2 (mapas): ${err.message}`, 'error');
      return { success: false, error: `Error calcular ruta: ${err.message}`, step: 2 };
    }

    // PASO 3: Guardar ruta en BD
    try {
      this.log('PASO 3/3 — Guardando ruta optimizada en la base de datos...', 'info');
      await PostgresMCP.actualizar_pedido_entrega(SessionState.currentOrder.pedidoId, rutaResult);
      SessionState.currentOrder.status = 'En Camino';
      this.log('✅ Ruta asignada al delivery y guardada en BD', 'success');
    } catch (err) {
      this.log(`❌ Error en PASO 3 (guardar ruta): ${err.message}`, 'error');
      return { success: false, error: `Error guardar ruta: ${err.message}`, step: 3 };
    }

    // Enviar email de confirmación (no crítico)
    try {
      await EmailMCP.enviar_correo_confirmacion(
        SessionState.customer.email,
        SessionState.currentOrder.pedidoId,
        SessionState.customer.name,
        rutaResult
      );
    } catch (err) {
      this.log(`Advertencia: No se pudo enviar email de confirmación: ${err.message}`, 'warning');
    }

    // Generar respuesta final estructurada
    const finalResponse = this._buildFinalResponse(rutaResult);
    this.log('🎉 FLUJO COMPLETADO — Generando respuesta final para el frontend', 'success');

    return {
      success: true,
      handoff: null,
      finalResponse
    };
  }

  _buildFinalResponse(rutaResult) {
    const order = SessionState.currentOrder;
    const customer = SessionState.customer;

    return {
      status: 'SUCCESS',
      pedido: {
        id: order.pedidoId,
        status: 'En Camino',
        items: order.items,
        total: order.total,
        totalFormateado: `$${order.total.toLocaleString('es-CO')} COP`
      },
      cliente: {
        nombre: customer.name,
        email: customer.email,
        direccion: customer.address
      },
      pago: {
        aprobado: true,
        token: order.paymentToken
      },
      entrega: {
        trackingId: rutaResult.tracking_id,
        origen: rutaResult.origen.nombre,
        destino: {
          direccion: rutaResult.destino.direccion,
          ciudad: rutaResult.destino.ciudad,
          lat: rutaResult.destino.lat,
          lng: rutaResult.destino.lng
        },
        distanciaKm: rutaResult.distanciaKm,
        tiempoEstimadoMin: rutaResult.tiempoEstimadoMin,
        tiempoEstimadoTexto: rutaResult.tiempoEstimadoTexto,
        vehiculo: rutaResult.vehiculo,
        rutaPuntos: rutaResult.rutaPuntos
      },
      mensajeFrontend: `🍫 ¡Tu pedido **${order.pedidoId}** está en camino! Tiempo estimado: **${rutaResult.tiempoEstimadoTexto}**. Tracking: ${rutaResult.tracking_id}`,
      generadoEn: new Date().toISOString()
    };
  }
}

window.LogisticsAgent = LogisticsAgent;
