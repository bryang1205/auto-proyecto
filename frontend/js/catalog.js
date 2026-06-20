/* ── Catálogo de Productos — Chocolates Helena ──────────────── */

const CATALOG = [
  {
    id: 'choc-001',
    name: 'Trufa Negra Intenso',
    type: 'trufa_negra',
    price: 45,
    category: 'Trufas',
    badge: 'Más Vendido',
    badgeClass: 'bestseller',
    description: 'Ganache de cacao 70% con polvo de oro comestible. Intensidad y elegancia en cada bocado.',
    features: ['70% Cacao puro', 'Oro comestible', 'Artesanal'],
    image: 'assets/images/trufa_negra.png',
    emoji: '🍫'
  },
  {
    id: 'choc-002',
    name: 'Bombón de Maracuyá',
    type: 'bombon_maracuya',
    price: 38,
    category: 'Bombones',
    badge: 'Tropical',
    badgeClass: 'tropical',
    description: 'Cobertura de chocolate oscuro con relleno de maracuyá fresco. Equilibrio perfecto entre dulce y ácido.',
    features: ['Fruta fresca', 'Sin conservantes', 'Caja x6'],
    image: 'assets/images/bombon_maracuya.png',
    emoji: '🌺'
  },
  {
    id: 'choc-003',
    name: 'Tableta de Leche Premium',
    type: 'tableta_leche',
    price: 32,
    category: 'Tabletas',
    badge: 'Clásico',
    badgeClass: 'classic',
    description: 'Chocolate de leche con caramelo salado artesanal. La textura perfecta, crujiente por fuera y suave por dentro.',
    features: ['Caramelo artesanal', '100g', 'Leche peruana'],
    image: 'assets/images/tableta_leche.png',
    emoji: '🍬'
  },
  {
    id: 'choc-004',
    name: 'Chocolate Blanco con Rosa',
    type: 'chocolate_blanco',
    price: 42,
    category: 'Tabletas',
    badge: 'Edición Especial',
    badgeClass: 'special',
    description: 'Chocolate blanco belga con pétalos de rosa deshidratados y frambuesa liofilizada. Delicadeza en estado puro.',
    features: ['Pétalos de rosa', 'Frambuesa liofilizada', 'Belga'],
    image: 'assets/images/chocolate_blanco_rosa.png',
    emoji: '🌹'
  },
  {
    id: 'choc-005',
    name: 'Caja de Regalo Especial',
    type: 'caja_regalo',
    price: 120,
    category: 'Colecciones',
    badge: 'Premium',
    badgeClass: 'premium',
    description: 'Selección curada de 20 piezas exclusivas en caja negra con ribete dorado. El regalo perfecto para ocasiones especiales.',
    features: ['20 piezas', 'Caja premium', 'Personalizable'],
    image: 'assets/images/caja_regalo.png',
    emoji: '🎁'
  },
  {
    id: 'choc-006',
    name: 'Chocolate Negro Picante',
    type: 'chocolate_picante',
    price: 36,
    category: 'Especiales',
    badge: '🌶️ Atrevido',
    badgeClass: 'spicy',
    description: '75% cacao con extracto de ají peruano. Para los paladares aventureros que buscan una experiencia única.',
    features: ['75% Cacao', 'Ají peruano', 'Edición limitada'],
    image: 'assets/images/chocolate_picante.png',
    emoji: '🌶️'
  }
];

/* ── Lógica del Carrito ─────────────────────────────────────── */
const Cart = {
  addItem(productId, quantity = 1) {
    const product = CATALOG.find(p => p.id === productId);
    if (!product) return false;
    SessionState.addCartItem(product, quantity);
    UI.renderCart();
    UI.showToast(`✅ ${product.name} agregado al carrito`, 'success');
    return true;
  },

  removeItem(productId) {
    SessionState.removeCartItem(productId);
    UI.renderCart();
  },

  updateQuantity(productId, quantity) {
    SessionState.updateCartQuantity(productId, parseInt(quantity));
    UI.renderCart();
  },

  clear() {
    SessionState.cart = [];
    SessionState.emit('cart:update', { cart: [] });
    UI.renderCart();
  },

  getCount() {
    return SessionState.cart.reduce((sum, i) => sum + i.quantity, 0);
  },

  getTotal() {
    return SessionState.getCartTotal();
  }
};

window.CATALOG = CATALOG;
window.Cart = Cart;
