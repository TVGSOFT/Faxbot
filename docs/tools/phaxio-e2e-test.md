# Phaxio End-to-End Test (No Physical Fax Required)

Goal: Send a real fax through Phaxio and receive it on a Phaxio number — fully end-to-end, no hardware.

Prerequisites
- Phaxio API key/secret and a Phaxio receiving number
- Public HTTPS URL for callbacks and PDF fetch

1) Configure Faxbot for Phaxio
```
FAX_BACKEND=phaxio
API_KEY=<secure>
PHAXIO_API_KEY=<from console>
PHAXIO_API_SECRET=<from console>
PUBLIC_API_URL=https://<your-host>
PHAXIO_CALLBACK_URL=https://<your-host>/phaxio-callback
```
Start API: `make up-cloud`

2) Expose the API via HTTPS
- Fast path: `./scripts/setup-phaxio-tunnel.sh`
- Manual: cloudflared or ngrok; set `PUBLIC_API_URL` and `PHAXIO_CALLBACK_URL`, restart API.

3) Send a fax to your Phaxio number
```
echo "Test Faxbot → Phaxio end-to-end" > /tmp/fax.txt
FAX_API_URL=http://localhost:8080 API_KEY=$API_KEY ./scripts/send-fax.sh +1YOURPHAXIONUMBER /tmp/fax.txt
```
Poll status: `./scripts/get-status.sh <job_id>`

4) Verify delivery
- Phaxio dashboard shows inbound fax
- Callback updates job status in Faxbot

Notes
- Use HTTPS in production; secure `/fax` with `X-API-Key`
- Provider retries webhooks; monitor API logs for `pdf_served` and status updates
