# MCP Integration

<div class="grid cards" markdown>

- :material-nodejs: **Node Server**  
  stdio, HTTP, SSE transports.  
  [Open](node.md)

- :material-language-python: **Python Server**  
  stdio and SSE transports.  
  [Open](python.md)

- :material-connection: **Transports**  
  Capabilities and limits across stdio/HTTP/SSE.  
  [Reference](transports.md)

</div>

Faxbot provides MCP servers in Node and Python with identical tools:
- Tools: `send_fax`, `get_fax_status`
- Transports:
  - stdio (local desktop assistants)
  - HTTP (Node streamable HTTP)
  - SSE + OAuth2 (Node and Python)

See also: [Transports](transports.md)

Limits and file handling
- stdio: use `filePath` to avoid base64 limits
- HTTP/SSE: JSON limit is ~16 MB for Node; REST API raw file limit is 10 MB
- Allowed types: PDF, TXT
