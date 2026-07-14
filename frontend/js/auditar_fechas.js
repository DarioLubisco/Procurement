// --- AUDITAR FECHAS INVERTIDAS ---
window.auditoriaFechasList = [];

window.abrirModalAuditarFechas = function() {
    if (!window.currentData || window.currentData.length === 0) {
        if(window.showToast) showToast("No hay datos cargados para analizar.", "warning");
        return;
    }

    window.auditoriaFechasList = window.currentData.filter(item => {
        if (!item.FechaE || !item.FechaI) return false;
        const fe = new Date(item.FechaE);
        const fi = new Date(item.FechaI);
        return fe > fi;
    });

    if (window.auditoriaFechasList.length === 0) {
        if(window.showToast) showToast("No se encontraron facturas con Fecha Emisión > Fecha Ingreso.", "success");
        return;
    }

    renderAuditoriaFechasTable();
    forceShowModal(document.getElementById('auditarFechasModal'));
};

window.closeModalAuditarFechas = function() {
    forceHideModal(document.getElementById('auditarFechasModal'));
};

function auditarFormatDate(dateString) {
    if (!dateString) return '-';
    if (dateString.includes('T')) dateString = dateString.split('T')[0];
    const parts = dateString.split('-');
    if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
    return dateString;
}

function renderAuditoriaFechasTable() {
    const tbody = document.getElementById('auditarFechasTbody');
    if(!tbody) return;
    tbody.innerHTML = '';
    
    window.auditoriaFechasList.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid var(--border-color)';
        
        const montoStr = Number(item.MontoUsd || 0).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
        
        tr.innerHTML = `
            <td style="padding: 0.5rem; text-align: center;">
                <input type="checkbox" class="auditar-checkbox" data-index="${index}" style="width: 16px; height: 16px; cursor: pointer;">
            </td>
            <td style="padding: 0.5rem;">${item.Descrip || item.CodProv}</td>
            <td style="padding: 0.5rem; font-weight: 600;">${item.NumeroD}</td>
            <td style="padding: 0.5rem; text-align: center; color: var(--error);">${auditarFormatDate(item.FechaE)}</td>
            <td style="padding: 0.5rem; text-align: center; color: var(--success);">${auditarFormatDate(item.FechaI)}</td>
            <td style="padding: 0.5rem; text-align: right; font-weight: bold;">$ ${montoStr}</td>
        `;
        tbody.appendChild(tr);
    });
}

window.auditarSeleccionarTodos = function() {
    document.querySelectorAll('.auditar-checkbox').forEach(cb => cb.checked = true);
};

window.auditarSeleccionarNinguno = function() {
    document.querySelectorAll('.auditar-checkbox').forEach(cb => cb.checked = false);
};

window.auditarInvertirSeleccion = function() {
    document.querySelectorAll('.auditar-checkbox').forEach(cb => cb.checked = !cb.checked);
};

window.procesarAuditoriaFechas = async function() {
    const checkboxes = document.querySelectorAll('.auditar-checkbox:checked');
    if (checkboxes.length === 0) {
        if(window.showToast) showToast("Selecciona al menos una factura para procesar.", "warning");
        return;
    }

    const facturas = [];
    checkboxes.forEach(cb => {
        const item = window.auditoriaFechasList[cb.dataset.index];
        facturas.push({
            NumeroD: item.NumeroD,
            CodProv: item.CodProv
        });
    });

    if (!confirm(`¿Estás seguro de intercambiar FechaE y FechaI para ${facturas.length} facturas?`)) {
        return;
    }

    try {
        const res = await fetch('/api/cxp/admin/reparar-fechas-batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ facturas })
        });
        const data = await res.json();

        if (res.ok) {
            if(window.showToast) showToast(data.message || "Fechas corregidas con éxito", "success");
            window.closeModalAuditarFechas();
            const btnRefresh = document.getElementById('refreshBtn');
            if(btnRefresh) btnRefresh.click();
        } else {
            if(window.showToast) showToast(data.detail || "Error al procesar fechas", "error");
        }
    } catch (err) {
        console.error(err);
        if(window.showToast) showToast("Error de conexión.", "error");
    }
};
