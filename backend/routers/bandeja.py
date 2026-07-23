"""Bandeja de pedidos API — ADR-0030."""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos"])


class PatchPropuestaRequest(BaseModel):
    pedido_propuesto: List[Dict[str, Any]]
    comparativa_cantidades: Optional[List[Dict[str, Any]]] = None


class EstadoRequest(BaseModel):
    motivo: Optional[str] = None
    revision: Optional[int] = None
    snapshot_hash: Optional[str] = Field(None, alias="snapshot_hash")
    model_config = {"populate_by_name": True}


def _svc():
    try:
        from backend.services import bandeja_service as svc
    except ImportError:
        from services import bandeja_service as svc  # type: ignore
    return svc


def _conn():
    import database

    return database.get_db_connection()


@router.get("/bandeja")
async def get_bandeja(tab: str = "por_enviar", limit: int = 100):
    svc = _svc()
    if tab not in ("por_enviar", "por_aprobar", "historial"):
        raise HTTPException(400, detail="tab inválido")
    conn = _conn()
    try:
        items = svc.list_bandeja(conn, tab=tab, limit=min(limit, 500))
        counts = svc.bandeja_counts(conn)
        return {"ok": True, "tab": tab, "items": items, "counts": counts}
    except Exception as exc:
        logging.error("bandeja list failed: %s", exc, exc_info=True)
        raise HTTPException(500, detail=str(exc)) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.get("/bandeja/counts")
async def get_bandeja_counts():
    svc = _svc()
    conn = _conn()
    try:
        return {"ok": True, "counts": svc.bandeja_counts(conn)}
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.get("/bandeja/{propuesta_id}/comparativa")
async def get_bandeja_comparativa(propuesta_id: int):
    svc = _svc()
    conn = _conn()
    try:
        snap = svc.get_comparativa(conn, propuesta_id)
        if not snap:
            raise HTTPException(404, detail="Propuesta no encontrada")
        return {"ok": True, **snap}
    except HTTPException:
        raise
    except Exception as exc:
        logging.error("bandeja comparativa failed: %s", exc, exc_info=True)
        raise HTTPException(500, detail=str(exc)) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.get("/bandeja/{propuesta_id}/pdf-desviaciones")
