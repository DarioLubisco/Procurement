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
    let configCollapsed = false;
    let fxState = { moneda_trabajo: 'USD', dolarbcv: null };
    // ADR-0027: qty overrides (clave barra_propuesto||proveedor → qty)
    let qtyOverridesPending = null;

    function getFx() {
        const meta = (lastGenerarResult && lastGenerarResult.meta) || {};
        return {
            moneda_trabajo: (meta.moneda_trabajo || fxState.moneda_trabajo || 'USD').toUpperCase(),
            dolarbcv: meta.dolarbcv != null ? Number(meta.dolarbcv) : fxState.dolarbcv,
        };
    }

    /** Motor always USD; display in Bs when MonedaTrabajo=VES. */
    function moneyDisplay(amountUsd, { digits = 2 } = {}) {
        if (amountUsd == null || amountUsd === '' || Number.isNaN(Number(amountUsd))) {
            return '—';
        }
        const fx = getFx();
        const usd = Number(amountUsd);
        if (fx.moneda_trabajo === 'VES' && fx.dolarbcv && fx.dolarbcv > 0) {
            const bs = usd * fx.dolarbcv;
            return `Bs ${bs.toLocaleString('es-VE', { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
        }
        return `$${usd.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
    }

    function moneyUnitLabel() {
        return getFx().moneda_trabajo === 'VES' ? 'Bs' : 'USD';
    }

    const CRITERIOS_DEFAULT = [
        'principio_activo',
        'forma_farmaceutica',
        'concentracion',
        'cantidad_presentacion',
        'contenido_neto',
    ];
    const CRITERIOS_FALLBACK = [
        { nombre_campo: 'principio_activo', etiqueta: 'Principio Activo', activo: true },
        { nombre_campo: 'concentracion', etiqueta: 'Concentración', activo: true },
        { nombre_campo: 'forma_farmaceutica', etiqueta: 'Forma Farmacéutica', activo: true },
        { nombre_campo: 'cantidad_presentacion', etiqueta: 'Presentación', activo: true },
        { nombre_campo: 'origen', etiqueta: 'Origen', activo: true },
        { nombre_campo: 'fabricante', etiqueta: 'Fabricante', activo: true },
        { nombre_campo: 'contenido_neto', etiqueta: 'Contenido Neto', activo: true },
        { nombre_campo: 'generico', etiqueta: 'Genérico', activo: true },
        { nombre_campo: 'marca', etiqueta: 'Marca', activo: true },
    ];

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

    // --- CONFIG DEFAULTS (localStorage) ---
    const btnSaveDefaults = document.getElementById('btnSaveDefaults');
    const inputDays = document.getElementById('pedidoDays');
    const inputRows = document.getElementById('numRows');
    const inputUmbral = document.getElementById('umbralRotacion');
    const DEFAULTS_KEY = 'syn_ped_defaults_v2';

    function readStoredDefaults() {
        try {
            const raw = localStorage.getItem(DEFAULTS_KEY);
            if (raw) return JSON.parse(raw);
        } catch (e) { /* ignore */ }
        // Legacy single keys
        return {
            days: localStorage.getItem('syn_ped_days'),
            rows: localStorage.getItem('syn_ped_rows'),
            umbral: localStorage.getItem('syn_ped_umbral'),
        };
    }

    function collectDefaultsSnapshot() {
        const selectedCatIds = Object.values(categoryMap)
            .filter(c => c.selected)
            .map(c => c.id);
        return {
            days: inputDays ? inputDays.value : '30',
            rows: inputRows ? inputRows.value : '5000',
            umbral: inputUmbral ? inputUmbral.value : '0.5',
            preset: document.getElementById('presetSencillo')?.value || 'Normal',
            presupuesto: document.getElementById('presupuestoMaximo')?.value || '',
            include_generics: document.getElementById('includeGenerics')?.checked !== false,
            include_brands: document.getElementById('includeBrands')?.checked !== false,
            criterios: collectCriteriosAgrupacion(),
            category_ids: selectedCatIds,
        };
    }

    function applyScalarDefaults(d) {
        if (!d) return;
        if (d.days && inputDays) inputDays.value = d.days;
        if (d.rows && inputRows) inputRows.value = d.rows;
        if (d.umbral != null && d.umbral !== '' && inputUmbral) inputUmbral.value = d.umbral;
        const preset = document.getElementById('presetSencillo');
        if (d.preset && preset) preset.value = d.preset;
        const presupuesto = document.getElementById('presupuestoMaximo');
        if (presupuesto && d.presupuesto != null) presupuesto.value = d.presupuesto;
        const gen = document.getElementById('includeGenerics');
        if (gen && typeof d.include_generics === 'boolean') gen.checked = d.include_generics;
        const brands = document.getElementById('includeBrands');
        if (brands && typeof d.include_brands === 'boolean') brands.checked = d.include_brands;
    }

    function applyCriteriosDefaults(d) {
        if (!d || !Array.isArray(d.criterios) || !d.criterios.length) return;
        const wanted = new Set(d.criterios);
        document.querySelectorAll('.criterio-cb').forEach(cb => {
            cb.checked = wanted.has(cb.value);
        });
    }

    function applyCategoryDefaults(d) {
        if (!d || !Array.isArray(d.category_ids) || !Object.keys(categoryMap).length) return;
        const wanted = new Set(d.category_ids.map(String));
        Object.values(categoryMap).forEach(cat => {
            cat.selected = wanted.has(String(cat.id));
            cat.indeterminate = false;
        });
        // Recompute parent indeterminate from children (bottom-up via each parent)
        Object.values(categoryMap).forEach(cat => {
            if (cat.parentId && cat.parentId !== '0') updateParentState(cat.parentId);
        });
        renderCategories();
    }

    function loadDefaults() {
        const d = readStoredDefaults();
        applyScalarDefaults(d);
        window.__pedDefaults = d;
    }

    if (btnSaveDefaults) {
        btnSaveDefaults.addEventListener('click', () => {
            const snap = collectDefaultsSnapshot();
            localStorage.setItem(DEFAULTS_KEY, JSON.stringify(snap));
            // Keep legacy keys for older tabs
            localStorage.setItem('syn_ped_days', snap.days);
            localStorage.setItem('syn_ped_rows', snap.rows);
            localStorage.setItem('syn_ped_umbral', snap.umbral);
            window.__pedDefaults = snap;
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
            applyCategoryDefaults(window.__pedDefaults);
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
        const checkedCount = Object.values(categoryMap).filter(c => c.selected).length;
        categoryCount.textContent = `${checkedCount} Seleccionadas`;
    }

    function openCategoriesModal() {
        const modal = document.getElementById('categoriesModal');
        if (!modal) return;
        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function closeCategoriesModal() {
        const modal = document.getElementById('categoriesModal');
        if (!modal) return;
        modal.classList.remove('active');
        modal.setAttribute('aria-hidden', 'true');
    }

    function setConfigCollapsed(collapsed) {
        configCollapsed = !!collapsed;
        const body = document.getElementById('configBody');
        const btn = document.getElementById('btnToggleConfig');
        const label = document.getElementById('btnToggleConfigLabel');
        if (body) body.classList.toggle('collapsed', configCollapsed);
        if (btn) btn.style.display = 'inline-flex';
        if (label) {
            label.textContent = configCollapsed ? 'Editar configuración' : 'Ocultar configuración';
        }
        const icon = btn && btn.querySelector('i');
        if (icon) {
            icon.className = configCollapsed ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
        }
    }

    function renderCriteriosAgrupacion(atributos) {
        const host = document.getElementById('criteriosAgrupacion');
        if (!host) return;
        const list = (atributos || []).filter(
            a => a && a.activo !== false && a.nombre_campo && a.nombre_campo !== 'blister'
        );
        const effective = list.length ? list : CRITERIOS_FALLBACK;
        const defaultSet = new Set(CRITERIOS_DEFAULT);
        host.innerHTML = '';
        effective.forEach(attr => {
            const key = attr.nombre_campo;
            const label = document.createElement('label');
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.className = 'criterio-cb';
            cb.value = key;
            cb.checked = defaultSet.has(key);
            label.appendChild(cb);
            label.appendChild(document.createTextNode(' ' + (attr.etiqueta || key)));
            host.appendChild(label);
        });
        applyCriteriosDefaults(window.__pedDefaults);
    }

    async function fetchCriteriosAtributos() {
        try {
            const response = await fetch('/api/rotacion-grupal/atributos');
            if (!response.ok) throw new Error('atributos HTTP ' + response.status);
            const data = await response.json();
            renderCriteriosAgrupacion(data.atributos || []);
        } catch (err) {
            console.warn('Fallback criterios whitelist:', err);
            renderCriteriosAgrupacion(CRITERIOS_FALLBACK);
        }
    }

    if (categorySearch) categorySearch.addEventListener('input', (e) => applySearch(e.target.value));
    if (btnSelectAll) btnSelectAll.addEventListener('click', () => {
        categoryTree.forEach(root => handleCheckboxChange(root.id, true));
    });
    if (btnSelectNone) btnSelectNone.addEventListener('click', () => {
        categoryTree.forEach(root => handleCheckboxChange(root.id, false));
    });

    const btnEditCategories = document.getElementById('btnEditCategories');
    const btnCloseCategoriesModal = document.getElementById('btnCloseCategoriesModal');
    const btnCloseCategoriesModalX = document.getElementById('btnCloseCategoriesModalX');
    const categoriesModal = document.getElementById('categoriesModal');
    if (btnEditCategories) btnEditCategories.addEventListener('click', openCategoriesModal);
    if (btnCloseCategoriesModal) btnCloseCategoriesModal.addEventListener('click', closeCategoriesModal);
    if (btnCloseCategoriesModalX) btnCloseCategoriesModalX.addEventListener('click', closeCategoriesModal);
    if (categoriesModal) {
        categoriesModal.addEventListener('click', (e) => {
            if (e.target === categoriesModal) closeCategoriesModal();
        });
    }
    const btnToggleConfig = document.getElementById('btnToggleConfig');
    if (btnToggleConfig) {
        btnToggleConfig.addEventListener('click', () => setConfigCollapsed(!configCollapsed));
    }

    fetchCategories();
    fetchCriteriosAtributos();

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
            preset: document.getElementById('presetSencillo')?.value || 'Normal',
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
        }).join(' · ');
    }

    function renderCompetenciaBlock(datos) {
        if (!datos) return '';
        const rivales = datos.rivales || [];
        const hermanos = datos.hermanos_reemplazables || [];
        const hasHeader = datos.precio != null || datos.media_de_mediana != null;
        if (!rivales.length && !hermanos.length && !hasHeader) return '';
        let html = '<div style="margin-top:0.45rem; padding:0.5rem 0.65rem; background:rgba(255,255,255,0.04); border-radius:6px; font-size:0.78rem;">';

        // Cabecera elegida: precio · media hist · Δ$ · % (siempre USD)
        if (hasHeader) {
            const px = datos.precio != null ? `$${Number(datos.precio).toFixed(4)}` : '—';
            let line = `<strong>${escapeHtml(datos.proveedor || 'Oferta')}</strong> ${px}`;
            if (datos.media_de_mediana != null) {
                const media = Number(datos.media_de_mediana);
                const delta = datos.delta_vs_media_usd != null
                    ? Number(datos.delta_vs_media_usd)
                    : (datos.precio != null ? Number(datos.precio) - media : null);
                line += ` · media hist. $${media.toFixed(4)}`;
                if (delta != null) {
                    const sign = delta >= 0 ? '+' : '';
                    line += ` · Δ $${sign}${delta.toFixed(4)}`;
                }
                if (datos.desvio != null) {
                    line += ` (${(Number(datos.desvio) * 100).toFixed(1)}%)`;
                }
            } else if (datos.desvio != null) {
                line += ` · desvío ${(Number(datos.desvio) * 100).toFixed(1)}%`;
            }
            if (datos.fuente_baseline) {
                line += ` <span style="opacity:0.75;">[${escapeHtml(datos.fuente_baseline)}]</span>`;
            }
            if (datos.pdr_semaforo) {
                line += ` <span style="opacity:0.75;">[PDR:${escapeHtml(String(datos.pdr_semaforo))}]</span>`;
            }
            html += `<div style="margin-bottom:0.35rem;">${line}</div>`;
        }

        if (rivales.length) {
            html += '<div style="font-weight:600; margin-bottom:0.25rem;">¿Por qué esta oferta? (top ' +
                (datos.top_n_rivales || rivales.length) + ')</div>';
            html += '<ol style="margin:0; padding-left:1.2rem;">';
            rivales.forEach(r => {
                const mark = r.elegida ? ' ← elegida' : '';
                const px = r.precio != null ? `$${Number(r.precio).toFixed(4)}` : '—';
                const dv = r.desvio != null ? ` · desvío ${(Number(r.desvio) * 100).toFixed(1)}%` : '';
                const lt = r.lead_time_dias != null ? ` · LT ${r.lead_time_dias}d` : '';
                html += `<li><strong>${escapeHtml(r.proveedor)}</strong> / ${escapeHtml(r.barra)} — ${px}${dv}${lt}${mark}</li>`;
            });
            html += '</ol>';
        }
        if (hermanos.length) {
            html += '<div style="font-weight:600; margin:0.5rem 0 0.25rem;">Hermanos reemplazables (top ' +
                (datos.top_n_hermanos || hermanos.length) + ')</div>';
            html += '<ol style="margin:0; padding-left:1.2rem;">';
            hermanos.forEach(h => {
                const px = h.precio != null ? `$${Number(h.precio).toFixed(4)}` : '—';
                const desc = h.descripcion ? ` — ${escapeHtml(h.descripcion)}` : '';
                html += `<li><code>${escapeHtml(h.barra)}</code> via <strong>${escapeHtml(h.proveedor)}</strong> ${px}${desc}</li>`;
            });
            html += '</ol>';
        }
        html += '</div>';
        return html;
    }

    function renderFactoresAccordion(factores) {
        if (!factores || !factores.length) {
            return '<div style="padding:0.5rem 0.75rem; color:var(--text-secondary); font-size:0.8rem;">Sin factores de motor.</div>';
        }
        return '<ul style="margin:0; padding:0.5rem 0.75rem 0.75rem 1.25rem; font-size:0.8rem; line-height:1.4;">' +
            factores.map(f => {
                const t = escapeHtml(f.titulo || f.codigo || '');
                const d = escapeHtml(f.detalle || '');
                const extra = renderCompetenciaBlock(f.datos || {});
                return `<li style="margin-bottom:0.35rem;"><strong>${t}</strong>${d ? ` — ${d}` : ''}${extra}</li>`;
            }).join('') +
            '</ul>';
    }

    function overrideKey(row) {
        return `${String(row.barra_propuesto || '')}||${String(row.proveedor || '')}`;
    }

    function collectQtyOverrides(data) {
        const map = {};
        (data?.comparativa_cantidades || []).forEach(row => {
            if (!row.qty_editado) return;
            map[overrideKey(row)] = Number(row.qty_propuesto);
        });
        return map;
    }

    function hasQtyOverrides(data) {
        return Object.keys(collectQtyOverrides(data)).length > 0;
    }

    function promptOverridesBeforeGenerar() {
        if (!lastGenerarResult || !hasQtyOverrides(lastGenerarResult)) {
            qtyOverridesPending = null;
            return true;
        }
        const n = Object.keys(collectQtyOverrides(lastGenerarResult)).length;
        const ok = window.confirm(
            `Hay ${n} qty editada(s) en Comparativa.\n\n` +
            'Aceptar = Descartar overrides y usar el nuevo Generar.\n' +
            'Cancelar = Reaplicar overrides sobre el resultado (si la clave barra+proveedor sigue existiendo).'
        );
        if (ok) {
            qtyOverridesPending = null;
            return true;
        }
        qtyOverridesPending = collectQtyOverrides(lastGenerarResult);
        return true;
    }

    function applyPendingOverrides(data) {
        if (!qtyOverridesPending || !data?.comparativa_cantidades) {
            qtyOverridesPending = null;
            return data;
        }
        const map = qtyOverridesPending;
        qtyOverridesPending = null;
        data.comparativa_cantidades.forEach(row => {
            const k = overrideKey(row);
            if (!(k in map)) return;
            const newQty = Math.max(0, Math.round(Number(map[k]) || 0));
            if (row.qty_propuesto_original == null) {
                row.qty_propuesto_original = Number(row.qty_propuesto);
            }
            row.qty_propuesto = newQty;
            row.qty_editado = newQty !== Number(row.qty_propuesto_original);
            syncPedidoPropuestoPrimary(data, row, newQty);
        });
        refreshGrupoSumsInPlace(data.comparativa_cantidades);
        return data;
    }

    function refreshGrupoSumsInPlace(rows) {
        const sumBase = {};
        const sumProp = {};
        rows.forEach(r => {
            const gk = String(r.grupo_key || '');
            sumBase[gk] = (sumBase[gk] || 0) + (Number(r.qty_baseline) || 0);
            sumProp[gk] = (sumProp[gk] || 0) + (Number(r.qty_propuesto) || 0);
        });
        rows.forEach(r => {
            const gk = String(r.grupo_key || '');
            r.grupo_sum_baseline = sumBase[gk] || 0;
            r.grupo_sum_propuesto = sumProp[gk] || 0;
        });
    }

    /** SplitLeadTime: delta solo en pierna primaria; extras fijas (ADR-0027). */
    function syncPedidoPropuestoPrimary(data, row, newTotalQty) {
        if (!data) return;
        const barra = String(row.barra_propuesto || '');
        const proveedor = String(row.proveedor || '');
        const extras = Math.max(0, Number(row.extra_legs_qty) || 0);
        let primaryQty = Math.max(0, Math.round(Number(newTotalQty) || 0) - extras);
        const lines = data.pedido_propuesto || [];
        const idx = lines.findIndex(
            l => String(l.barra || '') === barra && String(l.proveedor || '') === proveedor
        );
        if (primaryQty <= 0) {
            if (idx >= 0) lines.splice(idx, 1);
            data.pedido_propuesto = lines;
            return;
        }
        if (idx >= 0) {
            lines[idx].cantidad = primaryQty;
        } else if (proveedor) {
            lines.push({
                barra,
                descripcion: row.desc_propuesto || '',
                proveedor,
                cantidad: primaryQty,
                precio: null,
            });
        }
        data.pedido_propuesto = lines;
    }

    function qtyWarnFlags(row) {
        const qty = Number(row.qty_propuesto) || 0;
        const base = Number(row.qty_baseline) || 0;
        const gProp = Number(row.grupo_sum_propuesto) || 0;
        const gBase = Number(row.grupo_sum_baseline) || 0;
        return {
            overLine: qty > base,
            overGrupo: gProp > gBase,
        };
    }

    function clearComparativaActiveRow() {
        document.querySelectorAll('#comparativaTableBody tr.comparativa-main-row.is-qty-focus')
            .forEach(el => el.classList.remove('is-qty-focus'));
    }

    function setComparativaActiveRow(tr) {
        clearComparativaActiveRow();
        if (tr) tr.classList.add('is-qty-focus');
    }

    function closeQtyContextoDrawer() {
        const drawer = document.getElementById('qtyContextoDrawer');
        if (drawer) drawer.style.display = 'none';
        clearComparativaActiveRow();
    }

    function openQtyContextoDrawer(row, tr = null) {
        const drawer = document.getElementById('qtyContextoDrawer');
        const body = document.getElementById('qtyContextoDrawerBody');
        if (!drawer || !body) return;
        if (tr) setComparativaActiveRow(tr);
        const warn = qtyWarnFlags(row);
        const stockOferta = row.stock_oferta != null ? row.stock_oferta : '—';
        let competenciaHtml = '';
        (row.justificacion_factores || []).forEach(f => {
            const block = renderCompetenciaBlock(f.datos || {});
            if (block) competenciaHtml += block;
        });
        if (!competenciaHtml) {
            competenciaHtml = '<div style="opacity:0.7;">Sin rivales/hermanos en justificación.</div>';
        }
        const warnHtml = (warn.overLine || warn.overGrupo)
            ? `<div style="margin:0.5rem 0; padding:0.4rem 0.5rem; border-left:3px solid #f59e0b; background:rgba(245,158,11,0.12); color:var(--text-primary);">
                ${warn.overLine ? 'Qty fila &gt; baseline.<br>' : ''}
                ${warn.overGrupo ? 'Σ propuesto del Grupo &gt; Σ baselines.' : ''}
               </div>`
            : '';
        body.innerHTML = `
            ${warnHtml}
            <div style="font-weight:600; color:var(--text-primary); margin-bottom:0.25rem;">Línea</div>
            <div>Baseline neto: <strong>${Number(row.qty_baseline) || 0}</strong></div>
            <div>Qty propuesto: <strong>${Number(row.qty_propuesto) || 0}</strong></div>
            <div>Existen: <strong>${row.existen != null ? row.existen : '—'}</strong></div>
            <div>Backorder: <strong>${Number(row.backorder_qty) || 0}</strong></div>
            <div>Stock oferta: <strong>${stockOferta}</strong></div>
            <div>Proveedor: <strong>${escapeHtml(row.proveedor || '—')}</strong></div>
            <div style="font-weight:600; color:var(--text-primary); margin:0.65rem 0 0.25rem;">Grupo</div>
            <div>Σ propuesto / Σ baseline: <strong>${Number(row.grupo_sum_propuesto) || 0}</strong> / <strong>${Number(row.grupo_sum_baseline) || 0}</strong></div>
            <div style="font-weight:600; color:var(--text-primary); margin:0.65rem 0 0.25rem;">Competencia</div>
            ${competenciaHtml}
        `;
        drawer.style.display = 'block';
    }

    document.getElementById('qtyContextoDrawerClose')?.addEventListener('click', closeQtyContextoDrawer);

    function onQtyPropuestoEdit(row, inputEl) {
        const raw = inputEl.value;
        let newQty = Math.max(0, Math.round(Number(raw) || 0));
        if (String(raw) !== String(newQty)) inputEl.value = String(newQty);
        if (row.qty_propuesto_original == null) {
            row.qty_propuesto_original = Number(row.qty_propuesto);
        }
        row.qty_propuesto = newQty;
        row.qty_editado = newQty !== Number(row.qty_propuesto_original);
        if (lastGenerarResult) {
            syncPedidoPropuestoPrimary(lastGenerarResult, row, newQty);
            refreshGrupoSumsInPlace(lastGenerarResult.comparativa_cantidades || []);
            renderGenerarResult(lastGenerarResult, { scroll: false, keepDrawerRow: row });
        }
    }

    function isComparativaIdentityRow(row) {
        if (row.qty_editado) return false;
        const sameBarra = String(row.barra_baseline || '') === String(row.barra_propuesto || '');
        const sameQty = Number(row.qty_baseline) === Number(row.qty_propuesto);
        return sameBarra && sameQty;
    }

    function renderGenerarResult(data, { scroll = true, keepDrawerRow = null } = {}) {
        const section = document.getElementById('generarResultSection');
        const compBody = document.getElementById('comparativaTableBody');
        const propBody = document.getElementById('propuestoTableBody');
        if (!section || !compBody || !propBody) return;

        const allRows = data.comparativa_cantidades || [];
        const soloCambios = document.getElementById('comparativaSoloCambios')?.checked !== false;
        const visibleRows = soloCambios
            ? allRows.filter(r => !isComparativaIdentityRow(r))
            : allRows;
        const hiddenN = allRows.length - visibleRows.length;
        const hint = document.getElementById('comparativaFilterHint');
        if (hint) {
            if (!allRows.length) {
                hint.textContent = 'Comparativa vacía: el motor no devolvió filas.';
            } else if (soloCambios && visibleRows.length === 0) {
                hint.textContent = `Ningún cambio de unidad/barra (${allRows.length} filas ocultas). Desmarque «Solo cambios» para verlas, o revise desvío/amplificador.`;
            } else if (soloCambios && hiddenN > 0) {
                hint.textContent = `Mostrando ${visibleRows.length} cambios · ocultas ${hiddenN} sin cambio de barra/qty.`;
            } else {
                hint.textContent = `${allRows.length} filas en Comparativa` +
                    (visibleRows.length !== allRows.length ? ` (${visibleRows.length} visibles).` : '.');
            }
        }

        compBody.innerHTML = '';
        let openJustRow = null;

        if (!visibleRows.length) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="7" style="padding:1rem; color:var(--text-secondary); text-align:center;">
                ${soloCambios && allRows.length
                    ? 'Sin diferencias de unidad/barra con el filtro «Solo cambios». Desmarque el checkbox arriba para ver todas las filas.'
                    : 'Sin filas para mostrar.'}
            </td>`;
            compBody.appendChild(tr);
        }

        visibleRows.forEach((row, idx) => {
            const tr = document.createElement('tr');
            tr.className = 'comparativa-main-row';
            tr.dataset.justIdx = String(idx);
            tr.dataset.barra = String(row.barra_propuesto || row.barra_baseline || '');
            tr.dataset.proveedor = String(row.proveedor || '');
            const resumen = row.justificacion_delta || '';
            const factores = row.justificacion_factores || [];
            const hasDetail = factores.length > 0 || !!resumen;
            const warn = qtyWarnFlags(row);
            const warnBorder = (warn.overLine || warn.overGrupo)
                ? 'outline:2px solid #f59e0b; outline-offset:1px; border:1px solid #f59e0b;'
                : 'border:1px solid var(--border-subtle);';
            if (warn.overLine || warn.overGrupo) {
                tr.style.background = 'rgba(245,158,11,0.08)';
            }
            const editBadge = row.qty_editado
                ? ' <span style="font-size:0.65rem; text-transform:uppercase; letter-spacing:0.04em; color:#f59e0b; font-weight:700;">editado</span>'
                : '';
            const stockTxt = row.stock_oferta != null ? String(row.stock_oferta) : '—';
            const boTxt = String(Number(row.backorder_qty) || 0);
            const exTxt = row.existen != null ? String(row.existen) : '—';
            const hoverTitle = (factorsHoverText(factores) || resumen || '').replace(/[\r\n]+/g, ' · ');
            tr.innerHTML = `
                <td style="padding:0.5rem; font-family:monospace;">${escapeHtml(row.barra_baseline)}</td>
                <td style="padding:0.5rem;">${escapeHtml(row.desc_baseline || '')}</td>
                <td style="padding:0.5rem; text-align:right;">${row.qty_baseline}</td>
                <td style="padding:0.5rem; font-family:monospace;">${escapeHtml(row.barra_propuesto)}</td>
                <td style="padding:0.5rem;">${escapeHtml(row.desc_propuesto || '')}</td>
                <td style="padding:0.5rem; text-align:right; white-space:nowrap;">
                    <input type="number" min="0" step="1" class="qty-propuesto-input"
                        value="${Number(row.qty_propuesto) || 0}"
                        style="width:4.5rem; text-align:right; padding:0.25rem 0.35rem; border-radius:4px; background:rgba(0,0,0,0.25); color:inherit; ${warnBorder}"
                        title="${warn.overLine || warn.overGrupo ? 'Qty por encima del baseline (informativo)' : 'Editar qty propuesto'}">
                    ${editBadge}
                    <div style="font-size:0.68rem; color:var(--text-secondary); margin-top:0.2rem; line-height:1.35; text-align:right;">
                        stock oferta <strong style="color:var(--text-primary);">${escapeHtml(stockTxt)}</strong>
                        · BO <strong style="color:var(--text-primary);">${escapeHtml(boTxt)}</strong>
                        · existen <strong style="color:var(--text-primary);">${escapeHtml(exTxt)}</strong>
                    </div>
                </td>
                <td class="justificacion-cell" style="padding:0.5rem; font-size:0.8rem; color:var(--text-secondary); max-width:220px; cursor:${hasDetail ? 'pointer' : 'default'};">
                    <span class="justificacion-resumen" style="display:inline-block; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; border-bottom:${hasDetail ? '1px dotted var(--text-secondary)' : 'none'};">${escapeHtml(resumen) || '—'}</span>
                </td>
            `;
            const justSpan = tr.querySelector('.justificacion-resumen');
            if (justSpan && hoverTitle) {
                justSpan.setAttribute('title', hoverTitle);
            }
            const qtyInput = tr.querySelector('.qty-propuesto-input');
            qtyInput.addEventListener('focus', () => openQtyContextoDrawer(row, tr));
            qtyInput.addEventListener('change', () => onQtyPropuestoEdit(row, qtyInput));
            qtyInput.addEventListener('keydown', (ev) => {
                if (ev.key === 'Enter') {
                    ev.preventDefault();
                    qtyInput.blur();
                }
            });

            const detailTr = document.createElement('tr');
            detailTr.className = 'comparativa-detail-row';
            detailTr.style.display = 'none';
            // Lazy: do not expand rivales/hermanos HTML for every row up-front (kills UI on Agresivo).
            detailTr.innerHTML = `<td colspan="7" style="background:rgba(0,0,0,0.15); border-bottom:1px solid var(--border-subtle); padding:0.75rem; color:var(--text-secondary); font-size:0.8rem;">Cargando detalle…</td>`;

            if (hasDetail) {
                tr.querySelector('.justificacion-cell').addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    const opening = detailTr.style.display === 'none';
                    if (openJustRow && openJustRow !== detailTr) {
                        openJustRow.style.display = 'none';
                    }
                    if (opening && detailTr.dataset.rendered !== '1') {
                        detailTr.innerHTML = `<td colspan="7" style="background:rgba(0,0,0,0.15); border-bottom:1px solid var(--border-subtle); padding:0;">${renderFactoresAccordion(factores)}</td>`;
                        detailTr.dataset.rendered = '1';
                    }
                    detailTr.style.display = opening ? 'table-row' : 'none';
                    openJustRow = opening ? detailTr : null;
                });
            }

            compBody.appendChild(tr);
            compBody.appendChild(detailTr);
        });

        propBody.innerHTML = '';
        const thPrecio = document.querySelector('#propuestoTableBody')?.closest('table')?.querySelector('thead th:nth-child(4)');
        if (thPrecio) thPrecio.textContent = `Precio (${moneyUnitLabel()})`;
        const thTotal = document.querySelector('#propuestoTableBody')?.closest('table')?.querySelector('thead th:nth-child(6)');
        if (thTotal) thTotal.textContent = `Total (${moneyUnitLabel()})`;

        (data.pedido_propuesto || []).forEach(line => {
            const qty = Number(line.cantidad) || 0;
            const pxUsd = line.precio != null ? Number(line.precio) : null;
            const totalUsd = pxUsd != null ? pxUsd * qty : null;
            const tr = document.createElement('tr');
            tr.dataset.barra = String(line.barra || '');
            tr.innerHTML = `
                <td style="padding:0.5rem; font-family:monospace;">${escapeHtml(line.barra)}</td>
                <td style="padding:0.5rem;">${escapeHtml(line.descripcion || '')}</td>
                <td style="padding:0.5rem; font-weight:600;">${escapeHtml(line.proveedor || '')}</td>
                <td style="padding:0.5rem; text-align:right; font-variant-numeric:tabular-nums;">${moneyDisplay(pxUsd, { digits: 4 })}</td>
                <td style="padding:0.5rem; text-align:right;">${qty}</td>
                <td style="padding:0.5rem; text-align:right; font-weight:600; font-variant-numeric:tabular-nums;">${moneyDisplay(totalUsd)}</td>
            `;
            propBody.appendChild(tr);
        });

        section.style.display = 'block';
        setConfigCollapsed(true);
        if (keepDrawerRow) {
            const kBarra = String(keepDrawerRow.barra_propuesto || keepDrawerRow.barra_baseline || '');
            const kProv = String(keepDrawerRow.proveedor || '');
            const matchTr = Array.from(
                compBody.querySelectorAll('tr.comparativa-main-row')
            ).find(el =>
                String(el.dataset.barra || '') === kBarra
                && String(el.dataset.proveedor || '') === kProv
            );
            openQtyContextoDrawer(keepDrawerRow, matchTr || null);
            if (matchTr) {
                const inp = matchTr.querySelector('.qty-propuesto-input');
                if (inp && document.activeElement !== inp) {
                    // Restore focus after re-render without scrolling page
                    try { inp.focus({ preventScroll: true }); } catch (_) { inp.focus(); }
                }
            }
        } else if (!scroll) {
            // keep drawer as-is on silent re-render without keepDrawerRow
        } else {
            closeQtyContextoDrawer();
        }
        if (scroll) {
            section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    document.getElementById('comparativaSoloCambios')?.addEventListener('change', () => {
        if (lastGenerarResult) renderGenerarResult(lastGenerarResult, { scroll: false });
    });

    function stashGenerarResult(data, { resetVm = true } = {}) {
        applyPendingOverrides(data);
        lastGenerarResult = data;
        window.lastGenerarResult = data;
        window.stashGenerarResult = stashGenerarResult;
        if (data && data.meta) {
            if (data.meta.moneda_trabajo) fxState.moneda_trabajo = String(data.meta.moneda_trabajo).toUpperCase();
            if (data.meta.dolarbcv != null) fxState.dolarbcv = Number(data.meta.dolarbcv);
        }
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
        renderGenerarResult(lastGenerarResult, { scroll: false });
        renderValidarMinimosUI(vm);
        if (vm.requiere_panel_antes_recalc) {
            vmPanelAck = true;
        }
        // Stay on Validar mínimos panel (do not jump to Comparativa top).
        const vmSection = document.getElementById('validarMinimosSection');
        if (vmSection) {
            vmSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    function scrollToPedidoBarra(barra) {
        const b = String(barra || '').trim();
        if (!b) return;
        const el = document.querySelector(`#propuestoTableBody tr[data-barra="${b.replace(/"/g, '')}"]`)
            || document.querySelector(`#comparativaTableBody tr[data-barra="${b.replace(/"/g, '')}"]`);
        if (!el) {
            showAlert(`No encontré la línea ${b} en el pedido visible.`, false);
            return;
        }
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.style.outline = '2px solid var(--primary-accent)';
        setTimeout(() => { el.style.outline = ''; }, 2200);
    }

    function renderValidarMinimosUI(vm) {
        const panel = document.getElementById('validarMinimosPanel');
        const colaEl = document.getElementById('validarMinimosCola');
        const detEl = document.getElementById('validarMinimosDetalle');
        const hint = document.getElementById('validarMinimosHint');
        if (!panel || !colaEl || !detEl) return;
        panel.style.display = 'block';
        const cola = vm.cola || [];
        const p = vm.panel;

        function panelHtml(p) {
            if (!p) return '';
            const name = p.nombre_corto || p.proveedor;
            const aliases = (p.aliases || []).length
                ? ` <span style="color:var(--text-secondary);font-size:0.8em;">[${(p.aliases || []).join(', ')}]</span>`
                : '';
            const deficit = Number(p.deficit_usd || 0);
            const okBadge = deficit <= 0
                ? ' <span style="color:#10b981;font-weight:600;">(cumple mínimo)</span>'
                : '';

            const rows = [];
            (p.reemplazos || []).forEach(r => {
                const unreliable = !!(r.precio_actual_missing || r.precio_actual_invalido || r.ahorro_usd == null);
                const checked = r.redistribuible_default !== false && !unreliable;
                const desc = r.descripcion_actual || r.descripcion_alt || '';
                const dest = `${r.proveedor_alt}/${r.barra_alternativa}`;
                let deltaCell = '—';
                if (!unreliable) {
                    const delta = Number(r.ahorro_usd);
                    const sign = delta >= 0 ? '+' : '';
                    deltaCell = `${sign}${moneyDisplay(delta)}`;
                    if (r.delta_pct != null) {
                        const pct = Number(r.delta_pct);
                        deltaCell += ` (${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%)`;
                    }
                } else {
                    deltaCell = '⚠ no confiable';
                }
                rows.push({
                    barra: r.barra_actual,
                    desc,
                    dest: `${r.proveedor_actual || p.proveedor} → ${dest}`,
                    deltaCell,
                    checked,
                    kind: 'reemplazo',
                    disabled: false,
                });
            });
            (p.huerfanos_si_rechaza || []).forEach(h => {
                rows.push({
                    barra: h.barra,
                    desc: h.descripcion || '',
                    dest: 'sin 2º (huérfano si se saca del lab)',
                    deltaCell: '—',
                    checked: false,
                    kind: 'huerfano',
                    disabled: false,
                });
            });

            const tableRows = rows.map(row => `
                <tr>
                  <td style="padding:0.35rem 0.4rem; vertical-align:top;">
                    <input type="checkbox" class="vm-redis-cb" data-barra="${escapeHtml(row.barra)}"
                      ${row.checked ? 'checked' : ''} ${row.disabled ? 'disabled' : ''}
                      title="${row.kind === 'huerfano' ? 'Si marca: saca del lab → huérfano' : 'Si marca: mueve al 2º'}">
                  </td>
                  <td style="padding:0.35rem 0.4rem;">
                    <a href="#" class="vm-jump-barra" data-barra="${escapeHtml(row.barra)}"
                       style="color:var(--text-primary); text-decoration:underline; text-underline-offset:2px;">
                      ${escapeHtml(row.desc || '(sin descripción)')}
                    </a>
                    <div style="font-family:monospace; font-size:0.72rem; color:var(--text-secondary);">${escapeHtml(row.barra)}</div>
                  </td>
                  <td style="padding:0.35rem 0.4rem; font-size:0.8rem;">${escapeHtml(row.dest)}</td>
                  <td style="padding:0.35rem 0.4rem; text-align:right; white-space:nowrap;">${row.deltaCell}</td>
                </tr>`).join('');

            return `
                <div style="margin-bottom:0.5rem;">
                  <strong>En turno:</strong> ${escapeHtml(name)} <code>${escapeHtml(p.proveedor)}</code>${aliases}
                  — total <strong>${moneyDisplay(p.total_usd)}</strong>, mín ${moneyDisplay(p.minimo_usd)},
                  déficit <strong>${moneyDisplay(p.deficit_usd)}</strong>${okBadge}
                </div>
                <div style="margin-bottom:0.5rem; font-size:0.85rem;">
                  <strong>Δ si mueve todo lo confiable:</strong> ${moneyDisplay(p.ahorro_vs_segundo_usd)}
                  <span style="color:var(--text-secondary);">(solo líneas con precio OK; motor USD)</span>
                </div>
                <div style="overflow:auto; max-height:320px; border:1px solid var(--border-subtle);">
                  <table style="width:100%; border-collapse:collapse; font-size:0.82rem;">
                    <thead style="position:sticky; top:0; background:var(--bg-surface);">
                      <tr>
                        <th style="padding:0.4rem; text-align:left; width:2rem;">Mover</th>
                        <th style="padding:0.4rem; text-align:left;">Descripción</th>
                        <th style="padding:0.4rem; text-align:left;">Destino</th>
                        <th style="padding:0.4rem; text-align:right;">Δ</th>
                      </tr>
                    </thead>
                    <tbody>${tableRows || '<tr><td colspan="4" style="padding:0.75rem;">Sin líneas de este lab.</td></tr>'}</tbody>
                  </table>
                </div>
                <p style="margin:0.5rem 0 0; font-size:0.75rem; color:var(--text-secondary);">
                  Marcadas = van al 2º (o huérfano). Sin marcar = se quedan con <strong>${escapeHtml(name)}</strong> (submínimo parcial).
                  Clic en la descripción para ir a la línea del pedido.
                </p>
            `;
        }

        if (!cola.length) {
            colaEl.innerHTML = '<strong style="color:#10b981;">Todos los proveedores cumplen el mínimo (o no tienen mínimo configurado).</strong>';
            detEl.innerHTML = panelHtml(p);
            if (hint) hint.textContent = p ? 'Montos actualizados tras la última acción.' : '';
            return;
        }
        colaEl.innerHTML = '<strong>Cola (mayor déficit primero):</strong><ul style="margin:0.4rem 0 0 1.2rem;">' +
            cola.map((d, i) => {
                const label = d.nombre_corto || d.proveedor;
                const enTurno = i === 0 ? ' <span style="color:var(--primary-accent);font-weight:600;">← en turno</span>' : '';
                return `<li><strong>${escapeHtml(label)}</strong> <code>${escapeHtml(d.proveedor)}</code>
                  total ${moneyDisplay(d.total_usd)} / mín ${moneyDisplay(d.minimo_usd)}
                  (déficit ${moneyDisplay(d.deficit_usd)})${enTurno}</li>`;
            }).join('') +
            '</ul>';
        detEl.innerHTML = panelHtml(p);
        detEl.querySelectorAll('.vm-jump-barra').forEach(a => {
            a.addEventListener('click', (ev) => {
                ev.preventDefault();
                scrollToPedidoBarra(a.getAttribute('data-barra'));
            });
        });
        if (hint) {
            hint.textContent = vm.requiere_panel_antes_recalc
                ? 'Tras el 1er recálculo revise la tabla (confiables marcados por defecto) antes de otro %. Pulse Recalcular de nuevo para confirmar.'
                : 'Marque qué líneas redistribuir. «Aceptar submínimo» = quedarse con el lab. «Aplicar redistribución» = mover solo las marcadas.';
        }
        if (vm.requiere_panel_antes_recalc) {
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
        if (extra.barras_redistribuir !== undefined) {
            payload.barras_redistribuir = extra.barras_redistribuir;
        }
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
            showAlert(`Validar mínimos: revise panel de ${vm.activo || ''}.`, true);
        } else if (action === 'redistribuir') {
            showAlert(`Redistribución aplicada (${(extra.barras_redistribuir || []).length} líneas). Cola: ${(vm.cola || []).length}`, true);
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
    document.getElementById('btnVmRedistribuir')?.addEventListener('click', async () => {
        try {
            const cbs = [...document.querySelectorAll('.vm-redis-cb:checked')];
            const barras = cbs.map(cb => cb.getAttribute('data-barra')).filter(Boolean);
            if (!barras.length) {
                showAlert('No hay líneas marcadas. Marque qué redistribuir, o use «Aceptar submínimo».', false);
                return;
            }
            if (!confirm(`¿Mover ${barras.length} línea(s) al 2º proveedor (o huérfano)?\nLas no marcadas se quedan con el lab actual.`)) {
                return;
            }
            await callValidarMinimos('redistribuir', { barras_redistribuir: barras });
        } catch (e) {
            showAlert(e.message, false);
        }
    });

    const AMP_OVERRIDE_KEYS = new Set([
        'amplifier_enabled', 'amp_a', 'amp_b', 'amp_max_increment_pct', 'amp_floor_pct',
    ]);
    let lastDefinitivoSchema = null;
    let pendingCustomOverrides = null;

    function allDefinitivoOverrideInputs() {
        return document.querySelectorAll(
            '#definitivoOverridesHost [data-override-key], #definitivoAmpFields [data-override-key]'
        );
    }

    function valuesEqual(a, b, type) {
        if (type === 'boolean') return !!a === !!b;
        if (type === 'select') return String(a ?? '') === String(b ?? '');
        const na = Number(a);
        const nb = Number(b);
        if (!Number.isNaN(na) && !Number.isNaN(nb)) return Math.abs(na - nb) < 1e-9;
        return String(a ?? '') === String(b ?? '');
    }

    function collectDefinitivoOverrides({ allValues = false } = {}) {
        const overrides = {};
        allDefinitivoOverrideInputs().forEach((el) => {
            const key = el.getAttribute('data-override-key');
            if (!key) return;
            const type = el.getAttribute('data-override-type') || 'number';
            let current;
            if (type === 'boolean') {
                current = !!el.checked;
            } else if (type === 'select') {
                current = (el.value || '').trim();
                if (current === '' && !allValues) return;
            } else {
                const raw = (el.value || '').trim();
                if (raw === '') return;
                const num = Number(raw);
                if (Number.isNaN(num)) return;
                current = num;
            }
            if (allValues) {
                overrides[key] = current;
                return;
            }
            const defRaw = el.getAttribute('data-default');
            let defVal = defRaw;
            if (type === 'boolean') defVal = defRaw === 'true' || defRaw === '1';
            else if (type !== 'select' && defRaw != null && defRaw !== '') defVal = Number(defRaw);
            if (defRaw == null || defRaw === '' || !valuesEqual(current, defVal, type)) {
                overrides[key] = current;
            }
        });
        return overrides;
    }

    function applyValuesToDefinitivoFields(values, { markTouched = false } = {}) {
        const map = values || {};
        allDefinitivoOverrideInputs().forEach((el) => {
            const key = el.getAttribute('data-override-key');
            if (!key || !(key in map)) return;
            const type = el.getAttribute('data-override-type') || 'number';
            const val = map[key];
            if (type === 'boolean') {
                el.checked = !!val;
            } else {
                el.value = val == null ? '' : String(val);
            }
            if (markTouched) el.dataset.touched = '1';
            else delete el.dataset.touched;
        });
    }

    function fillDefinitivoFromSchemaDefaults() {
        if (!lastDefinitivoSchema) return;
        const defaults = {};
        (lastDefinitivoSchema.fields || []).forEach((f) => {
            if (f.default !== undefined) defaults[f.key] = f.default;
        });
        applyValuesToDefinitivoFields(defaults, { markTouched: false });
    }

    function updateAmpSectionVisibility(basePreset) {
        const section = document.getElementById('definitivoAmpSection');
        if (!section) return;
        const show = (basePreset || 'Normal') !== 'Conservador';
        section.style.display = show ? 'block' : 'none';
    }

    function renderDefinitivoOverrideFields(schema) {
        const host = document.getElementById('definitivoOverridesHost');
        const ampHost = document.getElementById('definitivoAmpFields');
        const note = document.getElementById('definitivoOverridesNote');
        if (!host) return;
        host.innerHTML = '';
        if (ampHost) ampHost.innerHTML = '';
        lastDefinitivoSchema = schema;
        const fields = schema.fields || [];
        const basePreset = schema.base_preset
            || document.getElementById('basePresetDefinitivo')?.value
            || 'Normal';
        updateAmpSectionVisibility(basePreset);

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
                input.checked = !!field.default;
                input.addEventListener('change', () => { input.dataset.touched = '1'; });
            } else if (field.type === 'select') {
                input = document.createElement('select');
                input.className = 'form-control';
                input.style.height = '40px';
                (field.options || []).forEach((opt) => {
                    const o = document.createElement('option');
                    o.value = opt;
                    o.textContent = opt;
                    input.appendChild(o);
                });
                if (field.default != null) input.value = String(field.default);
                input.addEventListener('change', () => { input.dataset.touched = '1'; });
            } else {
                input = document.createElement('input');
                input.type = 'number';
                input.className = 'form-control';
                input.style.height = '40px';
                if (field.step) input.step = field.step;
                if (field.default != null) {
                    input.value = String(field.default);
                    input.placeholder = String(field.default);
                }
                input.addEventListener('input', () => { input.dataset.touched = '1'; });
            }
            input.setAttribute('data-override-key', field.key);
            input.setAttribute('data-override-type', field.type || 'number');
            if (field.default !== undefined && field.default !== null) {
                input.setAttribute('data-default', String(field.default));
            }
            input.id = `ov_${field.key}`;
            wrap.appendChild(input);
            const target = (AMP_OVERRIDE_KEYS.has(field.key) && ampHost) ? ampHost : host;
            target.appendChild(wrap);
        });
        if (pendingCustomOverrides) {
            applyValuesToDefinitivoFields(pendingCustomOverrides, { markTouched: true });
            pendingCustomOverrides = null;
        }
        if (note) {
            const dead = (schema.dead_keys_excluded || []).join(', ');
            note.textContent = schema.note
                || `Nivel ${schema.nivel} / ${basePreset}: ${fields.length} knobs. Excluidos: ${dead || '—'}.`;
        }
    }

    async function loadDefinitivoOverrideSchema(attempt = 0) {
        const nivel = document.getElementById('nivelDefinitivo')?.value || 'Intermedio';
        const basePreset = document.getElementById('basePresetDefinitivo')?.value || 'Normal';
        try {
            const qs = new URLSearchParams({ nivel, base_preset: basePreset });
            const response = await fetch(`/api/pedidos/overrides-schema?${qs}`);
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

    window.__loadDefinitivoOverrideSchema = loadDefinitivoOverrideSchema;

    const nivelDefinitivoEl = document.getElementById('nivelDefinitivo');
    if (nivelDefinitivoEl) {
        nivelDefinitivoEl.addEventListener('change', () => loadDefinitivoOverrideSchema(0));
    }
    const basePresetDefinitivoEl = document.getElementById('basePresetDefinitivo');
    if (basePresetDefinitivoEl) {
        basePresetDefinitivoEl.addEventListener('change', () => loadDefinitivoOverrideSchema(0));
    }
    document.getElementById('btnResetDefinitivoOverrides')?.addEventListener('click', () => {
        fillDefinitivoFromSchemaDefaults();
        showAlert('Overrides restablecidos al preset base.', true);
    });
    loadDefinitivoOverrideSchema(0);

    async function refreshCustomPresetsList() {
        const sel = document.getElementById('customPresetSelect');
        if (!sel) return;
        try {
            const response = await fetch('/api/pedidos/presets');
            if (!response.ok) throw new Error(`presets HTTP ${response.status}`);
            const data = await response.json();
            const presets = data.presets || [];
            const prev = sel.value;
            sel.innerHTML = '<option value="">Mis presets…</option>';
            presets.forEach((p) => {
                const o = document.createElement('option');
                o.value = String(p.preset_id);
                o.textContent = `${p.nombre} (${p.nivel}/${p.base_preset})`;
                o.dataset.nombre = p.nombre;
                o.dataset.nivel = p.nivel;
                o.dataset.basePreset = p.base_preset;
                o.dataset.overrides = JSON.stringify(p.overrides || {});
                sel.appendChild(o);
            });
            if (prev && [...sel.options].some(o => o.value === prev)) sel.value = prev;
        } catch (err) {
            console.warn('custom presets list failed', err);
        }
    }

    document.getElementById('btnSaveCustomPreset')?.addEventListener('click', async () => {
        hideAlert();
        const nombre = (document.getElementById('customPresetName')?.value || '').trim();
        if (!nombre) {
            showAlert('Indique un nombre para el preset personalizado.', false);
            return;
        }
        const nivel = document.getElementById('nivelDefinitivo')?.value || 'Intermedio';
        const base_preset = document.getElementById('basePresetDefinitivo')?.value || 'Normal';
        const overrides = collectDefinitivoOverrides({ allValues: true });
        try {
            const response = await fetch('/api/pedidos/presets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nombre, nivel, base_preset, overrides }),
            });
            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || `HTTP ${response.status}`);
            }
            const saved = await response.json();
            showAlert(`Preset «${saved.nombre}» guardado (id ${saved.preset_id}).`, true);
            await refreshCustomPresetsList();
            const sel = document.getElementById('customPresetSelect');
            if (sel) sel.value = String(saved.preset_id);
        } catch (error) {
            showAlert(error.message, false);
        }
    });

    document.getElementById('btnLoadCustomPreset')?.addEventListener('click', async () => {
        hideAlert();
        const sel = document.getElementById('customPresetSelect');
        const opt = sel?.selectedOptions?.[0];
        if (!opt || !opt.value) {
            showAlert('Seleccione un preset personalizado.', false);
            return;
        }
        let overrides = {};
        try { overrides = JSON.parse(opt.dataset.overrides || '{}'); } catch (e) { overrides = {}; }
        const nivelEl = document.getElementById('nivelDefinitivo');
        const baseEl = document.getElementById('basePresetDefinitivo');
        if (nivelEl && opt.dataset.nivel) nivelEl.value = opt.dataset.nivel;
        if (baseEl && opt.dataset.basePreset) baseEl.value = opt.dataset.basePreset;
        const nameEl = document.getElementById('customPresetName');
        if (nameEl) nameEl.value = opt.dataset.nombre || '';
        pendingCustomOverrides = overrides;
        await loadDefinitivoOverrideSchema(0);
        showAlert(`Preset «${opt.dataset.nombre}» cargado.`, true);
    });

    document.getElementById('btnDeleteCustomPreset')?.addEventListener('click', async () => {
        hideAlert();
        const sel = document.getElementById('customPresetSelect');
        const id = sel?.value;
        if (!id) {
            showAlert('Seleccione un preset para borrar.', false);
            return;
        }
        if (!confirm('¿Borrar este preset personalizado de la BD?')) return;
        try {
            const response = await fetch(`/api/pedidos/presets/${encodeURIComponent(id)}`, { method: 'DELETE' });
            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || `HTTP ${response.status}`);
            }
            showAlert('Preset borrado.', true);
            await refreshCustomPresetsList();
        } catch (error) {
            showAlert(error.message, false);
        }
    });

    refreshCustomPresetsList();


    const btnRegenerarDefinitivo = document.getElementById('btnRegenerarDefinitivo');
    if (btnRegenerarDefinitivo) {
        btnRegenerarDefinitivo.addEventListener('click', async () => {
            hideAlert();
            const resultSection = document.getElementById('generarResultSection');
            if (!resultSection || resultSection.style.display === 'none') {
                showAlert("Primero ejecute Generar (Sencillo) para ver la Comparativa.", false);
                return;
            }
            promptOverridesBeforeGenerar();
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

    const btnEnviarPedido = document.getElementById('btnEnviarPedido');
    if (btnEnviarPedido) {
        btnEnviarPedido.addEventListener('click', async () => {
            if (window.__bandejaMode && window.__bandejaMode.propuesta_id) {
                try {
                    const id = window.__bandejaMode.propuesta_id;
                    const propuesto = (lastGenerarResult && lastGenerarResult.pedido_propuesto) || [];
                    const comparativa = (lastGenerarResult && lastGenerarResult.comparativa_cantidades) || [];
                    await fetch(`/api/pedidos/bandeja/${id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            pedido_propuesto: propuesto,
                            comparativa_cantidades: comparativa,
                        }),
                    });
                    const r = await fetch(`/api/pedidos/bandeja/${id}/enviar`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            revision: window.__bandejaMode.revision,
                            snapshot_hash: window.__bandejaMode.snapshot_hash,
                        }),
                    });
                    const data = await r.json().catch(() => ({}));
                    if (!r.ok) {
                        const d = data.detail;
                        if (d && d.error === 'requiere_analizar') {
                            showAlert(d.message || 'Hay desvíos: revise Comparativa.', false);
                            return;
                        }
                        throw new Error(typeof d === 'string' ? d : 'Error al enviar');
                    }
                    showAlert(data.aviso || `Enviando #${id}`, true);
                    if (typeof window.refreshBandejaBadges === 'function') window.refreshBandejaBadges();
                } catch (err) {
                    showAlert(err.message || String(err), false);
                }
                return;
            }
            showAlert(
                'Enviar pedido (FTP/Telegram): abra Bandeja de pedidos o cargue una propuesta con Analizar. Spec ADR-0029/0030.',
                false
            );
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

            promptOverridesBeforeGenerar();

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
                const nChg = (data.comparativa_cantidades || []).filter(r =>
                    !isComparativaIdentityRow(r)
                ).length;
                showAlert(
                    `Generar Sencillo listo: ${nComp} filas Comparativa (${nChg} con cambio unidad/barra), ${nProp} líneas Propuesto (${data.meta?.preset || ''}).`,
                    true
                );
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

    // --- Moneda trabajo + MonedaOferta por lab ---
    async function loadMonedaConfig() {
        const sel = document.getElementById('monedaTrabajo');
        const bcvEl = document.getElementById('dolarbcvLabel');
        const table = document.getElementById('proveedorMonedaTable');
        try {
            const resp = await fetch('/api/pedidos/moneda-config');
            if (!resp.ok) throw new Error('No se pudo cargar moneda-config');
            const data = await resp.json();
            fxState.moneda_trabajo = (data.moneda_trabajo || 'USD').toUpperCase();
            fxState.dolarbcv = data.dolarbcv != null ? Number(data.dolarbcv) : null;
            if (sel) sel.value = fxState.moneda_trabajo === 'VES' ? 'VES' : 'USD';
            if (bcvEl) {
                bcvEl.textContent = fxState.dolarbcv
                    ? Number(fxState.dolarbcv).toLocaleString('es-VE', { maximumFractionDigits: 4 })
                    : 'n/d';
            }
            if (table) {
                const rows = (data.proveedores || []).map(p => {
                    const mon = (p.moneda_oferta || 'USD').toUpperCase();
                    return `<tr>
                        <td style="padding:0.35rem 0.5rem;">${escapeHtml(p.nombre_corto || p.cod_prov)}</td>
                        <td style="padding:0.35rem 0.5rem; font-family:monospace; font-size:0.75rem;">${escapeHtml(p.cod_prov)}</td>
                        <td style="padding:0.35rem 0.5rem;">
                          <select data-prov-id="${p.proveedor_id}" class="prov-moneda-sel form-control" style="height:32px; font-size:0.8rem;">
                            <option value="USD" ${mon === 'USD' ? 'selected' : ''}>USD</option>
                            <option value="VES" ${mon === 'VES' ? 'selected' : ''}>VES (Bs)</option>
                          </select>
                        </td>
                      </tr>`;
                }).join('');
                table.innerHTML = `
                  <table style="width:100%; border-collapse:collapse;">
                    <thead><tr>
                      <th style="text-align:left; padding:0.35rem 0.5rem;">Lab</th>
                      <th style="text-align:left; padding:0.35rem 0.5rem;">CodProv</th>
                      <th style="text-align:left; padding:0.35rem 0.5rem;">Oferta en</th>
                    </tr></thead>
                    <tbody>${rows || '<tr><td colspan="3" style="padding:0.5rem;">Sin proveedores</td></tr>'}</tbody>
                  </table>`;
                table.querySelectorAll('.prov-moneda-sel').forEach(s => {
                    s.addEventListener('change', async () => {
                        const id = s.getAttribute('data-prov-id');
                        try {
                            const r = await fetch(`/api/pedidos/moneda-config/proveedor/${id}`, {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ moneda_oferta: s.value }),
                            });
                            if (!r.ok) {
                                const err = await r.json().catch(() => ({}));
                                throw new Error(err.detail || 'Error al guardar');
                            }
                            showAlert(`Moneda oferta actualizada (${s.value}).`, true);
                        } catch (e) {
                            showAlert(e.message, false);
                        }
                    });
                });
            }
        } catch (e) {
            if (bcvEl) bcvEl.textContent = 'error';
            console.warn(e);
        }
    }

    document.getElementById('monedaTrabajo')?.addEventListener('change', async (ev) => {
        const val = ev.target.value;
        try {
            const r = await fetch('/api/pedidos/moneda-config/trabajo', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ moneda_trabajo: val }),
            });
            if (!r.ok) {
                const err = await r.json().catch(() => ({}));
                throw new Error(err.detail || 'Error al guardar');
            }
            const data = await r.json();
            fxState.moneda_trabajo = (data.moneda_trabajo || val).toUpperCase();
            if (data.dolarbcv != null) fxState.dolarbcv = Number(data.dolarbcv);
            if (lastGenerarResult) {
                lastGenerarResult.meta = { ...(lastGenerarResult.meta || {}), ...fxState };
                renderGenerarResult(lastGenerarResult, { scroll: false });
            }
            showAlert(
                fxState.moneda_trabajo === 'VES'
                    ? 'Pantalla en bolívares (desvío sigue en USD; Δ reconvertido con BCV).'
                    : 'Pantalla en dólares.',
                true
            );
        } catch (e) {
            showAlert(e.message, false);
        }
    });

    loadMonedaConfig();
});
