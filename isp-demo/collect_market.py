"""Builds data/market.json from a cached, filtered extract of ANATEL's open SCM
(fixed broadband) access dataset. Real competitive data; independent of the
fictional SerraLink network scenario.

No subscriber, address or individual data: rows are already aggregated by
ANATEL at company/municipality/month level before publication.

Reproduce offline, from isp-demo/, with no network access:

    python3 collect_market.py

To refresh the cache from the public source (requires internet and ~1.1 GB of
disk for the full national ZIP; only the six target municipalities are kept):

    python3 collect_market.py --refresh
"""
import argparse
import csv
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / 'data' / 'anatel-cache'
OUTPUT = ROOT / 'data' / 'market.json'

SOURCE_URL = 'https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_banda_larga_fixa.zip'
DATASET_PAGE = 'https://dados.gov.br/dados/conjuntos-dados/acessos---banda-larga-fixa'
METHODOLOGY_URL = 'https://sistemas.anatel.gov.br/anexar-api/publico/anexos/download/c29c9ceb173725ba2e0d49c0b30cdc0d'

# city_id matches the ids already used by territory.json / simulation.json
# where the city is also part of the fictional network scenario.
CITIES = {
    'Pouso Alegre': {'id': 'pouso-alegre', 'uf': 'MG', 'scope': 'network'},
    'Itajubá': {'id': 'itajuba', 'uf': 'MG', 'scope': 'network'},
    'Santa Rita do Sapucaí': {'id': 'santa-rita', 'uf': 'MG', 'scope': 'network'},
    'Vila Velha': {'id': 'vila-velha', 'uf': 'ES', 'scope': 'benchmark'},
    'Vitória': {'id': 'vitoria', 'uf': 'ES', 'scope': 'benchmark'},
    'Serra': {'id': 'serra', 'uf': 'ES', 'scope': 'benchmark'},
}

CACHE_FILES = [
    ('2025', CACHE_DIR / 'acessos_banda_larga_fixa_2025_recorte.csv'),
    ('2026', CACHE_DIR / 'acessos_banda_larga_fixa_2026_recorte.csv'),
]


def refresh_cache():
    """Downloads the national ZIP and overwrites the six-city CSV cache."""
    print('Baixando dataset nacional da ANATEL (~1,1 GB)…', file=sys.stderr)
    with urllib.request.urlopen(SOURCE_URL, timeout=600) as response:
        raw = response.read()
    digest = hashlib.sha256(raw).hexdigest()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for year, out_path in CACHE_FILES:
            name = f'Acessos_Banda_Larga_Fixa_{year}.csv'
            if name not in archive.namelist():
                continue
            with archive.open(name) as member, out_path.open('w', encoding='utf-8', newline='') as out:
                reader = io.TextIOWrapper(member, encoding='utf-8-sig')
                header = reader.readline()
                out.write(header)
                for line in reader:
                    if any(f';{city};' in line for city in CITIES):
                        out.write(line)
    (CACHE_DIR / 'PROVENANCE.json').write_text(json.dumps({
        'source_url': SOURCE_URL, 'source_sha256': digest,
    }, indent=2) + '\n')
    print(f'Cache atualizado. SHA-256 do ZIP original: {digest}', file=sys.stderr)


def load_rows():
    rows = []
    for year, path in CACHE_FILES:
        if not path.exists():
            raise SystemExit(f'Cache ausente: {path}. Rode com --refresh (exige internet).')
        with path.open(encoding='utf-8-sig') as f:
            for row in csv.DictReader(f, delimiter=';'):
                if row['Município'] in CITIES:
                    rows.append(row)
    return rows


def build(rows):
    by_city = defaultdict(list)
    for row in rows:
        by_city[row['Município']].append(row)

    cities_out = []
    for name, meta in CITIES.items():
        city_rows = by_city.get(name, [])
        if not city_rows:
            continue
        months = sorted({(int(r['Ano']), int(r['Mês'])) for r in city_rows})
        latest = months[-1]

        companies = defaultdict(int)
        for r in city_rows:
            if (int(r['Ano']), int(r['Mês'])) == latest:
                companies[r['Empresa']] += int(r['Acessos'])
        total_latest = sum(companies.values())
        ranking = [
            {'company': name_, 'accesses': acc, 'share': round(acc / total_latest, 4) if total_latest else 0}
            for name_, acc in sorted(companies.items(), key=lambda kv: -kv[1])
        ]

        series = defaultdict(int)
        for r in city_rows:
            key = f"{r['Ano']}-{int(r['Mês']):02d}"
            series[key] += int(r['Acessos'])
        monthly_total = [{'month': k, 'accesses': v} for k, v in sorted(series.items())]

        cities_out.append({
            'id': meta['id'],
            'name': name,
            'uf': meta['uf'],
            'scope': meta['scope'],
            'reference_month': f'{latest[0]}-{latest[1]:02d}',
            'total_accesses': total_latest,
            'distinct_providers': len(companies),
            'ranking': ranking,
            'monthly_total_accesses': monthly_total,
        })

    return {
        'meta': {
            'source': 'ANATEL — Acessos em Serviço do SCM (banda larga fixa)',
            'source_url': SOURCE_URL,
            'dataset_page': DATASET_PAGE,
            'methodology_url': METHODOLOGY_URL,
            'license': 'Creative Commons Attribution',
            'synthetic': False,
            'periodicity': 'Mensal',
            'retrieved_at': '2026-11-02',
            'unit': 'Acessos em serviço declarados pelas prestadoras à ANATEL, por município',
            'limitations': [
                'Autodeclarado pelas prestadoras; nem todas enviam dados todo mês, o que pode subestimar provedores pequenos.',
                'Contagem por acesso em serviço (linha/contrato ativo na prestadora), não é número de domicílios, pessoas ou participação de mercado validada em campo.',
                'Município é o de registro da prestadora para aquele acesso; não há endereço, rua ou coordenada nesta base.',
                'Sem relação com o cadastro fictício de clientes, CTOs ou rede do cenário SerraLink: nenhuma empresa aqui foi convertida em infraestrutura ou cliente simulado.',
                '"Grupo Econômico" agrega marcas de um mesmo grupo; "Empresa" é a razão social individual usada nesta base — os dois recortes podem divergir para grupos com múltiplas prestadoras.',
            ],
        },
        'cities': cities_out,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true', help='Baixa o ZIP nacional novamente e atualiza o cache (exige internet).')
    args = parser.parse_args()
    if args.refresh:
        refresh_cache()
    rows = load_rows()
    OUTPUT.write_text(json.dumps(build(rows), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Gerado {OUTPUT} a partir de {len(rows)} registros em cache.', file=sys.stderr)


if __name__ == '__main__':
    main()
