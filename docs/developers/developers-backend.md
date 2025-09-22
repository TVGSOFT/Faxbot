# Backend Internals (Developers)

Notes covering backend architecture, settings validation, admin endpoints, and UI guardrails. This page is adapted from development docs and summarizes internals for implementers.

Topics
- Admin namespace and settings lifecycle (get/update/reload/validate)
- Local-only Admin UI posture and middleware
- Plugins (v3) feature gating and config persistence
- Jobs/inbound listing and scopes
- Diagnostics surface and Admin Actions

See also
- Security overview: ../security/index.md
- OAuth/OIDC setup: ../security/oauth-setup.md
- Canonical events: ../api/canonical-events.md