async def get_pdf_desviaciones(propuesta_id: int):
    """JSON payload for exhaustive PDF section (ADR-0030). Prefer GET .../pdf for binary."""
    svc = _svc()
    conn = _conn()
    try:
        snap = svc.get_comparativa(conn, propuesta_id)
        if not snap:
            raise HTTPException(404, detail="Propuesta no encontrada")
        return {
            "ok": True,
            "propuesta_id": propuesta_id,
            "cod_prov": snap["cod_prov"],
            "revision": snap["revision"],
            "snapshot_hash": snap["snapshot_hash"],
            "desviaciones": snap["desviaciones"],
            "lineas_desviacion": snap["desviacion_rows"],
            "resumen": {
                "total_lineas_comparativa": len(snap.get("comparativa_cantidades") or []),
                "lineas_con_desvio": snap["desviaciones"],
            },
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _build_pdf_for_snap(snap: Dict[str, Any], propuesta_id: int) -> bytes:
    try:
        from backend.services.pedido_pdf import build_pedido_pdf_bytes
    except ImportError:
        from services.pedido_pdf import build_pedido_pdf_bytes  # type: ignore
    return build_pedido_pdf_bytes(
        propuesta_id=propuesta_id,
        cod_prov=snap["cod_prov"],
        estado=snap["estado"],
        revision=int(snap["revision"] or 1),
        snapshot_hash=snap.get("snapshot_hash"),
        comparativa=snap.get("comparativa_cantidades") or [],
        propuesto=snap.get("pedido_propuesto") or [],
        monto_total_usd=None,
        synapse_link="modulo_pedidos.html?bandeja=1",
    )


@router.get("/bandeja/{propuesta_id}/pdf")
async def get_bandeja_pdf(propuesta_id: int):
    """Binary PDF with exhaustive desvíos section (ADR-0030)."""
    from fastapi.responses import Response

    svc = _svc()
    conn = _conn()
    try:
        snap = svc.get_comparativa(conn, propuesta_id)
        if not snap:
            raise HTTPException(404, detail="Propuesta no encontrada")
        # ensure hash exists (old rows may lack it)
        if not snap.get("snapshot_hash"):
            from analytics_engine.core.borrador_snapshot import snapshot_hash as sh

            snap["snapshot_hash"] = sh(
                snap.get("comparativa_cantidades") or [],
                snap.get("pedido_propuesto") or [],
            )
        pdf = _build_pdf_for_snap(snap, propuesta_id)
        fname = f"pedido_{propuesta_id}_{snap['cod_prov']}_r{snap['revision']}.pdf"
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logging.error("PDF build failed: %s", exc, exc_info=True)
        raise HTTPException(500, detail=f"Error generando PDF: {exc}") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.post("/bandeja/{propuesta_id}/telegram-notify")
async def telegram_notify_propuesta(propuesta_id: int):
    """Send PDF + Aprobar/Rechazar buttons with revision+hash8 in callback_data."""
    try:
        from backend.services import telegram_pedidos as tg
    except ImportError:
        from services import telegram_pedidos as tg  # type: ignore

    svc = _svc()
    conn = _conn()
    try:
        snap = svc.get_comparativa(conn, propuesta_id)
        if not snap:
            raise HTTPException(404, detail="Propuesta no encontrada")
        if snap["estado"] not in ("PENDIENTE_APROBACION", "BORRADOR", "FALLIDO_ENVIO"):
            raise HTTPException(
                400,
                detail=f"estado_no_notificable:{snap['estado']}",
            )
        if not snap.get("snapshot_hash"):
            from analytics_engine.core.borrador_snapshot import snapshot_hash as sh

            snap["snapshot_hash"] = sh(
                snap.get("comparativa_cantidades") or [],
                snap.get("pedido_propuesto") or [],
            )
            # persist hash on cabecera for later validation
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE Procurement.BorradorPedidosCabecera
                SET SnapshotHash = ?
                WHERE PropuestaID = ? AND (SnapshotHash IS NULL OR SnapshotHash = '')
                """,
                (snap["snapshot_hash"], propuesta_id),
            )
            conn.commit()

        pdf = _build_pdf_for_snap(snap, propuesta_id)
        result = tg.send_pedido_approval(
            propuesta_id=propuesta_id,
            cod_prov=snap["cod_prov"],
            revision=int(snap["revision"] or 1),
            snapshot_hash=str(snap["snapshot_hash"]),
            pdf_bytes=pdf,
            desviaciones=int(snap.get("desviaciones") or 0),
            synapse_link="modulo_pedidos.html?bandeja=1",
        )
        return {"ok": True, **result}
    except HTTPException:
        raise
    except Exception as exc:
        logging.error("telegram-notify failed: %s", exc, exc_info=True)
        raise HTTPException(500, detail=str(exc)) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


class TelegramUpdate(BaseModel):
    """Subset of Telegram Update for callback_query."""
    update_id: Optional[int] = None
    callback_query: Optional[Dict[str, Any]] = None


@router.post("/bandeja/telegram-callback")
async def telegram_callback(update: TelegramUpdate):
    """
    Webhook for Telegram callback_query.
    Validates hash8 vs current SnapshotHash; stale → alert and no-op.
    """
    try:
        from backend.services import telegram_pedidos as tg
    except ImportError:
        from services import telegram_pedidos as tg  # type: ignore

    cq = update.callback_query or {}
    if not cq:
        return {"ok": True, "ignored": True}
    cb_id = str(cq.get("id") or "")
    data = str(cq.get("data") or "")
    msg = cq.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    message_id = msg.get("message_id")
    from_user = (cq.get("from") or {}).get("username") or (cq.get("from") or {}).get("id")

    svc = _svc()
    conn = _conn()
    try:
        try:
            parsed = tg.parse_callback(data)
        except ValueError:
            if cb_id:
                tg.answer_callback(cb_id, "Callback inválido", show_alert=True)
            raise HTTPException(400, detail="callback_invalid")

        snap = svc.get_comparativa(conn, parsed["propuesta_id"])
        if not snap:
            if cb_id:
                tg.answer_callback(cb_id, "Propuesta no encontrada", show_alert=True)
            raise HTTPException(404, detail="propuesta_not_found")

        current_hash = str(snap.get("snapshot_hash") or "")
        current_rev = int(snap.get("revision") or 1)
        if current_rev != int(parsed["revision"]) or not tg.hash_matches(
            current_hash, parsed["hash8"]
        ):
            if cb_id:
                tg.answer_callback(
                    cb_id,
                    "Desactualizado: la web guardó cambios. Abra Synapse Bandeja.",
                    show_alert=True,
                )
            if chat_id and message_id:
                tg.edit_message_text(
                    chat_id,
                    int(message_id),
                    f"⚠️ Pedido #{parsed['propuesta_id']} — botones *inválidos* (rev/hash desactualizados).\n"
                    f"Rev actual `{current_rev}` · reabra Bandeja en Synapse.",
                )
            return {
                "ok": False,
                "error": "stale",
                "propuesta_id": parsed["propuesta_id"],
                "expected_revision": parsed["revision"],
                "current_revision": current_rev,
            }

        if parsed["action"] == "rechazar":
            motivo = f"Telegram @{from_user}" if from_user else "Telegram"
            result = svc.set_estado(
                conn,
                parsed["propuesta_id"],
                "RECHAZADO",
                motivo=motivo[:500],
                expected_revision=current_rev,
                expected_hash=current_hash,
            )
            conn.commit()
            if cb_id:
                tg.answer_callback(cb_id, "Rechazado", show_alert=False)
            if chat_id and message_id:
                tg.edit_message_text(
                    chat_id,
                    int(message_id),
                    f"❌ Pedido #{parsed['propuesta_id']} *RECHAZADO* por {from_user} (rev {current_rev})",
                )
            return {"ok": True, **result}

        # aprobar → BORRADOR (sin enviar automático por Telegram; FE/n8n envía)
        result = svc.set_estado(
            conn,
            parsed["propuesta_id"],
            "BORRADOR",
            expected_revision=current_rev,
            expected_hash=current_hash,
        )
        conn.commit()
        if cb_id:
            tg.answer_callback(cb_id, "Aprobado → Borrador (listo para Enviar)", show_alert=False)
        if chat_id and message_id:
            tg.edit_message_text(
                chat_id,
                int(message_id),
                f"✅ Pedido #{parsed['propuesta_id']} *APROBADO* por {from_user} → BORRADOR (rev {current_rev}).\n"
                f"Envío FTP desde Bandeja Synapse.",
            )
        return {"ok": True, **result}
    except HTTPException:
        raise
    except ValueError as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        code = str(exc)
        if cb_id:
            try:
                tg.answer_callback(cb_id, code[:180], show_alert=True)
            except Exception:
                pass
        status = 409 if "stale" in code else 400
        raise HTTPException(status, detail=code) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.patch("/bandeja/{propuesta_id}")
async def patch_bandeja_propuesta(propuesta_id: int, body: PatchPropuestaRequest):
    svc = _svc()
    conn = _conn()
    try:
        result = svc.save_snapshot_edits(
            conn,
            propuesta_id,
            pedido_propuesto=body.pedido_propuesto,
            comparativa_cantidades=body.comparativa_cantidades,
        )
        conn.commit()
        return {"ok": True, **result}
    except ValueError as exc:
        conn.rollback()
        code = str(exc)
        status = 409 if "stale" in code or "no_editable" in code else 400
        raise HTTPException(status, detail=code) from exc
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        logging.error("bandeja patch failed: %s", exc, exc_info=True)
        raise HTTPException(500, detail=str(exc)) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.post("/bandeja/{propuesta_id}/aprobar")
async def aprobar_propuesta(propuesta_id: int, enviar: bool = False, body: Optional[EstadoRequest] = None):
    """Aprobar sin enviar → BORRADOR; Aprobar y enviar → ENVIANDO (disparo n8n = stub)."""
    svc = _svc()
    body = body or EstadoRequest()
    conn = _conn()
    try:
        nuevo = "ENVIANDO" if enviar else "BORRADOR"
        result = svc.set_estado(
            conn,
            propuesta_id,
            nuevo,
            expected_revision=body.revision,
            expected_hash=body.snapshot_hash,
        )
        conn.commit()
        out = {"ok": True, "enviar": enviar, "n8n_disparado": False, **result}
        if enviar:
            out["aviso"] = (
                "Estado ENVIANDO. Disparo n8n FTP/API pendiente de wiring (TASK-135/137)."
            )
        return out
    except ValueError as exc:
        conn.rollback()
        code = str(exc)
        status = 409 if "stale" in code else 400
        raise HTTPException(status, detail=code) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.post("/bandeja/{propuesta_id}/rechazar")
async def rechazar_propuesta(propuesta_id: int, body: EstadoRequest):
    svc = _svc()
    conn = _conn()
    try:
        result = svc.set_estado(
            conn,
            propuesta_id,
            "RECHAZADO",
            motivo=body.motivo,
            expected_revision=body.revision,
            expected_hash=body.snapshot_hash,
        )
        conn.commit()
        return {"ok": True, **result}
    except ValueError as exc:
        conn.rollback()
        code = str(exc)
        status = 409 if "stale" in code else 400
        raise HTTPException(status, detail=code) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.post("/bandeja/{propuesta_id}/enviar")
async def enviar_propuesta(propuesta_id: int, body: Optional[EstadoRequest] = None):
    """Enviar desde Por enviar: exige 0 desvíos salvo force via query (Analizar path)."""
    svc = _svc()
    body = body or EstadoRequest()
    conn = _conn()
    try:
        snap = svc.get_comparativa(conn, propuesta_id)
        if not snap:
            raise HTTPException(404, detail="Propuesta no encontrada")
        if snap["estado"] not in ("BORRADOR", "FALLIDO_ENVIO"):
            raise HTTPException(400, detail=f"estado_no_enviable:{snap['estado']}")
        desv = int(snap.get("desviaciones") or 0)
        if desv > 0:
            raise HTTPException(
                409,
                detail={
                    "error": "requiere_analizar",
                    "message": "Hay desviaciones vs Pedido Sencillo; abra Analizar antes de Enviar.",
                    "desviaciones": desv,
                },
            )
        result = svc.set_estado(
            conn,
            propuesta_id,
            "ENVIANDO",
            expected_revision=body.revision or snap["revision"],
            expected_hash=body.snapshot_hash or snap["snapshot_hash"],
        )
        conn.commit()
        return {
            "ok": True,
            "n8n_disparado": False,
            "aviso": "Estado ENVIANDO. Disparo n8n pendiente (TASK-135/137).",
            **result,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        conn.rollback()
        code = str(exc)
        status = 409 if "stale" in code else 400
        raise HTTPException(status, detail=code) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.post("/bandeja/{propuesta_id}/clonar")
async def clonar_propuesta(propuesta_id: int):
    svc = _svc()
    conn = _conn()
    try:
        result = svc.clonar_a_borrador(conn, propuesta_id)
        conn.commit()
        return {"ok": True, **result}
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(404 if "not_found" in str(exc) else 400, detail=str(exc)) from exc
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(500, detail=str(exc)) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.post("/bandeja/ttl-run")
async def run_ttl():
    """Manual/cron trigger for ADR-0030 TTL job."""
    svc = _svc()
    conn = _conn()
    try:
        stats = svc.run_ttl_job(conn)
        conn.commit()
        return {"ok": True, "stats": stats}
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(500, detail=str(exc)) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
