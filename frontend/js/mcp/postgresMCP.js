/* ═══════════════════════════════════════════════════════════════
   postgres_mcp_server — Simulado
   ─ Simula operaciones de base de datos para el enjambre de agentes
   ─ En producción, este MCP conectaría a PostgreSQL / Supabase
   ═══════════════════════════════════════════════════════════════ */

const PostgresMCP = {
  SERVER_NAME: 'postgres_mcp_server',

  // ── Stock simulado (mismo catálogo que el backend Python) ──────
  _stock: {
    'trufa_negra':         { nombre: 'Trufa Negra Intenso',        cantidad: 50 },
    'bombon_maracuya':     { nombre: 'Bombón de Maracuyá',         cantidad: 40 },
    'tableta_leche':       { nombre: 'Tableta de Leche Premium',   cantidad: 60 },
    'chocolate_blanco':    { nombre: 'Chocolate Blanco con Rosa',  cantidad: 35 },
    'caja_regalo':         { nombre: 'Caja de Regalo Especial',    cantidad: 20 },
    'chocolate_picante':   { nombre: 'Chocolate Negro Picante',    cantidad: 45 },
    // IDs alternativos por si el frontend usa otro formato
    'choc-001': { nombre: 'Trufa Negra Intenso',        cantidad: 50 },
    'choc-002': { nombre: 'Bombón de Maracuyá',         cantidad: 40 },
    'choc-003': { nombre: 'Tableta de Leche Premium',   cantidad: 60 },
    'choc-004': { nombre: 'Chocolate Blanco con Rosa',  cantidad: 35 },
    'choc-005': { nombre: 'Caja de Regalo Especial',    cantidad: 20 },
    'choc-006': { nombre: 'Chocolate Negro Picante',    cantidad: 45 },
  },

  // ── Pedidos en sesión ──────────────────────────────────────────
  _pedidos: {},

  // ── Helpers ────────────────────────────────────────────────────
  _delay(ms) { return new Promise(r => setTimeout(r, ms)); },

  _log(tool, params, result, status = 'success') {
    try {
      if (typeof SessionState !== 'undefined' && SessionState.addMCPCall) {
        SessionState.addMCPCall(this.SERVER_NAME, tool, params, result, status);
        const icon = status === 'success' ? '✅' : '❌';
        SessionState.addToLog(
          'Sistema MCP',
          `${this.SERVER_NAME}::${tool} → ${icon} ${result._msg || ''}`,
          'mcp',
          '🗄️'
        );
      }
    } catch (e) { console.warn('PostgresMCP._log error:', e); }
  },

  _generatePedidoId() {
    const ts   = Date.now().toString(36).toUpperCase();
    const rand = Math.random().toString(36).substr(2, 4).toUpperCase();
    return `PED-HEL-${ts}-${rand}`;
  },

  // ── Herramienta 1: Verificar Stock ────────────────────────────
  async verificar_stock(productoTipo, cantidad) {
    await this._delay(400 + Math.random() * 300);

    const item = this._stock[productoTipo];
    const stockActual = item ? item.cantidad : 100; // Si no se reconoce el tipo, asumir 100

    const disponible = stockActual >= cantidad;
    const result = {
      disponible,
      stock_actual: stockActual,
      solicitado:   cantidad,
      producto:     item?.nombre || productoTipo,
      _msg:         disponible
        ? `Stock OK (${stockActual} disp.)`
        : `Sin stock (${stockActual} < ${cantidad})`,
    };

    this._log('verificar_stock', { productoTipo, cantidad }, result, disponible ? 'success' : 'error');
    return result;
  },

  // ── Herramienta 2: Insertar Pedido ────────────────────────────
  async insertar_pedido(payload) {
    await this._delay(600 + Math.random() * 400);

    const pedidoId = this._generatePedidoId();
    const pedido = {
      pedido_id:        pedidoId,
      cliente_nombre:   payload.clienteNombre   || payload.nombre   || '',
      cliente_email:    payload.clienteEmail     || payload.email    || '',
      cliente_telefono: payload.clienteTelefono  || payload.telefono || '',
      direccion:        payload.direccion        || '',
      items:            payload.items            || [],
      total:            payload.total            || 0,
      status:           'Pendiente de Pago',
      created_at:       new Date().toISOString(),
    };

    this._pedidos[pedidoId] = pedido;

    // Reducir stock
    for (const item of (payload.items || [])) {
      const tipo = item.type || item.productId || '';
      if (this._stock[tipo]) {
        this._stock[tipo].cantidad = Math.max(0, this._stock[tipo].cantidad - (item.quantity || 1));
      }
    }

    const result = {
      success:   true,
      pedido_id: pedidoId,
      status:    'Pendiente de Pago',
      _msg:      `Pedido ${pedidoId} creado`,
    };

    this._log('insertar_pedido', { cliente: payload.clienteNombre, total: payload.total }, result, 'success');
    return result;
  },

  // ── Herramienta 3: Cancelar / Eliminar Pedido ─────────────────
  async eliminar_o_cancelar_pedido(pedidoId) {
    await this._delay(300 + Math.random() * 200);

    const pedido = this._pedidos[pedidoId];
    if (pedido) {
      pedido.status = 'Cancelado';

      // Reintegrar stock
      for (const item of (pedido.items || [])) {
        const tipo = item.type || item.productId || '';
        if (this._stock[tipo]) {
          this._stock[tipo].cantidad += (item.quantity || 1);
        }
      }
    }

    const result = {
      success:   true,
      pedido_id: pedidoId,
      status:    'Cancelado',
      _msg:      `Pedido ${pedidoId} cancelado y stock reintegrado`,
    };

    this._log('eliminar_o_cancelar_pedido', { pedidoId }, result, 'success');
    return result;
  },

  // ── Herramienta 4: Actualizar a Producción ────────────────────
  async actualizar_pedido_produccion(pedidoId) {
    await this._delay(400 + Math.random() * 300);

    const pedido = this._pedidos[pedidoId];
    if (pedido) {
      pedido.status = 'Pagado - En Preparación';
      pedido.updated_at = new Date().toISOString();
    }

    const result = {
      success:   true,
      pedido_id: pedidoId,
      status:    'Pagado - En Preparación',
      _msg:      `Pedido ${pedidoId} → En Preparación`,
    };

    this._log('actualizar_pedido_produccion', { pedidoId }, result, 'success');
    return result;
  },

  // ── Herramienta 5: Guardar Ruta de Entrega ────────────────────
  async actualizar_pedido_entrega(pedidoId, rutaInfo) {
    await this._delay(300 + Math.random() * 200);

    const pedido = this._pedidos[pedidoId];
    if (pedido) {
      pedido.status      = 'En Camino';
      pedido.ruta        = rutaInfo;
      pedido.tracking_id = rutaInfo?.tracking_id || '';
      pedido.updated_at  = new Date().toISOString();
    }

    const result = {
      success:     true,
      pedido_id:   pedidoId,
      status:      'En Camino',
      tracking_id: rutaInfo?.tracking_id || '',
      _msg:        `Ruta asignada al pedido ${pedidoId}`,
    };

    this._log('actualizar_pedido_entrega', { pedidoId, tracking: rutaInfo?.tracking_id }, result, 'success');
    return result;
  },
};

window.PostgresMCP = PostgresMCP;
