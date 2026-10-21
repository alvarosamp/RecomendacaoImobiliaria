"""Local read-only demo. No credentials, real subscribers or external API dependency."""
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from planner import Planner, PlanningError

ROOT = Path(__file__).resolve().parent
PLANNER = Planner.from_directory(ROOT / 'data')


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'web'), **kwargs)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ('/health', '/api/simulation', '/api/roads', '/api/radar', '/api/territory', '/api/regulations'):
            if path == '/health':
                body = json.dumps({'status': 'ok', 'mode': 'synthetic-demo'}).encode()
            else:
                name = {'/api/simulation':'simulation.json','/api/roads':'roads.json','/api/radar':'radar.json','/api/territory':'territory.json','/api/regulations':'regulations.json'}[path]
                body = (ROOT / 'data' / name).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != '/api/plan':
            self.send_json(404, {'error':'Endpoint não encontrado.'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16384:
                self.send_json(413, {'error':'O pedido deve conter até 16 KB de JSON.'})
                return
            if self.headers.get('Content-Type','').split(';')[0].strip() != 'application/json':
                self.send_json(415, {'error':'Envie o estudo como application/json.'})
                return
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise PlanningError('O estudo deve ser um objeto JSON.')
            result = PLANNER.plan(payload)
        except (PlanningError, ValueError, UnicodeError) as error:
            self.send_json(400, {'error':str(error)})
            return
        self.send_json(200, result)

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        super().end_headers()


if __name__ == '__main__':
    host, port = os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '18089'))
    print(f'Urbia ISP · simulação local em http://{host}:{port}', flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
