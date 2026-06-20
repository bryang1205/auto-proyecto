/* ── SwarmOrchestrator — OS Central de Chocolates Helena ───── */

class SwarmOrchestrator {
  constructor() {
    this.frontAgent    = new FrontAgent(this);
    this.orderAgent    = new OrderAgent(this);
    this.paymentAgent  = new PaymentAgent(this);
    this.logisticsAgent = new LogisticsAgent(this);

    this.agents = {
      frontAgent:    this.frontAgent,
      orderAgent:    this.orderAgent,
      paymentAgent:  this.paymentAgent,
      logisticsAgent: this.logisticsAgent
    };

    this.flowState = 'idle'; // idle | running | completed | error
    this._log('OS Orquestador Central iniciado. Enjambre de 4 agentes listo.', 'info', '🧠');
  }

  _log(msg, type = 'info', icon = '🧠') {
    SessionState.addToLog('Orquestador Central', msg, type, icon);
  }

  /* ────────────────────────────────────────────────────────────
     FLUJO PRINCIPAL: Iniciar desde el checkout
     ──────────────────────────────────────────────────────────── */
  async startCheckoutFlow(formData, paymentData) {
    if (this.flowState === 'running') {
      this._log('ADVERTENCIA: Flujo ya en ejecución. Ignorando solicitud duplicada.', 'warning');
      return null;
    }

    this.flowState = 'running';
    SessionState.flowActive = true;
    this._log('═══════════════════════════════════════════════════════', 'info');
    this._log('INICIANDO FLUJO DE COMPRA — Enjambre Swarm activado', 'info');
    this._log('═══════════════════════════════════════════════════════', 'info');

    const usePythonBackend = !!(window.HELENA_CONFIG?.PYTHON_BACKEND_URL);

    if (usePythonBackend) {
      try {
        this._log('Iniciando procesamiento en Backend Python (LangGraph)...', 'info');

        // 1. Fase Triage (Simulación de handoff a classify)
        this._log('Transfiriendo control → Clasificador de Perfil', 'handoff');
        SessionState.emit('flow:step', { step: 1, agent: 'frontAgent', label: 'Triage' });
        await new Promise(r => setTimeout(r, 600));

        // Llamar al backend real
        const res = await GeminiAPI.callPythonCheckout(formData, paymentData, SessionState.cart);

        // Playback de los nodos recorridos
        if (res.node_path && res.node_path.length > 0) {
          for (const node of res.node_path) {
            this._log(`Procesado por nodo LangGraph: [${node}]`, 'info');
            if (node === 'order_agent') {
              SessionState.emit('agent:change', { agent: 'Agente Analizador de Pedidos' });
              SessionState.emit('flow:step', { step: 2, agent: 'orderAgent', label: 'Pedidos' });
              await new Promise(r => setTimeout(r, 800));
            } else if (node === 'payment_agent') {
              SessionState.emit('agent:change', { agent: 'Agente de Validación de Pagos' });
              SessionState.emit('flow:step', { step: 3, agent: 'paymentAgent', label: 'Pagos' });
              await new Promise(r => setTimeout(r, 800));
            } else if (node === 'logistics_agent') {
              SessionState.emit('agent:change', { agent: 'Agente de Operaciones y Logística' });
              SessionState.emit('flow:step', { step: 4, agent: 'logisticsAgent', label: 'Logística' });
              await new Promise(r => setTimeout(r, 800));
            }
          }
        }

        if (!res.success) {
          this.flowState = 'error';
          SessionState.flowActive = false;
          
          if (res.stage === 'payment') {
            this._log(`Pago rechazado por el Agente de Pagos: ${res.error}`, 'error');
            SessionState.emit('flow:payment_rejected', { motivo: res.error });
            return { success: false, stage: 'payment', error: res.error };
          } else {
            this._log(`Error en flujo de compra (${res.stage}): ${res.error || res.message}`, 'error');
            SessionState.emit('flow:error', { agent: res.stage + 'Agent', result: { error: res.error || res.message } });
            return { success: false, stage: res.stage, error: res.error || res.message };
          }
        }

        // Flujo completado con éxito
        this.flowState = 'completed';
        SessionState.flowActive = false;
        this._log('═══════════════════════════════════════════════════════', 'success');
        this._log('✅ FLUJO COMPLETADO — Pedido procesado por LangGraph en Python', 'success');
        this._log('═══════════════════════════════════════════════════════', 'success');

        const finalResponse = {
          status: 'SUCCESS',
          pedido: {
            id: res.order_id,
            status: 'En Camino',
            items: SessionState.cart.map(item => ({
              name: item.name,
              quantity: item.quantity,
              subtotal: item.subtotal
            })),
            total: SessionState.getCartTotal(),
            totalFormateado: `$${SessionState.getCartTotal().toLocaleString('es-CO')} COP`
          },
          cliente: {
            nombre: formData.name,
            email: formData.email,
            direccion: formData.address
          },
          pago: {
            aprobado: true,
            token: 'tok_py_' + Math.random().toString(36).substr(2, 9).toUpperCase()
          },
          entrega: {
            trackingId: res.tracking_id || 'TRK-PY-' + Math.random().toString(36).substr(2, 6).toUpperCase(),
            origen: 'Bodega Helena — Miraflores',
            destino: {
              direccion: formData.address,
              ciudad: 'Lima',
              lat: -12.1191,
              lng: -77.0299
            },
            distanciaKm: res.distancia_km || 3.5,
            tiempoEstimadoMin: 25,
            tiempoEstimadoTexto: res.eta || '25 minutos',
            vehiculo: 'Moto de Delivery Helena',
            rutaPuntos: []
          },
          mensajeFrontend: res.message,
          generadoEn: new Date().toISOString()
        };

        SessionState.emit('flow:completed', finalResponse);
        return { success: true, stage: 'completed', result: finalResponse };

      } catch (err) {
        this._log(`Error llamando a Backend Python: ${err.message} — Usando fallback local`, 'warning');
        // Continuar con fallback local
      }
    }

    try {
      // ── AGENTE 1: Atención Web & Triage ─────────────────────
      this._log('Transfiriendo control → AGENTE 1: Atención Web & Triage', 'handoff');
      SessionState.emit('flow:step', { step: 1, agent: 'frontAgent', label: 'Triage' });

      const extractResult = this.frontAgent.extractOrderDataFromForm(formData);

      if (!extractResult.success) {
        this.flowState = 'error';
        SessionState.flowActive = false;
        const handoffResult = await this.frontAgent.activate({ reason: 'orden_incompleta', missingFields: extractResult.missingFields });
        SessionState.emit('flow:error', { agent: 'frontAgent', result: handoffResult });
        return { success: false, stage: 'front', result: handoffResult };
      }

      this._log('Agente 1 completó captura. Transfiriendo → AGENTE 2', 'handoff');

      // ── AGENTE 2: Analizador de Pedidos ─────────────────────
      SessionState.emit('flow:step', { step: 2, agent: 'orderAgent', label: 'Pedidos' });
      const orderResult = await this.orderAgent.activate();

      if (!orderResult.success) {
        this.flowState = 'error';
        SessionState.flowActive = false;
        if (orderResult.handoff === 'frontAgent') {
          await this.frontAgent.activate({ reason: orderResult.reason, missingFields: orderResult.missingFields });
        }
        SessionState.emit('flow:error', { agent: 'orderAgent', result: orderResult });
        return { success: false, stage: 'order', result: orderResult };
      }

      this._log('Agente 2 completó validación. Transfiriendo → AGENTE 3', 'handoff');

      // ── AGENTE 3: Validación de Pagos ────────────────────────
      SessionState.emit('flow:step', { step: 3, agent: 'paymentAgent', label: 'Pagos' });
      const paymentResult = await this.paymentAgent.activate(paymentData);

      if (!paymentResult.success) {
        this.flowState = 'error';
        SessionState.flowActive = false;
        if (paymentResult.handoff === 'frontAgent') {
          await this.frontAgent.activate({ reason: 'pago_rechazado', motivo: paymentResult.motivo });
        }
        SessionState.emit('flow:payment_rejected', paymentResult);
        return { success: false, stage: 'payment', result: paymentResult };
      }

      this._log('Agente 3: PAGO APROBADO. Transfiriendo → AGENTE 4', 'handoff');

      // ── AGENTE 4: Operaciones y Logística ───────────────────
      SessionState.emit('flow:step', { step: 4, agent: 'logisticsAgent', label: 'Logística' });
      const logisticsResult = await this.logisticsAgent.activate();

      if (!logisticsResult.success) {
        this.flowState = 'error';
        SessionState.flowActive = false;
        this._log(`Error en logística (paso ${logisticsResult.step}): ${logisticsResult.error}`, 'error');
        SessionState.emit('flow:error', { agent: 'logisticsAgent', result: logisticsResult });
        return { success: false, stage: 'logistics', result: logisticsResult };
      }

      // ── FLUJO COMPLETADO ─────────────────────────────────────
      this.flowState = 'completed';
      SessionState.flowActive = false;
      this._log('═══════════════════════════════════════════════════════', 'success');
      this._log('✅ FLUJO COMPLETADO — Pedido procesado exitosamente por el enjambre Swarm', 'success');
      this._log('═══════════════════════════════════════════════════════', 'success');

      SessionState.emit('flow:completed', logisticsResult.finalResponse);
      return { success: true, stage: 'completed', result: logisticsResult.finalResponse };

    } catch (err) {
      this.flowState = 'error';
      SessionState.flowActive = false;
      this._log(`ERROR CRÍTICO NO MANEJADO: ${err.message}`, 'error');
      console.error('[SwarmOrchestrator] Error:', err);
      SessionState.emit('flow:critical_error', { error: err.message });
      return { success: false, stage: 'critical', error: err.message };
    }
  }

  /* ────────────────────────────────────────────────────────────
     Chat con el Agente 1 (usa Gemini si hay API key)
     ──────────────────────────────────────────────────────────── */
  async chat(userMessage) {
    // frontAgent.chat() maneja Gemini + fallback automáticamente
    return this.frontAgent.chat(userMessage);
  }

  async greetUser() {
    return (await this.frontAgent.activate({ reason: 'inicio' })).message;
  }

  reset() {
    this.flowState = 'idle';
    SessionState.reset();
    this._log('Sistema reiniciado. Listo para nuevo flujo.', 'info');
  }
}

// Singleton global
window.Orchestrator = new SwarmOrchestrator();
