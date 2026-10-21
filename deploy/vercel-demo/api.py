"""Public synthetic calculator: no database, credentials, accounts or shared state."""
from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime, timezone
from demo_engine.case_demos import demo_inputs, demo_context
from demo_engine.decision_cases import evaluate_case
from demo_engine.case_reports import presentation_tables, render_case_markdown, render_case_html
from demo_engine.financial_study import evaluate_financial
from demo_engine.technical_study import evaluate_technical
from demo_engine.business_study import evaluate_business
from demo_engine.concept import ConceptInput, analyze_concept, _simple_pdf
import base64


def calculate(data):
    action = data.get('action')
    if action == 'case':
        case = data['value']
        kind = case['kind']
        context = demo_context(kind)
        result = evaluate_case(kind, case['inputs'], city_ibge=case.get('city_ibge', '3152501'),
                               demonstration=True, **context)
        result.update(captured_at=datetime.now(timezone.utc).isoformat(), city_ibge=case.get('city_ibge', '3152501'),
                      municipality_name='Pouso Alegre', sources=[], tables=presentation_tables(kind, result))
        return result
    if action == 'concept':
        return analyze_concept(ConceptInput.model_validate(data['value']))
    if action == 'concept_report':
        concept = analyze_concept(ConceptInput.model_validate(data['value']))
        lines = ['Urbia - Demonstracao publica', 'Dados ficticios. Nao utilizar para decisoes.', '']
        for scenario in concept['scenarios']:
            lines.append(str(scenario))
        return {'pdf': base64.b64encode(_simple_pdf(lines)).decode()}
    if action == 'project':
        project = data['value']
        premises = project.get('premises') or {}
        legal = dict(status='analisar', notes='Demonstração: zoneamento e restrições do lote não foram consultados.',
                     spatial_overlays_verified=False, articles=[], sources=[])
        return dict(mode='premises_only', captured_at=datetime.now(timezone.utc).isoformat(), legal=legal,
                    concept=analyze_concept(ConceptInput.model_validate(premises)),
                    financial=evaluate_financial(project['financial'], premises.get('buildArea', 165)) if project.get('financial') else None,
                    technical=evaluate_technical(project['technical'], {}, legal) if project.get('technical') is not None else None,
                    business=evaluate_business(project['business'], {}, legal) if project.get('business') is not None else None)
    if action == 'report':
        return (render_case_html if data.get('format') == 'html' else render_case_markdown)(data['value'])
    raise ValueError('Operação demonstrativa desconhecida')


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status":"ok","mode":"synthetic-demo"}')

    def do_POST(self):
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 250_000:
                raise ValueError('Solicitação demonstrativa muito grande ou vazia')
            result = calculate(json.loads(self.rfile.read(size)))
            status, body = 200, result
        except (ValueError, KeyError, TypeError) as exc:
            status, body = 422, {'detail': str(exc)[:1200]}
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False, allow_nan=False).encode())
