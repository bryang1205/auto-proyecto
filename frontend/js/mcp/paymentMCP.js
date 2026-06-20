/* ── payment_mcp_server — Simulado ──────────────────────────── */

const PaymentMCP = {
  SERVER_NAME: 'payment_mcp_server',

  // Tarjetas mágicas
  MAGIC_APPROVE: '4242424242424242',
  MAGIC_REJECT:  '4000000000000002',

  _delay(ms) { return new Promise(r => setTimeout(r, ms)); },

  _log(tool, params, result, status) {
    try {
      if (typeof SessionState !== 'undefined' && SessionState.addMCPCall) {
        SessionState.addMCPCall(this.SERVER_NAME, tool, params, result, status);
        SessionState.addToLog('Sistema MCP', `${this.SERVER_NAME}::${tool} → ${status === 'success' ? '✅' : '⚠️'} ${result.mensaje || ''}`, 'mcp', '💳');
      }
    } catch(e) { console.warn('PaymentMCP._log error:', e); }
  },

  _generateToken() {
    return 'tok_' + Math.random().toString(36).substr(2,24).toUpperCase();
  },

  _generateAuthCode() {
    return Math.floor(100000 + Math.random() * 900000).toString();
  },

  async procesar_pago(cardNumber, cardHolder, expiry, cvv, monto) {
    await this._delay(1200 + Math.random() * 800);

    // Normalizar número de tarjeta
    const normalized = (cardNumber || '').replace(/\s/g, '');
    const token = this._generateToken();

    // Lógica de aprobación
    let aprobado;
    let codigo_rechazo = null;
    let mensaje;

    if (normalized === this.MAGIC_APPROVE) {
      aprobado = true;
    } else if (normalized === this.MAGIC_REJECT) {
      aprobado = false;
      codigo_rechazo = 'FONDOS_INSUFICIENTES';
    } else {
      // 80% aprobación aleatoria para otras tarjetas
      const rand = Math.random();
      if (rand < 0.80) {
        aprobado = true;
      } else {
        aprobado = false;
        const rechazos = ['FONDOS_INSUFICIENTES', 'TARJETA_VENCIDA', 'LIMITE_EXCEDIDO', 'BANCO_NO_AUTORIZA'];
        codigo_rechazo = rechazos[Math.floor(Math.random() * rechazos.length)];
      }
    }

    const mensajesRechazo = {
      'FONDOS_INSUFICIENTES': 'Fondos insuficientes. Intente con otra tarjeta.',
      'TARJETA_VENCIDA':      'La tarjeta ha expirado. Verifique la fecha de vencimiento.',
      'LIMITE_EXCEDIDO':      'Límite de crédito excedido. Contacte su banco.',
      'BANCO_NO_AUTORIZA':    'El banco no autorizó la transacción. Intente nuevamente.'
    };

    const result = {
      token,
      aprobado,
      monto,
      moneda: 'PEN',
      codigo_autorizacion: aprobado ? this._generateAuthCode() : null,
      codigo_rechazo: aprobado ? null : codigo_rechazo,
      mensaje: aprobado
        ? `Pago aprobado por S/ ${monto.toLocaleString('es-PE')}`
        : mensajesRechazo[codigo_rechazo] || 'Pago rechazado por el banco.',
      tarjeta_ultimos4: normalized.slice(-4) || '****',
      timestamp: new Date().toISOString(),
      procesador: 'Helena Pay Gateway v2.1'
    };

    this._log('procesar_pago', { monto, tarjeta: '****' + normalized.slice(-4) }, result, aprobado ? 'success' : 'error');
    return result;
  }
};

window.PaymentMCP = PaymentMCP;
