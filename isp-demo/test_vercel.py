"""HTTP contract and deployment artifact tests for the Vercel adapter."""
import http.client
import json
import os
import re
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from api.plan import handler
from build_vercel import build, OUTPUT, ROOT
from server import PLANNER


class VercelHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path='/api/plan', body=None, content_type='application/json'):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=30)
        connection.request(method, path, body=body, headers={'Content-Type': content_type})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_planning_matches_engine_from_other_working_directory(self):
        request = PLANNER.inventory['requests'][2]
        payload = {k:request[k] for k in ('city_id','lat','lng')}
        payload['request_id'] = request['id']
        original = Path.cwd()
        try:
            os.chdir('/tmp')
            status, headers, body = self.request('POST', body=json.dumps(payload))
        finally:
            os.chdir(original)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), PLANNER.plan(payload))
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertLess(len(body), 4_500_000)

    def test_input_validation_is_preserved(self):
        for body, kind, expected in [('[]','application/json',400), ('{','application/json',400), ('{}','text/plain',415), ('x'*16385,'application/json',413), ('{}','application/json',400)]:
            with self.subTest(expected=expected):
                status, _, response = self.request('POST', body=body, content_type=kind)
                self.assertEqual(status, expected)
                self.assertIn('error', json.loads(response))

    def test_function_cannot_serve_source_or_data_files(self):
        for path in ('/api/plan', '/server.py', '/data/simulation.json', '/../planner.py'):
            status, headers, body = self.request('GET', path)
            self.assertEqual(status, 405)
            self.assertEqual(headers['Allow'], 'POST')
            self.assertEqual(body, b'')
        self.assertEqual(self.request('POST', '/not-plan', '{}')[0], 404)
        self.assertEqual(self.request('HEAD')[0], 405)


class VercelArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()
        cls.config = json.loads((ROOT/'vercel.json').read_text())

    def test_snapshot_rewrites_preserve_the_data(self):
        paths = {r['source']:r['destination'] for r in self.config['rewrites']}
        for name, file in (('simulation','simulation'),('roads','roads'),('radar','radar'),('territory','territory'),('regulations','regulations'),('market','market'),('companies','market-companies')):
            target = OUTPUT / paths[f'/api/{name}'].lstrip('/')
            self.assertEqual(json.loads(target.read_text()), json.loads((ROOT/'data'/f'{file}.json').read_text()))
        self.assertEqual(json.loads((OUTPUT/'health.json').read_text())['status'], 'ok')
        self.assertEqual(self.config['outputDirectory'], 'public')
        self.assertIsNone(self.config['framework'])

    def test_assets_exist_and_no_sources_are_public(self):
        html = (OUTPUT/'index.html').read_text()
        for asset in re.findall(r'(?:src|href)="(/[^"?#]+)', html):
            self.assertTrue((OUTPUT/asset.lstrip('/')).is_file(), asset)
        self.assertEqual((OUTPUT/'vendor'/'LEAFLET-LICENSE').read_bytes(), (ROOT/'web'/'vendor'/'LEAFLET-LICENSE').read_bytes())
        for name in ('server.py','planner.py','api/plan.py','vercel.json','.env','requirements.txt','data/roads.json'):
            self.assertFalse((OUTPUT/name).exists(), name)
        self.assertFalse(any(p.suffix=='.py' or p.name.startswith('.') for p in OUTPUT.rglob('*')))
        for snapshot in (OUTPUT/'snapshots').iterdir():
            self.assertLess(snapshot.stat().st_size, 4_500_000)


if __name__ == '__main__':
    unittest.main()
