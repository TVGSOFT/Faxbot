# Admin Console Terminal

The Admin Console includes a built‑in terminal that provides direct shell access to the Faxbot container or server environment via a secure WebSocket.

## Features

- Full TTY with `xterm-256color`, history, and standard shortcuts
- Uses existing admin authentication
- Container‑aware; works in Docker and local dev

!!! tip
    Default posture is local‑only. Keep it that way unless you fully trust the network path.

## Install

- Docker images include required deps. For manual installs:

```bash
./scripts/install-terminal-deps.sh
```

## Usage

1. Open the Admin Console
2. Authenticate with your admin API key
3. Open the Terminal tab and start typing

## Security

- Admin‑only; requires a key with `keys:manage` scope (or bootstrap `API_KEY`)
- Runs with the same privileges as the API service

!!! warning
    Avoid exposing the Terminal over public tunnels or shared networks. Keep SIP/AMI and internal interfaces private.

## Troubleshooting

- If the terminal won’t connect, verify the API is up and check browser console logs
- For older servers, ensure WebSocket query parsing matches your Starlette version
