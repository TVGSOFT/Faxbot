import base64
import json
import time

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient

from app.telnyx_service import (
    TelnyxFaxService,
    extract_event_payload,
    extract_event_type,
    job_id_from_client_state,
    normalize_e164,
)
from app.main import app


TEST_PDF = (
    b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\n"
    b"0000000000 65535 f \ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n9\n%%EOF"
)


def _service(**kwargs) -> TelnyxFaxService:
    defaults = dict(api_key="key", connection_id="conn", from_number="+15551230000")
    defaults.update(kwargs)
    return TelnyxFaxService(**defaults)


def _delivered_event(fax_id="fax_abc", job_id=None, status="delivered", **payload):
    inner = {"fax_id": fax_id, "status": status, "to": "+15551234567", "from": "+15551230000"}
    if job_id:
        inner["client_state"] = base64.b64encode(job_id.encode()).decode()
    inner.update(payload)
    return {"data": {"event_type": f"fax.{status}", "id": "evt_1", "payload": inner}}


# ----- service basics -------------------------------------------------------


def test_service_initialization():
    service = _service()
    assert service.is_configured() is True
    assert service.base_url == "https://api.telnyx.com/v2"
    assert service._headers()["Authorization"] == "Bearer key"


def test_service_base_url_override():
    assert _service(base_url="https://example.test/v2/").base_url == "https://example.test/v2"


def test_service_not_configured():
    assert _service(api_key="", connection_id="").is_configured() is False
    assert _service(api_key="key", connection_id="").is_configured() is False
    assert _service(api_key="", connection_id="conn").is_configured() is False


def test_normalize_e164():
    assert normalize_e164("+15551234567") == "+15551234567"
    assert normalize_e164("(555) 123-4567") == "+5551234567"
    assert normalize_e164("1-555-123-4567") == "+15551234567"
    # Too short to guess a country code — left alone for the provider to reject
    assert normalize_e164("911") == "911"
    assert normalize_e164("") == ""


def test_status_mapping():
    cases = [
        ("delivered", "success"),
        ("failed", "failed"),
        ("sending", "in_progress"),
        ("originated", "in_progress"),
        ("media.processed", "in_progress"),
        ("initiated", "in_progress"),
        ("queued", "queued"),
        ("DELIVERED", "success"),
        ("something_new", "in_progress"),
        ("", "in_progress"),
    ]
    for provider_status, expected in cases:
        assert TelnyxFaxService._map_status_str(provider_status) == expected


# ----- send -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_fax_not_configured():
    with pytest.raises(ValueError):
        await _service(api_key="", connection_id="").send_fax(
            "+15551234567", "https://example.com/a.pdf", job_id="job1"
        )


@pytest.mark.asyncio
async def test_send_fax_requires_sender():
    with pytest.raises(ValueError, match="sender number"):
        await _service(from_number="").send_fax(
            "+15551234567", "https://example.com/a.pdf", job_id="job1"
        )


@pytest.mark.asyncio
async def test_send_fax_success():
    captured = {}

    class DummyResp:
        status_code = 200

        def json(self):
            return {"data": {"id": "fax_123", "status": "queued"}}

    async def fake_post(url, json=None, headers=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return DummyResp()

    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=fake_post)):
        res = await _service().send_fax(
            "5551234567",
            "https://example.com/a.pdf",
            job_id="job1",
            webhook_url="https://example.com/telnyx-callback?job_id=job1",
        )

    assert res == {"provider_sid": "fax_123", "status": "queued", "provider_status": "queued"}
    assert captured["url"] == "https://api.telnyx.com/v2/faxes"
    assert captured["headers"]["Authorization"] == "Bearer key"
    body = captured["json"]
    assert body["connection_id"] == "conn"
    assert body["to"] == "+5551234567"          # normalized
    assert body["from"] == "+15551230000"
    assert body["media_url"] == "https://example.com/a.pdf"
    assert body["webhook_url"] == "https://example.com/telnyx-callback?job_id=job1"
    # client_state carries the job id as a correlation fallback
    assert job_id_from_client_state(body["client_state"]) == "job1"


