/* ── Agente 1: Atención Web & Triage (con Gemini API) ───────── */

class FrontAgent {
  constructor(orchestrator) {
    this.name = 'Agente de Atención Web';
    this.icon = '👋';
    this.orchestrator = orchestrator;
    this.conversationHistory = [];
  }

  log(msg, type = 'info') {
    SessionState.addToLog(this.name, msg, type, this.icon);
  }

  async activate(context = {}) {
    SessionState.setAgent(this.name);
    this.log(`Activado. Contexto: ${context.reason || 'inicio de sesión'}`, 'info');
    if (context.reason === 'pago_rechazado') return this._handlePaymentRejection(context);
    if (context.reason === 'orden_incompleta') return this._handleIncompleteOrder(context);
    return { agent: this.name, action: 'greet', message: this._getWelcomeMessage() };
  }

  _getWelcomeMessage() {
    const h = new Date().getHours();
    const g = h < 12 ? 'Buenos días' : h < 18 ? 'Buenas tardes' : 'Buenas noches';
    return `${g} ✨ Bienvenido/a a **Chocolates Helena**. Soy tu asistente personal impulsado por IA 🤖🍫. ¿En qué puedo deleitarte hoy? Puedo ayudarte con el catálogo, resolver dudas o acompañarte en tu compra.`;
  }

  _handlePaymentRejection(context) {
    this.log('Recibiendo handoff de rechazo de pago', 'warning');
    return {
      agent: this.name, action: 'payment_rejected',
      message: `😔 Lamentamos informarte que tu pago no pudo procesarse.\n\n**Motivo:** ${context.motivo || 'El banco no autorizó la transacción'}\n\nPuedes intentar con otra tarjeta. ¿Deseas reintentar? 🙏`,
      showRetry: true
    };
  }

  _handleIncompleteOrder(context) {
    this.log(`Orden incompleta. Faltan: ${context.missingFields?.join(', ')}`, 'warning');
    const labels = { name: 'tu nombre', email: 'tu correo', phone: 'tu teléfono', address: 'la dirección de entrega', items: 'productos en el carrito' };
    const missing = (context.missingFields || []).map(f => labels[f] || f).join(', ');
    return { agent: this.name, action: 'request_missing_fields', message: `Para completar tu pedido necesito: **${missing}**. ¿Puedes completarlo? 😊`, missingFields: context.missingFields };
  }

  // ── Chat principal (usa Backend Python si está configurado, si no Gemini / fallback) ──
  async chat(userMessage) {
    this.conversationHistory.push({ role: 'user', content: userMessage });

    let response;
    const usePythonBackend = !!(window.HELENA_CONFIG?.PYTHON_BACKEND_URL);

    if (usePythonBackend) {
      try {
        let userType = 'visitante';
        if (window.AdminAuth && typeof window.AdminAuth.isAuthenticated === 'function' && window.AdminAuth.isAuthenticated()) {
          userType = 'admin';
        } else if (SessionState.cart && SessionState.cart.length > 0) {
          userType = 'comprador';
        }
        
        this.log(`Enviando mensaje a Backend Python (LangGraph) con perfil: ${userType}`, 'info');
        const res = await GeminiAPI.callPythonAgent(userMessage, SessionState.cart, userType);
        
        if (res.node_path && res.node_path.length > 0) {
          this.log(`[LangGraph Path] ${res.node_path.join(' ➔ ')}`, 'handoff');
        }
        if (res.rag_used && res.sources && res.sources.length > 0) {
          this.log(`📖 RAG activado. Fuentes: ${res.sources.join(', ')}`, 'success');
        }
        
        response = res.message;
      } catch (err) {
        this.log(`Error en Backend Python: ${err.message} — usando fallback local`, 'warning');
        if (GeminiAPI.hasKey()) {
          response = await this._chatWithGemini(userMessage);
        } else {
          response = this._chatFallback(userMessage);
        }
      }
    } else {
      if (GeminiAPI.hasKey()) {
        response = await this._chatWithGemini(userMessage);
      } else {
        response = this._chatFallback(userMessage);
      }
    }

    this.conversationHistory.push({ role: 'agent', content: response });
    // Mantener historial acotado
    if (this.conversationHistory.length > 20) {
      this.conversationHistory = this.conversationHistory.slice(-16);
    }
    return response;
  }

