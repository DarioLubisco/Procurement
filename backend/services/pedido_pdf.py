"""Generate pedido PDF (summary + exhaustive desvíos vs Sencillo) — ADR-0030."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from analytics_engine.core.borrador_snapshot import build_desviacion_rows, count_desviaciones


def _esc(text: Any) -> str:
    """Escape user/DB text for ReportLab Paragraph (XML)."""
    s = str(text if text is not None else "")
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _p(text: Any, style: ParagraphStyle, *, markup: bool = False) -> Paragraph:
    """
    Build a Paragraph.
    markup=False (default): escape raw text (product names, etc.).
    markup=True: trust intentional ReportLab subset tags (<b>, <i>, <br/>).
    Caller must _esc() any untrusted fragments before embedding them in markup.
    """
    s = str(text if text is not None else "")
    if not markup:
        s = _esc(s)
    return Paragraph(s, style)


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
    """Return PDF bytes: cabecera + totals + exhaustive desvío section + líneas."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title=f"Pedido {propuesta_id} {cod_prov}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=14, spaceAfter=8)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=8, leading=11)
    small = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#444444"),
    )
    mono = ParagraphStyle(
        "Mono", parent=styles["Normal"], fontSize=7, fontName="Courier", leading=9
    )

    desv_rows = build_desviacion_rows(comparativa)
    n_desv = count_desviaciones(comparativa)
    n_prop = sum(1 for r in propuesto if int(r.get("cantidad") or 0) > 0)
    hash_short = (snapshot_hash or "")[:16]

    story: List[Any] = []
    story.append(_p(f"Synapse — Pedido / Propuesta #{propuesta_id}", h1))
    story.append(
        _p(
            f"<b>Proveedor:</b> {_esc(cod_prov)} &nbsp;&nbsp; "
            f"<b>Estado:</b> {_esc(estado)} &nbsp;&nbsp; "
            f"<b>Rev:</b> {revision} &nbsp;&nbsp; "
            f"<b>Hash:</b> {_esc(hash_short)}…",
            body,
            markup=True,
        )
    )
    story.append(
        _p(
            f"Generado {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
            f"Líneas propuesto: {n_prop} · Desvíos vs Sencillo: <b>{n_desv}</b>",
            body,
            markup=True,
        )
    )
    if monto_total_usd is not None:
        story.append(
            _p(f"Monto estimado USD: <b>{monto_total_usd:,.2f}</b>", body, markup=True)
        )
    if synapse_link:
        story.append(_p(f"Abrir en Synapse: {_esc(synapse_link)}", small, markup=True))
    story.append(Spacer(1, 6))

    # Exhaustive deviations section (ADR-0030)
    story.append(_p("Desviaciones vs Pedido Sencillo (sección exhaustiva)", h2))
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
                "Incluye Δ cantidad (misma barra), sucedáneo (barra distinta) y altas/bajas.",
                small,
            )
        )
        header = [
            "Motivos",
            "BARRA base",
            "Qty base",
            "BARRA prop.",
            "Qty prop.",
            "Justificación",
        ]
        data = [header]
        for row in desv_rows:
            motivos = ",".join(row.get("desviacion_motivos") or [])
            just = str(row.get("justificacion_delta") or "")[:120]
            data.append(
                [
                    _p(motivos, small),
                    _p(row.get("barra_baseline") or "—", small),
                    _p(row.get("qty_baseline"), small),
                    _p(row.get("barra_propuesto") or "—", small),
                    _p(row.get("qty_propuesto"), small),
                    _p(just or "—", small),
                ]
            )
        tw = doc.width
        col_w = [0.14 * tw, 0.14 * tw, 0.08 * tw, 0.14 * tw, 0.08 * tw, 0.42 * tw]
        t = Table(data, colWidths=col_w, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d313a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#888888")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f3f4f6")],
                    ),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(t)

    story.append(_p("Pedido propuesto (líneas)", h2))
    prop_header = ["BARRA", "Descripción", "Cant.", "Precio", "Total"]
    prop_data = [prop_header]
    for r in propuesto:
        try:
            qty = int(r.get("cantidad") or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0:
            continue
        try:
            precio = float(r.get("precio")) if r.get("precio") is not None else None
        except (TypeError, ValueError):
            precio = None
        total = (qty * precio) if precio is not None else None
        prop_data.append(
            [
                _p(r.get("barra") or "", small),
                _p(str(r.get("descripcion") or r.get("descrip") or "")[:80], small),
                _p(qty, small),
                _p(f"{precio:.4f}" if precio is not None else "—", small),
                _p(f"{total:.2f}" if total is not None else "—", small),
            ]
        )
    if len(prop_data) == 1:
        story.append(_p("Sin líneas con cantidad > 0.", body))
    else:
        tw = doc.width
        pt = Table(
            prop_data,
            colWidths=[0.16 * tw, 0.48 * tw, 0.1 * tw, 0.13 * tw, 0.13 * tw],
            repeatRows=1,
        )
        pt.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8b3a4a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#888888")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#faf5f6")],
                    ),
                    ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ]
            )
        )
        story.append(pt)

    story.append(Spacer(1, 10))
    story.append(
        _p(
            f"Telegram approve debe enviar revision={revision} hash={hash_short}… "
            "(si la web guarda cambios, el hash cambia y los botones quedan inválidos).",
            mono,
        )
    )
    doc.build(story)
    return buf.getvalue()