@pytest.mark.asyncio
async def test_send_fax_per_request_from_overrides_default():
    class DummyResp:
        status_code = 200

        def json(self):
            return {"data": {"id": "fax_1", "status": "queued"}}

    captured = {}

    async def fake_post(url, json=None, headers=None):
        captured["json"] = json
        return DummyResp()

    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=fake_post)):
        await _service().send_fax(
            "+15551234567", "https://x/a.pdf", job_id="job1", from_number="+15559998888"
        )
    assert captured["json"]["from"] == "+15559998888"


@pytest.mark.asyncio
async def test_send_fax_retries_then_raises():
    class ErrorResp:
        status_code = 422

        def json(self):
            return {"errors": [{"code": "10015", "detail": "media_url is not reachable"}]}

    calls = {"n": 0}

    async def fake_post(url, json=None, headers=None):
        calls["n"] += 1
        return ErrorResp()

    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=fake_post)), patch(
        "app.telnyx_service.asyncio.sleep", new=AsyncMock()
    ):
        with pytest.raises(RuntimeError, match="media_url is not reachable"):
            await _service().send_fax("+15551234567", "https://x/a.pdf", job_id="job1")
    assert calls["n"] == 3  # 3 attempts, no silent success


@pytest.mark.asyncio
async def test_send_fax_recovers_on_retry():
    class ErrorResp:
        status_code = 500

        def json(self):
            return {}

        text = "boom"

    class OkResp:
        status_code = 200

        def json(self):
            return {"data": {"id": "fax_9", "status": "sending"}}

    responses = [ErrorResp(), OkResp()]

    async def fake_post(url, json=None, headers=None):
        return responses.pop(0)

    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=fake_post)), patch(
        "app.telnyx_service.asyncio.sleep", new=AsyncMock()
    ):
        res = await _service().send_fax("+15551234567", "https://x/a.pdf", job_id="job1")
    assert res["provider_sid"] == "fax_9"
    assert res["status"] == "in_progress"


# ----- webhook payload parsing ---------------------------------------------


def test_handle_status_callback_delivered():
    res = _service().handle_status_callback(_delivered_event(page_count=3))
    assert res["provider_sid"] == "fax_abc"
    assert res["status"] == "success"
    assert res["provider_status"] == "delivered"
    assert res["pages"] == 3
    assert res["error"] is None


def test_handle_status_callback_failed():
    body = _delivered_event(status="failed", failure_reason="rejected_by_receiver")
    res = _service().handle_status_callback(body)
    assert res["status"] == "failed"
    assert res["error"] == "rejected_by_receiver"


def test_handle_status_callback_flat_body():
    res = _service().handle_status_callback(
        {"fax_id": "fax_flat", "status": "sending", "page_count": "2"}
    )
    assert res["provider_sid"] == "fax_flat"
    assert res["status"] == "in_progress"
    assert res["pages"] == 2


def test_handle_status_callback_tolerates_junk():
    res = _service().handle_status_callback({})
    assert res["provider_sid"] == ""
    assert res["status"] == "in_progress"
    assert res["pages"] is None


def test_event_extraction_helpers():
    body = _delivered_event(job_id="job42")
    assert extract_event_type(body) == "fax.delivered"
    assert extract_event_payload(body)["fax_id"] == "fax_abc"
    assert extract_event_type({"event_type": "fax.received"}) == "fax.received"
    assert extract_event_type({}) == ""
    assert extract_event_payload({"a": 1}) == {"a": 1}


def test_job_id_from_client_state():
    assert job_id_from_client_state(base64.b64encode(b"job42").decode()) == "job42"
    assert job_id_from_client_state(None) is None
    assert job_id_from_client_state("") is None
    # Non-utf8 payloads must not raise
    assert job_id_from_client_state(base64.b64encode(b"\xff\xfe").decode()) is None


# ----- signature verification ----------------------------------------------


