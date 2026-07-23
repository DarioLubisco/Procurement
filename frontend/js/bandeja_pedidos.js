/**
 * Bandeja de pedidos — ADR-0030
 * Modal + hydrate Comparativa + CTAs aprobar/enviar/rechazar/clonar
 */
(function () {
    let bandejaTab = 'por_enviar';
    let bandejaMode = null; // { propuesta_id, revision, snapshot_hash, cod_prov, estado }

    function $(id) {
        return document.getElementById(id);
    }

    function showAlertSafe(msg, ok) {
        if (typeof showAlert === 'function') showAlert(msg, ok);
        else if (typeof window.showAlert === 'function') window.showAlert(msg, ok);
        else alert(msg);
    }

    function openBandejaModal(tab) {
        const modal = $('bandejaModal');
        if (!modal) return;
        if (tab) bandejaTab = tab;
        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
        setActiveTab(bandejaTab);
        loadBandeja();
        refreshBadges();
    }

    function closeBandejaModal() {
        const modal = $('bandejaModal');
        if (!modal) return;
        modal.classList.remove('active');
        modal.setAttribute('aria-hidden', 'true');
    }

    function setActiveTab(tab) {
        bandejaTab = tab;
        document.querySelectorAll('.bandeja-tab').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
    }

    async function refreshBadges() {
        try {
            const r = await fetch('/api/pedidos/bandeja/counts');
            const data = await r.json();
            if (!r.ok) return;
            const c = data.counts || {};
            const elSend = $('badgeBandejaEnviar');
            const elApr = $('badgeBandejaAprobar');
            const elSendSb = $('badgeBandejaEnviarSb');
            const elAprSb = $('badgeBandejaAprobarSb');
            const nE = c.por_enviar || 0;
            const nA = c.por_aprobar || 0;
            [elSend, elSendSb].forEach((el) => {
                if (!el) return;
                el.textContent = String(nE);
                el.style.display = nE ? 'inline-flex' : 'none';
            });
            [elApr, elAprSb].forEach((el) => {
                if (!el) return;
                el.textContent = String(nA);
                el.style.display = nA ? 'inline-flex' : 'none';
            });
        } catch (_) { /* ignore */ }
    }

    async function loadBandeja() {
        const host = $('bandejaList');
        if (!host) return;
        host.innerHTML = '<p style="color:var(--text-secondary);padding:1rem;">Cargando…</p>';
        try {
            const r = await fetch(`/api/pedidos/bandeja?tab=${encodeURIComponent(bandejaTab)}&limit=100`);
            const data = await r.json();
            if (!r.ok) throw new Error(data.detail || 'Error bandeja');
            if (data.counts) {
                const c = data.counts;
                const elSend = $('badgeBandejaEnviar');
                const elApr = $('badgeBandejaAprobar');
                if (elSend) {
                    elSend.textContent = String(c.por_enviar || 0);
                    elSend.style.display = c.por_enviar ? 'inline-flex' : 'none';
                }
                if (elApr) {
                    elApr.textContent = String(c.por_aprobar || 0);
                    elApr.style.display = c.por_aprobar ? 'inline-flex' : 'none';
                }
            }
            const items = data.items || [];
            if (!items.length) {
                host.innerHTML = '<p style="color:var(--text-secondary);padding:1rem;">Sin propuestas en esta pestaña.</p>';
                return;
            }
            host.innerHTML = items.map((it) => renderRow(it)).join('');
            host.querySelectorAll('[data-action]').forEach((btn) => {
                btn.addEventListener('click', onRowAction);
            });
        } catch (err) {
            host.innerHTML = `<p style="color:var(--danger);padding:1rem;">${err.message}</p>`;
        }
    }

    function renderRow(it) {
        const desv = it.desviaciones != null ? it.desviaciones : '—';
        const canEnviarLista = bandejaTab === 'por_enviar' && Number(desv) === 0;
        const isHist = bandejaTab === 'historial';
        const isApr = bandejaTab === 'por_aprobar';
        return `
        <div class="bandeja-row" data-id="${it.propuesta_id}">
          <div class="bandeja-row-main">
            <strong>#${it.propuesta_id}</strong>
            <span>${it.cod_prov || ''}</span>
            <span class="bandeja-pill">${it.estado || ''}</span>
            <span title="Desviaciones vs Sencillo">Δ ${desv}</span>
            <span style="color:var(--text-secondary);font-size:0.75rem;">${(it.fecha_generacion || '').slice(0, 19)}</span>
            <span style="margin-left:auto;font-size:0.8rem;">${it.total_lineas || 0} líns · ${it.monto_total_usd != null ? '$' + Number(it.monto_total_usd).toFixed(2) : '—'}</span>
          </div>
          <div class="bandeja-row-actions">
            <button type="button" class="btn btn-secondary btn-sm" data-action="analizar" data-id="${it.propuesta_id}">Analizar</button>
            <a class="btn btn-secondary btn-sm" href="/api/pedidos/bandeja/${it.propuesta_id}/pdf" target="_blank" rel="noopener">PDF</a>
            <button type="button" class="btn btn-secondary btn-sm" data-action="telegram" data-id="${it.propuesta_id}">Telegram</button>
            ${canEnviarLista ? `<button type="button" class="btn btn-primary btn-sm" data-action="enviar" data-id="${it.propuesta_id}">Enviar</button>` : ''}
            ${isApr ? `
              <button type="button" class="btn btn-secondary btn-sm" data-action="aprobar" data-id="${it.propuesta_id}">Aprobar sin enviar</button>
              <button type="button" class="btn btn-primary btn-sm" data-action="aprobar-enviar" data-id="${it.propuesta_id}">Aprobar y enviar</button>
              <button type="button" class="btn btn-secondary btn-sm" data-action="rechazar" data-id="${it.propuesta_id}" style="border-color:#ef4444;color:#ef4444;">Rechazar</button>
            ` : ''}
            ${isHist ? `<button type="button" class="btn btn-secondary btn-sm" data-action="clonar" data-id="${it.propuesta_id}">Clonar a borrador</button>` : ''}
            ${bandejaTab === 'por_enviar' && Number(desv) > 0 ? `<span style="font-size:0.72rem;color:var(--text-secondary);">Hay desvíos → Analizar</span>` : ''}
          </div>
        </div>`;
    }

    async function onRowAction(ev) {
        const btn = ev.currentTarget;
        const action = btn.dataset.action;
        const id = Number(btn.dataset.id);
        if (!id) return;
        try {
            if (action === 'analizar') await analizarPropuesta(id);
            else if (action === 'enviar') await enviarPropuesta(id);
            else if (action === 'aprobar') await aprobarPropuesta(id, false);
            else if (action === 'aprobar-enviar') await aprobarPropuesta(id, true);
            else if (action === 'rechazar') await rechazarPropuesta(id);
            else if (action === 'clonar') await clonarPropuesta(id);
            else if (action === 'telegram') await telegramNotify(id);
        } catch (err) {
            showAlertSafe(err.message || String(err), false);
        }
    }

    async function telegramNotify(id) {
        const r = await fetch(`/api/pedidos/bandeja/${id}/telegram-notify`, { method: 'POST' });
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Error Telegram');
        showAlertSafe(
            `Telegram enviado #${id} · callbacks ${data.callback_aprobar || ''} / ${data.callback_rechazar || ''}`,
            true
        );
    }

    async function analizarPropuesta(propuestaId) {
        // Dirty session guard
        if (window.lastGenerarResult && window.__bandejaDirtyConfirm !== false) {
            const hasLocal = (window.lastGenerarResult.pedido_propuesto || []).length > 0;
            if (hasLocal && !window.__bandejaMode) {
                const ok = confirm(
                    'Hay un Generar/Comparativa en pantalla. ¿Reemplazar con la propuesta de la bandeja?'
                );
                if (!ok) return;
            }
        }
        const r = await fetch(`/api/pedidos/bandeja/${propuestaId}/comparativa`);
        const data = await r.json();
        if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'No se pudo cargar Comparativa');

        bandejaMode = {
            propuesta_id: data.propuesta_id,
            revision: data.revision,
            snapshot_hash: data.snapshot_hash,
            cod_prov: data.cod_prov,
            estado: data.estado,
        };
        window.__bandejaMode = bandejaMode;

        const payload = {
            comparativa_cantidades: data.comparativa_cantidades || [],
            pedido_propuesto: data.pedido_propuesto || [],
            meta: { phase: 'Bandeja', propuesta_id: propuestaId, cod_prov: data.cod_prov },
        };

        if (typeof window.stashGenerarResult === 'function') {
            window.stashGenerarResult(payload, { resetVm: true });
        } else if (typeof stashGenerarResult === 'function') {
            stashGenerarResult(payload, { resetVm: true });
        } else {
            // fallback: set globals used by render
            window.lastGenerarResult = payload;
            const sec = $('generarResultSection');
            if (sec) sec.style.display = 'block';
            if (typeof renderGenerarTables === 'function') renderGenerarTables(payload);
        }

        updateBandejaPersistBar(true);
        closeBandejaModal();
        showAlertSafe(
            `Bandeja #${propuestaId} (${data.cod_prov}) cargada · Δ desvíos: ${data.desviaciones || 0}. Edite qtys y Guarde cambios.`,
            true
        );
        $('generarResultSection')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function updateBandejaPersistBar(active) {
        const hint = $('pedidoPersistHint');
        const btnSave = $('btnGuardarBorrador');
        const btnEnviar = $('btnEnviarPedido');
        const btnSaveBandeja = $('btnGuardarCambiosBandeja');
        if (btnSaveBandeja) btnSaveBandeja.style.display = active ? 'inline-flex' : 'none';
        if (!active || !bandejaMode) {
            if (hint && !bandejaMode) return;
            return;
        }
        if (hint) {
            hint.innerHTML =
                `Modo bandeja <strong>#${bandejaMode.propuesta_id}</strong> ${bandejaMode.cod_prov} · rev ${bandejaMode.revision}. ` +
                `<strong>Guardar cambios</strong> persiste qtys. Enviar / Aprobar según estado.`;
        }
        if (btnSave) {
            btnSave.disabled = true;
            btnSave.title = 'Use Guardar cambios (modo bandeja)';
        }
        if (btnEnviar) {
            btnEnviar.style.opacity = '1';
            btnEnviar.disabled = false;
            btnEnviar.title = 'Enviar esta PropuestaID (0 desvíos o tras revisar)';
        }
    }

    async function guardarCambiosBandeja() {
        if (!bandejaMode) {
            showAlertSafe('No hay propuesta de bandeja cargada.', false);
            return;
        }
        const propuesto = (window.lastGenerarResult && window.lastGenerarResult.pedido_propuesto) || [];
        const comparativa = (window.lastGenerarResult && window.lastGenerarResult.comparativa_cantidades) || [];
        const r = await fetch(`/api/pedidos/bandeja/${bandejaMode.propuesta_id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pedido_propuesto: propuesto,
                comparativa_cantidades: comparativa,
            }),
        });
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data));
        bandejaMode.revision = data.revision;
        bandejaMode.snapshot_hash = data.snapshot_hash;
        window.__bandejaMode = bandejaMode;
        updateBandejaPersistBar(true);
        showAlertSafe(
            `Cambios guardados #${data.propuesta_id} · rev ${data.revision} · Δ ${data.desviaciones}`,
            true
        );
        refreshBadges();
    }

    async function enviarPropuesta(id) {
        const r = await fetch(`/api/pedidos/bandeja/${id}/enviar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        const data = await r.json().catch(() => ({}));
        if (!r.ok) {
            const d = data.detail;
            if (d && d.error === 'requiere_analizar') {
                throw new Error(d.message || 'Hay desvíos: Analizar primero');
            }
            throw new Error(typeof d === 'string' ? d : (d && d.message) || 'Error al enviar');
        }
        showAlertSafe(data.aviso || `Enviando #${id}`, true);
        loadBandeja();
        refreshBadges();
    }

    async function aprobarPropuesta(id, enviar) {
        const r = await fetch(`/api/pedidos/bandeja/${id}/aprobar?enviar=${enviar ? 'true' : 'false'}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Error al aprobar');
        showAlertSafe(
            enviar
                ? (data.aviso || `Aprobado y en envío #${id}`)
                : `Aprobado sin enviar → BORRADOR #${id}`,
            true
        );
        loadBandeja();
        refreshBadges();
    }

    async function rechazarPropuesta(id) {
        const motivo = prompt('Motivo de rechazo (obligatorio):');
        if (motivo == null) return;
        if (!String(motivo).trim()) {
            showAlertSafe('Motivo obligatorio.', false);
            return;
        }
        const r = await fetch(`/api/pedidos/bandeja/${id}/rechazar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ motivo: String(motivo).trim() }),
        });
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Error al rechazar');
        showAlertSafe(`Rechazado #${id}`, true);
        loadBandeja();
        refreshBadges();
    }

    async function clonarPropuesta(id) {
        const r = await fetch(`/api/pedidos/bandeja/${id}/clonar`, { method: 'POST' });
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Error al clonar');
        showAlertSafe(`Clonado → nuevo borrador #${data.propuesta_id} (${data.cod_prov})`, true);
        bandejaTab = 'por_enviar';
        setActiveTab(bandejaTab);
        loadBandeja();
        refreshBadges();
    }

    function wireUi() {
        $('btnOpenBandeja')?.addEventListener('click', () => openBandejaModal(bandejaTab));
        $('btnCloseBandeja')?.addEventListener('click', closeBandejaModal);
        $('bandejaModal')?.addEventListener('click', (e) => {
            if (e.target.id === 'bandejaModal') closeBandejaModal();
        });
        document.querySelectorAll('.bandeja-tab').forEach((btn) => {
            btn.addEventListener('click', () => {
                setActiveTab(btn.dataset.tab);
                loadBandeja();
            });
        });
        $('btnGuardarCambiosBandeja')?.addEventListener('click', async () => {
            try {
                await guardarCambiosBandeja();
            } catch (err) {
                showAlertSafe(err.message, false);
            }
        });

        // Deep link
        const params = new URLSearchParams(window.location.search);
        if (params.get('bandeja') === '1' || window.location.hash === '#bandeja') {
            openBandejaModal('por_enviar');
        }

        // Sidebar link (may be injected after)
        document.addEventListener('click', (e) => {
            const a = e.target.closest('#nav-bandeja, [data-open-bandeja]');
            if (!a) return;
            if (a.getAttribute('href') && a.getAttribute('href').includes('bandeja=1')) {
                if (window.location.pathname.includes('modulo_pedidos')) {
                    e.preventDefault();
                    openBandejaModal('por_enviar');
                }
            }
        });

        refreshBadges();
        setInterval(refreshBadges, 60000);
    }

    // Expose stash hook: app_pedidos may assign later
    window.openBandejaPedidos = openBandejaModal;
    window.refreshBandejaBadges = refreshBadges;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', wireUi);
    } else {
        wireUi();
    }
})();
