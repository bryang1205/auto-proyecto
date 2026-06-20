/* ── Agente 2: Analizador de Pedidos ───────────────────────── */

class OrderAgent {
  constructor(orchestrator) {
    this.name = 'Agente Analizador de Pedidos';
    this.icon = '📋';
    this.orchestrator = orchestrator;
  }

  log(msg, type = 'info') {
    SessionState.addToLog(this.name, msg, type, this.icon);
  }

  async activate() {
    SessionState.setAgent(this.name);
    this.log('Activado. Iniciando validación de integridad del pedido...', 'info');

    // 1. Validar estructura
    const validation = this._validateOrderStructure();
    if (!validation.valid) {
      this.log(`Pedido inválido: ${validation.reason}`, 'error');
      return {
        success: false,
        handoff: 'frontAgent',
        reason: 'orden_incompleta',
        missingFields: validation.missingFields
      };
    }

    this.log(`Pedido estructuralmente válido. Items: ${SessionState.currentOrder.items.length}, Total: $${SessionState.currentOrder.total.toLocaleString('es-CO')} COP`, 'success');

    // 2. Verificar stock por cada item vía MCP
    try {
      await this._verificarStockTodos();
    } catch (err) {
      this.log(`Error al verificar stock: ${err.message}`, 'error');
      return {
        success: false,
        handoff: 'frontAgent',
        reason: 'stock_insuficiente',
        error: err.message
      };
    }

    // 3. Insertar pedido en BD vía MCP
    let pedidoResult;
    try {
      pedidoResult = await this._insertarPedido();
    } catch (err) {
      this.log(`Error al registrar pedido en BD: ${err.message}`, 'error');
      return {
        success: false,
        handoff: null,
        error: `Error MCP BD: ${err.message}`
      };
    }

    SessionState.currentOrder.pedidoId = pedidoResult.pedido_id;
    SessionState.currentOrder.status = 'Pendiente de Pago';

    this.log(`✅ Pedido registrado exitosamente. ID: ${pedidoResult.pedido_id} | Estado: Pendiente de Pago`, 'success');
    this.log('🔀 HANDOFF → Agente de Validación de Pagos', 'handoff');

    return {
      success: true,
      handoff: 'paymentAgent',
      pedidoId: pedidoResult.pedido_id
    };
  }

  _validateOrderStructure() {
    const order = SessionState.currentOrder;
    const customer = SessionState.customer;
    const missing = [];

    if (!customer.name?.trim()) missing.push('name');
    if (!customer.email?.trim()) missing.push('email');
    if (!customer.phone?.trim()) missing.push('phone');
    if (!customer.address?.trim()) missing.push('address');
    if (!order.items || order.items.length === 0) missing.push('items');
    if (!order.total || order.total <= 0) missing.push('total');

    if (missing.length > 0) {
      return { valid: false, reason: `Campos faltantes: ${missing.join(', ')}`, missingFields: missing };
    }

    // Validar cada item
    for (const item of order.items) {
      if (!item.productId || !item.quantity || item.quantity <= 0 || !item.unitPrice) {
        return { valid: false, reason: `Item inválido en el pedido: ${JSON.stringify(item)}`, missingFields: ['items'] };
      }
    }

    return { valid: true };
  }

  async _verificarStockTodos() {
    this.log(`Verificando stock para ${SessionState.currentOrder.items.length} producto(s)...`, 'info');
    for (const item of SessionState.currentOrder.items) {
      const result = await PostgresMCP.verificar_stock(item.type, item.quantity);
      if (!result.disponible) {
        throw new Error(`Stock insuficiente para "${item.name}". Disponible: ${result.stock_actual}, Solicitado: ${item.quantity}`);
      }
      this.log(`Stock OK — ${item.name}: ${result.stock_actual} unidades disponibles`, 'success');
    }
  }

  async _insertarPedido() {
    const customer = SessionState.customer;
    const order = SessionState.currentOrder;

    this.log('Registrando pedido en la base de datos (estado: Pendiente de Pago)...', 'info');

    const ordenPayload = {
      clienteId: customer.id,
      clienteNombre: customer.name,
      clienteEmail: customer.email,
      clienteTelefono: customer.phone,
      direccion: customer.address,
      items: order.items,
      total: order.total
    };

    return await PostgresMCP.insertar_pedido(ordenPayload);
  }
}

window.OrderAgent = OrderAgent;
