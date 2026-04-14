"""
PyCharm debug entry point for the Faxbot API.

Run/debug this file directly from PyCharm to get full breakpoint support.

IMPORTANT: --reload is intentionally OFF.
  reload=True spawns a child process which breaks PyCharm's debugger attachment.
  Restart the run config manually after code changes when debugging.
"""
import os
import sys
from pathlib import Path

# ── Load .env from repo root ──────────────────────────────────────────────────
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ── Ensure repo root is on sys.path so `api.app.main` resolves ───────────────
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,       # Keep False — reload breaks PyCharm debugger
        log_level="debug",
    )

