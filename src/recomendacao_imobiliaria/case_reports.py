"""Shared presentation tables and script-free printable executive reports."""
from html import escape
import json
from .decision_cases import money

STATUS = {'unknown':'Não informado', 'provided':'Referência informada', 'reported_available':'Disponível segundo declaração',
          'reported_unavailable':'Indisponível segundo declaração', 'favoravel':'Favorável segundo visita',
          'desfavoravel':'Desfavorável segundo visita', 'pending':'Pendente', 'in_progress':'Em andamento', 'done':'Concluída'}
LABELS = dict(proposals='Proposta',name='Nome',product='Produto',build_area_m2='Área construída (m²)',financial='Premissas financeiras',
    land_cost='Terreno (R$)',construction_cost_m2='Construção por m² (R$)',other_costs='Outros custos (R$)',contingency_pct='Contingência (%)',
    saleable_area_m2='Área vendável (m²)',sale_price_m2='Venda por m² (R$)',sales_expenses_pct='Despesas sobre venda (%)',months='Prazo (meses)',
    annual_discount_pct='Desconto anual (%)',cost_variation_pct='Variação do custo (%)',price_variation_pct='Variação do preço (%)',
    source_note='Origem declarada',reference_date='Data de referência',investigation_note='Observações da investigação',budget='Orçamento (R$)',
    variation_pct='Variação da venda (%)',properties='Imóvel',acquisition='Aquisição (R$)',improvements='Melhorias (R$)',sale_price='Revenda (R$)',
    address='Identificação/endereço',property_type='Tipo de imóvel',transaction='Finalidade',area_m2='Área (m²)',asking_price='Preço pedido (R$)',
    positives='Pontos favoráveis',objections='Objeções',owner_questions='Perguntas ao proprietário',area_tolerance_pct='Diferença máxima de área (%)',
    maximum_age_days='Idade máxima da referência (dias)',comparables='Comparável',city_ibge='Município (IBGE)',price='Preço anunciado (R$)',
    differences='Diferenças observadas',provenance='Natureza da informação',selected='Selecionado',criteria='Critérios comerciais',sector='Setor',
    minimum_population='População mínima',distance_reference_m='Referência de distância (m)',criteria_note='Justificativa dos critérios',points='Ponto',
    h3_id='Identificador técnico do recorte',rent='Aluguel (R$)',other_monthly_costs='Outros custos mensais (R$)',visibility='Visibilidade',access='Acesso',
    observed_competitors='Concorrentes observados',visit_note='Observações da visita',target_distance_m='Distância de investigação (m)',regions='Região',justification='Justificativa')


def evidence_rows(inputs, prefix=''):
    rows = []
    for key, item in inputs.items():
        label = (prefix+' · ' if prefix else '') + LABELS.get(key, key)
        if isinstance(item, dict): rows.extend(evidence_rows(item, label))
        elif isinstance(item, list):
            for index, child in enumerate(item): rows.extend(evidence_rows(child, label+' '+str(index+1)))
        else:
            display = 'Sim' if item is True else 'Não' if item is False else {'user':'Informado pelo usuário','simulation':'Simulação','pharmacy':'Farmácia','market':'Mercado'}.get(str(item),value(item))
            rows.append([label, display])
    return rows


def value(item):
    return 'Não informado' if item is None else STATUS.get(str(item), str(item))


def amount(item):
    return 'Pendente' if item is None else money(item)


def table(title, columns, rows):
    return dict(title=title, columns=columns, rows=rows)


