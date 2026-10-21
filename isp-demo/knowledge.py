"""Historical public territory and source-linked documentary screening.

No approvals, customer forecasts or legal compliance certificates are inferred.
"""
import json
import math
from pathlib import Path
from planner_errors import PlanningError

CONTEXT_OPTIONS = {
    'support_owner': {'unknown','cemig','other'},
    'installation': {'aerial','underground'},
    'public_works': {'unknown','yes','no'},
    'crossing': {'unknown','yes','no'},
    'protected_area': {'unknown','yes','no'},
}
DEFAULT_CONTEXT = {'support_owner':'unknown','installation':'aerial','public_works':'unknown','crossing':'unknown','protected_area':'unknown'}
MUNICIPAL = {'pouso-alegre':'municipal-pouso','santa-rita':'municipal-santa','itajuba':'municipal-itajuba'}


def validate_context(value):
    if value is None:
        return dict(DEFAULT_CONTEXT)
    if not isinstance(value,dict) or set(value)-set(CONTEXT_OPTIONS):
        raise PlanningError('Contexto regulatório inválido.')
    result=dict(DEFAULT_CONTEXT)
    for key,option in value.items():
        if not isinstance(option,str) or option not in CONTEXT_OPTIONS[key]:
            raise PlanningError('Contexto regulatório: opção inválida em '+key+'.')
        result[key]=option
    return result


class Knowledge:
    def __init__(self,territory,catalog):
        self.territory=territory
        self.cities={c['id']:c for c in territory['cities']}
        self.catalog=catalog
        self.references={r['id']:r for r in catalog['references']}

    @classmethod
    def from_directory(cls,path):
        path=Path(path)
        return cls(*(json.loads((path/name).read_text()) for name in ('territory.json','regulations.json')))

    def nearby(self,city_id,site,radius):
        city=self.cities[city_id]
        lat,lng=site
        min_count=mid_count=max_count=0
        ids=[]
        # 200 m cells: allow 145 m for the diagonal and local projection approximation.
        margin=self.territory['meta']['grid_m']*math.sqrt(2)/2+4
        for cell in city['cells']:
            x=math.radians(cell['lng']-lng)*6371000*math.cos(math.radians(lat))
            y=math.radians(cell['lat']-lat)*6371000
            distance=math.hypot(x,y)
            count=cell['residential']
            if distance+margin<=radius:min_count+=count
            if distance<=radius:mid_count+=count;ids.append(cell['id'])
            if distance-margin<=radius:max_count+=count
        return {'source':'IBGE CNEFE 2022','source_url':city['source_url'],'reference_year':2022,'radius_m':radius,'grid_m':200,'residential_addresses':mid_count,'cell_boundary_min':min_count,'cell_boundary_max':max_count,'cell_ids':ids,'method':'Células com centro no raio em linha reta; faixa geométrica considera células inteiras e células que interceptam o raio.','limitations':'Endereços históricos selecionados por coordenada original; não são clientes, previsão de adesão ou contagem pelo percurso do cabo. A faixa é geométrica aproximada, não intervalo estatístico.','affects_ranking':False}

    def assess(self,city_id,context,kind=None):
        context=validate_context(context)
        checks=[]
        def add(id,title,status,action,ids):
            checks.append({'id':id,'title':title,'status':status,'action':action,'references':[self.references[i] for i in ids]})
        add('provider','Regularidade da prestadora SCM','pending','Conferir autorização e cadastro da prestadora na Anatel. O inventário é fictício; nenhuma empresa foi validada.',['lgt','rgst','outorga'])
        add('licensing','Licenciamento e direito de passagem','pending','Enquadrar a intervenção e verificar licenças, dispensas e autorizações com os órgãos competentes. Distância ou rua pública não autorizam a obra.',['infra','lgt'])
        municipal=MUNICIPAL.get(city_id)
        add('municipal','Enquadramento municipal da intervenção','pending','Confirmar na prefeitura as regras de infraestrutura, obras e ocupação do solo para fibra e CTO. A norma localizada inclui ETR/antenas; isso não certifica a exigência de licença para toda caixa ou drop.',[municipal] if municipal else ['lgt'])
        if context['installation']=='aerial':
            ids=['postes']+(['cemig'] if context['support_owner']=='cemig' else [])
            action='Conferir contrato, pontos de fixação, projeto aprovado e liberação da construção com a detentora.'
            if context['support_owner']=='unknown':action='Identificar a detentora dos postes; depois conferir contrato, projeto e liberação. A Cemig não foi presumida pela localização.'
            elif context['support_owner']=='other':action+=' Solicitar as normas da detentora informada; ND-6.6 não foi aplicada como regra dessa empresa.'
            add('poles','Compartilhamento de postes','pending' if context['support_owner']!='unknown' else 'scope_unknown',action,ids)
            if kind=='new_cto' and context['support_owner']=='cemig':
                add('equipment','Instalação de uma nova CTO em poste Cemig','pending','Conferir o procedimento de instalação de equipamentos e a inserção no projeto aprovado. O local proposto é vértice de rua, não poste identificado.',['cemig'])
        else:
            add('ducts','Dutos e rede subterrânea','pending','Identificar propriedade e disponibilidade dos dutos, interferências, projeto e autorizações de escavação. Não presumir compartilhamento de infraestrutura subterrânea da Cemig.',['infra','lgt'])
        for key,title,action,ids in [
            ('public_works','Obra ou intervenção em espaço público','Consultar o órgão municipal sobre escavação, ocupação, recomposição e autorizações aplicáveis.',['infra','lgt']),
            ('crossing','Travessia ou faixa de domínio','Identificar a autoridade da rodovia/ferrovia ou concessionária e confirmar a autorização específica. Um ato histórico de terceiro não autoriza esta rota.',['infra']),
            ('protected_area','Área ambiental ou patrimônio protegido','Conferir perímetro, órgão gestor, plano de manejo e eventual manifestação ambiental ou de patrimônio.',['snuc','patrimonio'])]:
            value=context[key]
            status={'yes':'pending','unknown':'scope_unknown','no':'declared_absent'}[value]
            message=action if value=='yes' else ('Incidência não informada. '+action if value=='unknown' else 'Condição declarada como ausente pelo usuário; não verificada por mapa ou órgão competente.')
            add(key,title,status,message,ids)
        return {'status':'pending_review','checked_on':self.catalog['meta']['checked_on'],'context':context,'checks':checks,'pending_count':sum(c['status']!='declared_absent' for c in checks),'approved':False,'geometry_checked':False,'documents_verified':False,'notice':'Triagem documental pelas premissas informadas. Não certifica vigência consolidada, conformidade, licença ou aprovação; fontes e documentos devem ser conferidos pelo responsável.'}
