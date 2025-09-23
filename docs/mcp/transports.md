# MCP Transports

## HTTP (Node MCP)

:material-lan: Port
: `3001` (default)

:material-shield-lock: Auth
: Protect with `MCP_HTTP_API_KEY`; set strict `MCP_HTTP_CORS_ORIGIN` (no `*` when credentials)

:material-cloud-lock: Deployment
: Run behind TLS via reverse proxy; add IP allowlists and rate limits where appropriate

## SSE (Node/Python MCP)

:material-lan-connect: Ports
: `3002` (Node), `3003` (Python)

:material-shield-key: Auth
: Require OAuth2/JWT in production. Configure `OAUTH_ISSUER`, `OAUTH_AUDIENCE`, and (optionally) `OAUTH_JWKS_URL`

:material-cloud-lock: Deployment
: Run behind TLS; validate tokens against your IdP; set short TTLs

## WebSocket (Node MCP)

:material-websocket: Port
: `3004` (default)

:material-shield-lock: Auth
: Protect with `MCP_WS_API_KEY` (or reuse `API_KEY`)

:material-cloud-lock: Deployment
: Run behind TLS or an authenticated proxy; use only for trusted clients or internal networks

## Stdio

:material-console-line: Use case
: Best for desktop assistants; avoids base64 limits

:material-file: Files
: Prefer `filePath` for fidelity

## Limits

:material-upload: REST API
: Raw file limit `MAX_FILE_SIZE_MB` (default 10 MB)

:material-code-json: Node MCP HTTP
: JSON body limit ~16 MB (base64 payload)