def _keypair():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    private_key = Ed25519PrivateKey.generate()
    public_b64 = base64.b64encode(
        private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode()
    return private_key, public_b64


def _sign(private_key, raw: bytes, ts: int) -> str:
    return base64.b64encode(private_key.sign(f"{ts}|".encode() + raw)).decode()


def test_verify_signature_valid():
    private_key, public_b64 = _keypair()
    raw = json.dumps(_delivered_event()).encode()
    ts = int(time.time())
    assert _service().verify_signature(
        raw, _sign(private_key, raw, ts), str(ts), public_key_b64=public_b64
    )


def test_verify_signature_rejects_tampered_body():
    private_key, public_b64 = _keypair()
    raw = json.dumps(_delivered_event()).encode()
    ts = int(time.time())
    sig = _sign(private_key, raw, ts)
    assert not _service().verify_signature(
        raw + b" ", sig, str(ts), public_key_b64=public_b64
    )


def test_verify_signature_rejects_wrong_key():
    private_key, _ = _keypair()
    _, other_public_b64 = _keypair()
    raw = b"{}"
    ts = int(time.time())
    assert not _service().verify_signature(
        raw, _sign(private_key, raw, ts), str(ts), public_key_b64=other_public_b64
    )


def test_verify_signature_rejects_stale_timestamp():
    private_key, public_b64 = _keypair()
    raw = b"{}"
    ts = int(time.time()) - 4000
    assert not _service().verify_signature(
        raw, _sign(private_key, raw, ts), str(ts), public_key_b64=public_b64,
        tolerance_seconds=300,
    )
    # ...but is accepted when the tolerance check is disabled
    assert _service().verify_signature(
        raw, _sign(private_key, raw, ts), str(ts), public_key_b64=public_b64,
        tolerance_seconds=0,
    )


def test_verify_signature_rejects_malformed_input():
    _, public_b64 = _keypair()
    service = _service()
    assert not service.verify_signature(b"{}", None, "123", public_key_b64=public_b64)
    assert not service.verify_signature(b"{}", "sig", None, public_key_b64=public_b64)
    assert not service.verify_signature(b"{}", "sig", "not-a-number", public_key_b64=public_b64)
    assert not service.verify_signature(b"{}", "!!!not-base64!!!", str(int(time.time())), public_key_b64=public_b64)
    assert not service.verify_signature(b"{}", "sig", str(int(time.time())), public_key_b64="")
    assert not service.verify_signature(b"{}", "sig", str(int(time.time())), public_key_b64="short")


# ----- media fetch ----------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_media_uses_bearer_then_falls_back():
    class Resp:
        def __init__(self, status_code, content=b""):
            self.status_code = status_code
            self.content = content

    seen = []

    async def fake_get(url, headers=None):
        seen.append(headers)
        return Resp(403) if headers else Resp(200, b"%PDF-1.4 inbound")

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=fake_get)):
        data = await _service().fetch_media("https://media.telnyx.test/x.pdf")

    assert data == b"%PDF-1.4 inbound"
    assert len(seen) == 2
    assert seen[0]["Authorization"] == "Bearer key"
    assert seen[1] is None


@pytest.mark.asyncio
async def test_fetch_media_returns_none_on_failure():
    async def fake_get(url, headers=None):
        raise RuntimeError("network down")

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=fake_get)):
        assert await _service().fetch_media("https://media.telnyx.test/x.pdf") is None


# ----- backend selection ----------------------------------------------------


def test_backend_selection_from_env(monkeypatch):
    from app import config as config_mod

    monkeypatch.setenv("FAX_BACKEND", "telnyx")
    monkeypatch.delenv("FAX_OUTBOUND_BACKEND", raising=False)
    monkeypatch.delenv("FAX_INBOUND_BACKEND", raising=False)
    config_mod.reload_settings()
    try:
        assert config_mod.settings.fax_backend == "telnyx"
        assert config_mod.active_outbound() == "telnyx"
        assert config_mod.active_inbound() == "telnyx"
        assert "telnyx" in config_mod.valid_backends()
    finally:
        monkeypatch.setenv("FAX_BACKEND", "phaxio")
        config_mod.reload_settings()


def test_telnyx_in_valid_backends_fallback():
    """The hardcoded fallback set must include telnyx.

    Without it, an unreadable config/provider_traits.json (tests running from
    another cwd) makes active_outbound() silently coerce telnyx to phaxio.
    """
    from app import config as config_mod

    with patch.object(config_mod, "get_provider_registry", return_value={}):
        assert "telnyx" in config_mod.valid_backends()


