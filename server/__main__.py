from __future__ import annotations

import os

import uvicorn


def main() -> None:
    # Hosts inject PORT. Bind all interfaces in containers; localhost still works.
    host = os.environ.get("LAPSIMPRO_HOST") or os.environ.get("HOST") or "0.0.0.0"
    port = int(os.environ.get("PORT") or os.environ.get("LAPSIMPRO_PORT") or "8787")
    uvicorn.run("server.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
