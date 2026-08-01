"""Telegram notify/approve for Bandeja pedidos with revision+hash — ADR-0029/0030."""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_CRED_CANDIDATES = (
    "/home/synapse/source/N8N/synapse.credentials",
    str(Path.home() / "source/N8N/synapse.credentials"),
    "/app/synapse.credentials",
)


def _load_credentials_file() -> None:
    """Load synapse.credentials into os.environ if keys missing."""
    for path in _CRED_CANDIDATES:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
        except Exception as exc:
            logger.warning("Could not load %s: %s", path, exc)
        break


def get_telegram_config() -> Tuple[str, str]:
    """
    Bot + chat for pedidos (ADR-0029 → AMC_Administrativo).

    Priority (bot):
      1. PEDIDOS_TELEGRAM_BOT
      2. TELEGRAM_AMC_ADMIN_BOT  (@AMC_Administrativo_bot)
    Priority (chat):
      1. PEDIDOS_TELEGRAM_CHAT_ID
      2. AMC_ADMINISTRATIVO_CHAT_ID  (grupo Gestión Administrativa)
    Escape hatch only if PEDIDOS_TELEGRAM_FALLBACK_NOTIFICACION=1:
      TELEGRAM_AMC_NOTIFICACION_BOT + ERROR_CHAT_ID (alertas sistema; no pedidos).
    """
    _load_credentials_file()
    use_notif_fallback = os.getenv(
        "PEDIDOS_TELEGRAM_FALLBACK_NOTIFICACION", ""
    ).strip().lower() in ("1", "true", "yes")

    if use_notif_fallback:
        token = (
            os.getenv("PEDIDOS_TELEGRAM_BOT")
            or os.getenv("TELEGRAM_AMC_NOTIFICACION_BOT")
            or ""
        ).strip()
        chat = (
            os.getenv("PEDIDOS_TELEGRAM_CHAT_ID")
            or os.getenv("ERROR_CHAT_ID")
            or ""
        ).strip()
    else:
        token = (
            os.getenv("PEDIDOS_TELEGRAM_BOT")
            or os.getenv("TELEGRAM_AMC_ADMIN_BOT")
            or ""
        ).strip()
        chat = (
            os.getenv("PEDIDOS_TELEGRAM_CHAT_ID")
            or os.getenv("AMC_ADMINISTRATIVO_CHAT_ID")
            or ""
        ).strip()

    if not token or not chat:
        raise RuntimeError(
            "Telegram pedidos no configurado: hace falta "
            "TELEGRAM_AMC_ADMIN_BOT + AMC_ADMINISTRATIVO_CHAT_ID "
            "(o PEDIDOS_TELEGRAM_BOT + PEDIDOS_TELEGRAM_CHAT_ID)"
        )
    return token, chat


def encode_callback(action: str, propuesta_id: int, revision: int, snapshot_hash: str) -> str:
    """Compact callback_data ≤64 bytes: bp|{a|r}|{id}|{rev}|{hash8}."""
    act = "a" if action in ("aprobar", "a", "approve") else "r"
    h8 = (snapshot_hash or "0")[:8]
    data = f"bp|{act}|{int(propuesta_id)}|{int(revision)}|{h8}"
    if len(data.encode("utf-8")) > 64:
        raise ValueError("callback_data too long")
    return data


def parse_callback(data: str) -> Dict[str, Any]:
    parts = str(data or "").split("|")
    if len(parts) != 5 or parts[0] != "bp":
        raise ValueError("callback_invalid")
    act = parts[1]
    if act not in ("a", "r"):
        raise ValueError("callback_action_invalid")
    return {
        "action": "aprobar" if act == "a" else "rechazar",
        "propuesta_id": int(parts[2]),
        "revision": int(parts[3]),
        "hash8": parts[4],
    }


def hash_matches(full_hash: Optional[str], hash8: str) -> bool:
    if not full_hash or not hash8:
        return False
    return str(full_hash).startswith(str(hash8))