def test_telnyx_traits_registered():
    import json as _json
    import os

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    with open(os.path.join(root, "config", "provider_traits.json")) as f:
        traits = _json.load(f)
    assert "telnyx" in traits
    entry = traits["telnyx"]
    assert entry["kind"] == "cloud"
    assert entry["traits"]["supports_inbound"] is True
    # Telnyx accepts PDFs directly — no TIFF conversion, or /fax would hand it
    # a file the provider cannot read.
    assert entry["traits"]["requires_tiff"] is False
    assert set(entry["traits"]) == set(traits["_schema"]["canonical_trait_keys"])


# ----- end-to-end through the API -----------------------------------------


@pytest.fixture
def telnyx_env(monkeypatch, tmp_path):
    monkeypatch.setenv("FAX_BACKEND", "telnyx")
    monkeypatch.delenv("FAX_OUTBOUND_BACKEND", raising=False)
    monkeypatch.delenv("FAX_INBOUND_BACKEND", raising=False)
    monkeypatch.setenv("TELNYX_API_KEY", "test_key")
    monkeypatch.setenv("TELNYX_CONNECTION_ID", "test_conn")
    monkeypatch.setenv("TELNYX_FROM_E164", "+15551230000")
    # Both verification flags off — individual tests opt back in explicitly.
    monkeypatch.setenv("TELNYX_VERIFY_SIGNATURE", "false")
    monkeypatch.setenv("TELNYX_INBOUND_VERIFY_SIGNATURE", "false")
    monkeypatch.setenv("FAX_DISABLED", "true")
    monkeypatch.setenv("FAX_DATA_DIR", str(tmp_path))
    from app import config as config_mod

    config_mod.reload_settings()
    yield
    monkeypatch.setenv("FAX_BACKEND", "phaxio")
    config_mod.reload_settings()


def _create_job(client) -> str:
    files = {
        "to": (None, "+15551234567"),
        "file": ("test.pdf", TEST_PDF, "application/pdf"),
    }
    resp = client.post("/fax", files=files)
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["backend"] == "telnyx"
    assert data["status"] in {"queued", "disabled"}
    return data["id"]


def _job_status(job_id: str):
    from app.db import FaxJob, SessionLocal

    with SessionLocal() as db:
        job = db.get(FaxJob, job_id)
        return (job.status, job.pages, job.error, job.provider_sid) if job else None


def test_telnyx_end_to_end_submit(telnyx_env):
    with TestClient(app) as client:
        with patch("app.telnyx_service.get_telnyx_service") as mock_get_service:
            mock_service = Mock()
            mock_service.is_configured.return_value = True
            mock_service.send_fax = AsyncMock(
                return_value={
                    "provider_sid": "fax_123",
                    "status": "queued",
                    "provider_status": "queued",
                }
            )
            mock_get_service.return_value = mock_service
            _create_job(client)


@pytest.mark.asyncio
async def test_dispatcher_routes_telnyx_to_send_via_telnyx():
    """Regression guard: a missing dispatch arm silently falls through to SIP."""
    from app import main as main_mod

    with patch.object(main_mod, "_send_via_telnyx", new=AsyncMock()) as sender, patch.object(
        main_mod, "_originate_job", new=AsyncMock()
    ) as sip_sender:
        await main_mod._dispatch_fax_by_backend(
            "no_such_job", "+15551234567", "/tmp/x.pdf", "/tmp/x.tiff", "telnyx"
        )
    sender.assert_awaited_once()
    sip_sender.assert_not_awaited()
    assert sender.await_args.args[0] == "no_such_job"
    assert sender.await_args.args[2] == "/tmp/x.pdf"   # PDF, not TIFF