def presentation_tables(kind, result):
    d = result['details']
    tables = []
    if kind == 'incorpora':
        rows, scenarios = [], []
        for p in d['proposals']:
            f = p['financial']; base = (f.get('scenarios') or [{}])[0]
            rows.append([p['name'], p['product'], value(p['build_area_m2']), amount(base.get('total_cost')), amount(base.get('profit')), amount(base.get('npv'))])
            for s in f.get('scenarios', []): scenarios.append([p['name'], s['label'], amount(s['total_cost']), amount(s['net_revenue']), amount(s['profit'])])
        tables += [table('Propostas declaradas', ['Proposta', 'Produto', 'Área construída (m²)', 'Custo total', 'Resultado base', 'Valor presente líquido'], rows),
                   table('Sensibilidade das propostas', ['Proposta', 'Cenário', 'Custo', 'Receita líquida', 'Resultado'], scenarios)]
    elif kind == 'obras':
        tables.append(table('Evidências do terreno', ['Verificação', 'Situação'], [[x['label'], value(x['status'])] for x in d['technical'].get('checks', [])]))
    elif kind == 'invest':
        rows = []
        for p in d['properties']:
            if p['missing']: rows.append([p['name'], 'Dados pendentes', 'Pendente', 'Pendente', 'Pendente', 'Pendente'])
            else:
                for s in p['scenarios']: rows.append([p['name'], s['label'], amount(p['capital']), amount(s['profit']), str(s['roi_pct'])+'%' if s['roi_pct'] is not None else 'Não calculável', 'Sim' if p['within_budget'] else 'Não' if p['within_budget'] is False else 'Orçamento pendente'])
        tables.append(table('Compra e revenda — ROI do empreendimento, sem anualização', ['Imóvel', 'Cenário', 'Capital inicial', 'Resultado', 'ROI', 'Cabe no orçamento?'], rows))
    elif kind == 'mercado':
        p = d['property']
        tables += [table('Imóvel apresentado', ['Identificação', 'Área (m²)', 'Preço pedido', 'Referência por m²', 'Diferença em relação à mediana'], [[p['address'], value(p['area_m2']), amount(p['asking_price']), amount(d.get('reference_price_m2')), value(d.get('deviation_pct'))+'%' if d.get('deviation_pct') is not None else 'Pendente']]),
                   table('Comparáveis selecionados — anúncios, não transações comprovadas', ['Imóvel', 'Área (m²)', 'Preço', 'Preço/m²', 'Origem declarada', 'Referência', 'Diferenças observadas'], [[x['name'], value(x['area_m2']), amount(x['price']), amount(x['price_m2']), x['source_note'], value(x['reference_date']), x['differences']] for x in d['comparables']]),
                   table('Referências excluídas', ['Referência', 'Motivo'], [[x['name'], '; '.join(x['reasons'])] for x in d['excluded']]),
                   table('Argumentos e perguntas', ['Pontos favoráveis declarados', 'Objeções a investigar', 'Perguntas ao proprietário'], [[p['positives'], p['objections'], p['owner_questions']]])]
    elif kind == 'negocios':
        tables.append(table('Pontos para visita — sem previsão de faturamento', ['Ponto', 'Custo mensal', 'Área (m²)', 'Visibilidade', 'Acesso', 'Concorrentes observados', 'População estimada no recorte', 'Serviços mapeados', 'Distância ao serviço (m)'],
            [[p['name'], amount(p['monthly_cost']), value(p['visit']['area_m2']), value(p['visit']['visibility']), value(p['visit']['access']), value(p['visit']['observed_competitors']), value(p['commercial']['population_estimate']), value(p['commercial']['mapped_establishments']), value(p['commercial']['nearest_distance_m'])] for p in d['points']]))
    else:
        tables.append(table('Regiões escolhidas para investigação escolar', ['Recorte', 'Justificativa', 'População', 'Estabelecimentos mapeados', 'Distância (m)', 'Explicação territorial'],
            [[p['name'] or 'Recorte selecionado', p['justification'], value((p['evidence'] or {}).get('population')), value((p['evidence'] or {}).get('count')), value((p['evidence'] or {}).get('distance_m')), (p['evidence'] or {}).get('reason', 'Indicadores pendentes')] for p in d['regions']]))
    return tables


def render_case_markdown(case):
    r, s = case['result'], case['result']['summary']
    lines = ['# '+r['title'], case['title'], f"Revisão: {case['revision']} · captura: {r['captured_at']} · município: {r['municipality_name']}",
             'SIMULAÇÃO DEMONSTRATIVA — valores e observações fictícios.' if case['demonstration'] else 'Informações declaradas e fontes disponíveis; consultar proveniência.',
             '', '## Síntese', s['conclusion'], '## Motivos']
    for reason in s['reasons']: lines += ['- '+reason['found'], '  '+reason['why'], '  Verificar: '+reason['verify']]
    lines += ['## Pendências decisivas'] + ['- '+x for x in s['gaps']]
    for t in r['tables']:
        lines += ['', '## '+t['title'], ' | '.join(t['columns'])]
        lines += [' | '.join(str(x) for x in row) for row in t['rows']]
    lines += ['## Próximas ações'] + [f"- {x['title']} · responsável: {x['assignee'] or 'a definir'} · prazo: {x['due_date'] or 'a definir'} · {value(x['status'])} · evidência: {x['evidence'] or 'pendente'}" for x in case['tasks']]
    lines += ['## Limitações'] + r['limitations'] + ['## Premissas e fontes', '```json', json.dumps(dict(inputs=case['inputs'], sources=r['sources'], result=r), ensure_ascii=False, indent=2), '```']
    return '\n'.join(lines)


