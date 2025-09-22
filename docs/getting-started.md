# Getting started

A fast path to a working Faxbot and your first fax.

Quick steps
- Start the API (Docker): `docker compose up -d --build api`
- Set an API key: add `API_KEY=your_secure_key` to `.env`
- Send a fax (PDF/TXT):
  ```bash
  curl -X POST http://localhost:8080/fax \
    -H "X-API-Key: $API_KEY" \
    -F to=+15551234567 \
    -F file=@./example.pdf
  ```
- Check status: `curl -H "X-API-Key: $API_KEY" http://localhost:8080/fax/<job_id>`

Next
- Choose a backend and follow setup:
  - Phaxio (Cloud): setup/phaxio.md
  - Sinch (Cloud v3): setup/sinch.md
  - SIP/Asterisk (Self‑hosted): setup/sip-asterisk.md
- Explore the Admin Console: admin-console.md
- Review security defaults for HIPAA vs non‑PHI: security/index.md
