"""Typed decision inputs and evidence-based summaries for the six Urbia journeys.

All monetary values are declared assumptions. No inferred market appreciation,
engineering approval, consumer demand or public-service capacity is produced.
"""
from datetime import date
from statistics import median
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .business_study import BusinessInput, evaluate_business
from .financial_study import FinancialInput, evaluate_financial

PA = '3152501'
KINDS = ('incorpora', 'obras', 'invest', 'mercado', 'negocios', 'governo')
TITLES = dict(incorpora='Comparação de propostas de empreendimento', obras='Plano de investigação do terreno',
              invest='Quadro de compra e revenda', mercado='Apresentação comercial do imóvel',
              negocios='Comparação de pontos comerciais', governo='Agenda de investigação territorial')
MONEY = dict(ge=0, le=1e12)


class Input(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra='forbid')


class EvidenceInput(Input):
    source_note: str = Field('', max_length=4000)
    reference_date: date | None = None


class Proposal(Input):
    name: str = Field('', max_length=160)
    product: str = Field('', max_length=500)
    build_area_m2: float | None = Field(None, gt=0, le=1e8)
    financial: FinancialInput = Field(default_factory=FinancialInput)

    @model_validator(mode='after')
    def areas(self):
        if self.build_area_m2 is not None and self.financial.saleable_area_m2 is not None and self.financial.saleable_area_m2 > self.build_area_m2:
            raise ValueError('Área vendável não pode superar a área construída da proposta')
        return self


class Incorporation(Input):
    proposals: list[Proposal] = Field(default_factory=list, max_length=2)


class Works(Input):
    investigation_note: str = Field('', max_length=4000)


class Investment(EvidenceInput):
    name: str = Field('', max_length=160)
    acquisition: float | None = Field(None, **MONEY)
    improvements: float | None = Field(None, **MONEY)
    other_costs: float | None = Field(None, **MONEY)
    sale_price: float | None = Field(None, **MONEY)
    sales_expenses_pct: float | None = Field(None, ge=0, le=100)
    months: int | None = Field(None, ge=1, le=600)


class Investments(Input):
    budget: float | None = Field(None, **MONEY)
    variation_pct: float = Field(10, ge=0, le=100)
    properties: list[Investment] = Field(default_factory=list, max_length=3)


class Comparable(EvidenceInput):
    name: str = Field('', max_length=160)
    city_ibge: str = Field(PA, pattern=r'^\d{7}$')
    property_type: Literal['casa', 'apartamento', 'terreno', 'comercial'] = 'casa'
    transaction: Literal['venda', 'aluguel'] = 'venda'
    area_m2: float | None = Field(None, ge=.01, le=1e8)
    price: float | None = Field(None, ge=.01, le=1e12)
    differences: str = Field('', max_length=2000)
    provenance: Literal['user', 'simulation'] = 'user'
    selected: bool = True


class Market(EvidenceInput):
    address: str = Field('', max_length=500)
    property_type: Literal['casa', 'apartamento', 'terreno', 'comercial'] = 'casa'
    transaction: Literal['venda', 'aluguel'] = 'venda'
    area_m2: float | None = Field(None, ge=.01, le=1e8)
    asking_price: float | None = Field(None, ge=.01, le=1e12)
    positives: str = Field('', max_length=4000)
    objections: str = Field('', max_length=4000)
    owner_questions: str = Field('', max_length=4000)
    area_tolerance_pct: float = Field(30, ge=0, le=100)
    maximum_age_days: int = Field(365, ge=1, le=3650)
    comparables: list[Comparable] = Field(default_factory=list, max_length=12)


class Point(EvidenceInput):
    name: str = Field('', max_length=160)
    address: str = Field('', max_length=500)
    h3_id: str | None = None
    rent: float | None = Field(None, **MONEY)
    other_monthly_costs: float | None = Field(None, **MONEY)
    area_m2: float | None = Field(None, gt=0, le=1e8)
    visibility: Literal['unknown', 'favoravel', 'desfavoravel'] = 'unknown'
    access: Literal['unknown', 'favoravel', 'desfavoravel'] = 'unknown'
    observed_competitors: int | None = Field(None, ge=0, le=100000)
    visit_note: str = Field('', max_length=4000)


