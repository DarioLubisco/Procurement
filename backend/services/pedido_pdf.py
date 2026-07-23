"""Generate pedido PDF (mobile-readable, desvíos vs Sencillo) — ADR-0030."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from analytics_engine.core.borrador_snapshot import build_desviacion_rows, count_desviaciones

# Shared visual language with FE Comparativa (barra cambio / sucedáneo).
# Web CSS: --barra-cambio / .barra-cambio  (modulo_pedidos.html)
BARRA_CAMBIO_BG = colors.HexColor("#f3dcc4")
BARRA_CAMBIO_FG = colors.HexColor("#8a4b1a")
BARRA_CAMBIO_EDGE = colors.HexColor("#c4783a")
QTY_DELTA_BG = colors.HexColor("#e8eef7")
HEADER_BG = colors.HexColor("#2d313a")
ACCENT = colors.HexColor("#8b3a4a")


def _esc(text: Any) -> str:
    """Escape user/DB text for ReportLab Paragraph (XML)."""
    s = str(text if text is not None else "")
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _p(text: Any, style: ParagraphStyle, *, markup: bool = False) -> Paragraph:
    s = str(text if text is not None else "")
    if not markup:
        s = _esc(s)
    return Paragraph(s, style)


def _is_barra_cambio(row: Dict[str, Any]) -> bool:
    bb = str(row.get("barra_baseline") or "").strip()
    bp = str(row.get("barra_propuesto") or "").strip()
    motivos = row.get("desviacion_motivos") or []
    if "sucedaneo" in motivos:
        return True
    return bool(bb and bp and bb != bp)


def _motivo_labels(motivos: Sequence[str]) -> str:
    map_ = {
        "sucedaneo": "Cambio de barra",
        "delta_qty": "Δ cantidad",
        "alta_propuesto": "Alta (solo propuesto)",
        "baja_baseline": "Baja (solo baseline)",
    }
    return " · ".join(map_.get(m, m) for m in motivos) or "Desvío"


def build_pedido_pdf_bytes(
    *,
    propuesta_id: int,
    cod_prov: str,
    estado: str,
    revision: int,
    snapshot_hash: Optional[str],
    comparativa: Sequence[Dict[str, Any]],
    propuesto: Sequence[Dict[str, Any]],
    monto_total_usd: Optional[float] = None,
    synapse_link: Optional[str] = None,
) -> bytes:
    """
    Phone-first PDF (A5): cabecera → desvíos en tarjetas → líneas propuesto.
    Barra distinta vs Sencillo se resalta (mismo tono que FE .barra-cambio).
    """
    buf = io.BytesIO()
    # A5 portrait ≈ readable on phone when zoomed; generous margins
    page = A5
    doc = SimpleDocTemplate(
        buf,
        pagesize=page,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=f"Pedido {propuesta_id} {cod_prov}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "H1m",
        parent=styles["Heading1"],
        fontSize=13,
        leading=16,
        spaceAfter=6,
        textColor=ACCENT,
    )
    h2 = ParagraphStyle(
        "H2m",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        spaceBefore=10,
        spaceAfter=6,
        textColor=HEADER_BG,
    )
    body = ParagraphStyle(
        "Bodym", parent=styles["Normal"], fontSize=9, leading=12, spaceAfter=2
    )
    small = ParagraphStyle(
        "Smallm",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#444444"),
    )
    mono = ParagraphStyle(
        "Monom",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Courier",
        leading=10,
    )
    card_title = ParagraphStyle(
        "CardTitle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=HEADER_BG,
        spaceAfter=2,
    )
    badge = ParagraphStyle(
        "Badge",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=BARRA_CAMBIO_FG,
    )

    desv_rows = build_desviacion_rows(comparativa)
    n_desv = count_desviaciones(comparativa)
    n_prop = sum(1 for r in propuesto if int(r.get("cantidad") or 0) > 0)
    hash_short = (snapshot_hash or "")[:12]
    n_barra = sum(1 for r in desv_rows if _is_barra_cambio(r))
    n_qty = sum(
        1
        for r in desv_rows
        if "delta_qty" in (r.get("desviacion_motivos") or []) and not _is_barra_cambio(r)
    )

    story: List[Any] = []
    story.append(_p(f"Synapse · Pedido #{propuesta_id}", h1))
    story.append(
        _p(
            f"<b>{_esc(cod_prov)}</b><br/>"
            f"Estado <b>{_esc(estado)}</b> · Rev <b>{revision}</b><br/>"
            f"Hash <font face='Courier'>{_esc(hash_short)}…</font>",
            body,
            markup=True,
        )
    )
    meta_bits = [
        f"Generado {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Líneas: <b>{n_prop}</b>",
        f"Desvíos vs Sencillo: <b>{n_desv}</b>",
    ]
    if n_barra:
        meta_bits.append(f"cambio barra: <b>{n_barra}</b>")
    if n_qty:
        meta_bits.append(f"solo Δqty: <b>{n_qty}</b>")
    story.append(_p(" · ".join(meta_bits), small, markup=True))
    if monto_total_usd is not None:
        story.append(
            _p(f"Monto estimado USD: <b>{monto_total_usd:,.2f}</b>", body, markup=True)
        )
    if synapse_link:
        story.append(_p(f"Synapse: {_esc(synapse_link)}", small, markup=True))

    # Legend
    if n_desv:
        story.append(Spacer(1, 4))
        legend = Table(
            [
                [
                    _p("<b>Leyenda</b>", small, markup=True),
                    _p(
                        "<font color='#8a4b1a'><b>■ Cambio de barra</b></font> (sucedáneo)",
                        small,
                        markup=True,
                    ),
                    _p("■ Solo Δ cantidad", small),
                ]
            ],
            colWidths=[doc.width * 0.18, doc.width * 0.42, doc.width * 0.40],
        )
        legend.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (1, 0), (1, 0), BARRA_CAMBIO_BG),
                    ("BACKGROUND", (2, 0), (2, 0), QTY_DELTA_BG),
                    ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(legend)

    # —— Desvíos as stacked cards (phone-friendly) ——
    story.append(_p("Desviaciones vs Pedido Sencillo", h2))
    if not desv_rows:
        story.append(
            _p(
                "Sin desviaciones: qty y producto alineados al baseline Sencillo.",
                body,
            )
        )
    else:
        story.append(
            _p(
                "Cada tarjeta es una línea distinta del Pedido Sencillo. "
                "Si el código de barras cambió, la barra propuesta va resaltada.",
                small,
            )
        )
        for i, row in enumerate(desv_rows, start=1):
            story.append(_desvio_card(row, i, doc.width, card_title, badge, body, small, mono))
            story.append(Spacer(1, 5))

    # —— Propuesto lines ——
    story.append(_p("Pedido propuesto (líneas)", h2))
    prop_lines = []
    for r in propuesto:
        try:
            qty = int(r.get("cantidad") or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0:
            continue
        prop_lines.append(r)

    if not prop_lines:
        story.append(_p("Sin líneas con cantidad > 0.", body))
    else:
        # Map barra → is sucedaneo from comparativa for highlighting in propuesto list
        cambio_barras = {
            str(r.get("barra_propuesto") or "").strip()
            for r in desv_rows
            if _is_barra_cambio(r)
        }
        header = [
            _p("<b>#</b>", small, markup=True),
            _p("<b>BARRA</b>", small, markup=True),
            _p("<b>Descripción</b>", small, markup=True),
            _p("<b>Cant.</b>", small, markup=True),
            _p("<b>Total</b>", small, markup=True),
        ]
        data = [header]
        row_styles: List[Tuple] = []
        for idx, r in enumerate(prop_lines, start=1):
            barra = str(r.get("barra") or "")
            try:
                qty = int(r.get("cantidad") or 0)
            except (TypeError, ValueError):
                qty = 0
            try:
                precio = float(r.get("precio")) if r.get("precio") is not None else None
            except (TypeError, ValueError):
                precio = None
            total = (qty * precio) if precio is not None else None
            desc = str(r.get("descripcion") or r.get("descrip") or "")[:70]
            is_cambio = barra.strip() in cambio_barras
            barra_cell = (
                _p(f"<b>{_esc(barra)}</b>", mono, markup=True)
                if is_cambio
                else _p(barra, mono)
            )
            data.append(
                [
                    _p(str(idx), small),
                    barra_cell,
                    _p(desc, small),
                    _p(str(qty), small),
                    _p(f"{total:.2f}" if total is not None else "—", small),
                ]
            )
            if is_cambio:
                # data row index in table = idx (header is 0)
                row_styles.append(
                    ("BACKGROUND", (1, idx), (1, idx), BARRA_CAMBIO_BG)
                )
                row_styles.append(
                    ("TEXTCOLOR", (1, idx), (1, idx), BARRA_CAMBIO_FG)
                )

        tw = doc.width
        pt = Table(
            data,
            colWidths=[0.07 * tw, 0.28 * tw, 0.37 * tw, 0.12 * tw, 0.16 * tw],
            repeatRows=1,
        )
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bbbbbb")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#faf7f5")],
            ),
            ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        style_cmds.extend(row_styles)
        pt.setStyle(TableStyle(style_cmds))
        story.append(pt)

    story.append(Spacer(1, 8))
    story.append(
        _p(
            f"Telegram approve: revision={revision} hash={hash_short}… "
            "(si la web guarda, el hash cambia y los botones quedan inválidos).",
            mono,
        )
    )
    doc.build(story)
    return buf.getvalue()


def _desvio_card(
    row: Dict[str, Any],
    index: int,
    width: float,
    card_title: ParagraphStyle,
    badge: ParagraphStyle,
    body: ParagraphStyle,
    small: ParagraphStyle,
    mono: ParagraphStyle,
) -> Table:
    motivos = list(row.get("desviacion_motivos") or [])
    barra_cambio = _is_barra_cambio(row)
    bb = str(row.get("barra_baseline") or "—")
    bp = str(row.get("barra_propuesto") or "—")
    qb = row.get("qty_baseline")
    qp = row.get("qty_propuesto")
    db = str(row.get("desc_baseline") or "")[:90]
    dp = str(row.get("desc_propuesto") or "")[:90]
    just = str(row.get("justificacion_delta") or "").strip()[:220]

    rows_data = [
        [_p(f"<b>#{index}</b> · {_esc(_motivo_labels(motivos))}", card_title, markup=True)],
        [
            _p(
                "● BARRA DISTINTA vs Sencillo" if barra_cambio else "Δ cantidad (misma barra)",
                badge if barra_cambio else small,
            )
        ],
        [_p("<b>Sencillo (baseline)</b>", small, markup=True)],
        [
            _p(
                f"<font face='Courier'>{_esc(bb)}</font> × <b>{_esc(qb)}</b>",
                body,
                markup=True,
            )
        ],
        [_p(db or "—", small)],
        [_p("<b>↓ Propuesto</b>", small, markup=True)],
    ]
    if barra_cambio:
        rows_data.append(
            [
                _p(
                    f"<font face='Courier' color='#8a4b1a'><b>{_esc(bp)}</b></font>"
                    f" × <b>{_esc(qp)}</b>",
                    body,
                    markup=True,
                )
            ]
        )
    else:
        rows_data.append(
            [
                _p(
                    f"<font face='Courier'>{_esc(bp)}</font> × <b>{_esc(qp)}</b>",
                    body,
                    markup=True,
                )
            ]
        )
    rows_data.append([_p(dp or "—", small)])
    rows_data.append([_p("<b>Por qué</b>", small, markup=True)])
    rows_data.append([_p(f"<i>{_esc(just)}</i>" if just else "—", small, markup=True)])

    card = Table(rows_data, colWidths=[width])
    bg = BARRA_CAMBIO_BG if barra_cambio else QTY_DELTA_BG
    edge = BARRA_CAMBIO_EDGE if barra_cambio else colors.HexColor("#8aa0c0")
    style = [
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1.0, edge),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    # Highlight the propuesto barcode row (index 6 in rows_data)
    if barra_cambio:
        style.append(("BACKGROUND", (0, 6), (-1, 6), colors.HexColor("#e8c9a8")))
        style.append(("BOX", (0, 6), (-1, 6), 1.2, BARRA_CAMBIO_EDGE))
        style.append(("TOPPADDING", (0, 6), (-1, 6), 5))
        style.append(("BOTTOMPADDING", (0, 6), (-1, 6), 5))
    card.setStyle(TableStyle(style))
    return card