@pytest.mark.asyncio
async def test_send_via_telnyx_builds_media_url_and_updates_job(telnyx_env, monkeypatch):
    """Exercise the real send path (FAX_DISABLED=true skips it in the API test)."""
    from app import main as main_mod
    from app.db import FaxJob, SessionLocal

    monkeypatch.setenv("PUBLIC_API_URL", "https://fax.example.test/")
    from app import config as config_mod

    config_mod.reload_settings()

    with TestClient(app) as client:
        job_id = _create_job(client)

    mock_service = Mock()
    mock_service.is_configured.return_value = True
    mock_service.send_fax = AsyncMock(
        return_value={"provider_sid": "fax_sent", "status": "queued", "provider_status": "queued"}
    )
    with patch.object(main_mod, "get_telnyx_service", return_value=mock_service):
        await main_mod._send_via_telnyx(job_id, "+15551234567", "/tmp/ignored.pdf")

    kwargs = mock_service.send_fax.await_args.kwargs
    args = mock_service.send_fax.await_args.args
    assert args[0] == "+15551234567"
    media_url = args[1]
    assert media_url.startswith(f"https://fax.example.test/fax/{job_id}/pdf?token=")
    assert kwargs["job_id"] == job_id
    assert kwargs["webhook_url"] == f"https://fax.example.test/telnyx-callback?job_id={job_id}"

    with SessionLocal() as db:
        job = db.get(FaxJob, job_id)
        assert job.provider_sid == "fax_sent"
        assert job.status == "queued"
        # The tokenized URL handed to Telnyx must be servable by /fax/{id}/pdf
        assert job.pdf_url == media_url
        assert job.pdf_token and job.pdf_token in media_url
        assert job.pdf_token_expires_at is not None


@pytest.mark.asyncio
async def test_send_via_telnyx_marks_job_failed(telnyx_env):
    from app import main as main_mod
    from app.db import FaxJob, SessionLocal

    with TestClient(app) as client:
        job_id = _create_job(client)

    mock_service = Mock()
    mock_service.is_configured.return_value = True
    mock_service.send_fax = AsyncMock(side_effect=RuntimeError("Telnyx create fax error 422"))
    with patch.object(main_mod, "get_telnyx_service", return_value=mock_service):
        await main_mod._send_via_telnyx(job_id, "+15551234567", "/tmp/ignored.pdf")

    with SessionLocal() as db:
        job = db.get(FaxJob, job_id)
        assert job.status == "failed"
        assert "422" in (job.error or "")


@pytest.mark.asyncio
async def test_send_via_telnyx_fails_when_unconfigured(telnyx_env):
    from app import main as main_mod
    from app.db import FaxJob, SessionLocal

    with TestClient(app) as client:
        job_id = _create_job(client)

    with patch.object(main_mod, "get_telnyx_service", return_value=None):
        await main_mod._send_via_telnyx(job_id, "+15551234567", "/tmp/ignored.pdf")

    with SessionLocal() as db:
        job = db.get(FaxJob, job_id)
        assert job.status == "failed"
        assert "not properly configured" in (job.error or "")


def test_telnyx_callback_updates_job(telnyx_env):
    with TestClient(app) as client:
        job_id = _create_job(client)

        resp = client.post(
            f"/telnyx-callback?job_id={job_id}",
            json=_delivered_event(page_count=2),
        )
        assert resp.status_code == 200
        status, pages, error, _ = _job_status(job_id)
        assert status == "success"
        assert pages == 2
        assert error is None


def test_telnyx_callback_terminal_guard(telnyx_env):
    """A late in-progress event must not regress a terminal job."""
    with TestClient(app) as client:
        job_id = _create_job(client)

        client.post(f"/telnyx-callback?job_id={job_id}", json=_delivered_event())
        assert _job_status(job_id)[0] == "success"

        resp = client.post(
            f"/telnyx-callback?job_id={job_id}", json=_delivered_event(status="sending")
        )
        assert resp.status_code == 200
        assert _job_status(job_id)[0] == "success"


def test_telnyx_callback_records_failure(telnyx_env):
    with TestClient(app) as client:
        job_id = _create_job(client)
        client.post(
            f"/telnyx-callback?job_id={job_id}",
            json=_delivered_event(status="failed", failure_reason="no_answer"),
        )
        status, _, error, _ = _job_status(job_id)
        assert status == "failed"
        assert error == "no_answer"


def test_telnyx_callback_resolves_job_from_client_state(telnyx_env):
    """No job_id query param — fall back to the base64 client_state."""
    with TestClient(app) as client:
        job_id = _create_job(client)
        resp = client.post("/telnyx-callback", json=_delivered_event(job_id=job_id))
        assert resp.status_code == 200
        assert _job_status(job_id)[0] == "success"


def test_telnyx_callback_unknown_job_is_ok(telnyx_env):
    with TestClient(app) as client:
        resp = client.post("/telnyx-callback?job_id=does_not_exist", json=_delivered_event())
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


