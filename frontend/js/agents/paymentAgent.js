/* ── Agente 3: Validación de Pagos ──────────────────────────── */

class PaymentAgent {
  constructor(orchestrator) {
    this.name = 'Agente de Validación de Pagos';
    this.icon = '💳';
    this.orchestrator = orchestrator;
  }

  log(msg, type = 'info') {
    SessionState.addToLog(this.name, msg, type, this.icon);
  }

  async activate(paymentData) {
    SessionState.setAgent(this.name);
    this.log('Activado. Procesando transacción en la pasarela de pagos...', 'info');

    // Validar datos de pago
    if (!paymentData || !paymentData.cardNumber) {
      this.log('Datos de pago incompletos', 'error');
      return { success: false, error: 'Datos de pago incompletos' };
    }

    // Llamar al MCP de Pagos
    let paymentResult;
    try {
      this.log(`Enviando token de pago a payment_mcp_server... Monto: $${SessionState.currentOrder.total.toLocaleString('es-CO')} COP`, 'info');
      paymentResult = await PaymentMCP.procesar_pago(
        paymentData.cardNumber,
        paymentData.cardHolder,
        paymentData.expiry,
        paymentData.cvv,
        SessionState.currentOrder.total
      );
    } catch (err) {
      this.log(`Error crítico en pasarela de pago: ${err.message}`, 'error');
      return { success: false, error: `Error MCP pago: ${err.message}` };
    }

    SessionState.currentOrder.paymentToken = paymentResult.token;
    SessionState.currentOrder.paymentApproved = paymentResult.aprobado;

    if (!paymentResult.aprobado) {
      return await this._handleRejectedPayment(paymentResult);
    }

    return await this._handleApprovedPayment(paymentResult);
  }

  async _handleRejectedPayment(paymentResult) {
    this.log(`❌ PAGO RECHAZADO — Código: ${paymentResult.codigo_rechazo} | Motivo: ${paymentResult.mensaje}`, 'error');

    // 1. Cancelar pedido en BD
    try {
      this.log(`Cancelando pedido ${SessionState.currentOrder.pedidoId} en la BD...`, 'info');
      await PostgresMCP.eliminar_o_cancelar_pedido(SessionState.currentOrder.pedidoId);
      SessionState.currentOrder.status = 'Cancelado - Pago Rechazado';
      this.log('Pedido cancelado y stock reintegrado correctamente', 'success');
    } catch (err) {
      this.log(`Error al cancelar pedido en BD: ${err.message}`, 'error');
    }

    // 2. Enviar email de rechazo
    try {
      this.log(`Enviando notificación de rechazo a ${SessionState.customer.email}...`, 'info');
      await EmailMCP.enviar_correo_rechazo(
        SessionState.customer.email,
        SessionState.currentOrder.pedidoId,
        paymentResult.mensaje,
        SessionState.customer.name
      );
    } catch (err) {
      this.log(`Error al enviar email de rechazo: ${err.message}`, 'error');
    }

    // 3. Handoff al Front Agent
    this.log('🔀 HANDOFF → Agente de Atención Web (notificar rechazo al usuario)', 'handoff');

    return {
      success: false,
      paymentApproved: false,
      handoff: 'frontAgent',
      reason: 'pago_rechazado',
      motivo: paymentResult.mensaje,
      codigoRechazo: paymentResult.codigo_rechazo,
      token: paymentResult.token
    };
  }

  async _handleApprovedPayment(paymentResult) {
    this.log(`✅ PAGO APROBADO — Código de autorización: ${paymentResult.codigo_autorizacion} | Token: ${paymentResult.token.substring(0,20)}...`, 'success');
    this.log('🔀 HANDOFF → Agente de Operaciones y Logística', 'handoff');

    return {
      success: true,
      paymentApproved: true,
      handoff: 'logisticsAgent',
      codigoAutorizacion: paymentResult.codigo_autorizacion,
      token: paymentResult.token,
      mensaje: paymentResult.mensaje
    };
  }
}

window.PaymentAgent = PaymentAgent;
