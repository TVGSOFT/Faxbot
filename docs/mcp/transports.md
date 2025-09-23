# MCP Transports

## HTTP (Node MCP)

Port
: `3001` (default)

Auth
: Protect with `MCP_HTTP_API_KEY`; set strict `MCP_HTTP_CORS_ORIGIN` (no `*` when credentials)

Deployment
: Run behind TLS via reverse proxy; add IP allowlists and rate limits where appropriate

## SSE (Node/Python MCP)

Ports
: `3002` (Node), `3003` (Python)

Auth
: Require OAuth2/JWT in production. Configure `OAUTH_ISSUER`, `OAUTH_AUDIENCE`, and (optionally) `OAUTH_JWKS_URL`

Deployment
: Run behind TLS; validate tokens against your IdP; set short TTLs

## WebSocket (Node MCP)

Port
: `3004` (default)

Auth
: Protect with `MCP_WS_API_KEY` (or reuse `API_KEY`)

Deployment
: Run behind TLS or an authenticated proxy; use only for trusted clients or internal networks

## Stdio

Use case
: Best for desktop assistants; avoids base64 limits

Files
: Prefer `filePath` for fidelity

## Limits

REST API
: Raw file limit `MAX_FILE_SIZE_MB` (default 10 MB)

Node MCP HTTP
: JSON body limit ~16 MB (base64 payload)