  async _chatWithGemini(userMessage) {
    this.log(`Enviando mensaje a Gemini API: "${userMessage.substring(0,40)}..."`, 'info');
    try {
      const response = await GeminiAPI.generate(
        userMessage,
        GeminiAPI.PROMPTS.frontAgent,
        this.conversationHistory.slice(-10)
      );
      this.log(`Gemini respondió (${response.length} chars)`, 'success');
      return response;
    } catch (err) {
      this.log(`Error Gemini: ${err.message} — usando respuesta de respaldo`, 'warning');
      return this._chatFallback(userMessage) + '\n\n_⚠️ (Modo sin conexión a Gemini)_';
    }
  }

  _chatFallback(userMessage) {
    const lower = userMessage.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    if (/\b(hola|buen|salud|hey)\b/.test(lower)) return `¡Hola! 🍫 Es un placer atenderte. Tenemos una colección exclusiva de chocolates artesanales. ¿Te gustaría explorar nuestro catálogo?`;
    if (/\b(catalog|producto|chocolate|ver|mostrar|que (tienen|hay)|variedad)\b/.test(lower)) return `¡Claro! Contamos con **6 variedades premium**:\n• Trufa Negra Intenso — $45.000\n• Bombón de Maracuyá — $38.000\n• Tableta de Leche — $32.000\n• Chocolate Blanco con Rosa — $42.000\n• Caja de Regalo Especial — $120.000\n• Chocolate Negro Picante — $36.000\n\n¿Cuál te llama la atención?`;
    if (/\b(precio|cuanto|vale|cuesta)\b/.test(lower)) return `Nuestros precios van desde **$32.000** hasta **$120.000 COP**. Todos incluyen envío gratis. 🎁`;
    if (/\b(pedido|orden|listo|comprar|checkout|pagar|proceder)\b/.test(lower)) return `¡Perfecto! Agrega tus productos al carrito y haz clic en **"Proceder al Checkout"**. 🛒`;
    if (/\b(ayuda|help|duda|pregunt)\b/.test(lower)) return `Puedo ayudarte a:\n• 🛍️ **Ver el catálogo** de chocolates\n• 🛒 **Agregar productos** al carrito\n• 💳 **Proceder al checkout**\n\n¿Qué necesitas?`;
    if (/\b(entrega|envio|domicilio|ciudad)\b/.test(lower)) return `Entregamos en toda Colombia 🇨🇴. El tiempo estimado se calcula automáticamente según tu dirección al hacer el pedido.`;
    return `Estoy aquí para ayudarte con nuestros chocolates premium 🍫. ¿Tienes alguna pregunta específica sobre el catálogo o el proceso de compra?`;
  }

  // ── Extracción de datos del formulario ──────────────────
  extractOrderDataFromForm(formData) {
    this.log('Extrayendo datos del formulario de checkout...', 'info');
    const missing = [];
    if (!formData.name?.trim()) missing.push('name');
    if (!formData.email?.trim() || !formData.email.includes('@')) missing.push('email');
    if (!formData.phone?.trim()) missing.push('phone');
    if (!formData.address?.trim() || formData.address.trim().length < 8) missing.push('address');
    if (!SessionState.cart || SessionState.cart.length === 0) missing.push('items');

    if (missing.length > 0) {
      this.log(`Datos incompletos. Faltan: ${missing.join(', ')}`, 'warning');
      return { success: false, missingFields: missing };
    }

    SessionState.customer.id = 'CLI-' + Date.now().toString(36).toUpperCase();
    SessionState.customer.name = formData.name.trim();
    SessionState.customer.email = formData.email.trim().toLowerCase();
    SessionState.customer.phone = formData.phone.trim();
    SessionState.customer.address = formData.address.trim();
    SessionState.buildOrderFromCart();

    this.log(`Capturado: ${formData.name} | ${formData.email} | ${SessionState.cart.length} items | $${SessionState.currentOrder.total.toLocaleString('es-CO')} COP`, 'success');
    return { success: true, customer: SessionState.customer, order: SessionState.currentOrder };
  }

  handoffToOrderAgent() {
    this.log('🔀 HANDOFF → Agente Analizador de Pedidos', 'handoff');
    return 'orderAgent';
  }
}

window.FrontAgent = FrontAgent;
