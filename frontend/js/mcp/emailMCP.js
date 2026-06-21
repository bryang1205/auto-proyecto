/* ═══════════════════════════════════════════════════════════════
   email_mcp_server — Simulado
   ─ Simula el envío de correos transaccionales
   ─ En producción, conectaría a SendGrid / AWS SES / Resend
   ═══════════════════════════════════════════════════════════════ */

const EmailMCP = {
  SERVER_NAME: 'email_mcp_server',

  // ── Registro de emails enviados (para auditoría en sesión) ────
  _emailLog: [],

  // ── Helpers ───────────────────────────────────────────────────
  _delay(ms) { return new Promise(r => setTimeout(r, ms)); },

  _log(tool, params, result, status = 'success') {
    try {
      if (typeof SessionState !== 'undefined' && SessionState.addMCPCall) {
        SessionState.addMCPCall(this.SERVER_NAME, tool, params, result, status);
        const icon = status === 'success' ? '✅' : '⚠️';
        SessionState.addToLog(
          'Sistema MCP',
          `${this.SERVER_NAME}::${tool} → ${icon} Email enviado a ${params.email || '?'}`,
          'mcp',
          '📧'
        );
      }
    } catch (e) { console.warn('EmailMCP._log error:', e); }
  },

  _generateMessageId() {
    return 'msg_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 6);
  },

  // ── Herramienta 1: Email de Confirmación ──────────────────────
  async enviar_correo_confirmacion(email, pedidoId, nombreCliente, rutaResult) {
    await this._delay(500 + Math.random() * 400);

    const eta     = rutaResult?.tiempoEstimadoTexto || '30-45 minutos';
    const distKm  = rutaResult?.distanciaKm         || '?';
    const tracking = rutaResult?.tracking_id        || 'N/A';

    const emailData = {
      to:       email,
      subject:  `🍫 ¡Tu pedido ${pedidoId} está en camino! — Chocolates Helena`,
      template: 'order_confirmation',
      body: [
        `Hola ${nombreCliente || 'estimado cliente'},`,
        ``,
        `¡Tu pedido de Chocolates Helena ha sido confirmado y está en camino!`,
        ``,
        `📦 Pedido: ${pedidoId}`,
        `📡 Tracking: ${tracking}`,
        `📏 Distancia: ${distKm} km`,
        `⏱️  Tiempo estimado de entrega: ${eta}`,
        ``,
        `Gracias por elegir Chocolates Helena 🍫`,
        `Lima, Perú`,
      ].join('\n'),
    };

    const messageId = this._generateMessageId();
    const result = {
      success:    true,
      message_id: messageId,
      to:         email,
      subject:    emailData.subject,
      sent_at:    new Date().toISOString(),
      provider:   'Helena Mail Gateway',
      _msg:       `Confirmación enviada a ${email}`,
    };

    this._emailLog.push({ ...result, template: 'confirmation', pedidoId });
    this._log('enviar_correo_confirmacion', { email, pedidoId }, result, 'success');

    // En desarrollo: mostrar en consola como si fuera el email
    console.groupCollapsed(`[EmailMCP] 📧 Correo de confirmación → ${email}`);
    console.log(emailData.body);
    console.groupEnd();

    return result;
  },

  // ── Herramienta 2: Email de Rechazo de Pago ──────────────────
  async enviar_correo_rechazo(email, pedidoId, motivo, nombreCliente) {
    await this._delay(400 + Math.random() * 300);

    const emailData = {
      to:       email,
      subject:  `⚠️ Tu pago no pudo procesarse — Chocolates Helena`,
      template: 'payment_rejection',
      body: [
        `Hola ${nombreCliente || 'estimado cliente'},`,
        ``,
        `Lamentamos informarte que tu pago para el pedido ${pedidoId} no pudo procesarse.`,
        ``,
        `❌ Motivo: ${motivo || 'El banco no autorizó la transacción'}`,
        ``,
        `Puedes intentar nuevamente con otra tarjeta. Te recomendamos usar:`,
        `• Tarjeta de prueba aprobada: 4242 4242 4242 4242`,
        ``,
        `Si el problema persiste, contáctanos en soporte@chocolateshelena.pe`,
        ``,
        `Equipo Chocolates Helena 🍫`,
      ].join('\n'),
    };

    const messageId = this._generateMessageId();
    const result = {
      success:    true,
      message_id: messageId,
      to:         email,
      subject:    emailData.subject,
      sent_at:    new Date().toISOString(),
      provider:   'Helena Mail Gateway',
      _msg:       `Notificación de rechazo enviada a ${email}`,
    };

    this._emailLog.push({ ...result, template: 'rejection', pedidoId, motivo });
    this._log('enviar_correo_rechazo', { email, pedidoId, motivo }, result, 'success');

    // En desarrollo: mostrar en consola
    console.groupCollapsed(`[EmailMCP] 📧 Correo de rechazo → ${email}`);
    console.log(emailData.body);
    console.groupEnd();

    return result;
  },

  // ── Historial de emails ───────────────────────────────────────
  getEmailLog() {
    return [...this._emailLog];
  },
};

window.EmailMCP = EmailMCP;
