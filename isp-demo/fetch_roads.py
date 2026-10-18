"""Fetch public OpenStreetMap road geometry; never subscriber information."""
import json
import pathlib
import urllib.request
import urllib.parse
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent
CITIES = [
    {"id": "pouso-alegre", "name": "Pouso Alegre", "ibge": "3152501", "center": [-22.2300, -45.9360], "bbox": [-22.255, -45.961, -22.207, -45.909], "ctos": 36},
    {"id": "santa-rita", "name": "Santa Rita do Sapucaí", "ibge": "3159605", "center": [-22.2525, -45.7030], "bbox": [-22.269, -45.722, -22.239, -45.685], "ctos": 20},
    {"id": "itajuba", "name": "Itajubá", "ibge": "3132404", "center": [-22.4250, -45.4530], "bbox": [-22.444, -45.475, -22.407, -45.434], "ctos": 24},
]

for city in CITIES:
    query = '[out:json][timeout:90];way["highway"~"^(residential|tertiary|secondary|primary|unclassified|living_street)$"](%s);out geom;' % ','.join(map(str, city['bbox']))
    body = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request('https://overpass-api.de/api/interpreter', data=body, headers={"User-Agent": "UrbiaISP-local-demo/0.1 (public road geometry research)"})
    with urllib.request.urlopen(req, timeout=120) as response:
        raw = json.load(response)
    roads = [{"osm_way_id": w['id'], "name": w.get('tags', {}).get('name', 'Via sem nome no OSM'), "type": w['tags']['highway'], "points": [[p['lat'], p['lon']] for p in w['geometry']]} for w in raw['elements'] if len(w.get('geometry', [])) > 1]
    city['roads'] = roads
    print(city['name'], len(roads), 'vias públicas')

output = {"source": "OpenStreetMap contributors / Overpass API", "license": "ODbL-1.0", "retrieved_at": datetime.now(timezone.utc).isoformat(), "url": "https://www.openstreetmap.org/copyright", "cities": CITIES}
(ROOT / 'data' / 'roads.json').write_text(json.dumps(output, ensure_ascii=False), encoding='utf-8')
