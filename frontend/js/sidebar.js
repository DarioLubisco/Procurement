// js/sidebar.js

const sidebarHTML = `
  <div class="sidebar-header">
    <div class="logo-container">
      <i class="fas fa-atom" style="color:white; font-size:1.4rem;"></i>
    </div>
    <h2>Synapse Suite</h2>
    <button id="themeBtn" class="btn-icon" onclick="toggleTheme()" style="margin-left:auto; background:transparent; border:none; color:var(--text-secondary); cursor:pointer;" title="Cambiar Tema">
      <i data-lucide="moon" id="themeIcon"></i>
    </button>
    <button class="btn-icon" id="sidebarToggle" style="background:transparent; border:none; color:var(--text-secondary); cursor:pointer;" title="Colapsar menú">
      <i data-lucide="menu"></i>
    </button>
  </div>

  <nav class="sidebar-nav">
    <a href="index.html" class="nav-item" id="nav-home">
      <i class="fas fa-home"></i>
      <span>Dashboard</span>
    </a>
    <a href="modulo_caja.html" class="nav-item" id="nav-caja">
      <i class="fas fa-cash-register"></i>
      <span>Caja y ventas</span>
    </a>
    <a href="modulo_cxp.html" class="nav-item" id="nav-cxp">
      <i class="fas fa-file-invoice-dollar"></i>
      <span>Cuentas por Pagar</span>
    </a>
    <a href="modulo_pedidos.html" class="nav-item" id="nav-pedidos">
      <i class="fas fa-box-open"></i>
      <span>Pedidos & Moléculas</span>
    </a>
  </nav>

  <div style="margin-top:auto; padding-top:1.5rem; border-top:1px solid var(--border-subtle);">
    <div style="display:flex; align-items:center; gap:.75rem; color:var(--text-secondary); font-size:.9rem;">
      <i class="fas fa-user-circle" style="font-size:1.5rem;"></i>
      <div style="display:flex; flex-direction:column;">
         <span id="current-user-label" style="font-weight:600; color:#fff;">DARIO</span>
         <span style="font-size:0.75rem; color:var(--success);">Online - Admin</span>
      </div>
    </div>
  </div>
`;

document.addEventListener('DOMContentLoaded', () => {
    const sidebarElement = document.getElementById('sidebar-container');
    if (sidebarElement) {
        sidebarElement.innerHTML = sidebarHTML;
        // Marcar activo según la URL
        const currentPath = window.location.pathname;
        if (currentPath.includes('modulo_caja')) document.getElementById('nav-caja').classList.add('active');
        else if (currentPath.includes('modulo_cxp')) document.getElementById('nav-cxp').classList.add('active');
        else if (currentPath.includes('modulo_pedidos')) document.getElementById('nav-pedidos').classList.add('active');
        else document.getElementById('nav-home').classList.add('active');

        // Toggle Event
        document.getElementById('sidebarToggle').addEventListener('click', () => {
             document.querySelector('.sidebar').classList.toggle('collapsed');
        });
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    // Atajos de teclado Globales (Ej: Ctrl + Alt + C -> Calculadora)
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.altKey && e.key.toLowerCase() === 'c') {
            e.preventDefault();
            window.location.href = 'modulo_caja.html';
        }
    });
});
