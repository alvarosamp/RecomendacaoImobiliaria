"""Vercel entrypoint: reuse the Docker server's planning validation and engine."""
from pathlib import Path
import sys

# Resolve from this file, not the function's current working directory.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import Handler  # noqa: E402


class handler(Handler):
    """Only the planning API is dynamic; never expose the source as static files."""

    def do_GET(self):
        self.send_response(405)
        self.send_header('Allow', 'POST')
        self.send_header('Content-Length', '0')
        self.end_headers()

    do_HEAD = do_GET
    do_OPTIONS = do_GET
