/**
 * PROTOTYPE — wipe me.
 * Question: ¿Cómo comparar variables usadas vs resultados obtenidos,
 *           corriendo 3 presets contemporáneamente (Conservador/Normal/Agresivo)?
 * Variants via ?prototype=compare-presets&variant=A|B|C on modulo_pedidos.html
 */
(function () {
  'use strict';

  const PARAM = 'prototype';
  const VALUE = 'compare-presets';
  const VARIANTS = [
    { key: '1', name: 'Alt1 tabla resultados' },
    { key: '2', name: 'Alt2 zonas fijas' },
    { key: 'A', name: 'A cards (previa)' },
  ];

  /** Roles sobre las 3 corridas (Presente + Comp1 + Comp2). */
  const causalPick = {
    presente: 'Conservador',
    comp1: 'Normal',
    comp2: 'Agresivo',
    focusKpi: 'montoUsd',
  };

  const KNOB_META = [
    { key: 'amplifier_enabled', label: 'Amplificador', group: 'Vars', format: 'bool' },
    { key: 'amp_max_increment_pct', label: 'Tope amp %', group: 'Vars', format: 'num' },
    { key: 'ext_max_dias_extra', label: 'Días extra F5', group: 'Vars', format: 'num' },
    { key: 'f5_umbral', label: 'Umbral F5', group: 'Vars', format: 'num' },
    { key: 'opp_lambda', label: 'Lambda opp', group: 'Vars', format: 'num' },
    { key: 'w3_posicionamiento', label: 'w3 precio', group: 'Vars', format: 'weight' },
    { key: 'w4', label: 'w4 oportunidad', group: 'Vars', format: 'weight' },
    { key: 'w5', label: 'w5 extensión', group: 'Vars', format: 'weight' },
    { key: 'lead_time_soft', label: 'Lead time', group: 'Vars', format: 'text' },
  ];

  const RESULT_META = [
    { key: 'montoUsd', label: 'Monto propuesto (USD)', format: 'money' },
    { key: 'unidades', label: 'Unidades', format: 'int' },
    { key: 'renglones', label: 'Renglones', format: 'int' },
    { key: 'deltaMontoVsBaseline', label: 'Δ monto vs Baseline', format: 'money_delta' },
    { key: 'deltaUnitsVsBaseline', label: 'Δ unidades vs Baseline', format: 'int_delta' },
    { key: 'nCambios', label: 'Líneas con cambio', format: 'int' },
    { key: 'topProveedor', label: 'Top proveedor', format: 'text' },
  ];

  // Knob snapshots (resolve_preset_knobs) — in memory.
  const PRESET_DEFS = {
    Conservador: {
      amplifier_enabled: false, amp_max_increment_pct: 500, ext_max_dias_extra: 0,
      f5_umbral: -0.1, opp_lambda: 1.0, w3_posicionamiento: 1, w4: 0, w5: 0, lead_time_soft: 'low',
    },
    Normal: {
      amplifier_enabled: true, amp_max_increment_pct: 500, ext_max_dias_extra: 21,
      f5_umbral: -0.1, opp_lambda: 1.0, w3_posicionamiento: 0.25, w4: 0.2, w5: 0.15, lead_time_soft: 'medium',
    },
    Agresivo: {
      amplifier_enabled: true, amp_max_increment_pct: 800, ext_max_dias_extra: 45,
      f5_umbral: -0.05, opp_lambda: 1.5, w3_posicionamiento: 0.15, w4: 0.35, w5: 0.25, lead_time_soft: 'high',
    },
  };

  const COMPARE_SET = ['Conservador', 'Normal', 'Agresivo'];

  /** Drawer: knobs del Presente (grill: edita Presente). */
  let presenteDraft = { ...PRESET_DEFS.Conservador };

  /** @type {{ status: string, source: string, message: string, runs: object[], sencillo: object|null }} */
  let session = {
    status: 'idle',
    source: 'mock',
    message: 'Sin corrida aún. Pulse «Correr 3 presets».',
    runs: COMPARE_SET.map((name) => emptyRun(name)),
    sencillo: null,
  };

  function emptyRun(name) {
    return {
      preset: name,
      knobs: { ...PRESET_DEFS[name] },
      results: null,
      error: null,
      ms: null,
    };
  }

  // Realistic mock KPIs (PROTOTYPE — wipe me). Same catalog imagined.
  function mockResults(preset) {
    const table = {
      Conservador: {
        montoUsd: 84200, unidades: 18420, renglones: 910,
        deltaMontoVsBaseline: 1200, deltaUnitsVsBaseline: 180, nCambios: 42,
        topProveedor: 'DROG. CENTRAL',
      },
      Normal: {
        montoUsd: 91850, unidades: 20110, renglones: 938,
        deltaMontoVsBaseline: 8850, deltaUnitsVsBaseline: 1870, nCambios: 186,
        topProveedor: 'FARMATODO DIST',
      },
      Agresivo: {
        montoUsd: 104400, unidades: 23480, renglones: 972,
        deltaMontoVsBaseline: 21400, deltaUnitsVsBaseline: 5240, nCambios: 311,
        topProveedor: 'FARMATODO DIST',
      },
    };
    return { ...table[preset] };
  }

  function summarizeApiResult(data) {
    const comp = data.comparativa_cantidades || [];
    const prop = data.pedido_propuesto || [];
    let monto = 0;
    let units = 0;
    let baseUnits = 0;
    let baseMonto = 0;
    let priced = 0;
    let basePriced = 0;
    const byProv = {};
    let nCambios = 0;

    comp.forEach((row) => {
      const qb = Number(row.qty_baseline) || 0;
      const qp = Number(row.qty_propuesto) || 0;
      baseUnits += qb;
      units += qp;
      const px = row.precio_propuesto ?? row.precio ?? row.oferta_propuesta?.precio;
      const pxB = row.precio_baseline ?? row.oferta_baseline?.precio;
      if (px != null && !Number.isNaN(Number(px)) && qp > 0) {
        monto += Number(px) * qp;
        priced += 1;
        const pk = String(row.proveedor_propuesto || row.proveedor || '').trim() || '—';
        byProv[pk] = (byProv[pk] || 0) + Number(px) * qp;
      }
      if (pxB != null && !Number.isNaN(Number(pxB)) && qb > 0) {
        baseMonto += Number(pxB) * qb;
        basePriced += 1;
      }
      const sameQty = qb === qp;
      const sameBarra = String(row.barra_baseline || '') === String(row.barra_propuesto || row.barra || '');
      if (!sameQty || !sameBarra) nCambios += 1;
    });

    if (!comp.length && prop.length) {
      prop.forEach((line) => {
        const q = Number(line.cantidad ?? line.qty) || 0;
        const px = line.precio;
        units += q;
        if (px != null) {
          monto += Number(px) * q;
          priced += 1;
          const pk = String(line.proveedor || '').trim() || '—';
          byProv[pk] = (byProv[pk] || 0) + Number(px) * q;
        }
      });
    }

    const top = Object.entries(byProv).sort((a, b) => b[1] - a[1])[0];
    const results = {
      montoUsd: priced ? Math.round(monto) : null,
      unidades: Math.round(units),
      renglones: prop.length || comp.filter((r) => (Number(r.qty_propuesto) || 0) > 0).length,
      deltaMontoVsBaseline: (priced && basePriced) ? Math.round(monto - baseMonto) : null,
      deltaUnitsVsBaseline: Math.round(units - baseUnits),
      nCambios,
      topProveedor: top ? top[0] : '—',
    };
    const sencillo = {
      montoUsd: basePriced ? Math.round(baseMonto) : null,
      unidades: Math.round(baseUnits),
      renglones: comp.filter((r) => (Number(r.qty_baseline) || 0) > 0).length,
      deltaMontoVsBaseline: 0,
      deltaUnitsVsBaseline: 0,
      nCambios: 0,
      topProveedor: '—',
    };
    return { results, sencillo };
  }

  function mockSencillo() {
    return {
      montoUsd: 83000, unidades: 18240, renglones: 900,
      deltaMontoVsBaseline: 0, deltaUnitsVsBaseline: 0, nCambios: 0, topProveedor: '—',
    };
  }

  function readFormPayloadBase() {
    // Prefer real form if present; else stub for static-server demos.
    const cats = [];
    try {
      // categoryMap is closed over in app_pedidos — read checkboxes / data attrs if any
      document.querySelectorAll('#criteriosAgrupacion input[type=checkbox]:checked').forEach(() => {});
    } catch (_) { /* ignore */ }

    const criterios = [];
    document.querySelectorAll('#criteriosAgrupacion input[type=checkbox]:checked').forEach((el) => {
      if (el.value) criterios.push(el.value);
    });

    // Categories live in JS map; try selected chips / modal state via DOM hints
    let categorias = [];
    if (typeof window.__protoGetSelectedCategories === 'function') {
      categorias = window.__protoGetSelectedCategories();
    } else {
      // Heuristic: categories bar count text, or empty → API will fail → mock fallback
      categorias = [];
    }

    const presupuestoRaw = document.getElementById('presupuestoMaximo')?.value;
    return {
      cobertura: Number(document.getElementById('pedidoDays')?.value || 30),
      criterios_agrupacion: criterios.length ? criterios : [
        'principio_activo', 'forma_farmaceutica', 'concentracion',
        'cantidad_presentacion', 'contenido_neto',
      ],
      categorias,
      include_generics: document.getElementById('includeGenerics')?.checked !== false,
      include_brands: document.getElementById('includeBrands')?.checked !== false,
      umbral_rotacion: Number(document.getElementById('umbralRotacion')?.value || 0),
      num_rows: Number(document.getElementById('numRows')?.value || 5000),
      presupuesto_maximo: presupuestoRaw ? Number(presupuestoRaw) : null,
    };
  }

  async function runTriple() {
    session.status = 'running';
    session.message = 'Disparando 3× POST /api/pedidos/generar-sencillo…';
    session.runs = COMPARE_SET.map((name) => emptyRun(name));
    session.sencillo = null;
    // Sync draft onto Presente display knobs for this session
    presenteDraft = { ...(PRESET_DEFS[causalPick.presente] || PRESET_DEFS.Normal), ...presenteDraft };
    render();

    const base = readFormPayloadBase();
    let categorias = base.categorias;
    if (!categorias.length) {
      session.source = 'mock';
      session.message = 'Sin categorías. Mock ×3 + Sencillo (laboratorio; no toca Comparativa).';
      await delay(450);
      session.sencillo = mockSencillo();
      session.runs = COMPARE_SET.map((name) => ({
        preset: name,
        knobs: name === causalPick.presente ? { ...presenteDraft } : { ...PRESET_DEFS[name] },
        results: mockResults(name),
        error: null,
        ms: 120 + Math.round(Math.random() * 80),
      }));
      session.status = 'ready';
      render();
      return;
    }

    try {
      const settled = await Promise.all(COMPARE_SET.map(async (preset) => {
        const t0 = performance.now();
        const payload = { ...base, preset, categorias };
        const response = await fetch('/api/pedidos/generar-sencillo', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const ms = Math.round(performance.now() - t0);
        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${response.status} (${preset})`);
        }
        const data = await response.json();
        const sum = summarizeApiResult(data);
        return {
          preset,
          knobs: preset === causalPick.presente ? { ...presenteDraft } : { ...PRESET_DEFS[preset] },
          results: sum.results,
          sencillo: sum.sencillo,
          error: null,
          ms,
        };
      }));
      session.runs = settled;
      session.sencillo = settled[0]?.sencillo || null;
      session.source = 'api';
      session.status = 'ready';
      session.message = `3 corridas API OK (${settled.map((r) => `${r.preset} ${r.ms}ms`).join(' · ')}). Comparativa Pedidos intacta.`;
    } catch (err) {
      session.source = 'mock';
      session.message = `API falló (${err.message}). Fallback mock.`;
      session.sencillo = mockSencillo();
      session.runs = COMPARE_SET.map((name) => ({
        preset: name,
        knobs: name === causalPick.presente ? { ...presenteDraft } : { ...PRESET_DEFS[name] },
        results: mockResults(name),
        error: null,
        ms: null,
      }));
      session.status = 'ready';
    }
    render();
  }

  function delay(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function fmtMeta(meta, v) {
    if (v === null || v === undefined) return '—';
    if (meta.format === 'bool') return v ? 'Sí' : 'No';
    if (meta.format === 'weight') return Number(v).toFixed(2);
    if (meta.format === 'money') return `$${Number(v).toLocaleString('en-US')}`;
    if (meta.format === 'money_delta') {
      const n = Number(v);
      const s = `$${Math.abs(n).toLocaleString('en-US')}`;
      return n > 0 ? `+${s}` : n < 0 ? `−${s}` : s;
    }
    if (meta.format === 'int') return Number(v).toLocaleString('es-VE');
    if (meta.format === 'int_delta') {
      const n = Math.round(Number(v));
      if (n > 0) return `+${n.toLocaleString('es-VE')}`;
      if (n < 0) return `−${Math.abs(n).toLocaleString('es-VE')}`;
      return '0';
    }
    return String(v);
  }

  function valuesEqual(a, b) {
    return a === b || (typeof a === 'number' && typeof b === 'number' && Math.abs(a - b) < 1e-9);
  }

  function getVariant() {
    const v = (new URLSearchParams(window.location.search).get('variant') || 'A').toUpperCase();
    return VARIANTS.some((x) => x.key === v) ? v : '1';
  }

  function isActive() {
    return new URLSearchParams(window.location.search).get(PARAM) === VALUE;
  }

  function setVariant(key) {
    const url = new URL(window.location.href);
    url.searchParams.set(PARAM, VALUE);
    url.searchParams.set('variant', key);
    window.history.replaceState({}, '', url);
    render();
  }

  function ensureHost() {
    let host = document.getElementById('prototypeComparePresets');
    if (host) return host;
    host = document.createElement('section');
    host.id = 'prototypeComparePresets';
    host.className = 'section-card proto-compare';
    host.style.display = 'none';
    const config = document.getElementById('configSection');
    if (config?.parentNode) config.parentNode.insertBefore(host, config.nextSibling);
    else document.querySelector('.main-content')?.appendChild(host);
    return host;
  }

  function ensureEntryLink() {
    const label = document.querySelector('label[for="presetSencillo"]');
    if (!label || document.getElementById('protoCompareEntry')) return;
    const a = document.createElement('a');
    a.id = 'protoCompareEntry';
    a.href = '?prototype=compare-presets&variant=A';
    a.textContent = 'Comparar ▸';
    a.title = 'PROTOTYPE — variables vs resultados (3 presets)';
    a.style.cssText = 'margin-left:0.4rem;font-size:0.7rem;color:var(--primary-accent);text-decoration:underline;font-weight:600;';
    label.appendChild(a);
  }

  function runToolbarHtml(title, sub) {
    const busy = session.status === 'running';
    return `
      <header class="proto-head">
        <div>
          <p class="proto-badge">PROTOTYPE · ${escapeHtml(title)}</p>
          <h3>Variables usadas → resultados (×3 contemporáneos)</h3>
          <p class="proto-sub">${escapeHtml(sub)}</p>
        </div>
        <button type="button" class="btn btn-primary proto-run-btn" id="protoRunTriple" ${busy ? 'disabled' : ''}>
          ${busy ? 'Corrriendo 3…' : 'Correr 3 presets'}
        </button>
      </header>
      <p class="proto-status" data-src="${session.source}">${escapeHtml(session.message)}</p>`;
  }

  function bindRunButton(root) {
    root.querySelector('#protoRunTriple')?.addEventListener('click', () => runTriple());
  }

  function statePre() {
    return `<pre class="proto-state">${escapeHtml(JSON.stringify({
      variant: getVariant(),
      status: session.status,
      source: session.source,
      causalPick,
      runs: session.runs.map((r) => ({
        preset: r.preset,
        ms: r.ms,
        knobs: r.knobs,
        results: r.results,
        error: r.error,
      })),
    }, null, 2))}</pre>`;
  }

  function escapeHtml(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function deltaLineHtml(meta, senVal, runVal) {
    if (typeof senVal !== 'number' || typeof runVal !== 'number') return '';
    if (meta.format === 'text' || meta.format === 'bool') return '';
    const d = runVal - senVal;
    if (meta.format === 'money' || meta.format === 'money_delta') {
      return `<div class="proto-cell-delta">Δ vs Sen ${escapeHtml(fmtMeta({ format: 'money_delta' }, d))}</div>`;
    }
    const n = Math.round(d);
    const t = n > 0 ? `+${n.toLocaleString('es-VE')}` : n < 0 ? `−${Math.abs(n).toLocaleString('es-VE')}` : '0';
    return `<div class="proto-cell-delta">Δ vs Sen ${t}</div>`;
  }

  /** Presente + Comp1 + Comp2 + KPI (hueco rojo = Comp2). */
  function causalPickersHtml() {
    const opts = COMPARE_SET.map((p) => `<option value="${escapeHtml(p)}">${escapeHtml(p)}</option>`).join('');
    return `
      <div class="proto-diff-pickers" id="protoCausalPickers">
        <div class="input-group"><label>Presente</label>
          <select id="protoPresente" class="form-control">${opts}</select></div>
        <div class="proto-arrow">→</div>
        <div class="input-group"><label>Comparar con</label>
          <select id="protoComp1" class="form-control">${opts}</select></div>
        <div class="input-group"><label>Comparar con</label>
          <select id="protoComp2" class="form-control">${opts}</select></div>
        <div class="input-group"><label>KPI foco</label>
          <select id="protoKpi" class="form-control">
            ${RESULT_META.map((m) => `<option value="${m.key}">${escapeHtml(m.label)}</option>`).join('')}
          </select></div>
      </div>
      <div id="protoCausal"></div>`;
  }

  function bindCausalPickers(root, onChange) {
    const presenteSel = root.querySelector('#protoPresente');
    const c1 = root.querySelector('#protoComp1');
    const c2 = root.querySelector('#protoComp2');
    const kpiSel = root.querySelector('#protoKpi');
    if (!presenteSel || !c1 || !c2 || !kpiSel) return;
    presenteSel.value = causalPick.presente;
    c1.value = causalPick.comp1;
    c2.value = causalPick.comp2;
    kpiSel.value = causalPick.focusKpi;
    presenteSel.addEventListener('change', () => {
      causalPick.presente = presenteSel.value;
      presenteDraft = { ...PRESET_DEFS[causalPick.presente] };
      onChange();
    });
    c1.addEventListener('change', () => { causalPick.comp1 = c1.value; onChange(); });
    c2.addEventListener('change', () => { causalPick.comp2 = c2.value; onChange(); });
    kpiSel.addEventListener('change', () => { causalPick.focusKpi = kpiSel.value; onChange(); });
  }

  function paintCausalPanel(root) {
    const P = session.runs.find((r) => r.preset === causalPick.presente);
    const C1 = session.runs.find((r) => r.preset === causalPick.comp1);
    const C2 = session.runs.find((r) => r.preset === causalPick.comp2);
    const kpiMeta = RESULT_META.find((m) => m.key === causalPick.focusKpi);
    const box = root.querySelector('#protoCausal');
    if (!box || !kpiMeta) return;
    if (!P?.results || !C1?.results || !C2?.results) {
      box.innerHTML = '<p class="proto-empty">Corra los 3 presets para ver Sen → P / C1 / C2.</p>';
      return;
    }
    const sen = session.sencillo;
    const pv = P.results[causalPick.focusKpi];
    const v1 = C1.results[causalPick.focusKpi];
    const v2 = C2.results[causalPick.focusKpi];
    const sv = sen ? sen[causalPick.focusKpi] : null;
    const dNote = (from, to) => {
      if (typeof from !== 'number' || typeof to !== 'number') return '';
      return `Δ ${fmtMeta(kpiMeta, to - from)}`;
    };
    box.innerHTML = `
      <div class="proto-causal-hero">
        <div><span class="proto-g">KPI foco</span><strong>${escapeHtml(kpiMeta.label)}</strong></div>
        <div class="proto-diff-vals proto-diff-vals-wide">
          <span title="Sencillo"><span class="proto-g">Sen</span>${escapeHtml(fmtMeta(kpiMeta, sv))}</span>
          <span class="proto-diff-arrow">→</span>
          <span title="Presente"><span class="proto-g">P</span>${escapeHtml(fmtMeta(kpiMeta, pv))}</span>
          <span class="proto-delta">${escapeHtml(dNote(sv, pv))}</span>
          <span class="proto-diff-arrow">|</span>
          <span title="Comp1"><span class="proto-g">C1</span>${escapeHtml(fmtMeta(kpiMeta, v1))}</span>
          <span class="proto-delta">${escapeHtml(dNote(sv, v1))}</span>
          <span class="proto-diff-arrow">|</span>
          <span title="Comp2"><span class="proto-g">C2</span>${escapeHtml(fmtMeta(kpiMeta, v2))}</span>
          <span class="proto-delta">${escapeHtml(dNote(sv, v2))}</span>
        </div>
      </div>`;
  }

  function knobDiffRowsHtml() {
    const P = session.runs.find((r) => r.preset === causalPick.presente);
    const C1 = session.runs.find((r) => r.preset === causalPick.comp1);
    const C2 = session.runs.find((r) => r.preset === causalPick.comp2);
    if (!P?.knobs || !C1?.knobs || !C2?.knobs) {
      return '<p class="proto-empty" style="font-size:0.75rem;">Corra 3 presets.</p>';
    }
    const diffs = KNOB_META.filter((m) =>
      !valuesEqual(P.knobs[m.key], C1.knobs[m.key]) || !valuesEqual(P.knobs[m.key], C2.knobs[m.key])
    );
    if (!diffs.length) {
      return '<p class="proto-empty" style="font-size:0.75rem;">Sin diferencias.</p>';
    }
    return `<ul class="proto-vars-compact">
      ${diffs.map((m) => `
        <li>
          <span class="proto-vars-k">${escapeHtml(m.label)}</span>
          <span class="proto-vars-v">
            <b title="Presente">${escapeHtml(fmtMeta(m, P.knobs[m.key]))}</b>
            →
            <span title="Comp1">${escapeHtml(fmtMeta(m, C1.knobs[m.key]))}</span>
            /
            <span title="Comp2">${escapeHtml(fmtMeta(m, C2.knobs[m.key]))}</span>
          </span>
        </li>`).join('')}
    </ul>
    <p class="proto-col-meta" style="margin-top:0.35rem;">P → C1 / C2 · ${diffs.length}</p>`;
  }

  function openDrawer(open) {
    document.getElementById('protoDrawer')?.classList.toggle('is-open', open);
    document.getElementById('protoDrawerScrim')?.classList.toggle('is-open', open);
  }

  function paintDrawerFields(root) {
    const host = root.querySelector('#protoDrawerFields');
    if (!host) return;
    host.innerHTML = `
      <p class="proto-sub">Knobs del <strong>Presente</strong> (${escapeHtml(causalPick.presente)}). Cobertura/categorías siguen arriba.</p>
      <div class="proto-drawer-grid">
        ${KNOB_META.map((m) => {
          const v = presenteDraft[m.key];
          if (m.format === 'bool') {
            return `<label class="proto-drawer-field"><span>${escapeHtml(m.label)}</span>
              <select data-knob="${m.key}" class="form-control">
                <option value="true" ${v ? 'selected' : ''}>Sí</option>
                <option value="false" ${!v ? 'selected' : ''}>No</option>
              </select></label>`;
          }
          if (m.key === 'lead_time_soft') {
            return `<label class="proto-drawer-field"><span>${escapeHtml(m.label)}</span>
              <select data-knob="${m.key}" class="form-control">
                ${['low', 'medium', 'high'].map((x) => `<option value="${x}" ${v === x ? 'selected' : ''}>${x}</option>`).join('')}
              </select></label>`;
          }
          return `<label class="proto-drawer-field"><span>${escapeHtml(m.label)}</span>
            <input type="number" class="form-control" data-knob="${m.key}" value="${escapeHtml(v)}" step="any"></label>`;
        }).join('')}
      </div>
      <div class="proto-drawer-actions">
        <button type="button" class="btn btn-primary" id="protoSaveDraft" style="height:40px;flex:1;font-weight:700;">Guardar</button>
        <button type="button" class="btn btn-secondary" id="protoResetDraft" style="height:40px;">Reset</button>
      </div>`;
    host.querySelectorAll('[data-knob]').forEach((el) => {
      const key = el.getAttribute('data-knob');
      const go = () => {
        const meta = KNOB_META.find((x) => x.key === key);
        if (meta?.format === 'bool') presenteDraft[key] = el.value === 'true';
        else if (el.tagName === 'SELECT') presenteDraft[key] = el.value;
        else {
          const n = Number(el.value);
          presenteDraft[key] = Number.isNaN(n) ? el.value : n;
        }
      };
      el.addEventListener('change', go);
      el.addEventListener('input', go);
    });
    host.querySelector('#protoSaveDraft')?.addEventListener('click', () => {
      const run = session.runs.find((r) => r.preset === causalPick.presente);
      if (run) run.knobs = { ...presenteDraft };
      openDrawer(false);
      root.dispatchEvent(new CustomEvent('proto-refresh-cols'));
      session.message = `Knobs del Presente (${causalPick.presente}) guardados.`;
      const st = root.querySelector('.proto-status');
      if (st) {
        st.textContent = session.message;
        st.dataset.src = session.source;
      }
    });
    host.querySelector('#protoResetDraft')?.addEventListener('click', () => {
      presenteDraft = { ...PRESET_DEFS[causalPick.presente] };
      paintDrawerFields(root);
    });
  }


  function roleTag(preset) {
    if (preset === causalPick.presente) return '<span class="proto-role-tag">Presente</span>';
    if (preset === causalPick.comp1) return '<span class="proto-role-tag alt">Comp1</span>';
    if (preset === causalPick.comp2) return '<span class="proto-role-tag alt2">Comp2</span>';
    return '';
  }

  function runFor(preset) {
    return session.runs.find((r) => r.preset === preset) || emptyRun(preset);
  }

  function labShellHtml(badge, title, sub) {
    const busy = session.status === 'running';
    return `
      <header class="proto-head">
        <div>
          <p class="proto-badge">${escapeHtml(badge)}</p>
          <h3>${escapeHtml(title)}</h3>
          <p class="proto-sub">${escapeHtml(sub)}</p>
        </div>
        <div class="proto-head-actions">
          <button type="button" class="btn btn-secondary" id="protoOpenDrawer" style="height:40px;">⚙ Knobs</button>
          <button type="button" class="btn btn-primary proto-run-btn" id="protoRunTriple" ${busy ? 'disabled' : ''}>
            ${busy ? 'Corriendo 3…' : 'Correr 3 presets'}
          </button>
        </div>
      </header>
      <p class="proto-status" data-src="${session.source}">${escapeHtml(session.message)}</p>
      ${causalPickersHtml()}`;
  }

  function bindLabChrome(root, refresh) {
    bindRunButton(root);
    root.querySelector('#protoOpenDrawer')?.addEventListener('click', () => {
      paintDrawerFields(root);
      openDrawer(true);
    });
    if (!root.querySelector('#protoDrawer')) {
      root.insertAdjacentHTML('beforeend', `
        <div id="protoDrawerScrim" class="proto-drawer-scrim"></div>
        <aside id="protoDrawer" class="proto-drawer" aria-hidden="true">
          <div class="proto-drawer-head">
            <strong>⚙ Presente</strong>
            <button type="button" class="btn btn-secondary" id="protoCloseDrawer" style="padding:0.25rem 0.6rem;">×</button>
          </div>
          <div id="protoDrawerFields"></div>
        </aside>`);
    }
    root.querySelector('#protoCloseDrawer')?.addEventListener('click', () => openDrawer(false));
    root.querySelector('#protoDrawerScrim')?.addEventListener('click', () => openDrawer(false));
    bindCausalPickers(root, refresh);
    root.addEventListener('proto-refresh-cols', refresh);
  }

  function resultsAlignedTableHtml() {
    const sen = session.sencillo;
    const cols = [
      { key: 'sen', label: 'Sencillo', bag: sen, delta: false },
      { key: 'p', label: `P · ${causalPick.presente}`, bag: runFor(causalPick.presente).results, delta: true },
      { key: 'c1', label: `C1 · ${causalPick.comp1}`, bag: runFor(causalPick.comp1).results, delta: true },
      { key: 'c2', label: `C2 · ${causalPick.comp2}`, bag: runFor(causalPick.comp2).results, delta: true },
    ];
    return `
      <div class="proto-scroll proto-alt1-table-wrap">
        <table class="proto-matrix proto-alt1-table">
          <thead>
            <tr>
              <th>KPI</th>
              ${cols.map((c) => `<th>${escapeHtml(c.label)}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${RESULT_META.map((m) => {
              const focus = m.key === causalPick.focusKpi ? 'proto-kpi-focus-row' : '';
              return `<tr class="${focus}">
                <td>${escapeHtml(m.label)}</td>
                ${cols.map((c) => {
                  const v = c.bag ? c.bag[m.key] : null;
                  const senV = sen ? sen[m.key] : null;
                  const delta = c.delta ? deltaLineHtml(m, senV, v) : '';
                  return `<td class="proto-cell-stack"><div class="proto-cell-val">${escapeHtml(fmtMeta(m, v))}</div>${delta}</td>`;
                }).join('')}
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>`;
  }

  function knobsOnlyCard(preset, roleClass) {
    const run = runFor(preset);
    return `
      <article class="proto-col ${roleClass}">
        <h4>${escapeHtml(preset)} ${roleTag(preset)}</h4>
        <p class="proto-col-meta">${run.ms != null ? `${run.ms} ms` : '—'} · knobs</p>
        <dl class="proto-dl">
          ${KNOB_META.map((m) => `<div><dt>${escapeHtml(m.label)}</dt><dd>${escapeHtml(fmtMeta(m, run.knobs[m.key]))}</dd></div>`).join('')}
        </dl>
      </article>`;
  }

  /** Alternativa 1: tabla de resultados alineada + knobs abajo */
  function Variant1(root) {
    root.innerHTML = `
      ${labShellHtml('PROTOTYPE · Alt 1 — Tabla resultados', 'Resultados en una grilla', 'Sencillo es columna, no card. Abajo: Δ vars + knobs P/C1/C2.')}
      <div id="protoAlt1Results"></div>
      <div class="proto-cols proto-cols-knobs" id="protoAlt1Knobs"></div>
      ${statePre()}`;
    function refresh() {
      paintCausalPanel(root);
      root.querySelector('#protoAlt1Results').innerHTML = resultsAlignedTableHtml();
      root.querySelector('#protoAlt1Knobs').innerHTML = `
        <article class="proto-col proto-col-vars">
          <h4>Δ Variables</h4>
          <p class="proto-col-meta">P → C1 / C2</p>
          ${knobDiffRowsHtml()}
        </article>
        ${knobsOnlyCard(causalPick.presente, 'proto-col-presente')}
        ${knobsOnlyCard(causalPick.comp1, 'proto-col-alternativa')}
        ${knobsOnlyCard(causalPick.comp2, 'proto-col-alternativa2')}
      `;
    }
    bindLabChrome(root, refresh);
    refresh();
    if (session.status === 'idle') runTriple();
  }

  /** Alternativa 2: 5 cards, zonas fijas (header / knobs-or-spacer / resultados) */
  function Variant2(root) {
    root.innerHTML = `
      ${labShellHtml('PROTOTYPE · Alt 2 — Zonas fijas', '5 cards con franjas alineadas', 'Vars + Sencillo angostos; knobs/spacer arriba; RESULTADOS en la misma banda.')}
      <div class="proto-cols proto-cols-5z" id="protoAlt2Cols"></div>
      ${statePre()}`;

    function zonedCard({ title, tagHtml, meta, knobsHtml, resultsHtml, extraClass }) {
      return `
        <article class="proto-col proto-zoned ${extraClass || ''}">
          <div class="proto-zone-head">
            <h4>${title} ${tagHtml || ''}</h4>
            <p class="proto-col-meta">${meta || ''}</p>
          </div>
          <div class="proto-zone-knobs">${knobsHtml}</div>
          <div class="proto-zone-res">
            <h5>Resultados</h5>
            ${resultsHtml}
          </div>
        </article>`;
    }

    function resultsDl(bag, withDelta) {
      const sen = session.sencillo;
      if (!bag) return '<p class="proto-empty">Sin datos.</p>';
      return `<dl class="proto-dl proto-dl-res">
        ${RESULT_META.map((m) => {
          const focus = m.key === causalPick.focusKpi;
          const senV = sen ? sen[m.key] : null;
          const delta = withDelta ? deltaLineHtml(m, senV, bag[m.key]) : '';
          return `<div class="${focus ? 'proto-kpi-focus' : ''}"><dt>${escapeHtml(m.label)}</dt>
            <dd>${escapeHtml(fmtMeta(m, bag[m.key]))}${delta}</dd></div>`;
        }).join('')}
      </dl>`;
    }

    function refresh() {
      paintCausalPanel(root);
      const sen = session.sencillo;
      const p = runFor(causalPick.presente);
      const c1 = runFor(causalPick.comp1);
      const c2 = runFor(causalPick.comp2);
      const knobsDl = (run) => `<dl class="proto-dl">
        ${KNOB_META.map((m) => `<div><dt>${escapeHtml(m.label)}</dt><dd>${escapeHtml(fmtMeta(m, run.knobs[m.key]))}</dd></div>`).join('')}
      </dl>`;
      root.querySelector('#protoAlt2Cols').innerHTML = [
        zonedCard({
          title: 'Δ Vars',
          meta: 'angosto',
          extraClass: 'proto-col-vars proto-z-narrow',
          knobsHtml: knobDiffRowsHtml(),
          resultsHtml: '<p class="proto-empty" style="font-size:0.72rem;">Solo diffs de knobs</p>',
        }),
        zonedCard({
          title: 'Sencillo',
          tagHtml: '<span class="proto-role-tag sen">Baseline</span>',
          meta: 'sin knobs · resultados alineados',
          extraClass: 'proto-col-sencillo proto-z-narrow',
          knobsHtml: '<div class="proto-knob-spacer" aria-hidden="true"><span>Sin variables de preset</span></div>',
          resultsHtml: resultsDl(sen, false),
        }),
        zonedCard({
          title: escapeHtml(p.preset),
          tagHtml: roleTag(causalPick.presente),
          meta: `${p.ms != null ? p.ms + ' ms' : '—'} · ${session.source}`,
          extraClass: 'proto-col-presente',
          knobsHtml: `<h5 style="margin-top:0;">Variables usadas</h5>${knobsDl(p)}`,
          resultsHtml: resultsDl(p.results, true),
        }),
        zonedCard({
          title: escapeHtml(c1.preset),
          tagHtml: roleTag(causalPick.comp1),
          meta: `${c1.ms != null ? c1.ms + ' ms' : '—'}`,
          extraClass: 'proto-col-alternativa',
          knobsHtml: `<h5 style="margin-top:0;">Variables usadas</h5>${knobsDl(c1)}`,
          resultsHtml: resultsDl(c1.results, true),
        }),
        zonedCard({
          title: escapeHtml(c2.preset),
          tagHtml: roleTag(causalPick.comp2),
          meta: `${c2.ms != null ? c2.ms + ' ms' : '—'}`,
          extraClass: 'proto-col-alternativa2',
          knobsHtml: `<h5 style="margin-top:0;">Variables usadas</h5>${knobsDl(c2)}`,
          resultsHtml: resultsDl(c2.results, true),
        }),
      ].join('');
    }
    bindLabChrome(root, refresh);
    refresh();
    if (session.status === 'idle') runTriple();
  }

  // ── A: cards + Comp2 + card Sencillo + drawer (MISMO formato cards) ──
  function VariantA(root) {
    const busy = session.status === 'running';
    root.innerHTML = `
      <header class="proto-head">
        <div>
          <p class="proto-badge">PROTOTYPE · A — 3 columnas + causal</p>
          <h3>Variables usadas → resultados (×3 contemporáneos)</h3>
          <p class="proto-sub">Cards por corrida + Sencillo. Presente / Comp1 / Comp2 / KPI. Drawer ⚙ = knobs del Presente.</p>
        </div>
        <div class="proto-head-actions">
          <button type="button" class="btn btn-secondary" id="protoOpenDrawer" style="height:40px;">⚙ Knobs</button>
          <button type="button" class="btn btn-primary proto-run-btn" id="protoRunTriple" ${busy ? 'disabled' : ''}>
            ${busy ? 'Corriendo 3…' : 'Correr 3 presets'}
          </button>
        </div>
      </header>
      <p class="proto-status" data-src="${session.source}">${escapeHtml(session.message)}</p>
      ${causalPickersHtml()}
      <div class="proto-cols proto-cols-4" id="protoCols"></div>
      <div id="protoDrawerScrim" class="proto-drawer-scrim"></div>
      <aside id="protoDrawer" class="proto-drawer" aria-hidden="true">
        <div class="proto-drawer-head">
          <strong>⚙ Presente</strong>
          <button type="button" class="btn btn-secondary" id="protoCloseDrawer" style="padding:0.25rem 0.6rem;">×</button>
        </div>
        <div id="protoDrawerFields"></div>
      </aside>
      ${statePre()}`;
    bindRunButton(root);
    root.querySelector('#protoOpenDrawer')?.addEventListener('click', () => {
      paintDrawerFields(root);
      openDrawer(true);
    });
    root.querySelector('#protoCloseDrawer')?.addEventListener('click', () => openDrawer(false));
    root.querySelector('#protoDrawerScrim')?.addEventListener('click', () => openDrawer(false));

    function roleFor(preset) {
      if (preset === causalPick.presente) return 'presente';
      if (preset === causalPick.comp1) return 'alternativa';
      if (preset === causalPick.comp2) return 'alternativa2';
      return '';
    }
    function roleTag(preset) {
      if (preset === causalPick.presente) return '<span class="proto-role-tag">Presente</span>';
      if (preset === causalPick.comp1) return '<span class="proto-role-tag alt">Comp1</span>';
      if (preset === causalPick.comp2) return '<span class="proto-role-tag alt2">Comp2</span>';
      return '';
    }

    function paintCols() {
      const cols = root.querySelector('#protoCols');
      const sen = session.sencillo;
      const varsCard = `
        <article class="proto-col proto-col-vars">
          <h4>Δ Variables</h4>
          <p class="proto-col-meta">vs Presente · compacto</p>
          ${knobDiffRowsHtml()}
        </article>`;
      const senCard = `
        <article class="proto-col proto-col-sencillo">
          <h4>Sencillo <span class="proto-role-tag sen">Baseline</span></h4>
          <p class="proto-col-meta">PedidoBaseline</p>
          <h5>Resultados</h5>
          ${sen ? `<dl class="proto-dl proto-dl-res">
            ${RESULT_META.map((m) => {
              const focus = m.key === causalPick.focusKpi;
              return `<div class="${focus ? 'proto-kpi-focus' : ''}"><dt>${escapeHtml(m.label)}</dt>
                <dd>${escapeHtml(fmtMeta(m, sen[m.key]))}</dd></div>`;
            }).join('')}
          </dl>` : '<p class="proto-empty">Corra 3 presets.</p>'}
        </article>`;
      const order = [causalPick.presente, causalPick.comp1, causalPick.comp2];
      const uniq = [...new Set(order)];
      const runCards = uniq.map((presetName) => {
        const run = session.runs.find((r) => r.preset === presetName) || emptyRun(presetName);
        const res = run.results;
        const role = roleFor(presetName);
        return `
          <article class="proto-col ${role ? `proto-col-${role}` : ''}">
            <h4>${escapeHtml(run.preset)} ${roleTag(presetName)}</h4>
            <p class="proto-col-meta">${run.ms != null ? `${run.ms} ms` : '—'} · ${session.source}</p>
            <h5>Variables usadas</h5>
            <dl class="proto-dl">
              ${KNOB_META.map((m) => `<div><dt>${escapeHtml(m.label)}</dt><dd>${escapeHtml(fmtMeta(m, run.knobs[m.key]))}</dd></div>`).join('')}
            </dl>
            <h5>Resultados</h5>
            ${res ? `<dl class="proto-dl proto-dl-res">
              ${RESULT_META.map((m) => {
                const focus = m.key === causalPick.focusKpi;
                const senV = sen ? sen[m.key] : null;
                return `<div class="${focus ? 'proto-kpi-focus' : ''}"><dt>${escapeHtml(m.label)}</dt>
                  <dd>${escapeHtml(fmtMeta(m, res[m.key]))}${deltaLineHtml(m, senV, res[m.key])}</dd></div>`;
              }).join('')}
            </dl>` : `<p class="proto-empty">${run.error || 'Sin resultado.'}</p>`}
          </article>`;
      }).join('');
      cols.innerHTML = varsCard + senCard + runCards;
    }

    function refresh() {
      paintCausalPanel(root);
      paintCols();
    }
    bindCausalPickers(root, refresh);
    root.addEventListener('proto-refresh-cols', refresh);
    refresh();
  }

  // ── B: unified matrix vars then KPIs ───────────────────────────
  function VariantB(root) {
    root.innerHTML = `
      ${runToolbarHtml('B — Matriz var→KPI', 'Filas = variables o KPIs; columnas = las 3 corridas. Diferencias resaltadas.')}
      <div class="proto-scroll">
        <table class="proto-matrix" id="protoMatrixVars"></table>
      </div>
      <div class="proto-scroll" style="margin-top:0.75rem;">
        <table class="proto-matrix" id="protoMatrixRes"></table>
      </div>
      ${statePre()}`;
    bindRunButton(root);

    const runs = session.runs;
    const paintBlock = (tableId, metas, getter, section) => {
      const table = root.querySelector(tableId);
      const hasData = runs.every((r) => getter(r) != null);
      table.innerHTML = `
        <thead><tr><th>${section}</th>${runs.map((r) => `<th>${escapeHtml(r.preset)}</th>`).join('')}</tr></thead>
        <tbody>
          ${metas.map((m) => {
            const vals = runs.map((r) => {
              const bag = getter(r);
              return bag ? bag[m.key] : null;
            });
            const allSame = hasData && vals.every((v) => valuesEqual(v, vals[0]));
            return `<tr class="${allSame ? '' : 'proto-diff-row'}">
              <td>${escapeHtml(m.label)}</td>
              ${vals.map((v, i) => {
                const hi = hasData && !allSame && !valuesEqual(v, vals[0]);
                return `<td class="${hi ? 'proto-cell-diff' : ''}">${escapeHtml(fmtMeta(m, v))}</td>`;
              }).join('')}
            </tr>`;
          }).join('')}
        </tbody>`;
    };
    paintBlock('#protoMatrixVars', KNOB_META, (r) => r.knobs, 'VARIABLES');
    paintBlock('#protoMatrixRes', RESULT_META, (r) => r.results, 'RESULTADOS');
  }

  // ── C: causal — pick KPI delta, see which vars explain it ──────
  function VariantC(root) {
    const state = { left: 'Normal', right: 'Agresivo', focusKpi: 'deltaMontoVsBaseline' };

    root.innerHTML = `
      ${runToolbarHtml('C — Causal delta', 'Elija dos corridas y un KPI: ve el Δ de resultado junto a las variables que difieren.')}
      <div class="proto-diff-pickers">
        <div class="input-group"><label>Corrida A</label>
          <select id="protoLeft" class="form-control">${COMPARE_SET.map((p) => `<option>${p}</option>`).join('')}</select></div>
        <div class="proto-arrow">→</div>
        <div class="input-group"><label>Corrida B</label>
          <select id="protoRight" class="form-control">${COMPARE_SET.map((p) => `<option>${p}</option>`).join('')}</select></div>
        <div class="input-group"><label>KPI foco</label>
          <select id="protoKpi" class="form-control">
            ${RESULT_META.map((m) => `<option value="${m.key}">${escapeHtml(m.label)}</option>`).join('')}
          </select></div>
      </div>
      <div id="protoCausal"></div>
      ${statePre()}`;
    bindRunButton(root);

    const leftSel = root.querySelector('#protoLeft');
    const rightSel = root.querySelector('#protoRight');
    const kpiSel = root.querySelector('#protoKpi');
    leftSel.value = state.left;
    rightSel.value = state.right;
    kpiSel.value = state.focusKpi;

    function paint() {
      const L = session.runs.find((r) => r.preset === state.left);
      const R = session.runs.find((r) => r.preset === state.right);
      const kpiMeta = RESULT_META.find((m) => m.key === state.focusKpi);
      const box = root.querySelector('#protoCausal');
      if (!L?.results || !R?.results) {
        box.innerHTML = '<p class="proto-empty">Corra los 3 presets para ver el vínculo variables → KPI.</p>';
        return;
      }
      const lv = L.results[state.focusKpi];
      const rv = R.results[state.focusKpi];
      let deltaNote = '';
      if (typeof lv === 'number' && typeof rv === 'number') {
        const d = rv - lv;
        deltaNote = `Δ ${fmtMeta(kpiMeta, d)}`;
      }
      const knobDiffs = KNOB_META.filter((m) => !valuesEqual(L.knobs[m.key], R.knobs[m.key]));
      box.innerHTML = `
        <div class="proto-causal-hero">
          <div><span class="proto-g">KPI</span><strong>${escapeHtml(kpiMeta.label)}</strong></div>
          <div class="proto-diff-vals">
            <span class="proto-from">${escapeHtml(fmtMeta(kpiMeta, lv))}</span>
            <span class="proto-diff-arrow">→</span>
            <span class="proto-to">${escapeHtml(fmtMeta(kpiMeta, rv))}</span>
            <span class="proto-delta">${escapeHtml(deltaNote)}</span>
          </div>
        </div>
        <h5>Variables que difieren (${knobDiffs.length})</h5>
        <ul class="proto-diff-list">
          ${knobDiffs.map((m) => `
            <li>
              <div class="proto-diff-label">${escapeHtml(m.label)}</div>
              <div class="proto-diff-vals">
                <span class="proto-from">${escapeHtml(fmtMeta(m, L.knobs[m.key]))}</span>
                <span class="proto-diff-arrow">→</span>
                <span class="proto-to">${escapeHtml(fmtMeta(m, R.knobs[m.key]))}</span>
              </div>
            </li>`).join('') || '<li class="proto-empty">Knobs idénticos (¿mismo preset?).</li>'}
        </ul>
        <p class="proto-sub" style="margin-top:0.75rem;">Hipótesis de lectura (prototype): el Δ de KPI se interpreta junto a estas variables — no implica causalidad automática.</p>`;
    }

    leftSel.addEventListener('change', () => { state.left = leftSel.value; paint(); root.querySelector('.proto-state').outerHTML = statePre(); });
    rightSel.addEventListener('change', () => { state.right = rightSel.value; paint(); });
    kpiSel.addEventListener('change', () => { state.focusKpi = kpiSel.value; paint(); });
    paint();
  }

  function ensureSwitcher() {
    let bar = document.getElementById('prototypeSwitcher');
    if (bar) return bar;
    bar = document.createElement('div');
    bar.id = 'prototypeSwitcher';
    bar.className = 'proto-switcher';
    bar.innerHTML = `
      <button type="button" id="protoPrev" aria-label="Anterior">←</button>
      <span id="protoLabel"></span>
      <button type="button" id="protoNext" aria-label="Siguiente">→</button>`;
    document.body.appendChild(bar);
    function cycle(dir) {
      const keys = VARIANTS.map((v) => v.key);
      const i = keys.indexOf(getVariant());
      setVariant(keys[(i + dir + keys.length) % keys.length]);
    }
    bar.querySelector('#protoPrev').addEventListener('click', () => cycle(-1));
    bar.querySelector('#protoNext').addEventListener('click', () => cycle(1));
    document.addEventListener('keydown', (e) => {
      if (!isActive()) return;
      const t = e.target;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
      if (e.key === 'ArrowLeft') { e.preventDefault(); cycle(-1); }
      if (e.key === 'ArrowRight') { e.preventDefault(); cycle(1); }
    });
    return bar;
  }

  function render() {
    ensureEntryLink();
    const host = ensureHost();
    const bar = ensureSwitcher();
    const active = isActive();
    host.style.display = active ? 'block' : 'none';
    bar.style.display = active ? 'flex' : 'none';
    if (!active) return;
    const v = getVariant();
    bar.querySelector('#protoLabel').textContent = `${v} — ${VARIANTS.find((x) => x.key === v).name}`;
    host.innerHTML = '';
    if (v === '1') Variant1(host);
    else if (v === '2') Variant2(host);
    else if (v === 'A') VariantA(host);
    else Variant1(host);
  }

  // Bridge: let prototype read selected categories from app_pedidos if it exposes them later.
  // Also try scraping categoryMap via a tiny hook after load.
  function tryHookCategories() {
    // app_pedidos keeps categoryMap private; expose a best-effort reader via DOM if categories modal lists selected.
    window.__protoGetSelectedCategories = function () {
      const names = [];
      document.querySelectorAll('#categoriesList li, #categoriesModal li').forEach((li) => {
        const cb = li.querySelector('input[type=checkbox]');
        if (cb?.checked) {
          const t = (li.textContent || '').trim();
          if (t) names.push(t.split('\n')[0].trim());
        }
      });
      return names.filter(Boolean);
    };
  }

  const style = document.createElement('style');
  style.textContent = `
    .proto-compare { margin-top:0.5rem; border:2px dashed var(--primary-accent) !important; }
    .proto-head { display:flex; justify-content:space-between; gap:1rem; flex-wrap:wrap; margin-bottom:0.75rem; align-items:flex-start; }
    .proto-badge { font-size:0.7rem; letter-spacing:0.08em; color:var(--primary-accent); font-weight:700; margin:0 0 0.25rem; }
    .proto-compare h3 { margin:0; font-family:var(--font-display); font-size:1.25rem; }
    .proto-compare h4 { margin:0 0 0.15rem; font-size:1rem; }
    .proto-compare h5 { margin:0.75rem 0 0.35rem; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-secondary); }
    .proto-sub { margin:0.25rem 0 0; color:var(--text-secondary); font-size:0.85rem; }
    .proto-status { font-size:0.8rem; padding:0.45rem 0.65rem; border:1px solid var(--border-subtle); margin-bottom:0.85rem; color:var(--text-secondary); }
    .proto-status[data-src="api"] { border-color: var(--success); color: var(--success); }
    .proto-status[data-src="mock"] { border-color: var(--warning); color: var(--warning); }
    .proto-run-btn { height:40px; white-space:nowrap; }
    .proto-head-actions { display:flex; gap:0.5rem; flex-wrap:wrap; }
    .proto-cols { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:0.75rem; }
    .proto-cols-4 { grid-template-columns:minmax(200px,0.9fr) repeat(3,minmax(0,1fr)); gap:0.85rem; align-items:start; }
    @media (max-width:1200px) { .proto-cols-4 { grid-template-columns:repeat(2,minmax(0,1fr)); } }
    @media (max-width:900px) { .proto-cols, .proto-cols-4 { grid-template-columns:1fr; } }
    .proto-col-vars { border-color: var(--border-focus); background: rgba(0,0,0,0.18); }
    .proto-vars-compact { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:0.35rem; }
    .proto-vars-compact li {
      display:flex; flex-direction:column; gap:0.1rem; padding:0.4rem 0.45rem;
      border:1px solid var(--border-subtle); font-size:0.72rem; line-height:1.25;
    }
    .proto-vars-k { color:var(--text-secondary); font-weight:600; }
    .proto-vars-v { font-family:var(--font-mono); color:var(--text-primary); word-break:break-word; }
    .proto-vars-v b { color:var(--primary-accent); }
    .proto-drawer-actions { display:flex; gap:0.5rem; margin-top:1rem; }
    .proto-alt1-table-wrap { margin-bottom: 0.85rem; max-height: none; }
    .proto-alt1-table th:first-child, .proto-alt1-table td:first-child { width: 11rem; }
    .proto-kpi-focus-row { background: rgba(139,58,74,0.12); }
    .proto-cols-knobs { display:grid; grid-template-columns:minmax(160px,0.8fr) repeat(3,minmax(0,1fr)); gap:0.75rem; }
    .proto-cols-5z {
      display:grid;
      grid-template-columns: minmax(140px,0.7fr) minmax(140px,0.7fr) repeat(3,minmax(0,1.15fr));
      gap:0.65rem;
      align-items: stretch;
    }
    .proto-zoned { display:flex; flex-direction:column; min-height:100%; padding:0 !important; overflow:hidden; }
    .proto-zone-head { padding:0.65rem 0.65rem 0.35rem; border-bottom:1px solid var(--border-subtle); }
    .proto-zone-knobs { padding:0.5rem 0.65rem; flex:1 1 auto; min-height:12rem; border-bottom:1px solid var(--border-subtle); overflow:auto; }
    .proto-zone-res { padding:0.5rem 0.65rem 0.65rem; flex:0 0 auto; background:rgba(0,0,0,0.12); }
    .proto-z-narrow .proto-zone-knobs { min-height:12rem; }
    .proto-knob-spacer {
      height:100%; min-height:10rem; display:flex; align-items:center; justify-content:center;
      border:1px dashed var(--border-subtle); color:var(--text-muted); font-size:0.72rem; text-align:center; padding:0.5rem;
    }
    @media (max-width:1100px) {
      .proto-cols-5z, .proto-cols-knobs { grid-template-columns:repeat(2,minmax(0,1fr)); }
    }

    .proto-col { border:1px solid var(--border-subtle); padding:0.75rem; background:var(--bg-surface-hover); }
    .proto-col-meta { font-size:0.7rem; color:var(--text-muted); margin:0 0 0.5rem; font-family:var(--font-mono); }
    .proto-col-presente { border-color: var(--primary-accent); box-shadow: inset 0 0 0 1px var(--primary-accent); }
    .proto-col-alternativa, .proto-col-alternativa2 { border-color: var(--warning); }
    .proto-col-sencillo { border-style: dashed; opacity: 0.95; }
    .proto-role-tag {
      display:inline-block; margin-left:0.35rem; font-size:0.65rem; font-weight:700; letter-spacing:0.04em;
      text-transform:uppercase; padding:0.1rem 0.35rem; background:var(--primary-accent); color:#fff; vertical-align:middle;
    }
    .proto-role-tag.alt, .proto-role-tag.alt2 { background: transparent; color: var(--warning); border:1px solid var(--warning); }
    .proto-role-tag.sen { background: transparent; color: var(--text-secondary); border:1px dashed var(--border-subtle); }
    .proto-cell-delta { display:block; font-size:0.68rem; color:var(--warning); font-weight:500; margin-top:0.1rem; }
    .proto-diff-vals-wide { flex-wrap:wrap; gap:0.35rem 0.55rem; }
    .proto-drawer-scrim { display:none; position:fixed; inset:0; background:rgba(0,0,0,0.45); z-index:10002; }
    .proto-drawer-scrim.is-open { display:block; }
    .proto-drawer {
      position:fixed; top:0; right:0; width:min(400px,100vw); height:100vh; z-index:10003;
      background:var(--bg-surface); border-left:2px solid var(--primary-accent);
      transform:translateX(100%); transition:transform 0.2s ease; overflow:auto; padding:1rem;
    }
    .proto-drawer.is-open { transform:translateX(0); }
    .proto-drawer-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem; }
    .proto-drawer-grid { display:flex; flex-direction:column; gap:0.5rem; }
    .proto-drawer-field { display:flex; flex-direction:column; gap:0.2rem; font-size:0.8rem; color:var(--text-secondary); }
    .proto-kpi-focus { background: rgba(139,58,74,0.12); outline:1px solid var(--primary-accent); }
    .proto-kpi-focus dt { font-weight:700; color: var(--primary-accent); }
    .proto-dl { display:flex; flex-direction:column; gap:0.2rem; font-size:0.78rem; }
    .proto-dl div { display:flex; justify-content:space-between; gap:0.5rem; border-bottom:1px solid var(--border-subtle); padding:0.15rem 0; }
    .proto-dl dt { color:var(--text-secondary); }
    .proto-dl dd { margin:0; font-family:var(--font-mono); }
    .proto-dl-res dd { color: var(--warning); font-weight:600; }
    .proto-scroll { overflow:auto; max-height:280px; border:1px solid var(--border-subtle); }
    .proto-matrix { width:100%; border-collapse:collapse; font-size:0.8rem; font-family:var(--font-mono); }
    .proto-matrix th, .proto-matrix td { padding:0.4rem 0.55rem; border-bottom:1px solid var(--border-subtle); text-align:left; }
    .proto-matrix th { position:sticky; top:0; background:var(--bg-surface); z-index:1; }
    .proto-diff-row { background: rgba(139,58,74,0.08); }
    .proto-cell-diff { color: var(--warning); font-weight:600; }
    .proto-diff-pickers { display:flex; align-items:end; gap:0.75rem; flex-wrap:wrap; margin-bottom:0.75rem; }
    .proto-compare #protoCausal { margin-bottom:1rem; }
    .proto-diff-pickers .input-group { flex:1; min-width:140px; margin:0; }
    .proto-arrow { font-size:1.4rem; color:var(--text-muted); padding-bottom:0.35rem; }
    .proto-diff-list { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:0.45rem; }
    .proto-diff-list li { display:flex; justify-content:space-between; gap:1rem; flex-wrap:wrap; padding:0.55rem 0.65rem; border:1px solid var(--border-subtle); background:var(--bg-surface-hover); }
    .proto-diff-label { font-weight:600; font-size:0.85rem; }
    .proto-diff-vals { font-family:var(--font-mono); font-size:0.82rem; display:flex; align-items:center; gap:0.45rem; }
    .proto-from { color:var(--text-muted); text-decoration:line-through; }
    .proto-to { color:var(--warning); font-weight:700; }
    .proto-delta { color:var(--text-secondary); font-size:0.75rem; }
    .proto-causal-hero { display:flex; justify-content:space-between; align-items:center; gap:1rem; flex-wrap:wrap; padding:0.85rem; border:1px solid var(--primary-accent); margin-bottom:0.75rem; }
    .proto-empty { color:var(--text-secondary); font-size:0.85rem; }
    .proto-g { display:block; font-size:0.65rem; color:var(--text-muted); }
    .proto-state { margin-top:1rem; font-size:0.7rem; max-height:160px; overflow:auto; background:rgba(0,0,0,0.25); padding:0.65rem; color:var(--text-secondary); border:1px solid var(--border-subtle); }
    .proto-switcher {
      position:fixed; bottom:1.25rem; left:50%; transform:translateX(-50%); z-index:9999;
      display:none; align-items:center; gap:0.75rem; padding:0.55rem 0.9rem;
      background:#111; color:#f5f5f5; border:2px solid #f5f5f5; box-shadow:0 8px 24px rgba(0,0,0,0.45);
      font-family:var(--font-mono); font-size:0.8rem; font-weight:600;
    }
    .proto-switcher button { background:transparent; border:1px solid #666; color:#f5f5f5; width:2rem; height:2rem; cursor:pointer; font-size:1rem; }
    .proto-switcher button:hover { border-color:#fff; }
    #protoLabel { min-width:11rem; text-align:center; }
  `;
  document.head.appendChild(style);

  tryHookCategories();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();