def _api(token: str, method: str, payload: Dict[str, Any], *, files: Optional[Dict] = None) -> Dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    if files:
        # multipart for sendDocument — use urllib with manual multipart is painful;
        # prefer JSON for sendMessage; for document use http.client multipart below
        return _api_multipart(token, method, payload, files)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        logger.error("Telegram %s HTTP %s: %s", method, exc.code, err_body[:500])
        raise RuntimeError(f"Telegram {method} failed: {exc.code} {err_body[:200]}") from exc


def _api_multipart(token: str, method: str, fields: Dict[str, Any], files: Dict[str, Tuple[str, bytes, str]]) -> Dict[str, Any]:
    import uuid

    boundary = f"----SynapseBoundary{uuid.uuid4().hex}"
    body = bytearray()
    for k, v in fields.items():
        if v is None:
            continue
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
        body.extend(str(v).encode("utf-8"))
        body.extend(b"\r\n")
    for name, (filename, content, content_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode())
        body.extend(content)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    url = f"https://api.telegram.org/bot{token}/{method}"
    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_pedido_approval(
    *,
    propuesta_id: int,
    cod_prov: str,
    revision: int,
    snapshot_hash: str,
    pdf_bytes: bytes,
    caption_extra: str = "",
    desviaciones: int = 0,
    monto_total_usd: Optional[float] = None,
    synapse_link: Optional[str] = None,
) -> Dict[str, Any]:
    """Send PDF + inline Aprobar/Rechazar buttons carrying revision+hash8."""
    token, chat_id = get_telegram_config()
    cb_ok = encode_callback("aprobar", propuesta_id, revision, snapshot_hash)
    cb_ko = encode_callback("rechazar", propuesta_id, revision, snapshot_hash)
    monto = f"${monto_total_usd:,.2f}" if monto_total_usd is not None else "—"
    link = synapse_link or f"modulo_pedidos.html?bandeja=1"
    text = (
        f"📦 *Pedido #{propuesta_id}* — `{cod_prov}`\n"
        f"Rev `{revision}` · hash `{snapshot_hash[:8]}`\n"
        f"Monto ~ {monto} · Desvíos vs Sencillo: *{desviaciones}*\n"
        f"{caption_extra}\n"
        f"[Abrir Bandeja]({link})"
    ).strip()
    # 1) document
    doc_resp = _api_multipart(
        token,
        "sendDocument",
        {
            "chat_id": chat_id,
            "caption": f"PDF pedido #{propuesta_id} {cod_prov} (rev {revision})",
        },
        {
            "document": (
                f"pedido_{propuesta_id}_{cod_prov}_r{revision}.pdf",
                pdf_bytes,
                "application/pdf",
            )
        },
    )
    # 2) message with buttons
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Aprobar", "callback_data": cb_ok},
                {"text": "❌ Rechazar", "callback_data": cb_ko},
            ]
        ]
    }
    msg_resp = _api(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": keyboard,
            "disable_web_page_preview": True,
        },
    )
    return {
        "ok": True,
        "chat_id": chat_id,
        "callback_aprobar": cb_ok,
        "callback_rechazar": cb_ko,
        "document": doc_resp.get("result"),
        "message": msg_resp.get("result"),
    }


def answer_callback(callback_query_id: str, text: str, *, show_alert: bool = True) -> None:
    if not callback_query_id or callback_query_id in ("0", "999"):
        return
    token, _ = get_telegram_config()
    try:
        _api(
            token,
            "answerCallbackQuery",
            {
                "callback_query_id": callback_query_id,
                "text": text[:200],
                "show_alert": show_alert,
            },
        )
    except Exception as exc:
        logger.warning("answerCallbackQuery failed: %s", exc)


def edit_message_text(chat_id: Any, message_id: int, text: str) -> None:
    token, _ = get_telegram_config()
    try:
        _api(
            token,
            "editMessageText",
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "Markdown",
            },
        )
    except Exception as exc:
        logger.warning("editMessageText failed: %s", exc)
