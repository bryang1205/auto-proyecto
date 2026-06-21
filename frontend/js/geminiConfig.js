/* ═══════════════════════════════════════════════════════════════
   GeminiConfig — Configuración e inicialización del sistema
   ─ Verifica estado del backend Python y LangSmith
   ─ Actualiza el indicador de estado en el chat header
   ═══════════════════════════════════════════════════════════════ */

const GeminiConfig = {

  _initialized: false,

  init() {
    if (this._initialized) return;
    this._initialized = true;

    const config = window.HELENA_CONFIG || {};
    const backendUrl = config.PYTHON_BACKEND_URL || '';
    const geminiKey  = config.GEMINI_API_KEY     || '';

    console.log('[Helena] GeminiConfig.init()');
    console.log(`  Backend Python: ${backendUrl || '(no configurado)'}`);
    console.log(`  Gemini Key: ${geminiKey ? '✅ configurada' : '⚠️ no configurada'}`);

    // Verificar estado del backend en background (no bloquea la UI)
    if (backendUrl) {
      this._checkBackendStatus(backendUrl);
    } else {
      this._updateStatusUI({ backend: false, langsmith: false });
    }
  },

  // Solo muestra prompt si no hay ni backend ni key de Gemini
  promptIfNeeded() {
    const config = window.HELENA_CONFIG || {};
    const hasBackend = !!(config.PYTHON_BACKEND_URL);
    const hasGemini  = !!(config.GEMINI_API_KEY && !config.GEMINI_API_KEY.includes('TU_'));

    if (!hasBackend && !hasGemini) {
      console.warn('[Helena] Sin backend Python ni API key de Gemini. El chat usará respuestas de fallback.');
    }
  },

  // ── Verificar estado del backend ───────────────────────────────
  async _checkBackendStatus(backendUrl) {
    try {
      const health = await GeminiAPI.checkBackendHealth();

      if (!health) {
        console.warn('[Helena] Backend Python no responde en', backendUrl);
        this._updateStatusUI({ backend: false, langsmith: false });
        return;
      }

      const langsmithActive = health?.components?.langsmith?.active === true;

      console.log('[Helena] ✅ Backend Python conectado:', health.app);
      if (langsmithActive) {
        console.log('[Helena] 🔭 LangSmith activo:', health.components.langsmith.dashboard);
      }

      this._updateStatusUI({
        backend:   true,
        langsmith: langsmithActive,
        project:   health?.components?.langsmith?.project || '',
        dashboard: health?.components?.langsmith?.dashboard || '',
        faiss:     health?.components?.faiss_rag === true,
      });

    } catch (err) {
      console.warn('[Helena] Error verificando backend:', err.message);
      this._updateStatusUI({ backend: false, langsmith: false });
    }
  },

  // ── Actualizar indicador visual en el chat header ──────────────
  _updateStatusUI({ backend, langsmith, project = '', dashboard = '', faiss = false }) {
    const statusEl = document.getElementById('chat-agent-status');
    if (!statusEl) return;

    if (backend && langsmith) {
      statusEl.innerHTML = `
        <span class="status-dot status-active"></span>
        En línea · LangSmith activo
        ${dashboard ? `<a href="${dashboard}" target="_blank" rel="noopener" class="status-link" title="Ver trazas en LangSmith">🔭</a>` : ''}
      `;
      statusEl.className = 'chat-agent-status status-ok';
    } else if (backend) {
      statusEl.innerHTML = `<span class="status-dot status-active"></span> En línea · Backend Python`;
      statusEl.className = 'chat-agent-status status-ok';
    } else {
      const geminiOk = GeminiAPI.hasKey();
      if (geminiOk) {
        statusEl.innerHTML = `<span class="status-dot status-gemini"></span> Modo Gemini Directo`;
        statusEl.className = 'chat-agent-status status-gemini';
      } else {
        statusEl.innerHTML = `<span class="status-dot status-offline"></span> Modo offline`;
        statusEl.className = 'chat-agent-status status-offline';
      }
    }

    // Emitir evento para quien quiera escuchar
    if (typeof SessionState !== 'undefined') {
      SessionState.emit('backend:status', { backend, langsmith, project });
    }
  },
};

window.GeminiConfig = GeminiConfig;
