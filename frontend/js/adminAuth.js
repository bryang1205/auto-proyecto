/* ── AdminAuth — Sistema de Autenticación para Panel Helena ─── */

const AdminAuth = (() => {
  const TOKEN_KEY    = 'helena_admin_token';
  const SESSION_KEY  = 'helena_admin_session';
  const CREDENTIALS  = { user: 'admin', pass: 'helena2026' };
  const TOKEN_TTL_MS = 8 * 60 * 60 * 1000; // 8 horas

  // ── Generar token de sesión ───────────────────────────────
  function _generateToken() {
    const rand = () => Math.random().toString(36).substr(2, 9).toUpperCase();
    return `HLN-${rand()}-${Date.now().toString(36).toUpperCase()}-${rand()}`;
  }

  // ── Verificar si el token es válido ──────────────────────
  function isAuthenticated() {
    try {
      const stored = localStorage.getItem(TOKEN_KEY);
      if (!stored) return false;
      const session = JSON.parse(stored);
      if (!session || !session.token || !session.ts) return false;
      if (Date.now() - session.ts > TOKEN_TTL_MS) {
        logout(); // Token expirado
        return false;
      }
      return true;
    } catch (e) {
      return false;
    }
  }

  // ── Login ─────────────────────────────────────────────────
  function login(username, password) {
    if (username === CREDENTIALS.user && password === CREDENTIALS.pass) {
      const session = { token: _generateToken(), ts: Date.now(), user: username };
      localStorage.setItem(TOKEN_KEY, JSON.stringify(session));
      return { success: true };
    }
    return { success: false, error: 'Credenciales incorrectas. Verifica usuario y contraseña.' };
  }

  // ── Logout ────────────────────────────────────────────────
  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    window.location.href = 'admin.html';
  }

  // ── Obtener nombre del usuario activo ─────────────────────
  function getUser() {
    try {
      const stored = localStorage.getItem(TOKEN_KEY);
      if (!stored) return null;
      const session = JSON.parse(stored);
      return session.user || null;
    } catch (e) { return null; }
  }

  // ── Proteger la página: redirige si no hay sesión ─────────
  function requireAuth() {
    if (!isAuthenticated()) {
      _showLoginOverlay();
    } else {
      _hideLoginOverlay();
    }
  }

  // ── Mostrar overlay de login ──────────────────────────────
  function _showLoginOverlay() {
    const overlay = document.getElementById('admin-login-overlay');
    const content = document.getElementById('admin-main-content');
    if (overlay) overlay.style.display = 'flex';
    if (content) content.style.display = 'none';
  }

  // ── Ocultar overlay y mostrar panel ──────────────────────
  function _hideLoginOverlay() {
    const overlay = document.getElementById('admin-login-overlay');
    const content = document.getElementById('admin-main-content');
    if (overlay) overlay.style.display = 'none';
    if (content) content.style.display = 'block';
    // Actualizar info del usuario en la navbar
    const userEl = document.getElementById('admin-user-badge');
    if (userEl) userEl.textContent = `👤 ${getUser() || 'admin'}`;
  }

  // ── Manejar formulario de login ───────────────────────────
  function handleLoginForm() {
    const form = document.getElementById('login-form');
    if (!form) return;

    form.addEventListener('submit', e => {
      e.preventDefault();
      const username = document.getElementById('login-username')?.value?.trim();
      const password = document.getElementById('login-password')?.value;
      const errorEl  = document.getElementById('login-error');
      const btn      = document.getElementById('login-btn');

      if (!username || !password) {
        if (errorEl) errorEl.textContent = 'Completa todos los campos.';
        return;
      }

      // Efecto de carga
      btn.disabled = true;
      btn.textContent = 'Verificando...';
      if (errorEl) errorEl.textContent = '';

      setTimeout(() => {
        const result = login(username, password);
        if (result.success) {
          btn.textContent = '✅ ¡Bienvenido!';
          // Animación de éxito
          const overlay = document.getElementById('admin-login-overlay');
          if (overlay) {
            overlay.style.animation = 'loginFadeOut 0.5s ease forwards';
          }
          setTimeout(() => {
            _hideLoginOverlay();
            if (typeof loadAdminData === 'function') loadAdminData();
          }, 500);
        } else {
          btn.disabled = false;
          btn.textContent = '🔐 Ingresar al Panel';
          if (errorEl) {
            errorEl.textContent = result.error;
            // Shake animation
            const loginCard = document.getElementById('login-card');
            if (loginCard) {
              loginCard.style.animation = 'loginShake 0.4s ease';
              setTimeout(() => loginCard.style.animation = '', 400);
            }
          }
        }
      }, 800); // Simular validación
    });
  }

  // ── Init ──────────────────────────────────────────────────
  function init() {
    requireAuth();
    handleLoginForm();

    // Botón de logout
    const logoutBtn = document.getElementById('admin-logout-btn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => {
        if (confirm('¿Deseas cerrar sesión del panel de administración?')) {
          logout();
        }
      });
    }
  }

  return { init, isAuthenticated, login, logout, getUser, requireAuth };
})();

window.AdminAuth = AdminAuth;
