/* ── UI Controller — Chocolates Helena ──────────────────────── */

const UI = {
  // ── Toast ─────────────────────────────────────────────────
  showToast(message, type = 'info', duration = 3500) {
    const container = document.getElementById('toast-container') || this._createToastContainer();
    const toast = document.createElement('div');
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.animation = 'toastIn 0.3s ease reverse forwards';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  _createToastContainer() {
    const el = document.createElement('div');
    el.id = 'toast-container';
    el.className = 'toast-container';
    document.body.appendChild(el);
    return el;
  },

  // ── Cart ──────────────────────────────────────────────────
  renderCart() {
    const cart = SessionState.cart;
    const total = SessionState.getCartTotal();

    // Counter badge
    const count = cart.reduce((s, i) => s + i.quantity, 0);
    document.querySelectorAll('.cart-count').forEach(el => {
      el.textContent = count;
      el.style.display = count > 0 ? 'flex' : 'none';
    });

    // Cart panel
    const cartItems = document.getElementById('cart-items');
    const cartTotal = document.getElementById('cart-total');
    const cartEmpty = document.getElementById('cart-empty');

    if (!cartItems) return;

    if (cart.length === 0) {
      cartItems.innerHTML = '';
      if (cartEmpty) cartEmpty.style.display = 'flex';
      if (cartTotal) cartTotal.textContent = 'S/ 0.00';
      return;
    }

    if (cartEmpty) cartEmpty.style.display = 'none';
    cartItems.innerHTML = cart.map(item => `
      <div class="cart-item" data-id="${item.productId}">
        <img src="${item.image}" alt="${item.name}" class="cart-item-img">
        <div class="cart-item-info">
          <div class="cart-item-name">${item.name}</div>
          <div class="cart-item-price">S/ ${item.unitPrice.toLocaleString('es-PE')}</div>
          <div class="cart-item-controls">
            <button class="qty-btn" onclick="Cart.updateQuantity('${item.productId}', ${item.quantity - 1})">−</button>
            <span class="qty-val">${item.quantity}</span>
            <button class="qty-btn" onclick="Cart.updateQuantity('${item.productId}', ${item.quantity + 1})">+</button>
          </div>
        </div>
        <div class="cart-item-subtotal">
          <div>S/ ${item.subtotal.toLocaleString('es-PE')}</div>
          <button class="cart-remove-btn" onclick="Cart.removeItem('${item.productId}')" title="Eliminar">✕</button>
        </div>
      </div>
    `).join('');

    if (cartTotal) cartTotal.textContent = `S/ ${total.toLocaleString('es-PE')}`;
  },

  toggleCart() {
    const panel = document.getElementById('cart-panel');
    const overlay = document.getElementById('cart-overlay');
    if (!panel) return;
    const isOpen = panel.classList.contains('open');
    if (isOpen) {
      panel.classList.remove('open');
      if (overlay) overlay.classList.remove('active');
    } else {
      panel.classList.add('open');
      if (overlay) overlay.classList.add('active');
      this.renderCart();
    }
  },

  // ── Catalog ───────────────────────────────────────────────
  renderCatalog() {
    const grid = document.getElementById('catalog-grid');
    if (!grid) return;
    grid.innerHTML = CATALOG.map((p, i) => `
      <div class="product-card glass-card reveal" style="animation-delay:${i * 0.08}s" data-id="${p.id}">
        <div class="product-img-wrap">
          <img src="${p.image}" alt="${p.name}" class="product-img" loading="lazy">
          <span class="product-badge ${p.badgeClass}">${p.badge}</span>
          <div class="product-category-tag">${p.category}</div>
        </div>
        <div class="product-body">
          <h3 class="product-name">${p.emoji} ${p.name}</h3>
          <p class="product-desc">${p.description}</p>
          <div class="product-features">
            ${p.features.map(f => `<span class="feature-tag">✓ ${f}</span>`).join('')}
          </div>
          <div class="product-footer">
            <div class="product-price">
              <span class="price-label">Desde</span>
              <span class="price-amount">S/ ${p.price.toLocaleString('es-PE')}</span>
              <span class="price-currency">PEN</span>
            </div>
            <button class="btn btn-primary btn-sm add-to-cart-btn"
              id="add-${p.id}"
              onclick="Cart.addItem('${p.id}'); this.classList.add('added'); setTimeout(()=>this.classList.remove('added'),800)">
              🛒 Agregar
            </button>
          </div>
        </div>
      </div>
    `).join('');

    // Scroll reveal
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); } });
    }, { threshold: 0.1 });
    grid.querySelectorAll('.reveal').forEach(el => observer.observe(el));
  },

  // ── Chat ──────────────────────────────────────────────────
  appendChatMessage(role, content, typing = false) {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    const msgEl = document.createElement('div');
    msgEl.className = `chat-msg ${role}`;

    if (typing) {
      msgEl.innerHTML = `<div class="chat-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
      container.appendChild(msgEl);
      container.scrollTop = container.scrollHeight;
      return msgEl;
    }

    // Parse simple markdown: **bold**, \n as <br>
    const formatted = content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');

    const avatar = role === 'agent' ? '🍫' : '👤';
    msgEl.innerHTML = `
      <div class="chat-avatar">${avatar}</div>
      <div class="chat-bubble">${formatted}</div>
    `;
    msgEl.style.animation = 'logEntry 0.3s ease forwards';
    container.appendChild(msgEl);
    container.scrollTop = container.scrollHeight;
    return msgEl;
  },

  toggleChat() {
    const panel = document.getElementById('chat-panel');
    const btn = document.getElementById('chat-toggle-btn');
    if (!panel) return;
    const isOpen = panel.classList.contains('open');
    panel.classList.toggle('open');
    if (btn) btn.innerHTML = isOpen ? '💬' : '✕';
  },

  // ── Swarm Log ─────────────────────────────────────────────
  appendSwarmLog(entry) {
    const container = document.getElementById('swarm-log');
    if (!container) return;

    const el = document.createElement('div');
    el.className = `log-entry log-${entry.type}`;
    el.style.animation = 'logEntry 0.3s ease forwards';

    const typeLabels = { info: '', success: '✅', error: '❌', warning: '⚠️', mcp: '🔌', handoff: '🔀' };
    el.innerHTML = `
      <span class="log-time">${entry.timestamp}</span>
      <span class="log-icon">${entry.icon}</span>
      <div class="log-content">
        <span class="log-agent">${entry.agent}</span>
        <span class="log-msg">${typeLabels[entry.type] || ''} ${entry.message}</span>
      </div>
    `;
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
  },

  // ── Step Indicator ────────────────────────────────────────
  updateStep(stepNum) {
    document.querySelectorAll('.step').forEach((el, i) => {
      el.classList.remove('active', 'done');
      if (i + 1 < stepNum) el.classList.add('done');
      else if (i + 1 === stepNum) el.classList.add('active');
    });
  },

  // ── Navbar scroll ─────────────────────────────────────────
  initNavbar() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    window.addEventListener('scroll', () => {
      navbar.classList.toggle('scrolled', window.scrollY > 40);
    });
  }
};

window.UI = UI;
