"""Aggregate Anatel fixed-broadband accesses per provider for the three study municipalities.

Reads the official open-data archive (about 1 GB) from --zip or from data/market-cache/. The web build never
downloads it. Only company-level aggregates are kept: no subscriber, address or individual data exists in the source.
"""
import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import defaultdict
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parent
URL = 'https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_banda_larga_fixa.zip'
CITIES = [('pouso-alegre', '3152501', 'Pouso Alegre'), ('santa-rita', '3159605', 'Santa Rita do Sapucaí'), ('itajuba', '3132404', 'Itajubá')]
YEARS = (2024, 2025, 2026)
SERIES_MONTHS = 13


def download(path):
    partial = path.with_suffix('.partial')
    with urlopen(Request(URL, headers={'User-Agent': 'UrbiaISP public-data collection'}), timeout=120) as response, partial.open('wb') as out:
        modified = response.headers.get('Last-Modified')
        while chunk := response.read(1024 * 1024):
            out.write(chunk)
    partial.replace(path)
    return modified


def read_csv(archive, name):
    raw = archive.read(name)
    # Recent files are Latin-1; accept UTF-8 should Anatel change the encoding.
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('latin-1')
    return csv.DictReader(io.StringIO(text), delimiter=';')


def collect(zip_path, retrieved_at, last_modified=None):
    codes = {code: (cid, name) for cid, code, name in CITIES}
    accesses = defaultdict(int)  # (code, month, cnpj) -> accesses
    detail = defaultdict(int)    # (code, month, field, value) -> accesses
    names = {}                   # (code, cnpj) -> (month, empresa, grupo, porte); latest month wins
    with zipfile.ZipFile(zip_path) as archive:
        for year in YEARS:
            for row in read_csv(archive, f'Acessos_Banda_Larga_Fixa_{year}.csv'):
                code = row['Código IBGE Município']
                if code not in codes:
                    continue
                month, cnpj, value = f"{int(row['Ano']):04d}-{int(row['Mês']):02d}", row['CNPJ'].strip(), int(row['Acessos'] or 0)
                accesses[code, month, cnpj] += value
                detail[code, month, 'tecnologia', row['Tecnologia'].strip()] += value
                detail[code, month, 'pessoa', row['Tipo de Pessoa'].strip()] += value
                if names.get((code, cnpj), ('',))[0] <= month:
                    names[code, cnpj] = (month, row['Empresa'].strip(), row['Grupo Econômico'].strip(), row['Porte da Prestadora'].strip())
    months = sorted({k[1] for k in accesses})
    last, recent = months[-1], months[-SERIES_MONTHS:]
    year_before = f'{int(last[:4]) - 1}-{last[5:]}'
    cities = []
    for cid, code, name in CITIES:
        totals = {m: sum(v for (c, mm, _), v in accesses.items() if c == code and mm == m) for m in months}
        total = totals[last]
        providers = []
        for cnpj in sorted({k[2] for k in accesses if k[0] == code}):
            series = {m: accesses.get((code, m, cnpj), 0) for m in recent}
            if not series[last]:
                continue  # Not present in the reference month.
            _, empresa, grupo, porte = names[code, cnpj]
            before = accesses.get((code, year_before, cnpj), 0)
            providers.append({'cnpj': cnpj, 'empresa': empresa, 'grupo': grupo, 'porte': porte, 'acessos': series[last], 'share_pct': round(series[last] / total * 100, 2), 'acessos_12m_antes': before, 'variacao_12m': series[last] - before, 'series': [series[m] for m in recent]})
        providers.sort(key=lambda p: (-p['acessos'], p['cnpj']))
        # CNPJs that declared in the last 6 months but not in the reference month: usually a missing declaration,
        # sometimes an exit or a CNPJ change. Listed apart so a drop in the total is not read as lost customers.
        window = months[-7:-1]
        absent = []
        for cnpj in sorted({k[2] for k in accesses if k[0] == code}):
            if accesses.get((code, last, cnpj), 0):
                continue
            seen = [(m, accesses.get((code, m, cnpj), 0)) for m in window if accesses.get((code, m, cnpj), 0) >= 50]
            if seen:
                _, empresa, grupo, porte = names[code, cnpj]
                absent.append({'cnpj': cnpj, 'empresa': empresa, 'grupo': grupo, 'porte': porte, 'ultimo_mes': seen[-1][0], 'ultimos_acessos': seen[-1][1]})
        absent.sort(key=lambda p: (-p['ultimos_acessos'], p['cnpj']))
        groups = defaultdict(int)
        for p in providers:
            groups[p['grupo'] if p['grupo'] != 'OUTROS' else p['cnpj']] += p['acessos']
        hhi = round(sum((v / total * 100) ** 2 for v in groups.values()))
        pick = lambda field: dict(sorted(((k[3], v) for k, v in detail.items() if k[0] == code and k[1] == last and k[2] == field), key=lambda x: -x[1]))
        cities.append({'id': cid, 'ibge_code': code, 'name': name, 'total': total, 'total_12m_antes': totals.get(year_before, 0), 'providers_count': len(providers), 'hhi_grupos': hhi, 'tecnologia': pick('tecnologia'), 'tipo_pessoa': pick('pessoa'), 'series': [{'month': m, 'total': totals[m]} for m in months], 'providers': providers, 'absent_in_reference': absent})
    return {
        'meta': {
            'source': 'Anatel · Acessos de banda larga fixa (dados abertos)', 'synthetic': False, 'url': URL,
            'panel_url': 'https://www.gov.br/anatel/pt-br/dados/dados-abertos', 'source_last_modified': last_modified,
            'source_sha256': hashlib.sha256(Path(zip_path).read_bytes()).hexdigest(), 'retrieved_at': retrieved_at,
            'files': [f'Acessos_Banda_Larga_Fixa_{y}.csv' for y in YEARS], 'reference_month': last, 'comparison_month': year_before, 'series_months': recent,
            'limitations': [
                'Acessos declarados pelas prestadoras à Anatel por município e mês; não são domicílios, pessoas, cobertura ou disponibilidade por rua.',
                'Inclui pessoa física e jurídica e todas as tecnologias (FTTH, rádio, satélite, cabo).',
                'Cada linha é um CNPJ. Variação em 12 meses por CNPJ pode refletir troca de CNPJ, incorporação ou ajuste de declaração, e não apenas ganho ou perda de clientes.',
                'Concentração (HHI) agrupa por grupo econômico; prestadoras do grupo "OUTROS" são contadas por CNPJ.',
                'A Anatel pode revisar meses anteriores; o snapshot reflete o arquivo na data de coleta.',
                'Meses com queda brusca e recuperação em seguida, e prestadoras que deixam de aparecer, costumam indicar declaração ausente ou atrasada. Prestadoras com ao menos 50 acessos nos 6 meses anteriores e sem declaração no mês de referência são listadas à parte.',
            ],
        },
        'cities': cities,
    }


