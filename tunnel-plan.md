# Faxbot Auto‑Tunneling — Current State and Revised Plan (v1.5)

This reflects what’s in the repo now and what’s required next. It follows AGENTS.md: Admin Console first, backend isolation, HIPAA‑safe defaults, and no CLI‑only features. Tunnels serve both non‑HIPAA users (external reachability) and HIPAA users (private VPN access).

## 0) Big Picture

- Purpose: external reachability for the Admin Console and iOS app when LAN access isn’t available. Not for SIP/UDPTL/T.38 media.
- Boundaries: the API surfaces status, runs safe checks, and persists config; it does not orchestrate containers.
- Compliance: HIPAA posture disables Cloudflare Quick Tunnel and hides public URL. WireGuard/Tailscale are HIPAA‑capable.
- Target: persisted provider choice, reliable status, WireGuard QR + .conf, isolated UX, helpful docs.

## 1) Current Reality (implemented)

Server (FastAPI)
- ~~`GET /admin/tunnel/status`: status with HIPAA guard; dev‑only Cloudflared log parsing to auto‑detect trycloudflare URL when mounted.~~
- ~~`POST /admin/tunnel/config`: runtime apply of provider settings (pairs with persisted provider via `/admin/settings`).~~
- ~~`POST /admin/tunnel/test`: probes health via public/tunnel URL.~~
- ~~`POST /admin/tunnel/pair`: short‑lived numeric pairing code.~~
- ~~`POST /admin/tunnel/register-sinch`: gated by inbound=sinch; sets webhook to `{public}/sinch-inbound`.~~
- ~~`GET /admin/tunnel/cloudflared/logs`: safe file tail (no shell).~~

Admin Console (Vite/React/MUI)
- ~~Tools → Tunnels: provider select (none|cloudflare|wireguard|tailscale), Save & Apply, Test, Pairing code, Register with Sinch (only when applicable), Cloudflared logs (HIPAA‑off only).~~

Compose / Runtime
- ~~`cloudflared` sidecar (profile `cloudflare`), logs bind‑mounted to API for auto‑detect. No shell orchestration from API.~~

Security / HIPAA
- ~~Admin endpoints require bootstrap API_KEY or a DB key with `keys:manage`. Cloudflare URL hidden/blocked in HIPAA posture.~~

## 2) Notable Changes Since v1.3

- ~~WireGuard QR is SVG‑only via `segno` (no native deps). `.conf` size capped; must include `[Interface]`, `PrivateKey`, and `[Peer]`.~~
- ~~Safe Cloudflared logs endpoint added; removed unsafe admin actions.~~
- ~~Persisted `tunnel_provider` via `/admin/settings`; `.env` export includes `TUNNEL_PROVIDER` when set.~~
- ~~Setup Wizard and Settings select bindings fixed to stick to saved values.~~
- ~~Dashboard “System Status” now routes directly to Tools → Diagnostics.~~
- ~~Sinch: optional `SINCH_BASE_URL` override supported server‑side and exposed in Settings.~~

## 3) What’s Left (P0)

- Sinch auth probe resilience: if `services/default` isn’t enabled for some tenants, add a simple fallback probe (e.g., `GET /faxes?limit=1`).
- Tighten Admin UI types where using `any` in Tunnels panel and Wizard.
- Docs: ensure tunnels page and Sinch setup clearly reflect current behavior.

## 4) WireGuard

- Endpoints (admin‑only):
  - Import `.conf` (file or text) → stored at `WIREGUARD_CONF_PATH` (mode 600), returns `{ ok: true }` only.
  - Download/Delete `.conf`.
  - QR render: returns `{ svg_base64 }` only.
- Security: no `.conf` content in logs; admin‑only endpoints.

## 5) Cloudflare “Just Works” (non‑HIPAA)

- Start: `docker compose --profile cloudflare up -d --build api cloudflared`.
- Auto‑detect: API reads mounted log and sets runtime `PUBLIC_API_URL` when allowed. Admin Console remains local‑only unless `ADMIN_UI_ALLOW_TUNNEL=true` (demo only).

## 6) HIPAA Posture

- Cloudflare disabled; select WireGuard or Tailscale. Require HTTPS for public URLs and avoid exposing the Admin Console through proxies.

## 7) CTO Alpha Test Readiness

- Preconditions (Done): Sinch gating, SVG‑only QR, WG validation, persisted tunnel_provider, safe logs, select bindings fixed, diagnostics routing.
- Smoke:
  1) Admin login with bootstrap key (or DB key with `keys:manage`).
  2) Non‑HIPAA: launch with Cloudflared profile; status shows “Connected” (or at least “Connected via public URL”).
  3) WireGuard: import `.conf`, Show QR (SVG), Download, Delete.
  4) HIPAA: `ENFORCE_PUBLIC_HTTPS=true`; Cloudflare disabled; WG still works.
  5) Sinch: with inbound=sinch and creds, register webhook succeeds (set region if needed via Base URL field).

## 8) Plan Hygiene

- Re‑read this plan before each change. Update sections when behaviors change (QR format, endpoints, UI routing) and keep CTO readiness explicit.

