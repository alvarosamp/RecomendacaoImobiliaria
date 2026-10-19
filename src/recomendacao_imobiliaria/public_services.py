"""Exploratory service-access triage, independent from real-estate scores."""
import math
from datetime import datetime, timezone

SERVICES = {
    "schools": {"label": "Escolas e creches", "count": "poi_school_cnt", "distance": "dist_min_school_m"},
    "hospitals": {"label": "Hospitais e atendimento hospitalar", "count": "poi_hospital_cnt", "distance": "dist_min_hospital_m"},
}
LIMITATIONS = [
    "Estabelecimentos mapeados podem incluir unidades públicas e privadas; a oferta pública não está isolada.",
    "Capacidade, vagas, demanda por faixa etária e cobertura efetiva não estão disponíveis. Este diagnóstico não mede déficit de vagas.",
    "Distâncias vêm das features territoriais existentes; não representam tempo de viagem nem rotas acessíveis.",
    "População por H3 pode ser estimada; a data de processamento não equivale à data de referência do levantamento.",
    "O ranking orienta investigação. Implantação de equipamentos requer estudo de terreno, risco, zoneamento e validação técnica.",
]


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError):
        return None


def build_diagnosis(records, service, target_distance_m, sources=None):
    cfg = SERVICES[service]
    rows = []
    for record in records:
        count, distance = number(record.get(cfg['count'])), number(record.get(cfg['distance']))
        census = number(record.get('population_2022'))
        population = census if census is not None else number(record.get('pop_estimated'))
        gaps = []
        if population is None: gaps.append('população')
        if count is None: gaps.append('contagem de estabelecimentos')
        if distance is None: gaps.append('distância')
        absence = None if count is None else (40.0 if count == 0 else 0.0)
        access = None if distance is None else 60 * min(distance / target_distance_m, 1)
        score = None if gaps or population == 0 else round(absence + access, 1)
        priority = 'dados_pendentes' if gaps else 'sem_populacao' if population == 0 else 'alta' if score >= 70 else 'media' if score >= 40 else 'baixa'
        rows.append({
            'h3_id': record['h3_id'], 'neighborhood': record.get('neighborhood'), 'population': population,
            'population_basis': 'census_h3' if census is not None else 'estimate' if population is not None else 'missing',
            'population_source': record.get('population_source') if census is not None else 'Estimativa territorial sem referência censitária individual',
            'population_processed_at': record.get('population_processed_at'),
            'count': count, 'distance_m': distance, 'priority': priority, 'investigation_score': score,
            'contributions': {'absence': absence, 'access': round(access, 1) if access is not None else None},
            'missing': gaps, 'risk_level': record.get('risk_level'),
            'reason': 'Dados insuficientes: ' + ', '.join(gaps) if gaps else 'População informada igual a zero; fora do ranking.' if population == 0 else f"{int(count)} estabelecimentos no recorte; menor distância {distance:.0f} m. Capacidade não verificada.",
        })
    rows.sort(key=lambda row: (row['investigation_score'] is None, -(row['investigation_score'] or 0), -(row['population'] or 0), row['h3_id']))
    rank = 0
    for row in rows:
        if row['investigation_score'] is not None:
            rank += 1
            row['rank'] = rank
        else:
            row['rank'] = None
    result = {'service': service, 'service_label': cfg['label'], 'captured_at': datetime.now(timezone.utc).isoformat(),
              'target_distance_m': target_distance_m, 'methodology': 'triagem_acesso_v1',
              'formula': '60 × min(distância / referência, 1) + 40 × indicador(contagem = 0). População desempata; dados completos e população > 0 são necessários para ranquear.',
              'summary': {'areas': len(rows), 'ranked': rank, 'high_priority': sum(row['priority'] == 'alta' for row in rows), 'pending': sum(bool(row['missing']) for row in rows)},
              'limitations': LIMITATIONS, 'sources': sources or [], 'rows': rows}
    result['report_markdown'] = report(result)
    return result


def report(data):
    lines = ['# Diagnóstico exploratório de acesso a equipamentos — Urbia Governo', '', data['service_label'],
             f"Captura: {data['captured_at']}", f"Referência de distância escolhida pelo usuário: {data['target_distance_m']} m (não é norma urbanística)",
             '', '## Metodologia', data['methodology'], data['formula'], '', '## Regiões']
    for row in data['rows']:
        lines += [f"- {row['h3_id']} · {row.get('neighborhood') or 'bairro não informado'} · posição {row['rank'] or 'não ranqueada'} · prioridade {row['priority']} · score {row['investigation_score'] if row['investigation_score'] is not None else 'indisponível'}", f"  População: {row['population']} ({row['population_basis']}); {row['reason']}"]
    lines += ['', '## Fontes registradas']
    if not data['sources']: lines += ['Proveniência de equipamentos não registrada; confirmar origem e atualização antes de interpretar ausência como falta de oferta.']
    for source in data['sources']:
        lines += [f"- {source.get('dataset')}: {source.get('source_name')} · referência {source.get('reference_date') or 'não informada'} · coleta {source.get('collected_at') or 'não informada'} · {source.get('source_uri') or 'sem endereço registrado'}"]
    lines += ['', '## Limitações'] + ['- ' + item for item in data['limitations']]
    lines += ['', '## Registro da captura', '```json']
    import json
    lines += [json.dumps({key: value for key, value in data.items() if key != 'report_markdown'}, ensure_ascii=False, indent=2), '```']
    return '\n'.join(lines)
