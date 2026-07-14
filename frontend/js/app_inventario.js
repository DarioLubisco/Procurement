document.addEventListener('DOMContentLoaded', () => {
    loadStatus();
    loadFrescuraETL();
    loadVencimientos();
});

async function loadStatus() {
    try {
        const res = await fetch('/inventario/status');
        const data = await res.json();
        
        document.getElementById('kpi-total').textContent = data.total_items.toLocaleString();
        document.getElementById('kpi-criticos').textContent = data.items_criticos.toLocaleString();
        document.getElementById('kpi-proximos').textContent = data.items_proximos.toLocaleString();
        
        const calidad = data.indice_calidad;
        document.getElementById('kpi-calidad').textContent = calidad.toFixed(1) + '%';
        
        const cardCalidad = document.getElementById('card-calidad');
        if(calidad >= 90) {
            cardCalidad.classList.add('good');
            document.getElementById('kpi-calidad').style.color = 'var(--success)';
        } else if(calidad >= 75) {
            cardCalidad.classList.add('warning');
            document.getElementById('kpi-calidad').style.color = 'var(--warning)';
        } else {
            cardCalidad.classList.add('critical');
            document.getElementById('kpi-calidad').style.color = 'var(--danger)';
        }
    } catch(e) {
        console.error("Error loading status:", e);
    }
}

async function loadVencimientos() {
    try {
        const res = await fetch('/inventario/vencimientos');
        const json = await res.json();
        const tbody = document.getElementById('vencimientosBody');
        tbody.innerHTML = '';
        
        if (!json.data || json.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 2rem; color: var(--text-secondary);">No hay vencimientos en los próximos 180 días. ¡Excelente!</td></tr>';
            return;
        }

        json.data.forEach(item => {
            const tr = document.createElement('tr');
            
            let daysBadge = '';
            if (item.dias_para_vencer < 0) {
                daysBadge = `<span class="badge-critical">Vencido (${Math.abs(item.dias_para_vencer)}d)</span>`;
            } else if (item.dias_para_vencer <= 30) {
                daysBadge = `<span class="badge-critical">${item.dias_para_vencer} días</span>`;
            } else if (item.dias_para_vencer <= 90) {
                daysBadge = `<span class="badge-warning">${item.dias_para_vencer} días</span>`;
            } else {
                daysBadge = `<span>${item.dias_para_vencer} días</span>`;
            }

            tr.innerHTML = `
                <td style="font-family: monospace; font-size: 0.9em; color: var(--text-secondary);">${item.codigo}</td>
                <td style="font-weight: 500;">${item.producto}</td>
                <td style="color: var(--text-secondary);">${item.lote}</td>
                <td>${item.fecha_vencimiento}</td>
                <td>${daysBadge}</td>
                <td style="font-weight: 600;">${item.stock}</td>
                <td style="color: var(--success);">$${item.precio.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });

    } catch(e) {
        console.error("Error loading vencimientos:", e);
        document.getElementById('vencimientosBody').innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: var(--danger);"><i class="fas fa-exclamation-triangle"></i> Error de conexión con el backend.</td></tr>`;
    }
}

async function loadFrescuraETL() {
    try {
        const res = await fetch('/inventario/frescura-etl');
        const json = await res.json();
        const tbody = document.getElementById('etlFrescuraBody');
        tbody.innerHTML = '';
        
        if (!json.data || json.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 2rem; color: var(--text-secondary);">No hay datos de ETL configurados.</td></tr>';
            return;
        }

        json.data.forEach(item => {
            const tr = document.createElement('tr');
            
            let statusBadge = '';
            if (item.estado_semaforo.startsWith('ROJO')) {
                statusBadge = `<span class="badge-critical"><i class="fas fa-times-circle"></i> ${item.estado_semaforo}</span>`;
            } else if (item.estado_semaforo.startsWith('NARANJA')) {
                statusBadge = `<span class="badge-warning"><i class="fas fa-exclamation-triangle"></i> ${item.estado_semaforo}</span>`;
            } else if (item.estado_semaforo.startsWith('VERDE')) {
                statusBadge = `<span style="background: rgba(16, 185, 129, 0.1); color: var(--success); padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600;"><i class="fas fa-check-circle"></i> ${item.estado_semaforo}</span>`;
            } else {
                statusBadge = `<span style="color: var(--text-secondary);">${item.estado_semaforo}</span>`;
            }

            let horasText = item.horas_transcurridas >= 0 ? `${item.horas_transcurridas.toFixed(1)} horas` : 'N/A';

            tr.innerHTML = `
                <td style="font-weight: 600; text-transform: uppercase;">${item.proveedor}</td>
                <td><span style="background: var(--bg-body); padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem; border: 1px solid var(--border-subtle);">${item.protocolo}</span></td>
                <td style="color: var(--text-secondary);">${item.ultima_actualizacion}</td>
                <td style="font-family: monospace;">${horasText}</td>
                <td>${statusBadge}</td>
            `;
            tbody.appendChild(tr);
        });

    } catch(e) {
        console.error("Error loading frescura ETL:", e);
        document.getElementById('etlFrescuraBody').innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 2rem; color: var(--danger);"><i class="fas fa-exclamation-triangle"></i> Error de conexión con el backend.</td></tr>`;
    }
}
