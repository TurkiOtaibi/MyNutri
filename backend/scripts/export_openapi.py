from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path
from typing import NoReturn


def _reject_network(*_args: object, **_kwargs: object) -> NoReturn:
    raise RuntimeError("OpenAPI export must not initialize network access.")


def export_openapi(output: Path) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_root))

    original_connect = socket.socket.connect
    original_create_connection = socket.create_connection
    socket.socket.connect = _reject_network  # type: ignore[method-assign]
    socket.create_connection = _reject_network
    try:
        from app.main import app

        schema = app.openapi()
    finally:
        socket.socket.connect = original_connect  # type: ignore[method-assign]
        socket.create_connection = original_create_connection

    serialized = json.dumps(
        schema,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{serialized}\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the FastAPI OpenAPI schema without starting the application."
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export_openapi(args.output)


if __name__ == "__main__":
    main()