def test_telnyx_callback_rejects_bad_signature(telnyx_env, monkeypatch):
    _, public_b64 = _keypair()
    monkeypatch.setenv("TELNYX_VERIFY_SIGNATURE", "true")
    monkeypatch.setenv("TELNYX_PUBLIC_KEY", public_b64)
    from app import config as config_mod

    config_mod.reload_settings()

    with TestClient(app) as client:
        job_id = _create_job(client)
        resp = client.post(
            f"/telnyx-callback?job_id={job_id}",
            json=_delivered_event(),
            headers={
                "telnyx-signature-ed25519": base64.b64encode(b"x" * 64).decode(),
                "telnyx-timestamp": str(int(time.time())),
            },
        )
        assert resp.status_code == 401
        # Job untouched
        assert _job_status(job_id)[0] in {"queued", "disabled"}


def test_telnyx_callback_accepts_valid_signature(telnyx_env, monkeypatch):
    private_key, public_b64 = _keypair()
    monkeypatch.setenv("TELNYX_VERIFY_SIGNATURE", "true")
    monkeypatch.setenv("TELNYX_PUBLIC_KEY", public_b64)
    from app import config as config_mod

    config_mod.reload_settings()

    with TestClient(app) as client:
        job_id = _create_job(client)
        raw = json.dumps(_delivered_event()).encode()
        ts = int(time.time())
        resp = client.post(
            f"/telnyx-callback?job_id={job_id}",
            content=raw,
            headers={
                "content-type": "application/json",
                "telnyx-signature-ed25519": _sign(private_key, raw, ts),
                "telnyx-timestamp": str(ts),
            },
        )
        assert resp.status_code == 200
        assert _job_status(job_id)[0] == "success"


def test_telnyx_callback_fails_closed_without_public_key(telnyx_env, monkeypatch):
    """Verification on but no key configured must reject, not silently trust."""
    monkeypatch.setenv("TELNYX_VERIFY_SIGNATURE", "true")
    monkeypatch.setenv("TELNYX_PUBLIC_KEY", "")
    from app import config as config_mod

    config_mod.reload_settings()

    with TestClient(app) as client:
        resp = client.post("/telnyx-callback?job_id=x", json=_delivered_event())
        assert resp.status_code == 401


# ----- inbound --------------------------------------------------------------


def _received_event(fax_id="fax_in_1", media_url="https://media.telnyx.test/in.pdf"):
    return {
        "data": {
            "event_type": "fax.received",
            "id": "evt_in",
            "payload": {
                "fax_id": fax_id,
                "status": "received",
                "from": "+15559990000",
                "to": "+15551230000",
                "page_count": 1,
                "media_url": media_url,
                "direction": "inbound",
            },
        }
    }


def test_inbound_verify_flag_adds_strictness(telnyx_env, monkeypatch):
    """TELNYX_INBOUND_VERIFY_SIGNATURE must gate inbound even with the main flag off."""
    _, public_b64 = _keypair()
    monkeypatch.setenv("INBOUND_ENABLED", "true")
    monkeypatch.setenv("TELNYX_VERIFY_SIGNATURE", "false")
    monkeypatch.setenv("TELNYX_INBOUND_VERIFY_SIGNATURE", "true")
    monkeypatch.setenv("TELNYX_PUBLIC_KEY", public_b64)
    from app import config as config_mod

    config_mod.reload_settings()
    try:
        with TestClient(app) as client:
            # Inbound is verified → unsigned event rejected
            assert client.post("/telnyx-inbound", json=_received_event()).status_code == 401
            # Outbound verification is off → unsigned status event still accepted
            resp = client.post("/telnyx-callback?job_id=nope", json=_delivered_event())
            assert resp.status_code == 200
    finally:
        monkeypatch.setenv("INBOUND_ENABLED", "false")
        config_mod.reload_settings()


