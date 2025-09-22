# API Tests Overview

Location: `api/tests/`

How to run
- Docker: `make test`
- Local: create a venv and run `pytest api/tests`

Test files (high level)
- `test_api.py` — health and basic `/fax` validation
- `test_api_keys.py` — admin key mint/list/revoke, send and read with token
- `test_api_scopes.py` — scope enforcement for send/read
- `test_rate_limit.py` — per‑key rate limiting
- `test_phaxio.py` — Phaxio send path (mocked), status mapping, callback, PDF token endpoint
- `test_inbound_internal.py` — internal inbound post/list/get/PDF (scoped)
- `test_freeswitch.py` — disabled‑mode outbound result callback → SUCCESS

Tips
- Set `FAX_DISABLED=true` to simulate sends without contacting a provider.
- Use a temporary `FAX_DATA_DIR` per test run to isolate artifacts.
