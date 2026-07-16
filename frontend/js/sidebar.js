// js/sidebar.js
const SIDEBAR_COLLAPSED_KEY = 'synapse-sidebar-collapsed';

const sidebarHTML = `
  <div class="sidebar-header">
    <div class="logo-container" title="Synapse Suite">
      <i class="fas fa-atom" style="color:white; font-size:1.4rem;"></i>
    </div>
    <h2>Synapse Suite</h2>
    <button id="themeBtn" class="btn-icon" type="button" onclick="toggleTheme()" style="margin-left:auto; background:transparent; border:none; color:var(--text-secondary); cursor:pointer;" title="Cambiar Tema">
      <i data-lucide="moon" id="themeIcon"></i>
    </button>
  </div>

  <button type="button" class="sidebar-collapse-btn" id="sidebarToggle" title="Colapsar menú (Ctrl+Alt+B)" aria-label="Colapsar menú" aria-expanded="true">
    <i class="fas fa-angles-left" id="sidebarToggleIcon" aria-hidden="true"></i>
    <span class="sidebar-collapse-label">Ocultar menú</span>
  </button>

  <nav class="sidebar-nav">
    <a href="index.html" class="nav-item" id="nav-home" title="Dashboard">
      <i class="fas fa-home"></i>
      <span>Dashboard</span>
    </a>
    <a href="modulo_caja.html" class="nav-item" id="nav-caja" title="Caja y ventas">
      <i class="fas fa-cash-register"></i>
      <span>Caja y ventas</span>
    </a>
    <a href="modulo_cxp.html" class="nav-item" id="nav-cxp" title="Cuentas por Pagar">
      <i class="fas fa-file-invoice-dollar"></i>
      <span>Cuentas por Pagar</span>
    </a>
    <a href="modulo_pedidos.html" class="nav-item" id="nav-pedidos" title="Pedidos &amp; Moléculas">
      <i class="fas fa-box-open"></i>
      <span>Pedidos &amp; Moléculas</span>
    </a>
    <a href="modulo_marcas.html" class="nav-item" id="nav-marcas" title="Revisión de Marcas">
      <i class="fas fa-tags" style="color: #a855f7;"></i>
      <span style="color: #a855f7; font-weight: 600;">Revisión de Marcas</span>
    </a>
  </nav>

  <div class="sidebar-user" style="margin-top:auto; padding-top:1.5rem; border-top:1px solid var(--border-subtle);">
    <div style="display:flex; align-items:center; gap:.75rem; color:var(--text-secondary); font-size:.9rem;">
      <i class="fas fa-user-circle" style="font-size:1.5rem;"></i>
      <div class="sidebar-user-meta" style="display:flex; flex-direction:column;">
         <span id="current-user-label" style="font-weight:600; color:#fff;">DARIO</span>
         <span style="font-size:0.75rem; color:var(--success);">Online - Admin</span>
      </div>
    </div>
  </div>
`;

function isSidebarCollapsedPreferred() {
    try {
        return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1';
    } catch (_) {
        return false;
    }
}

function setSidebarCollapsed(sidebar, collapsed) {
    if (!sidebar) return;
    collapsed = !!collapsed;
    sidebar.classList.toggle('collapsed', collapsed);
    try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? '1' : '0');
    } catch (_) { /* ignore */ }

    const toggle = document.getElementById('sidebarToggle');
    const icon = document.getElementById('sidebarToggleIcon');
    const label = toggle && toggle.querySelector('.sidebar-collapse-label');
    if (toggle) {
        toggle.title = collapsed ? 'Expandir menú (Ctrl+Alt+B)' : 'Colapsar menú (Ctrl+Alt+B)';
        toggle.setAttribute('aria-label', collapsed ? 'Expandir menú' : 'Colapsar menú');
        toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    }
    if (icon) {
        icon.className = collapsed ? 'fas fa-angles-right' : 'fas fa-angles-left';
    }
    if (label) {
        label.textContent = collapsed ? 'Menú' : 'Ocultar menú';
    }
}

function ensureSidebarCollapseStyles() {
    if (document.getElementById('synapse-sidebar-collapse-css')) return;
    const style = document.createElement('style');
    style.id = 'synapse-sidebar-collapse-css';
    style.textContent = `
      .sidebar { position: relative; transition: width .25s ease, min-width .25s ease, padding .25s ease; }
      .sidebar.collapsed { width: 64px !important; min-width: 64px !important; padding: 1.25rem .4rem !important; overflow: hidden; }
      .sidebar.collapsed .sidebar-header h2,
      .sidebar.collapsed #themeBtn,
      .sidebar.collapsed .logo-container,
      .sidebar.collapsed .nav-item span,
      .sidebar.collapsed .sidebar-user-meta { display: none !important; }
      .sidebar.collapsed .nav-item { justify-content: center; padding: .75rem; }
      .sidebar-collapse-btn {
        display: flex; align-items: center; gap: .6rem;
        width: 100%; margin: 0 0 1rem; padding: .55rem .75rem;
        background: var(--bg-dark, #0f1115); color: var(--text-primary, #f5f5f5);
        border: 1px solid var(--border-subtle, #2d313a); cursor: pointer;
        font-family: inherit; font-size: .85rem; font-weight: 500;
      }
      .sidebar-collapse-btn:hover { border-color: var(--border-focus, #4b5263); }
      .sidebar.collapsed .sidebar-collapse-btn { justify-content: center; padding: .65rem 0; gap: 0; }
      .sidebar.collapsed .sidebar-collapse-label { display: none; }
      .sidebar.collapsed .sidebar-header { justify-content: center; margin-bottom: .75rem; }
      .sidebar.collapsed .sidebar-user { display: flex; justify-content: center; }
      .sidebar.collapsed .sidebar-user > div { justify-content: center; gap: 0; }
    `;
    document.head.appendChild(style);
}

document.addEventListener('DOMContentLoaded', () => {
    const sidebarElement = document.getElementById('sidebar-container');
    if (!sidebarElement) return;

    ensureSidebarCollapseStyles();
    sidebarElement.innerHTML = sidebarHTML;

    const currentPath = window.location.pathname;
    if (currentPath.includes('modulo_caja')) document.getElementById('nav-caja')?.classList.add('active');
    else if (currentPath.includes('modulo_cxp')) document.getElementById('nav-cxp')?.classList.add('active');
    else if (currentPath.includes('modulo_pedidos')) document.getElementById('nav-pedidos')?.classList.add('active');
    else if (currentPath.includes('modulo_marcas')) document.getElementById('nav-marcas')?.classList.add('active');
    else document.getElementById('nav-home')?.classList.add('active');

    setSidebarCollapsed(sidebarElement, isSidebarCollapsedPreferred());

    document.getElementById('sidebarToggle')?.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        setSidebarCollapsed(sidebarElement, !sidebarElement.classList.contains('collapsed'));
    });

    if (typeof lucide !== 'undefined') lucide.createIcons();
});

document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.altKey && e.key.toLowerCase() === 'c') {
        e.preventDefault();
        window.location.href = 'modulo_caja.html';
        return;
    }
    // Ctrl+Alt+B — no choca con Firefox (Ctrl+B = favoritos)
    if (e.ctrlKey && e.altKey && e.key.toLowerCase() === 'b') {
        const sidebar = document.getElementById('sidebar-container');
        if (!sidebar) return;
        e.preventDefault();
        setSidebarCollapsed(sidebar, !sidebar.classList.contains('collapsed'));
    }
});
