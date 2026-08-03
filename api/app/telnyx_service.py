import asyncio
import base64
import logging
import os
import time
from typing import Any, Dict, Optional

import httpx

from .config import settings, reload_settings

logger = logging.getLogger(__name__)


def normalize_e164(number: str) -> str:
    """Best-effort E.164 normalization.

    Mirrors the behavior used by the Phaxio/Sinch services: leave an existing
    '+' prefix alone, otherwise strip non-digits and add '+' when the result
    looks like it carries a country code.
    """
    if not number:
        return number
    if number.startswith("+"):
        return number
    digits = "".join(c for c in number if c.isdigit())
    if len(digits) >= 10:
        return f"+{digits}"
    return number


class TelnyxFaxService:
    """
    Telnyx Programmable Fax API v2 integration.

    Flow (pull model, like Phaxio/SignalWire):
      1) Faxbot mints a tokenized, publicly fetchable PDF URL
      2) POST /v2/faxes { connection_id, to, from, media_url, webhook_url }
         → { "data": { "id": ..., "status": "queued", ... } }
      3) Telnyx fetches the media_url, sends the fax, and POSTs webhook events
         back to webhook_url (fax.queued / fax.sending / fax.delivered /
         fax.failed, and fax.received for inbound).

    Webhooks are signed with Ed25519: headers ``telnyx-signature-ed25519``
    (base64 signature) and ``telnyx-timestamp`` (unix seconds), over the
    payload ``f"{timestamp}|{raw_body}"``.
    """

    DEFAULT_BASE = "https://api.telnyx.com/v2"

    # Internal status vocabulary is lowercase to match the Sinch backend, so
    # switching FAX_BACKEND between sinch and telnyx keeps FCM notifications,
    # the terminal-state guard, and the UI behaving identically.
    STATUS_MAP = {
        "delivered": "success",
        "failed": "failed",
        "sending": "in_progress",
        "originated": "in_progress",
        "media.processed": "in_progress",
        "initiated": "in_progress",
        "queued": "queued",
    }

    def __init__(
        self,
        api_key: str,
        connection_id: str,
        from_number: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.connection_id = connection_id
        self.from_number = from_number or ""
        self.base_url = (base_url or os.getenv("TELNYX_BASE_URL") or self.DEFAULT_BASE).rstrip("/")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.connection_id)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    # ----- outbound ---------------------------------------------------------

    async def send_fax(
        self,
        to_number: str,
        media_url: str,
        *,
        job_id: str,
        from_number: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a fax on Telnyx from a publicly fetchable media URL.

        Returns ``{"provider_sid": str, "status": <internal status>,
        "provider_status": str}``.
        """
        if not self.is_configured():
            raise ValueError("Telnyx is not properly configured")

        sender = normalize_e164(from_number or self.from_number)
        if not sender:
            raise ValueError(
                "Telnyx requires a sender number: set TELNYX_FROM_E164 or pass from_number"
            )

        payload: Dict[str, Any] = {
            "connection_id": self.connection_id,
            "to": normalize_e164(to_number),
            "from": sender,
            "media_url": media_url,
            "store_media": False,
            # client_state must be base64; used as a correlation fallback when
            # the job_id query param is missing from the webhook URL.
            "client_state": base64.b64encode(job_id.encode()).decode(),
        }
        if webhook_url:
            payload["webhook_url"] = webhook_url

        logger.info(
            "Sending fax via Telnyx: job_id=%s, to=%s, media_url=redacted", job_id, payload["to"]
        )

        url = f"{self.base_url}/faxes"
        attempts = 3
        delay = 1.0
        last_err: Optional[Exception] = None
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(attempts):
                try:
                    resp = await client.post(url, json=payload, headers=self._headers())
                    if resp.status_code >= 400:
                        raise RuntimeError(
                            f"Telnyx create fax error {resp.status_code}: {_error_text(resp)}"
                        )
                    data = (resp.json() or {}).get("data") or {}
                    fax_id = data.get("id")
                    if not fax_id:
                        raise RuntimeError(f"Telnyx did not return a fax id: {data}")
                    provider_status = str(data.get("status") or "queued")
                    return {
                        "provider_sid": str(fax_id),
                        "status": self._map_status_str(provider_status),
                        "provider_status": provider_status,
                    }
                except Exception as e:
                    last_err = e
                    if attempt == attempts - 1:
                        break
                    logger.warning("Telnyx send attempt %s failed: %s", attempt + 1, e)
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 8.0)
        assert last_err is not None
        raise last_err

    async def get_fax_status(self, fax_id: str) -> Dict[str, Any]:
        if not self.is_configured():
            raise ValueError("Telnyx is not properly configured")
        url = f"{self.base_url}/faxes/{fax_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            data = (resp.json() or {}).get("data") or {}
            provider_status = str(data.get("status") or "")
            return {
                "provider_sid": str(data.get("id") or ""),
                "status": self._map_status_str(provider_status),
                "provider_status": provider_status,
                "pages": _as_int(data.get("page_count")),
                "error": data.get("failure_reason"),
            }

    async def fetch_media(self, media_url: str, *, timeout: float = 30.0) -> Optional[bytes]:
        """Download inbound fax media.

        Telnyx inbound media URLs are short-lived; some are pre-signed and some
        require the API key, so send the Bearer header and fall back to an
        anonymous fetch if the authenticated one is rejected.
        """
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for headers in (self._headers(), None):
                try:
                    resp = await client.get(media_url, headers=headers)
                    if resp.status_code == 200:
                        return resp.content
                    logger.warning(
                        "Telnyx media fetch returned %s (auth=%s)",
                        resp.status_code,
                        headers is not None,
                    )
                except Exception as e:
                    logger.warning("Telnyx media fetch error (auth=%s): %s", headers is not None, e)
        return None

    # ----- webhooks ---------------------------------------------------------

    def verify_signature(
        self,
        raw_body: bytes,
        signature_b64: Optional[str],
        timestamp: Optional[str],
        *,
        public_key_b64: Optional[str] = None,
        tolerance_seconds: int = 300,
    ) -> bool:
        """Verify a Telnyx Ed25519 webhook signature.

        Never raises — returns False on any malformed or missing input so the
        caller can answer 401 rather than 500.
        """
        key_b64 = public_key_b64 if public_key_b64 is not None else settings.telnyx_public_key
        if not (key_b64 and signature_b64 and timestamp):
            return False
        try:
            ts = int(str(timestamp).strip())
        except Exception:
            return False
        if tolerance_seconds > 0 and abs(time.time() - ts) > tolerance_seconds:
            logger.warning("Telnyx webhook timestamp outside tolerance window")
            return False
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

            public_key = Ed25519PublicKey.from_public_bytes(_b64decode(key_b64))
            signature = _b64decode(signature_b64)
            signed_payload = f"{ts}|".encode() + raw_body
            try:
                public_key.verify(signature, signed_payload)
            except InvalidSignature:
                return False
            return True
        except Exception as e:
            logger.warning("Telnyx signature verification error: %s", e)
            return False

    def handle_status_callback(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a Telnyx fax webhook body into Faxbot's internal shape.

        Accepts the documented envelope::

            {"data": {"event_type": "fax.delivered", "payload": {...}}}

        and also tolerates a flat body (just the inner payload).
        """
        inner = extract_event_payload(payload)

        provider_status = str(inner.get("status") or "")
        internal = self._map_status_str(provider_status)

        failure = inner.get("failure_reason") or inner.get("failureReason")
        error: Optional[str] = str(failure) if failure else None

        return {
            "provider_sid": str(inner.get("fax_id") or inner.get("id") or ""),
            "status": internal,
            "provider_status": provider_status,
            "pages": _as_int(inner.get("page_count") or inner.get("pages")),
            "error": error,
        }

    @classmethod
    def _map_status_str(cls, status: str) -> str:
        return cls.STATUS_MAP.get((status or "").strip().lower(), "in_progress")


def extract_event_type(body: Dict[str, Any]) -> str:
    """Read the Telnyx event type from a webhook body (envelope or flat)."""
    if not isinstance(body, dict):
        return ""
    data = body.get("data")
    if isinstance(data, dict) and data.get("event_type"):
        return str(data.get("event_type") or "")
    return str(body.get("event_type") or "")


def extract_event_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    """Read the Telnyx event payload from a webhook body (envelope or flat)."""
    if not isinstance(body, dict):
        return {}
    data = body.get("data")
    if isinstance(data, dict):
        inner = data.get("payload")
        if isinstance(inner, dict):
            return inner
        return data
    inner = body.get("payload")
    if isinstance(inner, dict):
        return inner
    return body


def job_id_from_client_state(client_state: Optional[str]) -> Optional[str]:
    """Decode the base64 client_state Faxbot sets when creating a fax."""
    if not client_state:
        return None
    try:
        decoded = _b64decode(str(client_state)).decode("utf-8", errors="strict").strip()
    except Exception:
        return None
    return decoded or None


def _b64decode(value: str) -> bytes:
    s = str(value).strip()
    # Tolerate missing padding and URL-safe alphabets.
    padding = "=" * (-len(s) % 4)
    try:
        return base64.b64decode(s + padding, validate=False)
    except Exception:
        return base64.urlsafe_b64decode(s + padding)


def _as_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(str(value))
    except Exception:
        return None


def _error_text(resp: httpx.Response) -> str:
    try:
        body = resp.json()
    except Exception:
        return resp.text
    errors = body.get("errors") if isinstance(body, dict) else None
    if isinstance(errors, list) and errors:
        parts = []
        for err in errors:
            if not isinstance(err, dict):
                continue
            detail = err.get("detail") or err.get("title")
            code = err.get("code")
            parts.append(" — ".join(str(x) for x in (code, detail) if x))
        if parts:
            return "; ".join(parts)
    return str(body)


_telnyx_service: Optional[TelnyxFaxService] = None
_telnyx_creds: Optional[tuple] = None


def get_telnyx_service() -> Optional[TelnyxFaxService]:
    """Get the singleton Telnyx service instance.

    Rebuilt whenever the effective credentials change so that applying new
    settings through the Admin console takes effect without a restart.
    """
    global _telnyx_service, _telnyx_creds
    # Ensure settings reflect current environment (tests monkeypatch env at runtime)
    reload_settings()
    if not (settings.telnyx_api_key and settings.telnyx_connection_id):
        _telnyx_service = None
        _telnyx_creds = None
        return None
    creds = (
        settings.telnyx_api_key,
        settings.telnyx_connection_id,
        settings.telnyx_from_e164,
        os.getenv("TELNYX_BASE_URL") or "",
    )
    if _telnyx_service is None or _telnyx_creds != creds:
        _telnyx_service = TelnyxFaxService(
            api_key=settings.telnyx_api_key,
            connection_id=settings.telnyx_connection_id,
            from_number=settings.telnyx_from_e164 or None,
            base_url=os.getenv("TELNYX_BASE_URL") or None,
        )
        _telnyx_creds = creds
    return _telnyx_service
