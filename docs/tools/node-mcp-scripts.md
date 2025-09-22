# Node MCP Scripts

Helper scripts for running and testing the Node.js MCP server that integrates tools like `send_fax` with assistants.

Prerequisites
- Node.js 18+
- A running Faxbot API (`FAX_API_URL`, default `http://localhost:8080`)
- Optional: `API_KEY` for protected endpoints

Environment
- Scripts inherit `FAX_API_URL` and `API_KEY` from your shell or `.env`.

Server launchers
- `node_mcp/scripts/start-stdio.sh` — stdio server (`src/servers/stdio.js`)
- `node_mcp/scripts/start-http.sh` — HTTP server (port 3001)
- `node_mcp/scripts/start-sse.sh` — SSE server (port 3002)

Tool invocations
- `node node_mcp/scripts/test-stdio.js "+15551234567" /abs/path/sample.pdf`
- `node node_mcp/scripts/call-send-fax.js "+15551234567" /abs/path/sample.pdf`

Notes
- For HTTP/SSE, large files must be base64‑encoded JSON; keep under ~16 MB.
- Prefer stdio + `filePath` for desktop integrations to avoid base64 overhead.
