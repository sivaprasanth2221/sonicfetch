from __future__ import annotations

import argparse

import uvicorn

from app.config import settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the YouTube to MP3 backend application."
    )
    parser.add_argument("--host", default=settings.host, help="Host to bind the backend server.")
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help="Port to bind the backend server.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    uvicorn.run("app.server:app", host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
