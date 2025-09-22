# v3 Phase Status (Summary)

High‑level readiness notes for v3 plugins, backends, and Admin Console features. Originally tracked in development.

Highlights
- v3 plugin loader and config endpoints — available behind feature flags
- Backends — Phaxio/Sinch stable; SIP/Asterisk stable for outbound; FreeSWITCH preview
- Admin Console — core flows present; Plugins tab gated; Scripts & Tests coverage expanding
- Docs — MkDocs primary, Material theme, mike to gh‑pages

Focus areas
- UI parity for all features with contextual help/links
- Backend isolation via traits (no backend name gating)
- Test coverage for Admin actions and Terminal WS
