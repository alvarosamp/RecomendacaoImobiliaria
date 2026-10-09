"""Run inside the isolated API container through the real nginx proxy."""
import json
import secrets
import requests
from sqlalchemy import text
from recomendacao_imobiliaria.config import load_settings
from recomendacao_imobiliaria.db import make_engine

base = 'http://frontend'
headers = {'Host': '127.0.0.1:18087', 'Origin': 'http://127.0.0.1:18087'}
checks = []

def check(method, path, expected=200, **kwargs):
    response = requests.request(method, base + path, headers=kwargs.pop('headers', headers), timeout=60, **kwargs)
    assert response.status_code == expected, (path, response.status_code, response.text[:500])
    checks.append({'path': path, 'status': response.status_code})
    return response

check('GET', '/')
check('GET', '/register')
check('GET', '/app')
check('GET', '/api/scores')
account = {'name': 'Deployment Test', 'email': secrets.token_hex(8) + '@example.invalid', 'password': secrets.token_hex(20), 'profile': 'corretor'}
check('POST', '/api/auth/register', json=account)
token = check('POST', '/api/auth/login', json=account).json()['access_token']
authorized = {**headers, 'Authorization': 'Bearer ' + token}
check('GET', '/api/auth/me', headers=authorized)
check('GET', '/api/auth/me', expected=401)
check('POST', '/api/auth/login', expected=401, json={**account, 'password': 'wrong'})
check('POST', '/api/auth/login', expected=403, json=account, headers={**headers, 'Origin': 'https://foreign.example'})
lead = check('POST', '/api/leads', headers=authorized, json={'name': 'Synthetic lead', 'budget': 500000, 'financing_status': 'aprovado', 'timeline': 'imediato'}).json()
assert lead['score'] >= 70
assert len(check('GET', '/api/leads', headers=authorized).json()) == 1
check('PATCH', f"/api/leads/{lead['id']}/status", headers=authorized, json={'status': 'contatado'})
second = {**account, 'email': secrets.token_hex(8) + '@example.invalid'}
check('POST', '/api/auth/register', json=second)
second_token = check('POST', '/api/auth/login', json=second).json()['access_token']
assert check('GET', '/api/leads', headers={**headers, 'Authorization': 'Bearer ' + second_token}).json() == []
check('POST', '/api/predict', json={'area_m2': 100, 'bedrooms': 2})
check('POST', '/api/concept/analyze', json={})
pdf = check('POST', '/api/concept/report', json={})
assert pdf.content.startswith(b'%PDF')
check('GET', '/api/legal/assess?zone=ZM&intended_use=residencial')
check('GET', '/api/legal/annexes')
check('GET', '/api/indices/timeseries')
check('GET', '/api/pipeline/status')
check('GET', '/api/mlops/runs')
check('GET', '/api/market/compare?neighborhood=Centro&asking_price=400000&area_m2=100', expected=503)
check('GET', '/api/analytics/zoning-geojson')
check('GET', '/api/analytics/pois-geojson')
engine = make_engine(load_settings())
with engine.connect() as conn:
    assert conn.execute(text('SELECT postgis_version()')).scalar()
    assert conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='geo'")).scalar() >= 10
for endpoint in ['http://mlflow:5000/health', 'http://minio:9000/minio/health/live']:
    assert requests.get(endpoint, timeout=30).status_code == 200
assert 'Set-Cookie' not in check('GET', '/api/auth/me', headers=authorized).headers
print(json.dumps({'passed': len(checks), 'checks': checks}, indent=2))
