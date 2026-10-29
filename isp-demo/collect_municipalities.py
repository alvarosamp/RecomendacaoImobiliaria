"""Minas Gerais municipal boundaries from the IBGE mesh API, simplified for the company footprint map.

Uses --input or data/municipality-cache/ when present; --download fetches the official file. The web build never
calls the API.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parent
URL = 'https://servicodados.ibge.gov.br/api/v3/malhas/estados/31?formato=application/vnd.geo%2Bjson&intrarregiao=municipio&qualidade=minima'


def polygons(geometry):
    if geometry['type'] == 'Polygon':
        return [geometry['coordinates']]
    if geometry['type'] == 'MultiPolygon':
        return geometry['coordinates']
    raise ValueError(f"Unexpected geometry {geometry['type']}")


def ring_area_centroid(ring):
    """Signed area and centroid of a lon/lat ring (planar; adequate at municipal scale)."""
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area /= 2
    return area, (cx / (6 * area), cy / (6 * area)) if area else ring[0]


def convert(source, retrieved_at, raw_bytes):
    features = []
    for feature in source['features']:
        code = str(feature['properties']['codarea'])
        rings, weighted, total = [], [0.0, 0.0], 0.0
        for polygon in polygons(feature['geometry']):
            outer = polygon[0]  # Holes are irrelevant at this scale.
            area, (x, y) = ring_area_centroid(outer)
            weighted[0] += x * abs(area); weighted[1] += y * abs(area); total += abs(area)
            rings.append([[round(lat, 4), round(lng, 4)] for lng, lat in outer])
        features.append({'code': code, 'centroid': [round(weighted[1] / total, 4), round(weighted[0] / total, 4)], 'rings': rings})
    features.sort(key=lambda f: f['code'])
    return {
        'meta': {'source': 'IBGE · Malhas territoriais (API v3), qualidade mínima', 'url': URL, 'retrieved_at': retrieved_at, 'synthetic': False,
                 'source_sha256': hashlib.sha256(raw_bytes).hexdigest(), 'coordinates': '[lat, lng], 4 casas decimais',
                 'limitations': ['Contornos simplificados para visualização; não servem para medir área ou definir limites legais.', 'Centroide planar do maior conjunto de polígonos; pode cair fora de municípios muito irregulares.']},
        'features': features,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=REPO / 'data/municipality-cache/mg-minima.json')
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--retrieved-at', default='2026-10-28')
    parser.add_argument('--output', type=Path, default=REPO / 'data/mg-municipalities.json')
    args = parser.parse_args()
    if not args.input.exists():
        if not args.download:
            raise FileNotFoundError(f'{args.input}: use --download or --input with the IBGE file.')
        args.input.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(Request(URL, headers={'User-Agent': 'UrbiaISP public-data collection'}), timeout=120) as response:
            args.input.write_bytes(response.read())
    raw = args.input.read_bytes()
    result = convert(json.loads(raw), args.retrieved_at, raw)
    if len(result['features']) != 853:
        raise ValueError(f"Expected 853 municipalities in Minas Gerais, got {len(result['features'])}")
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(len(result['features']), 'municípios', 'bytes', args.output.stat().st_size)


if __name__ == '__main__':
    main()