def test_main_verify_flag_covers_inbound_events(telnyx_env, monkeypatch):
    """A forged event_type must not downgrade verification."""
    _, public_b64 = _keypair()
    monkeypatch.setenv("INBOUND_ENABLED", "true")
    monkeypatch.setenv("TELNYX_VERIFY_SIGNATURE", "true")
    monkeypatch.setenv("TELNYX_INBOUND_VERIFY_SIGNATURE", "false")
    monkeypatch.setenv("TELNYX_PUBLIC_KEY", public_b64)
    from app import config as config_mod

    config_mod.reload_settings()
    try:
        with TestClient(app) as client:
            assert client.post("/telnyx-inbound", json=_received_event()).status_code == 401
            assert client.post("/telnyx-callback", json=_delivered_event()).status_code == 401
    finally:
        monkeypatch.setenv("INBOUND_ENABLED", "false")
        config_mod.reload_settings()


def test_both_verify_flags_off_accepts_unsigned(telnyx_env, monkeypatch):
    monkeypatch.setenv("INBOUND_ENABLED", "true")
    monkeypatch.setenv("TELNYX_VERIFY_SIGNATURE", "false")
    monkeypatch.setenv("TELNYX_INBOUND_VERIFY_SIGNATURE", "false")
    from app import config as config_mod

    config_mod.reload_settings()
    try:
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_media_resp())):
            with TestClient(app) as client:
                resp = client.post("/telnyx-inbound", json=_received_event(fax_id="fax_unsigned"))
                assert resp.status_code == 200
    finally:
        monkeypatch.setenv("INBOUND_ENABLED", "false")
        config_mod.reload_settings()


def test_telnyx_inbound_404_when_disabled(telnyx_env, monkeypatch):
    monkeypatch.setenv("INBOUND_ENABLED", "false")
    from app import config as config_mod

    config_mod.reload_settings()
    with TestClient(app) as client:
        for path in ("/telnyx-inbound", "/telnyx-callback"):
            assert client.post(path, json=_received_event()).status_code == 404


def test_telnyx_inbound_404_when_other_backend_active(telnyx_env, monkeypatch):
    monkeypatch.setenv("INBOUND_ENABLED", "true")
    monkeypatch.setenv("FAX_INBOUND_BACKEND", "sip")
    from app import config as config_mod

    config_mod.reload_settings()
    try:
        with TestClient(app) as client:
            assert client.post("/telnyx-inbound", json=_received_event()).status_code == 404
    finally:
        monkeypatch.delenv("FAX_INBOUND_BACKEND", raising=False)
        monkeypatch.setenv("INBOUND_ENABLED", "false")
        config_mod.reload_settings()


def test_telnyx_inbound_stores_fax(telnyx_env, monkeypatch, tmp_path):
    monkeypatch.setenv("INBOUND_ENABLED", "true")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    from app import config as config_mod
    from app.db import InboundFax, SessionLocal

    config_mod.reload_settings()
    try:
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_media_resp())):
            with TestClient(app) as client:
                resp = client.post("/telnyx-inbound", json=_received_event(fax_id="fax_in_store"))
                assert resp.status_code == 200
                assert resp.json() == {"status": "ok"}

                # Replaying the same event must not create a second row
                resp = client.post("/telnyx-inbound", json=_received_event(fax_id="fax_in_store"))
                assert resp.status_code == 200

        with SessionLocal() as db:
            rows = db.query(InboundFax).filter(InboundFax.provider_sid == "fax_in_store").all()
            assert len(rows) == 1
            row = rows[0]
            assert row.backend == "telnyx"
            assert row.from_number == "+15559990000"
            assert row.pages == 1
            assert row.size_bytes == len(TEST_PDF)
            assert row.pdf_path
    finally:
        monkeypatch.setenv("INBOUND_ENABLED", "false")
        config_mod.reload_settings()


def _media_resp():
    class Resp:
        status_code = 200
        content = TEST_PDF

    return Resp()


def test_telnyx_inbound_ignores_event_without_fax_id(telnyx_env, monkeypatch):
    monkeypatch.setenv("INBOUND_ENABLED", "true")
    from app import config as config_mod

    config_mod.reload_settings()
    try:
        body = _received_event()
        body["data"]["payload"].pop("fax_id")
        with TestClient(app) as client:
            resp = client.post("/telnyx-inbound", json=body)
            assert resp.status_code == 200
            assert resp.json() == {"status": "ignored"}
    finally:
        monkeypatch.setenv("INBOUND_ENABLED", "false")
        config_mod.reload_settings()


# ----- admin surfaces -------------------------------------------------------


ADMIN_KEY = "bootstrap_admin_only"


