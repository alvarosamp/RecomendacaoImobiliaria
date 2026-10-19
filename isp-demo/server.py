"""Local read-only demo. No credentials, real subscribers or external API dependency."""
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'web'), **kwargs)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ('/health', '/api/simulation', '/api/roads', '/api/radar'):
            if path == '/health':
                body = json.dumps({'status': 'ok', 'mode': 'synthetic-demo'}).encode()
            else:
                name = {'/api/simulation':'simulation.json','/api/roads':'roads.json','/api/radar':'radar.json'}[path]
                body = (ROOT / 'data' / name).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        super().end_headers()


if __name__ == '__main__':
    host, port = os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '18089'))
    print(f'Urbia ISP · simulação local em http://{host}:{port}', flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
