/* ═══════════════════════════════════════════════════════════════
   GeminiAPI — Módulo central de integración
   ─ Conecta el frontend con el Backend Python (FastAPI + LangGraph)
   ─ Fallback directo a Gemini API si el backend no está disponible
   ═══════════════════════════════════════════════════════════════ */

const GeminiAPI = {

  // ── Prompts del sistema ─────────────────────────────────────
  PROMPTS: {
    frontAgent: `Eres el asistente premium de "Chocolates Helena", chocolatería artesanal peruana.
Tu personalidad: cálida, elegante, apasionada por el chocolate. Siempre en español latinoamericano.
Catálogo disponible:
• Trufa Negra Intenso — S/ 45.00 (70% cacao, oro comestible)
• Bombón de Maracuyá — S/ 38.00 (relleno tropical fresco)
• Tableta de Leche Premium — S/ 32.00 (caramelo salado artesanal)
• Chocolate Blanco con Rosa — S/ 42.00 (pétalos de rosa + frambuesa)
• Caja de Regalo Especial — S/ 120.00 (20 piezas seleccionadas)
• Chocolate Negro Picante — S/ 36.00 (75% cacao + ají peruano)
Envíos gratuitos a todo el Perú. Pago con tarjeta en checkout seguro.
Máximo 3-4 oraciones. Usa ocasionalmente emojis de chocolate 🍫.
Si el cliente quiere comprar, indícale que agregue al carrito y proceda al checkout.`
  },

  // ── Helpers ─────────────────────────────────────────────────
  _getBackendUrl() {
    return window.HELENA_CONFIG?.PYTHON_BACKEND_URL || '';
  },

  _getGeminiKey() {
    return window.HELENA_CONFIG?.GEMINI_API_KEY || '';
  },

  _getGeminiModel() {
    return window.HELENA_CONFIG?.GEMINI_MODEL || 'gemini-2.0-flash-lite';
  },

  hasKey() {
    const key = this._getGeminiKey();
    return !!(key && key.length > 10 && !key.includes('TU_'));
  },

  _getSessionId() {
    let sid = sessionStorage.getItem('helena_session_id');
    if (!sid) {
      sid = 'sess_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 6);
      sessionStorage.setItem('helena_session_id', sid);
    }
    return sid;
  },

  _log(msg, type = 'info') {
    try {
      if (typeof SessionState !== 'undefined') {
        SessionState.addToLog('GeminiAPI', msg, type, '🔗');
      }
    } catch (e) { /* silencioso */ }
  },

  // ── Llamada directa a Gemini API ─────────────────────────────
  async generate(userMessage, systemPrompt = '', conversationHistory = []) {
    const key   = this._getGeminiKey();
    const model = this._getGeminiModel();

    if (!key || key.includes('TU_')) {
      throw new Error('GEMINI_API_KEY no configurada');
    }

    // Construir el contenido del mensaje con historial
    const contents = [];

    // Añadir historial de conversación
    for (const h of conversationHistory.slice(-10)) {
      if (h.role === 'user' || h.content) {
        contents.push({
          role: h.role === 'agent' ? 'model' : 'user',
          parts: [{ text: h.content }]
        });
      }
    }

    // Añadir el mensaje actual
    contents.push({
      role: 'user',
      parts: [{ text: userMessage }]
    });

    const requestBody = {
      contents,
      systemInstruction: systemPrompt
        ? { parts: [{ text: systemPrompt }] }
        : undefined,
      generationConfig: {
        temperature: 0.7,
        maxOutputTokens: 512,
        topP: 0.9,
      }
    };

    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`;

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err?.error?.message || `Gemini API error ${response.status}`);
    }

    const data = await response.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!text) throw new Error('Respuesta vacía de Gemini');
    return text;
  },

  // ── Llamada al Backend Python — Chat ─────────────────────────
  async callPythonAgent(userMessage, cart = [], userType = 'visitante') {
    const baseUrl = this._getBackendUrl();
    if (!baseUrl) throw new Error('PYTHON_BACKEND_URL no configurado');

    // Convertir carrito al formato que espera el backend
    const cartItems = (cart || []).map(item => ({
      product_id: item.productId || item.type || '',
      name:       item.name || '',
      type:       item.type || item.productId || '',
      quantity:   item.quantity || 1,
      price:      item.unitPrice || item.price || 0,
    }));

    const payload = {
      message:    userMessage,
      session_id: this._getSessionId(),
      user_type:  userType,
      cart:       cartItems,
    };

    this._log(`POST ${baseUrl}/api/agent/chat | perfil=${userType} | "${userMessage.substr(0, 40)}..."`, 'info');

    const response = await fetch(`${baseUrl}/api/agent/chat`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
      signal:  AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      const errBody = await response.json().catch(() => ({}));
      throw new Error(errBody?.detail || `Backend error ${response.status}`);
    }

    const data = await response.json();
    this._log(
      `Respuesta: perfil=${data.profile} | RAG=${data.rag_used} | path=[${(data.node_path || []).join('→')}]`,
      'success'
    );
    return data;
  },

  // ── Llamada al Backend Python — Checkout ──────────────────────
  async callPythonCheckout(formData, paymentData, cart = []) {
    const baseUrl = this._getBackendUrl();
    if (!baseUrl) throw new Error('PYTHON_BACKEND_URL no configurado');

    // Mapear campos del formulario al esquema del backend
    const cartItems = (cart || []).map(item => ({
      product_id: item.productId || item.type || '',
      name:       item.name || '',
      type:       item.type || item.productId || '',
      quantity:   item.quantity || 1,
      price:      item.unitPrice || item.price || 0,
    }));

    // Normalizar número de tarjeta (quitar espacios)
    const cardNumber = (paymentData.cardNumber || '').replace(/\s/g, '');

    const payload = {
      session_id: this._getSessionId(),
      customer: {
        nombre:    formData.name    || '',
        email:     formData.email   || '',
        telefono:  formData.phone   || '',
        direccion: formData.address || '',
      },
      payment: {
        card_number: cardNumber,
        card_holder: paymentData.cardHolder || paymentData.card_holder || '',
        expiry:      paymentData.expiry     || '',
        cvv:         paymentData.cvv        || '',
      },
      cart: cartItems,
    };

    this._log(
      `POST ${baseUrl}/api/agent/checkout | cliente=${formData.name} | items=${cartItems.length}`,
      'info'
    );

    const response = await fetch(`${baseUrl}/api/agent/checkout`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
      signal:  AbortSignal.timeout(60000), // Checkout puede tomar más tiempo
    });

    if (!response.ok) {
      const errBody = await response.json().catch(() => ({}));
      throw new Error(errBody?.detail || `Backend checkout error ${response.status}`);
    }

    const data = await response.json();
    this._log(
      `Checkout: success=${data.success} | stage=${data.stage} | order_id=${data.order_id || 'N/A'}`,
      data.success ? 'success' : 'error'
    );
    return data;
  },

  // ── Verificar estado del backend Python ───────────────────────
  async checkBackendHealth() {
    const baseUrl = this._getBackendUrl();
    if (!baseUrl) return null;

    try {
      const response = await fetch(`${baseUrl}/api/agent/health`, {
        signal: AbortSignal.timeout(5000),
      });
      if (!response.ok) return null;
      return await response.json();
    } catch {
      return null;
    }
  },
};

window.GeminiAPI = GeminiAPI;
