document.addEventListener('DOMContentLoaded', () => {
    console.log('--- Static Assets Version 24 Loaded ---');
    // DOM Elements
    const tableBody = document.getElementById('tableBody');
    const searchInput = document.getElementById('searchInput');
    const filterDate = document.getElementById('filterDate');
    const filterDateHasta = document.getElementById('filterDateHasta');
    const filterStatus = document.getElementById('filterStatus');
    const refreshBtn = document.getElementById('refreshBtn');
    // Cashflow Filters
    const cashflowDateDesde = document.getElementById('cashflowDateDesde');
    const cashflowDateHasta = document.getElementById('cashflowDateHasta');
    const refreshCashflowBtn = document.getElementById('refreshCashflowBtn');

    // Summaries
    const totalDocsStr = document.getElementById('totalDocs');
    const totalSaldoBsStr = document.getElementById('totalSaldoBs');
    const totalSaldoUsdStr = document.getElementById('totalSaldoUsd');
    const selectedTotalBsStr = document.getElementById('selectedTotalBs');
    const selectedTotalUsdStr = document.getElementById('selectedTotalUsd');

    // Forecast Consolidated Params
    const paramFechaCero = document.getElementById('paramFechaCero');
    const paramCajaUsd = document.getElementById('paramCajaUsd');
    const paramCajaBs = document.getElementById('paramCajaBs');
    const paramRetardoDays = document.getElementById('paramRetardoDays');
    const fcToggleDelay = document.getElementById('fcToggleDelay');

    // Action Bar & Selection
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const planningActionBar = document.getElementById('planningActionBar');
    const planFecha = document.getElementById('planFecha');
    const planBanco = document.getElementById('planBanco');
    const submitPlanBtn = document.getElementById('submitPlanBtn');
    const cancelPlanBtn = document.getElementById('cancelPlanBtn');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');

    // Forecast & Forecast Consolidated Elements
    const fsDateDesde = document.getElementById('fsDateDesde');
    const fsDateHasta = document.getElementById('fsDateHasta');
    const fcDateDesde = document.getElementById('fcDateDesde');
    const fcDateHasta = document.getElementById('fcDateHasta');
    const fcDateDesdePlan = document.getElementById('fcDateDesde'); // duplicated just in case

    const refreshForecastSalesBtn = document.getElementById('refreshForecastSalesBtn');
    const refreshForecastConsolidatedBtn = document.getElementById('refreshForecastConsolidatedBtn');

    window.currentData = [];
    window.globalRetConfig = {
        TasaEmisionSource: 'SACOMP',
        MontoUsdSource: 'Calculado'
    };

    // ── Modo Pago Múltiple ──────────────────────────────────────────────
    window.getItemKey = (item) => `${item.CodProv}_${item.NumeroD}`;
    // Store multi-pay selections globally across pages/filters
    window.multiPayMode = true;
    window.multiPaySelection = new Set();     // Set<String rowKey>
    window.multiPaySelectionData = new Map(); // Map<String rowKey, item>


    // Fetch Global Configs on Load
    const loadConfigs = async () => {
        try {
            // 1. General Settings
            const res1 = await fetch('/api/procurement/settings');
            if (res1.ok) {
                const json = await res1.json();
                window.globalRetConfig = { ...window.globalRetConfig, ...(json.data || {}) };
            }
            // 2. Retenciones/ISLR Config (ValorUT)
            const res2 = await fetch('/api/retenciones/config');
            if (res2.ok) {
                const json = await res2.json();
                window.globalRetConfig = { ...window.globalRetConfig, ...(json.data || {}) };
            }

            // Hydrate the Global Settings Form inputs dynamically
            const settingsForm = document.getElementById('globalSettingsForm');
            if (settingsForm && window.globalRetConfig) {
                const cfg = window.globalRetConfig;
                if (cfg.TasaEmisionSource) {
                    const r = settingsForm.querySelector(`input[name="TasaEmisionSource"][value="${cfg.TasaEmisionSource}"]`);
                    if (r) r.checked = true;
                }
                if (cfg.MontoUSDSource) {
                    const r = settingsForm.querySelector(`input[name="MontoUSDSource"][value="${cfg.MontoUSDSource}"]`);
                    if (r) r.checked = true;
                }
                if (cfg.LimiteCarga != null) {
                    const el = document.getElementById('settingsLimiteCarga');
                    if (el) el.value = cfg.LimiteCarga;
                }
                if (cfg.ToleranceSaldo != null) {
                    const el = document.getElementById('settingsToleranceSaldo');
                    if (el) el.value = cfg.ToleranceSaldo;
                }
            }
        } catch (e) {
            console.error('Failed to load global configs:', e);
        }
    };
    loadConfigs();
    // Provider Modals
    const providerCondModal = document.getElementById('providerCondModal');
    const editProviderCondModal = document.getElementById('editProviderCondModal');
    const providersTableBody = document.getElementById('providersTableBody');
    const editProvForm = document.getElementById('editProvForm');
    const providerSearchInput = document.getElementById('providerSearchInput');
    const providerActivoCheck = document.getElementById('providerActivoCheck');

    let fetchTimeout;

    // Currency Formatters
    const bsFormatter = new Intl.NumberFormat('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format;
    const usdFormatter = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 4 }).format;
    const roundBs = (n) => Math.round((n + Number.EPSILON) * 100) / 100;
    const roundUSD = (n) => Math.round((n + Number.EPSILON) * 10000) / 10000;

    const formatBs = (val) => `Bs ${bsFormatter(val)}`;

    // Safely evaluate SQL BIT or boolean strings
    const hasRet = (item) => item.Has_Retencion === true || item.Has_Retencion === 1 || String(item.Has_Retencion) === '1' || String(item.Has_Retencion).toLowerCase() === 'true';


    // === Cashflow Params State Management ===
    const loadCashflowParams = () => {
        if (!paramFechaCero) return;
        const saved = JSON.parse(localStorage.getItem('cashflowParams') || '{}');

        setDateValue(paramFechaCero, saved.fechaCero || new Date().toISOString().split('T')[0]);
        paramCajaUsd.value = saved.cajaUsd !== undefined ? saved.cajaUsd : 0;
        paramCajaBs.value = saved.cajaBs !== undefined ? saved.cajaBs : 0;
        paramRetardoDays.value = saved.retardoDays !== undefined ? saved.retardoDays : 1;
        if (fcToggleDelay) {
            // Default to true if not explicitly saved as false
            fcToggleDelay.checked = saved.toggleDelay !== false;
        }
    };

    window.saveCashflowParams = () => {
        const params = {
            fechaCero: getDateValue(paramFechaCero),
            cajaUsd: parseFloat(paramCajaUsd.value) || 0,
            cajaBs: parseFloat(paramCajaBs.value) || 0,
            retardoDays: parseInt(paramRetardoDays.value) || 0,
            toggleDelay: fcToggleDelay ? fcToggleDelay.checked : false
        };
        localStorage.setItem('cashflowParams', JSON.stringify(params));

        // Force refresh next time dashboard is opened
        if (window.forecastConsChartInstance) {
            window.forecastConsChartInstance.destroy();
            window.forecastConsChartInstance = null;
        }

        // Refresh forecast immediately if we are viewing it
        if (document.querySelector('.view-section.active')?.id === 'view-forecast-consolidated') {
            fetchForecastConsolidated();
        }
    };

    // Auto-save listeners
    paramFechaCero?.addEventListener('change', saveCashflowParams);
    paramCajaUsd?.addEventListener('change', saveCashflowParams);
    paramCajaBs?.addEventListener('change', saveCashflowParams);
    paramRetardoDays?.addEventListener('change', saveCashflowParams);

    if (fcToggleDelay) {
        fcToggleDelay.addEventListener('change', () => {
            saveCashflowParams();
        });
    }

    // ==========================================

    // Date Formatter (DD/MM/YYYY)
    const formatDate = (dateString) => {
        if (!dateString) return '-';
        // Handle ISO dates yyyy-mm-dd
        if (dateString.includes('-')) {
            const parts = dateString.split('T')[0].split('-');
            if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
        }
        const date = new Date(dateString);
        const d = String(date.getDate()).padStart(2, '0');
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const y = date.getFullYear();
        return `${d}/${m}/${y}`;
    };

    // --- Date Input Helper (Force DD/MM/YYYY display) ---
    // --- Date Input Helper ---
    // Note: Switching between 'text' and 'date' types dynamically causes breaking issues 
    // on iOS Safari/Brave and desyncs when typing manually. Falling back to native HTML5.
    const setupDateInput = (input) => {
        if (!input) return;
        input.type = 'date';
        // Remove any old event listeners if they were attached by forcing a clone, or just trust the new code doesn't attach them
    };

    const getDateValue = (input) => {
        if (!input) return "";
        return input.value || "";
    };

    const setDateValue = (input, val) => {
        if (!input) return;
        input.type = 'date';
        // Native date inputs require YYYY-MM-DD format
        if (val && val.includes('T')) {
            input.value = val.split('T')[0];
        } else {
            input.value = val;
        }
    };
    // -----------------------------------------------------
    // -----------------------------------------------------

    // Generic Table Sorting
    window.setupSortableTable = (tableId, arrayObjString, renderFuncName, sortClass = 'sortable', defaultSortKey = '') => {
        let sortCfg = { key: defaultSortKey, direction: 'asc' };
        document.querySelectorAll(`#${tableId} th.${sortClass}`).forEach(header => {
            header.addEventListener('click', () => {
                const key = header.getAttribute('data-sort');
                if (!key) return;

                if (sortCfg.key === key) {
                    sortCfg.direction = sortCfg.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    sortCfg.key = key;
                    sortCfg.direction = 'asc';
                }

                document.querySelectorAll(`#${tableId} th.${sortClass} .sort-icon`).forEach(icon => {
                    icon.classList.remove('active', 'desc');
                });
                header.querySelector('.sort-icon').classList.add('active');
                if (sortCfg.direction === 'desc') header.querySelector('.sort-icon').classList.add('desc');

                let arr = window[arrayObjString];
                if (!arr) return;

                arr.sort((a, b) => {
                    let valA = a[sortCfg.key] !== undefined && a[sortCfg.key] !== null ? a[sortCfg.key] : '';
                    let valB = b[sortCfg.key] !== undefined && b[sortCfg.key] !== null ? b[sortCfg.key] : '';
                    if (typeof valA === 'string') valA = valA.toLowerCase();
                    if (typeof valB === 'string') valB = valB.toLowerCase();
                    if (valA < valB) return sortCfg.direction === 'asc' ? -1 : 1;
                    if (valA > valB) return sortCfg.direction === 'asc' ? 1 : -1;
                    return 0;
                });

                if (typeof window[renderFuncName] === 'function') {
                    window[renderFuncName]();
                }
            });
        });
    };

    // Utility for strict financial rounding to avoid floating point cent errors
    const roundFixed = (num) => Math.round((num + Number.EPSILON) * 100) / 100;

    const calcISLR = (base, rate, codProv, tipoPersonaOverride) => {
        if (!rate || rate <= 0) return 0;
        let isNatural = false;
        if (tipoPersonaOverride === 'PJ') {
            isNatural = false;
        } else if (tipoPersonaOverride === 'PN') {
            isNatural = true;
        } else if (codProv) {
            const firstChar = String(codProv).trim().toUpperCase().charAt(0);
            isNatural = (firstChar === 'V' || firstChar === 'E' || firstChar === 'P');
        }

        const ut = parseFloat(window.globalRetConfig?.ValorUT) || 9.00;
        let ret = base * rate;
        if (isNatural) {
            const sustraendo = rate * ut * 83.3334;
            ret = Math.max(0, ret - sustraendo);
        }
        return roundFixed(ret);
    };

    const calculateInvoiceFinancials = (cxp, { tasaDia, aplicaIndex, aplicaIndexIva, pctDesc, descBasePct, islrRate, deduceIvaBase = true, deduceIvaPP = true }) => {
        const historicalTasa = (cxp.Factor && cxp.Factor > 0 && (window.globalRetConfig?.TasaEmisionSource === 'SACOMP' || window.globalRetConfig?.TasaEmisionSource === 'SACOMP_FACTOR')) 
            ? parseFloat(cxp.Factor) 
            : parseFloat(cxp.TasaEmision) || 1;

        const currentTasa = (aplicaIndex && tasaDia > 0) ? tasaDia : historicalTasa;

        const tGravableUsd = roundUSD((parseFloat(cxp.TGravable) || 0) / historicalTasa);
        const exentoOrigBs = Math.max(0, (parseFloat(cxp.Monto) || 0) - (parseFloat(cxp.TGravable) || 0) - (parseFloat(cxp.MtoTax) || 0));
        const exentoUsd = roundUSD(exentoOrigBs / historicalTasa);

        let baseBs, exentoBs;

        if (aplicaIndex) {
            baseBs   = roundFixed(tGravableUsd * currentTasa);
            exentoBs = roundFixed(exentoUsd * currentTasa);
        } else {
            baseBs   = roundFixed(parseFloat(cxp.TGravable) || 0);
            exentoBs = roundFixed(exentoOrigBs);
        }
        
        let baseBsLegalParaIva = baseBs;
        let exentoBsLegalParaIva = exentoBs;

        const pctPP = parseFloat(pctDesc) || 0;
        const pctBase = parseFloat(descBasePct) || 0;
        let fDescuento = 1.0;
        let fDescuentoIva = 1.0;
        
        if (pctPP > 0 || pctBase > 0) {
            fDescuento = (1.0 - (pctBase / 100.0)) * (1.0 - (pctPP / 100.0));
            baseBs   = roundFixed(baseBs * fDescuento);
            exentoBs = roundFixed(exentoBs * fDescuento);
            
            const factIvaBase = (deduceIvaBase !== false) ? (1.0 - (pctBase / 100.0)) : 1.0;
            const factIvaPP = (deduceIvaPP !== false) ? (1.0 - (pctPP / 100.0)) : 1.0;
            fDescuentoIva = factIvaBase * factIvaPP;
            
            baseBsLegalParaIva = roundFixed(baseBsLegalParaIva * fDescuentoIva);
            exentoBsLegalParaIva = roundFixed(exentoBsLegalParaIva * fDescuentoIva);
        }

        // --- Granular IVA Indexation Logic ---
        let ivaBs;
        const indexaIVA = aplicaIndexIva !== undefined ? aplicaIndexIva : (cxp.IndexaIVA ?? true);
        
        if (indexaIVA && aplicaIndex) {
            ivaBs = roundFixed(baseBsLegalParaIva * 0.16); 
        } else {
            // Keep historical IVA value, but respect discounts if applied
            let historicalIva = parseFloat(cxp.MtoTax) || 0;
            if (fDescuentoIva < 1.0) {
                historicalIva = roundFixed(historicalIva * fDescuentoIva);
            }
            ivaBs = historicalIva;
        }

        const newMtoBs = roundFixed(baseBs + ivaBs + exentoBs);

        const isReten = String(cxp.EsReten) === '1' || cxp.EsReten === true;
        let porctRet  = parseFloat(cxp.PorctRet) || 0;
        if (isReten && isNaN(porctRet)) porctRet = 75; 

        const ret_iva_abonada = parseFloat(cxp.RetencionIvaAbonada) || 0;
        const ret_islr_abonada = parseFloat(cxp.RetencionIslrAbonada) || 0;

        const retencionBs = (isReten && ret_iva_abonada === 0) ? roundFixed(ivaBs * (porctRet / 100.0)) : 0;
        
        let ivaAPagarBs = roundFixed(ivaBs - retencionBs - ret_iva_abonada);
        if (ivaAPagarBs < 0) ivaAPagarBs = 0;
        
        let retenIslrBs = 0;
        if (ret_islr_abonada === 0) {
            retenIslrBs = calcISLR((baseBsLegalParaIva + exentoBsLegalParaIva), (parseFloat(islrRate) || 0), cxp.CodProv, cxp.TipoPersona);
        }

        let mtoTotalUsd = 0;
        if (pctPP === 0 && pctBase === 0 && (window.globalRetConfig?.MontoUsdSource === 'SACOMP' || window.globalRetConfig?.MontoUsdSource === 'SACOMP_MONOMEX') && cxp.MontoMEx > 0) {
            mtoTotalUsd = parseFloat(cxp.MontoMEx);
        } else {
            mtoTotalUsd = roundUSD(newMtoBs / (currentTasa > 0 ? currentTasa : 1));
        }

        const portalUsdAbonado = parseFloat(cxp.TotalUsdAbonado) || 0;
        const saintPagosBs = parseFloat(cxp.MtoPagos) || 0;
        const portalPagosBs = parseFloat(cxp.TotalBsAbonado) || 0;
        
        let estimatedSaintUsd = 0;
        if (saintPagosBs > portalPagosBs) {
             let origMonto = parseFloat(cxp.Monto) || 1;
             if (origMonto <= 0) origMonto = 1;
             let p = saintPagosBs / origMonto;
             if (p > 1) p = 1;
             estimatedSaintUsd = mtoTotalUsd * p;
        }
        
        let amortizedUsd = Math.max(portalUsdAbonado, estimatedSaintUsd);

        let remainingUsd = mtoTotalUsd - amortizedUsd;
        if (remainingUsd < 0) remainingUsd = 0;
        
        let saldoTargetBs = 0;
        
        // ULTIMATE FALLBACK: if cxp.Saldo is explicitly 0, the ERP considers the invoice dead.
        let deudaDb = parseFloat(cxp.Saldo) || 0;
        let isFullyPaid = (deudaDb <= 0 && (parseFloat(cxp.Monto) || 0) > 0);

        if (isFullyPaid) {
            remainingUsd = 0;
            saldoTargetBs = 0;
        } else if (aplicaIndex) {
            // Reflects 'temporal reality': only the unpaid portion in USD is multiplied by the current BCV rate
            saldoTargetBs = roundFixed(remainingUsd * currentTasa);
        } else {
            // Take the Bolivar amount directly to avoid rounding drift from USD conversion back to BS
            let abonoBs = 0;
            const portalPagos = parseFloat(cxp.TotalBsAbonado) || 0;
            const saintPagos = parseFloat(cxp.MtoPagos) || 0;
            abonoBs = Math.max(portalPagos, saintPagos);
            
            saldoTargetBs = roundFixed(newMtoBs - abonoBs);
            if (saldoTargetBs < 0) saldoTargetBs = 0;
        }
        
        let finalBs = roundFixed(saldoTargetBs - retencionBs - retenIslrBs);
        if (finalBs < 0) finalBs = 0;
        if (isFullyPaid) finalBs = 0; // Double ensure no negative/micro cents create ghosts

        const equivUsd = currentTasa > 0 ? (finalBs / currentTasa) : 0;
            
        let descUsdMonto = 0;
        let descBaseUsdMonto = 0;
        let descPPUsdMonto = 0;
        if(fDescuento < 1.0) {
           descUsdMonto = roundUSD(mtoTotalUsd * (1.0 - fDescuento));
           descBaseUsdMonto = roundUSD(mtoTotalUsd * (pctBase / 100.0));
           descPPUsdMonto = roundUSD((mtoTotalUsd - descBaseUsdMonto) * (pctPP / 100.0));
        }

        const origTotalUsd = (cxp.MontoMEx > 0) ? parseFloat(cxp.MontoMEx) : ((parseFloat(cxp.Monto) || 0) / historicalTasa);

        return {
            historicalTasa,
            currentTasa,
            baseBs,
            exentoBs,
            ivaBs,
            retencionBs,
            ivaAPagarBs,
            retenIslrBs,
            saldoTargetBs,
            finalBs,
            equivUsd,
            descUsdMonto,
            descBaseUsdMonto,
            descPPUsdMonto,
            mtoTotalUsd,
            origTotalUsd,
            subtotalUsd: (parseFloat(cxp.TotalPrd) || 0) / historicalTasa,
            fletesUsd: (parseFloat(cxp.Fletes) || 0) / historicalTasa,
            d1Usd: (parseFloat(cxp.Descto1) || 0) / historicalTasa,
            d2Usd: (parseFloat(cxp.Descto2) || 0) / historicalTasa,
            ivaUsd: currentTasa > 0 ? (ivaBs / currentTasa) : 0
        };
    };

    // Determine status based on dates, balances and planned status
    const getBaseStatus = (item) => {
        const tasaAct = parseFloat(item.TasaActual) || 1;
        const tasaEmi = parseFloat(item.TasaEmision) || 1;
        
        // We assume indexation applies if today's rate is higher than emission
        const indexado = tasaAct > tasaEmi;

        const fin = calculateInvoiceFinancials(item, {
            tasaDia: tasaAct,
            aplicaIndex: indexado,
            pctDesc: 0,
            islrRate: 0
        });

        const tolerance = parseFloat(window.globalRetConfig?.ToleranceSaldo) || 0.50;
        if (fin.finalBs <= tolerance) {
            return 'Pagado';
        }

        const now   = new Date();
        const vDate = new Date(item.FechaV);
        if (vDate < now) return 'Vencido';

        return 'Pendiente';
    };

    const getStatusHtml = (item) => {
        const base = getBaseStatus(item);
        let html = '';
        if (base === 'Pagado') html = `<span class="status-badge status-paid">Pagado</span>`;
        if (base === 'Vencido') html = `<span class="status-badge status-overdue">Vencido</span>`;
        if (base === 'Pendiente') html = `<span class="status-badge status-pending">Pendiente</span>`;

        // Attributes (Flags)
        const flags = [];
        if (item.Plan_ID) flags.push(`<span title="Planificado: Banco ${item.Plan_Banco}">🗓️</span>`);
        if (item.Has_Abonos) flags.push(`<span title="Tiene Abonos Parciales">💵</span>`);
        if (hasRet(item)) flags.push(`<span title="Tiene Retenciones">🧾</span>`);

        if (flags.length > 0) {
            html += ` <div style="display: inline-flex; gap: 0.2rem; filter: grayscale(0.2); font-size: 1.1em;">${flags.join('')}</div>`;
        }

        return html;
    };

    const fetchData = async () => {
        tableBody.innerHTML = `<tr><td colspan="9" class="loading-cell"><div class="loader"></div><p>Cargando datos...</p></td></tr>`;

        try {
            const search = encodeURIComponent(searchInput.value);
            let url = `/api/cuentas-por-pagar?search=${search}`;
            const dDesde = getDateValue(filterDate);
            const dHasta = getDateValue(filterDateHasta);
            if (dDesde) url += `&desde=${dDesde}`;
            if (dHasta) url += `&hasta=${dHasta}`;
            const response = await fetch(url);

            if (!response.ok) throw new Error('Error al obtener datos del servidor');

            const json = await response.json();
            window.currentData = json.data || [];

            // Sort by FechaE ascending by default
            window.currentData.sort((a, b) => {
                const dateA = a.FechaE || '';
                const dateB = b.FechaE || '';
                if (dateA < dateB) return 1;
                if (dateA > dateB) return -1;
                return 0;
            });

            // Background audit for inverted dates (Emission > Expiration)
            const invertedDates = window.currentData.filter(item => {
                const dateE = (item.FechaE || '').split('T')[0];
                const dateV = (item.FechaV || '').split('T')[0];
                return dateE && dateV && dateE > dateV;
            });
            if (invertedDates.length > 0) {
                const numStr = invertedDates.map(i => i.NumeroD).join(', ');
                window.showToast(`Auditoría: Se encontraron ${invertedDates.length} facturas con fechas invertidas (Emisión > Vencimiento): ${numStr}`, 'warning', 12000);
            }

            window.renderTable();
        } catch (error) {
            console.error('Fetch error:', error);
            tableBody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--danger); padding: 2rem;">Error al cargar datos.<br></td></tr>`;
        }
    };

    const recalculateSelection = () => {
        const selectedCheckboxes = document.querySelectorAll('.row-checkbox:checked');
        let selBs = 0;
        let selUsd = 0;

        if (window.multiPayMode) {
            // En modo múltiple: calcular desde el Set completo (incluye facturas fuera de vista)
            window.multiPaySelectionData.forEach(item => {
                const saldo = parseFloat(item.Saldo) || 0;
                const tasaEmi = parseFloat(item.TasaEmision) || 1;
                const tasaAct = parseFloat(item.TasaActual) || 1;
                selBs += (saldo / tasaEmi) * tasaAct;
                selUsd += saldo / tasaEmi;
            });
        } else {
            selectedCheckboxes.forEach(cb => {
                const nroUnico = parseInt(cb.getAttribute('data-nrounico'));
                const item = window.currentData.find(d => d.NroUnico === nroUnico);
                if (item) {
                    const saldo = parseFloat(item.Saldo) || 0;
                    const tasaEmi = parseFloat(item.TasaEmision) || 1;
                    const tasaAct = parseFloat(item.TasaActual) || 1;
                    selBs += (saldo / tasaEmi) * tasaAct;
                    selUsd += saldo / tasaEmi;
                }
            });
        }

        selectedTotalBsStr.textContent = formatBs(selBs);
        selectedTotalUsdStr.textContent = usdFormatter(selUsd);

        // Cuenta efectiva para mostrar controles
        const effectiveCount = window.multiPayMode
            ? window.multiPaySelection.size
            : selectedCheckboxes.length;

        // Show/hide action bar
        if (effectiveCount > 0) {
            planningActionBar.style.display = 'flex';
        } else {
            planningActionBar.style.display = 'none';
        }

        const btnGenerarRetencion = document.getElementById('btnGenerarRetencion');
        if (btnGenerarRetencion) {
            btnGenerarRetencion.style.display = effectiveCount >= 1 ? 'inline-flex' : 'none';
            if (effectiveCount >= 1) {
                let selItems = [];
                if (window.multiPayMode) {
                    selItems = Array.from(window.multiPaySelectionData.values());
                } else {
                    document.querySelectorAll('.row-checkbox:checked').forEach(cb => {
                        const idx = cb.getAttribute('data-index');
                        if (window.currentData[idx]) selItems.push(window.currentData[idx]);
                    });
                }
                const itemsConIva = selItems.filter(i => (parseFloat(i.TGravable) || 0) > 0 || (parseFloat(i.MtoTax) || 0) > 0);
                const sinRetencion = itemsConIva.filter(i => (parseFloat(i.RetencionIvaAbonada) || 0) === 0 && !i.Has_Retencion);
                
                if (itemsConIva.length > 0 && sinRetencion.length > 0) {
                    // Amarillo si hay algo pendiente por retener
                    btnGenerarRetencion.style.color = '#eab308';
                    btnGenerarRetencion.style.borderColor = 'rgba(234,179,8,0.4)';
                } else {
                    // Verde si TODAS ya tienen retención o NINGUNA tiene IVA
                    btnGenerarRetencion.style.color = '#10b981';
                    btnGenerarRetencion.style.borderColor = 'rgba(16,185,129,0.4)';
                }
            }
        }

        const btnGenerarRetencionIslr = document.getElementById('btnGenerarRetencionIslr');
        if (btnGenerarRetencionIslr) {
            btnGenerarRetencionIslr.style.display = effectiveCount >= 1 ? 'inline-flex' : 'none';
        }

        const btnProcesarPago = document.getElementById('btnProcesarPago');
        if (btnProcesarPago) {
            btnProcesarPago.style.display = effectiveCount >= 1 ? 'inline-flex' : 'none';
        }

        // Disable checkboxes from other providers if 1+ selected
        const selectedProvider = window.multiPaySelectionData.size > 0 
            ? window.multiPaySelectionData.values().next().value.CodProv 
            : null;
        
        document.querySelectorAll('.row-checkbox').forEach(cb => {
            if (selectedProvider) {
                const item = window.currentData[cb.getAttribute('data-index')];
                if (item && item.CodProv !== selectedProvider && !cb.checked) {
                    cb.disabled = true;
                    cb.parentElement.style.opacity = '0.5';
                } else {
                    cb.disabled = false;
                    cb.parentElement.style.opacity = '1';
                }
            } else {
                cb.disabled = false;
                cb.parentElement.style.opacity = '1';
            }
        });

        // Update 'Select All' state (solo aplica a filas visibles)
        const allVisible = document.querySelectorAll('.row-checkbox:not(:disabled)').length;
        selectAllCheckbox.checked = allVisible > 0 && document.querySelectorAll('.row-checkbox:checked').length === allVisible;
    };

    window.renderTable = () => {
        const baseStatusValue = document.getElementById('filterStatusBase')?.value || 'TODOS_ACTIVOS';
        const requiresPlan = document.getElementById('filterAttrPlanificado')?.checked;
        const requiresAbonos = document.getElementById('filterAttrAbonos')?.checked;
        const requiresReten = document.getElementById('filterAttrRetenciones')?.checked;
        const requiresCDebito = document.getElementById('filterAttrCDebito')?.checked;

        const filteredData = window.currentData.filter(item => {
            const baseStatus = getBaseStatus(item); // 'Pagado', 'Pendiente', 'Vencido'

            // Base Status Match
            let baseMatch = false;
            if (baseStatusValue === 'TODOS') {
                baseMatch = true;
            } else if (baseStatusValue === 'TODOS_ACTIVOS') {
                baseMatch = (baseStatus === 'Pendiente' || baseStatus === 'Vencido');
            } else if (baseStatusValue === 'PENDIENTE') {
                baseMatch = (baseStatus === 'Pendiente');
            } else if (baseStatusValue === 'VENCIDO') {
                baseMatch = (baseStatus === 'Vencido');
            } else if (baseStatusValue === 'PAGADO') {
                baseMatch = (baseStatus === 'Pagado');
            } else if (baseStatusValue === 'CONTADO_ERROR') {
                // CONTADO error: Pagado + same FechaI/FechaE + no abonos in Procurement
                const fechaI = (item.FechaI || '').split('T')[0];
                const fechaE = (item.FechaE || '').split('T')[0];
                const sameDates = fechaI && fechaE && fechaI === fechaE;
                baseMatch = (baseStatus === 'Pagado') && sameDates && !item.Has_Abonos;
            }

            if ((requiresCDebito || requiresAbonos) && baseStatus === 'Pagado' && baseStatusValue === 'TODOS_ACTIVOS') {
                baseMatch = true;
            }

            if (!baseMatch) return false;

            // Extra Conditions (AND Logic)
            if (requiresPlan && !item.Plan_ID) return false;
            if (requiresAbonos && !item.Has_Abonos) return false;
            if (requiresReten && !hasRet(item)) return false;
            if (requiresCDebito) {
                const totAbonado = parseFloat(item.TotalBsAbonado) || 0;
                const totOrig = parseFloat(item.Monto) || 0;
                if (totAbonado <= totOrig + 0.1) return false;
            }

            return true;
        });

        if (filteredData.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-secondary); padding: 2rem;">No se encontraron registros.</td></tr>`;
            totalDocsStr.textContent = '0';
            totalSaldoBsStr.textContent = 'Bs 0.00';
            totalSaldoUsdStr.textContent = '$0.00';
            return;
        }

        let totalBs = 0;
        let totalUsd = 0;

        const rowsHtml = filteredData.map((item, index) => {
            const saldo = parseFloat(item.Saldo) || 0;
            const tasaEmi = parseFloat(item.TasaEmision) || 1;
            const tasaAct = parseFloat(item.TasaActual) || 1;
            const indexado = tasaAct > tasaEmi;

            const fin = calculateInvoiceFinancials(item, {
                tasaDia: tasaAct,
                aplicaIndex: indexado,
                pctDesc: 0,
                islrRate: 0
            });

            let saldoActualizadoBs = fin.finalBs;
            let montoUsd = fin.equivUsd;

            // Apply tolerance zeroing for display
            const tolerance = parseFloat(window.globalRetConfig?.ToleranceSaldo) || 0.50;
            if (saldoActualizadoBs <= tolerance) {
                saldoActualizadoBs = 0;
                montoUsd = 0;
            }

            totalBs += saldoActualizadoBs;
            totalUsd += montoUsd;

            // Allow selection: always for active invoices, also for paid if CONTADO_ERROR or PAGADO filter
            const currentFilter = document.getElementById('filterStatusBase')?.value || 'TODOS_ACTIVOS';
            const canSelect = (saldoActualizadoBs > 0.01) || currentFilter === 'CONTADO_ERROR' || currentFilter === 'PAGADO' || currentFilter === 'TODOS';
            const rKey = window.getItemKey(item);
            const globalIndex = window.currentData.indexOf(item);
            const checkboxHtml = canSelect
                ? `<input type="checkbox" class="row-checkbox" data-index="${globalIndex}" data-rowkey="${rKey}" data-nrounico="${item.NroUnico}">`
                : `<input type="checkbox" disabled>`;

            // Highlight planned rows
            const rowClass = item.Plan_ID ? 'planned-row' : '';

            return `
                <tr class="${rowClass}">
                    <td class="col-checkbox">${checkboxHtml}</td>
                    <td>${formatDate(item.FechaE)}</td>
                    <td>${formatDate(item.FechaV)}</td>
                    <td style="font-weight: 500;">${item.NumeroD || '-'}</td>
                    <td>${item.NumeroD_SAPAGCXP || '-'}</td>
                    <td>${item.Descrip || '-'}</td>
                    <td class="amount">${formatBs(saldoActualizadoBs)}</td>
                    <td class="amount us-amount">${usdFormatter(montoUsd)}</td>
                    <td style="white-space:nowrap;">
                        ${getStatusHtml(item)}
                        <button class="btn-icon" title="Gestionar Pagos" onclick="openAbonosPanel('${item.CodProv}', '${item.NumeroD}', ${item.NroUnico})" style="margin-left:4px; vertical-align:middle;">
                            <i data-lucide="calculator" size="16"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        tableBody.innerHTML = rowsHtml;
        totalDocsStr.textContent = filteredData.length.toLocaleString();
        totalSaldoBsStr.textContent = formatBs(totalBs);
        totalSaldoUsdStr.textContent = usdFormatter(totalUsd);

        lucide.createIcons();

        // Attach listeners to checkboxes
        document.querySelectorAll('.row-checkbox').forEach(cb => {
            const rKey = cb.getAttribute('data-rowkey');
            const dataIndex = cb.getAttribute('data-index');

            // Restaurar estado desde el Set si está en modo múltiple
            if (window.multiPayMode && window.multiPaySelection.has(rKey)) {
                cb.checked = true;
            }

            cb.addEventListener('change', () => {
                if (window.multiPayMode) {
                    if (cb.checked) {
                        window.multiPaySelection.add(rKey);
                        const item = window.currentData[dataIndex];
                        if (item) window.multiPaySelectionData.set(rKey, item);
                    } else {
                        window.multiPaySelection.delete(rKey);
                        window.multiPaySelectionData.delete(rKey);
                    }
                }
                recalculateSelection();
            });
        });

        recalculateSelection();
    };

    // Toggle Sidebar
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        // Let the CSS transition handle layout shifts, resize chart if it exists
        setTimeout(() => { if (window.cashflowChartInstance) window.cashflowChartInstance.resize(); }, 300);
    });

    // Events
    refreshCashflowBtn.addEventListener('click', () => {
        fetchCashflow();
    });

    document.getElementById('filterStatusBase')?.addEventListener('change', (e) => {
        if (e.target.value === 'TODOS_ACTIVOS') {
            if (window.currentData) {
                window.currentData.sort((a, b) => {
                    let valA = a['FechaV'] ? String(a['FechaV']).toLowerCase() : '';
                    let valB = b['FechaV'] ? String(b['FechaV']).toLowerCase() : '';
                    if (valA < valB) return -1;
                    if (valA > valB) return 1;
                    return 0;
                });
                const headerCell = document.querySelector('#cxpTable th.sortable[data-sort="FechaV"]');
                if (headerCell) {
                    document.querySelectorAll('#cxpTable th.sortable .sort-icon').forEach(icon => {
                        icon.classList.remove('active', 'desc');
                    });
                    const icon = headerCell.querySelector('.sort-icon');
                    if (icon) icon.classList.add('active');
                }
            }
        }
        window.renderTable();
    });
    document.getElementById('filterAttrPlanificado')?.addEventListener('change', window.renderTable);
    document.getElementById('filterAttrAbonos')?.addEventListener('change', window.renderTable);
    document.getElementById('filterAttrRetenciones')?.addEventListener('change', window.renderTable);
    document.getElementById('filterAttrCDebito')?.addEventListener('change', window.renderTable);

    searchInput.addEventListener('input', () => {
        clearTimeout(fetchTimeout);
        fetchTimeout = setTimeout(fetchData, 500);
    });

    refreshBtn.addEventListener('click', () => {
        const base = document.getElementById('filterStatusBase');
        if (base) base.value = 'TODOS_ACTIVOS';
        ['filterAttrPlanificado', 'filterAttrAbonos', 'filterAttrRetenciones', 'filterAttrCDebito'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.checked = false;
        });
        if (window.multiPayMode) {
            window.multiPaySelection.clear();
            window.multiPaySelectionData.clear();
        }
        fetchData();
    });
    filterDate.addEventListener('change', fetchData);
    filterDateHasta.addEventListener('change', fetchData);

    selectAllCheckbox.addEventListener('change', (e) => {
        const isChecked = e.target.checked;
        document.querySelectorAll('.row-checkbox').forEach(cb => {
            cb.checked = isChecked;
        });
        recalculateSelection();
    });

    cancelPlanBtn.addEventListener('click', () => {
        document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = false);
        if (window.multiPayMode) {
            window.multiPaySelection.clear();
            window.multiPaySelectionData.clear();
        }
        recalculateSelection();
    });

    submitPlanBtn.addEventListener('click', async () => {
        const selectedRows = Array.from(document.querySelectorAll('.row-checkbox:checked'))
            .map(cb => window.currentData[cb.getAttribute('data-index')]);

        const fecha = getDateValue(planFecha);
        const banco = planBanco.value;

        if (selectedRows.length === 0) return alert('Seleccione al menos una factura.');
        if (!fecha) return alert('Debe seleccionar una Fecha Planificada.');
        if (!banco) return alert('Debe seleccionar un Banco.');

        const facturas = selectedRows.map(r => ({
            NroUnico: r.NroUnico || 0,
            NumeroD: r.NumeroD,
            CodProv: r.CodProv
        }));

        try {
            submitPlanBtn.disabled = true;
            submitPlanBtn.innerHTML = '<i data-lucide="loader" class="spin"></i> Guardando...';

            const response = await fetch('/api/plan-pagos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    facturas: facturas,
                    fecha_planificada: fecha,
                    banco: banco
                })
            });

            if (!response.ok) throw new Error('Error al guardar plan de pago');

            // Clean up UI and reload
            setDateValue(planFecha, '');
            planBanco.value = '';
            await fetchData();

        } catch (error) {
            console.error(error);
            alert('Error al intentar planificar pagos.');
        } finally {
            submitPlanBtn.disabled = false;
            submitPlanBtn.innerHTML = '<i data-lucide="calendar-check"></i> Planificar Pago';
            lucide.createIcons();
        }
    });

    const unplanBtn = document.getElementById('unplanBtn');
    unplanBtn?.addEventListener('click', async () => {
        const selectedRows = Array.from(document.querySelectorAll('.row-checkbox:checked'))
            .map(cb => window.currentData[cb.getAttribute('data-index')]);

        if (selectedRows.length === 0) return alert('Seleccione al menos una factura.');
        if (!confirm(`¿Seguro que desea reversar la planificación de ${selectedRows.length} factura(s)?`)) return;

        const facturas = selectedRows.map(r => ({
            NroUnico: r.NroUnico || 0,
            NumeroD: r.NumeroD,
            CodProv: r.CodProv
        }));

        try {
            unplanBtn.disabled = true;
            unplanBtn.innerHTML = '<i data-lucide="loader" class="spin"></i> Procesando...';

            const response = await fetch('/api/plan-pagos/unplan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ facturas: facturas })
            });

            if (!response.ok) throw new Error('Error al reversar plan de pago');

            document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = false);
            recalculateSelection();
            await fetchData();

        } catch (error) {
            console.error(error);
            alert('Error al intentar reversar la planificación.');
        } finally {
            unplanBtn.disabled = false;
            unplanBtn.innerHTML = '<i data-lucide="calendar-x"></i> Reversar';
            lucide.createIcons();
        }
    });

    // --- Export Functionality ---
    const handleExport = (reportType, dateDesde = null, dateHasta = null) => {
        let url = `/api/export/${reportType}`;
        const params = new URLSearchParams();
        if (dateDesde) params.append('desde', dateDesde);
        if (dateHasta) params.append('hasta', dateHasta);
        if (params.toString()) url += '?' + params.toString();
        window.location.href = url;
    };

    document.getElementById('exportCxpBtn')?.addEventListener('click', () => {
        const d1 = getDateValue(document.getElementById('filterDate'));
        const d2 = getDateValue(document.getElementById('filterDateHasta'));
        handleExport('cuentas-por-pagar', d1, d2);
    });

    document.getElementById('exportComprasBtn')?.addEventListener('click', () => {
        const d1 = getDateValue(document.getElementById('comprasDesde'));
        const d2 = getDateValue(document.getElementById('comprasHasta'));
        handleExport('compras', d1, d2);
    });

    document.getElementById('exportAgingBtn')?.addEventListener('click', () => {
        handleExport('aging');
    });

    document.getElementById('exportDebitNotesBtn')?.addEventListener('click', () => {
        handleExport('debit-notes');
    });

    // --- SPA Routing ---
    const navItems = document.querySelectorAll('.nav-item, .nav-item-sub');
    const views = document.querySelectorAll('.view-section');

    const switchView = (viewId) => {
        // Update Nav
        navItems.forEach(item => {
            if (item.getAttribute('data-view') === viewId) item.classList.add('active');
            else item.classList.remove('active');
        });

        // Hide all views, show selected
        views.forEach(view => {
            if (view.id === `view-${viewId}`) view.classList.add('active');
            else view.classList.remove('active');
        });

        // Trigger fetches if needed
        if (viewId === 'dashboard') fetchData();
        else if (viewId === 'compras') fetchCompras();
        else if (viewId === 'aging') fetchAging();
        else if (viewId === 'cashflow') fetchCashflow();
        else if (viewId === 'forecast-sales') fetchForecastSales();
        else if (viewId === 'forecast-consolidated') fetchForecastConsolidated();
        else if (viewId === 'forecast-events') fetchForecastEvents();
        else if (viewId === 'debit-notes') {
            if (typeof window._fetchDebitNotes === 'function') window._fetchDebitNotes();
        }
        else if (viewId === 'credit-notes') fetchCreditNotes();
        else if (viewId === 'dpo') fetchDpo();
        else if (viewId === 'expense-templates') fetchExpenseTemplates();
        else if (viewId === 'expense-batch') fetchSavedBatch();
        else if (viewId === 'sedematri') { /* Static view, no fetch needed for now */ }
        else if (viewId === 'retenciones') {
            if (typeof window._fetchRetenciones === 'function') window._fetchRetenciones();
        }
        else if (viewId === 'retenciones-islr') {
            if (typeof window._fetchRetencionesISLR === 'function') window._fetchRetencionesISLR();
        }
    };

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            const viewId = item.getAttribute('data-view') || item.closest('.nav-item, .nav-item-sub')?.getAttribute('data-view');
            if (viewId) {
                e.preventDefault();
                switchView(viewId);
            }
        });
    });

    // --- Reports Fetches ---
    // Debit Notes logic has been moved completely to modules-report.js


    const registerDebitNoteModal = document.getElementById('registerDebitNoteModal');

    document.getElementById('btnRegisterDebitNote')?.addEventListener('click', () => {
        const selected = getSelectedDebitNotes();
        if (selected.length === 0) return;

        document.getElementById('regNdInputNumero').value = '';
        document.getElementById('regNdInputControl').value = '';

        const listContainer = document.getElementById('regNdFacturasContainer');
        if (listContainer) {
            listContainer.innerHTML = selected.map((s, idx) => `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">
                    <div>
                        <span style="font-size: 0.85rem; color: var(--text-secondary);">Factura:</span>
                        <strong style="display: block;">${s.NumeroD}</strong>
                    </div>
                    <div>
                        <span style="font-size: 0.85rem; color: var(--text-secondary);">V. Editable (Bs):</span>
                        <input type="number" id="retenInput_${idx}" class="form-control" step="0.01" value="${s._estimatedReten.toFixed(2)}" required>
                    </div>
                </div>
            `).join('');
        }

        registerDebitNoteModal.classList.add('active');
    });

    window.closeRegisterDebitNoteModal = () => {
        registerDebitNoteModal.classList.remove('active');
    };

    document.getElementById('registerDebitNoteForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const num = document.getElementById('regNdInputNumero').value.trim();
        const ctrl = document.getElementById('regNdInputControl').value.trim();
        if (!num || !ctrl) return;

        let selected = window.onTheFlyND || getSelectedDebitNotes();
        if (selected.length === 0) return;

        // Asignar el monto exacto tipeado por el usuario en cada factura
        selected.forEach((s, idx) => {
            const inputVal = parseFloat(document.getElementById(`retenInput_${idx}`).value || 0);
            s.MontoRetencionBs = inputVal;
            // Quitamos la estimacion inicial
            delete s._estimatedReten;
        });

        const btn = e.target.querySelector('button[type="submit"]');
        const origText = btn.innerHTML;
        btn.innerHTML = `<i data-lucide="loader" class="rotating"></i> Cargando...`;
        btn.disabled = true;

        try {
            const res = await fetch('/api/procurement/debit-notes/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ Invoices: selected, NotaDebitoID: num, ControlID: ctrl })
            });
            if (!res.ok) throw new Error("Error al registrar");
            closeRegisterDebitNoteModal();
            window.onTheFlyND = null; // Clear state
            if (typeof window._fetchDebitNotes === 'function') window._fetchDebitNotes();
        } catch (err) {
            console.error(err);
            alert("Ocurrió un error registrando la Nota de Débito.");
        } finally {
            btn.innerHTML = origText;
            btn.disabled = false;
            lucide.createIcons();
        }
    });

    // --- Credit Notes Logic ---
    const fetchCreditNotes = async () => {
        window.fetchCreditNotes = fetchCreditNotes; // Expose globally just in case
        const tbody = document.getElementById('creditNotesTableBody');
        if (!tbody) return;

        tbody.innerHTML = `<tr><td colspan="10" class="loading-cell"><div class="loader"></div><p>Cargando notas de crédito...</p></td></tr>`;

        try {
            const provFilter = document.getElementById('cnFilterProv')?.value || "";
            const statusFilter = document.getElementById('cnFilterEstatus')?.value || "";
            let url = `/api/procurement/credit-notes?estatus=${statusFilter}`;
            if (provFilter) url += `&search=${encodeURIComponent(provFilter)}`;

            const res = await fetch(url);
            if (!res.ok) throw new Error("Error loading credit notes");
            const data = await res.json();

            if (!data.data || data.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-secondary);">No hay notas de crédito registradas.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.data.map(d => {
                const isPendiente = d.Estatus === 'PENDIENTE';
                const isSolicitada = d.Estatus === 'SOLICITADA';
                const effectiveRate = parseFloat(d.TasaCambio) || window.currentTasaBCV || 1;
                const computedUsd = parseFloat(d.MontoUsd) || (parseFloat(d.MontoBs) / effectiveRate);
                
                let bsCss = '';
                if (d.Estatus === 'SOLICITADA') bsCss = 'status-info'; // assuming it's added in CSS, else inline or secondary
                else if (d.Estatus === 'PENDIENTE') bsCss = 'status-pending';
                else if (d.Estatus === 'APLICADA') bsCss = 'status-paid';
                else bsCss = 'status-overdue';

                return `
                <tr>
                    <td>${d.CodProv}</td>
                    <td title="${d.Observacion || ''}">${d.NumeroD || '-'}</td>
                    <td><span class="badge badge-info" style="background: rgba(99,102,241,0.15); color: var(--primary-accent); padding: 2px 6px; border-radius: 4px; font-size: 0.8rem;">${d.Motivo}</span></td>
                    <td class="amount">${formatBs(d.MontoBs)}</td>
                    <td class="amount">${effectiveRate.toFixed(4)}</td>
                    <td class="amount us-amount" style="font-weight: 600;">${usdFormatter(computedUsd)}</td>
                    <td>${formatDate(d.FechaSolicitud)}</td>
                    <td style="text-align: center;">
                        <span class="status-badge ${bsCss}" ${d.Estatus === 'SOLICITADA' ? 'style="background:rgba(59,130,246,0.1);color:#3b82f6;"' : ''}>
                            ${d.Estatus}
                        </span>
                    </td>
                    <td>${d.NotaCreditoID || '-'}</td>
                    <td style="text-align: center;">
                        <div style="display: flex; gap: 0.5rem; justify-content: center;">
                            ${(isPendiente || isSolicitada) ? `
                                <button class="btn btn-sm btn-primary" onclick="applyCreditNote(${d.Id})" title="Aplicar como Abono" style="padding: 0.2rem 0.5rem;">
                                    <i data-lucide="check" style="width:14px;height:14px;"></i>
                                </button>
                                <button class="btn btn-sm btn-info" onclick="sendCreditNoteEmail(${d.Id})" title="Reenviar Solicitud al Proveedor" style="padding: 0.2rem 0.5rem; background: var(--primary); color: white;">
                                    <i data-lucide="send" style="width:14px;height:14px;"></i>
                                </button>
                                <button class="btn btn-sm btn-secondary" onclick="anularCreditNote(${d.Id})" title="Anular" style="padding: 0.2rem 0.5rem; color: var(--danger);">
                                    <i data-lucide="slash" style="width:14px;height:14px;"></i>
                                </button>
                            ` : ''}
                            <button class="btn btn-sm btn-secondary" onclick="deleteCreditNote(${d.Id || d.ID || d.id})" title="Eliminar Permanentemente" style="padding: 0.2rem 0.5rem; color: var(--danger); border-color: rgba(239, 68, 68, 0.2);">
                                <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `}).join('');
            lucide.createIcons();
        } catch (e) {
            console.error(e);
            tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--danger);">Error al cargar notas de crédito.</td></tr>`;
        }
    };

    const ncnModal = document.getElementById('newCreditNoteModal');
    const ncnForm = document.getElementById('newCreditNoteForm');
    
    window.openNewCreditNoteModal = () => {
        ncnForm.reset();
        const tasaInp = document.getElementById('cncTasa');
        if (tasaInp) tasaInp.value = window.currentTasaBCV || 0;
        if (typeof window.loadMotivosAjuste === 'function') window.loadMotivosAjuste();
        ncnModal.classList.add('active');
    };
    window.closeNewCreditNoteModal = () => ncnModal.classList.remove('active');

    window.recalcNCUsd = () => {
        const bs = parseFloat(document.getElementById('cncMontoBs')?.value) || 0;
        const tasa = parseFloat(document.getElementById('cncTasa')?.value) || 1;
        const usdInp = document.getElementById('cncMontoUsd');
        if(usdInp) {
            usdInp.value = `$${(bs / tasa).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }
    };
    document.getElementById('cncMontoBs')?.addEventListener('input', window.recalcNCUsd);
    document.getElementById('cncTasa')?.addEventListener('input', window.recalcNCUsd);

    document.getElementById('btnNewCreditNote')?.addEventListener('click', openNewCreditNoteModal);
    document.getElementById('refreshCreditNotesBtn')?.addEventListener('click', fetchCreditNotes);
    document.getElementById('cnFilterProv')?.addEventListener('input', () => {
        clearTimeout(fetchTimeout);
        fetchTimeout = setTimeout(fetchCreditNotes, 500);
    });
    document.getElementById('cnFilterEstatus')?.addEventListener('change', fetchCreditNotes);

    ncnForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const actionType = e.submitter ? e.submitter.dataset.action : 'register';
        const btn = ncnForm.querySelector('button[type="submit"]');
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="loader" style="width:14px;height:14px;border-color:#fff;border-bottom-color:transparent;"></i>';
        btn.disabled = true;

        const rawCodProv = document.getElementById('cncCodProv').value;
        const payload = {
            CodProv: rawCodProv.split(' - ')[0],
            NumeroD: document.getElementById('cncNumeroD').value || null,
            Motivo: document.getElementById('cncMotivo').value,
            MontoBs: parseFloat(document.getElementById('cncMontoBs').value),
            TasaCambio: parseFloat(document.getElementById('cncTasa').value),
            MontoUsd: parseFloat(document.getElementById('cncMontoUsd')?.value?.replace(/[\$\,]/g, '')) || 0,
            Observacion: document.getElementById('cncObservacion').value,
            EnviarInmediato: actionType === 'send'
        };

        try {
            const res = await fetch('/api/procurement/credit-notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!res.ok) {
                const err = await res.json().catch(()=>({}));
                throw new Error(err.detail || "Error al crear NC");
            }
            showToast('✅ Solicitud de Nota de Crédito registrada.', 'success');
            closeNewCreditNoteModal();
            fetchCreditNotes();
        } catch (e) {
            showToast(`❌ Error al registrar solicitud: ${e.message}`, 'error');
        } finally {
            btn.innerHTML = orig;
            btn.disabled = false;
        }
    });

    window.sendCreditNoteEmail = async (id) => {
        if (!confirm('¿Está seguro de enviar esta solicitud de nota de crédito por correo y cambiar su estatus a SOLICITADA?')) return;
        try {
            const res = await fetch(`/api/procurement/credit-notes/${id}/send`, { method: 'POST' });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Error al enviar la solicitud.");
            }
            showToast('✅ Correo de Solicitud de Nota de Crédito enviado.', 'success');
            fetchCreditNotes();
        } catch (e) {
            showToast('❌ ' + e.message, 'error');
        }
    };

    window.anularCreditNote = async (id) => {
        if (!confirm('¿Desea anular esta solicitud de Nota de Crédito?')) return;
        try {
            const res = await fetch(`/api/procurement/credit-notes/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ Estatus: 'ANULADA' })
            });
            if (!res.ok) throw new Error("Error");
            showToast('Nota de crédito anulada.', 'success');
            fetchCreditNotes();
        } catch (e) {
            showToast('Error al anular.', 'error');
        }
    };

    window.deleteCreditNote = async (id) => {
        if (!confirm('¿Está seguro de ELIMINAR PERMANENTEMENTE esta Nota de Crédito? Esta acción no se puede deshacer.')) return;
        try {
            const res = await fetch(`/api/procurement/credit-notes/${id}`, {
                method: 'DELETE'
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Error");
            }
            showToast('✅ Nota de crédito eliminada.', 'success');
            fetchCreditNotes();
        } catch (e) {
            showToast(`❌ Error: ${e.message}`, 'error');
        }
    };

    window.applyCreditNote = async (id) => {
        const ncId = prompt('Ingrese el Número de Nota de Crédito emitido en Saint (opcional):');
        if (ncId === null) return; // cancelled

        try {
            const res = await fetch(`/api/procurement/credit-notes/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ Estatus: 'APLICADA', NotaCreditoID: ncId })
            });
            if (!res.ok) throw new Error("Error");
            showToast('✅ Nota de crédito marcada como APLICADA.', 'success');
            fetchCreditNotes();
        } catch (e) {
            showToast('Error al aplicar.', 'error');
        }
    };

    window.comprasChartInstance = null;
    const refreshComprasBtn = document.getElementById('refreshComprasBtn');
    const comprasDesde = document.getElementById('comprasDesde');
    const comprasHasta = document.getElementById('comprasHasta');

    refreshComprasBtn?.addEventListener('click', () => fetchCompras());

    const fetchCompras = async () => {
        const tbody = document.getElementById('comprasBody');
        if (!tbody) return;

        tbody.innerHTML = `<tr><td colspan="4" class="loading-cell"><div class="loader"></div><p>Cargando compras...</p></td></tr>`;
        try {
            let url = '/api/reports/compras';
            const params = new URLSearchParams();
            if (comprasDesde && comprasDesde.value) params.append('desde', comprasDesde.value);
            if (comprasHasta && comprasHasta.value) params.append('hasta', comprasHasta.value);
            if (params.toString()) url += '?' + params.toString();

            const res = await fetch(url);
            const { data } = await res.json();

            if (!data.length) {
                tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-secondary);">No hay datos.</td></tr>`;
                if (window.comprasChartInstance) window.comprasChartInstance.destroy();
                return;
            }

            renderComprasChart(data.slice(0, 10)); // Mostrar top 10 en gráfico

            tbody.innerHTML = data.map(item => `
                <tr>
                    <td style="font-weight: 500;">${item.Proveedor || '-'}</td>
                    <td class="amount" style="font-weight: bold;">${usdFormatter(item.TotalUSD)}</td>
                    <td class="amount" style="color: var(--primary-accent);">${item.Porcentaje.toFixed(2)}%</td>
                    <td class="amount">${item.CantidadFacturas}</td>
                </tr>
            `).join('');
            lucide.createIcons();
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--danger);">Error al cargar.</td></tr>`;
        }
    };

    const renderComprasChart = (data) => {
        const ctx = document.getElementById('comprasChart').getContext('2d');
        if (window.comprasChartInstance) window.comprasChartInstance.destroy();

        const labels = data.map(i => i.Proveedor.substring(0, 15) + '...');
        const amounts = data.map(i => i.TotalUSD);

        window.comprasChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Monto Total Compras (USD)',
                    data: amounts,
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderColor: '#3b82f6',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y', // Grafico horizontal para mejor lectura de nombres
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8' } },
                    y: { grid: { display: false }, ticks: { color: '#f8fafc' } }
                }
            }
        });
    };

    const fetchAging = async () => {
        const tbody = document.getElementById('agingBody');
        tbody.innerHTML = `<tr><td colspan="7" class="loading-cell"><div class="loader"></div><p>Cargando antigüedad en USD...</p></td></tr>`;
        try {
            const res = await fetch('/api/reports/aging');
            const { data } = await res.json();
            if (!data.length) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-secondary);">No hay datos.</td></tr>`;
                return;
            }

            // Calculate summaries
            const sumPorVencer = data.reduce((acc, curr) => acc + (curr.PorVencer || 0), 0);
            const sum1_30 = data.reduce((acc, curr) => acc + (curr.Dias_1_30 || 0), 0);
            const sum31_60 = data.reduce((acc, curr) => acc + (curr.Dias_31_60 || 0), 0);
            const sum61_90 = data.reduce((acc, curr) => acc + (curr.Dias_61_90 || 0), 0);
            const sumMas90 = data.reduce((acc, curr) => acc + (curr.Mas_90 || 0), 0);
            const sumTotal = data.reduce((acc, curr) => acc + (curr.Total || 0), 0);

            // Update summary DOM
            if (document.getElementById('agingSummaryPorVencer')) document.getElementById('agingSummaryPorVencer').innerText = usdFormatter(sumPorVencer);
            if (document.getElementById('agingSummary1_30')) document.getElementById('agingSummary1_30').innerText = usdFormatter(sum1_30);
            if (document.getElementById('agingSummary31_60')) document.getElementById('agingSummary31_60').innerText = usdFormatter(sum31_60);
            if (document.getElementById('agingSummary61_90')) document.getElementById('agingSummary61_90').innerText = usdFormatter(sum61_90);
            if (document.getElementById('agingSummaryMas90')) document.getElementById('agingSummaryMas90').innerText = usdFormatter(sumMas90);
            if (document.getElementById('agingSummaryTotal')) document.getElementById('agingSummaryTotal').innerText = usdFormatter(sumTotal);

            tbody.innerHTML = data.map(item => `
            <tr>
                <td style="font-weight: 500;">${item.Proveedor || '-'}</td>
                <td class="amount us-amount">${usdFormatter(item.PorVencer)}</td>
                <td class="amount us-amount" style="color: #eab308;">${usdFormatter(item.Dias_1_30)}</td>
                <td class="amount us-amount" style="color: #f97316;">${usdFormatter(item.Dias_31_60)}</td>
                <td class="amount us-amount" style="color: #ef4444;">${usdFormatter(item.Dias_61_90)}</td>
                <td class="amount us-amount" style="color: #b91c1c; font-weight: bold;">${usdFormatter(item.Mas_90)}</td>
                <td class="amount us-amount" style="font-weight: bold;">${usdFormatter(item.Total)}</td>
            </tr>
        `).join('');
        } catch (e) {
            console.error("fetchAging error:", e);
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger);">Error al cargar.</td></tr>`;
        }
    };

    window.cashflowChartInstance = null;

    const renderCashflowChart = (data) => {
        const ctx = document.getElementById('cashflowChart').getContext('2d');
        if (window.cashflowChartInstance) {
            window.cashflowChartInstance.destroy();
        }

        const labels = data.map(i => i.Periodo);
        const facturasUsd = data.map(i => Math.round(i.FacturasUSD || 0));
        const gastosFijosUsd = data.map(i => Math.round(i.GastosFijosUSD || 0));
        const gastosPersonalesUsd = data.map(i => Math.round(i.GastosPersonalesUSD || 0));

        const totalsUsd = data.map(i => Math.round(i.SaldoProyectadoUSD || 0));

        window.cashflowChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Pagos Proveedores',
                        data: facturasUsd,
                        backgroundColor: 'rgba(34, 197, 94, 0.7)',
                        borderColor: '#22c55e',
                        borderWidth: 1,
                        borderRadius: { topLeft: 0, topRight: 0, bottomLeft: 4, bottomRight: 4 }
                    },
                    {
                        label: 'Gastos Fijos',
                        data: gastosFijosUsd,
                        backgroundColor: 'rgba(251, 146, 60, 0.7)',
                        borderColor: '#fb923c',
                        borderWidth: 1,
                        borderRadius: 0
                    },
                    {
                        label: 'Gastos Personales',
                        data: gastosPersonalesUsd,
                        backgroundColor: 'rgba(192, 38, 211, 0.7)',
                        borderColor: '#c026d3',
                        borderWidth: 1,
                        borderRadius: { topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0 }
                    }
                ]
            },
            options: {
                layout: {
                    padding: { top: 25 }
                },
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        labels: { color: '#f8fafc', font: { family: 'Inter', size: 13 } }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function (context) {
                                let label = context.dataset.label || '';
                                if (label) label += ': ';
                                if (context.parsed.y !== null) {
                                    label += context.parsed.y + ' USD';
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { stacked: true, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
                    y: {
                        stacked: true,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: {
                            callback: function (value) {
                                return value >= 1000 ? (value / 1000).toFixed(0) + 'k' : value;
                            }
                        }
                    }
                },
                color: '#94a3b8'
            },
            plugins: [{
                id: 'topLabels',
                afterDatasetsDraw(chart) {
                    const ctx = chart.ctx;
                    ctx.fillStyle = '#f8fafc';
                    ctx.font = 'bold 12px Inter';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';

                    const padding = 5;
                    const metaKeys = chart.data.datasets.map((_, i) => i);

                    labels.forEach((_, index) => {
                        let total = totalsUsd[index];
                        if (total > 0) {
                            // Find the topmost visible rectangle for this index
                            let highestY = chart.chartArea.bottom;
                            metaKeys.forEach(dsIndex => {
                                const meta = chart.getDatasetMeta(dsIndex);
                                if (!meta.hidden && meta.data[index]) {
                                    const yPos = meta.data[index].y;
                                    if (yPos < highestY) { highestY = yPos; }
                                }
                            });

                            const xPos = chart.getDatasetMeta(0).data[index].x;
                            const dataString = Number(total).toLocaleString('de-DE') + ' $';
                            ctx.fillText(dataString, xPos, highestY - padding);
                        }
                    });
                }
            }]
        });
    };


    const fetchCashflow = async () => {
        const tbody = document.getElementById('cashflowBody');
        tbody.innerHTML = `<tr><td colspan="3" class="loading-cell"><div class="loader"></div><p>Cargando pronóstico...</p></td></tr>`;

        // Initialize 22-day default range (-7 to +14) if empty
        if (!cashflowDateDesde.value && !cashflowDateHasta.value) {
            const today = new Date();
            const past7 = new Date(today);
            past7.setDate(today.getDate() - 7);
            const future14 = new Date(today);
            future14.setDate(today.getDate() + 14);

            cashflowDateDesde.value = past7.toISOString().split('T')[0];
            cashflowDateHasta.value = future14.toISOString().split('T')[0];
        }

        try {
            let url = '/api/reports/cashflow';
            const params = new URLSearchParams();
            if (cashflowDateDesde.value) params.append('desde', cashflowDateDesde.value);
            if (cashflowDateHasta.value) params.append('hasta', cashflowDateHasta.value);

            if (params.toString()) {
                url += '?' + params.toString();
            }

            const res = await fetch(url);
            const { data } = await res.json();
            if (!data.length) {
                tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-secondary);">No hay datos en el rango seleccionado.</td></tr>`;
                if (window.cashflowChartInstance) window.cashflowChartInstance.destroy();
                document.getElementById('cashflowUsdTotal').textContent = "";
                return;
            }

            // Render Chart
            renderCashflowChart(data);

            // Compute Grand Total USD
            const totalUsd = data.reduce((sum, item) => sum + (parseFloat(item.SaldoProyectadoUSD) || 0), 0);
            document.getElementById('cashflowUsdTotal').innerHTML = `Deuda Total en USD (Rango): <span style="color: #22c55e;">${usdFormatter(totalUsd)}</span>`;

            // Populate Table
            const todayStr = new Date().toISOString().split('T')[0];

            tbody.innerHTML = data.map(item => {
                const isToday = item.Periodo === todayStr;
                const highlightStyle = isToday ? 'background: rgba(234, 179, 8, 0.15); border-left: 3px solid #eab308;' : '';
                const dateLabel = isToday ? `${item.Periodo || '-'} <span style="font-size: 0.75rem; background: #eab308; color: #0f172a; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">HOY</span>` : (item.Periodo || '-');

                return `
                <tr style="${highlightStyle}">
                    <td style="font-weight: 500;">${dateLabel}</td>
                    <td class="amount" style="color: #22c55e;">${usdFormatter(item.FacturasUSD)}</td>
                    <td class="amount" style="color: #fb923c;">${usdFormatter(item.GastosFijosUSD)}</td>
                    <td class="amount" style="color: #c026d3;">${usdFormatter(item.GastosPersonalesUSD)}</td>
                    <td class="amount us-amount" style="font-weight: bold;">${usdFormatter(item.SaldoProyectadoUSD)}</td>
                </tr>
            `}).join('');
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="2" style="text-align: center; color: var(--danger);">Error al cargar.</td></tr>`;
        }
    };

    const fetchDpo = async () => {
        const tbody = document.getElementById('dpoBody');
        tbody.innerHTML = `<tr><td colspan="3" class="loading-cell"><div class="loader"></div><p>Cargando DPO...</p></td></tr>`;
        try {
            const res = await fetch('/api/reports/dpo');
            const { data } = await res.json();
            if (!data.length) {
                tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-secondary);">No hay datos.</td></tr>`;
                return;
            }
            tbody.innerHTML = data.map(item => `
                <tr>
                    <td style="font-weight: 500;">${item.Periodo || '-'}</td>
                    <td class="amount">${Number(item.PromedioDiasPago).toFixed(1)} Días</td>
                    <td class="amount">${item.FacturasPagadas} Facturas</td>
                </tr>
            `).join('');
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--danger);">Error al cargar.</td></tr>`;
        }
    };

    // Boot - Handled by hash routing at the end of script
    // fetchData();

    // ==========================================
    // FORECAST MODULE: Sales, Consolidated, Events
    // ==========================================

    window.forecastSalesChartInstance = null;
    window.forecastConsChartInstance = null;

    // --- FORECAST SALES ---
    refreshForecastSalesBtn?.addEventListener('click', () => fetchForecastSales());

    const fetchForecastSales = async () => {
        const tbody = document.getElementById('forecastSalesBody');
        if (!tbody) return;

        tbody.innerHTML = `<tr><td colspan="3" class="loading-cell"><div class="loader"></div><p>Cargando pronóstico...</p></td></tr>`;

        if (!getDateValue(fsDateDesde) && !getDateValue(fsDateHasta)) {
            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
            setDateValue(fsDateDesde, firstDay.toISOString().split('T')[0]);
            setDateValue(fsDateHasta, lastDay.toISOString().split('T')[0]);
        }

        try {
            let url = '/api/reports/forecast-sales';
            const params = new URLSearchParams();
            const d1 = getDateValue(fsDateDesde);
            const d2 = getDateValue(fsDateHasta);
            if (d1) params.append('desde', d1);
            if (d2) params.append('hasta', d2);
            if (params.toString()) url += '?' + params.toString();

            const res = await fetch(url);
            if (!res.ok) throw new Error("Error loading");
            const { data } = await res.json();

            if (!data.length) {
                tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-secondary);">No hay datos en el rango seleccionado.</td></tr>`;
                if (window.forecastSalesChartInstance) window.forecastSalesChartInstance.destroy();
                document.getElementById('forecastSalesUsdTotal').textContent = "";
                return;
            }

            renderForecastSalesChart(data);

            const totalUsd = data.reduce((sum, item) => sum + (parseFloat(item.VentasProyectadasUSD) || 0), 0);
            document.getElementById('forecastSalesUsdTotal').innerHTML = `Ventas Totales Proyectadas (USD): <span style="color: #22c55e;">${usdFormatter(totalUsd)}</span>`;

            tbody.innerHTML = data.map(item => `
                <tr>
                    <td style="font-weight: 500;">${item.Periodo}</td>
                    <td class="amount" style="font-weight: bold; color: var(--text-primary);">${formatBs(item.VentasProyectadas)}</td>
                    <td class="amount us-amount" style="font-weight: bold;">${usdFormatter(item.VentasProyectadasUSD)}</td>
                </tr>
            `).join('');
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--danger);">Error al cargar.</td></tr>`;
        }
    };

    const renderForecastSalesChart = (data) => {
        const ctx = document.getElementById('forecastSalesChart').getContext('2d');
        if (window.forecastSalesChartInstance) window.forecastSalesChartInstance.destroy();

        const labels = data.map(i => i.Periodo);
        const amountsUsd = data.map(i => Math.round(i.VentasProyectadasUSD || 0));

        window.forecastSalesChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Ventas Proyectadas (USD)',
                    data: amountsUsd,
                    backgroundColor: 'rgba(34, 197, 94, 0.7)',
                    borderColor: '#22c55e',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                layout: { padding: { top: 25 } },
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: '#f8fafc', font: { family: 'Inter', size: 13 } } }
                },
                scales: {
                    x: { grid: { color: 'rgba(255, 255, 255, 0.05)' } },
                    y: { grid: { color: 'rgba(255, 255, 255, 0.05)' } }
                },
                color: '#94a3b8'
            }
        });
    };

    // --- FORECAST CONSOLIDATED ---
    refreshForecastConsolidatedBtn?.addEventListener('click', () => fetchForecastConsolidated());

    const fetchForecastConsolidated = async () => {
        const tbody = document.getElementById('forecastConsolidatedBody');
        if (!tbody) return;

        tbody.innerHTML = `<tr><td colspan="7" class="loading-cell"><div class="loader"></div><p>Cargando consolidado en vivo...</p></td></tr>`;

        // Default 21 days view if empty
        if (!getDateValue(fcDateDesde) && !getDateValue(fcDateHasta)) {
            const today = new Date();
            const future21 = new Date(today);
            future21.setDate(today.getDate() + 21);
            setDateValue(fcDateDesde, today.toISOString().split('T')[0]);
            setDateValue(fcDateHasta, future21.toISOString().split('T')[0]);
        }

        try {
            // Apply new settings from UI/Local Store
            const saved = JSON.parse(localStorage.getItem('cashflowParams') || '{}');
            const fechaCero = saved.fechaCero || new Date().toISOString().split('T')[0];
            const cajaUsd = saved.cajaUsd || 0;
            const cajaBs = saved.cajaBs || 0;
            const delayDays = saved.toggleDelay ? (saved.retardoDays || 1) : 0;

            let url = `/api/reports/forecast-consolidated?fecha_arranque=${fechaCero}&caja_usd=${cajaUsd}&caja_bs=${cajaBs}&delay_days=${delayDays}`;

            if (getDateValue(fcDateDesde)) url += `&desde=${getDateValue(fcDateDesde)}`;
            if (getDateValue(fcDateHasta)) url += `&hasta=${getDateValue(fcDateHasta)}`;

            const res = await fetch(url);
            if (!res.ok) throw new Error("Error loading flow");
            const { data } = await res.json();

            if (!data || !data.length) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-secondary);">No hay datos en el rango. Asegúrese de que la 'Fecha de Arranque' sea anterior a las fechas consultadas.</td></tr>`;
                if (window.forecastConsChartInstance) window.forecastConsChartInstance.destroy();
                return;
            }

            renderForecastConsolidatedChart(data);

            const todayStr = new Date().toISOString().split('T')[0];

            tbody.innerHTML = data.map(item => {
                const isPositive = item.SaldoRealCajaUSD >= 0;
                const statusColor = isPositive ? 'color: var(--success);' : 'color: var(--danger);';
                // Flujo Neto = Entradas - Salidas (Total USD)
                const flujoNeto = (parseFloat(item.EntradasUSD) || 0) - (parseFloat(item.SalidasPagosUSD) || 0) - (parseFloat(item.SalidasFarmaciaUSD) || 0) - (parseFloat(item.SalidasPersonalesUSD) || 0);
                const flujoNetoColor = flujoNeto >= 0 ? 'color: var(--success);' : 'color: var(--danger);';

                const isToday = item.Periodo === todayStr;
                const formattedDateStr = formatDate(item.Periodo);
                const highlightStyle = isToday ? 'background: rgba(234, 179, 8, 0.15); border-left: 3px solid #eab308;' : '';
                const dateLabel = isToday ? `${formattedDateStr} <span style="font-size: 0.75rem; background: #eab308; color: #0f172a; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">HOY</span>` : formattedDateStr;

                return `
                <tr style="${highlightStyle}">
                    <td style="font-weight: 500;">${dateLabel}</td>
                    <td class="amount us-amount" style="color:var(--text-primary)">${usdFormatter(item.EntradasUSD)}</td>
                    <td class="amount us-amount" style="color:var(--danger)">${usdFormatter(item.SalidasPagosUSD)}</td>
                    <td class="amount us-amount" style="color:#fb923c">${usdFormatter(item.SalidasFarmaciaUSD)}</td>
                    <td class="amount us-amount" style="color:#c026d3">${usdFormatter(item.SalidasPersonalesUSD)}</td>
                    <td class="amount us-amount" style="${flujoNetoColor}">${usdFormatter(flujoNeto)}</td>
                    <td class="amount us-amount" style="${statusColor} font-weight: bold; background: rgba(0,0,0,0.2);">${usdFormatter(item.SaldoRealCajaUSD)}</td>
                </tr>
            `}).join('');
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger);">Error al cargar.</td></tr>`;
        }
    };

    const renderForecastConsolidatedChart = (data) => {
        const ctx = document.getElementById('forecastConsolidatedChart').getContext('2d');
        if (window.forecastConsChartInstance) window.forecastConsChartInstance.destroy();

        const labels = data.map(i => formatDate(i.Periodo));
        const entradasUsd = data.map(i => Math.round(i.EntradasUSD || 0));
        const salidasFacturasUsd = data.map(i => -Math.round(i.SalidasPagosUSD || 0));
        const gastosFijosUsd = data.map(i => -Math.round(i.SalidasFarmaciaUSD || 0));
        const gastosPersonalesUsd = data.map(i => -Math.round(i.SalidasPersonalesUSD || 0));
        const acumuladoUsd = data.map(i => Math.round(i.SaldoRealCajaUSD || 0));

        window.forecastConsChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        type: 'line',
                        label: 'Saldo Acumulado Real (Dólares Netos)',
                        data: acumuladoUsd,
                        borderColor: '#10b981', // green success
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        yAxisID: 'y'
                    },
                    {
                        type: 'bar',
                        label: 'Ingresos (Ventas)',
                        data: entradasUsd,
                        backgroundColor: 'rgba(34, 197, 94, 0.7)',
                        stack: 'ingresos',
                        yAxisID: 'y'
                    },
                    {
                        type: 'bar',
                        label: 'Egresos (Pagos Proveedores)',
                        data: salidasFacturasUsd,
                        backgroundColor: 'rgba(239, 68, 68, 0.7)', // red
                        stack: 'egresos',
                        yAxisID: 'y'
                    },
                    {
                        type: 'bar',
                        label: 'Gastos Farmacia',
                        data: gastosFijosUsd,
                        backgroundColor: 'rgba(251, 146, 60, 0.7)', // orange
                        stack: 'egresos',
                        yAxisID: 'y'
                    },
                    {
                        type: 'bar',
                        label: 'Gastos Personales (Dueños)',
                        data: gastosPersonalesUsd,
                        backgroundColor: 'rgba(192, 38, 211, 0.7)', // rose/pink
                        stack: 'egresos',
                        yAxisID: 'y'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: '#f8fafc' } },
                    tooltip: { mode: 'index', intersect: false }
                },
                scales: {
                    x: {
                        stacked: true,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    y: {
                        stacked: true,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    }
                },
                color: '#94a3b8'
            }
        });
    };

    // --- FORECAST EVENTS (CRUD) ---
    const addEventBtn = document.getElementById('addEventBtn');
    addEventBtn?.addEventListener('click', async () => {
        const fecha = getDateValue(document.getElementById('eventFecha'));
        const tipo = document.getElementById('eventTipo').value;
        const valor = parseFloat(document.getElementById('eventValor').value);

        if (!fecha || !tipo || isNaN(valor)) {
            alert('Por favor complete todos los campos');
            return;
        }

        try {
            addEventBtn.disabled = true;
            addEventBtn.innerHTML = '<i data-lucide="loader" class="spin"></i> Guardando...';

            const res = await fetch('/api/forecast-events', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fecha, tipo_evento: tipo, valor })
            });
            if (!res.ok) throw new Error('Failed to save');

            setDateValue(document.getElementById('eventFecha'), '');

            document.getElementById('eventValor').value = '1.0';
            fetchForecastEvents();
        } catch (e) {
            alert('Error al guardar el evento.');
        } finally {
            addEventBtn.disabled = false;
            addEventBtn.innerHTML = '<i data-lucide="plus"></i> Añadir Evento';
            lucide.createIcons();
        }
    });

    const fetchForecastEvents = async () => {
        const tbody = document.getElementById('forecastEventsBody');
        if (!tbody) return;

        tbody.innerHTML = `<tr><td colspan="5" class="loading-cell"><div class="loader"></div><p>Cargando eventos...</p></td></tr>`;
        try {
            const res = await fetch('/api/forecast-events');
            const { data } = await res.json();
            if (!data.length) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-secondary);">No hay eventos registrados.</td></tr>`;
                return;
            }
            tbody.innerHTML = data.map(item => `
                <tr>
                    <td>${item.id}</td>
                    <td style="font-weight: 500;">${item.fecha}</td>
                    <td><span class="status-badge" style="background: rgba(168,85,247,0.1); color: #a855f7;">${item.tipo_evento}</span></td>
                    <td>${item.valor}</td>
                    <td>
                        <button class="btn-icon text-danger" onclick="deleteForecastEvent(${item.id})">
                            <i data-lucide="trash-2"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
            lucide.createIcons();
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--danger);">Error al cargar.</td></tr>`;
        }
    };

    window.deleteForecastEvent = async (id) => {
        if (!confirm('¿Seguro que desea eliminar este evento?')) return;
        try {
            const res = await fetch(`/api/forecast-events/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete');
            fetchForecastEvents();
        } catch (e) {
            alert('Error al eliminar.');
        }
    };

    // --- GASTOS PROGRAMADOS (PLANTILLAS Y BATCH) ---

    // Plantillas de Gastos
    window.expenseTemplatesData = [];
    window.renderExpenseTemplates = () => {
        const tbody = document.getElementById('expenseTemplatesBody');
        if (!tbody) return;
        if (!window.expenseTemplatesData.length) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-secondary);">No hay plantillas creadas.</td></tr>`;
            return;
        }
        tbody.innerHTML = window.expenseTemplatesData.map(t => `
            <tr>
                <td style="font-weight: 500;">${t.descripcion}</td>
                <td><span class="status-badge" style="background: ${t.tipo === 'Farmacia' ? 'rgba(251, 146, 60, 0.1)' : 'rgba(192, 38, 211, 0.1)'}; color: ${t.tipo === 'Farmacia' ? '#fb923c' : '#c026d3'};">${t.tipo}</span></td>
                <td class="amount">${usdFormatter(t.monto_usd)}</td>
                <td class="amount">Día ${t.dia_mes_estimado}</td>
                <td class="amount">
                    <button class="btn-icon text-primary" onclick="editExpenseTpl(${t.id}, '${t.descripcion.replace(/'/g, "\\'")}', '${t.tipo}', ${t.monto_usd}, ${t.dia_mes_estimado})">
                        <i data-lucide="edit"></i>
                    </button>
                    <button class="btn-icon text-danger" onclick="deleteExpenseTpl(${t.id})">
                        <i data-lucide="trash-2"></i>
                    </button>
                </td>
            </tr>
        `).join('');
        lucide.createIcons();
    };

    const fetchExpenseTemplates = async () => {
        const tbody = document.getElementById('expenseTemplatesBody');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="5" class="loading-cell"><div class="loader"></div><p>Cargando plantillas...</p></td></tr>`;
        try {
            const res = await fetch('/api/expense-templates');
            const { data } = await res.json();
            window.expenseTemplatesData = data || [];
            window.renderExpenseTemplates();
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--danger);">Error.</td></tr>`;
        }
    };

    const expenseTplModal = document.getElementById('expenseTplModal');
    window.showExpenseTplModal = () => {
        document.getElementById('expenseTplForm').reset();
        document.getElementById('tplId').value = '';
        document.getElementById('expenseTplModalTitle').innerText = 'Nueva Plantilla de Gasto';
        expenseTplModal.classList.add('active');
    };
    window.closeExpenseTplModal = () => expenseTplModal.classList.remove('active');

    window.editExpenseTpl = (id, desc, tipo, monto, dia) => {
        document.getElementById('tplId').value = id;
        document.getElementById('tplDesc').value = desc;
        document.getElementById('tplTipo').value = tipo;
        document.getElementById('tplMonto').value = monto;
        document.getElementById('tplDia').value = dia;
        document.getElementById('expenseTplModalTitle').innerText = 'Editar Plantilla';
        expenseTplModal.classList.add('active');
    };

    document.getElementById('expenseTplForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('tplId').value;
        const payload = {
            id: id ? parseInt(id) : null,
            descripcion: document.getElementById('tplDesc').value,
            tipo: document.getElementById('tplTipo').value,
            monto_estimado_usd: parseFloat(document.getElementById('tplMonto').value),
            dia_mes_estimado: parseInt(document.getElementById('tplDia').value)
        };
        try {
            await fetch('/api/expense-templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            closeExpenseTplModal();
            fetchExpenseTemplates();
        } catch (err) { alert('Error al guardar plantilla'); }
    });

    window.deleteExpenseTpl = async (id) => {
        if (!confirm('¿Eliminar plantilla? Todos los próximos cálculos la omitirán, pero los lotes ya guardados seguirán iguales.')) return;
        try {
            await fetch(`/api/expense-templates/${id}`, { method: 'DELETE' });
            fetchExpenseTemplates();
        } catch (e) { alert('Error al eliminar'); }
    };

    // Lotes Modificables
    window.currentBatchData = [];
    window.generateExpenseBatch = async () => {
        const mes = document.getElementById('batchMes').value;
        const anio = document.getElementById('batchAnio').value;
        if (!mes || !anio) return alert("Seleccione Mes y Año válidos.");

        document.getElementById('saveBatchBtn').style.display = 'inline-flex';
        document.getElementById('batchSection').style.display = 'block';
        const _extra1 = document.getElementById('batchControlsExtra');
        if (_extra1) _extra1.style.display = 'flex';

        const tbodyFijos = document.getElementById('expenseBatchBodyFijos');
        const tbodyAdhoc = document.getElementById('expenseBatchBodyAdhoc');
        tbodyFijos.innerHTML = `<tr><td colspan="5" class="loading-cell"><div class="loader"></div><p>Generando simulación...</p></td></tr>`;
        tbodyAdhoc.innerHTML = '';

        try {
            const res = await fetch(`/api/expenses/generate-batch/${mes}/${anio}`);
            const { data } = await res.json();

            // Assign isAdhoc flag
            window.currentBatchData = data.map(d => ({ ...d, isAdhoc: false }));

            if (!data.length) {
                tbodyFijos.innerHTML = `<tr><td colspan="5" style="text-align: center;">No hay plantillas para generar. Registre plantillas primero.</td></tr>`;
                document.getElementById('saveBatchBtn').style.display = 'none';
                return;
            }

            await fetchCashflowForBatch();
            renderBatchTable();
            fetchSavedBatch();
        } catch (e) { tbodyFijos.innerHTML = `<tr><td colspan="6" class="text-danger">Error al generar.</td></tr>`; }
    };

    window.renderBatchTable = () => {
        const tbodyFijos = document.getElementById('expenseBatchBodyFijos');
        const tbodyAdhoc = document.getElementById('expenseBatchBodyAdhoc');

        const rowTemplate = (t, idx) => {
            const fecha = (t.fecha_proyectada || '').slice(0, 10);
            const saldoCajaUsd = (window.batchCashflowMap || {})[fecha];
            const saldoCell = saldoCajaUsd !== undefined
                ? `<span style="color: ${saldoCajaUsd >= 0 ? '#34d399' : '#f87171'}; font-weight:600;">$${parseFloat(saldoCajaUsd).toLocaleString('es-VE', {minimumFractionDigits:2,maximumFractionDigits:2})}</span>`
                : `<span style="color: var(--text-secondary);">—</span>`;
            return `
            <tr>
                <td style="text-align: center; vertical-align: middle;">
                    ${t.isAdhoc ?
                `<button class="btn btn-primary btn-sm" onclick="saveSingleAdhocExpense(${idx})" style="padding: 2px 6px;"><i data-lucide="check"></i> Guardar</button>`
                : `<input type="checkbox" class="batch-checkbox form-control" style="width: 18px; height: 18px; cursor: pointer; display: inline-block; margin: 0;" data-index="${idx}">`
            }
                </td>
                <td style="font-weight: 500;">
                    <input type="text" class="form-control" style="background:#1e293b; color:var(--text-primary); border:1px solid #334155; padding:0.25rem 0.5rem;" 
                    value="${t.descripcion}" oninput="window.currentBatchData[${idx}].descripcion=this.value" placeholder="Descripción...">
                </td>
                <td>
                    <select class="form-control" style="background:#1e293b; color:${t.tipo === 'Farmacia' ? '#fb923c' : '#c026d3'}; border:1px solid #334155; padding:0.25rem 0.5rem; width: 140px;" onchange="window.currentBatchData[${idx}].tipo=this.value; renderBatchTable()">
                        <option value="Farmacia" style="color: #fb923c;" ${t.tipo === 'Farmacia' ? 'selected' : ''}>Farmacia</option>
                        <option value="Personal" style="color: #c026d3;" ${t.tipo === 'Personal' ? 'selected' : ''}>Personal</option>
                    </select>
                </td>
                <td class="amount">
                     <input type="number" class="form-control" step="0.01" style="width:100px; display:inline-block; background:#1e293b; color:var(--text-primary); border:1px solid #334155; padding:0.25rem 0.5rem;" 
                    value="${t.monto_usd}" oninput="window.currentBatchData[${idx}].monto_usd=parseFloat(this.value)">
                </td>
                <td class="amount">
                     <input type="date" class="form-control" style="width:130px; display:inline-block; background:#1e293b; color:var(--text-primary); border:1px solid #334155; padding:0.25rem 0.5rem;" 
                    value="${fecha}" oninput="window.updateBatchDate(${idx}, this)">
                </td>
                <td class="amount">${saldoCell}</td>
            </tr>
        `;};

        tbodyFijos.innerHTML = window.currentBatchData.map((t, idx) => !t.isAdhoc ? rowTemplate(t, idx) : '').join('');
        tbodyAdhoc.innerHTML = window.currentBatchData.map((t, idx) => t.isAdhoc ? rowTemplate(t, idx) : '').join('');

        // Apply formatting trick to newly generated inputs
        document.querySelectorAll('#expenseBatchTableFijos input[type="date"], #expenseBatchTableAdhoc input[type="date"]').forEach(el => setupDateInput(el));

        if (tbodyAdhoc.innerHTML.trim() === '') {
            tbodyAdhoc.innerHTML = `<tr><td colspan="5" style="text-align: center; color: #64748b;">No hay gastos variables añadidos.</td></tr>`;
        }
        lucide.createIcons();
    };

    window.updateBatchDate = (idx, el) => {
        window.currentBatchData[idx].fecha_proyectada = getDateValue(el);
    };

    window.saveExpenseBatch = async () => {
        if (!confirm("Advertencia: Solo se reemplazarán los registros SELECCIONADOS (tildados) de ese mes. Los no seleccionados quedarán intactos. ¿Deseas continuar?")) return;

        const mes = parseInt(document.getElementById('batchMes').value);
        const anio = parseInt(document.getElementById('batchAnio').value);

        // Filter only checked items
        const checkboxes = document.querySelectorAll('.batch-checkbox');
        const selectedGastos = [];
        checkboxes.forEach((cb) => {
            if (cb.checked) {
                const idx = parseInt(cb.getAttribute('data-index'));
                selectedGastos.push(window.currentBatchData[idx]);
            }
        });

        if (selectedGastos.length === 0) {
            return alert("Debe seleccionar al menos un gasto para guardar.");
        }

        // Pass the descriptions of selected items so the backend only deletes those
        const descripcionesAEliminar = selectedGastos.map(g => g.descripcion);

        try {
            const res = await fetch('/api/expenses/batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mes, anio, gastos: selectedGastos, descripcionesAEliminar })
            });
            if (!res.ok) throw new Error('Error de servidor al guardar lote');
            alert("Lote guardado exitosamente en la base de datos de Pronósticos.");
            fetchSavedBatch();
        } catch (e) { alert("Error al guardar Lote"); }
    };

    window.saveSingleAdhocExpense = async (idx) => {
        const item = window.currentBatchData[idx];
        if (!item.descripcion || item.monto_usd <= 0) return alert("Ingrese descripción y un monto mayor a 0.");

        try {
            const res = await fetch('/api/expenses/programmed/single', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(item)
            });
            if (!res.ok) throw new Error('Error de servidor al guardar variable');
            // Remove the ad-hoc row from the UI
            window.currentBatchData.splice(idx, 1);
            renderBatchTable();
            fetchSavedBatch();
        } catch (e) { alert("Error al guardar gasto variable"); }
    };

    window.addAdhocExpense = () => {
        document.getElementById('saveBatchBtn').style.display = 'inline-flex';
        document.getElementById('batchSection').style.display = 'block';
        const _extra2 = document.getElementById('batchControlsExtra');
        if (_extra2) _extra2.style.display = 'flex';

        const anio = document.getElementById('batchAnio').value || new Date().getFullYear();
        let mes = document.getElementById('batchMes').value || (new Date().getMonth() + 1);
        mes = mes.toString().padStart(2, '0');

        window.currentBatchData.push({
            descripcion: '',
            tipo: 'Farmacia',
            monto_usd: 0,
            fecha_proyectada: `${anio}-${mes}-15`,
            estado: 'Pendiente',
            isAdhoc: true
        });
        window.renderBatchTable();
    };

    // Gastos ya guardados del mes seleccionado
    window.expenseSavedBatchData = [];
    window.renderSavedBatchTable = () => {
        const tbody = document.getElementById('expenseSavedBatchBody');
        const searchInput = document.getElementById('expenseSavedBatchSearch');
        if (!tbody) return;

        let filteredData = window.expenseSavedBatchData;
        if (searchInput && searchInput.value) {
            const query = searchInput.value.toLowerCase();
            filteredData = filteredData.filter(t => t.descripcion.toLowerCase().includes(query));
        }

        if (!filteredData.length) {
            const colSpan = 7;
            if (window.expenseSavedBatchData.length) {
                tbody.innerHTML = `<tr><td colspan="${colSpan}" style="text-align: center; color: var(--text-secondary);">No hay resultados para la búsqueda.</td></tr>`;
            } else {
                tbody.innerHTML = `<tr><td colspan="${colSpan}" style="text-align: center; color: var(--text-secondary);">El mes está limpio en la base de datos.</td></tr>`;
            }
            return;
        }
        tbody.innerHTML = filteredData.map(t => {
            const fecha = (t.fecha_proyectada || '').slice(0, 10);
            const saldoCajaUsd = (window.batchCashflowMap || {})[fecha];
            const saldoCell = saldoCajaUsd !== undefined
                ? `<span style="color: ${saldoCajaUsd >= 0 ? '#34d399' : '#f87171'}; font-weight:600;">$${parseFloat(saldoCajaUsd).toLocaleString('es-VE', {minimumFractionDigits:2,maximumFractionDigits:2})}</span>`
                : `<span style="color: var(--text-secondary);">—</span>`;
            return `
            <tr>
                <td style="font-weight: 500;">${t.descripcion}</td>
                <td><span class="status-badge" style="background: ${t.tipo === 'Farmacia' ? 'rgba(251, 146, 60, 0.1)' : 'rgba(192, 38, 211, 0.1)'}; color: ${t.tipo === 'Farmacia' ? '#fb923c' : '#c026d3'};">${t.tipo}</span></td>
                <td class="amount">${usdFormatter(t.monto_usd)}</td>
                <td class="amount">
                    <input type="date" class="form-control" value="${fecha}"
                        style="background:#1e293b; color:var(--text-primary); border:1px solid #334155; padding:0.2rem 0.4rem; width:130px;"
                        onchange="updateSavedExpenseDate(${t.id}, this.value)">
                </td>
                <td class="amount">${saldoCell}</td>
                <td class="amount"><span class="status-badge">${t.estado}</span></td>
                <td class="amount">
                    <button class="btn-icon text-danger" onclick="deleteSavedExpense(${t.id})">
                        <i data-lucide="trash-2"></i>
                    </button>
                </td>
            </tr>
        `}).join('');
        lucide.createIcons();
    };

    const fetchSavedBatch = async () => {
        const mes = document.getElementById('batchMes').value;
        const anio = document.getElementById('batchAnio').value;
        const tbody = document.getElementById('expenseSavedBatchBody');
        if (!tbody || !mes || !anio) return;

        try {
            const [savedRes] = await Promise.all([
                fetch(`/api/expenses/programmed?mes=${mes}&anio=${anio}`),
                fetchCashflowForBatch()
            ]);
            const { data } = await savedRes.json();
            window.expenseSavedBatchData = data || [];
            window.renderSavedBatchTable();
        } catch (e) { tbody.innerHTML = `<tr><td colspan="7" class="text-danger">Error.</td></tr>`; }
    }

    window.deleteSavedExpense = async (id) => {
        if (!confirm('¿Eliminar definitivamente ente gasto del mes?')) return;
        try {
            await fetch(`/api/expenses/programmed/${id}`, { method: 'DELETE' });
            fetchSavedBatch();

            // Force refresh of flow dashboard if user returns
            if (window.forecastConsChartInstance) {
                window.forecastConsChartInstance.destroy();
                window.forecastConsChartInstance = null;
            }
            if (document.querySelector('.view-section.active')?.id === 'view-forecast-consolidated') {
                fetchForecastConsolidated();
            }
        } catch (e) { alert('Error al eliminar'); }
    };

    window.updateSavedExpenseDate = async (id, nuevaFecha) => {
        try {
            const res = await fetch(`/api/expenses/programmed/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fecha_proyectada: nuevaFecha })
            });
            if (!res.ok) throw new Error('Error al actualizar fecha');
            // Re-fetch so Saldo Caja column refreshes too
            await fetchSavedBatch();
        } catch (e) { alert('Error al guardar nueva fecha'); }
    };

    // Read cashflow data for month so Saldo Caja can be shown per-date
    window.batchCashflowMap = {};
    const fetchCashflowForBatch = async () => {
        try {
            const params = JSON.parse(localStorage.getItem('cashflowParams') || '{}');
            const cajaUsd = params.cajaUsd || 0;
            const cajaBs = params.cajaBs || 0;
            const fechaArranque = params.fechaCero || new Date().toISOString().slice(0, 10);
            const delayDays = params.toggleDelay ? (params.retardoDays || 1) : 0;
            const res = await fetch(`/api/reports/forecast-consolidated?fecha_arranque=${encodeURIComponent(fechaArranque)}&caja_usd=${cajaUsd}&caja_bs=${cajaBs}&delay_days=${delayDays}`);
            if (!res.ok) return;
            const { data } = await res.json();
            window.batchCashflowMap = {};
            (data || []).forEach(row => {
                window.batchCashflowMap[row.Periodo] = row.SaldoRealCajaUSD;
            });
        } catch (e) { console.warn('No se pudo cargar el cashflow para Saldo Caja:', e); }
    };

    window.selectBatch = (mode) => {
        const checkboxes = document.querySelectorAll('.batch-checkbox');
        checkboxes.forEach(cb => {
            if (mode === 'all') cb.checked = true;
            else if (mode === 'none') cb.checked = false;
            else if (mode === 'invert') cb.checked = !cb.checked;
        });
    };

    window.filterBatchTable = () => {
        const query = (document.getElementById('batchDescSearch')?.value || '').toLowerCase();
        const rows = document.querySelectorAll('#expenseBatchBodyFijos tr');
        rows.forEach(row => {
            const desc = row.querySelector('input[type="text"]')?.value?.toLowerCase() || '';
            row.style.display = (!query || desc.includes(query)) ? '' : 'none';
        });
    };

    // Auto-Set de Mes y Año en Batch y Cargar Lotes Previos
    const dateObj = new Date();
    const meshp = document.getElementById('batchMes');
    const aniohp = document.getElementById('batchAnio');
    if (meshp) {
        meshp.value = dateObj.getMonth() + 1;
        meshp.addEventListener('change', fetchSavedBatch);
    }
    if (aniohp) {
        // aniohp.value is already set to 2026/2027 in HTML usually, but we ensure listeners
        aniohp.addEventListener('change', fetchSavedBatch);
    }

    // ----- Módulo de Proveedores (Condiciones de Indexación) -----
    let providersData = [];

    window.openProviderCondModal = () => {
        providerCondModal.classList.add('active');
        fetchProviders();
    };

    window.closeProviderCondModal = () => {
        providerCondModal.classList.remove('active');
    };

    window.closeEditProviderModal = () => {
        editProviderCondModal.classList.remove('active');
        editProvForm.reset();
    };

    const fetchProviders = async () => {
        providersTableBody.innerHTML = `<tr><td colspan="8" class="loading-cell"><div class="loader"></div><p>Cargando proveedores...</p></td></tr>`;
        try {
            const res = await fetch('/api/procurement/providers');
            if (!res.ok) throw new Error("Error al obtener proveedores");
            const json = await res.json();
            providersData = json.data || [];
            renderProvidersTable();
        } catch (error) {
            console.error('Error fetching providers:', error);
            providersTableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--danger);">Error al cargar proveedores.</td></tr>`;
        }
    };

    const renderProvidersTable = () => {
        const searchTerm = (providerSearchInput.value || '').toLowerCase();
        const showOnlyActive = providerActivoCheck ? providerActivoCheck.checked : true;

        const filtered = providersData.filter(p => {
            const matchesSearch = p.CodProv.toLowerCase().includes(searchTerm) ||
                (p.Descrip && p.Descrip.toLowerCase().includes(searchTerm));
            const matchesActive = showOnlyActive ? p.activo === 1 : true;
            return matchesSearch && matchesActive;
        });

        if (filtered.length === 0) {
            providersTableBody.innerHTML = `<tr><td colspan="8" style="text-align: center;">No hay resultados.</td></tr>`;
            return;
        }

        providersTableBody.innerHTML = filtered.map(p => `
            <tr>
                <td>${p.CodProv}</td>
                <td>${p.Descrip}</td>
                <td>${p.BaseDiasCredito === 'EMISION' ? 'Emisión' : 'Recepción'}</td>
                <td>${p.DiasNoIndexacion}</td>
                <td>${p.DiasVencimiento}</td>
                <td>${p.Email || '-'}</td>
                <td><span class="status-badge" style="background:var(--bg-secondary);">${p.TipoPersona || 'Auto'}</span></td>
                <td>${p.Descuentos ? p.Descuentos.length : 0} tramos</td>
                <td>${p.IndexaIVA !== false ? '<span style="color:var(--success);">Sí</span>' : '<span style="color:var(--danger);">No</span>'}</td>
                <td>
                    <button class="btn-icon" title="Editar Condiciones" onclick="openEditProvider('${p.CodProv}')">
                        <i data-lucide="edit-3" size="18"></i>
                    </button>
                </td>
            </tr>
        `).join('');
        lucide.createIcons();
    };

    window.openEditProvider = (codProv) => {
        if(!providersData || providersData.length === 0) {
            showToast('Cargando datos del proveedor, reintente en 1 segundo...', 'info');
            return;
        }
        const p = providersData.find(x => String(x.CodProv).trim() === String(codProv).trim());
        if (!p) {
            showToast('⚠️ No se encontraron condiciones para este proveedor.', 'warning');
            return;
        }

        document.getElementById('editProvTitle').textContent = `Editar: ${p.Descrip}`;
        document.getElementById('editProvCod').value = p.CodProv;
        document.getElementById('editProvBase').value = p.BaseDiasCredito;
        document.getElementById('editProvDiasNI').value = p.DiasNoIndexacion;
        document.getElementById('editProvDiasV').value = p.DiasVencimiento;
        if(document.getElementById('editProvIndexaIVA')) {
            document.getElementById('editProvIndexaIVA').checked = (p.IndexaIVA !== false && p.IndexaIVA !== 0 && p.IndexaIVA !== '0');
        }
        if(document.getElementById('editProvDecimales')) {
            document.getElementById('editProvDecimales').value = p.DecimalesTasa || 4;
        }
        
        if(document.getElementById('editProvDescBasePct')) {
            document.getElementById('editProvDescBasePct').value = (p.DescuentoBase_Pct || 0).toFixed(2);
        }
        if(document.getElementById('editProvDescBaseCond')) {
            document.getElementById('editProvDescBaseCond').value = p.DescuentoBase_Condicion || 'INDEPENDIENTE';
        }
        if (document.getElementById('editProvDescBaseDeduceIVA')) {
            document.getElementById('editProvDescBaseDeduceIVA').checked = (p.DescuentoBase_DeduceIVA !== false && p.DescuentoBase_DeduceIVA !== 0);
        }

        document.getElementById('editProvEmail').value = p.Email || '';
        const tpSel = document.getElementById('editProvTipoPersona');
        if (tpSel) tpSel.value = (p.TipoPersonaLocal || '').trim();

        if (document.getElementById('editProvEsReten')) {
            document.getElementById('editProvEsReten').checked = (p.EsReten !== false && p.EsReten !== 0);
        }
        if (document.getElementById('editProvPorctRet')) {
            document.getElementById('editProvPorctRet').value = p.PorctRet || 75;
        }
        
        const container = document.getElementById('descuentosContainer');
        container.innerHTML = '';
        if (p.Descuentos && p.Descuentos.length > 0) {
            p.Descuentos.forEach(d => addDescuentoRow(d.DiasDesde, d.DiasHasta, d.Porcentaje, d.DeduceIVA));
        } else {
            // Optional: fallback empty row
        }

        editProviderCondModal.classList.add('active');
    };

    function addDescuentoRow(dDesde = '', dHasta = '', pct = '', deduceIVA = false) {
        const container = document.getElementById('descuentosContainer');
        const row = document.createElement('div');
        row.style.display = 'grid';
        row.style.gridTemplateColumns = '1fr 1fr 1fr auto auto';
        row.style.gap = '0.5rem';
        row.style.alignItems = 'center';
        row.className = 'descuento-row';
        row.innerHTML = `
            <input type="number" class="form-control desc-desde" placeholder="Días Desde" value="${dDesde}" min="0" required title="Días desde emisión de factura">
            <input type="number" class="form-control desc-hasta" placeholder="Días Hasta" value="${dHasta}" min="0" required title="Use 999 para indicar 'hasta vencimiento'">
            <input type="number" class="form-control desc-pct" placeholder="% Dcto" value="${pct}" step="0.01" min="0" required>
            <div style="display:flex; align-items:center; gap:0.25rem;">
                <input type="checkbox" class="desc-deduce-iva" title="¿Deduce IVA?" ${deduceIVA !== false && deduceIVA !== 0 ? 'checked' : ''} style="cursor:pointer; width:1.2rem; height:1.2rem;">
            </div>
            <button type="button" class="btn-icon" style="color:var(--danger);" onclick="this.parentElement.remove()"><i data-lucide="trash-2" size="16"></i></button>
        `;
        container.appendChild(row);
        lucide.createIcons();
    }

    const btnAddDescuento = document.getElementById('btnAddDescuento');
    if (btnAddDescuento) {
        btnAddDescuento.addEventListener('click', () => {
            const container = document.getElementById('descuentosContainer');
            const rows = container.querySelectorAll('.descuento-row');
            let nextDesde = 0;
            if (rows.length > 0) {
                const lastHasta = parseInt(rows[rows.length - 1].querySelector('.desc-hasta').value);
                if (!isNaN(lastHasta) && lastHasta < 999) nextDesde = lastHasta + 1;
            }
            addDescuentoRow(nextDesde, '', '');
        });
    }

    if (editProvForm) {
        editProvForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const codProv = document.getElementById('editProvCod').value;
            
            const descRows = document.querySelectorAll('.descuento-row');
            const Descuentos = Array.from(descRows).map(row => ({
                DiasDesde: parseInt(row.querySelector('.desc-desde').value) || 0,
                DiasHasta: parseInt(row.querySelector('.desc-hasta').value) || 0,
                Porcentaje: parseFloat(row.querySelector('.desc-pct').value) || 0,
                DeduceIVA: row.querySelector('.desc-deduce-iva')?.checked ?? false
            }));

            const payload = {
                CodProv: codProv,
                BaseDiasCredito: document.getElementById('editProvBase').value,
                DiasNoIndexacion: parseInt(document.getElementById('editProvDiasNI').value) || 0,
                DiasVencimiento: parseInt(document.getElementById('editProvDiasV').value) || 0,
                Descuentos: Descuentos,
                DescuentoBase_Pct: parseFloat(document.getElementById('editProvDescBasePct')?.value) || 0,
                DescuentoBase_Condicion: document.getElementById('editProvDescBaseCond')?.value || 'INDEPENDIENTE',
                DescuentoBase_DeduceIVA: document.getElementById('editProvDescBaseDeduceIVA')?.checked ?? false,
                Email: document.getElementById('editProvEmail').value || null,
                IndexaIVA: document.getElementById('editProvIndexaIVA')?.checked ?? true,
                DecimalesTasa: parseInt(document.getElementById('editProvDecimales')?.value) || 4,
                TipoPersona: document.getElementById('editProvTipoPersona')?.value || null,
                PorctRet: parseFloat(document.getElementById('editProvPorctRet')?.value) || 75,
                EsReten: document.getElementById('editProvEsReten')?.checked ?? true
            };

            const btn = editProvForm.querySelector('button[type="submit"]');
            const originalText = btn.textContent;
            btn.textContent = 'Guardando...';
            btn.disabled = true;

            try {
                const res = await fetch(`/api/procurement/providers/${encodeURIComponent(codProv)}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) {
                    const err = await res.json();
                    let errMsg = err.detail || 'Error al guardar parametrización';
                    if (typeof errMsg === 'object') {
                        errMsg = JSON.stringify(errMsg, null, 2);
                    }
                    throw new Error(errMsg);
                }
                closeEditProviderModal();
                fetchProviders(); // Refresh config list

                // Auto-recalculate any open payment modal for this provider
                if (typeof window._abRecalcAfterProviderSave === 'function') {
                    await window._abRecalcAfterProviderSave(codProv);
                }
                if (typeof window._pmRecalcAfterProviderSave === 'function') {
                    await window._pmRecalcAfterProviderSave(codProv);
                }

                // Update type in current data cache if it exists
                if (window.currentData) {
                    window.currentData.forEach(item => {
                        if (item.CodProv === codProv) {
                            item.TipoPersona = payload.TipoPersona; 
                        }
                    });
                    if (typeof fetchData === 'function') await fetchData();
                }
            } catch (error) {
                console.error(error);
                alert(`Error al guardar condiciones:\n${error.message}`);
            } finally {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        });
    }

    if (document.getElementById('openProvidersBtn')) {
        document.getElementById('openProvidersBtn').addEventListener('click', openProviderCondModal);
    }
    if (document.getElementById('refreshProvidersBtn')) {
        document.getElementById('refreshProvidersBtn').addEventListener('click', fetchProviders);
    }
    if (providerSearchInput) {
        providerSearchInput.addEventListener('input', renderProvidersTable);
    }
    // ----- Módulo de Abonos y Pagos -----
    const abonosModal = document.getElementById('abonosModal');
    const abonoForm = document.getElementById('abonoForm');

    // UI Elements
    const abMontoOrigBs = document.getElementById('abMontoOrigBs');
    const abMontoOrigUsd = document.getElementById('abMontoOrigUsd');
    const abFechaBase = document.getElementById('abFechaBase');
    const abFechaNI = document.getElementById('abFechaNI');
    const abFechaV = document.getElementById('abFechaV');
    const abSaldoUsd = document.getElementById('abSaldoUsd');
    const abonosHistoryBody = document.getElementById('abonosHistoryBody');

    // Form Inputs
    const abCodProv = document.getElementById('abCodProv');
    const abNumeroD = document.getElementById('abNumeroD');
    const abFechaPago = document.getElementById('abFechaPago');
    const abMontoBs = document.getElementById('abMontoBs');
    const abTasa = document.getElementById('abTasa');
    const abMontoUsd = document.getElementById('abMontoUsd');
    const abAplicaIndex = document.getElementById('abAplicaIndex');
    const abIndexaIva = document.getElementById('abIndexaIVA');
    const abReferencia = document.getElementById('abReferencia');
    const abTasaLoader = document.getElementById('abTasaLoader');

    let currentCxpStatus = null;
    let lastAutoFilledBs = '';

    window.abOpenEditProviderSafe = async () => {
        const codProv = document.getElementById('abCodProv').value;
        if (!codProv) { showToast('⚠️ No hay proveedor activo.', 'warning'); return; }
        
        if (!providersData || providersData.length === 0) {
            try {
                if (typeof fetchProviders === 'function') await fetchProviders();
            } catch(e) {}
        }
        
        if (typeof window.openEditProvider === 'function') {
            window.openEditProvider(codProv);
        }
    };

    window.openAbonosPanel = async (codProv, numeroD, nroUnico = null) => {
        abonosModal.classList.add('active');
        resetAbonoForm();

        abCodProv.value = codProv;
        abNumeroD.value = numeroD;
        if (nroUnico) {
            abonosModal.dataset.nrounico = nroUnico;
        } else {
            delete abonosModal.dataset.nrounico;
        }

        // Use today's date by default for payment
        setupDateInput(abFechaPago);
        setDateValue(abFechaPago, new Date().toISOString().split('T')[0]);

        await fetchCxpStatus(codProv, numeroD, nroUnico);
        await updateExchangeRate(); // fetch rate for today's date
    };

    window.closeAbonosModal = () => {
        abonosModal.classList.remove('active');
        currentCxpStatus = null;
    };

    const resetAbonoForm = () => {
        abonoForm.reset();
        abMontoBs.value = '';
        abMontoUsd.value = '';
        abTasa.value = '';
        abAplicaIndex.checked = false;
        if(abIndexaIva) abIndexaIva.checked = true;
        
        const abProntoPago = document.getElementById('abProntoPago');
        const abTipoDescuento = document.getElementById('abTipoDescuento');
        if (abProntoPago) abProntoPago.checked = false;
        if (abTipoDescuento) {
            abTipoDescuento.disabled = true;
            abTipoDescuento.innerHTML = '<option value="0">Descuento 0%</option>';
        }

        lastAutoFilledBs = '';

        abMontoOrigBs.textContent = 'Cargando...';
        abMontoOrigUsd.textContent = '...';
        abFechaBase.textContent = '...';
        abFechaNI.textContent = '...';
        abFechaV.textContent = '...';
        abSaldoUsd.textContent = '...';
        const abBI = document.getElementById('abBaseImponible');
        const abIVA = document.getElementById('abIVA');
        const abEx = document.getElementById('abExento');
        if (abBI) abBI.textContent = '...';
        if (abIVA) abIVA.textContent = '...';
        if (abEx) abEx.textContent = '...';
        abonosHistoryBody.innerHTML = `<tr><td colspan="7" class="loading-cell"><div class="loader"></div></td></tr>`;

        const abTasaBadge = document.getElementById('abTasaBadge');
        if (abTasaBadge) abTasaBadge.textContent = 'Tasa: —';
    };


    // ── Motivos de Ajuste y Notas de Crédito: cargar ─────────────────────────
    window.motivosNC = [];
    window.loadMotivosAjuste = async () => {
        try {
            const res = await fetch('/api/procurement/motivos-ajuste?solo_activos=true');
            if (!res.ok) return;
            const { data } = await res.json();
            
            const ajustes = data.filter(m => m.ParaAjuste);
            window.motivosNC = data.filter(m => m.ParaNotaCredito);

            const optsAjuste = ajustes.map(m => `<option value="${m.MotivoID}">[${m.Codigo}] ${m.Descripcion}</option>`).join('');
            ['abMotivoAjuste', 'pmMotivoAjuste'].forEach(id => {
                const sel = document.getElementById(id);
                if (sel) sel.innerHTML = '<option value="">— Seleccione Motivo —</option>' + optsAjuste;
            });

            // If the note of credit modal is active, we can populate its dropdown too
            const drpnc = document.getElementById('cncMotivo'); // we'll need to check the actual ID of the NC dropdown
            if (drpnc) {
                const optsNC = window.motivosNC.map(m => `<option value="${m.Descripcion}">[${m.Codigo || ''}] ${m.Descripcion}</option>`).join('');
                drpnc.innerHTML = '<option value="">— Seleccione Motivo —</option>' + optsNC;
            }
        } catch(e) { console.warn('No se pudieron cargar motivos', e); }
    };

    // Toggle motivo row visibility
    document.addEventListener('change', (e) => {
        if (e.target.id === 'abPermitirAjuste') {
            const row = document.getElementById('abAjusteRow');
            if (row) row.style.display = e.target.checked ? 'flex' : 'none';
        }
        if (e.target.id === 'pmPermitirAjuste') {
            const row = document.getElementById('pmAjusteRow');
            if (row) row.style.display = e.target.checked ? 'flex' : 'none';
        }
    });

    window.loadMotivosAjuste(); // load once on init

    const fetchCxpStatus = async (codProv, numeroD, nroUnico = null) => {
        try {
            let url = `/api/procurement/cxp-status?cod_prov=${encodeURIComponent(codProv)}&numero_d=${encodeURIComponent(numeroD)}`;
            if (nroUnico) url += `&nro_unico=${encodeURIComponent(nroUnico)}`;
            const res = await fetch(url);
            if (!res.ok) throw new Error("Factura no encontrada");
            const json = await res.json();
            currentCxpStatus = json.data;
            window._globalCxpStatus = currentCxpStatus;
            renderCxpStatus();
            checkIndexationStatus();
            // Restore previously saved ISLR concept for this invoice
            const savedIslr = localStorage.getItem(`islr_${numeroD}`);
            const islrSel = document.getElementById('abConceptoISLR');
            if (savedIslr && islrSel) {
                islrSel.value = savedIslr;
            }
        } catch (error) {
            console.error('Error fetching cxp status:', error);
            alert('Error al cargar datos de la factura.');
            closeAbonosModal();
        }
    };

    const renderCxpStatus = () => {
        if (!currentCxpStatus) return;
        const d = currentCxpStatus;

        document.getElementById('abonoModalSubtitle').textContent = `Factura: ${d.NumeroD} | Proveedor: ${d.ProveedorNombre || d.CodProv}`;

        abMontoOrigBs.textContent = formatBs(d.Monto);
        abMontoOrigUsd.textContent = usdFormatter(d.MontoOriginalUSD);

        // Fiscal breakdown: Base Imponible, IVA, Exento
        const tGravable = d.TGravable || 0;
        const mtoTax = d.MtoTax || 0;
        const exento = Math.max(0, (d.Monto || 0) - tGravable - mtoTax);
        const abBIel = document.getElementById('abBaseImponible');
        const abIVAel = document.getElementById('abIVA');
        const abExel = document.getElementById('abExento');
        const abIvaUsdEl = document.getElementById('abIvaUsd');

        if (abBIel) abBIel.textContent = formatBs(tGravable);
        if (abIVAel) abIVAel.textContent = formatBs(mtoTax);
        if (abExel) abExel.textContent = formatBs(exento);
        if (abIvaUsdEl) {
            const ivaUsd = d.TasaEmision ? (mtoTax / d.TasaEmision) : 0;
            abIvaUsdEl.textContent = usdFormatter(ivaUsd);
        }

        const baseDate = d.BaseDiasCredito === 'EMISION' ? d.FechaE : (d.FechaI || d.FechaE);
        abFechaBase.textContent = formatDate(baseDate);
        abFechaNI.textContent = formatDate(d.FechaNI_Calculada);
        // Use the official expiration date from SAACXP instead of the calculated one
        abFechaV.textContent = formatDate(d.FechaVSaint || d.FechaV_Calculada);

        // UI bound dynamically in fillDefaultPaymentAmount, but we set a placeholder here
        abSaldoUsd.textContent = '...';

        const abTipoDescuento = document.getElementById('abTipoDescuento');
        const abProntoPago = document.getElementById('abProntoPago');
        const abPPDeduceIVA = document.getElementById('abPPDeduceIVA');

        const abBtnRetIva = document.getElementById('abBtnRetIva');
        if (abBtnRetIva) {
            const hasIva = (parseFloat(d.MtoTax) || 0) > 0 || (parseFloat(d.TGravable) || 0) > 0;
            const hasRetIva = (d.HistorialAbonos && d.HistorialAbonos.some(a => a.TipoAbono === 'RETENCION_IVA')) || hasRet(d) || (parseFloat(d.RetencionIvaAbonada) || 0) > 0;
            if (!hasIva || hasRetIva) {
                abBtnRetIva.style.color = '#10b981';
                abBtnRetIva.style.borderColor = 'rgba(16,185,129,0.4)';
                abBtnRetIva.style.background = 'rgba(16,185,129,0.05)';
            } else {
                abBtnRetIva.style.color = '#eab308';
                abBtnRetIva.style.borderColor = 'rgba(234,179,8,0.4)';
                abBtnRetIva.style.background = 'rgba(234,179,8,0.05)';
            }
        }

        // Render Descuento Comercial Base info
        const abDescBaseAplica = document.getElementById('abDescBaseAplica');
        const abDescBaseInfo = document.getElementById('abDescBaseInfo');
        const abDescBaseDeduceIVA = document.getElementById('abDescBaseDeduceIVA');
        if (abDescBaseAplica && abDescBaseInfo) {
            const descBasePct = parseFloat(d.DescuentoBase_Pct) || 0;
            if (descBasePct > 0) {
                let appliesInitially = true;
                if (d.DescuentoBase_Condicion === 'VENCIMIENTO') {
                    const pagoD = new Date(getDateValue(document.getElementById('abFechaPago')) || new Date());
                    const vD = new Date(d.FechaVSaint || d.FechaV_Calculada);
                    pagoD.setHours(0,0,0,0); vD.setHours(0,0,0,0);
                    if (pagoD > vD) appliesInitially = false;
                }
                abDescBaseAplica.checked = appliesInitially;
                abDescBaseInfo.value = `${descBasePct.toFixed(2)}% (${d.DescuentoBase_Condicion === 'VENCIMIENTO' ? 'A Tiempo' : 'Siempre'})`;
                if (abDescBaseDeduceIVA) {
                    abDescBaseDeduceIVA.disabled = false;
                    abDescBaseDeduceIVA.checked = (d.DescuentoBase_DeduceIVA !== false && d.DescuentoBase_DeduceIVA !== 0);
                }
            } else {
                abDescBaseAplica.checked = false;
                abDescBaseInfo.value = '0% (Inactivo)';
                if (abDescBaseDeduceIVA) {
                    abDescBaseDeduceIVA.disabled = true;
                    abDescBaseDeduceIVA.checked = false;
                }
            }
        }

        if (abTipoDescuento) {
            abTipoDescuento.innerHTML = '';
            let optionsHtml = '<option value="0" data-deduce-iva="false">Descuento 0%</option>';
            if (d.Descuentos && d.Descuentos.length > 0) {
                d.Descuentos.forEach((desc, i) => {
                    optionsHtml += `<option value="${desc.Porcentaje}" data-deduce-iva="${desc.DeduceIVA ? 'true' : 'false'}">T${i+1}: ${parseFloat(desc.Porcentaje).toFixed(2)}%</option>`;
                });
                if (abProntoPago) {
                    abProntoPago.disabled = false;
                    const span = abProntoPago.nextElementSibling;
                    if (span) span.textContent = `Pronto Pago (${d.Descuentos.length} Tramos)`;
                }
            } else {
                if (abProntoPago) {
                    abProntoPago.disabled = true;
                    abProntoPago.checked = false;
                    const span = abProntoPago.nextElementSibling;
                }
            }
            abTipoDescuento.innerHTML = optionsHtml;
            // Si el checkbox está destildado (o se acaba de destildar/deshabilitar), entonces el dropdown se desactiva
            abTipoDescuento.disabled = !(abProntoPago && abProntoPago.checked);
            
            // Sync initial DeduceIVA state for PP
            if (abPPDeduceIVA) {
                const opt = abTipoDescuento.options[abTipoDescuento.selectedIndex];
                abPPDeduceIVA.checked = opt ? opt.getAttribute('data-deduce-iva') === 'true' : false;
                abPPDeduceIVA.disabled = abTipoDescuento.disabled;
            }
        }

        // Update historical UP data
        document.getElementById('abNumeroUP').textContent = d.NumeroUP || '-';
        document.getElementById('abFechaUP').textContent = d.FechaUP ? formatDate(d.FechaUP) : '-';
        document.getElementById('abMontoUP').textContent = d.MontoUP != null ? formatBs(d.MontoUP) : '-';

        // Render History
        if (d.HistorialAbonos && d.HistorialAbonos.length > 0) {
            const tipoBadge = (tipo, afectaSaldo) => {
                if (tipo === 'DESCUENTO') return '<span class="status-badge" style="background:rgba(234,179,8,0.15);color:#fbbf24;">Descuento</span>';
                if (tipo === 'AJUSTE')    return '<span class="status-badge" style="background:rgba(168,85,247,0.15);color:#d8b4fe;">Ajuste</span>';
                const map = {
                    'PAGO_MANUAL':     '<span class="status-badge status-paid">Pago</span>',
                    'PAGO':            '<span class="status-badge status-paid">Pago</span>',
                    'RETENCION_IVA':   '<span class="status-badge" style="background:rgba(139,92,246,0.15);color:#a78bfa;">Ret. IVA</span>',
                    'RETENCION_ISLR':  '<span class="status-badge" style="background:rgba(239,68,68,0.15);color:#f87171;">Ret. ISLR</span>',
                    'NOTA_CREDITO':    '<span class="status-badge" style="background:rgba(59,130,246,0.15);color:#60a5fa;">N/C</span>',
                    'NOTA_DEBITO':     '<span class="status-badge" style="background:rgba(239,68,68,0.15);color:#f87171;">N/D</span>',
                };
                return map[tipo] || `<span class="status-badge">${tipo || 'Pago'}</span>`;
            };
            abonosHistoryBody.innerHTML = d.HistorialAbonos.map(a => {
                const esDescuento = a.TipoAbono === 'DESCUENTO';
                const rowStyle = esDescuento ? 'opacity:0.75; font-style:italic;' : '';
                const displayRef = a.DescripcionAjuste || a.Referencia || '-';
                const displayMonto = esDescuento
                    ? `<span style="color:var(--warning, #fbbf24);">${formatBs(a.MontoBsAbonado)}</span>`
                    : `${formatBs(a.MontoBsAbonado)}`;
                const displayUsd  = esDescuento
                    ? `<span style="color:var(--warning, #fbbf24);">${usdFormatter(a.MontoUsdAbonado)}</span>`
                    : `${usdFormatter(a.MontoUsdAbonado)}`;
                const canDelete = !['RETENCION_IVA', 'RETENCION_ISLR', 'NOTA_CREDITO', 'DESCUENTO'].includes(a.TipoAbono);
                return `
                <tr style="${rowStyle}">
                    <td>${formatDate(a.FechaAbono)}</td>
                    <td>${tipoBadge(a.TipoAbono, a.AfectaSaldo)}</td>
                    <td class="amount">${displayMonto}</td>
                    <td>${bsFormatter(a.TasaCambioDiaAbono)}</td>
                    <td>${a.AplicaIndexacion ? '<span class="status-badge status-overdue">Sí</span>' : '<span class="status-badge status-paid">No</span>'}</td>
                    <td class="amount us-amount">${displayUsd}</td>
                    <td>${displayRef}</td>
                    <td style="text-align:center;">
                        ${canDelete ? `<button class="btn-icon" title="Anular Abono" onclick="anularAbonoCxp(${a.AbonoID}, '${d.CodProv}', '${d.NumeroD}')"><i data-lucide="trash-2" style="color:var(--danger);width:16px;"></i></button>` : `<span style="font-size:0.75rem;color:var(--text-secondary)" title="Registro automático">Auto.</span>`}
                    </td>
                </tr>
            `;}).join('');
        } else {
            abonosHistoryBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-secondary);">No hay abonos registrados.</td></tr>`;
        }
        
        lucide.createIcons();

        window.anularAbonoCxp = async (abonoId, codProv, numeroD) => {
            if (!confirm("¿Está seguro de eliminar este abono? Esta acción restaurará el saldo asociado.")) return;
            try {
                const res = await fetch(`/api/procurement/abonos/${abonoId}`, { method: 'DELETE' });
                if (!res.ok) {
                    const errorText = await res.text();
                    let errMsg = errorText;
                    try { const j = JSON.parse(errorText); if(j.detail) errMsg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail); } catch(e){}
                    throw new Error(errMsg);
                }
                showToast("Abono eliminado exitosamente", "success");
                await fetchCxpStatus(codProv, numeroD);
                if (typeof fetchData === 'function') fetchData(); // Refresh external table
            } catch(e) {
                showToast("Error al anular: " + e.message, "danger");
            }
        };

        // Show tasa for the invoice's BASE DATE (Emisión or Entrega) in the badge
        const baseDateStr = d.BaseDiasCredito === 'EMISION'
            ? (d.FechaE || '').split('T')[0]
            : ((d.FechaI || d.FechaE || '').split('T')[0]);
        const baseDateLabel = d.BaseDiasCredito === 'EMISION' ? 'Tasa Emis.' : 'Tasa Entr.';
        const abTasaBadge = document.getElementById('abTasaBadge');
        if (abTasaBadge && baseDateStr) {
            abTasaBadge.textContent = `${baseDateLabel}: ...`;
            fetch(`/api/exchange-rate?fecha=${encodeURIComponent(baseDateStr)}`)
                .then(r => r.ok ? r.json() : null)
                .then(json => {
                    if (json && json.rate) {
                        const decimals = d.DecimalesTasa !== undefined ? d.DecimalesTasa : 4;
                        abTasaBadge.textContent = `${baseDateLabel}: ${json.rate.toFixed(decimals)}`;
                        abTasaBadge.style.color = 'var(--primary-accent)';
                        abTasaBadge.style.borderColor = 'rgba(99,102,241,0.4)';
                        abTasaBadge.title = `Tasa BCV del d\u00eda de ${d.BaseDiasCredito === 'EMISION' ? 'Emisi\u00f3n' : 'Entrega'} (${formatDate(baseDateStr)})`;
                    } else {
                        abTasaBadge.textContent = `${baseDateLabel}: N/D`;
                        abTasaBadge.style.color = 'var(--text-secondary)';
                    }
                })
                .catch(() => { abTasaBadge.textContent = `${baseDateLabel}: N/D`; });
        }

        // Auto-check indexation based on FechaPago vs FechaNI
        checkIndexationStatus();

        // Phase 13/14 Fix: Ensure the payment amount is suggested on open
        // Reset lastAutoFilledBs to ensure the new invoice gets a fresh calculation
        lastAutoFilledBs = "";
        fillDefaultPaymentAmount(true);
    };

    const updateExchangeRate = async () => {
        const fecha = getDateValue(abFechaPago);
        console.log(`--- CAMBIO DE FECHA: ${fecha} ---`);
        if (!fecha) {
            abTasa.value = '';
            calculateUsdAmount();
            return;
        }

        abTasaLoader.style.display = 'block';
        try {
            const res = await fetch(`/api/exchange-rate?fecha=${encodeURIComponent(fecha)}`);
            if (res.ok) {
                const json = await res.json();
                abTasa.value = json.rate ? json.rate.toFixed(4) : '';
                console.log(`Tasa obtenida para ${fecha}: ${abTasa.value}`);

                checkIndexationStatus();
                fillDefaultPaymentAmount();
                calculateUsdAmount();
            }
        } catch (error) {
            console.error('Error fetching rate:', error);
        } finally {
            abTasaLoader.style.display = 'none';
        }
    };

    // --- Dynamic Invoice Status Modal ---
    window.closeDynamicInvoiceStatusModal = () => {
        const m = document.getElementById('dynamicInvoiceStatusModal');
        if (m) {
            m.classList.remove('active');
            m.style.cssText = "z-index: 10030;"; // Reset to its original inline style from HTML
        }
    };
    // --- Action Bar Event Listeners ---
    document.getElementById('abBtnRetIva')?.addEventListener('click', () => {
        const codProv = abCodProv.value;
        const numeroD = abNumeroD.value;
        const btn = document.getElementById('abBtnRetIva');
        if (btn && btn.dataset.yaCreada === "true") {
            window.open(`/api/retenciones/by-invoice/${encodeURIComponent(numeroD)}/pdf?cod_prov=${encodeURIComponent(codProv)}`, '_blank');
        } else {
            closeAbonosModal();
            openRetencionFromMain(codProv, numeroD);
        }
    });

    document.getElementById('abBtnRetIslr')?.addEventListener('click', () => {
        const codProv = abCodProv.value;
        const numeroD = abNumeroD.value;
        const btn = document.getElementById('abBtnRetIslr');
        if (btn && btn.dataset.yaCreada === "true") {
            window.open(`/api/retenciones-islr/by-invoice/${encodeURIComponent(numeroD)}/pdf?cod_prov=${encodeURIComponent(codProv)}`, '_blank');
        } else {
            closeAbonosModal();
            openRetencionIslrFromMain(codProv, numeroD);
        }
    });

    // Helper for NC / ND visualization
    window.visualizeAbono = (tipoAbono) => {
        if (!window.currentCxpStatus || !window.currentCxpStatus.HistorialAbonos) return;
        const ab = window.currentCxpStatus.HistorialAbonos.find(a => a.TipoAbono === tipoAbono);
        if (!ab) {
            showToast('Documento no encontrado', 'error');
            return;
        }
        
        let m = document.getElementById('visualizeDocModal');
        if (!m) {
            m = document.createElement('div');
            m.id = 'visualizeDocModal';
            m.className = 'modal-backdrop';
            m.innerHTML = `
                <div class="modal-card" style="max-width: 500px;">
                    <div class="modal-header">
                        <h2 id="visModalTitle" style="font-size: 1.25rem; font-weight:600; display:flex; align-items:center;"></h2>
                        <button class="btn-icon" onclick="forceHideModal(document.getElementById('visualizeDocModal'))">&times;</button>
                    </div>
                    <div class="modal-body" style="font-size: 0.95rem; line-height: 1.8; color: var(--text-primary);">
                        <div style="background:var(--bg-body); border-radius:8px; padding: 1.2rem; border: 1px solid var(--border-color);" id="visModalBody"></div>
                    </div>
                    <div class="modal-actions">
                        <button class="btn-secondary" onclick="forceHideModal(document.getElementById('visualizeDocModal'))">Cerrar Visualización</button>
                    </div>
                </div>
            `;
            document.body.appendChild(m);
        }
        
        let titleHtml = tipoAbono;
        if (tipoAbono === 'NOTA_CREDITO') titleHtml = '<i data-lucide="file-minus" style="color:var(--primary); margin-right:8px;"></i> Nota de Crédito Registrada';
        if (tipoAbono === 'NOTA_DEBITO') titleHtml = '<i data-lucide="file-plus" style="color:var(--danger); margin-right:8px;"></i> Nota de Débito Registrada';
        
        document.getElementById('visModalTitle').innerHTML = titleHtml;
        document.getElementById('visModalBody').innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;"><strong>Referencia/Nro:</strong> <span>${ab.Referencia || ab.DescripcionAjuste || 'S/N'}</span></div>
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;"><strong>Fecha Registro:</strong> <span>${formatDate(ab.FechaAbono)}</span></div>
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;"><strong>Monto Local (Bs):</strong> <span style="font-weight:600;">${formatBs(ab.MontoBsAbonado)}</span></div>
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;"><strong>Monto Ref ($):</strong> <span>${usdFormatter(ab.MontoUsdAbonado)}</span></div>
            ${ab.Observaciones ? `<div style="margin-top:16px; border-top:1px solid var(--border-color); padding-top:12px;"><strong>Observaciones:</strong><p style="margin-top:6px; color:var(--text-secondary);">${ab.Observaciones}</p></div>` : ''}
        `;
        
        forceShowModal(m);
        if(window.lucide) window.lucide.createIcons();
    };

    document.getElementById('abBtnNC')?.addEventListener('click', () => {
        const codProv = abCodProv.value;
        const numeroD = abNumeroD.value;
        const btn = document.getElementById('abBtnNC');
        if (btn && btn.dataset.yaCreada === "true") {
            visualizeAbono('NOTA_CREDITO');
            return;
        }
        // Do not close so user stays on the modal context
        // closeAbonosModal();
        let excess = 0;
        const entered = parseFloat(document.getElementById('abMontoBs').value);
        const required = window.lastCalculatedPaymentBs || 0;
        if (!isNaN(entered) && required > 0) {
            excess = Math.abs(entered - required);
        } else {
            excess = required > 0 ? required : 0;
        }
        const selectedTasa = parseFloat(document.getElementById('abTasa')?.value) || window.currentTasaBCV;
        openNCFromMain(codProv, numeroD, excess, selectedTasa);
    });

    document.getElementById('abBtnND')?.addEventListener('click', () => {
        const codProv = abCodProv.value;
        const numeroD = abNumeroD.value;
        const btn = document.getElementById('abBtnND');
        if (btn && btn.dataset.yaCreada === "true") {
            visualizeAbono('NOTA_DEBITO');
            return;
        }
        closeAbonosModal();
        if (window.currentNdDiff > 0) {
            document.getElementById('regNdInputNumero').value = '';
            document.getElementById('regNdInputControl').value = '';
            
            window.onTheFlyND = [{
                CodProv: codProv,
                NumeroD: numeroD,
                _estimatedReten: window.currentNdDiff
            }];
            
            const listContainer = document.getElementById('regNdFacturasContainer');
            if (listContainer) {
                listContainer.innerHTML = window.onTheFlyND.map((s, idx) => `
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">
                        <div>
                            <span style="font-size: 0.85rem; color: var(--text-secondary);">Factura:</span>
                            <strong style="display: block;">${s.NumeroD}</strong>
                        </div>
                        <div>
                            <span style="font-size: 0.85rem; color: var(--text-secondary);">V. Editable (Bs):</span>
                            <input type="number" id="retenInput_${idx}" class="form-control" step="0.01" value="${s._estimatedReten.toFixed(2)}" required>
                        </div>
                    </div>
                `).join('');
            }
            document.getElementById('registerDebitNoteModal').classList.add('active');
        } else {
             openNDFromMain(codProv, numeroD);
        }
    });

    document.getElementById('btnDynamicInvoiceStatus')?.addEventListener('click', () => {
        try {
            console.log('Botón Resumen Cálculo presionado');
            if (!currentCxpStatus) {
                showToast('Calculadora no disponible. Faltan datos financieros de la factura.', 'error');
                console.warn("Calculadora clickeada pero currentCxpStatus es null. Asegúrese de que los datos de la factura hayan cargado.");
                return;
            }
            const d = currentCxpStatus;
            const tasaDia = parseFloat(abTasa.value) || 0;
            if (!tasaDia) {
                showToast('Por favor espere a que cargue la Tasa BCV.', 'warning');
                return;
            }

            let pctDescuento = 0;
            const abProntoPago = document.getElementById('abProntoPago');
            const abTipoDescuento = document.getElementById('abTipoDescuento');
            if (abProntoPago && abProntoPago.checked && abTipoDescuento) {
                pctDescuento = parseFloat(abTipoDescuento.value) || 0;
            }

            const selIslrModal = document.getElementById('abConceptoISLR');
            const islrRateModal = parseFloat(selIslrModal?.value) || 0;
            const aplicaIndex = abAplicaIndex?.checked || false;

            const abDescBaseAplica = document.getElementById('abDescBaseAplica');
            let descBasePct = 0;
            if (abDescBaseAplica?.checked && Number(d.DescuentoBase_Pct) > 0) {
                descBasePct = Number(d.DescuentoBase_Pct);
            }
            const deduceIvaBase = document.getElementById('abDescBaseDeduceIVA')?.checked ?? true;
            const deduceIvaPP = document.getElementById('abPPDeduceIVA')?.checked ?? true;

            const fin = calculateInvoiceFinancials(d, {
                tasaDia: tasaDia,
                aplicaIndex: aplicaIndex,
                aplicaIndexIva: document.getElementById('abIndexaIVA')?.checked ?? true,
                pctDesc: pctDescuento,
                descBasePct: descBasePct,
                islrRate: islrRateModal,
                deduceIvaBase: deduceIvaBase,
                deduceIvaPP: deduceIvaPP
            });

            if (pctDescuento > 0 || descBasePct > 0) {
                const dynDescuentoBox = document.getElementById('dynDescuentoBox');
                const dynDescuentoBoxBs = document.getElementById('dynDescuentoBoxBs');
                if (dynDescuentoBox && dynDescuentoBoxBs) {
                    if (pctDescuento > 0) {
                        dynDescuentoBox.style.display = 'flex';
                        dynDescuentoBoxBs.style.display = 'flex';
                        const dynPctDesc = document.getElementById('dynPctDesc');
                        const dynPctDescBs = document.getElementById('dynPctDescBs');
                        if (dynPctDesc) dynPctDesc.textContent = pctDescuento;
                        if (dynPctDescBs) dynPctDescBs.textContent = pctDescuento;
                        const dynMontoDescUsd = document.getElementById('dynMontoDescUsd');
                        const dynMontoDescBs = document.getElementById('dynMontoDescBs');
                        if (dynMontoDescUsd) dynMontoDescUsd.textContent = '-' + usdFormatter(fin.descPPUsdMonto);
                        if (dynMontoDescBs) dynMontoDescBs.textContent = '-' + formatBs(fin.descPPUsdMonto * fin.currentTasa);
                    } else {
                        dynDescuentoBox.style.display = 'none';
                        dynDescuentoBoxBs.style.display = 'none';
                    }
                }
                const dynDescBaseBox = document.getElementById('dynDescBaseBox');
                const dynDescBaseBoxBs = document.getElementById('dynDescBaseBoxBs');
                if (dynDescBaseBox && dynDescBaseBoxBs) {
                    if (descBasePct > 0) {
                        dynDescBaseBox.style.display = 'flex';
                        dynDescBaseBoxBs.style.display = 'flex';
                        const dynPctDescBase = document.getElementById('dynPctDescBase');
                        const dynPctDescBaseBs = document.getElementById('dynPctDescBaseBs');
                        if (dynPctDescBase) dynPctDescBase.textContent = descBasePct;
                        if (dynPctDescBaseBs) dynPctDescBaseBs.textContent = descBasePct;
                        const dynMontoDescBaseUsd = document.getElementById('dynMontoDescBaseUsd');
                        const dynMontoDescBaseBs = document.getElementById('dynMontoDescBaseBs');
                        if (dynMontoDescBaseUsd) dynMontoDescBaseUsd.textContent = '-' + usdFormatter(fin.descBaseUsdMonto);
                        if (dynMontoDescBaseBs) dynMontoDescBaseBs.textContent = '-' + formatBs(fin.descBaseUsdMonto * fin.currentTasa);
                    } else {
                        dynDescBaseBox.style.display = 'none';
                        dynDescBaseBoxBs.style.display = 'none';
                    }
                }
            } else {
                const dynDescuentoBox = document.getElementById('dynDescuentoBox');
                if (dynDescuentoBox) dynDescuentoBox.style.display = 'none';
                const dynDescBaseBox = document.getElementById('dynDescBaseBox');
                if (dynDescBaseBox) dynDescBaseBox.style.display = 'none';
                
                const dynDescuentoBoxBs = document.getElementById('dynDescuentoBoxBs');
                if (dynDescuentoBoxBs) dynDescuentoBoxBs.style.display = 'none';
                const dynDescBaseBoxBs = document.getElementById('dynDescBaseBoxBs');
                if (dynDescBaseBoxBs) dynDescBaseBoxBs.style.display = 'none';
            }
            
            // UI Updates
            const exactUsdFormatter = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
            document.getElementById('dynTasaBcv').textContent = 'Bs ' + new Intl.NumberFormat('de-DE', { minimumFractionDigits: 4, maximumFractionDigits: 4 }).format(fin.currentTasa);
            
            // USD Column
            document.getElementById('dynSubtotalUsd').textContent = '$' + exactUsdFormatter.format(fin.subtotalUsd);
            document.getElementById('dynMtoTotalUsd').textContent = '$' + exactUsdFormatter.format(fin.origTotalUsd);
            
            // Bs Column
            document.getElementById('dynSubtotalBs').textContent = formatBs(fin.subtotalUsd * fin.currentTasa);
            document.getElementById('dynMtoTotalBs').textContent = formatBs(fin.origTotalUsd * fin.currentTasa);
            
            // Conditionally show Fletes/Desctos USD
            let desctoFletesHtml = '';
            if (fin.fletesUsd > 0) desctoFletesHtml += `<div style="display:flex;justify-content:space-between; margin-bottom: 2px;"><span>(+) Fletes:</span> <span>${usdFormatter(fin.fletesUsd)}</span></div>`;
            if (fin.d1Usd > 0) desctoFletesHtml += `<div style="display:flex;justify-content:space-between; margin-bottom: 2px;"><span>(-) Descto 1:</span> <span style="color:var(--danger);">${usdFormatter(fin.d1Usd)}</span></div>`;
            if (fin.d2Usd > 0) desctoFletesHtml += `<div style="display:flex;justify-content:space-between; margin-bottom: 2px;"><span>(-) Descto 2:</span> <span style="color:var(--danger);">${usdFormatter(fin.d2Usd)}</span></div>`;
            document.getElementById('dynDesctoFletesBox').innerHTML = desctoFletesHtml;

            // Conditionally show Fletes/Desctos Bs
            let desctoFletesHtmlBs = '';
            if (fin.fletesUsd > 0) desctoFletesHtmlBs += `<div style="display:flex;justify-content:space-between; margin-bottom: 2px;"><span>(+) Fletes:</span> <span>${formatBs(fin.fletesUsd * fin.currentTasa)}</span></div>`;
            if (fin.d1Usd > 0) desctoFletesHtmlBs += `<div style="display:flex;justify-content:space-between; margin-bottom: 2px;"><span>(-) Descto 1:</span> <span style="color:var(--danger);">${formatBs(fin.d1Usd * fin.currentTasa)}</span></div>`;
            if (fin.d2Usd > 0) desctoFletesHtmlBs += `<div style="display:flex;justify-content:space-between; margin-bottom: 2px;"><span>(-) Descto 2:</span> <span style="color:var(--danger);">${formatBs(fin.d2Usd * fin.currentTasa)}</span></div>`;
            if(document.getElementById('dynDesctoFletesBoxBs')) document.getElementById('dynDesctoFletesBoxBs').innerHTML = desctoFletesHtmlBs;

            // Base Imponible
            document.getElementById('dynBaseBs').textContent = formatBs(fin.baseBs);
            document.getElementById('dynBaseUsd').textContent = usdFormatter(fin.baseBs / fin.currentTasa);

            // IVA
            const ivaUsdVal = aplicaIndex ? fin.ivaUsd : roundFixed(fin.ivaBs / fin.currentTasa);
            document.getElementById('dynIvaBs').textContent = formatBs(fin.ivaBs);
            document.getElementById('dynIvaUsd').textContent = usdFormatter(ivaUsdVal);
            
            // IVA A Pagar
            if(document.getElementById('dynIvaAPagar')) document.getElementById('dynIvaAPagar').textContent = formatBs(fin.ivaAPagarBs);
            if(document.getElementById('dynIvaAPagarUsd')) document.getElementById('dynIvaAPagarUsd').textContent = usdFormatter(fin.ivaAPagarBs / fin.currentTasa);
            
            // IVA Retenido
            if(document.getElementById('dynIvaRetenido')) document.getElementById('dynIvaRetenido').textContent = formatBs(fin.retencionBs);
            if(document.getElementById('dynIvaRetenidoUsd')) document.getElementById('dynIvaRetenidoUsd').textContent = usdFormatter(fin.retencionBs / fin.currentTasa);
            
            // ISLR Retenido
            if(document.getElementById('dynRetenIslrBs')) document.getElementById('dynRetenIslrBs').textContent = '- ' + formatBs(fin.retenIslrBs);
            if(document.getElementById('dynRetenIslrUsd')) document.getElementById('dynRetenIslrUsd').textContent = '- ' + usdFormatter(fin.retenIslrBs / fin.currentTasa);

            // Exento
            document.getElementById('dynExentoBs').textContent = formatBs(fin.exentoBs);
            document.getElementById('dynExentoUsd').textContent = usdFormatter(fin.exentoBs / fin.currentTasa);
            
            // Final total payable
            document.getElementById('dynRestanteBs').textContent = formatBs(fin.finalBs);
            document.getElementById('dynRestanteUsd').textContent = usdFormatter(fin.finalBs / fin.currentTasa);

            const modalRecalculo = document.getElementById('dynamicInvoiceStatusModal');
            if (modalRecalculo) {
                document.body.appendChild(modalRecalculo);
                modalRecalculo.classList.add('active');
                modalRecalculo.style.cssText = "display: flex !important; z-index: 999999 !important; opacity: 1 !important; visibility: visible !important; pointer-events: auto !important; position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important;";
            } else {
                showToast("Error: No modal", "error");
            }
            lucide.createIcons();
        } catch (err) {
            console.error(err);
            showToast('Error: ' + err.message, 'error');
        }
    });

    const suggestDiscountTier = () => {
        if (!currentCxpStatus || !currentCxpStatus.Descuentos?.length) return;
        const d = currentCxpStatus;
        const abTipoDescuento = document.getElementById('abTipoDescuento');
        const abProntoPago = document.getElementById('abProntoPago');
        
        const dateInput = document.getElementById('abFechaPago');
        if (!dateInput || !abTipoDescuento) return;
        
        const pagoDateStr = getDateValue(dateInput) || new Date().toISOString().split('T')[0];
        const partsP = pagoDateStr.split('T')[0].split('-');
        const pagoDate = new Date(partsP[0], partsP[1] - 1, partsP[2]);

        const baseDateStr = d.BaseDiasCredito === 'EMISION' ? d.FechaE : (d.FechaI || d.FechaE);
        const partsB = baseDateStr.split('T')[0].split('-');
        const baseDate = new Date(partsB[0], partsB[1] - 1, partsB[2]);
        
        pagoDate.setHours(0,0,0,0);
        baseDate.setHours(0,0,0,0);
        
        const diffTime = pagoDate - baseDate;
        let diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
        
        // Si el usuario paga ANTES de que llegara la factura, el tiempo es negativo.
        // Si paga antes, obtiene el mayor beneficio (Día 0).
        if (diffDays < 0) diffDays = 0;
        
        // Find matching tier
        const match = d.Descuentos.find(tier => diffDays >= tier.DiasDesde && diffDays <= tier.DiasHasta);
        
        const abPPDeduceIVA = document.getElementById('abPPDeduceIVA');

        if (match) {
            abTipoDescuento.value = match.Porcentaje;
            if (abProntoPago) abProntoPago.checked = true;
            abTipoDescuento.disabled = false;
            if (abPPDeduceIVA) {
                abPPDeduceIVA.disabled = false;
                abPPDeduceIVA.checked = match.DeduceIVA !== false && match.DeduceIVA !== 0;
            }
        } else {
            abTipoDescuento.value = "0";
            if (abProntoPago) abProntoPago.checked = false;
            abTipoDescuento.disabled = true;
            if (abPPDeduceIVA) {
                abPPDeduceIVA.disabled = true;
                abPPDeduceIVA.checked = false;
            }
        }
    };

    const checkIndexationStatus = () => {
        if (!currentCxpStatus || !getDateValue(abFechaPago)) return;
        const pagoDateStr = getDateValue(abFechaPago);
        const partsP = pagoDateStr.split('T')[0].split('-');
        const pagoDate = new Date(partsP[0], partsP[1] - 1, partsP[2]);

        const partsNI = currentCxpStatus.FechaNI_Calculada.split('T')[0].split('-');
        const niDate = new Date(partsNI[0], partsNI[1] - 1, partsNI[2]);

        // Remove time portion for accurate day comparison
        pagoDate.setHours(0, 0, 0, 0);
        niDate.setHours(0, 0, 0, 0);

        // If payment date is STRICTLY greater than NI date, Indexation applies by default
        abAplicaIndex.checked = pagoDate > niDate;
        if(abIndexaIva) {
            abIndexaIva.checked = currentCxpStatus.IndexaIVA !== false;
        }
        
        // Auto-check descBase if applicable
        const abDescBaseAplica = document.getElementById('abDescBaseAplica');
        if (abDescBaseAplica && currentCxpStatus.DescuentoBase_Condicion === 'VENCIMIENTO') {
            const descBasePct = parseFloat(currentCxpStatus.DescuentoBase_Pct) || 0;
            if (descBasePct > 0) {
                const vDateStr = currentCxpStatus.FechaVSaint || currentCxpStatus.FechaV_Calculada;
                const partsV = vDateStr.split('T')[0].split('-');
                const vDate = new Date(partsV[0], partsV[1] - 1, partsV[2]);
                vDate.setHours(0,0,0,0);
                abDescBaseAplica.checked = (pagoDate <= vDate);
            }
        }

        // Dynamic Tier Selection (Pronto Pago)
        suggestDiscountTier();

        fillDefaultPaymentAmount(false); 
        calculateUsdAmount();
    };
    // Expose for external triggers (e.g., after saving provider conditions)
    window._abRecalcAfterProviderSave = async (codProv) => {
        if (!abonosModal.classList.contains('active')) return;
        if (!currentCxpStatus || String(currentCxpStatus.CodProv).trim() !== String(codProv).trim()) return;
        // Re-fetch provider conditions embedded in cxp-status
        const cod = abCodProv.value;
        const num = abNumeroD.value;
        const nroU = abonosModal.dataset.nrounico || null;
        if (!cod || !num) return;
        await fetchCxpStatus(cod, num, nroU);
        fillDefaultPaymentAmount(true);
        checkIndexationStatus();
        
        // Simular el click en la calculadora como pidió el usuario para refresque automático total
        document.getElementById('btnDynamicInvoiceStatus')?.click();
        
        showToast('✅ Montos recalculados con las nuevas condiciones del proveedor.', 'success');
    };

    const fillDefaultPaymentAmount = (forceUserToggle = false) => {
        if (!currentCxpStatus) return;
        
        const d = currentCxpStatus;
        const aplicaIndexacion = abAplicaIndex.checked;
        const tasaActual = parseFloat(abTasa.value) || 0;
        
        let pctDescuento = 0;
        const abProntoPago = document.getElementById('abProntoPago');
        const abTipoDescuento = document.getElementById('abTipoDescuento');
        if (abProntoPago && abProntoPago.checked && abTipoDescuento) {
            pctDescuento = parseFloat(abTipoDescuento.value) || 0;
        }

        let descBase = 0;
        const abDescBaseAplica = document.getElementById('abDescBaseAplica');
        if (abDescBaseAplica && abDescBaseAplica.checked) {
            descBase = parseFloat(d.DescuentoBase_Pct) || 0;
        }

        const selIslr = document.getElementById('abConceptoISLR');
        const islrRate = parseFloat(selIslr?.value) || 0;
        
        const deduceIvaBase = document.getElementById('abDescBaseDeduceIVA') ? document.getElementById('abDescBaseDeduceIVA').checked : true;
        const deduceIvaPP = document.getElementById('abPPDeduceIVA') ? document.getElementById('abPPDeduceIVA').checked : true;

        const fin = calculateInvoiceFinancials(d, {
            tasaDia: tasaActual,
            aplicaIndex: aplicaIndexacion,
            aplicaIndexIva: document.getElementById('abIndexaIVA')?.checked ?? true,
            pctDesc: pctDescuento,
            descBasePct: descBase,
            islrRate: islrRate,
            deduceIvaBase: deduceIvaBase,
            deduceIvaPP: deduceIvaPP
        });

        // Update new UI fields
        if(document.getElementById('abIvaAPagarBs')) document.getElementById('abIvaAPagarBs').value = formatBs(fin.ivaAPagarBs);
        if(document.getElementById('abIvaRetenidoBs')) document.getElementById('abIvaRetenidoBs').value = formatBs(fin.retencionBs);
        if(document.getElementById('abRetenIslrBs')) document.getElementById('abRetenIslrBs').value = formatBs(fin.retenIslrBs);

        // Re-calculate the visual "Saldo Restante USD" explicitly from the central math engine
        if (document.getElementById('abSaldoUsd')) {
            document.getElementById('abSaldoUsd').textContent = usdFormatter(fin.equivUsd);
        }

        let targetBs = fin.finalBs.toFixed(2);
        window.lastCalculatedPaymentBs = parseFloat(targetBs);

        const currentMonto = abMontoBs.value;
        const abExcedenteGroup = document.getElementById('abExcedenteGroup');
        const abExcedenteVal = document.getElementById('abExcedenteVal');
        
        let shouldFreezeInput = false;

        if (!forceUserToggle) {
            // No sobreescribir si el usuario ya escribió un monto manual (diferente al auto-llenado previo)
            if (currentMonto && parseFloat(currentMonto) > 0 && currentMonto !== lastAutoFilledBs) {
                shouldFreezeInput = true;
                abMontoBs.style.border = "2px solid var(--danger)";
                abMontoBs.style.boxShadow = "0 0 5px rgba(239, 68, 68, 0.5)";
                abMontoBs.title = "Monto editado manualmente (bloqueado para recálculo automático)";
                
                // Excedente calculation:
                const typedVal = parseFloat(currentMonto);
                const excd = typedVal - fin.finalBs;
                if (excd > 0.05) {
                    if (abExcedenteGroup) {
                        abExcedenteGroup.style.display = 'flex'; // Use flex to match original input-groups
                        if (abExcedenteVal) abExcedenteVal.textContent = bsFormatter(excd);
                    }
                } else {
                    if (abExcedenteGroup) abExcedenteGroup.style.display = 'none';
                }
            } else {
                if (abExcedenteGroup) abExcedenteGroup.style.display = 'none';
            }
        } else {
            if (abExcedenteGroup) abExcedenteGroup.style.display = 'none';
        }

        if (!shouldFreezeInput && targetBs) {
            abMontoBs.value = targetBs;
            lastAutoFilledBs = targetBs;
            abMontoBs.style.border = "";
            abMontoBs.style.boxShadow = "";
            abMontoBs.title = "";
            if (abExcedenteGroup) abExcedenteGroup.style.display = 'none';
        }

        updateActionBarState(d, fin);
    };

    const updateActionBarState = (cxp, fin) => {
        const btnRetIva  = document.getElementById('abBtnRetIva');
        const btnRetIslr = document.getElementById('abBtnRetIslr');
        const btnND      = document.getElementById('abBtnND');
        const btnNC      = document.getElementById('abBtnNC');

        const hasIva = (parseFloat(cxp.TGravable) || 0) > 0 && (parseFloat(cxp.MtoTax) || 0) > 0;
        const ivaYaRetenida = (cxp.HistorialAbonos || []).some(a => a.TipoAbono === 'RETENCION_IVA');
        
        if (btnRetIva) {
            btnRetIva.disabled = !hasIva && !ivaYaRetenida;
            btnRetIva.dataset.yaCreada = ivaYaRetenida;
            btnRetIva.title = (!hasIva && !ivaYaRetenida)
                ? 'Este documento no incluye IVA' 
                : ivaYaRetenida 
                    ? 'Visualizar Retención IVA' 
                    : 'Generar Retención IVA';
        }

        const islrYaRetenida = (cxp.HistorialAbonos || []).some(a => a.TipoAbono === 'RETENCION_ISLR');
        if (btnRetIslr) {
            btnRetIslr.disabled = false;
            btnRetIslr.dataset.yaCreada = islrYaRetenida;
            btnRetIslr.title = islrYaRetenida 
                ? 'Visualizar Retención ISLR' 
                : 'Generar Retención ISLR';
        }
        
        const tieneNC = (cxp.HistorialAbonos || []).some(a => a.TipoAbono === 'NOTA_CREDITO');
        if (btnNC) {
            btnNC.disabled = false;
            btnNC.dataset.yaCreada = tieneNC;
            btnNC.title = tieneNC ? "Visualizar Nota de Crédito" : "Generar Nota de Crédito";
        }

        const tieneND = (cxp.HistorialAbonos || []).some(a => a.TipoAbono === 'NOTA_DEBITO');
        if (btnND) {
            btnND.disabled = false;
            btnND.dataset.yaCreada = tieneND;
            const originalBsDebt = (Math.round(((fin.mtoTotalUsd - (parseFloat(cxp.TotalUsdAbonado) || 0)) * fin.historicalTasa) * 100) / 100);
            const indexationDiff = fin.saldoTargetBs - originalBsDebt;
            window.currentNdDiff = indexationDiff > 0 ? indexationDiff : 0; 
            
            if (tieneND) {
                btnND.title = "Visualizar Nota de Débito";
                btnND.style.boxShadow = 'none';
            } else if (indexationDiff > 0.01) {
               btnND.style.boxShadow = '0 0 8px rgba(239, 68, 68, 0.6)';
               btnND.title = `Indexación detectada: Bs ${indexationDiff.toFixed(2)}`;
            } else {
               btnND.style.boxShadow = 'none';
               btnND.title = 'Generar Nota de Débito';
            }
        }

        const submitBtn = document.querySelector('#abonoForm button[type="submit"]');
        if (fin.finalBs <= 0.01) {
            if (abMontoBs) abMontoBs.disabled = true;
            if (document.getElementById('abAplicaIndex')) document.getElementById('abAplicaIndex').disabled = true;
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.title = "Factura pagada en su totalidad";
            }
        } else {
            if (abMontoBs) abMontoBs.disabled = false;
            if (document.getElementById('abAplicaIndex')) document.getElementById('abAplicaIndex').disabled = false;
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.title = "";
            }
        }
    };

    const calculateUsdAmount = () => {
        const bs = parseFloat(abMontoBs.value) || 0;
        if (bs <= 0) {
            abMontoUsd.value = '';
            return;
        }

        if (!abAplicaIndex.checked && currentCxpStatus && currentCxpStatus.TasaEmision) {
            // Usa tasa original
            abMontoUsd.value = (bs / currentCxpStatus.TasaEmision).toFixed(2);
        } else {
            // Usa tasa del día
            const rate = parseFloat(abTasa.value) || 1;
            abMontoUsd.value = rate > 0 ? (bs / rate).toFixed(2) : '';
        }
    };

    // Event Listeners for Abono Form
    abFechaPago?.addEventListener('change', updateExchangeRate);
    abMontoBs?.addEventListener('input', () => {
        calculateUsdAmount();
        const excGrp = document.getElementById('abExcedenteGroup');
        const excVal = document.getElementById('abExcedenteVal');
        if (abMontoBs.value && abMontoBs.value !== lastAutoFilledBs) {
            abMontoBs.style.border = "2px solid var(--danger)";
            abMontoBs.style.boxShadow = "0 0 5px rgba(239, 68, 68, 0.5)";
            abMontoBs.title = "Monto editado manualmente (bloqueado para recálculo automático)";
            // Mostrar excedente si el monto ingresado supera el calculado
            const typedVal = parseFloat(abMontoBs.value) || 0;
            const refBs = window.lastCalculatedPaymentBs || parseFloat(lastAutoFilledBs) || 0;
            if (refBs > 0 && typedVal > refBs + 0.05) {
                const excd = Math.abs(typedVal - refBs); // abs para evitar negativos en UI si el redondeo falla
                if (excGrp) {
                    excGrp.style.display = 'flex';
                    if (excVal) excVal.textContent = `Bs.S ${bsFormatter(excd)}`;
                }
            } else {
                if (excGrp) excGrp.style.display = 'none';
            }
        } else {
            abMontoBs.style.border = "";
            abMontoBs.style.boxShadow = "";
            abMontoBs.title = "";
            if (excGrp) excGrp.style.display = 'none';
        }
    });
    abAplicaIndex?.addEventListener('change', () => {
        fillDefaultPaymentAmount(true);
        calculateUsdAmount();
    });
    
    document.getElementById('abIndexaIVA')?.addEventListener('change', (e) => {
        if (e.target.checked && !abAplicaIndex.checked) {
            e.target.checked = false;
        } else {
            fillDefaultPaymentAmount(true);
            calculateUsdAmount();
        }
    });

    document.getElementById('abDescBaseAplica')?.addEventListener('change', () => {
        fillDefaultPaymentAmount(true);
        calculateUsdAmount();
    });
    
    abAplicaIndex?.addEventListener('change', (e) => {
        const abIndexIva = document.getElementById('abIndexaIVA');
        if (!e.target.checked && abIndexIva) {
            abIndexIva.checked = false;
        }
    });
    
    const abProntoPago = document.getElementById('abProntoPago');
    const abTipoDescuento = document.getElementById('abTipoDescuento');
    abProntoPago?.addEventListener('change', () => {
        if (abTipoDescuento) {
            abTipoDescuento.disabled = !abProntoPago.checked;
            // UX enhancement: if they just checked it and it's at 0%, auto-select the first tier
            if (abProntoPago.checked && String(abTipoDescuento.value) === "0" && abTipoDescuento.options.length > 1) {
                abTipoDescuento.selectedIndex = 1;
            }
        }
        fillDefaultPaymentAmount(true);
        calculateUsdAmount();
    });
    abTipoDescuento?.addEventListener('change', () => {
        // Validation: If they pick a discount manually, ensure the checkbox stays checked
        if (abProntoPago && String(abTipoDescuento.value) !== "0") {
            abProntoPago.checked = true;
        }
        
        // Sync the DeduceIVA checkbox state when the dropdown changes
        const abPPDeduceIVA = document.getElementById('abPPDeduceIVA');
        if (abPPDeduceIVA) {
            const opt = abTipoDescuento.options[abTipoDescuento.selectedIndex];
            if (opt) abPPDeduceIVA.checked = opt.getAttribute('data-deduce-iva') === 'true';
        }
        
        fillDefaultPaymentAmount(true);
        calculateUsdAmount();
    });
    
    document.getElementById('abPPDeduceIVA')?.addEventListener('change', () => {
        fillDefaultPaymentAmount(true);
        calculateUsdAmount();
    });
    
    document.getElementById('abDescBaseDeduceIVA')?.addEventListener('change', () => {
        fillDefaultPaymentAmount(true);
        calculateUsdAmount();
    });
    document.getElementById('abConceptoISLR')?.addEventListener('change', () => {
        // Persist concept per invoice in localStorage
        const numD = document.getElementById('abNumeroD')?.value;
        if (numD) localStorage.setItem(`islr_${numD}`, document.getElementById('abConceptoISLR').value);
        fillDefaultPaymentAmount(true);
        calculateUsdAmount();
    });

    abonoForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!currentCxpStatus) return;

        const formData = new FormData();
        const abNroUnicoValue = abonosModal.dataset.nrounico;
        if (abNroUnicoValue) formData.append('NroUnico', abNroUnicoValue);
        formData.append('NumeroD', abNumeroD.value);
        formData.append('CodProv', abCodProv.value);
        formData.append('FechaAbono', getDateValue(abFechaPago));
        formData.append('MontoBsAbonado', parseFloat(abMontoBs.value));
        formData.append('TasaCambioDiaAbono', abAplicaIndex.checked ? (parseFloat(abTasa.value) || 0) : (currentCxpStatus.TasaEmision || 0));
        formData.append('MontoUsdAbonado', parseFloat(abMontoUsd.value));
        formData.append('AplicaIndexacion', abAplicaIndex.checked);
        formData.append('Referencia', abReferencia.value);
        
        const notificar = document.getElementById('abNotificarCorreo')?.checked || false;
        formData.append('NotificarCorreo', notificar);

        // --- Lógica: registrar descuento Pronto Pago como memo contable (AfectaSaldo=0)
        const pctDescuentoFinal = (document.getElementById('abProntoPago')?.checked && document.getElementById('abTipoDescuento'))
            ? (parseFloat(document.getElementById('abTipoDescuento').value) || 0)
            : 0;
        let descBase = 0;
        const abDescBaseAplicaForm = document.getElementById('abDescBaseAplica');
        if (abDescBaseAplicaForm && abDescBaseAplicaForm.checked) {
            descBase = parseFloat(currentCxpStatus.DescuentoBase_Pct) || 0;
        }

        if (pctDescuentoFinal > 0 || descBase > 0) {
            const deduceIvaBase = document.getElementById('abDescBaseDeduceIVA') ? document.getElementById('abDescBaseDeduceIVA').checked : true;
            const deduceIvaPP = document.getElementById('abPPDeduceIVA') ? document.getElementById('abPPDeduceIVA').checked : true;

            const finParamsBase = {
                tasaDia: abAplicaIndex.checked ? (parseFloat(abTasa.value) || 0) : (currentCxpStatus.TasaEmision || 0),
                aplicaIndex: abAplicaIndex.checked,
                aplicaIndexIva: document.getElementById('abIndexaIVA')?.checked ?? true,
                islrRate: parseFloat(document.getElementById('abConceptoISLR')?.value) || 0,
                deduceIvaBase: deduceIvaBase,
                deduceIvaPP: deduceIvaPP
            };
            
            const finSinDesc = calculateInvoiceFinancials(currentCxpStatus, { ...finParamsBase, pctDesc: 0, descBasePct: 0 });
            const finSoloBase = calculateInvoiceFinancials(currentCxpStatus, { ...finParamsBase, pctDesc: 0, descBasePct: descBase });
            const finConAmbos = calculateInvoiceFinancials(currentCxpStatus, { ...finParamsBase, pctDesc: pctDescuentoFinal, descBasePct: descBase });
            
            const montoDescBase = +(finSinDesc.finalBs - finSoloBase.finalBs).toFixed(2);
            const montoDescPP = +(finSoloBase.finalBs - finConAmbos.finalBs).toFixed(2);
            
            if (montoDescBase > 0) {
                formData.append('MontoDescuentoBaseBs', montoDescBase.toFixed(2));
            }
            if (montoDescPP > 0) {
                formData.append('MontoDescuentoBs', montoDescPP.toFixed(2));
                const selMotivo = document.getElementById('abMotivoAjuste');
                const ppOpt = Array.from(selMotivo?.options || []).find(o => o.text.includes('100') || o.text.toLowerCase().includes('pronto pago'));
                if (ppOpt) formData.append('MotivoDescuentoID', ppOpt.value);
            }
        }

        // --- Lógica de Ajuste por Remanente ---
        const checkAjuste = document.getElementById('abPermitirAjuste');
        if (checkAjuste && checkAjuste.checked) {
            
            const motiID = document.getElementById('abMotivoAjuste')?.value;
            const motiText = motiID ? document.getElementById('abMotivoAjuste').options[document.getElementById('abMotivoAjuste').selectedIndex].text : '';
            
            if (!motiID) {
                showToast('⚠️ Seleccione el Motivo del Ajuste Contable antes de proceder.', 'warning');
                return;
            }

            let pctDescuento = 0;
            if (document.getElementById('abProntoPago')?.checked && document.getElementById('abTipoDescuento')) {
                pctDescuento = parseFloat(document.getElementById('abTipoDescuento').value) || 0;
            }
            
            const deduceIvaBase = document.getElementById('abDescBaseDeduceIVA') ? document.getElementById('abDescBaseDeduceIVA').checked : true;
            const deduceIvaPP = document.getElementById('abPPDeduceIVA') ? document.getElementById('abPPDeduceIVA').checked : true;

            const fin = calculateInvoiceFinancials(currentCxpStatus, {
                tasaDia: abAplicaIndex.checked ? (parseFloat(abTasa.value) || 0) : (currentCxpStatus.TasaEmision || 0),
                aplicaIndex: abAplicaIndex.checked,
                aplicaIndexIva: document.getElementById('abIndexaIVA')?.checked ?? true,
                pctDesc: pctDescuento,
                descBasePct: descBase,
                islrRate: parseFloat(document.getElementById('abConceptoISLR')?.value) || 0,
                deduceIvaBase: deduceIvaBase,
                deduceIvaPP: deduceIvaPP
            });
            let pagoReal = parseFloat(abMontoBs.value) || 0;
            const deudaAcumuladaBs = fin.finalBs; // Lo que realmente se exige hoy en día
            let diferencia = (deudaAcumuladaBs - pagoReal);
            
            // Universal Auto-Split overpayment shield: Si pagan más de la deuda ERP, exigimos split para proteger Saint
            let deudaOriginalBs = currentCxpStatus.Saldo || 0;
            if (deudaOriginalBs <= 0) {
                showToast('⚠️ La factura no presenta saldo pendiente. No se pueden registrar más pagos.', 'warning');
                return;
            }
            
            if (pagoReal > deudaOriginalBs && deudaOriginalBs > 0) {
                 const tasaAplicada = abAplicaIndex.checked ? (parseFloat(abTasa.value) || 1) : (currentCxpStatus.TasaEmision || 1);
                 const overpay = pagoReal - deudaOriginalBs;
                 pagoReal = deudaOriginalBs; // Cap what goes into ERP
                 const usdProrrateado = pagoReal / tasaAplicada;
                 
                 formData.set('MontoBsAbonado', pagoReal.toFixed(2));
                 formData.set('MontoUsdAbonado', usdProrrateado.toFixed(2));
                 diferencia = overpay; // The excess goes to Ajuste local table
            } else {
                 diferencia = (deudaAcumuladaBs - pagoReal); // Normal discrepancy 
            }
            
            if (diferencia > 0) {
                const umbral = deudaAcumuladaBs * 0.10;
                if (diferencia > umbral) {
                    const r = confirm(`El ajuste contable a generar supera el 10% de la deuda exigida. ¿Desea proceder con este Ajuste de exceso?`);
                    if (!r) return;
                }
                formData.append('MontoAjusteBs', diferencia.toFixed(2));
                formData.append('MotivoAjusteID', motiID);
            }
        }

        const fileInput = document.getElementById('abComprobante');
        if (fileInput && fileInput.files.length > 0) {
            Array.from(fileInput.files).forEach(f => formData.append('archivos', f));
        }

        const btn = abonoForm.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<div class="loader" style="width: 16px; height: 16px; border-width: 2px;"></div> Procesando...';
        btn.disabled = true;

        try {
            const res = await fetch('/api/procurement/abonos', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) throw new Error('Error al procesar pago');

            const resJson = await res.json();
            // Toast if email could not be sent (offline or no email)
            if (notificar && resJson.email_sent === false) {
                showToast('⚠️ Pago registrado. No se pudo enviar el correo (sin conexión o sin email del proveedor).', 'warning');
            } else if (notificar && resJson.email_sent !== false) {
                showToast('✅ Pago registrado y correo enviado exitosamente.', 'success');
            } else {
                showToast('✅ Abono registrado exitosamente.', 'success');
            }

            // Reload status to reflect new history and balance
            await fetchCxpStatus(abCodProv.value, abNumeroD.value);
            abMontoBs.value = '';
            abReferencia.value = '';
            calculateUsdAmount();

            if (typeof fetchData === 'function') fetchData();

        } catch (error) {
            console.error(error);
            alert('Error al registrar el abono.');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    // --- Re-enviar correo para facturas ya pagadas ---
    const btnResendEmail = document.getElementById('btnResendEmail');
    const abNotificarCorreo = document.getElementById('abNotificarCorreo');

    abNotificarCorreo?.addEventListener('change', () => {
        if (btnResendEmail) btnResendEmail.disabled = !abNotificarCorreo.checked;
    });

    btnResendEmail?.addEventListener('click', async () => {
        if (!currentCxpStatus) return;
        btnResendEmail.disabled = true;
        btnResendEmail.innerHTML = '<div class="loader" style="width:14px;height:14px;border-width:2px;"></div> Enviando...';
        try {
            const fd = new FormData();
            fd.append('NumeroD', abNumeroD.value);
            fd.append('CodProv', abCodProv.value);
            const fileInput = document.getElementById('abComprobante');
            if (fileInput && fileInput.files.length > 0) {
                Array.from(fileInput.files).forEach(f => fd.append('archivos', f));
            }
            const res = await fetch('/api/procurement/send-email', { method: 'POST', body: fd });
            const json = await res.json();
            if (json.email_sent !== false) {
                showToast('✅ Correo re-enviado exitosamente.', 'success');
            } else {
                showToast(`⚠️ ${json.message || 'No se pudo enviar el correo.'}`, 'warning');
            }
        } catch (err) {
            console.error(err);
            showToast('❌ Error al intentar re-enviar el correo.', 'error');
        } finally {
            btnResendEmail.disabled = false;
            btnResendEmail.innerHTML = '<i data-lucide="send"></i> Re-enviar correo';
            lucide.createIcons();
        }
    });
    // --------------------------------------------------

    // Carga Inicial
    setTimeout(() => {
        if (meshp && aniohp) fetchSavedBatch();
    }, 500);

    // Init Table Sorts
    window.setupSortableTable('cxpTable', 'currentData', 'renderTable', 'sortable', 'FechaE');
    window.setupSortableTable('expenseTemplatesTable', 'expenseTemplatesData', 'renderExpenseTemplates', 'sortable', 'descripcion');
    window.setupSortableTable('expenseBatchTableFijos', 'currentBatchData', 'renderBatchTable', 'sortable', 'descripcion');
    window.setupSortableTable('expenseBatchTableAdhoc', 'currentBatchData', 'renderBatchTable', 'sortable', 'descripcion');
    window.setupSortableTable('expenseSavedBatchTable', 'expenseSavedBatchData', 'renderSavedBatchTable', 'sortable', 'fecha_proyectada');

    // Listeners
    document.getElementById('expenseSavedBatchSearch')?.addEventListener('input', renderSavedBatchTable);

    // Provider list listeners
    providerSearchInput?.addEventListener('input', renderProvidersTable);
    providerActivoCheck?.addEventListener('change', renderProvidersTable);
    document.getElementById('refreshProvidersBtn')?.addEventListener('click', fetchProviders);

    // Initialize date inputs for DD/MM/YYYY display
    [
        filterDate, filterDateHasta, cashflowDateDesde, cashflowDateHasta,
        paramFechaCero, fcDateDesde, fcDateHasta, fsDateDesde, fsDateHasta,
        document.getElementById('eventFecha'),
        document.getElementById('planFecha'),
        document.getElementById('comprasDesde'),
        document.getElementById('comprasHasta')
    ].forEach(el => setupDateInput(el));

    loadCashflowParams();

    // --- Toast Utility ---
    window.showToast = (message, type = 'success', duration = 4500) => {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            document.body.appendChild(container);
        }
        // Force critical styles every time to prevent background hiding
        container.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;display:flex;flex-direction:column;gap:0.5rem;z-index:1000001 !important;pointer-events:none;';
        
        const colors = { 
            success: '#22c55e', 
            warning: '#f59e0b', 
            error: '#ef4444',
            info: '#3b82f6',
            danger: '#ef4444'
        };
        const toast = document.createElement('div');
        toast.style.cssText = `background:#1e293b;border:1px solid ${colors[type]||colors.success};color:#f8fafc;padding:0.75rem 1.2rem;border-radius:8px;font-size:0.9rem;box-shadow:0 10px 25px rgba(0,0,0,0.5);max-width:400px;word-wrap:break-word;pointer-events:auto;transition:all 0.3s ease;`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => { 
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(20px)';
            setTimeout(() => { toast.remove(); }, 300);
        }, duration);
    };

    // --- Helper for forcefully rendering modals ---
    window.forceShowModal = (modalElement) => {
        if (!modalElement) return;
        document.body.appendChild(modalElement);
        modalElement.classList.add('active');
        modalElement.dataset.originalCssText = modalElement.style.cssText;
        modalElement.style.cssText = "display: flex !important; z-index: 999999 !important; opacity: 1 !important; visibility: visible !important; pointer-events: auto !important; position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important;";
    };

    window.forceHideModal = (modalElement) => {
        if (!modalElement) return;
        modalElement.classList.remove('active');
        if (typeof modalElement.dataset.originalCssText !== 'undefined') {
            modalElement.style.cssText = modalElement.dataset.originalCssText;
        } else {
            modalElement.style.cssText = "z-index: 10020;";
        }
    };

    // --- Invoice Edit Modal ---
    const invoiceEditModal = document.getElementById('invoiceEditModal');
    const invoiceEditForm = document.getElementById('invoiceEditForm');

    window.closeInvoiceEditModal = () => {
        forceHideModal(invoiceEditModal);
    };

    window.abrirModalEdicion = (item) => {
        if (!item) return;

        document.getElementById('ieNumeroD').value = item.NumeroD || '';
        document.getElementById('ieCodProv').value = item.CodProv || '';
        document.getElementById('ieFechaE').value = (item.FechaE || '').split('T')[0];
        document.getElementById('ieFechaI').value = (item.FechaI || '').split('T')[0];
        document.getElementById('ieFechaV').value = (item.FechaV || '').split('T')[0];
        // Notas10: '1' means indexed, anything else means not
        const n10 = item.Notas10;
        document.getElementById('ieNotas10').value = (n10 !== null && n10 !== undefined && String(n10).trim() === '1') ? '1' : '';
        document.getElementById('ieMontoFacturaBS').value = item.Monto || 0;
        document.getElementById('ieTGravable').value = item.TGravable || 0;
        document.getElementById('ieIVA').value = item.MtoTax || 0;
        
        // Phase 8 additional fields
        document.getElementById('ieFactor').value = item.Factor || 0;
        document.getElementById('ieMontoMEx').value = item.MontoMEx || 0;
        document.getElementById('ieTotalPrd').value = item.TotalPrd || 0;
        document.getElementById('ieFletes').value = item.Fletes || 0;
        document.getElementById('ieDescto1').value = item.Descto1 || 0;
        document.getElementById('ieDescto2').value = item.Descto2 || 0;
        document.getElementById('ieContado').value = item.Contado || 0;
        document.getElementById('ieCredito').value = item.Credito || 0;

        document.getElementById('invoiceEditSubtitle').textContent = `Factura: ${item.NumeroD} | ${item.Descrip || ''}`;
        
        // Auto-fetch correct rate for Emission Date on open (requested by user)
        const emissionDate = (item.FechaE || '').split('T')[0];
        if (emissionDate) {
            fetch(`/api/exchange-rate?fecha=${encodeURIComponent(emissionDate)}`)
                .then(res => res.ok ? res.json() : null)
                .then(json => {
                    if (json && json.rate) {
                        document.getElementById('ieFactor').value = json.rate.toFixed(4);
                        recalculateInvoice('Factor');
                    }
                })
                .catch(err => console.error('Error auto-fetching rate on open:', err));
        }

        // Save cod_prov in the form for the PATCH request
        invoiceEditForm.dataset.codProv = item.CodProv || '';

        forceShowModal(invoiceEditModal);
        lucide.createIcons();
    };

    // --- Interactive Recalculation Logic (Phase 8) ---
    const ieFactor = document.getElementById('ieFactor');
    const ieMontoMEx = document.getElementById('ieMontoMEx');
    const ieMontoFacturaBS = document.getElementById('ieMontoFacturaBS');
    const ieContado = document.getElementById('ieContado');
    const ieTGravable = document.getElementById('ieTGravable');
    const ieIVA = document.getElementById('ieIVA');

    const recalculateInvoice = (source) => {
        let factor = parseFloat(ieFactor.value) || 0;
        let montoMEx = parseFloat(ieMontoMEx.value) || 0;
        let mtoBs = parseFloat(ieMontoFacturaBS.value) || 0;
        let contado = parseFloat(ieContado.value) || 0;
        let credito = parseFloat(ieCredito.value) || 0;

        if (source === 'Factor' && factor > 0) {
            ieMontoMEx.value = (mtoBs / factor).toFixed(4);
        } else if (source === 'MontoMEx' && factor > 0) {
            ieMontoFacturaBS.value = (montoMEx * factor).toFixed(2);
            ieCredito.value = ((montoMEx * factor) - contado).toFixed(2);
        } else if (source === 'MontoFacturaBS') {
            if (factor > 0) ieMontoMEx.value = (mtoBs / factor).toFixed(4);
            ieCredito.value = (mtoBs - contado).toFixed(2); 
        } else if (source === 'Contado') {
            ieCredito.value = (mtoBs - contado).toFixed(2);
        } else if (source === 'Credito') {
            ieContado.value = (mtoBs - credito).toFixed(2);
        } else if (source === 'TGravable') {
            const base = parseFloat(ieTGravable.value) || 0;
            ieIVA.value = (base * 0.16).toFixed(2);
        }
    };

    ieTGravable?.addEventListener('input', () => recalculateInvoice('TGravable'));

    ieFactor?.addEventListener('input', () => recalculateInvoice('Factor'));
    ieMontoMEx?.addEventListener('input', () => recalculateInvoice('MontoMEx'));
    ieMontoFacturaBS?.addEventListener('input', () => recalculateInvoice('MontoFacturaBS'));
    ieContado?.addEventListener('input', () => recalculateInvoice('Contado'));
    ieCredito?.addEventListener('input', () => recalculateInvoice('Credito'));

    document.getElementById('ieFechaE')?.addEventListener('change', async (e) => {
        const fecha = e.target.value;
        if (!fecha) return;
        try {
            const res = await fetch(`/api/exchange-rate?fecha=${encodeURIComponent(fecha)}`);
            if (res.ok) {
                const json = await res.json();
                if (json.rate) {
                    ieFactor.value = json.rate.toFixed(4);
                    recalculateInvoice('Factor'); 
                }
            }
        } catch(err) { console.error('Error fetching rate for date:', err); }
    });

    invoiceEditForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const numeroD = document.getElementById('ieNumeroD').value;
        const codProv = document.getElementById('ieCodProv').value;
        if (!numeroD) return;

        const notas10Val = document.getElementById('ieNotas10')?.value;
        const payload = {
            FechaE: document.getElementById('ieFechaE').value || null,
            FechaI: document.getElementById('ieFechaI').value || null,
            FechaV: document.getElementById('ieFechaV').value || null,
            Notas10: document.getElementById('ieNotas10').value || "",
            MontoFacturaBS: parseFloat(document.getElementById('ieMontoFacturaBS').value) || 0,
            TGravable: parseFloat(document.getElementById('ieTGravable').value) || 0,
            IVA: parseFloat(document.getElementById('ieIVA').value) || 0,
            Factor: parseFloat(document.getElementById('ieFactor').value) || 0,
            MontoMEx: parseFloat(document.getElementById('ieMontoMEx').value) || 0,
            TotalPrd: parseFloat(document.getElementById('ieTotalPrd').value) || 0,
            Fletes: parseFloat(document.getElementById('ieFletes').value) || 0,
            Descto1: parseFloat(document.getElementById('ieDescto1').value) || 0,
            Descto2: parseFloat(document.getElementById('ieDescto2').value) || 0,
            Contado: parseFloat(document.getElementById('ieContado').value) || 0,
            Credito: parseFloat(document.getElementById('ieCredito').value) || 0,
            CodProv: invoiceEditForm.dataset.codProv || ""
        };
        // Only include Notas10 if user explicitly chose a value
        if (notas10Val !== '' && notas10Val !== undefined && notas10Val !== null) {
            payload.Notas10 = notas10Val;
        }

        const saveBtn = invoiceEditForm.querySelector('button[type="submit"]');
        const origText = saveBtn.innerHTML;
        saveBtn.innerHTML = '<div class="loader" style="width:14px;height:14px;border-width:2px;"></div> Guardando...';
        saveBtn.disabled = true;

        try {
            const res = await fetch(`/api/cuentas-por-pagar/${encodeURIComponent(numeroD)}?cod_prov=${encodeURIComponent(codProv)}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!res.ok) throw new Error('Error al guardar cambios');
            showToast('✅ Factura actualizada correctamente.', 'success');
            window.closeInvoiceEditModal();

            // If the edit was triggered from the PM modal: re-fetch + recalc that row
            const fromPm = invoiceEditForm.dataset.fromPm === 'true';
            const pmRowKey = invoiceEditForm.dataset.pmRowKey || '';
            const fromAb = invoiceEditForm.dataset.fromAb === 'true';

            invoiceEditForm.dataset.fromPm = 'false';
            invoiceEditForm.dataset.pmRowKey = '';
            invoiceEditForm.dataset.fromAb = 'false';

            if (fromAb) {
                await fetchData();
                if (typeof window._abRecalcAfterProviderSave === 'function') {
                    const codProv = invoiceEditForm.dataset.codProv || null;
                    if (codProv) {
                        try {
                            await window._abRecalcAfterProviderSave(codProv);
                        } catch(e) { console.warn('AB recalc failed', e); }
                    }
                }
            } else if (fromPm && pmRowKey) {
                await fetchData();
                const pmModal = document.getElementById('pagoMultipleModal');
                if (pmModal && pmModal.classList.contains('active')) {
                    const tbody = document.getElementById('pmInvoicesTable');
                    const pmRow = tbody ? tbody.querySelector(`tr[data-rowkey="${pmRowKey}"]`) : null;
                    if (pmRow) {
                        try {
                            const refreshedItem = (window._pmCurrentItems || []).find(i => window.getItemKey(i) === pmRowKey)
                                || (window.currentData || []).find(i => window.getItemKey(i) === pmRowKey);
                            if (refreshedItem) {
                                if (window._pmCurrentItems) {
                                    const idx = window._pmCurrentItems.findIndex(i => window.getItemKey(i) === pmRowKey);
                                    const freshItem = (window.currentData || []).find(i => window.getItemKey(i) === pmRowKey);
                                    if (idx !== -1 && freshItem) window._pmCurrentItems[idx] = freshItem;
                                }
                                if (typeof window._pmRecalcAfterProviderSave === 'function') {
                                    await window._pmRecalcAfterProviderSave(refreshedItem.CodProv);
                                }
                            }
                        } catch(pmErr) { console.warn('PM row refresh after invoice edit failed:', pmErr); }
                    }
                }
            } else {
                await fetchData();
            }
        } catch (err) {
            console.error(err);
            showToast('❌ Error al guardar cambios en la factura.', 'error');
        } finally {
            saveBtn.innerHTML = origText;
            saveBtn.disabled = false;
            lucide.createIcons();
        }
    });

    // ==========================================
    // PAGO MÚLTIPLE MODULE
    // ==========================================
    {
        const pmModal = document.getElementById('pagoMultipleModal');
        const pmForm  = document.getElementById('pagoMultipleForm');
        let pmItems      = [];
        let pmCxpStatuses = {};       // keyed by NumeroD
        window.pmCxpStatuses = pmCxpStatuses; // Accessible globally for retention UI updates
        let lastProcessedPagos = [];  // saved after successful processing for re-send

        document.getElementById('pmIndexadoMaster')?.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            const tbody = document.getElementById('pmInvoicesTable');
            
            if (!isChecked) {
                const ivaMaster = document.getElementById('pmIndexaIVAMaster');
                if (ivaMaster) ivaMaster.checked = false;
            }

            if (tbody) {
                tbody.querySelectorAll('tr').forEach(row => {
                    const cb = row.querySelector('.pm-indexado');
                    if (cb && !cb.disabled && cb.checked !== isChecked) {
                        cb.checked = isChecked;
                        if (!isChecked) {
                            const ivaCb = row.querySelector('.pm-indexado-iva');
                            if (ivaCb) ivaCb.checked = false;
                        }
                        pmCalcRow(row);
                    }
                });
                pmRecalcTotals();
            }
        });

        document.getElementById('pmIndexaIVAMaster')?.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            
            const masterBase = document.getElementById('pmIndexadoMaster');
            if (isChecked && masterBase && !masterBase.checked) {
                e.target.checked = false;
                return;
            }

            const tbody = document.getElementById('pmInvoicesTable');
            if (tbody) {
                tbody.querySelectorAll('tr').forEach(row => {
                    const cb = row.querySelector('.pm-indexado-iva');
                    if (cb && !cb.disabled && cb.checked !== isChecked) {
                        cb.checked = isChecked;
                        pmCalcRow(row);
                    }
                });
                pmRecalcTotals();
            }
        });

        const roundFixed = (n) => Math.round((n + Number.EPSILON) * 100) / 100;

        window.closePagoMultipleModal = () => pmModal?.classList.remove('active');

        // ── Single Abono helper: open invoice-edit modal
        window.abOpenEditInvoice = () => {
            const nroD = document.getElementById('abNumeroD')?.value;
            const codProv = document.getElementById('abCodProv')?.value;
            
            const item = (window.currentData || []).find(i => i.NumeroD === nroD && i.CodProv === codProv);
            if (!item) { showToast('⚠️ Factura no encontrada. Intente recargar.', 'warning'); return; }

            // Populate the existing invoiceEditModal fields (same logic as editInvoiceBtn)
            document.getElementById('ieNumeroD').value = item.NumeroD || '';
            document.getElementById('ieCodProv').value = item.CodProv || '';
            document.getElementById('ieFechaE').value = (item.FechaE || '').split('T')[0];
            document.getElementById('ieFechaI').value = (item.FechaI || '').split('T')[0];
            document.getElementById('ieFechaV').value = (item.FechaV || '').split('T')[0];
            const n10 = item.Notas10;
            document.getElementById('ieNotas10').value = (n10 !== null && n10 !== undefined && String(n10).trim() === '1') ? '1' : '';
            document.getElementById('ieMontoFacturaBS').value = item.Monto || 0;
            document.getElementById('ieTGravable').value = item.TGravable || 0;
            document.getElementById('ieIVA').value = item.MtoTax || 0;
            document.getElementById('ieFactor').value = item.Factor || 0;
            document.getElementById('ieMontoMEx').value = item.MontoMEx || 0;
            document.getElementById('ieTotalPrd').value = item.TotalPrd || 0;
            document.getElementById('ieFletes').value = item.Fletes || 0;
            document.getElementById('ieDescto1').value = item.Descto1 || 0;
            document.getElementById('ieDescto2').value = item.Descto2 || 0;
            document.getElementById('ieContado').value = item.Contado || 0;
            document.getElementById('ieCredito').value = item.Credito || 0;
            document.getElementById('invoiceEditSubtitle').textContent = `Factura: ${item.NumeroD} | ${item.Descrip || ''}`;

            const invoiceEditForm = document.getElementById('invoiceEditForm');
            if (invoiceEditForm) invoiceEditForm.dataset.codProv = item.CodProv || '';
            // Tag the form so the submit handler knows it came from Abono modal
            if (invoiceEditForm) invoiceEditForm.dataset.fromAb = 'true';

            const invoiceEditModal = document.getElementById('invoiceEditModal');
            if (typeof window.forceShowModal === 'function') window.forceShowModal(invoiceEditModal);
            if (typeof lucide !== 'undefined') lucide.createIcons();

            // Auto-fetch rate for emission date
            const emissionDate = (item.FechaE || '').split('T')[0];
            if (emissionDate) {
                fetch(`/api/exchange-rate?fecha=${encodeURIComponent(emissionDate)}`)
                    .then(r => r.ok ? r.json() : null)
                    .then(j => {
                        if (j && j.rate) {
                            const ieFactor = document.getElementById('ieFactor');
                            if (ieFactor) { ieFactor.value = j.rate.toFixed(4); }
                        }
                    }).catch(() => {});
            }
        };

        // ── PM helper: open edit-provider modal safely (fetches data if cache is empty)
        window.pmOpenEditProviderSafe = async () => {
            const items = window._pmCurrentItems;
            if (!items || items.length === 0) { showToast('⚠️ No hay proveedor activo en el modal.', 'warning'); return; }
            const codProv = items[0].CodProv;
            // Ensure providers cache is loaded before opening edit modal
            try {
                const res = await fetch('/api/procurement/providers');
                if (res.ok) {
                    const json = await res.json();
                    // Push data into the shared providersData array used by openEditProvider
                    // We do this by calling fetchProviders() through the public API
                    if (typeof fetchProviders === 'function') await fetchProviders();
                }
            } catch(e) {}
            if (typeof window.openEditProvider === 'function') {
                window.openEditProvider(codProv);
            }
        };

        // ── PM helper: open invoice-edit modal for a row (reuses existing invoiceEditModal)
        window.pmOpenEditInvoice = (rKey) => {
            const items = window._pmCurrentItems || [];
            const item = items.find(i => window.getItemKey(i) === rKey);
            if (!item) { showToast('⚠️ Factura no encontrada.', 'warning'); return; }

            // Populate the existing invoiceEditModal fields (same logic as editInvoiceBtn)
            document.getElementById('ieNumeroD').value = item.NumeroD || '';
            document.getElementById('ieCodProv').value = item.CodProv || '';
            document.getElementById('ieFechaE').value = (item.FechaE || '').split('T')[0];
            document.getElementById('ieFechaI').value = (item.FechaI || '').split('T')[0];
            document.getElementById('ieFechaV').value = (item.FechaV || '').split('T')[0];
            const n10 = item.Notas10;
            document.getElementById('ieNotas10').value = (n10 !== null && n10 !== undefined && String(n10).trim() === '1') ? '1' : '';
            document.getElementById('ieMontoFacturaBS').value = item.Monto || 0;
            document.getElementById('ieTGravable').value = item.TGravable || 0;
            document.getElementById('ieIVA').value = item.MtoTax || 0;
            document.getElementById('ieFactor').value = item.Factor || 0;
            document.getElementById('ieMontoMEx').value = item.MontoMEx || 0;
            document.getElementById('ieTotalPrd').value = item.TotalPrd || 0;
            document.getElementById('ieFletes').value = item.Fletes || 0;
            document.getElementById('ieDescto1').value = item.Descto1 || 0;
            document.getElementById('ieDescto2').value = item.Descto2 || 0;
            document.getElementById('ieContado').value = item.Contado || 0;
            document.getElementById('ieCredito').value = item.Credito || 0;
            document.getElementById('invoiceEditSubtitle').textContent = `Factura: ${item.NumeroD} | ${item.Descrip || ''}`;

            const invoiceEditForm = document.getElementById('invoiceEditForm');
            if (invoiceEditForm) invoiceEditForm.dataset.codProv = item.CodProv || '';
            // Tag the form so the submit handler knows it came from PM modal
            if (invoiceEditForm) invoiceEditForm.dataset.fromPm = 'true';
            if (invoiceEditForm) invoiceEditForm.dataset.pmRowKey = rKey;

            const invoiceEditModal = document.getElementById('invoiceEditModal');
            if (typeof window.forceShowModal === 'function') window.forceShowModal(invoiceEditModal);
            if (typeof lucide !== 'undefined') lucide.createIcons();

            // Auto-fetch rate for emission date
            const emissionDate = (item.FechaE || '').split('T')[0];
            if (emissionDate) {
                fetch(`/api/exchange-rate?fecha=${encodeURIComponent(emissionDate)}`)
                    .then(r => r.ok ? r.json() : null)
                    .then(j => {
                        if (j && j.rate) {
                            const ieFactor = document.getElementById('ieFactor');
                            if (ieFactor) { ieFactor.value = j.rate.toFixed(4); }
                        }
                    }).catch(() => {});
            }
        };

        // Expose PM recalc for external triggers (e.g., after saving provider conditions)
        window._pmRecalcAfterProviderSave = async (codProv) => {
            if (!pmModal?.classList.contains('active')) return;
            // Check if any row belongs to this provider
            const rows = document.querySelectorAll('#pmInvoicesTable tr');
            let affected = 0;
            for (const row of rows) {
                const rKey = row.dataset.rowkey;
                const rowNroUnico = row.dataset.nrounico;
                const cxp  = pmCxpStatuses[rKey];
                if (!cxp || String(cxp.CodProv).trim() !== String(codProv).trim()) continue;
                // Re-fetch the latest cxp-status for this invoice
                try {
                    let url = `/api/procurement/cxp-status?cod_prov=${encodeURIComponent(cxp.CodProv)}&numero_d=${encodeURIComponent(cxp.NumeroD)}`;
                    if (rowNroUnico && rowNroUnico !== "undefined" && rowNroUnico !== "null") {
                        url += `&nro_unico=${encodeURIComponent(rowNroUnico)}`;
                    }
                    const res = await fetch(url);
                    if (res.ok) {
                        const json = await res.json();
                        pmCxpStatuses[rKey] = json.data;
                        const pmMontoBsInput = row.querySelector('.pm-monto-bs');
                        if (pmMontoBsInput) pmMontoBsInput.dataset.manualEdit = "false";
                        
                        const sel = row.querySelector('.pm-desc');
                        const cbPP = row.querySelector('.pm-pronto-pago');
                        const dedPP = row.querySelector('.pm-pp-deduce-iva');
                        
                        const pagoDateStrRaw = row.querySelector('.pm-fecha')?.value || new Date().toISOString().split('T')[0];
                        const partsP2 = pagoDateStrRaw.split('T')[0].split('-');
                        const pagoDate = new Date(partsP2[0], partsP2[1] - 1, partsP2[2]);
                        pagoDate.setHours(0,0,0,0);

                        if (sel && json.data) {
                            let opts = '<option value="0">0%</option>';
                            let bestMatch = null;
                            if (json.data.Descuentos && json.data.Descuentos.length > 0) {
                                const baseDateStr = json.data.BaseDiasCredito === 'EMISION' ? json.data.FechaE : (json.data.FechaI || json.data.FechaE);
                                const baseDate = new Date(baseDateStr);
                                baseDate.setHours(0,0,0,0);
                                let diffDays = Math.floor((pagoDate - baseDate) / (1000 * 60 * 60 * 24));
                                if (diffDays < 0) diffDays = 0;
                                json.data.Descuentos.forEach((d, i) => {
                                    opts += `<option value="${d.Porcentaje}">${d.Porcentaje.toFixed(2)}% (T-${i+1})</option>`;
                                });
                                bestMatch = json.data.Descuentos.find(tier => diffDays >= tier.DiasDesde && diffDays <= tier.DiasHasta);
                            }
                            sel.innerHTML = opts;
                            if (bestMatch && cbPP) {
                                sel.value = bestMatch.Porcentaje;
                                sel.disabled = false;
                                cbPP.checked = true;
                                if (dedPP) {
                                    dedPP.disabled = false;
                                    dedPP.checked = bestMatch.DeduceIVA !== false && bestMatch.DeduceIVA !== 0 && bestMatch.DeduceIVA !== '0';
                                }
                            } else if (cbPP) {
                                cbPP.checked = false;
                                sel.disabled = true;
                                if (dedPP) {
                                    dedPP.disabled = true;
                                    dedPP.checked = false;
                                }
                            }
                        }

                        // --- Auto-Initialize Desc Basico Checkbox based on config ---
                        const cbDB = row.querySelector('.pm-desc-base-check');
                        const pctTxtDB = row.querySelector('.pm-desc-base-pct');
                        const dedDB = row.querySelector('.pm-db-deduce-iva');
                        if (cbDB && json.data && Number(json.data.DescuentoBase_Pct) > 0) {
                            let dbPct = Number(json.data.DescuentoBase_Pct);
                            let appliesInitially = true;
                            if (json.data.DescuentoBase_Condicion === 'VENCIMIENTO') {
                                const vDateStrDB = json.data.FechaVSaint || json.data.FechaV_Calculada;
                                const partsV = vDateStrDB.split('T')[0].split('-');
                                let vd = new Date(partsV[0], partsV[1] - 1, partsV[2]);
                                vd.setHours(0,0,0,0);
                                if (pagoDate > vd) appliesInitially = false;
                            }
                            cbDB.checked = appliesInitially;
                            if (pctTxtDB) {
                                pctTxtDB.value = dbPct;
                                pctTxtDB.readOnly = !appliesInitially;
                            }
                            if (dedDB) {
                                dedDB.disabled = !appliesInitially;
                                if (appliesInitially) {
                                    dedDB.checked = json.data.DescuentoBase_DeduceIVA !== false && json.data.DescuentoBase_DeduceIVA !== 0 && json.data.DescuentoBase_DeduceIVA !== '0';
                                }
                            }
                        } else if (cbDB) {
                            cbDB.checked = false;
                            if (pctTxtDB) {
                                pctTxtDB.value = 0;
                                pctTxtDB.readOnly = true;
                            }
                            if (dedDB) {
                                dedDB.disabled = true;
                                dedDB.checked = false;
                            }
                        }
                    }
                } catch(e) { console.warn('PM recalc: error re-fetching cxp-status', e); }
                
                pmCalcRow(row);
                affected++;
            }
            if (affected > 0) {
                pmRecalcTotals();
                showToast(`✅ ${affected} fila(s) recalculada(s) con las nuevas condiciones del proveedor.`, 'success');
            }
        };

        document.getElementById('pmGoBtnRetIva')?.addEventListener('click', () => {
            const btn = document.getElementById('pmGoBtnRetIva');
            if (btn && btn.dataset.yaCreada === "true") {
                const ivaItem = pmItems.find(i => (i.HistorialAbonos || []).some(a => a.TipoAbono === 'RETENCION_IVA'));
                if (ivaItem) {
                    window.open(`/api/retenciones/by-invoice/${encodeURIComponent(ivaItem.NumeroD)}/pdf?cod_prov=${encodeURIComponent(ivaItem.CodProv)}`, '_blank');
                }
            } else {
                if (typeof pmItems !== 'undefined' && pmItems.length > 0) {
                    if (window.launchRetencionModal) window.launchRetencionModal(pmItems);
                } else {
                    document.getElementById('btnGenerarRetencion')?.click();
                }
            }
        });
        document.getElementById('pmGoBtnRetIslr')?.addEventListener('click', () => {
            const btn = document.getElementById('pmGoBtnRetIslr');
            if (btn && btn.dataset.yaCreada === "true") {
                const islrItem = pmItems.find(i => (i.HistorialAbonos || []).some(a => a.TipoAbono === 'RETENCION_ISLR'));
                if (islrItem) {
                    window.open(`/api/retenciones-islr/by-invoice/${encodeURIComponent(islrItem.NumeroD)}/pdf?cod_prov=${encodeURIComponent(islrItem.CodProv)}`, '_blank');
                }
            } else {
                if (typeof pmItems !== 'undefined' && pmItems.length > 0) {
                    if (window.launchRetencionIslrModal) window.launchRetencionIslrModal(pmItems);
                } else {
                    document.getElementById('btnGenerarRetencionIslr')?.click();
                }
            }
        });
        document.getElementById('pmGoBtnND')?.addEventListener('click', () => {
            showToast('⚠️ Las Notas de Débito deben generarse desde el panel individual de cada factura.', 'warning');
        });
        document.getElementById('pmGoBtnNC')?.addEventListener('click', () => {
             // If they selected exactly 1, we can redirect. Otherwise warn.
             if (window.multiPaySelectionData && window.multiPaySelectionData.size === 1) {
                 closePagoMultipleModal();
                 const singleItem = Array.from(window.multiPaySelectionData.values())[0];
                 openNCFromMain(singleItem.CodProv, singleItem.NumeroD);
             } else {
                 showToast('⚠️ Seleccione una sola factura para generar Nota de Crédito Manual.', 'warning');
             }
        });
        window.closeGlobalDynamicRecalculateModal = () =>
            document.getElementById('globalDynamicRecalculateModal')?.classList.remove('active');

        // ── Helpers per-row ─────────────────────────────────────────────
        const pmGetDescBase = (cxp, row) => {
            if (!cxp) return 0;
            if (row) {
                const cb = row.querySelector('.pm-desc-base-check');
                if (cb && !cb.checked) return 0;
                const input = row.querySelector('.pm-desc-base-pct');
                if (input && parseFloat(input.value) > 0) return parseFloat(input.value);
            }
            if (!Number(cxp.DescuentoBase_Pct)) return 0;
            if (cxp.DescuentoBase_Condicion === 'INDEPENDIENTE') {
                return Number(cxp.DescuentoBase_Pct);
            } else if (cxp.DescuentoBase_Condicion === 'VENCIMIENTO') {
                const pagoDateDesc = row ? new Date(getDateValue(row.querySelector('.pm-fecha'))) : new Date();
                let vDate = new Date(cxp.FechaVSaint || cxp.FechaV_Calculada); 
                vDate.setHours(0,0,0,0);
                pagoDateDesc.setHours(0,0,0,0);
                if (pagoDateDesc <= vDate) {
                    return Number(cxp.DescuentoBase_Pct);
                }
            }
            return 0;
        };
        const pmGetDeduceIvaBase = (cxp, row) => {
            if (row) {
                const cb = row.querySelector('.pm-db-deduce-iva');
                if (cb) return cb.checked;
            }
            if (!cxp) return true;
            return cxp.DescuentoBase_DeduceIVA !== false && cxp.DescuentoBase_DeduceIVA !== '0' && cxp.DescuentoBase_DeduceIVA !== 0;
        };
        const pmGetDeduceIvaPP = (cxp, pctDesc, row) => {
            if (row) {
                const cb = row.querySelector('.pm-pp-deduce-iva');
                if (cb) return cb.checked;
            }
            if (!cxp || !cxp.Descuentos || pctDesc === 0) return true;
            const tier = cxp.Descuentos.find(x => parseFloat(x.Porcentaje) === pctDesc);
            return tier && tier.DeduceIVA !== undefined ? tier.DeduceIVA !== false && tier.DeduceIVA !== 0 && tier.DeduceIVA !== '0' : true;
        };


        const pmCalcRow = window.pmCalcRow = (row) => {
            const rKey = row.dataset.rowkey;
            const cxp = pmCxpStatuses[rKey];
            if (!cxp) return;

            const historicalTasa = parseFloat(cxp.TasaEmision) || 1;

            const idxBaseCb = row.querySelector('.pm-indexado');
            if (idxBaseCb) {
                if (parseFloat(cxp.TasaEmision) <= 1) {
                    idxBaseCb.checked = false;
                    idxBaseCb.disabled = true;
                    if(row.querySelector('.pm-indexado-iva')) {
                        row.querySelector('.pm-indexado-iva').checked = false;
                        row.querySelector('.pm-indexado-iva').disabled = true;
                    }
                } else {
                    idxBaseCb.disabled = false;
                    if(row.querySelector('.pm-indexado-iva')) row.querySelector('.pm-indexado-iva').disabled = false;
                }
            }

            const tasa = parseFloat(row.querySelector('.pm-tasa')?.value) || 0;
            const indexado = row.querySelector('.pm-indexado')?.checked || false;

            const fin = calculateInvoiceFinancials(cxp, {
                tasaDia: tasa || cxp.TasaEmision || 1,
                aplicaIndex: indexado,
                aplicaIndexIva: row.querySelector('.pm-indexado-iva') !== null ? row.querySelector('.pm-indexado-iva').checked : (cxp.IndexaIVA ?? true),
                pctDesc: row.querySelector('.pm-pronto-pago')?.checked ? (parseFloat(row.querySelector('.pm-desc')?.value) || 0) : 0,
                descBasePct: pmGetDescBase(cxp, row),
                islrRate: parseFloat(row.querySelector('.pm-islr-concept')?.value) || 0,
                deduceIvaBase: pmGetDeduceIvaBase(cxp, row),
                deduceIvaPP: pmGetDeduceIvaPP(cxp, row.querySelector('.pm-pronto-pago')?.checked ? (parseFloat(row.querySelector('.pm-desc')?.value) || 0) : 0, row)
            });

            const finExigido = calculateInvoiceFinancials(cxp, {
                tasaDia: indexado ? (tasa || cxp.TasaEmision || 1) : historicalTasa,
                aplicaIndex: indexado,
                aplicaIndexIva: row.querySelector('.pm-indexado-iva') !== null ? row.querySelector('.pm-indexado-iva').checked : (cxp.IndexaIVA ?? true),
                pctDesc: row.querySelector('.pm-pronto-pago')?.checked ? (parseFloat(row.querySelector('.pm-desc')?.value) || 0) : 0,
                descBasePct: pmGetDescBase(cxp, row),
                islrRate: parseFloat(row.querySelector('.pm-islr-concept')?.value) || 0,
                deduceIvaBase: pmGetDeduceIvaBase(cxp, row),
                deduceIvaPP: pmGetDeduceIvaPP(cxp, row.querySelector('.pm-pronto-pago')?.checked ? (parseFloat(row.querySelector('.pm-desc')?.value) || 0) : 0, row)
            });

            const deudaExigidaHoy = finExigido.finalBs;

            // ───────────────── ROW CALCULATION LOCK / SHIELD LOGIC ─────────────────
            const pmMontoBsInput = row.querySelector('.pm-monto-bs');
            
            let finalOutputBs = fin.finalBs; // default pure math target
            let isManualEdit = pmMontoBsInput && pmMontoBsInput.dataset.manualEdit === "true";
            
            if (isManualEdit) {
                let typedVal = parseFloat(pmMontoBsInput.value) || 0;
                
                // Si el usuario borró todo o puso 0, o introdujo exactamente lo mismo que el target previo, deshacemos el modo manual.
                if (typedVal <= 0 || pmMontoBsInput.value === row.dataset.lastAutoBs) {
                    pmMontoBsInput.dataset.manualEdit = "false";
                    isManualEdit = false;
                } else {
                    // Pago válido tipeado a mano (inferior, igual o superior al real): LO RESPETAMOS y bloqueamos calculos
                    finalOutputBs = typedVal;
                }
            }

            // Aplicamos UI
            if (isManualEdit) {
                 pmMontoBsInput.style.border = "2px solid var(--danger)";
                 pmMontoBsInput.style.boxShadow = "0 0 5px rgba(239, 68, 68, 0.5)";
                 pmMontoBsInput.title = "Monto editado manualmente (bloqueado para recálculo automático)";
            } else {
                 pmMontoBsInput.style.border = "";
                 pmMontoBsInput.style.boxShadow = "";
                 pmMontoBsInput.title = "";
            }

            // Aplicamos matemática
            pmMontoBsInput.value = finalOutputBs.toFixed(2);
            row.dataset.targetBs = fin.finalBs; // la deuda MATEMÁTICA real
            
            if (!isManualEdit || finalOutputBs === fin.finalBs) {
                 row.dataset.lastAutoBs = finalOutputBs.toFixed(2);
            }

            pmRecalcRowUsdAmount(row);

            // Update row hidden labels for Global Summary
            if(row.querySelector('.pm-base-bs'))       row.querySelector('.pm-base-bs').textContent       = fin.baseBs.toFixed(2);
            if(row.querySelector('.pm-iva-bs'))        row.querySelector('.pm-iva-bs').textContent        = fin.ivaBs.toFixed(2);
            if(row.querySelector('.pm-iva-apagar-bs')) row.querySelector('.pm-iva-apagar-bs').textContent = fin.ivaAPagarBs.toFixed(2);
            if(row.querySelector('.pm-exento-bs'))     row.querySelector('.pm-exento-bs').textContent     = fin.exentoBs.toFixed(2);
            if(row.querySelector('.pm-retiva-bs'))     row.querySelector('.pm-retiva-bs').textContent     = (fin.retencionBs + (parseFloat(cxp.RetencionIvaAbonada) || 0)).toFixed(2);
            if(row.querySelector('.pm-retislr-bs'))    row.querySelector('.pm-retislr-bs').textContent    = (fin.retenIslrBs + (parseFloat(cxp.RetencionIslrAbonada) || 0)).toFixed(2);

            // Equiv USD (for the auto-filled payment amount)
            row.querySelector('.pm-monto-usd').textContent = fin.equivUsd.toFixed(2);

            // IMPORTANT: Overwrite the visual "Saldo USD" with the calculated mathematical reality 
            // instead of the static database value to prevent incongruencies!
            row.querySelector('.pm-saldo').textContent = fin.equivUsd.toFixed(2);

            if (typeof pmDistributePartialPayment !== 'undefined') pmDistributePartialPayment();
            pmRecalcTotals();
        };

        // NEW HELPER: For when the user manually types a partial payment amount in Bs
        const pmRecalcRowUsdAmount = (row) => {
            const bs = parseFloat(row.querySelector('.pm-monto-bs')?.value) || 0;
            const usdCell = row.querySelector('.pm-monto-usd');
            if (bs <= 0) {
                usdCell.textContent = '0.00';
                return;
            }
            const indexado = row.querySelector('.pm-indexado')?.checked;
            const rKey = row.dataset.rowkey;
            const cxp = pmCxpStatuses[rKey];
            
            if (!indexado && cxp && cxp.TasaEmision) {
                usdCell.textContent = (bs / parseFloat(cxp.TasaEmision)).toFixed(2);
            } else {
                const rate = parseFloat(row.querySelector('.pm-tasa')?.value) || 1;
                usdCell.textContent = rate > 0 ? (bs / rate).toFixed(2) : '0.00';
            }
        };

        const pmDistributePartialPayment = () => {
            const montoInput = document.getElementById('pmMontoTotalReal');
            if (!montoInput || montoInput.dataset.manualEdit !== "true") return;
            
            let totalToDistribute = parseFloat(montoInput.value) || 0;
            document.querySelectorAll('#pmInvoicesTable tr').forEach(row => {
                let bsTarget = parseFloat(row.dataset.targetBs) || 0;
                if (totalToDistribute >= bsTarget && bsTarget > 0) {
                    row.querySelector('.pm-monto-bs').value = bsTarget.toFixed(2);
                    totalToDistribute -= bsTarget;
                } else if (totalToDistribute > 0) {
                    row.querySelector('.pm-monto-bs').value = totalToDistribute.toFixed(2);
                    totalToDistribute = 0;
                } else {
                    row.querySelector('.pm-monto-bs').value = "0.00";
                }
                pmRecalcRowUsdAmount(row);
            });
        };

        const pmRecalcTotals = () => {
            let totalBs = 0, totalUsd = 0, totalSaldo = 0;
            let totalIvaAPagar = 0, totalRetIva = 0, totalRetIslr = 0;

            document.querySelectorAll('#pmInvoicesTable tr').forEach(row => {
                totalBs    += parseFloat(row.querySelector('.pm-monto-bs')?.value)     || 0;
                totalUsd   += parseFloat(row.querySelector('.pm-monto-usd')?.textContent) || 0;
                totalSaldo += parseFloat(row.querySelector('.pm-saldo')?.textContent)  || 0;
                
                totalIvaAPagar += parseFloat(row.querySelector('.pm-iva-apagar-bs')?.textContent) || 0;
                totalRetIva    += parseFloat(row.querySelector('.pm-retiva-bs')?.textContent)    || 0;
                totalRetIslr   += parseFloat(row.querySelector('.pm-retislr-bs')?.textContent)   || 0;
            });

            document.getElementById('pmTotalMontoBs').textContent  = formatBs(totalBs);
            document.getElementById('pmTotalMontoUsd').textContent = totalUsd.toFixed(2);
            document.getElementById('pmTotalSaldoUsd').textContent = totalSaldo.toFixed(2);
            
            // New footer totals
            if(document.getElementById('pmTotalIvaAPagar')) document.getElementById('pmTotalIvaAPagar').textContent = formatBs(totalIvaAPagar);
            if(document.getElementById('pmTotalRetIva'))    document.getElementById('pmTotalRetIva').textContent    = formatBs(totalRetIva);
            if(document.getElementById('pmTotalRetIslr'))   document.getElementById('pmTotalRetIslr').textContent   = formatBs(totalRetIslr);

            const montoInput = document.getElementById('pmMontoTotalReal');
            if (montoInput && montoInput.dataset.manualEdit !== "true") {
                montoInput.value = totalBs.toFixed(2);
            }

            const montoReal = parseFloat(document.getElementById('pmMontoTotalReal')?.value) || 0;
            const diff = montoReal - totalBs;
            const group = document.getElementById('pmExcedenteGroup');
            if (diff > 0.01) {
                group.style.display = 'flex';
                document.getElementById('pmExcedenteVal').textContent = `Bs.S ${bsFormatter(diff)}`;
                if(montoInput) montoInput.style.borderColor = 'var(--danger)';
            } else {
                group.style.display = 'none';
                if(montoInput) montoInput.style.borderColor = 'var(--primary-accent)';
            }
        };

        document.getElementById('pmMontoTotalReal')?.addEventListener('input', (e) => {
            e.target.dataset.manualEdit = "true";
            pmDistributePartialPayment();
            pmRecalcTotals();
        });

        // ── Fetch exchange rate ─────────────────────────────────────────
        const pmFetchRate = async (row) => {
            const fecha = row.querySelector('.pm-fecha')?.value;
            if (!fecha) return;
            try {
                const res  = await fetch(`/api/exchange-rate?fecha=${encodeURIComponent(fecha)}`);
                if (!res.ok) return;
                const json = await res.json();
                const rKey = row.dataset.rowkey;
                const cxp = pmCxpStatuses[rKey];
                if (json.rate) {
                    const dec = cxp?.DecimalesTasa !== undefined ? cxp.DecimalesTasa : 4;
                    row.querySelector('.pm-tasa').value = json.rate.toFixed(dec);
                }
                
                // RE-EVALUATE DYNAMIC CHECKS ON DATE CHANGE:
                if (cxp) {
                    const partsP = fecha.split('T')[0].split('-');
                    const pagoDate = new Date(partsP[0], partsP[1] - 1, partsP[2]);
                    pagoDate.setHours(0,0,0,0);

                    // 1. Indexation
                    if (cxp.FechaNI_Calculada) {
                        const partsNI = cxp.FechaNI_Calculada.split('T')[0].split('-');
                        const niDate = new Date(partsNI[0], partsNI[1] - 1, partsNI[2]);
                        niDate.setHours(0,0,0,0);
                        row.querySelector('.pm-indexado').checked = pagoDate > niDate;
                        if(row.querySelector('.pm-indexado-iva')) {
                            row.querySelector('.pm-indexado-iva').checked = cxp.IndexaIVA !== false;
                        }
                    }

                    // 2. Descuento Base
                    const cbDB = row.querySelector('.pm-desc-base-check');
                    if (cbDB && cxp.DescuentoBase_Condicion === 'VENCIMIENTO') {
                        const descBasePct = parseFloat(cxp.DescuentoBase_Pct) || 0;
                        if (descBasePct > 0) {
                            const vDateStr = cxp.FechaVSaint || cxp.FechaV_Calculada;
                            const partsV = vDateStr.split('T')[0].split('-');
                            const vDate = new Date(partsV[0], partsV[1] - 1, partsV[2]);
                            vDate.setHours(0,0,0,0);
                            const appliesDescBase = (pagoDate <= vDate);
                            cbDB.checked = appliesDescBase;
                            const pctTxtDB = row.querySelector('.pm-desc-base-pct');
                            if (pctTxtDB) pctTxtDB.readOnly = !appliesDescBase;
                            const dedDB = row.querySelector('.pm-db-deduce-iva');
                            if (dedDB) {
                                dedDB.disabled = !appliesDescBase;
                                if (!appliesDescBase) dedDB.checked = false;
                                else dedDB.checked = cxp.DescuentoBase_DeduceIVA !== false && cxp.DescuentoBase_DeduceIVA !== 0 && cxp.DescuentoBase_DeduceIVA !== '0';
                            }
                        }
                    }

                    // 3. Pronto Pago Tiers
                    if (cxp.Descuentos && cxp.Descuentos.length > 0) {
                        const baseDateStr = cxp.BaseDiasCredito === 'EMISION' ? cxp.FechaE : (cxp.FechaI || cxp.FechaE);
                        const baseDate = new Date(baseDateStr);
                        baseDate.setHours(0,0,0,0);
                        let diffDays = Math.floor((pagoDate - baseDate) / (1000 * 60 * 60 * 24));
                        if (diffDays < 0) diffDays = 0;
                        
                        const match = cxp.Descuentos.find(tier => diffDays >= tier.DiasDesde && diffDays <= tier.DiasHasta);
                        const sel = row.querySelector('.pm-desc');
                        const cbPP = row.querySelector('.pm-pronto-pago');
                        const dedPP = row.querySelector('.pm-pp-deduce-iva');
                        if (sel && cbPP) {
                            if (match) {
                                sel.value = match.Porcentaje;
                                sel.disabled = false;
                                cbPP.checked = true;
                                if (dedPP) {
                                    dedPP.disabled = false;
                                    dedPP.checked = match.DeduceIVA !== false && match.DeduceIVA !== 0 && match.DeduceIVA !== '0';
                                }
                            } else {
                                cbPP.checked = false;
                                sel.disabled = true;
                                if (dedPP) {
                                    dedPP.disabled = true;
                                    dedPP.checked = false;
                                }
                            }
                        }
                    }
                }

                pmCalcRow(row);
            } catch (e) { console.error(e); }
        };

        // ── Open row-level Recálculo Dinámico ───────────────────────────
        const pmOpenRowDynamic = (row) => {
            const rKey = row.dataset.rowkey;
            const cxp = pmCxpStatuses[rKey];
            if (!cxp) return;

            const indexado   = row.querySelector('.pm-indexado')?.checked;
            const prontoPago = row.querySelector('.pm-pronto-pago')?.checked;
            const pctDesc    = prontoPago ? (parseFloat(row.querySelector('.pm-desc')?.value) || 0) : 0;
            const tasaDia    = parseFloat(row.querySelector('.pm-tasa')?.value) || 0;
            if (!tasaDia) { showToast('Cargando tasa BCV…', 'warning'); return; }
            const islrRate = parseFloat(row.querySelector('.pm-islr-concept')?.value) || 0;

            const fin = calculateInvoiceFinancials(cxp, {
                tasaDia: tasaDia,
                aplicaIndex: indexado,
                aplicaIndexIva: row.querySelector('.pm-indexado-iva') !== null ? row.querySelector('.pm-indexado-iva').checked : (cxp.IndexaIVA ?? true),
                pctDesc: pctDesc,
                descBasePct: pmGetDescBase(cxp, row),
                islrRate: islrRate,
                deduceIvaBase: pmGetDeduceIvaBase(cxp, row),
                deduceIvaPP: pmGetDeduceIvaPP(cxp, pctDesc, row)
            });

            // Populate dynModal (reuse existing single-invoice modal elements)
            const dynModal = document.getElementById('dynamicInvoiceStatusModal');
            if (!dynModal) return;

            dynModal.querySelector('#dynTasaBcv'     )&&(dynModal.querySelector('#dynTasaBcv'     ).textContent = formatBs(fin.currentTasa));
            dynModal.querySelector('#dynBaseBs'      )&&(dynModal.querySelector('#dynBaseBs'      ).textContent = formatBs(fin.baseBs));
            dynModal.querySelector('#dynIvaBs'       )&&(dynModal.querySelector('#dynIvaBs'       ).textContent = formatBs(fin.ivaBs));
            dynModal.querySelector('#dynIvaAPagar'   )&&(dynModal.querySelector('#dynIvaAPagar'   ).textContent = formatBs(fin.ivaAPagarBs));
            dynModal.querySelector('#dynIvaRetenido' )&&(dynModal.querySelector('#dynIvaRetenido' ).textContent = formatBs(fin.retencionBs + (parseFloat(cxp.RetencionIvaAbonada) || 0)));
            dynModal.querySelector('#dynRetenIslrBs' )&&(dynModal.querySelector('#dynRetenIslrBs' ).textContent = '- ' + formatBs(fin.retenIslrBs + (parseFloat(cxp.RetencionIslrAbonada) || 0)));
            dynModal.querySelector('#dynExentoBs'    )&&(dynModal.querySelector('#dynExentoBs'    ).textContent = formatBs(fin.exentoBs));
            dynModal.querySelector('#dynRestanteBs'  )&&(dynModal.querySelector('#dynRestanteBs'  ).textContent = formatBs(fin.finalBs));

            const exactUsdFormatter = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
            dynModal.querySelector('#dynMtoTotalUsd' )&&(dynModal.querySelector('#dynMtoTotalUsd' ).textContent = '$' + exactUsdFormatter.format(fin.origTotalUsd));
            dynModal.querySelector('#dynSubtotalUsd' )&&(dynModal.querySelector('#dynSubtotalUsd' ).textContent = '$' + exactUsdFormatter.format(fin.subtotalUsd));
            
            dynModal.querySelector('#dynMtoTotalBs' )&&(dynModal.querySelector('#dynMtoTotalBs' ).textContent = formatBs(fin.origTotalUsd * fin.currentTasa));
            dynModal.querySelector('#dynSubtotalBs' )&&(dynModal.querySelector('#dynSubtotalBs' ).textContent = formatBs(fin.subtotalUsd * fin.currentTasa));

            if (pctDesc > 0 || pmGetDescBase(cxp, row) > 0) {
                const dbox = dynModal.querySelector('#dynDescuentoBox');
                const dboxBs = dynModal.querySelector('#dynDescuentoBoxBs');
                if (pctDesc > 0) {
                    if(dbox) dbox.style.display = 'flex';
                    if(dboxBs) dboxBs.style.display = 'flex';
                    
                    const pctE = dynModal.querySelector('#dynPctDesc');
                    const pctEBs = dynModal.querySelector('#dynPctDescBs');
                    if (pctE) pctE.textContent = pctDesc;
                    if (pctEBs) pctEBs.textContent = pctDesc;
                    
                    const amE = dynModal.querySelector('#dynMontoDescUsd');
                    const amEBs = dynModal.querySelector('#dynMontoDescBs');
                    if (amE) amE.textContent = '-' + usdFormatter(fin.descPPUsdMonto);
                    if (amEBs) amEBs.textContent = '-' + formatBs(fin.descPPUsdMonto * fin.currentTasa);
                } else {
                    if(dbox) dbox.style.display = 'none';
                    if(dboxBs) dboxBs.style.display = 'none';
                }
                
                const dbbox = dynModal.querySelector('#dynDescBaseBox');
                const dbboxBs = dynModal.querySelector('#dynDescBaseBoxBs');
                if (pmGetDescBase(cxp, row) > 0) {
                    if(dbbox) dbbox.style.display = 'flex';
                    if(dbboxBs) dbboxBs.style.display = 'flex';
                    
                    const pctBe = dynModal.querySelector('#dynPctDescBase');
                    const pctBeBs = dynModal.querySelector('#dynPctDescBaseBs');
                    if (pctBe) pctBe.textContent = pmGetDescBase(cxp, row);
                    if (pctBeBs) pctBeBs.textContent = pmGetDescBase(cxp, row);
                    
                    const amBe = dynModal.querySelector('#dynMontoDescBaseUsd');
                    const amBeBs = dynModal.querySelector('#dynMontoDescBaseBs');
                    if (amBe) amBe.textContent = '-' + usdFormatter(fin.descBaseUsdMonto);
                    if (amBeBs) amBeBs.textContent = '-' + formatBs(fin.descBaseUsdMonto * fin.currentTasa);
                } else {
                    if(dbbox) dbbox.style.display = 'none';
                    if(dbboxBs) dbboxBs.style.display = 'none';
                }
            } else {
                const dbox = dynModal.querySelector('#dynDescuentoBox');
                if (dbox) dbox.style.display = 'none';
                const dboxBs = dynModal.querySelector('#dynDescuentoBoxBs');
                if (dboxBs) dboxBs.style.display = 'none';
                
                const dbbox = dynModal.querySelector('#dynDescBaseBox');
                if (dbbox) dbbox.style.display = 'none';
                const dbboxBs = dynModal.querySelector('#dynDescBaseBoxBs');
                if (dbboxBs) dbboxBs.style.display = 'none';
            }
            // Conditionally show Fletes/Desctos USD
            let desctoFletesHtml = '';
            if (fin.fletesUsd > 0) desctoFletesHtml += `<div style="display:flex;justify-content:space-between; margin-bottom: 2px;"><span>(+) Fletes:</span> <span>${usdFormatter(fin.fletesUsd)}</span></div>`;
            if (fin.d1Usd > 0) desctoFletesHtml += `<div style="display:flex;justify-content:space-between; margin-bottom: 2px;"><span>(-) Descto 1:</span> <span style="color:var(--danger);">${usdFormatter(fin.d1Usd)}</span></div>`;
            if (fin.d2Usd > 0) desctoFletesHtml += `<div style="display:flex;justify-content:space-between; margin-bottom: 2px;"><span>(-) Descto 2:</span> <span style="color:var(--danger);">${usdFormatter(fin.d2Usd)}</span></div>`;
            if (dynModal.querySelector('#dynDesctoFletesBox')) dynModal.querySelector('#dynDesctoFletesBox').innerHTML = desctoFletesHtml;

            // Conditionally show Fletes/Desctos Bs
            let desctoFletesHtmlBs = '';
            if (fin.fletesUsd > 0) desctoFletesHtmlBs += `<div style="display:flex;justify-content:space-between; margin-bottom: 2px;"><span>(+) Fletes:</span> <span>${formatBs(fin.fletesUsd * fin.currentTasa)}</span></div>`;
            if (fin.d1Usd > 0) desctoFletesHtmlBs += `<div style="display:flex;justify-content:space-between; margin-bottom: 2px;"><span>(-) Descto 1:</span> <span style="color:var(--danger);">${formatBs(fin.d1Usd * fin.currentTasa)}</span></div>`;
            if (fin.d2Usd > 0) desctoFletesHtmlBs += `<div style="display:flex;justify-content:space-between; margin-bottom: 2px;"><span>(-) Descto 2:</span> <span style="color:var(--danger);">${formatBs(fin.d2Usd * fin.currentTasa)}</span></div>`;
            if (dynModal.querySelector('#dynDesctoFletesBoxBs')) dynModal.querySelector('#dynDesctoFletesBoxBs').innerHTML = desctoFletesHtmlBs;
            
            dynModal.querySelector('#dynIvaUsd')&&(dynModal.querySelector('#dynIvaUsd').textContent = usdFormatter(fin.ivaUsd));

            dynModal.classList.add('active');
            lucide.createIcons();
        };

        // ── Open global summary modal ───────────────────────────────────
        document.getElementById('btnGlobalDynamicStatus')?.addEventListener('click', () => {
            console.log("Abriendo Resumen Global de Pagos...");
            const pmModal = document.getElementById('pagoMultipleModal');
            if(!pmModal || !pmModal.classList.contains('active')) {
                showToast('Debe tener abierta la modal de Pago Múltiple.', 'warning');
                return;
            }

            const tbody = document.getElementById('pmInvoicesTable');
            const summaryBody = document.getElementById('globalDynamicBody');
            if(!summaryBody) return;
            summaryBody.innerHTML = '';

            let totals = { base:0, iva:0, ivaAPagar:0, exento:0, retIva:0, retIslr:0, total:0 };

            tbody.querySelectorAll('tr').forEach(row => {
                const numeroD = row.getAttribute('data-numerod');
                const baseBs = parseFloat(row.querySelector('.pm-base-bs')?.textContent.replace(/[^0-9.-]+/g,"")) || 0;
                const ivaBs = parseFloat(row.querySelector('.pm-iva-bs')?.textContent.replace(/[^0-9.-]+/g,"")) || 0;
                const exentoBs = parseFloat(row.querySelector('.pm-exento-bs')?.textContent.replace(/[^0-9.-]+/g,"")) || 0;
                const retIvaBs = parseFloat(row.querySelector('.pm-retiva-bs')?.textContent.replace(/[^0-9.-]+/g,"")) || 0;
                const retIslrBs = parseFloat(row.querySelector('.pm-retislr-bs')?.textContent.replace(/[^0-9.-]+/g,"")) || 0;
                const ivaAPagarBs = roundFixed(ivaBs - retIvaBs);
                const totalBs = parseFloat(row.querySelector('.pm-monto-bs')?.value) || 0;

                totals.base += baseBs;
                totals.iva += ivaBs;
                totals.ivaAPagar += ivaAPagarBs;
                totals.exento += exentoBs;
                totals.retIva += retIvaBs;
                totals.retIslr += retIslrBs;
                totals.total += totalBs;

                summaryBody.innerHTML += `
                    <tr>
                        <td>${numeroD}</td>
                        <td class="amount">${formatBs(baseBs)}</td>
                        <td class="amount">${formatBs(ivaBs)}</td>
                        <td class="amount">${formatBs(ivaAPagarBs)}</td>
                        <td class="amount">${formatBs(exentoBs)}</td>
                        <td class="amount" style="color:var(--danger)">${formatBs(retIvaBs)}</td>
                        <td class="amount" style="color:var(--danger)">${formatBs(retIslrBs)}</td>
                        <td class="amount" style="font-weight:bold">${formatBs(totalBs)}</td>
                    </tr>
                `;
            });

            document.getElementById('gdobBase').textContent = formatBs(totals.base);
            document.getElementById('gdobIva').textContent = formatBs(totals.iva);
            document.getElementById('gdobIvaAPagar').textContent = formatBs(totals.ivaAPagar);
            document.getElementById('gdobExento').textContent = formatBs(totals.exento);
            document.getElementById('gdobRetIva').textContent = formatBs(totals.retIva);
            document.getElementById('gdobRetIslr').textContent = formatBs(totals.retIslr);
            document.getElementById('gdobTotal').textContent = formatBs(totals.total);

            document.getElementById('globalDynamicRecalculateModal')?.classList.add('active');
            lucide.createIcons();
        });

        // ── Build rows when modal opens ─────────────────────────────────
        document.getElementById('btnProcesarPago')?.addEventListener('click', async () => {
            let items = [];

            if (window.multiPayMode && window.multiPaySelection.size >= 1) {
                // En modo múltiple: usar el Set completo (incluye facturas de otras búsquedas)
                window.multiPaySelectionData.forEach(item => items.push(item));
            } else {
                // Modo normal: solo checkboxes visibles
                const checked = document.querySelectorAll('.row-checkbox:checked');
                if (checked.length < 1) return;
                checked.forEach(cb => {
                    const dataIndex = cb.getAttribute('data-index');
                    const item = window.currentData[dataIndex];
                    if (item) items.push(item);
                });
            }

            if (items.length === 0) return;

            if (items.length === 1) {
                window.abrirModalEdicion(items[0]);
                return;
            }

            const pmMontoTotalReal = document.getElementById('pmMontoTotalReal');
            if (pmMontoTotalReal) {
                pmMontoTotalReal.value = "";
                pmMontoTotalReal.dataset.manualEdit = "false";
            }

            const provs = new Set(items.map(i => i.CodProv));
            if (provs.size > 1) {
                showToast('⚠️ Para pago múltiple, todas las facturas deben ser del mismo proveedor.', 'warning');
                return;
            }

            pmItems = items;
            window._pmCurrentItems = pmItems; // expose for HTML onclick handlers
            pmCxpStatuses = {};
            lastProcessedPagos = [];
            document.getElementById('btnPmResendEmail') && (document.getElementById('btnPmResendEmail').disabled = true);

            const provName = items[0].ProveedorNombre || items[0].CodProv;
            document.getElementById('pmProvNameLabel').textContent = provName;
            document.getElementById('pmSelectedCountLabel').textContent = items.length;

            // Check retentions state for action bar
            const itemsConIva = items.filter(i => (parseFloat(i.TGravable) || 0) > 0 && (parseFloat(i.MtoTax) || 0) > 0);
            const sinRetencionIva = itemsConIva.filter(i => (parseFloat(i.RetencionIvaAbonada) || 0) === 0 && !hasRet(i) && !(i.HistorialAbonos || []).some(a => a.TipoAbono === 'RETENCION_IVA'));
            
            // Si no hay items con IVA que falten por retener (ya sea porque todos se retuvieron o porque ninguno lleva IVA)
            const allIvaRetainedOrNoIva = itemsConIva.length > 0 ? (sinRetencionIva.length === 0) : true;
            const hasAnyIvaRet = items.some(i => (parseFloat(i.RetencionIvaAbonada) || 0) > 0 || hasRet(i) || (i.HistorialAbonos || []).some(a => a.TipoAbono === 'RETENCION_IVA'));

            const btnPmRetIva = document.getElementById('pmGoBtnRetIva');
            if (btnPmRetIva) {
                if (itemsConIva.length === 0) {
                    btnPmRetIva.innerHTML = '<i data-lucide="file-check-2" size="16"></i> Sin IVA';
                    btnPmRetIva.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                    btnPmRetIva.style.color = '#10b981';
                    btnPmRetIva.style.background = 'rgba(16, 185, 129, 0.05)';
                    btnPmRetIva.dataset.yaCreada = 'true';
                    btnPmRetIva.disabled = true;
                } else if (allIvaRetainedOrNoIva) {
                    btnPmRetIva.innerHTML = '<i data-lucide="file-check-2" size="16"></i> Ver Ret. IVA';
                    btnPmRetIva.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                    btnPmRetIva.style.color = '#10b981';
                    btnPmRetIva.style.background = 'rgba(16, 185, 129, 0.05)';
                    btnPmRetIva.dataset.yaCreada = 'true';
                    btnPmRetIva.disabled = false;
                } else {
                    btnPmRetIva.innerHTML = '<i data-lucide="receipt" size="16"></i> Ret. IVA';
                    btnPmRetIva.style.borderColor = 'rgba(6, 182, 212, 0.4)';
                    btnPmRetIva.style.color = '#06b6d4';
                    btnPmRetIva.style.background = 'rgba(6, 182, 212, 0.05)';
                    btnPmRetIva.dataset.yaCreada = 'false';
                    btnPmRetIva.disabled = false;
                }
            }
            const hasIslrRet = items.some(i => (i.HistorialAbonos || []).some(a => a.TipoAbono === 'RETENCION_ISLR'));
            const btnPmRetIslr = document.getElementById('pmGoBtnRetIslr');
            if (btnPmRetIslr) {
                if (hasIslrRet) {
                    btnPmRetIslr.innerHTML = '<i data-lucide="file-check-2" size="16"></i> Ver Ret. ISLR';
                    btnPmRetIslr.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                    btnPmRetIslr.style.color = '#10b981';
                    btnPmRetIslr.style.background = 'rgba(16, 185, 129, 0.05)';
                    btnPmRetIslr.dataset.yaCreada = 'true';
                } else {
                    btnPmRetIslr.innerHTML = '<i data-lucide="file-text" size="16"></i> Ret. ISLR';
                    btnPmRetIslr.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                    btnPmRetIslr.style.color = '#ef4444';
                    btnPmRetIslr.style.background = 'rgba(239, 68, 68, 0.05)';
                    btnPmRetIslr.dataset.yaCreada = 'false';
                }
            }

            const today = new Date().toISOString().split('T')[0];
            const tbody = document.getElementById('pmInvoicesTable');
            tbody.innerHTML = items.map(item => {
                const rKey = window.getItemKey(item);
                return `
                <tr data-rowkey="${rKey}" data-nrounico="${item.NroUnico}" data-numerod="${item.NumeroD}" data-codprov="${item.CodProv}">
                    <td style="font-weight:500;">${item.NumeroD}</td>
                    <td class="amount pm-saldo" style="color:var(--success);">...</td>
                    <td><input type="date" class="form-control pm-fecha" value="${today}"
                        style="width:130px;padding:0.3rem;font-size:0.8rem;"></td>
                    <td><span class="pm-tasa-emis" style="font-size:0.8rem;color:var(--text-secondary);">—</span></td>
                    <td style="text-align:center;">
                        <button type="button" class="btn-icon pm-btn-calc" title="Recálculo Dinámico">
                            <i data-lucide="calculator" style="width:15px;height:15px;"></i>
                        </button>
                    </td>
                    <td style="text-align:center; display:flex; flex-direction:column; gap:2px; justify-content:center; align-items:center; height:100%;">
                        <input type="checkbox" class="pm-indexado" title="Indexar Base" style="margin:0;">
                        <input type="checkbox" class="pm-indexado-iva" title="Indexar IVA" style="margin:0;">
                    </td>
                    <td style="text-align:center;">
                        <div style="display:flex; flex-direction:column; align-items:center; gap:2px;">
                            <label style="display:flex;align-items:center;gap:0.3rem;font-size:0.8rem;"><input type="checkbox" class="pm-pronto-pago"> Activo</label>
                            <select class="form-control pm-desc" disabled style="width:110px;padding:0.2rem 0.4rem;font-size:0.85rem;">
                                <option value="0">0%</option>
                            </select>
                            <label style="display:flex;align-items:center;gap:0.2rem;font-size:0.75rem;"><input type="checkbox" class="pm-pp-deduce-iva" disabled> Ded. IVA</label>
                        </div>
                    </td>
                    <td style="text-align:center;">
                        <div style="display:flex; flex-direction:column; align-items:center; gap:2px;">
                            <label style="display:flex;align-items:center;gap:0.3rem;font-size:0.8rem;"><input type="checkbox" class="pm-desc-base-check"> Activo</label>
                            <input type="text" class="form-control pm-desc-base-pct" readonly style="width:100px;padding:0.2rem 0.4rem;font-size:0.85rem;text-align:center;" value="0%">
                            <label style="display:flex;align-items:center;gap:0.2rem;font-size:0.75rem;"><input type="checkbox" class="pm-db-deduce-iva" disabled> Ded. IVA</label>
                        </div>
                    </td>
                    <td><input type="number" class="form-control pm-tasa" step="0.0001" readonly
                        style="width:100px;padding:0.3rem;font-size:0.85rem;background:var(--bg-card);"></td>
                    <td>
                        <select class="form-control pm-islr-concept" style="width:110px;padding:0.2rem 0.3rem;font-size:0.8rem;">
                            <option value="0">Sin Ret. (0%)</option>
                            <option value="0.01">Bienes (1%)</option>
                            <option value="0.03">Servicios (3%)</option>
                            <option value="0.05">Alquileres (5%)</option>
                        </select>
                    </td>
                    <td><input type="number" class="form-control pm-monto-bs" step="0.01" min="0" required
                        style="width:130px;padding:0.3rem;font-size:0.9rem;font-weight:bold;"></td>
                    <td class="amount pm-monto-usd" style="font-weight:bold;color:var(--success);">0.00</td>
                    <td style="text-align:center;">
                        <button type="button" class="btn-icon pm-btn-edit-invoice" title="Editar Factura" data-rowkey="${rKey}" style="padding:0.15rem;">
                            <i data-lucide="edit" style="width:17px;height:17px;color:var(--primary-accent);"></i>
                        </button>
                    </td>
                    <td style="display:none;" class="pm-base-bs">0</td>
                    <td style="display:none;" class="pm-iva-bs">0</td>
                    <td style="display:none;" class="pm-iva-apagar-bs">0</td>
                    <td style="display:none;" class="pm-exento-bs">0</td>
                    <td style="display:none;" class="pm-retiva-bs">0</td>
                    <td style="display:none;" class="pm-retislr-bs">0</td>
                </tr>
            `}).join('');

            // Attach row-level listeners
            tbody.querySelectorAll('tr').forEach(row => {
                const dropLock = () => {
                    const el = row.querySelector('.pm-monto-bs');
                    if (el) el.dataset.manualEdit = "false";
                };

                row.querySelector('.pm-fecha')?.addEventListener('change', () => { dropLock(); pmFetchRate(row); });
                row.querySelector('.pm-monto-bs')?.addEventListener('input', (e) => {
                    e.target.dataset.manualEdit = "true";
                    pmRecalcRowUsdAmount(row);
                    pmRecalcTotals();
                });
                row.querySelector('.pm-islr-concept')?.addEventListener('change', () => {
                    dropLock();
                    pmCalcRow(row);
                    pmRecalcTotals();
                });
                row.querySelector('.pm-indexado')?.addEventListener('change', (e) => {
                    dropLock();
                    if (!e.target.checked) {
                        const ivaCb = row.querySelector('.pm-indexado-iva');
                        if (ivaCb) ivaCb.checked = false;
                    }
                    pmCalcRow(row)
                });
                row.querySelector('.pm-indexado-iva')?.addEventListener('change', (e) => {
                    dropLock();
                    const baseCb = row.querySelector('.pm-indexado');
                    if (baseCb && !baseCb.checked && e.target.checked) {
                        e.target.checked = false;
                    }
                    pmCalcRow(row)
                });
                row.querySelector('.pm-pronto-pago')?.addEventListener('change', () => {
                    dropLock();
                    const rKey = row.dataset.rowkey;
                    const cxp = pmCxpStatuses[rKey];
                    const sel = row.querySelector('.pm-desc');
                    const dedPP = row.querySelector('.pm-pp-deduce-iva');
                    if (sel) {
                        sel.disabled = !row.querySelector('.pm-pronto-pago').checked;
                        if (dedPP) dedPP.disabled = sel.disabled;
                        if (cxp && !sel.disabled) {
                            let opts = '<option value="0">0%</option>';
                            if (cxp.Descuentos && cxp.Descuentos.length > 0) {
                                cxp.Descuentos.forEach((d, i) => {
                                    opts += `<option value="${d.Porcentaje}">${d.Porcentaje.toFixed(2)}% (T-${i+1})</option>`;
                                });
                            }
                            sel.innerHTML = opts;
                        }
                    }
                    pmCalcRow(row);
                });
                row.querySelector('.pm-desc')?.addEventListener('change', () => { dropLock(); window.pmCalcRow(row); });
                row.querySelector('.pm-desc-base-check')?.addEventListener('change', (e) => {
                    dropLock();
                    const pctInput = row.querySelector('.pm-desc-base-pct');
                    const dedDB = row.querySelector('.pm-db-deduce-iva');
                    if (pctInput) pctInput.readOnly = !e.target.checked;
                    if (dedDB) dedDB.disabled = !e.target.checked;
                    window.pmCalcRow(row);
                });
                row.querySelector('.pm-desc-base-pct')?.addEventListener('input', () => { dropLock(); window.pmCalcRow(row); });
                row.querySelector('.pm-db-deduce-iva')?.addEventListener('change', () => { dropLock(); window.pmCalcRow(row); });
                row.querySelector('.pm-pp-deduce-iva')?.addEventListener('change', () => { dropLock(); window.pmCalcRow(row); });
                row.querySelector('.pm-btn-calc')?.addEventListener('click', () => pmOpenRowDynamic(row));
                row.querySelector('.pm-btn-edit-invoice')?.addEventListener('click', (e) => {
                    const rKey = e.currentTarget.dataset.rowkey;
                    window.pmOpenEditInvoice(rKey);
                });
            });

            pmModal.classList.add('active');
            lucide.createIcons();

            // Fetch CXP status and rate for each row
            for (const item of items) {
                try {
                    let url = `/api/procurement/cxp-status?cod_prov=${encodeURIComponent(item.CodProv)}&numero_d=${encodeURIComponent(item.NumeroD)}` + (item.NroUnico ? `&nro_unico=${item.NroUnico}`:'');
                    const res = await fetch(url);
                    if (!res.ok) continue;
                    const json = await res.json();
                    
                    const rKey = window.getItemKey(item);
                    pmCxpStatuses[rKey] = json.data;

                    const row = tbody.querySelector(`tr[data-rowkey="${rKey}"]`);
                    if (!row) continue;

                    row.querySelector('.pm-saldo').textContent = (json.data.SaldoRestanteUSD || 0).toFixed(2);
                    const tasaEmis = parseFloat(json.data.TasaEmision) || 0;
                    const tasaEmisEl = row.querySelector('.pm-tasa-emis');
                    if (tasaEmisEl) {
                        const recDec = json.data.DecimalesTasa !== undefined ? json.data.DecimalesTasa : 4;
                        tasaEmisEl.textContent = tasaEmis > 0 ? tasaEmis.toFixed(recDec) : '—';
                    }

                    const sel = row.querySelector('.pm-desc');
                    const cbPP = row.querySelector('.pm-pronto-pago');
                    const dedPP = row.querySelector('.pm-pp-deduce-iva');
                    if (sel && json.data) {
                        let opts = '<option value="0">0%</option>';
                        let bestMatch = null;
                        
                        if (json.data.Descuentos && json.data.Descuentos.length > 0) {
                            const pagoDate = new Date();
                            const baseDateStr = json.data.BaseDiasCredito === 'EMISION' ? json.data.FechaE : (json.data.FechaI || json.data.FechaE);
                            const baseDate = new Date(baseDateStr);
                            pagoDate.setHours(0,0,0,0);
                            baseDate.setHours(0,0,0,0);
                            
                            let diffDays = Math.floor((pagoDate - baseDate) / (1000 * 60 * 60 * 24));
                            if (diffDays < 0) diffDays = 0;

                            json.data.Descuentos.forEach((d, i) => {
                                opts += `<option value="${d.Porcentaje}">${d.Porcentaje.toFixed(2)}% (T-${i+1})</option>`;
                            });
                            bestMatch = json.data.Descuentos.find(tier => diffDays >= tier.DiasDesde && diffDays <= tier.DiasHasta);
                        }
                        sel.innerHTML = opts;
                        
                        if (bestMatch && cbPP) {
                            sel.value = bestMatch.Porcentaje;
                            sel.disabled = false;
                            cbPP.checked = true;
                            if (dedPP) {
                                dedPP.disabled = false;
                                dedPP.checked = bestMatch.DeduceIVA !== false && bestMatch.DeduceIVA !== 0 && bestMatch.DeduceIVA !== '0';
                            }
                        } else if (cbPP) {
                            cbPP.checked = false;
                            sel.disabled = true;
                            if (dedPP) {
                                dedPP.disabled = true;
                                dedPP.checked = false;
                            }
                        }
                    }

                    // --- Auto-Initialize Desc Basico Checkbox based on config ---
                    const cbDB = row.querySelector('.pm-desc-base-check');
                    const pctTxtDB = row.querySelector('.pm-desc-base-pct');
                    const dedDB = row.querySelector('.pm-db-deduce-iva');
                    
                    if (cbDB && json.data && Number(json.data.DescuentoBase_Pct) > 0) {
                        let dbPct = Number(json.data.DescuentoBase_Pct);
                        let appliesInitially = true;
                        
                        if (json.data.DescuentoBase_Condicion === 'VENCIMIENTO') {
                            const pmFechaInput = row.querySelector('.pm-fecha');
                            const pagoDateStrDB = pmFechaInput ? pmFechaInput.value : new Date().toISOString().split('T')[0];
                            const partsP = pagoDateStrDB.split('T')[0].split('-');
                            let pd = new Date(partsP[0], partsP[1] - 1, partsP[2]);

                            const vDateStrDB = json.data.FechaVSaint || json.data.FechaV_Calculada;
                            const partsV = vDateStrDB.split('T')[0].split('-');
                            let vd = new Date(partsV[0], partsV[1] - 1, partsV[2]);

                            pd.setHours(0,0,0,0); vd.setHours(0,0,0,0);
                            if (pd > vd) appliesInitially = false;
                        }
                        
                        cbDB.checked = appliesInitially;
                        if (pctTxtDB) {
                            pctTxtDB.value = dbPct;
                            pctTxtDB.readOnly = !appliesInitially;
                        }
                        if (dedDB) {
                            dedDB.disabled = !appliesInitially;
                            if (appliesInitially) {
                                dedDB.checked = json.data.DescuentoBase_DeduceIVA !== false && json.data.DescuentoBase_DeduceIVA !== 0 && json.data.DescuentoBase_DeduceIVA !== '0';
                            }
                        }
                    }
                    if (json.data) {
                        const pagoDateStrRaw = row.querySelector('.pm-fecha')?.value || new Date().toISOString().split('T')[0];
                        const partsP2 = pagoDateStrRaw.split('T')[0].split('-');
                        const pagoDate = new Date(partsP2[0], partsP2[1] - 1, partsP2[2]);

                        const partsNI = json.data.FechaNI_Calculada.split('T')[0].split('-');
                        const niDate = new Date(partsNI[0], partsNI[1] - 1, partsNI[2]);
                        pagoDate.setHours(0,0,0,0);
                        niDate.setHours(0,0,0,0);
                        row.querySelector('.pm-indexado').checked = pagoDate > niDate;
                        if(row.querySelector('.pm-indexado-iva')) {
                            row.querySelector('.pm-indexado-iva').checked = json.data.IndexaIVA !== false;
                        }
                    }

                    await pmFetchRate(row);

                    // Pre-load saved ISLR concept from localStorage
                    const savedIslrRate = localStorage.getItem(`islr_${item.NumeroD}`);
                    if (savedIslrRate) {
                        const islrInput = row.querySelector('.pm-islr-concept');
                        if (islrInput) {
                            islrInput.value = savedIslrRate;
                            pmCalcRow(row);
                        }
                    }
                } catch (e) { console.error(e); }
            }
            pmRecalcTotals();

            // Render Histories
            const container = document.getElementById('pmHistorialContainer');
            if(container) {
                container.innerHTML = '';
                const tipoBadge = (tipo, afectaSaldo) => {
                    if (tipo === 'DESCUENTO') return '<span class="status-badge" style="background:rgba(234,179,8,0.15);color:#fbbf24;">Descuento</span>';
                    if (tipo === 'AJUSTE')    return '<span class="status-badge" style="background:rgba(168,85,247,0.15);color:#d8b4fe;">Ajuste</span>';
                    const map = {
                        'PAGO_MANUAL':     '<span class="status-badge status-paid">Pago</span>',
                        'PAGO':            '<span class="status-badge status-paid">Pago</span>',
                        'RETENCION_IVA':   '<span class="status-badge" style="background:rgba(139,92,246,0.15);color:#a78bfa;">Ret. IVA</span>',
                        'RETENCION_ISLR':  '<span class="status-badge" style="background:rgba(239,68,68,0.15);color:#f87171;">Ret. ISLR</span>',
                        'NOTA_CREDITO':    '<span class="status-badge" style="background:rgba(59,130,246,0.15);color:#60a5fa;">N/C</span>',
                        'NOTA_DEBITO':     '<span class="status-badge" style="background:rgba(239,68,68,0.15);color:#f87171;">N/D</span>',
                    };
                    return map[tipo] || `<span class="status-badge">${tipo || 'Pago'}</span>`;
                };

                items.forEach(item => {
                    const rKey = window.getItemKey(item);
                    const d = pmCxpStatuses[rKey];
                    if (!d) return;

                    let historyRows = `<tr><td colspan="8" style="text-align: center; color: var(--text-secondary);">No hay abonos registrados.</td></tr>`;
                    
                    if (d.HistorialAbonos && d.HistorialAbonos.length > 0) {
                        historyRows = d.HistorialAbonos.map(a => {
                            const esDescuento = a.TipoAbono === 'DESCUENTO';
                            const rowStyle = esDescuento ? 'opacity:0.75; font-style:italic;' : '';
                            const displayRef = a.DescripcionAjuste || a.Referencia || '-';
                            const displayMonto = esDescuento
                                ? `<span style="color:var(--warning, #fbbf24);">${formatBs(a.MontoBsAbonado)}</span>`
                                : `${formatBs(a.MontoBsAbonado)}`;
                            const displayUsd  = esDescuento
                                ? `<span style="color:var(--warning, #fbbf24);">${usdFormatter(a.MontoUsdAbonado)}</span>`
                                : `${usdFormatter(a.MontoUsdAbonado)}`;
                            const canDelete = !['RETENCION_IVA', 'RETENCION_ISLR', 'NOTA_CREDITO', 'DESCUENTO'].includes(a.TipoAbono);
                            return `
                            <tr style="${rowStyle}">
                                <td>${formatDate(a.FechaAbono)}</td>
                                <td>${tipoBadge(a.TipoAbono, a.AfectaSaldo)}</td>
                                <td class="amount">${displayMonto}</td>
                                <td>${bsFormatter(a.TasaCambioDiaAbono)}</td>
                                <td>${a.AplicaIndexacion ? '<span class="status-badge status-overdue">Sí</span>' : '<span class="status-badge status-paid">No</span>'}</td>
                                <td class="amount us-amount">${displayUsd}</td>
                                <td>${displayRef}</td>
                                <td style="text-align:center;">
                                    ${canDelete ? `<button type="button" class="btn-icon" title="Anular Abono" onclick="anularAbonoCxp(${a.AbonoID}, '${d.CodProv}', '${d.NumeroD}')"><i data-lucide="trash-2" style="color:var(--danger);width:16px;"></i></button>` : `<span style="font-size:0.75rem;color:var(--text-secondary)" title="Registro automático">Auto.</span>`}
                                </td>
                            </tr>`;
                        }).join('');
                    }

                    const blockHtml = `
                    <div style="margin-bottom: 1.5rem; background: rgba(0,0,0,0.15); padding: 1rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
                            <h4 style="margin: 0; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem;">
                                <i data-lucide="history" size="18"></i> Histórico Factura
                                <span style="background: rgba(239,68,68,0.1); color: #ef4444; border: 1px solid rgba(239,68,68,0.3); padding: 2px 8px; border-radius: 4px; font-weight: 600; font-family: monospace;">${d.NumeroD}</span>
                            </h4>
                        </div>
                        <div class="table-responsive">
                            <table style="width: 100%; margin: 0; font-size: 0.85rem;">
                                <thead>
                                    <tr>
                                        <th>Fecha</th>
                                        <th>Tipo</th>
                                        <th class="amount">Monto Bs</th>
                                        <th>Tasa C.</th>
                                        <th>Indexado</th>
                                        <th class="amount">Amortizado USD</th>
                                        <th>Referencia</th>
                                        <th style="text-align:center;">Acción</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${historyRows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    `;
                    container.insertAdjacentHTML('beforeend', blockHtml);
                });
                lucide.createIcons();
            }

            // Sync master checkbox state with the first row (since mostly providers share the same setting)
            const firstCb = tbody.querySelector('.pm-indexado');
            const masterCb = document.getElementById('pmIndexadoMaster');
            if (firstCb && masterCb) {
                masterCb.checked = firstCb.checked;
            }

            const firstIvaCb = tbody.querySelector('.pm-indexado-iva');
            const masterIvaCb = document.getElementById('pmIndexaIVAMaster');
            if (firstIvaCb && masterIvaCb) {
                masterIvaCb.checked = firstIvaCb.checked;
            }
        });

        // ── Submit ──────────────────────────────────────────────────────
        pmForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (pmItems.length === 0) return;

            const btn = e.target.querySelector('button[type="submit"]');
            btn.innerHTML = '<div class="loader" style="width:16px;height:16px;border-width:2px;"></div> Procesando...';
            btn.disabled = true;

            const referencia = document.getElementById('pmReferencia').value;
            const notificar  = document.getElementById('pmNotificarCorreo')?.checked || false;
            const fileInput  = document.getElementById('pmComprobante');

            const pagos = [];
            let showAlert10Pct = false;
            document.querySelectorAll('#pmInvoicesTable tr').forEach(row => {
                const nD      = row.dataset.nrounico;
                const rKey    = row.dataset.rowkey;
                const codProv = row.dataset.codprov;
                const cxp     = pmCxpStatuses[rKey];
                const indexado = row.querySelector('.pm-indexado')?.checked;
                const tasa     = parseFloat(row.querySelector('.pm-tasa')?.value) || 0;
                const montoBs  = parseFloat(row.querySelector('.pm-monto-bs')?.value) || 0;
                const montoUsd = parseFloat(row.querySelector('.pm-monto-usd')?.textContent.replace(/[^0-9.-]+/g,"")) || 0;

                const checkAjuste = document.getElementById('pmPermitirAjuste');
                const isAjusteActivo = checkAjuste && checkAjuste.checked;

                // Ignore rows with NO payment AND NO adjustment requested
                if (montoBs <= 0 && !isAjusteActivo) return;

                const rawNumeroD = row.dataset.numerod;
                
                // Phase 14: Calculate Discounts for Batch (Feature Parity)
                let montoDescBs = 0;
                let montoDescBaseBs = 0;
                let motivoDescID = null;

                if (cxp) {
                    const pctDesc = row.querySelector('.pm-pronto-pago')?.checked ? (parseFloat(row.querySelector('.pm-desc')?.value) || 0) : 0;
                    const descBasePct = pmGetDescBase(cxp, row);
                    
                    if (pctDesc > 0 || descBasePct > 0) {
                        const finParams = {
                            tasaDia: tasa || cxp.TasaEmision || 1,
                            aplicaIndex: indexado,
                            aplicaIndexIva: row.querySelector('.pm-indexado-iva') !== null ? row.querySelector('.pm-indexado-iva').checked : (cxp.IndexaIVA ?? true),
                            islrRate: parseFloat(row.querySelector('.pm-islr-concept')?.value) || 0,
                            deduceIvaBase: pmGetDeduceIvaBase(cxp, row),
                            deduceIvaPP: pmGetDeduceIvaPP(cxp, pctDesc, row)
                        };
                        const f0 = calculateInvoiceFinancials(cxp, { ...finParams, pctDesc: 0, descBasePct: 0 });
                        const fB = calculateInvoiceFinancials(cxp, { ...finParams, pctDesc: 0, descBasePct: descBasePct });
                        const fA = calculateInvoiceFinancials(cxp, { ...finParams, pctDesc: pctDesc, descBasePct: descBasePct });
                        
                        montoDescBaseBs = +(f0.finalBs - fB.finalBs).toFixed(2);
                        montoDescBs = +(fB.finalBs - fA.finalBs).toFixed(2);
                        
                        if (montoDescBs > 0) {
                            const selMotivo = document.getElementById('pmMotivoAjuste');
                            const ppOpt = Array.from(selMotivo?.options || []).find(o => o.text.includes('100') || o.text.toLowerCase().includes('pronto pago'));
                            if (ppOpt) motivoDescID = ppOpt.value;
                        }
                    }
                }

                // Check if invoice is already fully paid
                if (cxp) {
                    let deudaReal = cxp.Saldo || 0;
                    if (deudaReal <= 0) {
                        showToast(`⚠️ Factura ${rawNumeroD} no presenta saldo. Ignorada en el pago.`, 'warning');
                        return;
                    }
                }
                
                // Calculate missing amount for this row
                let montoAjusteBs = 0;
                let finalMontoBs = montoBs;
                let finalMontoUsd = montoUsd;
                
                if (isAjusteActivo) {
                    if (cxp) {
                        let deudaReal = cxp.Saldo || 0;
                        
                        // Recalculate financial requirement including discounts
                        const finExigido = calculateInvoiceFinancials(cxp, {
                            tasaDia: tasa || cxp.TasaEmision || 1,
                            aplicaIndex: indexado,
                            aplicaIndexIva: row.querySelector('.pm-indexado-iva') !== null ? row.querySelector('.pm-indexado-iva').checked : (cxp.IndexaIVA ?? true),
                            pctDesc: row.querySelector('.pm-pronto-pago')?.checked ? (parseFloat(row.querySelector('.pm-desc')?.value) || 0) : 0,
                            descBasePct: pmGetDescBase(cxp, row),
                            islrRate: parseFloat(row.querySelector('.pm-islr-concept')?.value) || 0,
                            deduceIvaBase: pmGetDeduceIvaBase(cxp, row),
                            deduceIvaPP: pmGetDeduceIvaPP(cxp, row.querySelector('.pm-pronto-pago')?.checked ? (parseFloat(row.querySelector('.pm-desc')?.value) || 0) : 0, row)
                        });

                        const deudaExigidaHoy = finExigido.finalBs;

                        // Universal Auto-split overpayment shield (protect ERP balances)
                        if (montoBs > deudaReal && deudaReal > 0) {
                            montoAjusteBs = +(montoBs - deudaReal).toFixed(2);
                            finalMontoBs = deudaReal;
                            const tasaAplicada = tasa || cxp.TasaEmision || 1;
                            finalMontoUsd = +(finalMontoBs / tasaAplicada).toFixed(2);
                        } else {
                            // Waterfall-to-Adjustment: If we paid less than the exiged amount, we adjust the difference
                            const dif = +(deudaExigidaHoy - montoBs).toFixed(2);
                            if (dif > 0) {
                                montoAjusteBs = dif;
                                if (dif > (deudaExigidaHoy * 0.10)) {
                                    showAlert10Pct = true;
                                }
                            }
                        }
                    }
                }

                pagos.push({
                    NroUnico: nD,
                    NumeroD: rawNumeroD,
                    CodProv: codProv,
                    FechaAbono: row.querySelector('.pm-fecha')?.value,
                    MontoBsAbonado: finalMontoBs,
                    MontoAjusteBs: montoAjusteBs,
                    MotivoAjusteID: document.getElementById('pmMotivoAjuste')?.value || null,
                    MontoDescuentoBs: montoDescBs,
                    MotivoDescuentoID: motivoDescID,
                    MontoDescuentoBaseBs: montoDescBaseBs,
                    TasaCambioDiaAbono: indexado ? tasa : (cxp?.TasaEmision || 0),
                    MontoUsdAbonado: finalMontoUsd,
                    AplicaIndexacion: indexado || false,
                    Referencia: referencia
                });

            });

            if (pagos.length === 0) {
                showToast('❌ No hay pagos válidos mayores a 0.00 para procesar.', 'warning');
                btn.innerHTML = '<i data-lucide="check-circle"></i> Procesar Pagos';
                btn.disabled = false;
                lucide.createIcons();
                return;
            }

            const formData = new FormData();
            formData.append('pagos_json', JSON.stringify(pagos));
            formData.append('NotificarCorreo', notificar);
            formData.append('MontoTotalPagado', parseFloat(document.getElementById('pmMontoTotalReal')?.value) || 0);
            if (fileInput && fileInput.files.length > 0) {
                Array.from(fileInput.files).forEach(f => formData.append('archivos', f));
            }
            try {
                const res = await fetch('/api/procurement/abonos-batch', { method: 'POST', body: formData });
                if (!res.ok) {
                    const errBody = await res.json();
                    throw new Error(errBody.detail || 'Error al procesar pagos');
                }
                const result = await res.json();
                showToast(`✅ ${result.count || pagos.length} pagos registrados exitosamente.`, 'success');

                lastProcessedPagos = pagos;
                const resendBtn = document.getElementById('btnPmResendEmail');
                if (resendBtn) resendBtn.disabled = false;

                if (window.multiPayMode) {
                    window.multiPaySelection.clear();
                    window.multiPaySelectionData.clear();
                }
                if (typeof fetchData === 'function') fetchData();
            } catch (err) {
                console.error(err);
                showToast(`❌ ${err.message}`, 'error');
            }

            btn.innerHTML = '<i data-lucide="check-circle"></i> Procesar Pagos';
            btn.disabled = false;
            lucide.createIcons();
        });

        // ── Re-enviar correo ────────────────────────────────────────────
        document.getElementById('btnPmResendEmail')?.addEventListener('click', async () => {
            if (!lastProcessedPagos.length) return;
            const btn = document.getElementById('btnPmResendEmail');
            btn.disabled = true;
            btn.innerHTML = '<div class="loader" style="width:14px;height:14px;border-width:2px;"></div> Enviando...';
            try {
                const fileInput = document.getElementById('pmComprobante');
                const fd = new FormData();
                fd.append('pagos_json', JSON.stringify(lastProcessedPagos));
                if (fileInput && fileInput.files.length > 0) {
                    Array.from(fileInput.files).forEach(f => fd.append('archivos', f));
                }
                const res = await fetch('/api/procurement/send-email-batch', { method: 'POST', body: fd });
                const json = await res.json();
                if (json.email_sent !== false) {
                    showToast('✅ Correo re-enviado exitosamente.', 'success');
                } else {
                    showToast(`⚠️ ${json.message || 'No se pudo enviar el correo.'}`, 'warning');
                }
            } catch (err) {
                showToast('❌ Error al re-enviar el correo.', 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i data-lucide="send"></i> Re-enviar correo';
                lucide.createIcons();
            }
        });
    }

    // ==========================================
    // RETENCIONES IVA MODULE
    // ==========================================

    const retencionesView = document.getElementById('view-retenciones');

    if (retencionesView) {
        // fetchRetenciones y manejo de filtros han sido delegados a modules-report.js

        // Enviar Retención por Email
        window.enviarRetencionEmail = async (id) => {
            if (!confirm('¿Enviar comprobante de retención por correo al proveedor?')) return;
            showToast('Enviando correo...', 'info');
            try {
                const res = await fetch(`/api/retenciones/${id}/send-email`, { method: 'POST' });
                const json = await res.json();
                if (json.email_sent) {
                    showToast(`✅ ${json.message}`, 'success');
                } else {
                    showToast(`⚠️ ${json.message}`, 'warning');
                }
            } catch (e) {
                console.error(e);
                showToast('❌ Error al enviar correo de retención.', 'error');
            }
        };

        // Anular
        window.anularRetencion = async (id) => {
            if (!confirm('¿Seguro que desea anular esta retención de IVA? No se podrá revertir.')) return;
            try {
                const res = await fetch(`/api/retenciones/${id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ estatus: 'ANULADO' })
                });
                if (!res.ok) throw new Error('No se pudo anular');
                showToast('Retención anulada correctamente.', 'success');
                if (typeof window._fetchRetenciones === 'function') window._fetchRetenciones();
            } catch (e) {
                console.error(e);
                showToast('Error al anular la retención. Posiblemente ya está enterada al SENIAT.', 'error');
            }
        };

        // Text Export
        document.getElementById('exportRetencionesTxtBtn')?.addEventListener('click', async () => {
            if (!confirm('Esta acción exportará las retenciones EMITIDAS y las marcará como ENTERADAS (listas para declarar). ¿Desea continuar?')) return;
            try {
                const desde = getDateValue(document.getElementById('retencionesDesde'));
                const hasta = getDateValue(document.getElementById('retencionesHasta'));
                let url = '/api/retenciones/export-txt';
                const params = new URLSearchParams();
                if (desde) params.append('desde', desde);
                if (hasta) params.append('hasta', hasta);
                if (params.toString()) url += '?' + params.toString();

                window.location.href = url;
                setTimeout(() => { if (typeof window._fetchRetenciones === 'function') window._fetchRetenciones(); }, 2500); // refresh layout
            } catch (e) {
                console.error(e);
                showToast('Error en la exportación', 'error');
            }
        });

        // Config Modal
        const retConfigModal = document.getElementById('retConfigModal');
        const retConfigForm = document.getElementById('retConfigForm');

        window.openRetConfigModal = async () => {
            forceShowModal(retConfigModal);
            if (typeof switchSettingsTab === 'function') switchSettingsTab('financiero');
            try {
                const res = await fetch('/api/retenciones/config');
                const { data } = await res.json();
                document.getElementById('cfgRifAgente').value = data.RifAgente || '';
                document.getElementById('cfgNombreAgente').value = data.NombreAgente || '';
                document.getElementById('cfgDireccionAgente').value = data.DireccionAgente || '';
                document.getElementById('cfgValorUT').value = data.ValorUT || 0;
                document.getElementById('cfgProximoSecuencial').value = data.ProximoSecuencial || 1;
                document.getElementById('cfgTasaEmisionSource').value = data.TasaEmisionSource || 'SACOMP';
                document.getElementById('cfgMontoUsdSource').value = data.MontoUSDSource || 'Calculado';
                if (document.getElementById('cfgISLRPersonaSource')) {
                    document.getElementById('cfgISLRPersonaSource').value = window.globalRetConfig?.ISLRPersonaSource || 'SAINT';
                }
                if (document.getElementById('cfgAntigravityFlow')) {
                    document.getElementById('cfgAntigravityFlow').value = window.globalRetConfig?.AntigravityFlow || 90;
                }
                if (document.getElementById('cfgAntigravityWacc')) {
                    document.getElementById('cfgAntigravityWacc').value = window.globalRetConfig?.AntigravityWacc || 12;
                }
                if (document.getElementById('cfgAntigravityMaxCredit')) {
                    document.getElementById('cfgAntigravityMaxCredit').value = window.globalRetConfig?.AntigravityMaxCredit || 0;
                }
                if (document.getElementById('cfgAntigravityMaxCreditMod')) {
                    document.getElementById('cfgAntigravityMaxCreditMod').value = window.globalRetConfig?.AntigravityMaxCreditMod || 0;
                }
                if (document.getElementById('cfgAntigravityMaxCreditAgr')) {
                    document.getElementById('cfgAntigravityMaxCreditAgr').value = window.globalRetConfig?.AntigravityMaxCreditAgr || 0;
                }
                if (document.getElementById('cfgAntigravityLoanDays')) {
                    document.getElementById('cfgAntigravityLoanDays').value = window.globalRetConfig?.AntigravityLoanDays || 30;
                }
                if (document.getElementById('cfgAntigravityLoanRate')) {
                    document.getElementById('cfgAntigravityLoanRate').value = window.globalRetConfig?.AntigravityLoanRate || 18;
                }
                loadMotivosConfig();
            } catch (e) {
                console.error('Error fetching config', e);
            }
        };

        document.getElementById('configRetencionesBtn')?.addEventListener('click', openRetConfigModal);

        window.switchSettingsTab = (tabId) => {
            document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.settings-pane').forEach(p => p.classList.remove('active'));
            document.querySelector(`.settings-tab[onclick*="${tabId}"]`)?.classList.add('active');
            document.getElementById(`pane-${tabId}`)?.classList.add('active');
        };

        window.loadMotivosConfig = async () => {
            const tbody = document.getElementById('motivosConfigTableBody');
            if (!tbody) return;
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Cargando...</td></tr>';
            try {
                const res = await fetch('/api/procurement/motivos-ajuste?solo_activos=false');
                const { data } = await res.json();
                window.allMotivosConfig = data; // Store globally for editing
                tbody.innerHTML = data.map((m, idx) => `
                    <tr style="opacity: ${m.Activo ? '1' : '0.5'};">
                        <td>${m.Codigo}</td>
                        <td>${m.Descripcion} ${m.Activo ? '' : '(Inactivo)'}</td>
                        <td style="text-align:center;">
                            <button class="btn-icon" title="${m.EmailTemplate || 'Sin plantilla configurada'}" style="color: ${m.EmailTemplate ? 'var(--primary-accent)' : 'var(--text-secondary)'};">
                                <i data-lucide="${m.EmailTemplate ? 'message-circle' : 'message-circle-off'}" style="width:16px;height:16px;"></i>
                            </button>
                        </td>
                        <td style="text-align:center;">${m.ParaAjuste ? '✅' : '—'}</td>
                        <td style="text-align:center;">${m.ParaNotaCredito ? '✅' : '—'}</td>
                        <td style="text-align:center;">
                            <div style="display:flex; gap:0.5rem; justify-content:center;">
                                <button class="btn-icon" onclick="editMotivoConfig(${idx})" style="color:var(--primary-accent);" title="Editar"><i data-lucide="pencil" style="width:16px;height:16px;"></i></button>
                                ${m.Activo ? `<button class="btn-icon" onclick="deleteMotivoConfig(${m.MotivoID})" style="color:var(--danger);" title="Desactivar"><i data-lucide="trash-2" style="width:16px;height:16px;"></i></button>` : ''}
                            </div>
                        </td>
                    </tr>
                `).join('');
                if (data.length === 0) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No hay motivos configurados.</td></tr>';
                if (window.lucide) lucide.createIcons();
            } catch (err) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:red;">Error al cargar.</td></tr>';
            }
        };

        window.editMotivoConfig = (index) => {
            const m = window.allMotivosConfig[index];
            if (!m) return;
            document.getElementById('newMcCodigo').value = m.Codigo;
            document.getElementById('newMcCodigo').readOnly = true;
            document.getElementById('newMcDesc').value = m.Descripcion;
            document.getElementById('newMcAjuste').checked = m.ParaAjuste;
            document.getElementById('newMcNC').checked = m.ParaNotaCredito;
            document.getElementById('newMcEmailTemplate').value = m.EmailTemplate || '';
            document.getElementById('addMotivoForm').dataset.motivoId = m.MotivoID; // Store ID for update
            
            const btnSave = document.getElementById('btnSaveMotivo');
            if(btnSave) {
                btnSave.innerHTML = '<i data-lucide="check"></i> Actualizar';
                btnSave.classList.replace('btn-primary', 'btn-success'); 
            }
            document.getElementById('btnCancelEditMotivo').style.display = 'inline-flex';
            if (window.lucide) lucide.createIcons();
            document.getElementById('newMcDesc').focus();
        };

        window.resetMotivoForm = () => {
            const form = document.getElementById('addMotivoForm');
            if (form) {
                form.reset();
                delete form.dataset.motivoId;
            }
            document.getElementById('newMcCodigo').readOnly = false;
            document.getElementById('newMcAjuste').checked = true;
            const btnSave = document.getElementById('btnSaveMotivo');
            if(btnSave) {
                btnSave.innerHTML = '<i data-lucide="plus"></i>';
                btnSave.classList.remove('btn-success');
                btnSave.classList.add('btn-primary');
            }
            document.getElementById('btnCancelEditMotivo').style.display = 'none';
            if (window.lucide) lucide.createIcons();
        };

        document.getElementById('addMotivoForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('btnSaveMotivo');
            const orig = btn.innerHTML;
            btn.innerHTML = '<i class="loader" style="width:14px;height:14px;"></i>';
            btn.disabled = true;

            const form = document.getElementById('addMotivoForm');
            const payload = {
                MotivoID: form.dataset.motivoId || null,
                Codigo: document.getElementById('newMcCodigo').value,
                Descripcion: document.getElementById('newMcDesc').value,
                ParaAjuste: document.getElementById('newMcAjuste').checked,
                ParaNotaCredito: document.getElementById('newMcNC').checked,
                EmailTemplate: document.getElementById('newMcEmailTemplate')?.value || '',
                Activo: true
            };
            try {
                const res = await fetch('/api/procurement/motivos-ajuste', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
                });
                if(!res.ok) throw new Error("Error al guardar motivo");
                showToast('✅ Motivo configurado correctamente.', 'success');
                resetMotivoForm();
                loadMotivosConfig();
            } catch (err) { 
                showToast(err.message, 'error'); 
            } finally {
                btn.innerHTML = orig;
                btn.disabled = false;
                if(window.lucide) lucide.createIcons();
            }
        });

        window.deleteMotivoConfig = async (id) => {
            if (!confirm('¿Desactivar este motivo?')) return;
            try {
                await fetch(`/api/procurement/motivos-ajuste/${id}`, { method: 'DELETE' });
                loadMotivosConfig();
            } catch (err) { showToast('Error al desactivar', 'error'); }
        };

        window.closeRetConfigModal = () => forceHideModal(retConfigModal);

        retConfigForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button[type="submit"]');
            btn.innerHTML = '<i class="loader" style="width:14px;height:14px;"></i>';
            btn.disabled = true;

            const payload = {
                RifAgente: document.getElementById('cfgRifAgente').value,
                NombreAgente: document.getElementById('cfgNombreAgente').value,
                DireccionAgente: document.getElementById('cfgDireccionAgente').value,
                ValorUT: parseFloat(document.getElementById('cfgValorUT').value) || 0,
                ProximoSecuencial: parseInt(document.getElementById('cfgProximoSecuencial').value) || 1,
                TasaEmisionSource: document.getElementById('cfgTasaEmisionSource').value,
                MontoUsdSource: document.getElementById('cfgMontoUsdSource').value
            };
            // Save ISLRPersonaSource and ToleranceSaldo to Procurement.Settings
            const islrSrc = document.getElementById('cfgISLRPersonaSource')?.value;
            const toleranceVal = document.getElementById('cfgToleranceSaldo')?.value;
            const antigravityFlow = document.getElementById('cfgAntigravityFlow')?.value;
            const antigravityWacc = document.getElementById('cfgAntigravityWacc')?.value;
            const antigravityMaxCredit = document.getElementById('cfgAntigravityMaxCredit')?.value;
            const antigravityMaxCreditMod = document.getElementById('cfgAntigravityMaxCreditMod')?.value;
            const antigravityMaxCreditAgr = document.getElementById('cfgAntigravityMaxCreditAgr')?.value;
            const antigravityLoanDays = document.getElementById('cfgAntigravityLoanDays')?.value;
            const antigravityLoanRate = document.getElementById('cfgAntigravityLoanRate')?.value;
            
            if (islrSrc || toleranceVal || antigravityFlow || antigravityWacc || antigravityMaxCredit) {
                const settingsPayload = {};
                if (islrSrc) settingsPayload.ISLRPersonaSource = islrSrc;
                if (toleranceVal) settingsPayload.ToleranceSaldo = toleranceVal;
                if (antigravityFlow) settingsPayload.AntigravityFlow = antigravityFlow;
                if (antigravityWacc) settingsPayload.AntigravityWacc = antigravityWacc;
                if (antigravityMaxCredit) settingsPayload.AntigravityMaxCredit = antigravityMaxCredit;
                if (antigravityMaxCreditMod) settingsPayload.AntigravityMaxCreditMod = antigravityMaxCreditMod;
                if (antigravityMaxCreditAgr) settingsPayload.AntigravityMaxCreditAgr = antigravityMaxCreditAgr;
                if (antigravityLoanDays) settingsPayload.AntigravityLoanDays = antigravityLoanDays;
                if (antigravityLoanRate) settingsPayload.AntigravityLoanRate = antigravityLoanRate;

                fetch('/api/procurement/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settingsPayload)
                }).then(() => { 
                    if (islrSrc) window.globalRetConfig.ISLRPersonaSource = islrSrc;
                    if (toleranceVal) window.globalRetConfig.ToleranceSaldo = toleranceVal;
                    if (antigravityFlow) window.globalRetConfig.AntigravityFlow = antigravityFlow;
                    if (antigravityWacc) window.globalRetConfig.AntigravityWacc = antigravityWacc;
                    if (antigravityMaxCredit) window.globalRetConfig.AntigravityMaxCredit = antigravityMaxCredit;
                    if (antigravityMaxCreditMod) window.globalRetConfig.AntigravityMaxCreditMod = antigravityMaxCreditMod;
                    if (antigravityMaxCreditAgr) window.globalRetConfig.AntigravityMaxCreditAgr = antigravityMaxCreditAgr;
                    if (antigravityLoanDays) window.globalRetConfig.AntigravityLoanDays = antigravityLoanDays;
                    if (antigravityLoanRate) window.globalRetConfig.AntigravityLoanRate = antigravityLoanRate;
                });
            }

            try {
                const res = await fetch('/api/retenciones/config', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) throw new Error('Error al guardar config');
                showToast('Configuración guardada exitosamente.', 'success');
                // Update global state immediately
                window.globalRetConfig.TasaEmisionSource = payload.TasaEmisionSource;
                window.globalRetConfig.MontoUsdSource = payload.MontoUsdSource;
                window.globalRetConfig.ValorUT = payload.ValorUT;
                closeRetConfigModal();
                // Re-render table if needed
                if (window.currentData.length > 0) renderTable(window.currentData);
            } catch (e) {
                console.error(e);
                showToast('Error al guardar.', 'error');
            } finally {
                btn.innerHTML = 'Guardar';
                btn.disabled = false;
            }
        });

        // Generar Retención (Multi-Factura)
        const generarRetencionModal = document.getElementById('generarRetencionModal');
        const generarRetencionForm = document.getElementById('generarRetencionForm');
        let currentRetencionItems = []; // Array of selected invoice items
        let configValUT = 0;

        const recalcAllRetenciones = () => {
            const retenPct = parseFloat(document.getElementById('genRetPctGaceta').value) || 0;
            let totalMonto = 0, totalBase = 0, totalIVA = 0, totalRetenido = 0;

            document.querySelectorAll('#genRetInvoicesTable tr').forEach((row, idx) => {
                const base = parseFloat(row.querySelector('.ret-base')?.value) || 0;
                const alicuota = parseFloat(row.querySelector('.ret-alicuota')?.value) || 0;
                const ivaCausado = roundFixed(base * (alicuota / 100));
                const retenido = roundFixed(ivaCausado * (retenPct / 100));
                const monto = parseFloat(row.querySelector('.ret-monto')?.textContent) || 0;

                row.querySelector('.ret-iva-display').textContent = ivaCausado.toFixed(2);
                row.querySelector('.ret-retenido-display').textContent = retenido.toFixed(2);

                totalMonto += monto;
                totalBase += base;
                totalIVA += ivaCausado;
                totalRetenido += retenido;
            });

            document.getElementById('genRetTotalMonto').textContent = totalMonto.toFixed(2);
            document.getElementById('genRetTotalBase').textContent = totalBase.toFixed(2);
            document.getElementById('genRetTotalIVA').textContent = totalIVA.toFixed(2);
            document.getElementById('genRetTotalRetenido').textContent = totalRetenido.toFixed(2);

            // UT Warning
            const warnBox = document.getElementById('retenWarningUT');
            if (configValUT > 0 && totalRetenido < (configValUT * 20)) {
                warnBox.style.display = 'block';
                warnBox.textContent = `Advertencia: El monto de retención (Bs. ${totalRetenido.toFixed(2)}) es menor a 20 Unidades Tributarias (Bs. ${(configValUT * 20).toFixed(2)}). Generalmente no se retiene.`;
            } else {
                warnBox.style.display = 'none';
            }
        };

        window.launchRetencionModal = async (itemsToRetain) => {
            if (!itemsToRetain || itemsToRetain.length === 0) return;

            const itemsConIva = itemsToRetain.filter(i => (parseFloat(i.TGravable) || 0) > 0 && (parseFloat(i.MtoTax) || 0) > 0);
            if (itemsConIva.length === 0) {
                showToast('⚠️ Ninguna de las facturas seleccionadas posee IVA para retener.', 'warning');
                return;
            }

            const yaRetenidas = itemsConIva.filter(i => (parseFloat(i.RetencionIvaAbonada) || 0) > 0 || hasRet(i));
            const sinRetencion = itemsConIva.filter(i => (parseFloat(i.RetencionIvaAbonada) || 0) === 0 && !hasRet(i));

            if (sinRetencion.length === 0) {
                showToast('⚠️ Todas las facturas seleccionadas ya tienen retención de IVA registrada.', 'info');
                return;
            }

            if (yaRetenidas.length > 0) {
                const retenidasNums = yaRetenidas.map(i => i.NumeroD).join(', ');
                const sinRetenNums = sinRetencion.map(i => i.NumeroD).join(', ');
                
                if (itemsConIva.length > 1) {
                    // Create a foreground alert overlay to prevent background hiding issues with native alert()
                    const overlay = document.createElement('div');
                    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.7);z-index:9999999;display:flex;align-items:center;justify-content:center;';
                    overlay.innerHTML = `
                        <div style="background:#1e293b;border:1px solid #f59e0b;padding:2rem;border-radius:8px;max-width:500px;color:white;text-align:center;box-shadow:0 10px 25px rgba(0,0,0,0.5);">
                            <h3 style="color:#f59e0b;margin-bottom:1rem;font-size:1.2rem;">⚠️ Aviso de Retención Parcial</h3>
                            <p style="margin-bottom:1rem;">Se procesará la retención <b>SOLO</b> para:<br><span style="color:#10b981;">${sinRetenNums}</span></p>
                            <p style="margin-bottom:1.5rem;">Las facturas <span style="color:#ef4444;">[${retenidasNums}]</span> ya poseen retención de IVA registrada y serán omitidas.</p>
                            <button onclick="this.parentElement.parentElement.remove()" style="background:#3b82f6;color:white;border:none;padding:0.5rem 1.5rem;border-radius:4px;cursor:pointer;font-weight:600;">Entendido</button>
                        </div>
                    `;
                    document.body.appendChild(overlay);
                }
            }

            itemsToRetain = sinRetencion;

            // Validate: all same provider
            const provs = new Set(itemsToRetain.map(i => i.CodProv));
            if (provs.size > 1) {
                showToast('⚠️ Para generar una retención agrupada, todas las facturas deben ser del mismo proveedor.', 'warning');
                return;
            }

            // Fetch config for UT warning
            try {
                const resConf = await fetch('/api/retenciones/config');
                const confData = await resConf.json();
                configValUT = confData.data?.ValorUT || 0;
            } catch(e) {}

            currentRetencionItems = itemsToRetain;
            document.getElementById('genRetCodProv').value = itemsToRetain[0].CodProv;
            document.getElementById('genRetFechaEmision').value = new Date().toISOString().split('T')[0];
            
            let provPctRaw = itemsToRetain[0].PorctRet;
            let provPct = parseFloat(provPctRaw);
            if (isNaN(provPct)) {
                provPct = 75;
            }
            console.log(`[CXP] Auto-loading IVA retention \% for provider ${itemsToRetain[0].CodProv}. Raw API value:`, provPctRaw, 'Parsed:', provPct);
            const validPcts = ['0', '75', '100'];
            document.getElementById('genRetPctGaceta').value = validPcts.includes(String(provPct)) ? String(provPct) : (provPct >= 100 ? '100' : '75');

            // Build invoice rows
            const tbody = document.getElementById('genRetInvoicesTable');
            tbody.innerHTML = itemsToRetain.map((item, idx) => {
                const monto = parseFloat(item.Monto) || 0;
                // Base should correctly be TGravable, not the entire Monto
                const base = parseFloat(item.TGravable) || 0;
                let alicuota = 16;
                if (base > 0 && item.MtoTax > 0) {
                    const explicitAlicuota = (parseFloat(item.MtoTax) / base) * 100;
                    if (Math.abs(explicitAlicuota - 16) > 0.1 && Math.abs(explicitAlicuota - 8) < 0.1) {
                        alicuota = 8;
                    }
                }
                
                return `
                    <tr>
                        <td>${item.NumeroD}</td>
                        <td><input type="text" class="form-control ret-nrocontrol" value="${item.NroCtrol || ''}" style="width:100px;padding:0.3rem;font-size:0.8rem;"></td>
                        <td class="amount ret-monto">${monto.toFixed(2)}</td>
                        <td><input type="number" class="form-control ret-base" value="${base.toFixed(2)}" step="0.01" style="width:90px;padding:0.3rem;font-size:0.8rem;"></td>
                        <td><input type="number" class="form-control ret-alicuota" value="${alicuota}" step="0.01" style="width:55px;padding:0.3rem;font-size:0.8rem;"></td>
                        <td class="amount ret-iva-display">${(base * alicuota / 100).toFixed(2)}</td>
                        <td class="amount ret-retenido-display" style="font-weight:bold;color:var(--warning);">0.00</td>
                    </tr>
                `;
            }).join('');

            // Attach recalc listeners to editable inputs
            tbody.querySelectorAll('.ret-base, .ret-alicuota').forEach(inp => {
                inp.addEventListener('input', recalcAllRetenciones);
            });

            forceShowModal(generarRetencionModal);
            if(window.lucide) window.lucide.createIcons();
            recalcAllRetenciones();
        };

        document.getElementById('btnGenerarRetencion')?.addEventListener('click', async () => {
            const checked = document.querySelectorAll('.row-checkbox:checked');
            if (checked.length < 1) return;

            // Gather all selected items
            const items = [];
            checked.forEach(cb => {
                const nroUnico = parseInt(cb.getAttribute('data-nrounico'));
                const item = window.currentData.find(d => d.NroUnico === nroUnico);
                if (item) items.push(item);
            });
            if (items.length > 0) {
                window.launchRetencionModal(items);
            }
        });

        document.getElementById('genRetPctGaceta')?.addEventListener('change', recalcAllRetenciones);

        window.closeGenerarRetencionModal = () => {
            forceHideModal(generarRetencionModal);
            if (window._pendingAbonosReturn) {
                const { codProv, numeroD } = window._pendingAbonosReturn;
                window._pendingAbonosReturn = null;
                setTimeout(() => {
                    if (typeof openAbonosPanel === 'function') openAbonosPanel(codProv, numeroD);
                }, 100);
            }
        };

        let isGeneratingRetencion = false;
        generarRetencionForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (isGeneratingRetencion) return;
            if (currentRetencionItems.length === 0) return;
            isGeneratingRetencion = true;

            const btn = e.target.querySelector('button[type="submit"]');
            btn.innerHTML = '<i class="loader" style="width:14px;height:14px;"></i>';
            btn.disabled = true;

            const retenPct = parseFloat(document.getElementById('genRetPctGaceta').value) || 0;
            const fechaRetencion = document.getElementById('genRetFechaEmision').value;

            // Build facturas array from the table rows
            const rows = document.querySelectorAll('#genRetInvoicesTable tr');
            const facturas = [];
            rows.forEach((row, idx) => {
                const item = currentRetencionItems[idx];
                const base = parseFloat(row.querySelector('.ret-base')?.value) || 0;
                const alicuota = parseFloat(row.querySelector('.ret-alicuota')?.value) || 0;
                const ivaCausado = base * (alicuota / 100);
                const montoRetenido = ivaCausado * (retenPct / 100);
                const monto = parseFloat(row.querySelector('.ret-monto')?.textContent) || 0;
                const nroControl = row.querySelector('.ret-nrocontrol')?.value || '';

                facturas.push({
                    NumeroD: item.NumeroD,
                    CodProv: item.CodProv,
                    FechaFactura: item.FechaE || fechaRetencion,
                    NroControl: nroControl,
                    MontoTotal: monto,
                    BaseImponible: base,
                    MontoExento: Math.max(0, roundFixed(monto - base - ivaCausado)),
                    Alicuota: alicuota,
                    IVACausado: ivaCausado,
                    PorcentajeRetencion: retenPct,
                    MontoRetenido: montoRetenido
                });
            });

            try {
                const res = await fetch('/api/retenciones', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ FechaRetencion: fechaRetencion, facturas })
                });
                if (!res.ok) {
                    const errorJson = await res.json();
                    throw new Error(errorJson.detail || 'Error al generar retención');
                }
                const result = await res.json();
                showToast(`✅ Retención generada. Comprobante Nro: ${result.NumeroComprobante} (${facturas.length} factura${facturas.length > 1 ? 's' : ''})`, 'success');
                
                const pmModal = document.getElementById('pagoMultipleModal');
                if (pmModal && pmModal.classList.contains('active')) {
                    closeGenerarRetencionModal();
                    facturas.forEach(f => {
                        const it = currentRetencionItems.find(i => i.NumeroD === f.NumeroD);
                        if (it) {
                            it.HistorialAbonos = it.HistorialAbonos || [];
                            it.HistorialAbonos.push({ TipoAbono: 'RETENCION_IVA' });
                            
                            // Propagate to currentData so recalculations get the real value
                            it.RetencionIvaAbonada = (parseFloat(it.RetencionIvaAbonada) || 0) + parseFloat(f.MontoRetenido);
                            
                            // Also update pmCxpStatuses which drives the UI rows
                            if (window.pmCxpStatuses && window.pmCalcRow) {
                                const rKey = Object.keys(window.pmCxpStatuses).find(k => window.pmCxpStatuses[k].NroUnico === it.NroUnico);
                                if (rKey) {
                                    window.pmCxpStatuses[rKey].HistorialAbonos = window.pmCxpStatuses[rKey].HistorialAbonos || [];
                                    window.pmCxpStatuses[rKey].HistorialAbonos.push({ TipoAbono: 'RETENCION_IVA' });
                                    window.pmCxpStatuses[rKey].RetencionIvaAbonada = it.RetencionIvaAbonada;
                                    
                                    // Re-trigger calculation to update row visually
                                    const row = document.querySelector(`.pm-table-row[data-rowkey="${rKey}"]`);
                                    if (row) window.pmCalcRow(row);
                                }
                            }
                        }
                    });
                    const btnPmRetIva = document.getElementById('pmGoBtnRetIva');
                    if (btnPmRetIva) {
                        btnPmRetIva.innerHTML = '<i data-lucide="file-check-2" size="16"></i> Ver Ret. IVA';
                        btnPmRetIva.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                        btnPmRetIva.style.color = '#10b981';
                        btnPmRetIva.style.background = 'rgba(16, 185, 129, 0.05)';
                        btnPmRetIva.dataset.yaCreada = 'true';
                        lucide.createIcons();
                    }
                } else {
                    if (window.multiPayMode) {
                        window.multiPaySelection.clear();
                        window.multiPaySelectionData.clear();
                    }
                    if (typeof fetchData === 'function') await fetchData();
                    closeGenerarRetencionModal();
                }
            } catch (e) {
                console.error(e);
                showToast(e.message, 'error');
            } finally {
                isGeneratingRetencion = false;
                btn.innerHTML = 'Generar Comprobante';
                btn.disabled = false;
            }
        });

        // Generar Retencion ISLR (Multi-Factura)
        const generarRetencionIslrModal = document.getElementById('generarRetencionIslrModal');
        const generarRetencionIslrForm = document.getElementById('generarRetencionIslrForm');
        let currentIslrItems = [];
        let configUt = 43.00;

        const recalcIslr = () => {
            let totalMonto = 0, totalBase = 0, totalSustraendo = 0, totalRetenido = 0;
            const conceptoValue = document.getElementById('genRetIslrConcepto').value;
            const alicuota = parseFloat(conceptoValue) || 0;

            document.querySelectorAll('#genRetIslrInvoicesTable tr').forEach(row => {
                const monto = parseFloat(row.querySelector('.ret-monto')?.textContent) || 0;
                const base = parseFloat(row.querySelector('.ret-base')?.value) || 0;
                row.querySelector('.ret-alicuota-display').textContent = (alicuota * 100).toFixed(2);

                const codProv = document.getElementById('genRetIslrCodProv').value;
                const provInfo = allProviders.find(p => p.CodProv === codProv);
                let tipoOverride = provInfo ? provInfo.TipoPersonaLocal : null;

                // Evaluate ISLR using identical logic as standard Calc
                const islrRetInfo = calcISLR(base, alicuota, codProv, tipoOverride);

                // Note: calcISLR currently returns only mathematically rounded retained amount.
                // We'll calculate sustraendo visually for the modal
                let sustraendo = 0;
                let retained = base * alicuota;
                
                // Redo internal logic to find if natural person
                let isNatural = false;
                if (tipoOverride === 'PJ') isNatural = false;
                else if (tipoOverride === 'PN') isNatural = true;
                else {
                    const firstChar = String(codProv).trim().toUpperCase().charAt(0);
                    isNatural = (firstChar === 'V' || firstChar === 'E' || firstChar === 'P');
                }

                if (isNatural) {
                    sustraendo = alicuota * configUt * 83.3334;
                    retained = Math.max(0, retained - sustraendo);
                }

                row.querySelector('.ret-sustraendo-display').textContent = sustraendo.toFixed(2);
                row.querySelector('.ret-retenido-display').textContent = retained.toFixed(2);

                totalMonto += monto;
                totalBase += base;
                totalSustraendo += sustraendo;
                totalRetenido += retained;
            });

            document.getElementById('genRetIslrTotalMonto').textContent = totalMonto.toFixed(2);
            document.getElementById('genRetIslrTotalBase').textContent = totalBase.toFixed(2);
            document.getElementById('genRetIslrTotalSustraendo').textContent = totalSustraendo.toFixed(2);
            document.getElementById('genRetIslrTotalRetenido').textContent = totalRetenido.toFixed(2);
        };

        window.launchRetencionIslrModal = async (itemsToRetain) => {
            if (!itemsToRetain || itemsToRetain.length === 0) return;

            const provs = new Set(itemsToRetain.map(i => i.CodProv));
            if (provs.size > 1) {
                showToast('⚠️ Facturas deben ser del mismo proveedor.', 'warning');
                return;
            }

            try {
                if (window.globalRetConfig && window.globalRetConfig.ValorUT) {
                    configUt = parseFloat(window.globalRetConfig.ValorUT);
                }
            } catch(e) {}

            currentIslrItems = itemsToRetain;
            document.getElementById('genRetIslrCodProv').value = itemsToRetain[0].CodProv;
            document.getElementById('genRetIslrFechaEmision').value = new Date().toISOString().split('T')[0];

            const tbody = document.getElementById('genRetIslrInvoicesTable');
            tbody.innerHTML = itemsToRetain.map((item) => {
                const monto = parseFloat(item.Monto) || 0;
                const base = parseFloat(item.TGravable) || 0;
                
                return `
                    <tr>
                        <td>${item.NumeroD}</td>
                        <td><input type="text" class="form-control ret-nrocontrol" value="${item.NroCtrol || ''}" style="width:100px;padding:0.3rem;font-size:0.8rem;"></td>
                        <td class="amount ret-monto">${monto.toFixed(2)}</td>
                        <td><input type="number" class="form-control ret-base" value="${base.toFixed(2)}" step="0.01" style="width:90px;padding:0.3rem;font-size:0.8rem;"></td>
                        <td class="amount ret-alicuota-display">2.00</td>
                        <td class="amount ret-sustraendo-display">0.00</td>
                        <td class="amount ret-retenido-display" style="font-weight:bold;color:var(--danger);">0.00</td>
                    </tr>
                `;
            }).join('');

            tbody.querySelectorAll('.ret-base').forEach(inp => inp.addEventListener('input', recalcIslr));
            forceShowModal(generarRetencionIslrModal);
            if(window.lucide) window.lucide.createIcons();
            recalcIslr();
        };

        document.getElementById('btnGenerarRetencionIslr')?.addEventListener('click', async () => {
            const checked = document.querySelectorAll('.row-checkbox:checked');
            if (checked.length < 1) return;

            const items = [];
            checked.forEach(cb => {
                const nroUnico = parseInt(cb.getAttribute('data-nrounico'));
                const item = window.currentData.find(d => d.NroUnico === nroUnico);
                if (item) items.push(item);
            });
            
            if (items.length > 0) {
                window.launchRetencionIslrModal(items);
            }
        });

        document.getElementById('genRetIslrConcepto')?.addEventListener('change', recalcIslr);
        window.closeGenerarRetencionIslrModal = () => {
            forceHideModal(generarRetencionIslrModal);
            if (window._pendingAbonosReturn) {
                const { codProv, numeroD } = window._pendingAbonosReturn;
                window._pendingAbonosReturn = null;
                setTimeout(() => {
                    if (typeof openAbonosPanel === 'function') openAbonosPanel(codProv, numeroD);
                }, 100);
            }
        };

        let isGeneratingRetencionIslr = false;
        generarRetencionIslrForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (isGeneratingRetencionIslr) return;
            if (currentIslrItems.length === 0) return;
            isGeneratingRetencionIslr = true;

            const btn = e.target.querySelector('button[type="submit"]');
            btn.innerHTML = '<i class="loader" style="width:14px;height:14px;"></i>';
            btn.disabled = true;

            const fechaRetencion = document.getElementById('genRetIslrFechaEmision').value;
            const selectEl = document.getElementById('genRetIslrConcepto');
            const conceptoValue = selectEl.value;
            const alicuotaPts = parseFloat(conceptoValue) * 100;
            const conceptoName = selectEl.options[selectEl.selectedIndex].text;

            const facturas = [];
            document.querySelectorAll('#genRetIslrInvoicesTable tr').forEach((row, idx) => {
                const item = currentIslrItems[idx];
                const base = parseFloat(row.querySelector('.ret-base')?.value) || 0;
                const sustraendo = parseFloat(row.querySelector('.ret-sustraendo-display')?.textContent) || 0;
                const retained = parseFloat(row.querySelector('.ret-retenido-display')?.textContent) || 0;
                const monto = parseFloat(row.querySelector('.ret-monto')?.textContent) || 0;
                const nroControl = row.querySelector('.ret-nrocontrol')?.value || '';

                facturas.push({
                    NumeroD: item.NumeroD,
                    CodProv: item.CodProv,
                    FechaFactura: item.FechaE || fechaRetencion,
                    NroCtrol: nroControl,
                    MontoTotalBs: monto,
                    BaseImponibleBs: base,
                    AlicuotaPct: alicuotaPts,
                    SustraendoBs: sustraendo,
                    MontoRetenido: retained,
                    ConceptoISLR: conceptoName
                });
            });

            try {
                const res = await fetch('/api/retenciones-islr', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ FechaRetencion: fechaRetencion, facturas })
                });
                if (!res.ok) {
                    const errorJson = await res.json();
                    throw new Error(errorJson.detail || 'Error al generar retención ISLR');
                }
                const result = await res.json();
                showToast(`✅ Retención ISLR generada. Comprobante Nro: ${result.NumeroComprobante}`, 'success');
                
                const pmModal = document.getElementById('pagoMultipleModal');
                if (pmModal && pmModal.classList.contains('active')) {
                    closeGenerarRetencionIslrModal();
                    facturas.forEach(f => {
                        const it = currentIslrItems.find(i => i.NumeroD === f.NumeroD);
                        if (it) {
                            it.HistorialAbonos = it.HistorialAbonos || [];
                            it.HistorialAbonos.push({ TipoAbono: 'RETENCION_ISLR' });
                            
                            // Propagate to currentData so recalculations get the real value
                            it.RetencionIslrAbonada = (parseFloat(it.RetencionIslrAbonada) || 0) + parseFloat(f.MontoRetenido);
                            
                            // Also update pmCxpStatuses which drives the UI rows
                            if (window.pmCxpStatuses && window.pmCalcRow) {
                                const rKey = Object.keys(window.pmCxpStatuses).find(k => window.pmCxpStatuses[k].NroUnico === it.NroUnico);
                                if (rKey) {
                                    window.pmCxpStatuses[rKey].HistorialAbonos = window.pmCxpStatuses[rKey].HistorialAbonos || [];
                                    window.pmCxpStatuses[rKey].HistorialAbonos.push({ TipoAbono: 'RETENCION_ISLR' });
                                    window.pmCxpStatuses[rKey].RetencionIslrAbonada = it.RetencionIslrAbonada;
                                    
                                    // Re-trigger calculation to update row visually
                                    const row = document.querySelector(`.pm-table-row[data-rowkey="${rKey}"]`);
                                    if (row) window.pmCalcRow(row);
                                }
                            }
                        }
                    });
                    const btnPmRetIslr = document.getElementById('pmGoBtnRetIslr');
                    if (btnPmRetIslr) {
                        btnPmRetIslr.innerHTML = '<i data-lucide="file-check-2" size="16"></i> Ver Ret. ISLR';
                        btnPmRetIslr.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                        btnPmRetIslr.style.color = '#10b981';
                        btnPmRetIslr.style.background = 'rgba(16, 185, 129, 0.05)';
                        btnPmRetIslr.dataset.yaCreada = 'true';
                        lucide.createIcons();
                    }
                } else {
                    if (window.multiPayMode) {
                        window.multiPaySelection.clear();
                        window.multiPaySelectionData.clear();
                    }
                    if (typeof fetchData === 'function') await fetchData();
                    closeGenerarRetencionIslrModal();
                }
            } catch (e) {
                console.error(e);
                showToast(e.message, 'error');
            } finally {
                isGeneratingRetencionIslr = false;
                btn.innerHTML = 'Generar Comprobante ISLR';
                btn.disabled = false;
            }
        });
        // Trigger fetchRetenciones when the view is opened via SPA routing link
        document.querySelector('.nav-item[data-view="retenciones"]')?.addEventListener('click', () => {
            if (typeof window._fetchRetenciones === 'function') window._fetchRetenciones();
        });
    }

    // --- Settings Logic ---
    const settingsFormElement = document.getElementById('globalSettingsForm');
    if (settingsFormElement) {
        settingsFormElement.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(settingsFormElement);
            const TasaEmisionSource = formData.get('TasaEmisionSource');
            const MontoUSDSource = formData.get('MontoUSDSource');
            const LimiteCarga = formData.get('LimiteCarga');
            const ToleranceSaldo = formData.get('ToleranceSaldo');

            const payload = {};
            if (TasaEmisionSource) payload.TasaEmisionSource = TasaEmisionSource;
            if (MontoUSDSource) payload.MontoUSDSource = MontoUSDSource;
            if (LimiteCarga !== null && LimiteCarga !== undefined) payload.LimiteCarga = LimiteCarga;
            if (ToleranceSaldo !== null && ToleranceSaldo !== undefined && ToleranceSaldo !== "") payload.ToleranceSaldo = parseFloat(ToleranceSaldo);

            const btn = settingsFormElement.querySelector('button[type="submit"]');
            btn.innerHTML = '<i class="loader" style="width:14px;height:14px;border-color:white;border-bottom-color:transparent;"></i> Guardando...';
            btn.disabled = true;

            try {
                const res = await fetch('/api/procurement/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (!res.ok) {
                    const error = await res.json();
                    throw new Error(error.detail || 'Error saving settings');
                }
                
                showToast('Configuración global actualizada correctamente', 'success');
                
                // Update local memory
                window.globalRetConfig = { ...window.globalRetConfig, ...payload };
                
                // Refresh active dashboard to re-evaluate formulas
                if (typeof fetchData === 'function') fetchData();
            } catch (err) {
                console.error(err);
                showToast(err.message, 'error');
            } finally {
                btn.innerHTML = '<i data-lucide="save"></i> Guardar Configuración';
                btn.disabled = false;
                if (window.lucide) lucide.createIcons();
            }
        });
    }

    // --- Phase 5: Helper Functions for Direct Actions ---
    window.openRetencionFromMain = (codProv, numeroD) => {
        const item = window.currentData?.find(d => d.CodProv === codProv && d.NumeroD === numeroD);
        if (!item) return;
        window._pendingAbonosReturn = { codProv, numeroD };
        document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = false);
        const cb = document.querySelector(`.row-checkbox[data-nrounico="${item.NroUnico}"]`);
        if (cb) cb.checked = true;
        recalculateSelection();
        
        if (window.launchRetencionModal) {
            window.launchRetencionModal([item]);
        } else {
            document.getElementById('btnGenerarRetencion')?.click();
        }
    };

    window.openRetencionIslrFromMain = (codProv, numeroD) => {
        const item = window.currentData?.find(d => d.CodProv === codProv && d.NumeroD === numeroD);
        if (!item) return;
        window._pendingAbonosReturn = { codProv, numeroD };
        document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = false);
        const cb = document.querySelector(`.row-checkbox[data-nrounico="${item.NroUnico}"]`);
        if (cb) cb.checked = true;
        recalculateSelection();
        
        if (window.launchRetencionIslrModal) {
            window.launchRetencionIslrModal([item]);
        } else {
            document.getElementById('btnGenerarRetencionIslr')?.click();
        }
    };

    window.openNCFromMain = (codProv, numeroD, exceso = 0, passedTasa = null) => {
        openNewCreditNoteModal();
        setTimeout(() => {
            const codProvInput = document.getElementById('cncCodProv');
            const numDInput = document.getElementById('cncNumeroD');
            const montoBsInput = document.getElementById('cncMontoBs');
            const tasaInput = document.getElementById('cncTasa');
            const provider = window.allProviders?.find(p => p.CodProv === codProv);
            if (codProvInput) codProvInput.value = provider ? `${provider.CodProv} - ${provider.Descrip}` : codProv;
            if (numDInput) numDInput.value = numeroD;
            const item = window.currentData?.find(d => d.CodProv === codProv && d.NumeroD === numeroD);
            if (item || exceso > 0) {
                if (montoBsInput) montoBsInput.value = exceso > 0 ? exceso.toFixed(2) : (parseFloat(item?.Saldo || 0)).toFixed(2);
                if (tasaInput) tasaInput.value = passedTasa ? passedTasa.toFixed(4) : (parseFloat(item?.TasaActual || window.currentTasaBCV || 0)).toFixed(4);
            }
            if(window.recalcNCUsd) window.recalcNCUsd();
        }, 100);
    };

    window.openNDFromMain = (codProv, numeroD) => {
        const item = window.currentData?.find(d => d.CodProv === codProv && d.NumeroD === numeroD);
        if (!item) return;
        document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = false);
        const cb = document.querySelector(`.row-checkbox[data-nrounico="${item.NroUnico}"]`);
        if (cb) cb.checked = true;
        recalculateSelection();
        showToast('Factura seleccionada. Use "Recibir N/D" en la vista de Notas de Débito.', 'info');
        switchView('debit-notes');
    };

    // --- Provider Datalist Logic ---
    window.allProviders = [];
    window.initProvidersDatalist = async () => {
        try {
            const res = await fetch('/api/procurement/providers');
            if (res.ok) {
                const json = await res.json();
                window.allProviders = json.data || [];
                const datalist = document.getElementById('datalistProviders');
                if (datalist) {
                    datalist.innerHTML = window.allProviders.map(p => 
                        `<option value="${p.CodProv} - ${p.Descrip}">`
                    ).join('');
                }
            }
        } catch (e) { console.error('Error in initProvidersDatalist:', e); }
    };

    initProvidersDatalist();
    
    // Handle initial hash routing
    const initialHash = window.location.hash.substring(1);
    if (initialHash) {
        // Delay slightly to ensure modules-report.js has time to register its global overrides
        setTimeout(() => switchView(initialHash), 500); 
    } else {
        fetchData(); // Load default dashboard
    }

});

// ==========================================
// ANTIGRAVITY ENGINE CLIENT LOGIC — MULTI-ESCENARIO
// ==========================================

// Cache para re-filtrar sin llamar de nuevo a la API
window._antigScenarioData = { conservador: null, moderado: null, agresivo: null };
window._antigFilterActive = false;
window._antigLoanCosts = { conservador: 0, moderado: 0, agresivo: 0 };
window._antigCredits = { conservador: 0, moderado: 0, agresivo: 0 };

/**
 * Render rows into a tbody element from a schedule array.
 * @param {HTMLElement} tbody
 * @param {Array} schedule
 * @param {boolean} filterOptimized - If true, hide rows with savings=0 and same dates
 * @returns {{total: number, optimized: number}}
 */
function _antigRenderRows(tbody, schedule, filterOptimized = false) {
    const usdF = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format;
    const bsF  = new Intl.NumberFormat('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format;
    if (!tbody) return { total: 0, optimized: 0 };
    if (!schedule || schedule.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--text-secondary);">No hay pagos pendientes para este escenario.</td></tr>';
        return { total: 0, optimized: 0 };
    }
    schedule.sort((a, b) => a.date_t - b.date_t || b.savings - a.savings);

    let optimized = 0;
    const rows = [];
    for (const item of schedule) {
        const dateP = (item.date_str || '').substring(0, 10);
        const dateV = (item.due_date_str || '').substring(0, 10);
        const hasSavings = (item.savings || 0) > 0.005;
        const dateShifted = dateP !== dateV;
        const isOptimized = hasSavings || dateShifted;
        if (isOptimized) optimized++;

        if (filterOptimized && !isOptimized) continue;

        const noteHtml = item.note ? `<span title="${item.note}">⚠️</span>` : '';
        const pColor = item.priority === 'Alta' ? '#ef4444' : (item.priority === 'Media' ? '#f59e0b' : '#3b82f6');
        const pBg    = item.priority === 'Alta' ? 'rgba(239,68,68,0.1)' : (item.priority === 'Media' ? 'rgba(245,158,11,0.1)' : 'rgba(59,130,246,0.1)');
        const rowStyle = !isOptimized ? 'opacity:0.35;' : '';
        rows.push(`<tr style="${rowStyle}">
            <td>${dateP} ${noteHtml}</td>
            <td style="color:var(--text-secondary)">${dateV}</td>
            <td>${item.id}</td>
            <td>${item.supplier}</td>
            <td><span class="status-badge" style="background:${pBg};color:${pColor}">${item.priority}</span></td>
            <td class="amount" style="color:var(--text-secondary)">Bs ${bsF(item.orig_bs)}</td>
            <td class="amount">Bs ${bsF(item.final_bs)}</td>
            <td class="amount">$ ${usdF(item.usd_cost)}</td>
            <td class="amount" style="color:${hasSavings ? 'var(--success)' : 'var(--text-secondary)'};font-weight:${hasSavings ? 'bold' : 'normal'}">$ ${usdF(item.savings)}</td>
        </tr>`);
    }
    if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--text-secondary);">Ninguna factura tiene optimización de fecha en este escenario.</td></tr>';
    } else {
        tbody.innerHTML = rows.join('');
    }
    return { total: schedule.length, optimized };
}

/** Re-render all 3 tables with the current filter state */
function _antigReRenderAll() {
    const f = window._antigFilterActive;
    const usdF = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format;
    const scenarioMap = {
        conservador: { tbody: 'antigravityTableBody',    badge: 'antigConservadorBadge' },
        moderado:    { tbody: 'antigravityTableBodyMod',  badge: 'antigModeradoBadge' },
        agresivo:    { tbody: 'antigravityTableBodyAgr',  badge: 'antigAgesivoBadge' }
    };
    for (const [key, ids] of Object.entries(scenarioMap)) {
        const data = window._antigScenarioData[key];
        if (!data) continue;
        const counts = _antigRenderRows(document.getElementById(ids.tbody), data.schedule, f);
        const badge = document.getElementById(ids.badge);
        if (badge) {
            const credit = window._antigCredits[key] || 0;
            const loanCost = window._antigLoanCosts[key] || 0;
            const savingsBruto = data.metrics?.total_savings_usd || 0;
            const savingsNeto = savingsBruto - loanCost;
            const filterLabel = f ? `(mostrando ${counts.optimized})` : `${counts.optimized} de ${counts.total} optimizadas`;
            if (key === 'conservador') {
                badge.textContent = `Prestado: $${usdF(credit)} · Neto: $${usdF(savingsNeto)} · ${filterLabel}`;
            } else {
                badge.textContent = `Prestado: $${usdF(credit)} · Costo: $${usdF(loanCost)} · Neto: $${usdF(savingsNeto)} · ${filterLabel}`;
            }
        }
    }
}

/** Toggle del filtro "Solo optimizados" */
window.toggleAntigravityFilter = function() {
    window._antigFilterActive = !window._antigFilterActive;
    _antigReRenderAll();
    const btn = document.getElementById('btnAntigFilterToggle');
    if (btn) {
        if (window._antigFilterActive) {
            btn.style.background = 'rgba(139,92,246,0.25)';
            btn.style.color = '#a78bfa';
            btn.style.borderColor = 'rgba(139,92,246,0.6)';
            btn.innerHTML = '<i data-lucide="filter" style="width:13px;height:13px;"></i> Filtro activo';
        } else {
            btn.style.background = 'rgba(139,92,246,0.08)';
            btn.style.color = '#8b5cf6';
            btn.style.borderColor = 'rgba(139,92,246,0.3)';
            btn.innerHTML = '<i data-lucide="filter-x" style="width:13px;height:13px;"></i> Solo optimizados';
        }
        if (window.lucide) window.lucide.createIcons();
    }
};

window.runAntigravity = async function() {
    const usdF = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format;
    try {
        const btn = document.getElementById('btnAntigravity');
        btn.innerHTML = '<i class="loader" style="width:16px;height:16px;border-color:var(--primary-accent);border-bottom-color:transparent;display:inline-block;vertical-align:middle;"></i> Procesando...';
        btn.disabled = true;

        // ── Leer configuración global ──
        const cfg = window.globalRetConfig || {};
        const pctFlow   = (parseFloat(cfg.AntigravityFlow)  || 90)  / 100.0;
        const wacc      = parseFloat(cfg.AntigravityWacc)   || 0.12;
        const creditCon = parseFloat(cfg.AntigravityMaxCredit)     || 0;
        const creditMod = parseFloat(cfg.AntigravityMaxCreditMod)  || 0;
        const creditAgr = parseFloat(cfg.AntigravityMaxCreditAgr)  || 0;
        const loanDays  = parseFloat(cfg.AntigravityLoanDays) || 30;
        const loanRate  = (parseFloat(cfg.AntigravityLoanRate) || 18) / 100;

        const loanCostCon = creditCon * loanRate * (loanDays / 365);
        const loanCostMod = creditMod * loanRate * (loanDays / 365);
        const loanCostAgr = creditAgr * loanRate * (loanDays / 365);

        window._antigCredits   = { conservador: creditCon, moderado: creditMod, agresivo: creditAgr };
        window._antigLoanCosts = { conservador: loanCostCon, moderado: loanCostMod, agresivo: loanCostAgr };

        const savedFcParams = JSON.parse(localStorage.getItem('cashflowParams') || '{}');
        const cajaUsd   = savedFcParams.cajaUsd   || parseFloat(document.getElementById('paramCajaUsd')?.value)  || 0;
        const cajaBs    = savedFcParams.cajaBs    || parseFloat(document.getElementById('paramCajaBs')?.value)   || 0;
        const delayDays = savedFcParams.delayDays !== undefined ? savedFcParams.delayDays : 1;
        let fechaCero   = savedFcParams.fechaCero || document.getElementById('paramFechaCero')?.value;
        if (!fechaCero) {
            const tzoffset = (new Date()).getTimezoneOffset() * 60000;
            fechaCero = (new Date(Date.now() - tzoffset)).toISOString().split('T')[0];
        }

        const basePayload = { porcentaje_flujo: pctFlow, caja_usd: cajaUsd, caja_bs: cajaBs,
                              fecha_arranque: fechaCero, delay_days: delayDays, wacc };

        const [resCon, resMod, resAgr] = await Promise.all([
            fetch('/api/antigravity/run', { method:'POST', headers:{'Content-Type':'application/json'},
                  body: JSON.stringify({ ...basePayload, max_credit: creditCon }) }),
            fetch('/api/antigravity/run', { method:'POST', headers:{'Content-Type':'application/json'},
                  body: JSON.stringify({ ...basePayload, max_credit: creditMod }) }),
            fetch('/api/antigravity/run', { method:'POST', headers:{'Content-Type':'application/json'},
                  body: JSON.stringify({ ...basePayload, max_credit: creditAgr }) }),
        ]);
        if (!resCon.ok || !resMod.ok || !resAgr.ok) throw new Error('Error en el motor Antigravity');
        const [dataCon, dataMod, dataAgr] = await Promise.all([resCon.json(), resMod.json(), resAgr.json()]);

        window._antigScenarioData = { conservador: dataCon, moderado: dataMod, agresivo: dataAgr };
        window._antigFilterActive = false;

        const savingsConBruto = dataCon.metrics?.total_savings_usd || 0;
        const savingsModBruto = dataMod.metrics?.total_savings_usd || 0;
        const savingsAgrBruto = dataAgr.metrics?.total_savings_usd || 0;
        const savingsConNeto = savingsConBruto - loanCostCon;
        const savingsModNeto = savingsModBruto - loanCostMod;
        const savingsAgrNeto = savingsAgrBruto - loanCostAgr;

        // ── Conservador KPIs ──
        document.getElementById('antigDevMensual').innerText = ((dataCon.metrics?.r_dev_daily || 0) * 30 * 100).toFixed(2) + '%';
        document.getElementById('antigAhorroUsd').innerText  = '$ ' + usdF(savingsConBruto);
        document.getElementById('antigGastoUsd').innerText   = '$ ' + usdF(dataCon.metrics?.total_cost_usd || 0);
        document.getElementById('antigLimiteFlujo').innerText = (pctFlow * 100).toFixed(0) + '%';
        const cntCon = _antigRenderRows(document.getElementById('antigravityTableBody'), dataCon.schedule, false);
        const badgeCon = document.getElementById('antigConservadorBadge');
        if (badgeCon) badgeCon.textContent = `Prestado: $${usdF(creditCon)} · Neto: $${usdF(savingsConNeto)} · ${cntCon.optimized} de ${cntCon.total} optimizadas`;

        // ── Moderado KPIs ──
        document.getElementById('antigModCreditUsd').innerText        = '$ ' + usdF(creditMod);
        document.getElementById('antigModAhorroUsd').innerText        = '$ ' + usdF(savingsModBruto);
        document.getElementById('antigModCostoFinanciero').innerText  = '$ ' + usdF(loanCostMod);
        document.getElementById('antigModAhorroNeto').innerText       = '$ ' + usdF(savingsModNeto);
        const cntMod = _antigRenderRows(document.getElementById('antigravityTableBodyMod'), dataMod.schedule, false);
        const badgeMod = document.getElementById('antigModeradoBadge');
        if (badgeMod) badgeMod.textContent = `Prestado: $${usdF(creditMod)} · Costo: $${usdF(loanCostMod)} · Neto: $${usdF(savingsModNeto)} · ${cntMod.optimized} de ${cntMod.total} optimizadas`;

        // ── Agresivo KPIs ──
        document.getElementById('antigAgrCreditUsd').innerText        = '$ ' + usdF(creditAgr);
        document.getElementById('antigAgrAhorroUsd').innerText        = '$ ' + usdF(savingsAgrBruto);
        document.getElementById('antigAgrCostoFinanciero').innerText  = '$ ' + usdF(loanCostAgr);
        document.getElementById('antigAgrAhorroNeto').innerText       = '$ ' + usdF(savingsAgrNeto);
        const cntAgr = _antigRenderRows(document.getElementById('antigravityTableBodyAgr'), dataAgr.schedule, false);
        const badgeAgr = document.getElementById('antigAgesivoBadge');
        if (badgeAgr) badgeAgr.textContent = `Prestado: $${usdF(creditAgr)} · Costo: $${usdF(loanCostAgr)} · Neto: $${usdF(savingsAgrNeto)} · ${cntAgr.optimized} de ${cntAgr.total} optimizadas`;

        // ── Comparativa rápida ──
        document.getElementById('cmpConservadorCredit').innerText  = '$ ' + usdF(creditCon);
        document.getElementById('cmpConservadorSavings').innerText = '$ ' + usdF(savingsConNeto);
        document.getElementById('cmpModeradoCredit').innerText     = '$ ' + usdF(creditMod);
        document.getElementById('cmpModeradoSavings').innerText    = '$ ' + usdF(savingsModNeto);
        document.getElementById('cmpAgresivoCredit').innerText     = '$ ' + usdF(creditAgr);
        document.getElementById('cmpAgresivoSavings').innerText    = '$ ' + usdF(savingsAgrNeto);

        // Reset filter button
        const filterBtn = document.getElementById('btnAntigFilterToggle');
        if (filterBtn) {
            filterBtn.style.background = 'rgba(139,92,246,0.08)';
            filterBtn.style.color = '#8b5cf6';
            filterBtn.style.borderColor = 'rgba(139,92,246,0.3)';
            filterBtn.innerHTML = '<i data-lucide="filter-x" style="width:13px;height:13px;"></i> Solo optimizados';
        }

        window.switchAntigravityScenario('conservador');
        forceShowModal(document.getElementById('antigravityModal'));
        if (window.lucide) window.lucide.createIcons();

    } catch (err) {
        console.error(err);
        showToast('Falla de ejecución Antigravity: ' + err.message, 'error');
    } finally {
        const btn = document.getElementById('btnAntigravity');
        btn.innerHTML = '<i data-lucide="zap"></i> Finanza dinamica';
        btn.disabled = false;
        if (window.lucide) window.lucide.createIcons();
    }
};

window.switchAntigravityScenario = function(scenario) {
    document.querySelectorAll('.antg-scenario-pane').forEach(p => p.style.display = 'none');
    const pane = document.getElementById(`pane-scenario-${scenario}`);
    if (pane) pane.style.display = '';

    document.querySelectorAll('.antg-scenario-btn').forEach(b => {
        b.style.fontWeight = 'normal';
        b.style.boxShadow  = 'none';
    });
    const activeBtn = document.getElementById(`btnScenario${scenario.charAt(0).toUpperCase() + scenario.slice(1)}`);
    if (activeBtn) {
        activeBtn.style.fontWeight = '700';
        activeBtn.style.boxShadow  = '0 0 0 2px currentColor';
    }

    document.querySelectorAll('#antigScenarioComparison .stat-card').forEach(c => c.style.opacity = '0.55');
    const cmpCard = document.getElementById(`cmp${scenario.charAt(0).toUpperCase() + scenario.slice(1)}`);
    if (cmpCard) cmpCard.style.opacity = '1';

    if (window.lucide) window.lucide.createIcons();
};

window.closeAntigravityModal = function() {
    forceHideModal(document.getElementById('antigravityModal'));
};

/**
 * Genera un reporte detallado en ventana nueva con explicación factura por factura
 * de la lógica financiera detrás del ahorro/costo.
 */
window.generateAntigravityReport = function() {
    const scenarioNames = { conservador: '🛡️ Conservador', moderado: '⚡ Moderado', agresivo: '🔥 Agresivo' };
    const usdF = v => new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v);
    const bsF  = v => new Intl.NumberFormat('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v);
    const pctF = v => (v * 100).toFixed(4) + '%';
    const cfg = window.globalRetConfig || {};
    const loanDays = parseFloat(cfg.AntigravityLoanDays) || 30;
    const loanRate = (parseFloat(cfg.AntigravityLoanRate) || 18) / 100;

    let html = `<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
    <title>Reporte Detallado — Motor Antigravity</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:'Inter',sans-serif; background:#0f172a; color:#e2e8f0; padding:2rem; font-size:13px; }
        h1 { font-size:1.6rem; margin-bottom:0.3rem; color:#60a5fa; }
        h2 { font-size:1.2rem; margin:1.5rem 0 0.8rem; padding-bottom:0.4rem; border-bottom:1px solid #334155; color:#f1f5f9; }
        h3 { font-size:1rem; margin:1rem 0 0.4rem; color:#a78bfa; }
        .subtitle { color:#94a3b8; font-size:0.85rem; margin-bottom:1.5rem; }
        .summary-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:0.8rem; margin-bottom:1.5rem; }
        .summary-card { background:#1e293b; border:1px solid #334155; border-radius:8px; padding:0.8rem; }
        .summary-card .label { font-size:0.7rem; text-transform:uppercase; color:#94a3b8; letter-spacing:0.5px; }
        .summary-card .value { font-size:1.1rem; font-weight:700; color:#f1f5f9; margin-top:0.2rem; }
        .value.green { color:#4ade80; }
        .value.red { color:#f87171; }
        .value.yellow { color:#fbbf24; }
        table { width:100%; border-collapse:collapse; margin:0.5rem 0 1.5rem; }
        th { background:#1e293b; color:#94a3b8; font-weight:600; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.5px; padding:0.5rem 0.6rem; text-align:left; border-bottom:1px solid #334155; }
        td { padding:0.45rem 0.6rem; border-bottom:1px solid #1e293b; vertical-align:top; }
        tr:nth-child(even) { background:rgba(30,41,59,0.5); }
        .inv-detail { background:#1e293b; border:1px solid #334155; border-radius:8px; padding:1rem; margin-bottom:1rem; page-break-inside:avoid; }
        .inv-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem; }
        .inv-header .inv-id { font-weight:700; font-size:0.95rem; color:#60a5fa; }
        .inv-header .inv-supplier { color:#94a3b8; }
        .explanation { font-size:0.82rem; line-height:1.6; color:#cbd5e1; }
        .explanation strong { color:#f1f5f9; }
        .explanation .highlight { color:#4ade80; font-weight:600; }
        .explanation .warn { color:#fbbf24; font-weight:600; }
        .explanation .negative { color:#f87171; font-weight:600; }
        .tag { display:inline-block; padding:0.1rem 0.4rem; border-radius:4px; font-size:0.7rem; font-weight:600; margin-left:0.5rem; }
        .tag-optimized { background:rgba(74,222,128,0.15); color:#4ade80; }
        .tag-neutral { background:rgba(148,163,184,0.15); color:#94a3b8; }
        .tag-indexed { background:rgba(251,191,36,0.15); color:#fbbf24; }
        .scenario-separator { border:none; border-top:2px solid #3b82f6; margin:2rem 0; }
        .footer { margin-top:2rem; padding-top:1rem; border-top:1px solid #334155; color:#64748b; font-size:0.75rem; text-align:center; }
        @media print {
            body { background:#fff; color:#1e293b; font-size:11px; padding:1rem; }
            .summary-card { border-color:#e2e8f0; }
            .inv-detail { border-color:#e2e8f0; background:#f8fafc; }
            th { background:#f1f5f9; color:#475569; border-color:#e2e8f0; }
            td { border-color:#f1f5f9; }
            h1 { color:#1e40af; }
            h2 { color:#1e293b; border-color:#e2e8f0; }
            h3 { color:#7c3aed; }
            .value.green { color:#16a34a; }
            .value.red { color:#dc2626; }
            .explanation { color:#475569; }
            .explanation strong { color:#1e293b; }
            .highlight { color:#16a34a !important; }
            .warn { color:#d97706 !important; }
            .negative { color:#dc2626 !important; }
        }
    </style></head><body>`;

    html += `<h1>📊 Reporte Detallado — Motor Tesorería Antigravity</h1>`;
    html += `<p class="subtitle">Generado: ${new Date().toLocaleString('es-VE')} · Parámetros: Plazo ${loanDays} días, Tasa ${(loanRate*100).toFixed(1)}% anual</p>`;

    for (const [key, label] of Object.entries(scenarioNames)) {
        const data = window._antigScenarioData[key];
        if (!data) continue;
        const credit = window._antigCredits[key] || 0;
        const loanCost = window._antigLoanCosts[key] || 0;
        const m = data.metrics || {};
        const schedule = data.schedule || [];
        const savingsBruto = m.total_savings_usd || 0;
        const savingsNeto = savingsBruto - loanCost;
        const currentTc = m.current_tc || 0;
        const rDevMonthly = m.r_dev_monthly || 0;

        html += `<hr class="scenario-separator">`;
        html += `<h2>${label} — Monto Prestado: $${usdF(credit)}</h2>`;

        // ── Resumen del Escenario ──
        html += `<div class="summary-grid">
            <div class="summary-card"><div class="label">Monto Prestado</div><div class="value">$ ${usdF(credit)}</div></div>
            <div class="summary-card"><div class="label">Ahorro Bruto</div><div class="value ${savingsBruto > 0 ? 'green' : ''}">$ ${usdF(savingsBruto)}</div></div>
            <div class="summary-card"><div class="label">Costo Financiero</div><div class="value red">$ ${usdF(loanCost)}</div></div>
            <div class="summary-card"><div class="label">Ahorro Neto</div><div class="value ${savingsNeto >= 0 ? 'green' : 'red'}">$ ${usdF(savingsNeto)}</div></div>
            <div class="summary-card"><div class="label">Tasa BCV Actual</div><div class="value">Bs ${bsF(currentTc)}</div></div>
            <div class="summary-card"><div class="label">Devaluación Mensual</div><div class="value yellow">${pctF(rDevMonthly)}</div></div>
            <div class="summary-card"><div class="label">WACC Anualizado</div><div class="value">${pctF(m.annual_wacc || 0)}</div></div>
            <div class="summary-card"><div class="label">Estado Solver</div><div class="value">${m.optimization_status || 'N/A'}</div></div>
        </div>`;

        // Fórmula del costo financiero
        html += `<div class="explanation" style="margin-bottom:1rem;background:#0f172a;padding:0.7rem;border-radius:6px;border:1px solid #334155;">
            <strong>Fórmula Costo Financiero:</strong> $${usdF(credit)} × ${(loanRate*100).toFixed(1)}% × (${loanDays}/365) = <strong class="${loanCost > 0 ? 'negative' : ''}">$${usdF(loanCost)}</strong>
        </div>`;

        // ── Tabla resumen rápida ──
        const optimized = schedule.filter(i => (i.savings||0) > 0.005 || (i.date_str||'').substring(0,10) !== (i.due_date_str||'').substring(0,10));
        html += `<h3>Resumen de Facturas (${schedule.length} total, ${optimized.length} con optimización)</h3>`;
        html += `<table><thead><tr>
            <th>Nro Doc</th><th>Proveedor</th><th>Fecha Pago</th><th>Venc. Original</th>
            <th>Deuda Bs</th><th>Pago Equiv. Bs</th><th>Costo USD</th><th>Ahorro USD</th><th>Estado</th>
        </tr></thead><tbody>`;
        for (const item of schedule) {
            const dateP = (item.date_str||'').substring(0,10);
            const dateV = (item.due_date_str||'').substring(0,10);
            const hasSavings = (item.savings||0) > 0.005;
            const shifted = dateP !== dateV;
            const tagClass = hasSavings ? 'tag-optimized' : (item.indexacion_aplicada ? 'tag-indexed' : 'tag-neutral');
            const tagLabel = hasSavings ? 'Optimizado' : (item.indexacion_aplicada ? 'Indexado' : 'Sin cambio');
            html += `<tr style="${!hasSavings && !shifted ? 'opacity:0.5' : ''}">
                <td>${item.id}</td><td>${item.supplier}</td>
                <td>${dateP}</td><td>${dateV}</td>
                <td style="text-align:right">Bs ${bsF(item.orig_bs)}</td>
                <td style="text-align:right">Bs ${bsF(item.final_bs)}</td>
                <td style="text-align:right">$ ${usdF(item.usd_cost)}</td>
                <td style="text-align:right;color:${hasSavings ? '#4ade80' : '#94a3b8'}">$ ${usdF(item.savings)}</td>
                <td><span class="tag ${tagClass}">${tagLabel}</span></td>
            </tr>`;
        }
        html += `</tbody></table>`;

        // ── Detalle factura por factura ──
        html += `<h3>Análisis Detallado por Factura</h3>`;
        for (const item of schedule) {
            const dateP = (item.date_str||'').substring(0,10);
            const dateV = (item.due_date_str||'').substring(0,10);
            const hasSavings = (item.savings||0) > 0.005;
            const shifted = dateP !== dateV;
            const tagClass = hasSavings ? 'tag-optimized' : (item.indexacion_aplicada ? 'tag-indexed' : 'tag-neutral');
            const tagLabel = hasSavings ? '✅ Optimizado' : (item.indexacion_aplicada ? '⚠️ Indexado' : '— Sin cambio');
            const diasTotales = (item.dias_desde_emision || 0) + (item.chosen_day || 0);

            html += `<div class="inv-detail">`;
            html += `<div class="inv-header">
                <span class="inv-id">Factura #${item.id} <span class="tag ${tagClass}">${tagLabel}</span></span>
                <span class="inv-supplier">${item.supplier}</span>
            </div>`;
            html += `<div class="explanation">`;

            // Línea 1: Contexto temporal
            html += `<strong>Contexto Temporal:</strong> La factura lleva <strong>${item.dias_desde_emision || 0} días</strong> desde su emisión. `;
            html += `El plazo de vencimiento es <strong>${item.t_due_actual || 0} días</strong> desde hoy. `;
            html += `El motor la programó para pago en <strong>T+${item.chosen_day || 0} días</strong> (${dateP}), vs vencimiento original ${dateV}.<br>`;

            // Línea 2: Tasas de cambio
            const tcE = item.tc_emision || 0;
            const tcP = item.tc_pago_proyectado || 0;
            if (tcE > 0 && tcP > 0) {
                const diffTc = ((tcP / tcE - 1) * 100).toFixed(2);
                html += `<strong>Tasa de Cambio:</strong> Al momento de emisión: <strong>Bs ${bsF(tcE)}</strong>/$ · Proyección al pago: <strong>Bs ${bsF(tcP)}</strong>/$ · Variación: <strong class="${parseFloat(diffTc) > 0 ? 'warn' : 'highlight'}">${diffTc}%</strong><br>`;
            }

            // Línea 3: Indexación
            const tTol = item.t_tolerance || 15;
            if (item.indexacion_aplicada) {
                html += `<strong>Indexación:</strong> <span class="warn">SÍ aplica</span>. Los ${diasTotales} días acumulados <strong>superan</strong> la tolerancia de ${tTol} días del proveedor. `;
                html += `El monto original de <strong>Bs ${bsF(item.orig_bs)}</strong> se re-expresó a <strong>Bs ${bsF(item.final_bs)}</strong> usando la tasa proyectada.<br>`;
            } else {
                html += `<strong>Indexación:</strong> <span class="highlight">NO aplica</span>. Los ${diasTotales} días acumulados están <strong>dentro</strong> de la tolerancia de ${tTol} días → se paga al monto original en Bs.<br>`;
            }

            // Línea 4: Descuentos
            const descBase = item.descuento_base_pct || 0;
            if (descBase > 0) {
                html += `<strong>Descuento Base:</strong> ${(descBase * 100).toFixed(1)}% (Condición: ${item.descuento_base_cond || 'N/A'}). `;
            }
            const descPP = item.descuentos_pronto_pago || [];
            if (descPP.length > 0) {
                const applied = descPP.find(d => diasTotales >= d.DiasDesde && diasTotales <= d.DiasHasta);
                if (applied) {
                    html += `<strong>Descuento Pronto Pago:</strong> <span class="highlight">${(applied.Porcentaje * 100).toFixed(1)}%</span> (rango ${applied.DiasDesde}-${applied.DiasHasta} días). `;
                } else {
                    html += `Descuento Pronto Pago: No aplica para los ${diasTotales} días acumulados. `;
                }
            }
            if (descBase > 0 || descPP.length > 0) html += `<br>`;

            // Línea 5: Cálculo final
            html += `<strong>Costo USD:</strong> Bs ${bsF(item.final_bs)} ÷ Bs ${bsF(tcP)}/$ = <strong>$ ${usdF(item.usd_cost)}</strong> · `;
            html += `Valor Presente (WACC): <strong>$ ${usdF(item.pv_usd || item.usd_cost)}</strong><br>`;

            // Línea 6: Savings
            const baselineUsd = item.baseline_usd || 0;
            if (hasSavings) {
                html += `<strong>Ahorro:</strong> Costo si se paga al vencimiento: $${usdF(baselineUsd)} · Costo optimizado: $${usdF(item.usd_cost)} → <span class="highlight">Ahorro: $${usdF(item.savings)}</span>`;
            } else {
                html += `<strong>Ahorro:</strong> $${usdF(item.savings)} — <span class="warn">No hay ventana de optimización</span>. El solver no encontró un día de pago más barato que el vencimiento (Baseline: $${usdF(baselineUsd)}).`;
            }

            if (item.note) {
                html += `<br><strong>⚠️ Nota:</strong> <span class="warn">${item.note}</span>`;
            }

            html += `</div></div>`;
        }
    }

    // Footer
    html += `<div class="footer">
        Motor Antigravity v2.0 — Optimización MILP (PuLP CBC) · Synapse ERP<br>
        Este reporte fue generado automáticamente. Los valores proyectados son estimaciones basadas en la tendencia histórica del BCV de los últimos 30 días.
    </div>`;

    html += `</body></html>`;

    const w = window.open('', '_blank', 'width=1100,height=800');
    if (w) {
        w.document.write(html);
        w.document.close();
    } else {
        showToast('No se pudo abrir la ventana del reporte. Desbloquea los popups.', 'error');
    }
};


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
        
        // Si el año es distinto, pero el mes/día de emisión es anterior al de ingreso, lo consideramos válido (salto de año)
        if (fe.getFullYear() !== fi.getFullYear()) {
            const me = fe.getMonth();
            const de = fe.getDate();
            const mi = fi.getMonth();
            const di = fi.getDate();
            if (me < mi || (me === mi && de <= di)) return false;
        }
        
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

