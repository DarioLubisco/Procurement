/**
 * PROTOTYPE — wipe me.
 * Grill verdict (2026-07-25): Wireframe 3 —
 *   mesa Sencillo|Presente|Comp1|Comp2; slots = trío del pool (base+custom);
 *   drawer ⚙ edita Presente (knobs+guardar); form Pedidos arriba intacto;
 *   Correr 3 no toca Comparativa principal; celdas = valor + Δ vs Sencillo.
 * URL: ?prototype=compare-presets&variant=A
 */
(function () {
  'use strict';

  const PARAM = 'prototype';
  const VALUE = 'compare-presets';
  const VARIANTS = [
    { key: 'A', name: 'Lab Wireframe 3' },
    { key: 'B', name: 'Matriz legacy' },
    { key: 'C', name: 'Causal legacy' },
  ];

  /** Three slots = the run trio (must be distinct). */
  const slots = {
    presente: 'Conservador',
    comp1: 'Normal',
    comp2: 'Agresivo',
    focusKpi: 'ahorroTotalUsd',
  };

  const KNOB_META = [
    { key: 'amplifier_enabled', label: 'Amplificador', format: 'bool' },
    { key: 'amp_max_increment_pct', label: 'Tope amp %', format: 'num' },
    { key: 'amp_floor_pct', label: 'Piso amp', format: 'num' },
    { key: 'ext_max_dias_extra', label: 'Días extra F5', format: 'num' },
    { key: 'f5_umbral', label: 'Umbral F5', format: 'num' },
    { key: 'opp_lambda', label: 'Lambda opp', format: 'num' },
    { key: 'w1', label: 'w1 elasticidad', format: 'weight' },
    { key: 'w2', label: 'w2 demanda', format: 'weight' },
    { key: 'w3_posicionamiento', label: 'w3 precio', format: 'weight' },
    { key: 'w4', label: 'w4 oportunidad', format: 'weight' },
    { key: 'w5', label: 'w5 extensión', format: 'weight' },
    { key: 'lead_time_soft', label: 'Lead time', format: 'text' },
    { key: 'split_lead_time_enabled', label: 'Split lead time', format: 'bool' },
  ];

  const RESULT_META = [
    { key: 'montoUsd', label: 'Monto (USD)', format: 'money' },
    { key: 'unidades', label: 'Unidades', format: 'int' },
    { key: 'renglones', label: 'Renglones', format: 'int' },
    { key: 'ahorroTotalUsd', label: 'Ahorro total', format: 'money_delta' },
    { key: 'ahorroCantidadUsd', label: 'Ahorro cantidad', format: 'money_delta' },
    { key: 'ahorroSucedaneoUsd', label: 'Ahorro sucedáneo', format: 'money_delta' },
    { key: 'nCambios', label: 'Líneas con cambio', format: 'int' },
    { key: 'topProveedor', label: 'Top proveedor', format: 'text' },
  ];

  const PRESET_DEFS = {
    Conservador: {
      amplifier_enabled: false, amp_max_increment_pct: 500, amp_floor_pct: 0.2,
      ext_max_dias_extra: 0, f5_umbral: -0.1, opp_lambda: 1.0,
      w1: 0, w2: 0, w3_posicionamiento: 1, w4: 0, w5: 0,
      lead_time_soft: 'low', split_lead_time_enabled: false,
    },
    Normal: {
      amplifier_enabled: true, amp_max_increment_pct: 500, amp_floor_pct: 0.2,
      ext_max_dias_extra: 21, f5_umbral: -0.1, opp_lambda: 1.0,
      w1: 0.15, w2: 0.25, w3_posicionamiento: 0.25, w4: 0.2, w5: 0.15,
      lead_time_soft: 'medium', split_lead_time_enabled: true,
    },
    Agresivo: {
      amplifier_enabled: true, amp_max_increment_pct: 800, amp_floor_pct: 0.15,
      ext_max_dias_extra: 45, f5_umbral: -0.05, opp_lambda: 1.5,
      w1: 0.05, w2: 0.2, w3_posicionamiento: 0.15, w4: 0.35, w5: 0.25,
      lead_time_soft: 'high', split_lead_time_enabled: true,
    },
  };

  const BASE_NAMES = ['Conservador', 'Normal', 'Agresivo'];

  /** @type {{ id: string, name: string, base_preset: string, overrides: object, knobs: object }[]} */
  let customPool = [];

  /** Presente draft knobs (drawer edits this). */
  let presenteDraft = { ...PRESET_DEFS.Conservador };

  let session = {
    status: 'idle',
    source: 'mock',
    message: 'Elija Presente + Comp1 + Comp2 (distintos) y pulse «Correr 3».',
    /** @type {Record<string, object>} keyed by slot id */
    runsBySlot: {},
    /** Shared PedidoBaseline KPIs from last triple (any run). */
    sencillo: null,
  };

  function slotIds() {
    return [
      { id: 'presente', label: 'Presente', key: slots.presente },
      { id: 'comp1', label: 'Comp1', key: slots.comp1 },
      { id: 'comp2', label: 'Comp2', key: slots.comp2 },
    ];
  }

  function poolOptions() {
    const opts = BASE_NAMES.map((n) => ({ key: n, label: n, kind: 'base' }));
    customPool.forEach((c) => {
      opts.push({ key: `custom:${c.id}`, label: `${c.name} ★`, kind: 'custom', custom: c });
    });
    return opts;
  }

  function resolveEntry(key) {
    if (key.startsWith('custom:')) {
      const id = key.slice(7);
      const c = customPool.find((x) => String(x.id) === String(id));
      if (!c) return { key, name: key, kind: 'base', base_preset: 'Normal', knobs: { ...PRESET_DEFS.Normal }, overrides: {} };
      return {
        key,
        name: c.name,
        kind: 'custom',
        base_preset: c.base_preset || 'Normal',
        knobs: { ...c.knobs },
        overrides: { ...(c.overrides || {}) },
        customId: c.id,
      };
    }
    return {
      key,
      name: key,
      kind: 'base',
      base_preset: key,
      knobs: { ...PRESET_DEFS[key] },
      overrides: {},
    };
  }

  function syncPresenteDraftFromSlot() {
    const e = resolveEntry(slots.presente);
    presenteDraft = { ...e.knobs };
  }

  function emptyRun(entry) {
    return {
      slotKey: entry.key,
      name: entry.name,
      kind: entry.kind,
      base_preset: entry.base_preset,
      knobs: { ...entry.knobs },
      overrides: { ...entry.overrides },
      results: null,
      error: null,
      ms: null,
    };
  }

  function mockResults(name) {
    const table = {
      Conservador: {
        montoUsd: 84200, unidades: 18420, renglones: 910, nCambios: 42,
        ahorroCantidadUsd: 320, ahorroSucedaneoUsd: 180, ahorroTotalUsd: 500,
        topProveedor: 'DROG. CENTRAL',
      },
      Normal: {
        montoUsd: 91850, unidades: 20110, renglones: 938, nCambios: 186,
        ahorroCantidadUsd: 2100, ahorroSucedaneoUsd: 3400, ahorroTotalUsd: 5500,
        topProveedor: 'FARMATODO DIST',
      },
      Agresivo: {
        montoUsd: 104400, unidades: 23480, renglones: 972, nCambios: 311,
        ahorroCantidadUsd: 4800, ahorroSucedaneoUsd: 9200, ahorroTotalUsd: 14000,
        topProveedor: 'FARMATODO DIST',
      },
    };
    const base = table[name] || {
      montoUsd: 90000 + Math.round(Math.random() * 8000),
      unidades: 19000, renglones: 920, nCambios: 100,
      ahorroCantidadUsd: 1000, ahorroSucedaneoUsd: 2000, ahorroTotalUsd: 3000,
      topProveedor: '—',
    };
    return { ...base };
  }

  function mockSencillo() {
    return {
      montoUsd: 83000, unidades: 18240, renglones: 900,
      ahorroTotalUsd: 0, ahorroCantidadUsd: 0, ahorroSucedaneoUsd: 0,
      nCambios: 0, topProveedor: '—',
    };
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
    let baseLines = 0;

    comp.forEach((row) => {
      const qb = Number(row.qty_baseline) || 0;
      const qp = Number(row.qty_propuesto) || 0;
      baseUnits += qb;
      units += qp;
      if (qb > 0) baseLines += 1;
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
    const meta = data.meta || {};
    const motors = meta.ahorros_motores || [];
    const byCode = Object.fromEntries(motors.map((m) => [String(m.codigo || ''), m]));
    const roundMoney = (v) => (v == null || Number.isNaN(Number(v)) ? null : Math.round(Number(v)));
    const results = {
      montoUsd: priced ? Math.round(monto) : null,
      unidades: Math.round(units),
      renglones: prop.length || comp.filter((r) => (Number(r.qty_propuesto) || 0) > 0).length,
      ahorroCantidadUsd: roundMoney(byCode.cantidad_vs_historico?.usd ?? 0),
      ahorroSucedaneoUsd: roundMoney(byCode.sucedaneo?.usd ?? 0),
      ahorroTotalUsd: roundMoney(meta.ahorro_total_usd ?? 0),
      nCambios,
      topProveedor: top ? top[0] : '—',
    };
    const sencillo = {
      montoUsd: basePriced ? Math.round(baseMonto) : null,
      unidades: Math.round(baseUnits),
      renglones: baseLines,
      ahorroCantidadUsd: 0,
      ahorroSucedaneoUsd: 0,
      ahorroTotalUsd: 0,
      nCambios: 0,
      topProveedor: '—',
    };
    return { results, sencillo };
  }

  function readFormPayloadBase() {
    if (typeof window.__protoBuildSencilloPayload === 'function') {
      const p = window.__protoBuildSencilloPayload();
      if (p) {
        const { preset: _i, ...rest } = p;
        return rest;
      }
    }
    const criterios = [];
    document.querySelectorAll('#criteriosAgrupacion input[type=checkbox]:checked').forEach((el) => {
      if (el.value) criterios.push(el.value);
    });
    let categorias = [];
    if (typeof window.__protoGetSelectedCategories === 'function') {
      categorias = window.__protoGetSelectedCategories() || [];
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

  function slotsAreDistinct() {
    const s = [slots.presente, slots.comp1, slots.comp2];
    return new Set(s).size === 3;
  }

  async function fetchCustomPool() {
    try {
      const r = await fetch('/api/pedidos/presets');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      customPool = (data.presets || []).map((p) => {
        const base = p.base_preset || 'Normal';
        const overrides = p.overrides || {};
        return {
          id: String(p.preset_id),
          name: p.nombre || `Preset ${p.preset_id}`,
          base_preset: base,
          overrides,
          knobs: { ...PRESET_DEFS[base], ...overrides },
        };
      });
    } catch (_e) {
      /* keep local customs */
    }
  }

  async function runOneEntry(entry, base) {
    const t0 = performance.now();
    let response;
    if (entry.kind === 'custom' && Object.keys(entry.overrides || {}).length) {
      response = await fetch('/api/pedidos/regenerar-definitivo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...base,
          nivel: 'Avanzado',
          base_preset: entry.base_preset,
          overrides: entry.overrides,
          categorias: base.categorias,
        }),
      });
    } else {
      response = await fetch('/api/pedidos/generar-sencillo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...base,
          preset: entry.base_preset,
          categorias: base.categorias,
        }),
      });
    }
    const ms = Math.round(performance.now() - t0);
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${response.status} (${entry.name})`);
    }
    const data = await response.json();
    const sum = summarizeApiResult(data);
    return {
      ...emptyRun(entry),
      knobs: { ...entry.knobs },
      results: sum.results,
      sencillo: sum.sencillo,
      ms,
    };
  }

  async function runTriple() {
    if (!slotsAreDistinct()) {
      session.message = 'Presente, Comp1 y Comp2 deben ser tres presets distintos.';
      session.status = 'error';
      render({ scroll: false });
      return;
    }

    // Apply drawer draft onto Presente if it's a base or update knobs for run
    const entries = slotIds().map((s) => {
      const e = resolveEntry(s.key);
      if (s.id === 'presente') {
        e.knobs = { ...presenteDraft };
        // Treat draft diffs vs base as overrides for custom-like run
        const baseKnobs = PRESET_DEFS[e.base_preset] || PRESET_DEFS.Normal;
        const overrides = {};
        KNOB_META.forEach((m) => {
          if (!valuesEqual(presenteDraft[m.key], baseKnobs[m.key])) {
            overrides[m.key] = presenteDraft[m.key];
          }
        });
        if (Object.keys(overrides).length) {
          e.kind = 'custom';
          e.overrides = overrides;
        }
      }
      return { slotId: s.id, entry: e };
    });

    session.status = 'running';
    session.message = 'Disparando 3 corridas (laboratorio — no toca Comparativa)…';
    session.runsBySlot = {};
    session.sencillo = null;
    render({ scroll: false });

    const base = readFormPayloadBase();
    const categorias = base.categorias || [];

    if (!categorias.length) {
      session.source = 'mock';
      session.message = 'Sin categorías. 3 mocks + Sencillo baseline (laboratorio).';
      await delay(400);
      session.sencillo = mockSencillo();
      entries.forEach(({ slotId, entry }) => {
        session.runsBySlot[slotId] = {
          ...emptyRun(entry),
          knobs: slotId === 'presente' ? { ...presenteDraft } : entry.knobs,
          results: mockResults(entry.base_preset),
          ms: 100 + Math.round(Math.random() * 80),
        };
      });
      session.status = 'ready';
      render({ scroll: false });
      return;
    }

    try {
      const settled = await Promise.all(entries.map(async ({ slotId, entry }) => {
        const run = await runOneEntry(entry, base);
        if (slotId === 'presente') run.knobs = { ...presenteDraft };
        return { slotId, run };
      }));
      settled.forEach(({ slotId, run }) => {
        session.runsBySlot[slotId] = run;
        if (run.sencillo && !session.sencillo) session.sencillo = run.sencillo;
      });
      // Prefer average/first sencillo — all should match if same form
      session.sencillo = settled[0].run.sencillo || session.sencillo;
      session.source = 'api';
      session.status = 'ready';
      session.message = `3 corridas OK (${settled.map(({ run }) => `${run.name} ${run.ms}ms`).join(' · ')}). Comparativa Pedidos intacta.`;
    } catch (err) {
      session.source = 'mock';
      session.message = `API falló (${err.message}). Fallback mock.`;
      session.sencillo = mockSencillo();
      entries.forEach(({ slotId, entry }) => {
        session.runsBySlot[slotId] = {
          ...emptyRun(entry),
          knobs: slotId === 'presente' ? { ...presenteDraft } : entry.knobs,
          results: mockResults(entry.base_preset),
          ms: null,
        };
      });
      session.status = 'ready';
    }
    render({ scroll: false });
  }

  function delay(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function fmtMeta(meta, v) {
    if (v === null || v === undefined) return '—';
    if (meta.format === 'bool') return v ? 'Sí' : 'No';
    if (meta.format === 'weight' || meta.format === 'num') {
      if (typeof v === 'number') return Number.isInteger(v) ? String(v) : String(v);
      return String(v);
    }
    if (meta.format === 'money') return `$${Number(v).toLocaleString('en-US')}`;
    if (meta.format === 'money_delta') {
      const n = Number(v);
      const s = `$${Math.abs(n).toLocaleString('en-US')}`;
      return n > 0 ? `+${s}` : n < 0 ? `−${s}` : s;
    }
    if (meta.format === 'int') return Number(v).toLocaleString('es-VE');
    return String(v);
  }

  function deltaVs(sencilloVal, runVal, meta) {
    if (typeof sencilloVal !== 'number' || typeof runVal !== 'number') return null;
    if (meta.format === 'text' || meta.format === 'bool') return null;
    return runVal - sencilloVal;
  }

  function valuesEqual(a, b) {
    return a === b || (typeof a === 'number' && typeof b === 'number' && Math.abs(a - b) < 1e-9);
  }

  function getVariant() {
    const v = (new URLSearchParams(window.location.search).get('variant') || 'A').toUpperCase();
    return VARIANTS.some((x) => x.key === v) ? v : 'A';
  }

  function isActive() {
    return new URLSearchParams(window.location.search).get(PARAM) === VALUE;
  }

  function activatePrototype(variant) {
    const url = new URL(window.location.href);
    url.searchParams.set(PARAM, VALUE);
    url.searchParams.set('variant', variant || 'A');
    window.history.replaceState({}, '', url);
    render({ scroll: true });
  }

  function setVariant(key) {
    const url = new URL(window.location.href);
    url.searchParams.set(PARAM, VALUE);
    url.searchParams.set('variant', key);
    window.history.replaceState({}, '', url);
    render({ scroll: false });
  }

  function dismissBlockers() {
    const cat = document.getElementById('categoriesModal');
    if (cat) {
      cat.classList.remove('active');
      cat.setAttribute('aria-hidden', 'true');
    }
    const bandeja = document.getElementById('bandejaModal');
    if (bandeja) {
      bandeja.classList.remove('active', 'open', 'show');
      bandeja.setAttribute('aria-hidden', 'true');
      bandeja.style.display = 'none';
    }
  }

  function ensureHost() {
    let host = document.getElementById('prototypeComparePresets');
    if (!host) {
      host = document.createElement('section');
      host.id = 'prototypeComparePresets';
      host.className = 'section-card proto-compare';
      host.style.display = 'none';
      const config = document.getElementById('configSection');
      if (config?.parentNode) config.parentNode.insertBefore(host, config.nextSibling);
      else document.querySelector('.main-content')?.appendChild(host);
    }
    return host;
  }

  function ensureStickyBanner(active) {
    let ban = document.getElementById('protoStickyBanner');
    if (!ban) {
      ban = document.createElement('div');
      ban.id = 'protoStickyBanner';
      ban.className = 'proto-sticky-banner';
      ban.innerHTML = `
        <span><strong>PROTOTYPE</strong> · Lab comparar presets</span>
        <button type="button" id="protoBannerJump">Ir al panel ↓</button>`;
      document.body.appendChild(ban);
      ban.querySelector('#protoBannerJump').addEventListener('click', () => {
        document.getElementById('prototypeComparePresets')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    }
    ban.style.display = active ? 'flex' : 'none';
  }

  function ensureEntryControls() {
    if (document.getElementById('protoCompareEntryBtn')) return;
    const form = document.getElementById('generateForm');
    if (!form) return;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'protoCompareEntryBtn';
    btn.className = 'btn btn-secondary proto-entry-btn';
    btn.innerHTML = 'PROTOTYPE · Comparar 3 presets';
    btn.addEventListener('click', () => {
      dismissBlockers();
      const body = document.getElementById('configBody');
      if (body) body.classList.add('collapsed');
      activatePrototype('A');
    });
    form.appendChild(btn);
  }

  function focusPrototypePanel(scroll) {
    if (!scroll) return;
    dismissBlockers();
    const body = document.getElementById('configBody');
    if (body) body.classList.add('collapsed');
    requestAnimationFrame(() => {
      document.getElementById('prototypeComparePresets')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  function escapeHtml(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function optionHtml(selected) {
    return poolOptions().map((o) =>
      `<option value="${escapeHtml(o.key)}" ${o.key === selected ? 'selected' : ''}>${escapeHtml(o.label)}</option>`
    ).join('');
  }

  function cellWithDeltaClean(meta, sencilloBag, runBag) {
    const val = runBag ? runBag[meta.key] : null;
    const sen = sencilloBag ? sencilloBag[meta.key] : null;
    const d = deltaVs(sen, val, meta);
    let deltaLine = '';
    if (d != null && meta.format !== 'text' && meta.format !== 'bool') {
      if (meta.format === 'money' || meta.format === 'money_delta') {
        deltaLine = `<div class="proto-cell-delta">Δ ${escapeHtml(fmtMeta({ format: 'money_delta' }, d))}</div>`;
      } else {
        const n = Math.round(d);
        const t = n > 0 ? `+${n.toLocaleString('es-VE')}` : n < 0 ? `−${Math.abs(n).toLocaleString('es-VE')}` : '0';
        deltaLine = `<div class="proto-cell-delta">Δ ${t}</div>`;
      }
    }
    return `<td class="proto-cell-stack"><div class="proto-cell-val">${escapeHtml(fmtMeta(meta, val))}</div>${deltaLine}</td>`;
  }

  function openDrawer(open) {
    const d = document.getElementById('protoDrawer');
    const scrim = document.getElementById('protoDrawerScrim');
    if (!d || !scrim) return;
    d.classList.toggle('is-open', open);
    scrim.classList.toggle('is-open', open);
    d.setAttribute('aria-hidden', open ? 'false' : 'true');
  }

  function paintDrawerFields() {
    const host = document.getElementById('protoDrawerFields');
    if (!host) return;
    const e = resolveEntry(slots.presente);
    host.innerHTML = `
      <p class="proto-sub">Editando knobs del <strong>Presente</strong> (${escapeHtml(e.name)}). Cobertura/categorías siguen arriba.</p>
      <div class="proto-drawer-grid">
        ${KNOB_META.map((m) => {
          const v = presenteDraft[m.key];
          if (m.format === 'bool') {
            return `<label class="proto-drawer-field"><span>${escapeHtml(m.label)}</span>
              <input type="checkbox" data-knob="${m.key}" ${v ? 'checked' : ''}></label>`;
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
        <input type="text" id="protoCustomName" class="form-control" placeholder="Nombre preset personalizado" style="flex:1;min-width:140px;height:40px;">
        <button type="button" class="btn btn-secondary" id="protoSaveCustom" style="height:40px;">Guardar en pool</button>
        <button type="button" class="btn btn-secondary" id="protoResetDraft" style="height:40px;">Reset a base</button>
      </div>`;

    host.querySelectorAll('[data-knob]').forEach((el) => {
      const key = el.getAttribute('data-knob');
      const handler = () => {
        if (el.type === 'checkbox') presenteDraft[key] = el.checked;
        else if (el.tagName === 'SELECT') presenteDraft[key] = el.value;
        else {
          const n = Number(el.value);
          presenteDraft[key] = Number.isNaN(n) ? el.value : n;
        }
      };
      el.addEventListener('change', handler);
      el.addEventListener('input', handler);
    });

    host.querySelector('#protoResetDraft')?.addEventListener('click', () => {
      const base = resolveEntry(slots.presente);
      presenteDraft = { ...(PRESET_DEFS[base.base_preset] || PRESET_DEFS.Normal) };
      paintDrawerFields();
    });

    host.querySelector('#protoSaveCustom')?.addEventListener('click', async () => {
      const nombre = (host.querySelector('#protoCustomName')?.value || '').trim();
      if (!nombre) {
        session.message = 'Indique un nombre para guardar el preset.';
        render({ scroll: false });
        return;
      }
      const base = resolveEntry(slots.presente);
      const overrides = {};
      const baseKnobs = PRESET_DEFS[base.base_preset] || PRESET_DEFS.Normal;
      KNOB_META.forEach((m) => {
        if (!valuesEqual(presenteDraft[m.key], baseKnobs[m.key])) overrides[m.key] = presenteDraft[m.key];
      });
      try {
        const r = await fetch('/api/pedidos/presets', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nombre,
            nivel: 'Avanzado',
            base_preset: base.base_preset,
            overrides,
          }),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const saved = await r.json();
        await fetchCustomPool();
        slots.presente = `custom:${saved.preset_id}`;
        syncPresenteDraftFromSlot();
        session.message = `Preset «${nombre}» guardado en el pool.`;
        render({ scroll: false });
        openDrawer(true);
      } catch (err) {
        // Local-only fallback
        const id = `local-${Date.now()}`;
        customPool.push({
          id,
          name: nombre,
          base_preset: base.base_preset,
          overrides,
          knobs: { ...presenteDraft },
        });
        slots.presente = `custom:${id}`;
        session.message = `Preset «${nombre}» en pool local (API no disponible).`;
        render({ scroll: false });
        openDrawer(true);
      }
    });
  }

  function VariantA(root) {
    const busy = session.status === 'running';
    const sen = session.sencillo;
    const runs = {
      presente: session.runsBySlot.presente,
      comp1: session.runsBySlot.comp1,
      comp2: session.runsBySlot.comp2,
    };

    root.innerHTML = `
      <header class="proto-head">
        <div>
          <p class="proto-badge">PROTOTYPE · A — Wireframe 3</p>
          <h3>Lab · Sencillo vs 3 presets</h3>
          <p class="proto-sub">Presente + Comp1 + Comp2 (pool base/custom). Mesa 4 columnas. Drawer ⚙ = knobs del Presente.</p>
        </div>
        <div class="proto-head-actions">
          <button type="button" class="btn btn-secondary" id="protoOpenDrawer" style="height:40px;">⚙ Config knobs</button>
          <button type="button" class="btn btn-primary proto-run-btn" id="protoRunTriple" ${busy ? 'disabled' : ''}>
            ${busy ? 'Corriendo 3…' : 'Correr 3 presets'}
          </button>
        </div>
      </header>
      <p class="proto-status" data-src="${session.source}">${escapeHtml(session.message)}</p>

      <div class="proto-diff-pickers">
        <div class="input-group"><label>Presente</label>
          <select id="protoPresente" class="form-control">${optionHtml(slots.presente)}</select></div>
        <div class="proto-arrow">→</div>
        <div class="input-group"><label>Comparar con</label>
          <select id="protoComp1" class="form-control">${optionHtml(slots.comp1)}</select></div>
        <div class="input-group"><label>Comparar con</label>
          <select id="protoComp2" class="form-control">${optionHtml(slots.comp2)}</select></div>
        <div class="input-group"><label>KPI foco</label>
          <select id="protoKpi" class="form-control">
            ${RESULT_META.map((m) => `<option value="${m.key}" ${m.key === slots.focusKpi ? 'selected' : ''}>${escapeHtml(m.label)}</option>`).join('')}
          </select></div>
      </div>

      <div class="proto-scroll">
        <table class="proto-matrix" id="protoKpiTable">
          <thead>
            <tr>
              <th>KPI</th>
              <th>Sencillo</th>
              <th>Presente</th>
              <th>Comp1</th>
              <th>Comp2</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>

      <div class="proto-scroll" style="margin-top:0.75rem;">
        <table class="proto-matrix" id="protoVarTable">
          <thead>
            <tr>
              <th>Variable</th>
              <th>Presente</th>
              <th>Comp1</th>
              <th>Comp2</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>

      <div id="protoDrawerScrim" class="proto-drawer-scrim" aria-hidden="true"></div>
      <aside id="protoDrawer" class="proto-drawer" aria-hidden="true">
        <div class="proto-drawer-head">
          <strong>⚙ Knobs · Presente</strong>
          <button type="button" class="btn btn-secondary" id="protoCloseDrawer" style="padding:0.25rem 0.6rem;">×</button>
        </div>
        <div id="protoDrawerFields"></div>
      </aside>

      <pre class="proto-state">${escapeHtml(JSON.stringify({
        slots, status: session.status, source: session.source,
        sencillo: session.sencillo,
        runs: session.runsBySlot,
        presenteDraft,
        pool: poolOptions().map((o) => o.key),
      }, null, 2))}</pre>`;

    // KPI table body
    const kpiBody = root.querySelector('#protoKpiTable tbody');
    kpiBody.innerHTML = RESULT_META.map((m) => {
      const focus = m.key === slots.focusKpi ? 'proto-kpi-focus-row' : '';
      const senVal = sen ? sen[m.key] : null;
      return `<tr class="${focus}">
        <td>${escapeHtml(m.label)}</td>
        <td>${escapeHtml(fmtMeta(m, senVal))}</td>
        ${cellWithDeltaClean(m, sen, runs.presente?.results)}
        ${cellWithDeltaClean(m, sen, runs.comp1?.results)}
        ${cellWithDeltaClean(m, sen, runs.comp2?.results)}
      </tr>`;
    }).join('');

    // Vars table
    const varBody = root.querySelector('#protoVarTable tbody');
    const kP = runs.presente?.knobs || presenteDraft;
    const k1 = runs.comp1?.knobs || resolveEntry(slots.comp1).knobs;
    const k2 = runs.comp2?.knobs || resolveEntry(slots.comp2).knobs;
    varBody.innerHTML = KNOB_META.map((m) => {
      const vals = [kP[m.key], k1[m.key], k2[m.key]];
      const diff = !valuesEqual(vals[0], vals[1]) || !valuesEqual(vals[0], vals[2]);
      return `<tr class="${diff ? 'proto-diff-row' : ''}">
        <td>${escapeHtml(m.label)}</td>
        <td>${escapeHtml(fmtMeta(m, vals[0]))}</td>
        <td class="${!valuesEqual(vals[0], vals[1]) ? 'proto-cell-diff' : ''}">${escapeHtml(fmtMeta(m, vals[1]))}</td>
        <td class="${!valuesEqual(vals[0], vals[2]) ? 'proto-cell-diff' : ''}">${escapeHtml(fmtMeta(m, vals[2]))}</td>
      </tr>`;
    }).join('');

    root.querySelector('#protoRunTriple')?.addEventListener('click', () => runTriple());
    root.querySelector('#protoOpenDrawer')?.addEventListener('click', () => {
      paintDrawerFields();
      openDrawer(true);
    });
    root.querySelector('#protoCloseDrawer')?.addEventListener('click', () => openDrawer(false));
    root.querySelector('#protoDrawerScrim')?.addEventListener('click', () => openDrawer(false));

    const bindSlot = (selId, field) => {
      const el = root.querySelector(selId);
      if (!el) return;
      el.addEventListener('change', () => {
        slots[field] = el.value;
        if (field === 'presente') syncPresenteDraftFromSlot();
        if (!slotsAreDistinct()) {
          session.message = 'Los tres slots deben ser distintos.';
        }
        render({ scroll: false });
      });
    };
    bindSlot('#protoPresente', 'presente');
    bindSlot('#protoComp1', 'comp1');
    bindSlot('#protoComp2', 'comp2');
    root.querySelector('#protoKpi')?.addEventListener('change', (e) => {
      slots.focusKpi = e.target.value;
      render({ scroll: false });
    });
  }

  // Legacy B/C thin wrappers for switcher contrast
  function VariantB(root) {
    root.innerHTML = `<p class="proto-sub">Variant B legacy — use <strong>A</strong> (Wireframe 3).</p>`;
    VariantA(root);
  }
  function VariantC(root) {
    root.innerHTML = `<p class="proto-sub">Variant C legacy — use <strong>A</strong> (Wireframe 3).</p>`;
    VariantA(root);
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

  function render(opts) {
    const scroll = !!(opts && opts.scroll);
    ensureEntryControls();
    const host = ensureHost();
    const bar = ensureSwitcher();
    const active = isActive();
    host.style.display = active ? 'block' : 'none';
    bar.style.display = active ? 'flex' : 'none';
    ensureStickyBanner(active);
    if (!active) return;

    const v = getVariant();
    bar.querySelector('#protoLabel').textContent = `${v} — ${VARIANTS.find((x) => x.key === v).name}`;
    host.innerHTML = '';
    if (v === 'A') VariantA(host);
    else if (v === 'B') VariantB(host);
    else VariantC(host);
    focusPrototypePanel(scroll);
  }

  const style = document.createElement('style');
  style.textContent = `
    .proto-compare { margin-top:0.5rem; border:2px dashed var(--primary-accent) !important; scroll-margin-top:4.5rem; padding:1rem !important; background:rgba(139,58,74,0.06) !important; }
    .proto-sticky-banner { position:fixed; top:0; left:0; right:0; z-index:10001; display:none; align-items:center; justify-content:center; gap:1rem; flex-wrap:wrap; padding:0.55rem 1rem; background:#8b3a4a; color:#fff; font-size:0.85rem; font-weight:600; }
    .proto-sticky-banner button { background:#fff; color:#8b3a4a; border:none; padding:0.35rem 0.75rem; font-weight:700; cursor:pointer; }
    .proto-entry-btn { width:100%; margin-top:0.65rem; height:40px; border:2px dashed var(--primary-accent) !important; color:var(--primary-accent) !important; font-weight:700; }
    .proto-head { display:flex; justify-content:space-between; gap:1rem; flex-wrap:wrap; margin-bottom:0.75rem; align-items:flex-start; }
    .proto-head-actions { display:flex; gap:0.5rem; flex-wrap:wrap; }
    .proto-badge { font-size:0.7rem; letter-spacing:0.08em; color:var(--primary-accent); font-weight:700; margin:0 0 0.25rem; }
    .proto-compare h3 { margin:0; font-family:var(--font-display); font-size:1.25rem; }
    .proto-sub { margin:0.25rem 0 0; color:var(--text-secondary); font-size:0.85rem; }
    .proto-status { font-size:0.8rem; padding:0.45rem 0.65rem; border:1px solid var(--border-subtle); margin-bottom:0.85rem; color:var(--text-secondary); }
    .proto-status[data-src="api"] { border-color:var(--success); color:var(--success); }
    .proto-status[data-src="mock"] { border-color:var(--warning); color:var(--warning); }
    .proto-run-btn { height:40px; white-space:nowrap; font-weight:700; }
    .proto-diff-pickers { display:flex; align-items:end; gap:0.65rem; flex-wrap:wrap; margin-bottom:0.85rem; }
    .proto-diff-pickers .input-group { flex:1; min-width:130px; margin:0; }
    .proto-arrow { font-size:1.4rem; color:var(--text-muted); padding-bottom:0.35rem; }
    .proto-scroll { overflow:auto; max-height:340px; border:1px solid var(--border-subtle); }
    .proto-matrix { width:100%; border-collapse:collapse; font-size:0.8rem; font-family:var(--font-mono); }
    .proto-matrix th, .proto-matrix td { padding:0.4rem 0.55rem; border-bottom:1px solid var(--border-subtle); text-align:left; vertical-align:top; }
    .proto-matrix th { position:sticky; top:0; background:var(--bg-surface); z-index:1; }
    .proto-diff-row { background:rgba(139,58,74,0.08); }
    .proto-cell-diff { color:var(--warning); font-weight:600; }
    .proto-cell-stack { line-height:1.25; }
    .proto-cell-val { font-weight:600; }
    .proto-cell-delta { font-size:0.72rem; color:var(--warning); margin-top:0.15rem; }
    .proto-kpi-focus-row { outline:1px solid var(--primary-accent); background:rgba(139,58,74,0.1); }
    .proto-drawer-scrim { display:none; position:fixed; inset:0; background:rgba(0,0,0,0.45); z-index:10002; }
    .proto-drawer-scrim.is-open { display:block; }
    .proto-drawer {
      position:fixed; top:0; right:0; width:min(420px,100vw); height:100vh; z-index:10003;
      background:var(--bg-surface); border-left:2px solid var(--primary-accent);
      transform:translateX(100%); transition:transform 0.2s ease; overflow:auto; padding:1rem;
    }
    .proto-drawer.is-open { transform:translateX(0); }
    .proto-drawer-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem; }
    .proto-drawer-grid { display:flex; flex-direction:column; gap:0.55rem; }
    .proto-drawer-field { display:flex; flex-direction:column; gap:0.2rem; font-size:0.8rem; color:var(--text-secondary); }
    .proto-drawer-actions { display:flex; flex-wrap:wrap; gap:0.5rem; margin-top:1rem; }
    .proto-state { margin-top:1rem; font-size:0.7rem; max-height:140px; overflow:auto; background:rgba(0,0,0,0.25); padding:0.65rem; color:var(--text-secondary); border:1px solid var(--border-subtle); }
    .proto-switcher {
      position:fixed; bottom:1.25rem; left:50%; transform:translateX(-50%); z-index:9999;
      display:none; align-items:center; gap:0.75rem; padding:0.55rem 0.9rem;
      background:#111; color:#f5f5f5; border:2px solid #f5f5f5; box-shadow:0 8px 24px rgba(0,0,0,0.45);
      font-family:var(--font-mono); font-size:0.8rem; font-weight:600;
    }
    .proto-switcher button { background:transparent; border:1px solid #666; color:#f5f5f5; width:2rem; height:2rem; cursor:pointer; font-size:1rem; }
    #protoLabel { min-width:11rem; text-align:center; }
  `;
  document.head.appendChild(style);

  async function boot() {
    await fetchCustomPool();
    syncPresenteDraftFromSlot();
    render({ scroll: isActive() });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
