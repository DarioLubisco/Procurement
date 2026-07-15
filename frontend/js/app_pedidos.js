document.addEventListener('DOMContentLoaded', () => {
    // Basic Elements
    const fileInput = document.getElementById('subtractionFiles');
    const dropArea = document.getElementById('dropArea');
    const fileListContainer = document.getElementById('fileListContainer');

    const form = document.getElementById('generateForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const alertBox = document.getElementById('alertBox');

    // Category Elements
    const categoriesList = document.getElementById('categoriesList');
    const categoryCount = document.getElementById('categoryCount');
    const categorySearch = document.getElementById('categorySearch');
    const btnSelectAll = document.getElementById('btnSelectAll');
    const btnSelectNone = document.getElementById('btnSelectNone');

    let selectedFiles = []; // Array to store files
    let categoryMap = {};
    let categoryTree = [];
    let lastGenerarResult = null;
    let vmIntentosRecalc = {};
    let vmActivoProveedor = null;
    let vmPanelAck = false;
    // ADR-0018: Guardar borrador only after Regenerar Definitivo; clear on Sencillo
    let definitivoReadyForBorrador = false;
    let lastDefinitivoParams = null;

    function setDefinitivoReadyForBorrador(ready) {
        definitivoReadyForBorrador = !!ready;
        const btn = document.getElementById('btnGuardarBorrador');
        if (btn) {
            btn.disabled = !definitivoReadyForBorrador;
            btn.title = definitivoReadyForBorrador
                ? 'Guardar Pedido Definitivo en BorradorPedidos'
                : 'Disponible tras Regenerar Definitivo';
        }
        if (!definitivoReadyForBorrador) {
            lastDefinitivoParams = null;
        }
    }

    function buildDefinitivoParamsSnapshot(requestPayload, responseData) {
        const meta = (responseData && responseData.meta) || {};
        return {
            nivel: requestPayload.nivel || meta.nivel || null,
            base_preset: requestPayload.base_preset || meta.base_preset || null,
            cobertura: requestPayload.cobertura ?? meta.cobertura ?? null,
            criterios_agrupacion: requestPayload.criterios_agrupacion || meta.criterios_agrupacion_efectivos || [],
            categorias: requestPayload.categorias || null,
            include_generics: requestPayload.include_generics,
            include_brands: requestPayload.include_brands,
            umbral_rotacion: requestPayload.umbral_rotacion,
            num_rows: requestPayload.num_rows,
            presupuesto_maximo: requestPayload.presupuesto_maximo ?? null,
            overrides: requestPayload.overrides || {},
            overrides_applied: meta.overrides_applied || [],
            phase: meta.phase || 'PedidoDefinitivo',
        };
    }

    // --- CONFIG DEFAULTS LOGIC ---
    const btnSaveDefaults = document.getElementById('btnSaveDefaults');
    const inputDays = document.getElementById('pedidoDays');
    const inputRows = document.getElementById('numRows');
    const inputUmbral = document.getElementById('umbralRotacion');

    function loadDefaults() {
        const d_days = localStorage.getItem('syn_ped_days');
        const d_rows = localStorage.getItem('syn_ped_rows');
        const d_umbral = localStorage.getItem('syn_ped_umbral');
        
        if (d_days) inputDays.value = d_days;
        if (d_rows) inputRows.value = d_rows;
        if (d_umbral) inputUmbral.value = d_umbral;
    }
    
    if (btnSaveDefaults) {
        btnSaveDefaults.addEventListener('click', () => {
            localStorage.setItem('syn_ped_days', inputDays.value);
            localStorage.setItem('syn_ped_rows', inputRows.value);
            localStorage.setItem('syn_ped_umbral', inputUmbral.value);
            btnSaveDefaults.innerHTML = '<i class="fas fa-check"></i> Guardado';
            btnSaveDefaults.classList.remove('btn-secondary');
            btnSaveDefaults.classList.add('btn-primary');
            setTimeout(() => {
                btnSaveDefaults.innerHTML = '<i class="fas fa-save"></i> Guardar por Defecto';
                btnSaveDefaults.classList.remove('btn-primary');
                btnSaveDefaults.classList.add('btn-secondary');
            }, 2000);
        });
    }

    loadDefaults();

    // --- CATEGORY LOGIC ---
    async function fetchCategories() {
        try {
            const response = await fetch('/api/pedidos/categories');
            if (!response.ok) throw new Error("Fallo al obtener categorías");
            const data = await response.json();

            const rawCategories = data.categories || [];
            categoryMap = {};
            rawCategories.forEach(cat => {
                categoryMap[cat.id] = {
                    id: cat.id, name: cat.name, parentId: cat.parentId,
                    selected: true, indeterminate: false, children: [], visible: true
                };
            });

            categoryTree = [];
            Object.values(categoryMap).forEach(cat => {
                if (cat.parentId === "0" || !categoryMap[cat.parentId]) {
                    categoryTree.push(cat);
                } else {
                    categoryMap[cat.parentId].children.push(cat);
                }
            });

            renderCategories();
        } catch (error) {
            console.error(error);
            if (categoriesList) {
                categoriesList.innerHTML = `<li style="color:var(--danger); padding:1rem;">Error cargando categorías. Revisa la conexión al motor SQL.</li>`;
            }
        }
    }

    function renderCategories() {
        if (!categoriesList) return;
        categoriesList.innerHTML = '';
        let visibleCount = 0;

        function buildNodeDOM(node) {
            if (!node.visible) return null;
            visibleCount++;

            const li = document.createElement('li');
            li.style.listStyle = 'none';
            const hasChildren = node.children.some(c => c.visible);

            const row = document.createElement('div');
            row.style.display = 'flex';
            row.style.alignItems = 'center';
            row.style.gap = '0.5rem';
            row.style.padding = '0.25rem 0';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `cat_${node.id}`;
            checkbox.value = node.name;
            checkbox.checked = node.selected;
            checkbox.indeterminate = node.indeterminate;
            checkbox.addEventListener('change', (e) => handleCheckboxChange(node.id, e.target.checked));
            
            const label = document.createElement('label');
            label.htmlFor = `cat_${node.id}`;
            label.textContent = node.name;
            if(hasChildren) label.style.fontWeight = 'bold';

            row.appendChild(checkbox);
            row.appendChild(label);
            li.appendChild(row);

            if (hasChildren) {
                const ul = document.createElement('ul');
                ul.style.paddingLeft = '1.5rem';
                node.children.forEach(child => {
                    const childDOM = buildNodeDOM(child);
                    if (childDOM) ul.appendChild(childDOM);
                });
                li.appendChild(ul);
            }
            return li;
        }

        categoryTree.forEach(rootNode => {
            const nodeDOM = buildNodeDOM(rootNode);
            if (nodeDOM) categoriesList.appendChild(nodeDOM);
        });

        if (visibleCount === 0) categoriesList.innerHTML = `<li style="padding:1rem;">No se encontraron categorías.</li>`;
        updateCategoryCount();
    }

    function handleCheckboxChange(id, isChecked) {
        const node = categoryMap[id];
        if (!node) return;
        node.selected = isChecked;
        node.indeterminate = false;

        function updateChildren(n, checkState) {
            n.children.forEach(child => {
                child.selected = checkState;
                child.indeterminate = false;
                const cb = document.getElementById(`cat_${child.id}`);
                if (cb) { cb.checked = checkState; cb.indeterminate = false; }
                updateChildren(child, checkState);
            });
        }
        updateChildren(node, isChecked);
        updateParentState(node.parentId);
        updateCategoryCount();
    }

    function updateParentState(parentId) {
        if (!parentId || parentId === "0") return;
        const parent = categoryMap[parentId];
        if (!parent) return;

        let allSelected = true, noneSelected = true, hasIndeterminate = false;
        parent.children.forEach(child => {
            if (child.selected) noneSelected = false;
            else allSelected = false;
            if (child.indeterminate) hasIndeterminate = true;
        });

        if (allSelected && !hasIndeterminate) { parent.selected = true; parent.indeterminate = false; }
        else if (noneSelected && !hasIndeterminate) { parent.selected = false; parent.indeterminate = false; }
        else { parent.selected = false; parent.indeterminate = true; }

        const cb = document.getElementById(`cat_${parent.id}`);
        if (cb) { cb.checked = parent.selected; cb.indeterminate = parent.indeterminate; }
        updateParentState(parent.parentId);
    }

    function applySearch(filterText) {
        const lowerFilter = filterText.toLowerCase();
        Object.values(categoryMap).forEach(cat => cat.visible = cat.name.toLowerCase().includes(lowerFilter));
        
        function ensureParentVisibility(node) {
            let childIsVisible = false;
            node.children.forEach(child => { if (ensureParentVisibility(child)) childIsVisible = true; });
            if (childIsVisible) node.visible = true;
            return node.visible;
        }
        categoryTree.forEach(ensureParentVisibility);
        renderCategories();
    }

    function updateCategoryCount() {
        if (!categoryCount) return;
        const total = Object.keys(categoryMap).length;
        const checkedCount = Object.values(categoryMap).filter(c => c.selected).length;
        categoryCount.textContent = `${checkedCount} Seleccionadas`;
    }

    if (categorySearch) categorySearch.addEventListener('input', (e) => applySearch(e.target.value));
    if (btnSelectAll) btnSelectAll.addEventListener('click', () => {
        categoryTree.forEach(root => handleCheckboxChange(root.id, true));
    });
    if (btnSelectNone) btnSelectNone.addEventListener('click', () => {
        categoryTree.forEach(root => handleCheckboxChange(root.id, false));
    });

    fetchCategories();

    // --- DRAG AND DROP FILE LOGIC ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        if (dropArea) dropArea.addEventListener(eventName, preventDefaults, false);
    });
    function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

    ['dragenter', 'dragover'].forEach(eventName => {
        if (dropArea) dropArea.addEventListener(eventName, () => dropArea.classList.add('dragover'), false);
    });
    ['dragleave', 'drop'].forEach(eventName => {
        if (dropArea) dropArea.addEventListener(eventName, () => dropArea.classList.remove('dragover'), false);
    });

    if (dropArea) {
        dropArea.addEventListener('drop', (e) => handleFiles(e.dataTransfer.files), false);
        dropArea.addEventListener('click', () => fileInput.click());
    }

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
            fileInput.value = '';
        });
    }

    function handleFiles(files) {
        let validFiles = [];
        Array.from(files).forEach(file => {
            if (file.name.endsWith('.xlsx')) {
                if (!selectedFiles.find(f => f.name === file.name)) validFiles.push(file);
            } else {
                showAlert(`"${file.name}" ignorado, debe ser .xlsx`, false);
            }
        });

        if (validFiles.length > 0) {
            selectedFiles = selectedFiles.concat(validFiles);
            hideAlert();
            renderFileList();
        }
    }

    window.removeFile = function(index) {
        selectedFiles.splice(index, 1);
        renderFileList();
    }

    function renderFileList() {
        if (!fileListContainer) return;
        fileListContainer.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            fileListContainer.innerHTML += `
                <div class="file-chip">
                    <span><i class="fas fa-file-excel"></i> ${file.name}</span>
                    <i class="fas fa-times remove-btn" onclick="removeFile(${index})"></i>
                </div>
            `;
        });
    }

    // --- FORM SUBMISSION (Generar Sencillo → Comparativa + Propuesto) ---
    function showAlert(msg, isSuccess) {
        if (alertBox) {
            alertBox.textContent = msg;
            alertBox.style.display = 'block';
            alertBox.className = `alert alert-${isSuccess ? 'success' : 'danger'}`;
            alertBox.style.backgroundColor = isSuccess ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)';
            alertBox.style.color = isSuccess ? '#10b981' : '#ef4444';
        }
    }
    function hideAlert() { if (alertBox) alertBox.style.display = 'none'; }

    function collectCriteriosAgrupacion() {
        return Array.from(document.querySelectorAll('.criterio-cb:checked')).map(cb => cb.value);
    }

    function buildSencilloPayload() {
        const selectedCategoryNames = Object.values(categoryMap)
            .filter(c => c.selected).map(c => c.name);
        const presupuestoRaw = document.getElementById('presupuestoMaximo')?.value;
        const presupuesto = presupuestoRaw !== undefined && presupuestoRaw !== ''
            ? Number(presupuestoRaw) : null;
        return {
            cobertura: Number(document.getElementById('pedidoDays').value),
            preset: document.getElementById('presetSencillo')?.value || 'Conservador',
            criterios_agrupacion: collectCriteriosAgrupacion(),
            categorias: selectedCategoryNames,
            include_generics: document.getElementById('includeGenerics')?.checked !== false,
            include_brands: document.getElementById('includeBrands')?.checked !== false,
            umbral_rotacion: Number(document.getElementById('umbralRotacion')?.value || 0),
            num_rows: Number(document.getElementById('numRows').value),
            presupuesto_maximo: presupuesto,
        };
    }

    function escapeHtml(s) {
        return String(s ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function factorsHoverText(factores) {
        if (!factores || !factores.length) return '';
        return factores.map(f => {
            const t = f.titulo || f.codigo || '';
            const d = f.detalle || '';
            return d ? `${t}: ${d}` : t;
        }).join('\n');
    }

    function renderFactoresAccordion(factores) {
        if (!factores || !factores.length) {
            return '<div style="padding:0.5rem 0.75rem; color:var(--text-secondary); font-size:0.8rem;">Sin factores de motor.</div>';
        }
        return '<ul style="margin:0; padding:0.5rem 0.75rem 0.75rem 1.25rem; font-size:0.8rem; line-height:1.4;">' +
            factores.map(f => {
                const t = escapeHtml(f.titulo || f.codigo || '');
                const d = escapeHtml(f.detalle || '');
                return `<li style="margin-bottom:0.35rem;"><strong>${t}</strong>${d ? ` — ${d}` : ''}</li>`;
            }).join('') +
            '</ul>';
    }

    function renderGenerarResult(data) {
        const section = document.getElementById('generarResultSection');
        const compBody = document.getElementById('comparativaTableBody');
        const propBody = document.getElementById('propuestoTableBody');
        if (!section || !compBody || !propBody) return;

        compBody.innerHTML = '';
        let openJustRow = null;
        (data.comparativa_cantidades || []).forEach((row, idx) => {
            const tr = document.createElement('tr');
            tr.className = 'comparativa-main-row';
            tr.dataset.justIdx = String(idx);
            const resumen = row.justificacion_delta || '';
            const factores = row.justificacion_factores || [];
            const hover = factorsHoverText(factores) || resumen;
            const hasDetail = factores.length > 0 || !!resumen;
            tr.innerHTML = `
                <td style="padding:0.5rem; font-family:monospace;">${escapeHtml(row.barra_baseline)}</td>
                <td style="padding:0.5rem;">${escapeHtml(row.desc_baseline || '')}</td>
                <td style="padding:0.5rem; text-align:right;">${row.qty_baseline}</td>
                <td style="padding:0.5rem; font-family:monospace;">${escapeHtml(row.barra_propuesto)}</td>
                <td style="padding:0.5rem;">${escapeHtml(row.desc_propuesto || '')}</td>
                <td style="padding:0.5rem; text-align:right;">${row.qty_propuesto}</td>
                <td class="justificacion-cell" style="padding:0.5rem; font-size:0.8rem; color:var(--text-secondary); max-width:220px; cursor:${hasDetail ? 'pointer' : 'default'};">
                    <span class="justificacion-resumen" style="display:inline-block; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; border-bottom:${hasDetail ? '1px dotted var(--text-secondary)' : 'none'};" title="${escapeHtml(hover)}">${escapeHtml(resumen) || '—'}</span>
                </td>
            `;
            const detailTr = document.createElement('tr');
            detailTr.className = 'comparativa-detail-row';
            detailTr.style.display = 'none';
            detailTr.innerHTML = `<td colspan="7" style="background:rgba(0,0,0,0.15); border-bottom:1px solid var(--border-subtle); padding:0;">${renderFactoresAccordion(factores)}</td>`;

            if (hasDetail) {
                tr.querySelector('.justificacion-cell').addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    const opening = detailTr.style.display === 'none';
                    if (openJustRow && openJustRow !== detailTr) {
                        openJustRow.style.display = 'none';
                    }
                    detailTr.style.display = opening ? 'table-row' : 'none';
                    openJustRow = opening ? detailTr : null;
                });
            }

            compBody.appendChild(tr);
            compBody.appendChild(detailTr);
        });

        propBody.innerHTML = '';
        (data.pedido_propuesto || []).forEach(line => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="padding:0.5rem; font-family:monospace;">${escapeHtml(line.barra)}</td>
                <td style="padding:0.5rem;">${escapeHtml(line.descripcion || '')}</td>
                <td style="padding:0.5rem; font-weight:600;">${escapeHtml(line.proveedor || '')}</td>
                <td style="padding:0.5rem; text-align:right;">${line.cantidad}</td>
            `;
            propBody.appendChild(tr);
        });

        section.style.display = 'block';
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function stashGenerarResult(data, { resetVm = true } = {}) {
        lastGenerarResult = data;
        if (resetVm) {
            vmIntentosRecalc = {};
            vmActivoProveedor = null;
            vmPanelAck = false;
            const vmPanel = document.getElementById('validarMinimosPanel');
            if (vmPanel) vmPanel.style.display = 'none';
        }
        renderGenerarResult(data);
    }

    function applyValidarMinimosResponse(data) {
        if (!lastGenerarResult) lastGenerarResult = {};
        lastGenerarResult.pedido_propuesto = data.pedido_propuesto;
        lastGenerarResult.comparativa_cantidades = data.comparativa_cantidades;
        if (data.pedido_baseline) lastGenerarResult.pedido_baseline = data.pedido_baseline;
        const vm = (data.meta && data.meta.validar_minimos) || {};
        vmIntentosRecalc = vm.intentos_recalc || vmIntentosRecalc;
        vmActivoProveedor = vm.activo || null;
        renderGenerarResult(lastGenerarResult);
        renderValidarMinimosUI(vm);
        if (vm.requiere_panel_antes_recalc) {
            vmPanelAck = true;
        }
    }

    function renderValidarMinimosUI(vm) {
        const panel = document.getElementById('validarMinimosPanel');
        const colaEl = document.getElementById('validarMinimosCola');
        const detEl = document.getElementById('validarMinimosDetalle');
        const hint = document.getElementById('validarMinimosHint');
        if (!panel || !colaEl || !detEl) return;
        panel.style.display = 'block';
        const cola = vm.cola || [];
        if (!cola.length) {
            colaEl.innerHTML = '<strong style="color:#10b981;">Todos los proveedores cumplen el mínimo (o no tienen mínimo configurado).</strong>';
            detEl.innerHTML = '';
            if (hint) hint.textContent = '';
            return;
        }
            colaEl.innerHTML = '<strong>Cola (mayor déficit primero):</strong><ul style="margin:0.4rem 0 0 1.2rem;">' +
            cola.map(d => {
                const id = d.proveedor_id != null ? `#${d.proveedor_id} ` : '';
                const label = d.nombre_corto || d.proveedor;
                return `<li>${id}<strong>${label}</strong> <code>${d.proveedor}</code> total $${d.total_usd} / mín $${d.minimo_usd} (déficit $${d.deficit_usd})</li>`;
            }).join('') +
            '</ul>';
        const p = vm.panel;
        if (p) {
            const idLabel = p.proveedor_id != null ? `#${p.proveedor_id} ` : '';
            const name = p.nombre_corto || p.proveedor;
            const aliases = (p.aliases || []).length
                ? ` <span style="color:var(--text-secondary);font-size:0.8em;">[${(p.aliases || []).join(', ')}]</span>`
                : '';
            const reps = (p.reemplazos || []).slice(0, 8).map(r =>
                `${r.barra_actual}→${r.proveedor_alt}/${r.barra_alternativa} (ahorro línea $${r.ahorro_usd})`
            ).join('<br>');
            const huerf = (p.huerfanos_si_rechaza || []).map(h => h.barra).join(', ') || 'ninguno';
            detEl.innerHTML = `
                <div><strong>Activo:</strong> ${idLabel}${name} <code>${p.proveedor}</code>${aliases} — total $${p.total_usd}, mín $${p.minimo_usd}, déficit $${p.deficit_usd}</div>
                <div><strong>Ahorro vs 2º (barra→Grupo):</strong> $${p.ahorro_vs_segundo_usd}</div>
                <div style="margin-top:0.4rem;"><strong>Reemplazos:</strong><br>${reps || '—'}</div>
                <div style="margin-top:0.4rem;"><strong>Huérfanos si rechaza:</strong> ${huerf}</div>
            `;
        } else {
            detEl.innerHTML = '';
        }
        if (hint) {
            hint.textContent = vm.requiere_panel_antes_recalc
                ? 'Tras el 1er recálculo debe revisar el panel (costo de rechazo / reemplazos) antes de otro %. Pulse Recalcular de nuevo para confirmar (panel_ack).'
                : 'Sugerencia: +50% cobertura solo en SKUs de este proveedor. Puede aceptar submínimo o rechazar.';
        }
        if (vm.requiere_panel_antes_recalc) {
            // User has seen panel; next recalc will send panel_ack=true once they click Recalcular again
            vmPanelAck = true;
        }
    }

    async function callValidarMinimos(action, extra = {}) {
        if (!lastGenerarResult) {
            showAlert('Primero ejecute Generar (Sencillo).', false);
            return;
        }
        const payload = {
            action,
            cobertura: Number(document.getElementById('pedidoDays').value),
            criterios_agrupacion: collectCriteriosAgrupacion(),
            pedido_propuesto: lastGenerarResult.pedido_propuesto || [],
            comparativa_cantidades: lastGenerarResult.comparativa_cantidades || [],
            pedido_baseline: lastGenerarResult.pedido_baseline || [],
            intentos_recalc: vmIntentosRecalc,
            proveedor: extra.proveedor || vmActivoProveedor,
            pct_extra: Number(document.getElementById('vmPctExtra')?.value || 50),
            panel_ack: !!extra.panel_ack || (action === 'recalcular' && vmPanelAck),
        };
        const response = await fetch('/api/pedidos/validar-minimos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Error en Validar mínimos');
        }
        const data = await response.json();
        applyValidarMinimosResponse(data);
        const vm = data.meta?.validar_minimos || {};
        if (action === 'evaluar' && !(vm.cola || []).length) {
            showAlert('Sin proveedores bajo mínimo.', true);
        } else if (action === 'recalcular' && vm.requiere_panel_antes_recalc && (lastGenerarResult.pedido_propuesto || []).length) {
            // if qty unchanged because ack required first time — message already in hint
            showAlert(`Validar mínimos: revise panel de ${vm.activo || ''}.`, true);
        } else {
            showAlert(`Validar mínimos (${action}) — cola: ${(vm.cola || []).length}`, true);
        }
    }

    document.getElementById('btnValidarMinimos')?.addEventListener('click', async () => {
        try {
            await callValidarMinimos('evaluar');
        } catch (e) {
            showAlert(e.message, false);
        }
    });
    document.getElementById('btnVmRecalcular')?.addEventListener('click', async () => {
        try {
            await callValidarMinimos('recalcular', { panel_ack: vmPanelAck });
        } catch (e) {
            showAlert(e.message, false);
        }
    });
    document.getElementById('btnVmAceptar')?.addEventListener('click', async () => {
        try {
            await callValidarMinimos('aceptar');
        } catch (e) {
            showAlert(e.message, false);
        }
    });
    document.getElementById('btnVmRechazar')?.addEventListener('click', async () => {
        try {
            await callValidarMinimos('rechazar');
        } catch (e) {
            showAlert(e.message, false);
        }
    });

    function collectDefinitivoOverrides() {
        const overrides = {};
        document.querySelectorAll('#definitivoOverridesHost [data-override-key]').forEach((el) => {
            const key = el.getAttribute('data-override-key');
            if (!key) return;
            const type = el.getAttribute('data-override-type') || 'number';
            if (type === 'boolean') {
                if (el.dataset.touched === '1' || el.checked) {
                    // only send if user checked or explicitly toggled; unchecked default = omit
                    if (el.dataset.touched === '1') overrides[key] = !!el.checked;
                }
                return;
            }
            const raw = (el.value || '').trim();
            if (raw === '') return;
            if (type === 'select') {
                overrides[key] = raw;
                return;
            }
            const num = Number(raw);
            if (!Number.isNaN(num)) overrides[key] = num;
        });
        return overrides;
    }

    function renderDefinitivoOverrideFields(schema) {
        const host = document.getElementById('definitivoOverridesHost');
        const note = document.getElementById('definitivoOverridesNote');
        if (!host) return;
        host.innerHTML = '';
        const fields = schema.fields || [];
        fields.forEach((field) => {
            const wrap = document.createElement('div');
            wrap.className = 'input-group';
            wrap.style.margin = '0';
            const labelRow = document.createElement('div');
            labelRow.style.display = 'flex';
            labelRow.style.alignItems = 'center';
            labelRow.style.gap = '0.35rem';
            labelRow.style.marginBottom = '0.25rem';
            const label = document.createElement('label');
            label.textContent = field.label || field.key;
            label.style.margin = '0';
            labelRow.appendChild(label);
            const helpText = field.help || field.hint || '';
            if (helpText) {
                const info = document.createElement('button');
                info.type = 'button';
                info.className = 'btn-icon';
                info.setAttribute('aria-label', 'Información');
                info.title = helpText;
                info.textContent = 'ⓘ';
                info.style.cssText = 'border:none;background:transparent;color:var(--text-secondary);cursor:help;font-size:0.85rem;padding:0;line-height:1;';
                labelRow.appendChild(info);
            }
            wrap.appendChild(labelRow);

            let input;
            if (field.type === 'boolean') {
                input = document.createElement('input');
                input.type = 'checkbox';
                input.style.height = '20px';
                input.style.width = '20px';
                input.style.marginTop = '10px';
                input.addEventListener('change', () => { input.dataset.touched = '1'; });
            } else if (field.type === 'select') {
                input = document.createElement('select');
                input.className = 'form-control';
                input.style.height = '40px';
                const blank = document.createElement('option');
                blank.value = '';
                blank.textContent = '(preset)';
                input.appendChild(blank);
                (field.options || []).forEach((opt) => {
                    const o = document.createElement('option');
                    o.value = opt;
                    o.textContent = opt;
                    input.appendChild(o);
                });
            } else {
                input = document.createElement('input');
                input.type = 'number';
                input.className = 'form-control';
                input.style.height = '40px';
                if (field.step) input.step = field.step;
                input.placeholder = '(preset)';
            }
            input.setAttribute('data-override-key', field.key);
            input.setAttribute('data-override-type', field.type || 'number');
            input.id = `ov_${field.key}`;
            wrap.appendChild(input);
            if (field.default != null && field.type === 'number') {
                input.placeholder = String(field.default);
            }
            host.appendChild(wrap);
        });
        if (note) {
            const dead = (schema.dead_keys_excluded || []).join(', ');
            note.textContent = schema.note
                || `Nivel ${schema.nivel}: ${fields.length} knobs vivos. Excluidos: ${dead || '—'}.`;
        }
    }

    async function loadDefinitivoOverrideSchema(attempt = 0) {
        const nivel = document.getElementById('nivelDefinitivo')?.value || 'Intermedio';
        try {
            const response = await fetch(`/api/pedidos/overrides-schema?nivel=${encodeURIComponent(nivel)}`);
            if (!response.ok) throw new Error(`schema HTTP ${response.status}`);
            const schema = await response.json();
            if (!schema.fields || !schema.fields.length) {
                throw new Error('schema sin fields');
            }
            renderDefinitivoOverrideFields(schema);
        } catch (err) {
            console.warn('overrides-schema unavailable', err);
            if (attempt < 2) {
                setTimeout(() => loadDefinitivoOverrideSchema(attempt + 1), 600 * (attempt + 1));
            }
        }
    }

    // Expose for smoke / debugging
    window.__loadDefinitivoOverrideSchema = loadDefinitivoOverrideSchema;

    const nivelDefinitivoEl = document.getElementById('nivelDefinitivo');
    if (nivelDefinitivoEl) {
        nivelDefinitivoEl.addEventListener('change', () => loadDefinitivoOverrideSchema(0));
        loadDefinitivoOverrideSchema(0);
    }

    const btnRegenerarDefinitivo = document.getElementById('btnRegenerarDefinitivo');
    if (btnRegenerarDefinitivo) {
        btnRegenerarDefinitivo.addEventListener('click', async () => {
            hideAlert();
            const resultSection = document.getElementById('generarResultSection');
            if (!resultSection || resultSection.style.display === 'none') {
                showAlert("Primero ejecute Generar (Sencillo) para ver la Comparativa.", false);
                return;
            }
            btnRegenerarDefinitivo.disabled = true;
            const original = btnRegenerarDefinitivo.innerHTML;
            btnRegenerarDefinitivo.innerHTML = '<div class="loader" style="width:20px; height:20px; border-width:2px;"></div> Regenerando Definitivo...';
            try {
                const base = buildSencilloPayload();
                const overrides = collectDefinitivoOverrides();
                const payload = {
                    ...base,
                    nivel: document.getElementById('nivelDefinitivo')?.value || 'Intermedio',
                    base_preset: document.getElementById('basePresetDefinitivo')?.value || 'Normal',
                    overrides,
                };
                delete payload.preset;
                const response = await fetch('/api/pedidos/regenerar-definitivo', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || "Error al regenerar Definitivo");
                }
                const data = await response.json();
                stashGenerarResult(data, { resetVm: true });
                lastDefinitivoParams = buildDefinitivoParamsSnapshot(payload, data);
                setDefinitivoReadyForBorrador(true);
                const applied = (data.meta?.overrides_applied || []).join(', ') || 'ninguno';
                showAlert(
                    `Pedido Definitivo regenerado (${data.meta?.nivel}). Overrides: ${applied}.`,
                    true
                );
            } catch (error) {
                showAlert(error.message, false);
            } finally {
                btnRegenerarDefinitivo.disabled = false;
                btnRegenerarDefinitivo.innerHTML = original;
            }
        });
    }

    const btnGuardarBorrador = document.getElementById('btnGuardarBorrador');
    if (btnGuardarBorrador) {
        setDefinitivoReadyForBorrador(false);
        btnGuardarBorrador.addEventListener('click', async () => {
            hideAlert();
            if (!definitivoReadyForBorrador) {
                showAlert('Primero Regenerar Definitivo antes de Guardar borrador.', false);
                return;
            }
            const propuesto = (lastGenerarResult && lastGenerarResult.pedido_propuesto) || [];
            if (!propuesto.length) {
                showAlert('No hay líneas de Pedido Definitivo para guardar.', false);
                return;
            }
            btnGuardarBorrador.disabled = true;
            const original = btnGuardarBorrador.innerHTML;
            btnGuardarBorrador.innerHTML = '<div class="loader" style="width:20px; height:20px; border-width:2px;"></div> Guardando borrador...';
            try {
                const response = await fetch('/api/pedidos/guardar-borrador', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        pedido_propuesto: propuesto,
                        parametros: lastDefinitivoParams || undefined,
                    }),
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) {
                    const detail = data.detail;
                    const msg = typeof detail === 'string'
                        ? detail
                        : (detail && detail.message) || data.message || 'Error al guardar borrador';
                    throw new Error(msg);
                }
                const meta = data.meta || {};
                const nCab = (data.cabeceras || []).length || meta.cabeceras || 0;
                const nOmitProv = (meta.proveedores_omitidos || []).length;
                const nOmitSap = (meta.lineas_omitidas_saprod || []).length;
                const ids = (data.cabeceras || [])
                    .map(c => `#${c.propuesta_id} ${c.cod_prov}`)
                    .join(', ');
                showAlert(
                    `Borrador guardado: ${nCab} cabecera(s)${ids ? ` (${ids})` : ''}. ` +
                    `Omitidos: ${nOmitProv} proveedor(es), ${nOmitSap} línea(s) SAPROD.`,
                    true
                );
            } catch (error) {
                showAlert(error.message, false);
            } finally {
                btnGuardarBorrador.innerHTML = original;
                setDefinitivoReadyForBorrador(definitivoReadyForBorrador);
            }
        });
    }

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideAlert();

            submitBtn.disabled = true;
            btnText.innerHTML = '<div class="loader" style="width:20px; height:20px; border-width:2px;"></div> Generando...';

            const excludedSection = document.getElementById('excludedSection');
            if (excludedSection) excludedSection.style.display = 'none';

            const payload = buildSencilloPayload();
            if (!payload.categorias || payload.categorias.length === 0) {
                showAlert("Debe seleccionar al menos una familia.", false);
                submitBtn.disabled = false;
                btnText.innerHTML = 'Generar (Sencillo)';
                return;
            }
            if (!payload.criterios_agrupacion.length) {
                showAlert("Seleccione al menos un Criterio de Agrupación.", false);
                submitBtn.disabled = false;
                btnText.innerHTML = 'Generar (Sencillo)';
                return;
            }

            try {
                const response = await fetch('/api/pedidos/generar-sencillo', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || "Error en Generar Sencillo");
                }
                const data = await response.json();
                stashGenerarResult(data);
                setDefinitivoReadyForBorrador(false);
                const nComp = (data.comparativa_cantidades || []).length;
                const nProp = (data.pedido_propuesto || []).length;
                showAlert(`Generar Sencillo listo: ${nComp} filas Comparativa, ${nProp} líneas Propuesto (${data.meta?.preset || ''}).`, true);
            } catch (error) {
                showAlert(error.message, false);
            } finally {
                submitBtn.disabled = false;
                btnText.innerHTML = 'Generar (Sencillo)';
            }
        });
    }

    // Legacy Excel path (secondary)
    const btnLegacyExcel = document.getElementById('btnLegacyExcel');
    if (btnLegacyExcel) {
        btnLegacyExcel.addEventListener('click', async () => {
            hideAlert();
            btnLegacyExcel.disabled = true;
            const formData = new FormData();
            formData.append('pedido_days', document.getElementById('pedidoDays').value);
            formData.append('num_rows', document.getElementById('numRows').value);
            const umbral = document.getElementById('umbralRotacion') ? document.getElementById('umbralRotacion').value : '0.0';
            formData.append('umbral_rotacion', umbral);
            formData.append('preview_mode', 'true');
            const includeGenerics = document.getElementById('includeGenerics') ? document.getElementById('includeGenerics').checked : true;
            const includeBrands = document.getElementById('includeBrands') ? document.getElementById('includeBrands').checked : true;
            formData.append('include_generics', includeGenerics ? 'true' : 'false');
            formData.append('include_brands', includeBrands ? 'true' : 'false');
            selectedFiles.forEach(file => formData.append('subtraction_files', file));
            const selectedCategoryNames = Object.values(categoryMap).filter(c => c.selected).map(c => c.name);
            if (selectedCategoryNames.length === 0) {
                showAlert("Debe seleccionar al menos una familia.", false);
                btnLegacyExcel.disabled = false;
                return;
            }
            formData.append('categories', selectedCategoryNames.join(','));
            try {
                const response = await fetch('/api/pedidos/generate', { method: 'POST', body: formData });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || "Error al calcular el reporte");
                }
                const data = await response.json();
                const excludedSection = document.getElementById('excludedSection');
                if (data.excluidos && data.excluidos.length > 0) {
                    const tbody = document.getElementById('excludedTableBody');
                    const countSpan = document.getElementById('excludedCount');
                    if (tbody && countSpan && excludedSection) {
                        tbody.innerHTML = '';
                        countSpan.textContent = `${data.excluidos.length} Productos`;
                        data.excluidos.forEach(item => {
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td style="padding: 0.5rem; border-bottom: 1px solid var(--border-color); color: var(--text-primary);">
                                    <input type="checkbox" class="exclude-checkbox" value="${item.BARRA}">
                                </td>
                                <td style="padding: 0.5rem; border-bottom: 1px solid var(--border-color); font-family: monospace; color: var(--text-primary);">${item.BARRA}</td>
                                <td style="padding: 0.5rem; border-bottom: 1px solid var(--border-color); font-size: 0.85rem; color: var(--text-primary);">${item.Descrip || ''}</td>
                                <td style="padding: 0.5rem; border-bottom: 1px solid var(--border-color); color: var(--danger); font-weight: bold;">${item.RotacionMensual.toFixed(2)}</td>
                                <td style="padding: 0.5rem; border-bottom: 1px solid var(--border-color); color: var(--text-primary);">${item.Existen || 0}</td>
                                <td style="padding: 0.5rem; border-bottom: 1px solid var(--border-color); color: var(--text-primary);">${item.CANTIDAD}</td>
                            `;
                            tbody.appendChild(tr);
                        });
                        excludedSection.style.display = 'block';
                        showAlert("Legacy: revise exclusiones y use Generar Excel Definitivo.", false);
                    }
                } else {
                    formData.set('preview_mode', 'false');
                    await generateFinalExcel(formData);
                }
            } catch (error) {
                showAlert(error.message, false);
            } finally {
                btnLegacyExcel.disabled = false;
            }
        });
    }

    // Logic for Select All in exclusions table
    const selectAllExcluded = document.getElementById('selectAllExcluded');
    if (selectAllExcluded) {
        selectAllExcluded.addEventListener('change', (e) => {
            const checkboxes = document.querySelectorAll('.exclude-checkbox');
            checkboxes.forEach(cb => cb.checked = e.target.checked);
        });
    }

    // Logic for Final Generate
    const generateFinalBtn = document.getElementById('generateFinalBtn');
    if (generateFinalBtn) {
        generateFinalBtn.addEventListener('click', async () => {
            hideAlert();
            generateFinalBtn.disabled = true;
            const originalHtml = generateFinalBtn.innerHTML;
            generateFinalBtn.innerHTML = '<div class="loader" style="width:20px; height:20px; border-width:2px; border-color: white transparent transparent transparent;"></div> Generando...';
            
            const formData = new FormData();
            formData.append('pedido_days', document.getElementById('pedidoDays').value);
            formData.append('num_rows', document.getElementById('numRows').value);
            const umbral = document.getElementById('umbralRotacion') ? document.getElementById('umbralRotacion').value : '0.0';
            formData.append('umbral_rotacion', umbral);
            formData.append('preview_mode', 'false'); // Force final download
            
            const includeGenerics = document.getElementById('includeGenerics') ? document.getElementById('includeGenerics').checked : true;
            const includeBrands = document.getElementById('includeBrands') ? document.getElementById('includeBrands').checked : true;
            formData.append('include_generics', includeGenerics ? 'true' : 'false');
            formData.append('include_brands', includeBrands ? 'true' : 'false');
            
            selectedFiles.forEach(file => formData.append('subtraction_files', file));
            
            const selectedCategoryNames = Object.values(categoryMap)
                .filter(c => c.selected).map(c => c.name);
            formData.append('categories', selectedCategoryNames.join(','));

            // forced_includes deprecated — not part of Generar happy path (ticket 12)
            // Legacy Excel path no longer gathers forced barcodes for primary flow.

            try {
                await generateFinalExcel(formData);
                document.getElementById('excludedSection').style.display = 'none';
            } catch (error) {
                showAlert(error.message, false);
            } finally {
                generateFinalBtn.disabled = false;
                generateFinalBtn.innerHTML = originalHtml;
            }
        });
    }

    async function generateFinalExcel(formData) {
        const response = await fetch('/api/pedidos/generate', { method: 'POST', body: formData });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || "Error al generar el archivo Excel");
        }

        const blob = await response.blob();
        let filename = "Pedido.xlsx";
        const disposition = response.headers.get('Content-Disposition');
        if (disposition && disposition.indexOf('filename=') !== -1) {
            const match = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
            if (match != null && match[1]) filename = match[1].replace(/['"]/g, '');
        }

        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        a.remove();

        showAlert("Matríz de Pedidos generada y descargada exitosamente.", true);
        selectedFiles = [];
        renderFileList();
    }
});
