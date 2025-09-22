# MCP Integration (Legacy Overview)

This page consolidates the broader MCP integration overview from the development branch. Modern guides live under the MCP section.

Transports
- Node: stdio, HTTP, SSE, WebSocket helper
- Python: stdio, SSE

Quick Start (stdio)
```
{
  "mcpServers": {
    "faxbot": {
      "command": "node",
      "args": ["src/servers/stdio.js"],
      "cwd": "/PATH/TO/faxbot/node_mcp",
      "env": { "FAX_API_URL": "http://localhost:8080", "API_KEY": "your_api_key" }
    }
  }
}
```

Tools
- `send_fax` — stdio `{ to, filePath }`; HTTP/SSE `{ to, fileContent, fileName, fileType }`
- `get_fax_status` — `{ jobId }`

SSE (OAuth2/JWT)
- Set `OAUTH_ISSUER`, `OAUTH_AUDIENCE`, optional `OAUTH_JWKS_URL`
- Use Bearer tokens per your IdP; see Security → OAuth/OIDC Setup

Inspector
- `npx @modelcontextprotocol/inspector` or Docker profile `mcp-inspector`
- Configure stdio/http/sse endpoints and headers accordingly

See also
- MCP: ../mcp/index.md
- Transports: ../mcp/transports.md
- Images & PDFs: ../guides/images-and-pdfs.md