SPEED_EDGES = (100, 300, 500, 700, 1000)
SPEED_LABELS = ['< 100 Mbps', '100–299 Mbps', '300–499 Mbps', '500–699 Mbps', '700–999 Mbps', '≥ 1 Gbps']


def company_key(row):
    """Economic group for national groups; CNPJ root (same company, any branch) for independents."""
    group = row['Grupo Econômico'].strip()
    return group if group and group != 'OUTROS' else 'CNPJ-' + row['CNPJ'].strip()[:8]


def speed_bucket(value):
    try:
        mbps = float(value.replace(',', '.'))
    except ValueError:
        return None
    return sum(mbps >= edge for edge in SPEED_EDGES)


def collect_companies(zip_path, market):
    """Footprint in every Minas Gerais municipality for each company present in the three study cities."""
    study = {c['ibge_code'] for c in market['cities']}
    months = market['meta']['series_months']
    last, index = months[-1], {m: i for i, m in enumerate(months)}
    accesses = defaultdict(int)       # (municipality, month, company) -> accesses
    city_names, names, cnpjs = {}, defaultdict(lambda: defaultdict(int)), defaultdict(set)
    porte = {}
    speed = defaultdict(lambda: [0] * len(SPEED_LABELS))  # (company or '*', municipality or 'MG') -> buckets
    mix = defaultdict(lambda: defaultdict(int))           # (company, field) -> value -> accesses
    with zipfile.ZipFile(zip_path) as archive:
        for year in sorted({int(m[:4]) for m in months}):
            for row in read_csv(archive, f'Acessos_Banda_Larga_Fixa_{year}.csv'):
                if row['UF'] != 'MG':
                    continue
                month = f"{int(row['Ano']):04d}-{int(row['Mês']):02d}"
                if month not in index:
                    continue
                code, key, value = row['Código IBGE Município'], company_key(row), int(row['Acessos'] or 0)
                accesses[code, month, key] += value
                city_names[code] = row['Município'].strip()
                if month == last:
                    names[key][row['Empresa'].strip()] += value
                    cnpjs[key].add(row['CNPJ'].strip())
                    porte[key] = row['Porte da Prestadora'].strip()
                    bucket = speed_bucket(row['Velocidade'])
                    if bucket is not None:
                        for target in ((key, 'MG'), (key, code), ('*', 'MG'), ('*', code)):
                            speed[target][bucket] += value
                    mix[key, 'tecnologia'][row['Tecnologia'].strip()] += value
                    mix[key, 'pessoa'][row['Tipo de Pessoa'].strip()] += value
    tracked = sorted({k for (code, month, k) in accesses if code in study and month == last})
    totals = defaultdict(lambda: [0] * len(months))
    for (code, month, _), value in accesses.items():
        totals[code][index[month]] += value
    footprints = defaultdict(dict)
    for (code, month, key), value in accesses.items():
        if key in tracked:
            footprints[key].setdefault(code, [0] * len(months))[index[month]] += value
    used = set()
    companies = []
    for key in tracked:
        rows = sorted(([code] + series for code, series in footprints[key].items() if any(series)), key=lambda r: -r[-1])
        used.update(r[0] for r in rows)
        companies.append({
            'id': key, 'name': max(names[key].items(), key=lambda x: x[1])[0], 'grupo': key if not key.startswith('CNPJ-') else 'OUTROS',
            'porte': porte.get(key, ''), 'cnpjs': sorted(cnpjs[key]), 'footprint': rows,
            'speed': {code: speed[key, code] for code in ['MG', *sorted(study)] if any(speed[key, code])},
            'tecnologia': dict(sorted(mix[key, 'tecnologia'].items(), key=lambda x: -x[1])), 'pessoa': dict(mix[key, 'pessoa']),
        })
    companies.sort(key=lambda c: -sum(r[-1] for r in c['footprint'] if r[0] in study))
    return {
        'meta': {**{k: market['meta'][k] for k in ('source', 'synthetic', 'url', 'panel_url', 'source_last_modified', 'source_sha256', 'retrieved_at', 'reference_month', 'comparison_month', 'series_months')},
                 'scope': 'Minas Gerais', 'study_municipalities': sorted(study), 'speed_labels': SPEED_LABELS,
                 'company_key': 'Grupo econômico declarado; prestadoras do grupo "OUTROS" agrupadas pela raiz do CNPJ (8 dígitos).',
                 'footprint_row': 'código IBGE, acessos nos meses de series_months',
                 'limitations': market['meta']['limitations'] + ['Velocidade é a contratada declarada, não a medida. Faixas de velocidade da Anatel foram descartadas: mais de 95% dos acessos estão em "> 34 Mbps".',
                                                                 'Participação = acessos da empresa ÷ acessos de todas as prestadoras no município e mês; meses com declarações ausentes de terceiros inflam a participação.']},
        'municipalities': {code: {'name': city_names[code], 'total': totals[code]} for code in sorted(used)},
        'market_speed': {code: speed['*', code] for code in ['MG', *sorted(study)]},
        'companies': companies,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, default=REPO / 'data/market-cache/acessos_banda_larga_fixa.zip')
    parser.add_argument('--download', action='store_true', help='Download the official archive (about 1 GB) when missing.')
    parser.add_argument('--retrieved-at', default='2026-10-28')
    parser.add_argument('--last-modified', default='Thu, 08 Oct 2026 10:32:37 GMT', help='Last-Modified header of the collected archive.')
    parser.add_argument('--output', type=Path, default=REPO / 'data/market.json')
    parser.add_argument('--companies-output', type=Path, default=REPO / 'data/market-companies.json')
    args = parser.parse_args()
    modified = args.last_modified
    if not args.zip.exists():
        if not args.download:
            raise FileNotFoundError(f'{args.zip}: use --download or --zip with the official archive.')
        args.zip.parent.mkdir(parents=True, exist_ok=True)
        modified = download(args.zip)
    result = collect(args.zip, args.retrieved_at, parsedate_to_datetime(modified).date().isoformat() if modified else None)
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    for c in result['cities']:
        print(c['id'], c['total'], 'acessos', c['providers_count'], 'prestadoras', 'HHI', c['hhi_grupos'], c['providers'][0]['empresa'])
    print('bytes', args.output.stat().st_size)
    companies = collect_companies(args.zip, result)
    args.companies_output.write_text(json.dumps(companies, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(len(companies['companies']), 'empresas', len(companies['municipalities']), 'municípios de MG', 'bytes', args.companies_output.stat().st_size)


if __name__ == '__main__':
    main()
