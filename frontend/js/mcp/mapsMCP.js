/* ── Maps_mcp_server — Simulado (Ciudades Peruanas) ─────────── */

const MapsMCP = {
  SERVER_NAME: 'Maps_mcp_server',

  // Base de coordenadas de ciudades peruanas
  _geoBase: {
    'lima':        { lat: -12.0464, lng: -77.0428, ciudad: 'Lima' },
    'miraflores':  { lat: -12.1191, lng: -77.0299, ciudad: 'Lima - Miraflores' },
    'san isidro':  { lat: -12.0989, lng: -77.0369, ciudad: 'Lima - San Isidro' },
    'surco':       { lat: -12.1397, lng: -76.9976, ciudad: 'Lima - Surco' },
    'callao':      { lat: -12.0565, lng: -77.1181, ciudad: 'Callao' },
    'arequipa':    { lat: -16.4090, lng: -71.5375, ciudad: 'Arequipa' },
    'cusco':       { lat: -13.5319, lng: -71.9675, ciudad: 'Cusco' },
    'cuzco':       { lat: -13.5319, lng: -71.9675, ciudad: 'Cusco' },
    'trujillo':    { lat: -8.1091,  lng: -79.0215, ciudad: 'Trujillo' },
    'piura':       { lat: -5.1945,  lng: -80.6328, ciudad: 'Piura' },
    'chiclayo':    { lat: -6.7714,  lng: -79.8409, ciudad: 'Chiclayo' },
    'iquitos':     { lat: -3.7437,  lng: -73.2516, ciudad: 'Iquitos' },
    'puno':        { lat: -15.8402, lng: -70.0219, ciudad: 'Puno' },
    'huancayo':    { lat: -12.0647, lng: -75.2048, ciudad: 'Huancayo' },
    'tacna':       { lat: -18.0066, lng: -70.2493, ciudad: 'Tacna' },
    'ica':         { lat: -14.0678, lng: -75.7286, ciudad: 'Ica' },
    'ayacucho':    { lat: -13.1588, lng: -74.2236, ciudad: 'Ayacucho' },
    'cajamarca':   { lat: -7.1638,  lng: -78.5006, ciudad: 'Cajamarca' },
    'tarapoto':    { lat: -6.4851,  lng: -76.3640, ciudad: 'Tarapoto' },
    'default':     { lat: -12.0464, lng: -77.0428, ciudad: 'Lima' }
  },

  // Origen de despacho (bodega Chocolates Helena — Lima, Perú)
  _origen: { lat: -12.1191, lng: -77.0299, nombre: 'Bodega Helena — Miraflores, Lima' },

  _delay(ms) { return new Promise(r => setTimeout(r, ms)); },

  _log(tool, params, result, status) {
    try {
      if (typeof SessionState !== 'undefined' && SessionState.addMCPCall) {
        SessionState.addMCPCall(this.SERVER_NAME, tool, params, result, status);
        SessionState.addToLog('Sistema MCP', `${this.SERVER_NAME}::${tool} → ${status === 'success' ? '✅' : '❌'} Ruta calculada: ${result.distanciaKm || '?'}km, ${result.tiempoEstimadoMin || '?'}min`, 'mcp', '🗺️');
      }
    } catch(e) { console.warn('MapsMCP._log error:', e); }
  },

  _detectCiudad(direccion) {
    const lower = (direccion || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    for (const [key, val] of Object.entries(this._geoBase)) {
      if (lower.includes(key)) return val;
    }
    return this._geoBase['default'];
  },

  _calcDistance(lat1, lng1, lat2, lng2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180) * Math.cos(lat2*Math.PI/180) * Math.sin(dLng/2)**2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  },

  _generateRutaPuntos(origenLat, origenLng, destLat, destLng, n = 6) {
    const puntos = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n;
      const jitterLat = (Math.random() - 0.5) * 0.005;
      const jitterLng = (Math.random() - 0.5) * 0.005;
      puntos.push({
        lat: origenLat + (destLat - origenLat) * t + jitterLat,
        lng: origenLng + (destLng - origenLng) * t + jitterLng,
        seq: i
      });
    }
    return puntos;
  },

  async calcular_ruta_entrega(direccionDestino) {
    await this._delay(900 + Math.random() * 600);

    if (!direccionDestino || direccionDestino.trim().length < 5) {
      const result = { error: 'Dirección de entrega inválida o insuficiente' };
      this._log('calcular_ruta_entrega', { direccion: direccionDestino }, result, 'error');
      throw new Error(result.error);
    }

    const destGeo = this._detectCiudad(direccionDestino);
    // Añadir offset aleatorio pequeño para simular dirección específica
    const destLat = destGeo.lat + (Math.random() - 0.5) * 0.05;
    const destLng = destGeo.lng + (Math.random() - 0.5) * 0.05;

    const distanciaKm = Math.round(this._calcDistance(this._origen.lat, this._origen.lng, destLat, destLng) * 10) / 10;
    // Velocidad promedio ciudad: 25 km/h + tiempo de preparación
    const tiempoBase = Math.round((distanciaKm / 25) * 60);
    const tiempoEstimadoMin = tiempoBase + 20 + Math.floor(Math.random() * 15); // +20 prep +random

    const rutaPuntos = this._generateRutaPuntos(this._origen.lat, this._origen.lng, destLat, destLng);

    const result = {
      origen: this._origen,
      destino: {
        direccion: direccionDestino,
        ciudad: destGeo.ciudad,
        lat: parseFloat(destLat.toFixed(6)),
        lng: parseFloat(destLng.toFixed(6))
      },
      distanciaKm,
      tiempoEstimadoMin,
      tiempoEstimadoTexto: tiempoEstimadoMin < 60
        ? `${tiempoEstimadoMin} minutos`
        : `${Math.floor(tiempoEstimadoMin/60)}h ${tiempoEstimadoMin%60}min`,
      rutaPuntos,
      vehiculo: 'Moto de Delivery Helena — Lima',
      conductor: 'Asignado automáticamente',
      tracking_id: 'TRK-' + Date.now().toString(36).toUpperCase(),
      calculado_en: new Date().toISOString()
    };

    this._log('calcular_ruta_entrega', { direccion: direccionDestino }, result, 'success');
    return result;
  }
};

window.MapsMCP = MapsMCP;