def _admin_headers():
    return {"X-API-Key": ADMIN_KEY}


@pytest.fixture
def admin_env(telnyx_env, monkeypatch):
    monkeypatch.setenv("API_KEY", ADMIN_KEY)
    monkeypatch.setenv("REQUIRE_API_KEY", "true")
    from app import config as config_mod

    config_mod.reload_settings()
    yield


def test_admin_settings_exposes_telnyx(admin_env):
    with TestClient(app) as client:
        resp = client.get("/admin/settings", headers=_admin_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["telnyx"]["configured"] is True
        assert body["telnyx"]["connection_id"] == "test_conn"
        assert body["telnyx"]["api_key"] != "test_key"      # masked
        assert "telnyx" in body["inbound"]


def test_admin_config_reports_telnyx_configured(admin_env):
    with TestClient(app) as client:
        resp = client.get("/admin/config", headers=_admin_headers())
        assert resp.status_code == 200, resp.text
        assert resp.json()["backend_configured"]["telnyx"] is True


def test_admin_health_status_reflects_telnyx_config(admin_env, monkeypatch):
    """An unconfigured Telnyx must not report healthy (the default arm does)."""
    with TestClient(app) as client:
        resp = client.get("/admin/health-status", headers=_admin_headers())
        assert resp.status_code == 200, resp.text
        assert resp.json()["backend"] == "telnyx"

        monkeypatch.setenv("TELNYX_API_KEY", "")
        from app import config as config_mod

        config_mod.reload_settings()
        resp = client.get("/admin/health-status", headers=_admin_headers())
        assert resp.status_code == 200
        assert resp.json()["backend_healthy"] is False


def test_admin_settings_update_persists_telnyx(admin_env):
    with TestClient(app) as client:
        resp = client.put(
            "/admin/settings",
            headers=_admin_headers(),
            json={
                "outbound_backend": "telnyx",
                "telnyx_api_key": "rotated_key",
                "telnyx_connection_id": "rotated_conn",
                "telnyx_from_e164": "+15557778888",
                "telnyx_verify_signature": False,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["telnyx"]["connection_id"] == "rotated_conn"
        assert body["telnyx"]["verify_signature"] is False

        # The rotated key must reach the service singleton, not a stale instance
        from app.telnyx_service import get_telnyx_service

        service = get_telnyx_service()
        assert service is not None
        assert service.api_key == "rotated_key"
        assert service.connection_id == "rotated_conn"


def test_admin_inbound_callbacks_lists_telnyx(admin_env):
    with TestClient(app) as client:
        resp = client.get("/admin/inbound/callbacks", headers=_admin_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["backend"] == "telnyx"
        assert body["callbacks"]
        assert body["callbacks"][0]["url"].endswith("/telnyx-inbound")


def test_admin_validate_telnyx_presence_only(admin_env):
    """Network failures must not be reported as a credential failure."""
    with TestClient(app) as client:
        with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=RuntimeError("no net"))):
            resp = client.post(
                "/admin/settings/validate",
                headers=_admin_headers(),
                json={
                    "backend": "telnyx",
                    "telnyx_api_key": "test_key",
                    "telnyx_connection_id": "test_conn",
                },
            )
        assert resp.status_code == 200, resp.text
        checks = resp.json()["checks"]
        assert checks["auth"] is True
        assert checks["reachable"] is False


def test_admin_validate_telnyx_missing_credentials(admin_env, monkeypatch):
    monkeypatch.setenv("TELNYX_API_KEY", "")
    monkeypatch.setenv("TELNYX_CONNECTION_ID", "")
    from app import config as config_mod

    config_mod.reload_settings()
    with TestClient(app) as client:
        resp = client.post(
            "/admin/settings/validate", headers=_admin_headers(), json={"backend": "telnyx"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["checks"]["auth"] is False


def test_env_export_includes_telnyx(telnyx_env):
    from app.main import _export_settings_full_env

    env = _export_settings_full_env()
    assert "TELNYX_API_KEY=test_key" in env
    assert "TELNYX_CONNECTION_ID=test_conn" in env
    assert "TELNYX_FROM_E164=+15551230000" in env
    assert "TELNYX_INBOUND_VERIFY_SIGNATURE=" in env
