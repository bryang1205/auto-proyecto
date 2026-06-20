/* ── State Management — Chocolates Helena (con persistencia) ── */

const SessionState = {
  currentAgent: null,
  flowActive: false,

  customer: { id: null, name: null, email: null, phone: null, address: null },
  currentOrder: {
    items: [], total: 0, pedidoId: null, status: null,
    paymentToken: null, paymentCode: null, paymentApproved: null, deliveryInfo: null
  },
  cart: [],
  swarmLog: [],
  mcpCalls: [],

  // ── Persistencia localStorage ─────────────────────────────
  _storageKey: 'helena_session',

  saveToStorage() {
    try {
      localStorage.setItem('helena_cart', JSON.stringify(this.cart));
      localStorage.setItem('helena_customer', JSON.stringify(this.customer));
      localStorage.setItem('helena_mcp_calls', JSON.stringify(this.mcpCalls.slice(-200)));
      localStorage.setItem('helena_swarm_log', JSON.stringify(this.swarmLog.slice(-300)));
      if (this.currentOrder.pedidoId) {
        localStorage.setItem('helena_current_order', JSON.stringify(this.currentOrder));
      }
    } catch (e) { console.warn('SessionState.saveToStorage error:', e); }
  },

  loadFromStorage() {
    try {
      const cart = JSON.parse(localStorage.getItem('helena_cart') || '[]');
      const customer = JSON.parse(localStorage.getItem('helena_customer') || '{}');
      const mcpCalls = JSON.parse(localStorage.getItem('helena_mcp_calls') || '[]');
      const swarmLog = JSON.parse(localStorage.getItem('helena_swarm_log') || '[]');
      const order = JSON.parse(localStorage.getItem('helena_current_order') || 'null');
      this.cart = Array.isArray(cart) ? cart : [];
      if (customer && typeof customer === 'object') {
        this.customer = { ...this.customer, ...customer };
      }
      this.mcpCalls = Array.isArray(mcpCalls) ? mcpCalls : [];
      this.swarmLog = Array.isArray(swarmLog) ? swarmLog : [];
      if (order) this.currentOrder = { ...this.currentOrder, ...order };
    } catch (e) { console.warn('SessionState.loadFromStorage error:', e); }
  },

  clearStorage() {
    ['helena_cart','helena_customer','helena_mcp_calls','helena_swarm_log','helena_current_order',
     'helena_db_pedidos','helena_db_stock','helena_emails'].forEach(k => localStorage.removeItem(k));
    this.cart = [];
    this.customer = { id: null, name: null, email: null, phone: null, address: null };
    this.mcpCalls = [];
    this.swarmLog = [];
    this.currentOrder = { items: [], total: 0, pedidoId: null, status: null, paymentToken: null, paymentCode: null, paymentApproved: null, deliveryInfo: null };
    this.emit('cart:update', { cart: [] });
  },

  // ── Métodos ──────────────────────────────────────────────
  setAgent(agentName) {
    this.currentAgent = agentName;
    this.emit('agent:change', { agent: agentName });
  },

  addToLog(agentName, message, type = 'info', icon = '🤖') {
    const entry = {
      id: Date.now() + Math.random(),
      timestamp: new Date().toLocaleTimeString('es-CO', { hour12: false }),
      agent: agentName, message, type, icon
    };
    this.swarmLog.push(entry);
    this.emit('log:new', entry);
    this.saveToStorage();
    return entry;
  },

  addMCPCall(server, tool, params, result, status = 'success') {
    const call = {
      id: Date.now() + Math.random(),
      timestamp: new Date().toLocaleTimeString('es-CO', { hour12: false }),
      server, tool,
      params: JSON.stringify(params),
      result: JSON.stringify(result),
      status
    };
    this.mcpCalls.push(call);
    this.emit('mcp:call', call);
    this.saveToStorage();
    return call;
  },

  addCartItem(product, quantity = 1) {
    const existing = this.cart.find(i => i.productId === product.id);
    if (existing) {
      existing.quantity += quantity;
      existing.subtotal = existing.quantity * existing.unitPrice;
    } else {
      this.cart.push({
        productId: product.id, name: product.name, type: product.type,
        quantity, unitPrice: product.price, subtotal: product.price * quantity, image: product.image
      });
    }
    this.saveToStorage();
    this.emit('cart:update', { cart: this.cart });
  },

  removeCartItem(productId) {
    this.cart = this.cart.filter(i => i.productId !== productId);
    this.saveToStorage();
    this.emit('cart:update', { cart: this.cart });
  },

  updateCartQuantity(productId, quantity) {
    const item = this.cart.find(i => i.productId === productId);
    if (item) {
      if (quantity <= 0) { this.removeCartItem(productId); return; }
      item.quantity = quantity;
      item.subtotal = item.quantity * item.unitPrice;
    }
    this.saveToStorage();
    this.emit('cart:update', { cart: this.cart });
  },

  getCartTotal() {
    return this.cart.reduce((sum, i) => sum + i.subtotal, 0);
  },

  buildOrderFromCart() {
    this.currentOrder.items = [...this.cart];
    this.currentOrder.total = this.getCartTotal();
  },

  reset() {
    this.currentAgent = null;
    this.flowActive = false;
    this.customer = { id: null, name: null, email: null, phone: null, address: null };
    this.currentOrder = { items: [], total: 0, pedidoId: null, status: null, paymentToken: null, paymentCode: null, paymentApproved: null, deliveryInfo: null };
    localStorage.removeItem('helena_current_order');
  },

  // ── Event Bus ────────────────────────────────────────────
  _listeners: {},
  on(event, callback) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(callback);
  },
  off(event, callback) {
    if (this._listeners[event])
      this._listeners[event] = this._listeners[event].filter(cb => cb !== callback);
  },
  emit(event, data) {
    if (this._listeners[event]) this._listeners[event].forEach(cb => cb(data));
  }
};

// Cargar estado guardado al iniciar
SessionState.loadFromStorage();
window.SessionState = SessionState;