def render_case_html(case):
    e = lambda text: escape(str(text), quote=True)
    r, s = case['result'], case['result']['summary']
    badge = 'SIMULAÇÃO DEMONSTRATIVA · valores e observações fictícios' if case['demonstration'] else 'Análise de premissas declaradas e fontes disponíveis'
    reasons = ''.join(f"<article><h3>{e(x['found'])}</h3><p>{e(x['why'])}</p><p><strong>O que verificar:</strong> {e(x['verify'])}</p></article>" for x in s['reasons'])
    gaps = ''.join('<li>'+e(x)+'</li>' for x in s['gaps']) or '<li>Sem campos pendentes no modelo declarado; a revisão profissional continua necessária.</li>'
    tables = ''.join('<section><h2>'+e(t['title'])+'</h2><table><thead><tr>'+''.join('<th>'+e(x)+'</th>' for x in t['columns'])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+e(x)+'</td>' for x in row)+'</tr>' for row in t['rows'])+'</tbody></table></section>' for t in r['tables'])
    tasks = ''.join(f"<li><strong>{e(x['title'])}</strong> · {e(value(x['status']))}<br>Responsável: {e(x['assignee'] or 'a definir')} · prazo: {e(x['due_date'] or 'a definir')}<br>Evidência: {e(x['evidence'] or 'pendente')}</li>" for x in case['tasks'])
    evidence = ''.join('<tr><td>'+e(label)+'</td><td>'+e(item)+'</td></tr>' for label,item in evidence_rows(case['inputs']))
    source_rows = ''.join('<tr>'+''.join('<td>'+e(source.get(key) or 'Não registrado')+'</td>' for key in ['source_name','reference_date','collected_at','license_name'])+'</tr>' for source in r['sources'])
    sources = '<table><thead><tr><th>Fonte registrada</th><th>Referência</th><th>Coleta/processamento</th><th>Condição de uso</th></tr></thead><tbody>'+source_rows+'</tbody></table>' if source_rows else '<p>Sem fontes territoriais registradas nesta captura. Consultar as origens declaradas; exemplos são simulados.</p>'
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(case['title'])}</title>
<style>body{{font:15px/1.5 system-ui;color:#192b49;max-width:1000px;margin:40px auto;padding:0 24px}}h1{{font-size:28px}}h2{{font-size:20px}}article,li{{margin:12px 0}}.badge{{background:#fff2ce;padding:12px}}table{{border-collapse:collapse;width:100%;font-size:12px}}td,th{{border:1px solid #ccd3db;padding:8px;text-align:left;overflow-wrap:anywhere}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:10px}}section{{margin:28px 0}}@page{{size:A4;margin:16mm}}@media print{{body{{margin:0;padding:0;font-size:11px}}.executive{{break-after:page}}.appendix{{break-before:page}}thead{{display:table-header-group}}tr,article{{break-inside:avoid}}h2{{break-after:avoid}}}}</style></head><body>
<header><p>Urbia · {e(r['municipality_name'])}</p><h1>{e(r['title'])}</h1><p>{e(case['title'])} · revisão {case['revision']} · captura {e(r['captured_at'])}</p><p class="badge">{e(badge)}</p><p>Para salvar como PDF, use a opção de impressão do navegador.</p></header>
<section class="executive"><h2>O que encontramos</h2><p><strong>{e(s['conclusion'])}</strong></p>{reasons}<h2>Pendências decisivas</h2><ul>{gaps}</ul><h2>Próxima ação</h2><p>{e(s['next_action']['title'])}</p></section>
{tables}<section><h2>Plano de ação</h2><ul>{tasks}</ul></section><section><h2>Limitações</h2><ul>{''.join('<li>'+e(x)+'</li>' for x in r['limitations'])}</ul></section>
<section class="appendix"><h2>Anexo: premissas e fontes da captura</h2><p>Metodologia: {e(r['methodology'])}. Revisão do projeto vinculado: {e(r.get('source_project_revision') or 'não vinculado')}.</p><p>Referência das fontes e processamento são datas diferentes. A presença de uma fonte no catálogo não comprova cobertura integral do município. A memória integral, incluindo fluxos mensais, está disponível nos detalhes técnicos da análise salva e no relatório Markdown.</p><table><thead><tr><th>Premissa</th><th>Valor preservado</th></tr></thead><tbody>{evidence}</tbody></table><h3>Fontes registradas</h3>{sources}</section></body></html>'''
