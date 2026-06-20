/* ── MapPicker — Selección de dirección con Google Maps ────────
   VERSIÓN CORREGIDA:
   - Sin loading=async (incompatible con callback pattern)
   - Callback global para detección de carga correcta
   - Fallback a modo texto si Maps falla o no hay key
   - Botón "Usar esto" siempre funciona
   ────────────────────────────────────────────────────────────── */

const MapPicker = (() => {
  let _map = null;
  let _marker = null;
  let _autocomplete = null;
  let _selectedAddress = null;
  let _selectedLatLng = null;
  let _onConfirm = null;
  let _sdkLoaded = false;
  let _sdkLoading = false;
  let _sdkFailed = false;

  // ── Cargar SDK de Google Maps con callback clásico ────────
  function _loadSDK() {
    return new Promise((resolve, reject) => {

      // Ya está listo
      if (_sdkLoaded && window.google?.maps?.places) {
        resolve(); return;
      }

      // Ya falló antes — no reintentar
      if (_sdkFailed) {
        reject(new Error('SDK_FAILED')); return;
      }

      const key = window.HELENA_CONFIG?.GOOGLE_MAPS_API_KEY;
      if (!key || key === 'YOUR_GOOGLE_MAPS_API_KEY' || key.trim() === '') {
        console.warn('MapPicker: API Key no encontrada en window.HELENA_CONFIG');
        reject(new Error('NO_KEY')); return;
      }

      // Ya está cargando — esperar con polling
      if (_sdkLoading) {
        let attempts = 0;
        const poll = setInterval(() => {
          attempts++;
          if (_sdkLoaded && window.google?.maps?.places) {
            clearInterval(poll); resolve();
          } else if (_sdkFailed || attempts > 80) {
            clearInterval(poll); reject(new Error('TIMEOUT'));
          }
        }, 100);
        return;
      }

      _sdkLoading = true;

      // Callback global — el SDK lo llama cuando termina de cargar
      window.__helenaMapsReady = () => {
        _sdkLoaded = true;
        _sdkLoading = false;
        delete window.__helenaMapsReady;
        resolve();
      };

      const script = document.createElement('script');
      // IMPORTANTE: sin "loading=async" — usar callback clásico
      script.src = `https://maps.googleapis.com/maps/api/js?key=${key}&libraries=places&language=es&region=PE&callback=__helenaMapsReady`;
      script.async = true;
      script.defer = true;

      script.onerror = () => {
        _sdkLoading = false;
        _sdkFailed = true;
        delete window.__helenaMapsReady;
        reject(new Error('LOAD_FAIL'));
      };

      // Timeout de seguridad 10s
      const timeout = setTimeout(() => {
        if (!_sdkLoaded) {
          _sdkLoading = false;
          _sdkFailed = true;
          reject(new Error('TIMEOUT'));
        }
      }, 10000);

      // Limpiar timeout cuando resuelva
      const origReady = window.__helenaMapsReady;
      window.__helenaMapsReady = () => {
        clearTimeout(timeout);
        origReady();
      };

      document.head.appendChild(script);
    });
  }

  // ── Estilos del modal ────────────────────────────────────
  function _injectStyles() {
    if (document.getElementById('mp-styles')) return;
    const st = document.createElement('style');
    st.id = 'mp-styles';
    st.textContent = `
      #mp-overlay {
        position:fixed;inset:0;z-index:9800;
        background:rgba(8,3,5,0.92);backdrop-filter:blur(16px);
        display:flex;align-items:center;justify-content:center;padding:16px;
        animation:mpFade .3s ease;
      }
      #mp-overlay.hidden{display:none}
      @keyframes mpFade{from{opacity:0}to{opacity:1}}
      #mp-modal {
        background:rgba(26,10,13,.97);
        border:1px solid rgba(232,184,75,.3);
        border-radius:22px;width:100%;max-width:820px;
        max-height:92vh;display:flex;flex-direction:column;
        box-shadow:0 32px 80px rgba(0,0,0,.7),0 0 60px rgba(200,16,46,.15);
        overflow:hidden;animation:mpUp .4s cubic-bezier(.34,1.56,.64,1);
      }
      @keyframes mpUp{from{opacity:0;transform:translateY(28px) scale(.97)}to{opacity:1;transform:none}}
      #mp-header{
        padding:18px 22px 14px;border-bottom:1px solid rgba(232,184,75,.15);
        display:flex;align-items:center;justify-content:space-between;flex-shrink:0;
      }
      #mp-header h3{font-family:'Playfair Display',serif;color:#E8B84B;font-size:1.15rem;display:flex;align-items:center;gap:8px;margin:0}
      #mp-close{
        background:rgba(200,16,46,.15);border:1px solid rgba(200,16,46,.35);
        color:#ff7070;border-radius:50%;width:32px;height:32px;cursor:pointer;
        font-size:.95rem;display:flex;align-items:center;justify-content:center;
        transition:all .2s;flex-shrink:0;
      }
      #mp-close:hover{background:rgba(200,16,46,.35);transform:scale(1.1)}
      #mp-search-wrap{
        padding:14px 22px;flex-shrink:0;
        border-bottom:1px solid rgba(232,184,75,.1);
        display:flex;gap:10px;align-items:center;
      }
      #mp-search{
        flex:1;padding:12px 16px;
        background:rgba(45,18,24,.85);border:1px solid rgba(232,184,75,.28);
        border-radius:10px;color:#F7EDD8;font-size:.92rem;
        font-family:'Inter',sans-serif;outline:none;transition:border-color .2s;
      }
      #mp-search:focus{border-color:#E8B84B;box-shadow:0 0 0 3px rgba(232,184,75,.12)}
      #mp-search::placeholder{color:#8A6E52}
      #mp-use-typed{
        padding:11px 18px;border-radius:10px;font-size:.82rem;font-weight:600;
        background:linear-gradient(135deg,rgba(200,16,46,.8),rgba(139,10,30,.9));
        border:1px solid rgba(200,16,46,.5);
        color:#fff;cursor:pointer;white-space:nowrap;transition:all .2s;flex-shrink:0;
        box-shadow:0 2px 8px rgba(200,16,46,.3);
      }
      #mp-use-typed:hover{background:linear-gradient(135deg,#C8102E,#8B0A1E);transform:translateY(-1px)}
      /* Google Autocomplete dark override */
      .pac-container{
        background:rgba(26,10,13,.98)!important;
        border:1px solid rgba(232,184,75,.3)!important;
        border-radius:12px!important;
        box-shadow:0 16px 40px rgba(0,0,0,.6)!important;
        font-family:'Inter',sans-serif!important;
        z-index:99999!important;overflow:hidden;margin-top:4px;
      }
      .pac-item{padding:10px 16px!important;color:#C8A87A!important;border-top:1px solid rgba(232,184,75,.1)!important;cursor:pointer!important;font-size:.87rem!important}
      .pac-item:hover,.pac-item-selected{background:rgba(232,184,75,.08)!important}
      .pac-item-query{color:#F7EDD8!important;font-weight:600!important}
      .pac-matched{color:#E8B84B!important}
      .pac-icon{display:none!important}
      #mp-loading{
        flex:1;min-height:240px;display:flex;flex-direction:column;
        align-items:center;justify-content:center;gap:14px;
      }
      #mp-loading-spinner{
        width:36px;height:36px;border:3px solid rgba(232,184,75,.2);
        border-top-color:#E8B84B;border-radius:50%;
        animation:mpSpin .8s linear infinite;
      }
      @keyframes mpSpin{to{transform:rotate(360deg)}}
      #mp-map-div{width:100%;flex:1;min-height:340px;display:none}
      #mp-nokey{
        flex:1;min-height:200px;display:none;flex-direction:column;
        align-items:center;justify-content:center;gap:14px;padding:32px;text-align:center;
      }
      #mp-nokey .nk-icon{font-size:2.8rem}
      #mp-nokey h4{font-family:'Playfair Display',serif;color:#E8B84B;font-size:1.1rem;margin:0}
      #mp-nokey p{color:#8A6E52;font-size:.86rem;line-height:1.65;max-width:420px;margin:0}
      #mp-nokey code{background:rgba(45,18,24,.8);border:1px solid rgba(232,184,75,.2);border-radius:5px;padding:2px 7px;color:#E8B84B;font-size:.8rem}
      #mp-districts{
        display:none;flex-wrap:wrap;gap:8px;padding:16px 22px;
        border-top:1px solid rgba(232,184,75,.08);flex-shrink:0;
        max-height:120px;overflow-y:auto;
      }
      .mp-district-btn{
        padding:6px 14px;border-radius:20px;font-size:.78rem;font-weight:500;
        background:rgba(45,18,24,.6);border:1px solid rgba(232,184,75,.2);
        color:#C8A87A;cursor:pointer;transition:all .18s;white-space:nowrap;
      }
      .mp-district-btn:hover{background:rgba(232,184,75,.12);border-color:rgba(232,184,75,.5);color:#F7EDD8}
      #mp-info{
        padding:12px 22px;flex-shrink:0;
        border-top:1px solid rgba(232,184,75,.1);
        background:rgba(45,18,24,.5);
        display:flex;align-items:center;gap:10px;min-height:52px;
      }
      #mp-info-text{flex:1;font-size:.87rem;color:#8A6E52;font-style:italic;transition:color .25s;word-break:break-word}
      #mp-info-text.ok{color:#F7EDD8;font-style:normal}
      #mp-info-text.ok::before{content:'✅ ';font-style:normal}
      #mp-footer{
        padding:14px 22px;flex-shrink:0;border-top:1px solid rgba(232,184,75,.12);
        display:flex;gap:10px;justify-content:flex-end;align-items:center;
      }
      #mp-tip{flex:1;font-size:.74rem;color:#5A3838;line-height:1.4}
      #mp-cancel{
        padding:10px 22px;border-radius:999px;
        background:transparent;border:1px solid rgba(232,184,75,.2);
        color:#8A6E52;font-size:.86rem;cursor:pointer;transition:all .2s;
      }
      #mp-cancel:hover{border-color:rgba(232,184,75,.4);color:#C8A87A}
      #mp-confirm{
        padding:11px 28px;border-radius:999px;
        background:linear-gradient(135deg,#C8102E,#8B0A1E 55%,#C49A35);
        color:#fff;font-size:.88rem;font-weight:600;cursor:pointer;border:none;
        transition:all .2s;box-shadow:0 4px 16px rgba(200,16,46,.4);
        opacity:.35;pointer-events:none;
      }
      #mp-confirm.enabled{opacity:1;pointer-events:all}
      #mp-confirm.enabled:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(200,16,46,.55)}
    `;
    document.head.appendChild(st);
  }

  // ── Distritos de Lima para acceso rápido ─────────────────
  const LIMA_DISTRICTS = [
    'Miraflores', 'San Isidro', 'Surco', 'Barranco', 'La Molina',
    'San Borja', 'Jesús María', 'Lince', 'Magdalena', 'Pueblo Libre',
    'Callao', 'Los Olivos', 'SJL', 'Villa El Salvador', 'Chorrillos'
  ];

  // ── HTML del modal ───────────────────────────────────────
  function _injectModal() {
    if (document.getElementById('mp-overlay')) return;
    const el = document.createElement('div');
    el.id = 'mp-overlay';
    el.className = 'hidden';
    el.innerHTML = `
      <div id="mp-modal">
        <div id="mp-header">
          <h3>📍 Seleccionar dirección de entrega</h3>
          <button id="mp-close" onclick="window.MapPicker.close()" title="Cerrar">✕</button>
        </div>

        <div id="mp-search-wrap">
          <input id="mp-search" type="text"
            placeholder="🔍 Escribe tu dirección (ej: Av. Larco 123, Miraflores)..."
            autocomplete="off" autocorrect="off" spellcheck="false">
          <button id="mp-use-typed" onclick="window.MapPicker._useTyped()">
            ✍️ Usar esta dirección
          </button>
        </div>

        <!-- Accesos rápidos por distrito -->
        <div id="mp-districts">
          ${LIMA_DISTRICTS.map(d => `<button class="mp-district-btn" onclick="window.MapPicker._useDistrict('${d}')">${d}</button>`).join('')}
        </div>

        <!-- Estado de carga -->
        <div id="mp-loading">
          <div id="mp-loading-spinner"></div>
          <div style="font-size:.85rem;color:#8A6E52">Cargando mapa...</div>
        </div>

        <!-- Mapa (oculto hasta que cargue) -->
        <div id="mp-map-div"></div>

        <!-- Modo sin key -->
        <div id="mp-nokey">
          <div class="nk-icon">🗺️</div>
          <h4>Modo de texto activo</h4>
          <p>
            Escribe tu dirección completa en el campo de arriba y presiona
            <strong>"✍️ Usar esta dirección"</strong>, o selecciona un distrito de Lima abajo.<br><br>
            Para activar el mapa interactivo, verifica que la <code>GOOGLE_MAPS_API_KEY</code>
            en <code>js/config.js</code> tenga habilitadas las APIs
            <strong>Maps JavaScript API</strong> y <strong>Places API</strong>
            en <a href="https://console.cloud.google.com" target="_blank" style="color:#E8B84B">Google Cloud Console</a>.
          </p>
        </div>

        <div id="mp-info">
          <span style="font-size:1.1rem;flex-shrink:0">📍</span>
          <span id="mp-info-text">Escribe tu dirección o haz clic en el mapa</span>
        </div>

        <div id="mp-footer">
          <span id="mp-tip">💡 Tip: selecciona un distrito para autocompletar</span>
          <button id="mp-cancel" onclick="window.MapPicker.close()">Cancelar</button>
          <button id="mp-confirm" onclick="window.MapPicker.confirm()">✅ Confirmar dirección</button>
        </div>
      </div>
    `;
    document.body.appendChild(el);

    // Enter en el input → usar typed
    setTimeout(() => {
      const input = document.getElementById('mp-search');
      if (input) {
        input.addEventListener('keydown', e => {
          if (e.key === 'Enter') { e.preventDefault(); MapPicker._useTyped(); }
        });
        // Habilitar confirm cuando hay texto suficiente
        input.addEventListener('input', () => {
          if (input.value.trim().length >= 8) {
            _setAddress(input.value.trim(), null, null);
          }
        });
      }
    }, 50);
  }

  // ── Mostrar/ocultar secciones del modal ──────────────────
  function _showLoading() {
    document.getElementById('mp-loading').style.display = 'flex';
    document.getElementById('mp-map-div').style.display = 'none';
    document.getElementById('mp-nokey').style.display = 'none';
    document.getElementById('mp-districts').style.display = 'none';
  }
  function _showMap() {
    document.getElementById('mp-loading').style.display = 'none';
    document.getElementById('mp-map-div').style.display = 'block';
    document.getElementById('mp-nokey').style.display = 'none';
    document.getElementById('mp-districts').style.display = 'none';
    document.getElementById('mp-tip').textContent = '💡 Haz clic en el mapa o busca tu dirección arriba';
  }
  function _showNoKey() {
    document.getElementById('mp-loading').style.display = 'none';
    document.getElementById('mp-map-div').style.display = 'none';
    document.getElementById('mp-nokey').style.display = 'flex';
    document.getElementById('mp-districts').style.display = 'flex';
    document.getElementById('mp-search').placeholder = '✏️ Escribe tu dirección: Av. Larco 123, Miraflores, Lima';
    document.getElementById('mp-tip').textContent = '💡 Escribe tu dirección y presiona "Usar esta dirección"';
  }

  // ── Actualizar dirección seleccionada ────────────────────
  function _setAddress(address, lat, lng) {
    if (!address || address.trim().length < 4) return;
    _selectedAddress = address.trim();
    _selectedLatLng = (lat != null && lng != null) ? { lat, lng } : null;

    const txt = document.getElementById('mp-info-text');
    const btn = document.getElementById('mp-confirm');
    const srch = document.getElementById('mp-search');

    if (txt) { txt.textContent = _selectedAddress; txt.classList.add('ok'); }
    if (btn) btn.classList.add('enabled');
    if (srch && srch.value.trim() !== _selectedAddress) srch.value = _selectedAddress;
  }

  // ── Usar lo que el usuario escribió ──────────────────────
  function _useTyped() {
    const val = (document.getElementById('mp-search')?.value || '').trim();
    if (val.length >= 5) {
      // Añadir "Lima, Perú" si no lo tiene
      const enriched = /lima|perú|peru/i.test(val) ? val : `${val}, Lima, Perú`;
      _setAddress(enriched, null, null);
    } else {
      const txt = document.getElementById('mp-info-text');
      if (txt) { txt.textContent = 'Escribe al menos 5 caracteres de tu dirección'; txt.classList.remove('ok'); }
    }
  }

  // ── Seleccionar distrito rápido ──────────────────────────
  function _useDistrict(district) {
    const search = document.getElementById('mp-search');
    const currentVal = (search?.value || '').trim();
    let newVal;
    if (currentVal && currentVal.length > 3 && !/miraflores|surco|barranco|san isidro|san borja|la molina|lince|magdalena|jesús maría|pueblo libre|callao|los olivos|sjl|villa|chorrillos/i.test(currentVal)) {
      newVal = `${currentVal}, ${district}, Lima`;
    } else {
      newVal = `${district}, Lima, Perú`;
    }
    if (search) search.value = newVal;
    _setAddress(newVal, null, null);
    if (_autocomplete && window.google?.maps?.places) {
      // Trigger autocomplete con el nuevo valor
    }
  }

  // ── Estilos oscuros del mapa ─────────────────────────────
  const DARK_MAP_STYLES = [
    { elementType: 'geometry', stylers: [{ color: '#1a0a0d' }] },
    { elementType: 'labels.text.fill', stylers: [{ color: '#C8A87A' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: '#1a0a0d' }] },
    { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#2d1218' }] },
    { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#4a1e25' }] },
    { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#c8a87a' }] },
    { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#4a1e25' }] },
    { featureType: 'road.highway', elementType: 'geometry.stroke', stylers: [{ color: '#7a3030' }] },
    { featureType: 'administrative', elementType: 'geometry.stroke', stylers: [{ color: '#4a1e25' }] },
    { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0a0305' }] },
    { featureType: 'poi', stylers: [{ visibility: 'simplified' }] },
    { featureType: 'poi', elementType: 'geometry', stylers: [{ color: '#2d1218' }] },
    { featureType: 'transit', elementType: 'geometry', stylers: [{ color: '#2d1218' }] },
  ];

  // ── Inicializar Google Maps ──────────────────────────────
  async function _initMap() {
    _showLoading();
    try {
      await _loadSDK();
      _showMap();

      const center = { lat: -12.0464, lng: -77.0428 }; // Lima centro

      _map = new google.maps.Map(document.getElementById('mp-map-div'), {
        center,
        zoom: 13,
        gestureHandling: 'greedy',
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        zoomControl: true,
        styles: DARK_MAP_STYLES,
      });

      // Marcador (invisible hasta primer clic)
      _marker = new google.maps.Marker({
        map: _map,
        draggable: true,
        visible: false,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 13,
          fillColor: '#C8102E',
          fillOpacity: 1,
          strokeColor: '#E8B84B',
          strokeWeight: 3,
        },
        title: 'Tu dirección de entrega',
        zIndex: 999,
      });

      const geocoder = new google.maps.Geocoder();

      // ── Geocodificar latLng → dirección real ──────────────
      function geocodeAndSet(latLng) {
        _marker.setPosition(latLng);
        _marker.setVisible(true);
        _map.panTo(latLng);

        // Activar botón inmediatamente con coordenadas
        const fallback = `${latLng.lat().toFixed(5)}, ${latLng.lng().toFixed(5)}, Lima, Perú`;
        _setAddress(fallback, latLng.lat(), latLng.lng());

        // Enriquecer con dirección real (asíncrono)
        geocoder.geocode({ location: latLng, region: 'PE', language: 'es' }, (results, status) => {
          if (status === 'OK' && results[0]) {
            _setAddress(results[0].formatted_address, latLng.lat(), latLng.lng());
          }
        });
      }

      // Clic en el mapa
      _map.addListener('click', e => geocodeAndSet(e.latLng));

      // Arrastrar marcador
      _marker.addListener('dragend', e => geocodeAndSet(e.latLng));

      // Autocomplete
      const searchInput = document.getElementById('mp-search');
      _autocomplete = new google.maps.places.Autocomplete(searchInput, {
        componentRestrictions: { country: 'PE' },
        fields: ['formatted_address', 'geometry', 'name'],
        types: ['geocode', 'establishment'],
      });

      _autocomplete.addListener('place_changed', () => {
        const place = _autocomplete.getPlace();
        if (!place.geometry?.location) {
          _useTyped();
          return;
        }
        const latLng = place.geometry.location;
        _map.setCenter(latLng);
        _map.setZoom(17);
        _marker.setPosition(latLng);
        _marker.setVisible(true);
        _setAddress(
          place.formatted_address || place.name,
          latLng.lat(),
          latLng.lng()
        );
      });

    } catch (err) {
      console.warn('MapPicker: Maps no disponible:', err.message);
      _showNoKey();
    }
  }

  // ── API Pública ──────────────────────────────────────────
  function open(callback) {
    console.log('MapPicker.open llamado');
    try {
      _onConfirm = callback;
      _selectedAddress = null;
      _selectedLatLng = null;

      _injectStyles();
      _injectModal();

      const overlay = document.getElementById('mp-overlay');
      const infoTxt = document.getElementById('mp-info-text');
      const confirmBtn = document.getElementById('mp-confirm');
      const search = document.getElementById('mp-search');

      if (overlay) overlay.classList.remove('hidden');
      if (infoTxt) { infoTxt.textContent = 'Escribe tu dirección o haz clic en el mapa'; infoTxt.classList.remove('ok'); }
      if (confirmBtn) confirmBtn.classList.remove('enabled');
      if (search) { search.value = ''; search.focus(); }

      if (!_map) {
        _initMap();
      } else {
        // Mapa ya existe — resetear marcador
        _showMap();
        if (_marker) _marker.setVisible(false);
      }
    } catch (e) {
      console.error('Error in MapPicker.open:', e);
      alert('Error abriendo mapa: ' + e.message);
    }
  }

  function close() {
    const overlay = document.getElementById('mp-overlay');
    if (overlay) overlay.classList.add('hidden');
  }

  function confirm() {
    if (!_selectedAddress) return;
    close();
    if (typeof _onConfirm === 'function') {
      _onConfirm({
        address: _selectedAddress,
        lat: _selectedLatLng?.lat ?? null,
        lng: _selectedLatLng?.lng ?? null
      });
    }
  }

  // Exponer globalmente — retornar el objeto para que `const MapPicker` no quede como undefined
  const _api = { open, close, confirm, _useTyped, _useDistrict };
  window.MapPicker = _api;
  return _api;
})();