class Business(Input):
    criteria: BusinessInput = Field(default_factory=BusinessInput)
    points: list[Point] = Field(default_factory=list, max_length=3)


class Region(Input):
    h3_id: str = Field(min_length=1, max_length=32)
    name: str = Field('', max_length=160)
    justification: str = Field('', max_length=4000)


class Government(Input):
    target_distance_m: float = Field(2000, ge=100, le=50000)
    regions: list[Region] = Field(default_factory=list, max_length=30)


MODELS = dict(incorpora=Incorporation, obras=Works, invest=Investments, mercado=Market, negocios=Business, governo=Government)


def money(value):
    return f'R$ {value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def reason(found, why, verify, evidence):
    return dict(found=found, why=why, verify=verify, evidence=evidence)


def evaluate_case(kind, raw, *, city_ibge=PA, project=None, territory=None, diagnosis=None, demonstration=False):
    data = MODELS[kind].model_validate(raw).model_dump(mode='json')
    reasons, gaps, actions, details = [], [], [], {}
    limits = ['A conclusão descreve os dados desta captura, sem garantir resultado ou aprovação.']
    analysis = (project or {}).get('analysis') or {}
    legal = analysis.get('legal') or {}
    source_revision = (project or {}).get('revision')
    if kind in ('incorpora', 'obras'):
        if not project:
            gaps.append('Vincular um projeto de terreno acessível.')
        elif not analysis:
            gaps.append('Calcular e salvar a análise do projeto de terreno para consultar seu contexto.')
        if not legal.get('spatial_overlays_verified'):
            gaps.append('Confirmar os parâmetros urbanísticos e as restrições espaciais do lote.')
        if legal.get('status') == 'blocked':
            gaps.insert(0, 'Há restrição identificada na triagem urbanística; o resultado econômico não a afasta.')
        details['legal'] = legal
    if kind == 'incorpora':
        rows = []
        if len(data['proposals']) != 2: gaps.append('Registrar duas propostas para comparar.')
        for index, proposal in enumerate(data['proposals']):
            name = proposal['name'] or f'Proposta {index + 1}'
            result = evaluate_financial(proposal['financial'], proposal['build_area_m2'] or 0) if proposal['build_area_m2'] else {'status': 'pending'}
            if not proposal['name'] or not proposal['product'] or result['status'] != 'complete':
                gaps.append(f'{name}: informar produto, área, custos, vendas, origem e data das premissas.')
            rows.append(dict(name=name, product=proposal['product'], build_area_m2=proposal['build_area_m2'], financial=result))
        complete = [row for row in rows if row['financial']['status'] == 'complete']
        conclusion = 'As propostas precisam de mais informações para serem comparadas.'
        if len(complete) == 2:
            a, b = complete
            ca, cb = a['financial']['scenarios'][0]['total_cost'], b['financial']['scenarios'][0]['total_cost']
            conclusion = 'As duas propostas têm o mesmo custo total nas premissas informadas.' if ca == cb else f"{a['name'] if ca < cb else b['name']} tem menor custo total nas premissas informadas."
            reasons.append(reason(f'{a["name"]}: {money(ca)}; {b["name"]}: {money(cb)}.', 'Menor custo não significa maior retorno ou aprovação do produto.', 'Conferir áreas, orçamento e preço de venda com os responsáveis.', ['proposals.0.financial', 'proposals.1.financial']))
            reasons.append(reason(f"Resultado base: {a['name']} {money(a['financial']['scenarios'][0]['profit'])}; {b['name']} {money(b['financial']['scenarios'][0]['profit'])}.",
                'O resultado depende das áreas, despesas e valores de venda declarados.', 'Validar as referências de preço e a composição das despesas.', ['proposals.0.financial', 'proposals.1.financial']))
            reasons.append(reason(f"Com pressão de custos e vendas: {a['name']} {money(a['financial']['scenarios'][1]['profit'])}; {b['name']} {money(b['financial']['scenarios'][1]['profit'])}.",
                'A sensibilidade mostra como as hipóteses escolhidas mudam o resultado; não é uma previsão.', 'Revisar a tolerância ao risco e as variações informadas.', ['proposals.0.financial.cost_variation_pct', 'proposals.1.financial.price_variation_pct']))
        details['proposals'] = rows
        actions.append(dict(key='validate_proposals', title='Confirmar áreas e orçamento das propostas', evidence_required='Referência dos parâmetros e do orçamento revisado.'))
        limits.append('Áreas são declaradas. Não foi calculado potencial construtivo legal validado.')
    elif kind == 'obras':
        technical = analysis.get('technical') or {}
        checks = technical.get('checks') or []
        pending = [check for check in checks if check['status'] in ('unknown', 'reported_unavailable')]
        if not checks: gaps.append('Preencher e calcular as evidências técnicas no projeto vinculado.')
        for check in pending:
            actions.append(dict(key='technical_' + check['key'], title='Verificar ' + check['label'].lower(), evidence_required='Registrar referência documental ou resultado da verificação por responsável.'))
        conclusion = f'{len(pending)} verificações técnicas precisam ser encaminhadas.' if checks else 'O terreno precisa de um levantamento inicial de evidências.'
        if checks and not pending: conclusion = 'As informações técnicas estão preenchidas para revisão profissional.'
        for check in pending[:3]:
            found = check['label'] + (': indisponibilidade declarada.' if check['status']=='reported_unavailable' else ': evidência ainda não informada.')
            why = 'A condição pode exigir solução específica e custos que ainda precisam de levantamento.' if check['key'] in ('road_access','water','sewer','power','drainage') else 'A implantação depende de conhecer o terreno e a validade dos documentos.'
            reasons.append(reason(found, why, 'Registrar a verificação, sua origem e a revisão por responsável.', ['project.analysis.technical.'+check['key']]))
        if not reasons: reasons.append(reason('As referências técnicas precisam de revisão profissional.', 'Preenchimento de dados não comprova sua validade ou aprovação.', 'Conferir abrangência e autenticidade das evidências.', ['project.analysis.technical']))
        details['technical'] = technical
        limits.append('Disponibilidade de infraestrutura e documentos são declarações, sem validação de capacidade ou aprovação técnica.')
    elif kind == 'invest':
        rows = []
        if len(data['properties']) < 2: gaps.append('Registrar pelo menos duas alternativas para comparar.')
        if data['budget'] is None: gaps.append('Informar o orçamento disponível para verificar compatibilidade.')
        for index, item in enumerate(data['properties']):
            name = item['name'] or f'Imóvel {index + 1}'
            missing = [key for key, value in item.items() if value is None or (isinstance(value, str) and not value.strip())]
            row = dict(name=name, missing=missing, assumptions=item)
            if missing: gaps.append(f'{name}: completar preço, despesas, prazo, origem e data.')
            else:
                capital = round(item['acquisition'] + item['improvements'] + item['other_costs'], 2)
                scenarios = []
                for label, factor in [('Base informada', 1), ('Venda menor', 1-data['variation_pct']/100), ('Venda maior', 1+data['variation_pct']/100)]:
                    net = round(item['sale_price'] * factor * (1-item['sales_expenses_pct']/100), 2)
                    profit = round(net-capital, 2)
                    scenarios.append(dict(label=label, net_revenue=net, profit=profit, roi_pct=round(100*profit/capital, 2) if capital else None))
                row.update(capital=capital, within_budget=None if data['budget'] is None else capital <= data['budget'], scenarios=scenarios, months=item['months'],
                           cash_flow=[dict(month=0, net=-capital), dict(month=item['months'], net=scenarios[0]['net_revenue'])])
            rows.append(row)
        ready = [row for row in rows if not row['missing']]
        fits = [row for row in ready if row['within_budget'] is True]
        conclusion = f'{len(fits)} de {len(ready)} alternativas calculadas cabem no orçamento informado.' if ready and data['budget'] is not None else 'Complete as alternativas e o orçamento para comparar desembolsos.'
        for row in ready[:3]: reasons.append(reason(f"{row['name']}: desembolso de {money(row['capital'])}.", 'O capital é desembolsado no início; a venda ocorre no prazo informado.', 'Validar despesas, conservação, documentação e preço de revenda.', [f'properties.{rows.index(row)}']))
        details.update(properties=rows, budget=data['budget'], variation_pct=data['variation_pct'])
        limits.append('Compra, melhorias e despesas no mês zero; venda integral ao final. Sem aluguel, financiamento, desconto ou previsão de valorização. ROI não é anual.')
        actions.append(dict(key='validate_resale', title='Validar custos e preço de revenda', evidence_required='Orçamento e referências de venda com origem e data.'))
    elif kind == 'mercado':
        usable, excluded = [], []
        reference = date.fromisoformat(data['reference_date']) if data['reference_date'] else None
        for index, item in enumerate(data['comparables']):
            why = []
            if not item['selected']: why.append('Não selecionado')
            if item['city_ibge'] != city_ibge: why.append('Outro município')
            if item['property_type'] != data['property_type']: why.append('Outro tipo de imóvel')
            if item['transaction'] != data['transaction']: why.append('Outra finalidade')
            if not item['price'] or not item['area_m2']: why.append('Preço ou área ausente')
            if data['area_m2'] is None: why.append('Área do imóvel principal pendente')
            elif item['area_m2'] and abs(item['area_m2']/data['area_m2']-1)*100 > data['area_tolerance_pct']: why.append('Área fora da faixa escolhida')
            if not item['source_note'].strip() or not item['reference_date'] or not reference: why.append('Origem ou data pendente')
            elif not 0 <= (reference-date.fromisoformat(item['reference_date'])).days <= data['maximum_age_days']: why.append('Fora do período escolhido')
            if item['provenance'] == 'simulation' and not demonstration: why.append('Simulação não participa de estudo real')
            if why: excluded.append(dict(name=item['name'] or f'Comparável {index+1}', reasons=why))
            else: usable.append({**item, 'price_m2': item['price']/item['area_m2']})
        if not data['address'].strip() or not data['area_m2'] or not data['source_note'].strip() or reference is None: gaps.append('Completar identificação, área, origem e data do imóvel apresentado.')
        conclusion = 'Ficha comercial preparada; a pesquisa de comparáveis ainda está pendente.'
        details.update(comparables=usable, excluded=excluded, property=data, sample_size=len(usable))
        if usable:
            central = median([item['price_m2'] for item in usable])
            asking_m2 = data['asking_price']/data['area_m2'] if data['asking_price'] and data['area_m2'] else None
            deviation = round((asking_m2/central-1)*100, 2) if asking_m2 is not None else None
            conclusion = f'{len(usable)} comparáveis selecionados permitem uma discussão descritiva de preço.'
            details.update(reference_price_m2=central, asking_price_m2=asking_m2, deviation_pct=deviation)
            reasons.append(reason(f'Mediana da amostra: {money(central)} por m².', 'É uma referência dos anúncios escolhidos, não o preço de transação nem um laudo.', 'Conferir diferenças de conservação, localização e condição de negociação.', ['comparables']))
        else: gaps.append('Selecionar comparáveis adequados; nenhuma referência automática foi fabricada.')
        actions.append(dict(key='market_visit', title='Revisar comparáveis e perguntas ao proprietário', evidence_required='Referências selecionadas e diferenças observadas.'))
        limits.append('Amostra declarada pelo usuário, sem auditoria de anúncios. Não há ampliação automática de bairro, município, tipo ou finalidade.')
    elif kind == 'negocios':
        rows = []
        if len(data['points']) < 2: gaps.append('Registrar pelo menos dois pontos para comparar.')
        for index, point in enumerate(data['points']):
            area = next((area for area in territory or [] if area['h3_id'] == point['h3_id']), {})
            triage = evaluate_business(data['criteria'], area, {})
            cost = round(point['rent'] + point['other_monthly_costs'], 2) if point['rent'] is not None and point['other_monthly_costs'] is not None else None
            name = point['name'] or f'Ponto {index+1}'
            pending = [key for key in ['name', 'address', 'rent', 'other_monthly_costs', 'area_m2', 'observed_competitors', 'source_note', 'reference_date', 'visit_note'] if point[key] is None or point[key] == '']
            pending += [key for key in ['visibility', 'access'] if point[key] == 'unknown']
            if pending: gaps.append(f'{name}: completar ficha de visita, custos e origem das observações.')
            if triage['missing_data'] or triage['missing_criteria']: gaps.append(f'{name}: indicadores territoriais ou critérios comerciais pendentes.')
            rows.append(dict(name=name, monthly_cost=cost, visit=point, commercial=triage, pending=pending))
            actions.append(dict(key=f'point_{index}', title=f'Conferir em visita: {name}', evidence_required='Observações de acesso, visibilidade, custos e concorrentes com data.'))
        conclusion = 'Compare os custos declarados e organize as visitas; não há previsão de demanda ou faturamento.'
        for row in rows[:3]: reasons.append(reason(f"{row['name']}: custo mensal {money(row['monthly_cost']) if row['monthly_cost'] is not None else 'pendente'}.", 'O custo informado não inclui automaticamente obras, estoque ou despesas de operação.', 'Confirmar o contrato, o acesso e as condições de funcionamento.', [f'points.{rows.index(row)}']))
        details['points'] = rows
        limits.append('Observações de visita e dados territoriais não comprovam demanda, concorrência efetiva, capacidade de compra ou autorização do uso.')
    else:
        selected = []
        available = {row['h3_id']: row for row in (diagnosis or {}).get('rows', [])}
        if not data['regions']: gaps.append('Selecionar regiões para a investigação escolar.')
        for region in data['regions']:
            evidence = available.get(region['h3_id'])
            if evidence is None: gaps.append(f"{region['name'] or 'Região selecionada'}: indicadores indisponíveis nesta captura.")
            if not region['justification'].strip(): gaps.append(f"{region['name'] or 'Região selecionada'}: registrar justificativa da vistoria.")
            selected.append({**region, 'evidence': evidence})
            actions.append(dict(key='region_'+region['h3_id'], title='Investigar atendimento escolar: '+(region['name'] or 'região selecionada'), evidence_required='Justificativa, verificação de oferta e registro de vistoria.'))
        conclusion = f"{len(selected)} {'região selecionada' if len(selected) == 1 else 'regiões selecionadas'} para investigar o atendimento escolar."
        for region in selected[:3]:
            evidence=region['evidence'] or {}
            count=evidence.get('count')
            found=(region['name'] or 'Recorte selecionado')+(': '+str(count)+' estabelecimentos mapeados.' if count is not None else ': oferta mapeada ainda não disponível.')
            reasons.append(reason(found, 'Contagem territorial não informa quantas vagas existem ou quem pode ser atendido.', 'Confirmar oferta pública, faixa etária, capacidade e acesso em vistoria.', ['regions', 'diagnosis']))
        if not reasons: reasons.append(reason('Ainda não há regiões selecionadas.', 'A agenda precisa de recorte e justificativa para orientar a equipe.', 'Escolher as regiões que devem ser investigadas.', ['regions']))
        details.update(regions=selected, diagnosis=diagnosis)
        gaps.append('Capacidade e população por faixa etária não foram verificadas; não é possível calcular déficit de vagas.')
        limits.append('Distância e contagem de estabelecimentos não equivalem a déficit educacional ou necessidade comprovada de construir escolas.')
    if legal.get('status') == 'blocked':
        conclusion = 'Há restrição na triagem urbanística. Resolva essa questão antes de avançar com a proposta.'
        actions.insert(0, dict(key='legal_review', title='Esclarecer a restrição da triagem urbanística', evidence_required='Consulta à fonte aplicável e registro da revisão por responsável.'))
    if not actions: actions.append(dict(key='review_evidence', title='Revisar evidências e pendências com responsável', evidence_required='Referências e resultado da revisão.'))
    gaps = list(dict.fromkeys(gaps))
    return dict(methodology='decision_'+kind+'_v1', title=TITLES[kind], source_project_revision=source_revision,
                summary=dict(conclusion=conclusion, reasons=reasons[:3], gaps=gaps, next_action=actions[0],
                             data_status='partial' if gaps else 'declared_complete'),
                details=details, suggested_tasks=actions, limitations=limits,
                evidence_policy='Simulação identificada' if demonstration else 'Premissas declaradas e fontes territoriais quando disponíveis')
