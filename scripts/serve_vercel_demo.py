"""Serve the packaged public demo locally for browser verification."""
from pathlib import Path
import sys
import importlib.util
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[1] / 'tmp/vercel-imobiliario'
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('demo_api', ROOT / 'api/demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'public'), **kwargs)
    def do_GET(self):
        if self.path.startswith('/api/demo'):
            return demo.handler.do_GET(self)
        if self.path.split('?')[0] in ('/', '/app', '/login', '/register'):
            self.path = '/index.html'
        super().do_GET()
    do_POST = demo.handler.do_POST

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 4188), Handler).serve_forever()
