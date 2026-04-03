#!/usr/bin/env python3
"""
Start the GarminForge web server.

Usage:
    python run.py [--host HOST] [--port PORT] [--reload]

Environment variables:
    SECRET_KEY   — session signing key (auto-generated if omitted; set a stable
                   value in production so sessions survive restarts)
    GARMINTOKENS — path to token directory (default: ~/.garminconnect)

Quick start:
    pip install garminconnect[workout] fastapi uvicorn[standard] jinja2 python-multipart itsdangerous
    python run.py
    # Open http://localhost:8000
"""

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="GarminForge web server")
    parser.add_argument("--host",   default="0.0.0.0",   help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port",   type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--reload", action="store_true",   help="Auto-reload on code changes (dev mode)")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print(
            "uvicorn is not installed.\n"
            "Install web dependencies with:\n"
            "    pip install garminconnect[workout] fastapi 'uvicorn[standard]' "
            "jinja2 python-multipart itsdangerous\n"
            "Or: pip install -e '.[web]'",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Starting GarminForge at http://{args.host}:{args.port}")
    uvicorn.run(
        "web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
