"""Decision cases: typed journeys, live project access, revisions and task evidence."""
from datetime import date
import json
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint, and_, or_, update, text
from sqlalchemy.orm import Session

from .auth import Base, User, get_current_user, get_db, require_admin
from .organizations import Membership, ProjectOrganization, membership
from . import projects
from recomendacao_imobiliaria.config import load_settings
from recomendacao_imobiliaria.decision_cases import MODELS, TITLES, PA, evaluate_case
from recomendacao_imobiliaria.case_reports import presentation_tables, render_case_html, render_case_markdown

router = APIRouter(tags=['decision cases'], dependencies=[Depends(get_current_user)])
Kind = Literal['incorpora', 'obras', 'invest', 'mercado', 'negocios', 'governo']


class SupportedMunicipality(Base):
    __tablename__ = 'decision_municipalities'
    ibge = Column(String(7), primary_key=True)
    name = Column(String(120), nullable=False)
    state = Column(String(2), nullable=False)


class DecisionCase(Base):
    __tablename__ = 'decision_cases'
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey('land_studies.id'), nullable=True, index=True)
    kind = Column(String(24), nullable=False)
    city_ibge = Column(String(7), nullable=False)
    demonstration = Column(Integer, nullable=False, default=0)
    revision = Column(Integer, nullable=False)
    document = Column(Text, nullable=False)


class CaseVersion(Base):
    __tablename__ = 'decision_case_versions'
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('decision_cases.id'), nullable=False, index=True)
    revision = Column(Integer, nullable=False)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(40), nullable=False)
    occurred_at = Column(String(40), nullable=False)
    document = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint('case_id', 'revision'),)


class CaseInteraction(Base):
    __tablename__ = 'decision_case_interactions'
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('decision_cases.id'), nullable=False, index=True)
    event = Column(String(32), nullable=False)
    step = Column(Integer, nullable=True)
    occurred_at = Column(String(40), nullable=False)


class CaseInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=160)
    kind: Kind
    city_ibge: str = Field(PA, pattern=r'^\d{7}$')
    project_id: int | None = Field(None, ge=1)
    organization_id: int | None = Field(None, ge=1)
    demonstration: bool = False
    inputs: dict = Field(default_factory=dict)

    @model_validator(mode='after')
    def normalize(self):
        self.title = self.title.strip()
        if not self.title: raise ValueError('Informe um título')
        self.inputs = MODELS[self.kind].model_validate(self.inputs).model_dump(mode='json')
        if self.project_id and (self.kind not in ('incorpora', 'obras') or self.city_ibge != PA or self.organization_id):
            raise ValueError('Vínculo permitido apenas para Incorpora/Obras em Pouso Alegre, seguindo a equipe do projeto')
        return self


class CaseUpdate(CaseInput):
    revision: int = Field(ge=1)


class Revision(BaseModel):
    revision: int = Field(ge=1)


class TaskInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=240)
    assignee: str = Field('', max_length=160)
    due_date: date | None = None
    status: Literal['pending', 'in_progress', 'done'] = 'pending'
    evidence: str = Field('', max_length=4000)

    @model_validator(mode='after')
    def evidence_for_completion(self):
        self.title = self.title.strip()
        if not self.title: raise ValueError('Informe uma tarefa')
        if self.status == 'done' and not self.evidence.strip(): raise ValueError('Registre a evidência antes de concluir a tarefa')
        return self


def accessible_project_ids(db, user):
    shared = db.query(ProjectOrganization.project_id).join(Membership, Membership.organization_id == ProjectOrganization.organization_id).filter(Membership.user_id == user.id)
    all_shared = db.query(ProjectOrganization.project_id)
    return db.query(projects.LandStudy.id).filter(or_(projects.LandStudy.id.in_(shared), and_(projects.LandStudy.user_id == user.id, ~projects.LandStudy.id.in_(all_shared))))


def access(db, user, case_id, write=False):
    record = db.get(DecisionCase, case_id)
    if record is None: raise HTTPException(404, 'Caso não encontrado')
    editable = True
    if record.project_id:
        project = projects.owned(db, user, record.project_id, write=write)
        editable = project.can_edit
    elif record.organization_id:
        member = membership(db, record.organization_id, user.id, write=write)
        editable = member.role in ('owner', 'editor')
    elif record.owner_id != user.id: raise HTTPException(404, 'Caso não encontrado')
    record.can_edit = editable
    return record


def serialize(record, db, user):
    data = json.loads(record.document)
    stale = False
    if record.project_id and data.get('result'):
        source = projects.owned(db, user, record.project_id)
        stale = data['result'].get('source_project_revision') != source.revision
    return dict(id=record.id, kind=record.kind, city_ibge=record.city_ibge, project_id=record.project_id,
                organization_id=record.organization_id, demonstration=bool(record.demonstration), revision=record.revision,
                can_edit=getattr(record, 'can_edit', True), stale=stale, **data)


def snapshot(db, record, actor, action):
    db.add(CaseVersion(case_id=record.id, revision=record.revision, actor_id=actor.id, action=action,
                       occurred_at=projects.now(), document=record.document))


def persist(db, record, revision, document, actor, action, linkage=None):
    value = json.dumps(document, ensure_ascii=False, allow_nan=False)
    changed = db.execute(update(DecisionCase).where(DecisionCase.id == record.id, DecisionCase.revision == revision).values(document=value, revision=revision+1, **(linkage or {})))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, 'Caso alterado em outra sessão. Reabra antes de continuar.')
    snapshot(db, record, actor, action)
    db.commit()
    db.refresh(record)
    return serialize(record, db, actor)


def require_task_review(document):
    for task in document['tasks']:
        if task['status'] == 'done':
            task.update(status='pending', previous_evidence=task['evidence'], evidence='', completed_at=None, review_required=True)


def configured_for_pa():
    return load_settings().city_name.casefold().startswith('pouso alegre')


def territory_for_city(city):
    if city != PA or not configured_for_pa(): return []
    try: return projects.get_scores()
    except Exception: return []


def source_catalog(db):
    try:
        # Optional registry; a missing table must not break declared-premise cases.
        with db.begin_nested():
            exists = db.execute(text("SELECT to_regclass('ops.data_sources')")).scalar() if db.bind.dialect.name == 'postgresql' else None
            if not exists: return []
            rows = db.execute(text('SELECT dataset, source_name, source_uri, reference_date, collected_at, status, license_name FROM ops.data_sources ORDER BY collected_at DESC LIMIT 50')).mappings()
            return [{key: value.isoformat() if hasattr(value, 'isoformat') else value for key, value in row.items()} for row in rows]
    except Exception: return []


@router.get('/municipalities')
def municipalities(db: Session = Depends(get_db)):
    sources = source_catalog(db) if configured_for_pa() else []
    definitions = [
        ('territory', 'Limites e recortes territoriais', ['boundary', 'grid_h3', 'neighborhoods'], 'Bairro ou recorte não equivale ao limite cadastral do lote.'),
        ('services', 'Estabelecimentos e serviços mapeados', ['pois', 'osm_pois', 'cnes'], 'Não comprova funcionamento, cobertura completa ou natureza pública.'),
        ('population', 'População do recorte', ['population', 'census', 'census_h3'], 'População total não representa faixa etária ou área de influência comercial.'),
        ('legal', 'Zoneamento e regras estruturadas', ['zoning'], 'A existência de camada não comprova validação integral dos parâmetros ou aprovação do lote.'),
        ('market', 'Anúncios imobiliários', ['listings'], 'Preço anunciado não é preço de transação; verificar município, tipo, finalidade e período.'),
    ]
    datasets = [dict(key=key, label=label, status='partial' if any(s['dataset'] in names and s['status']=='ok' for s in sources) else 'pending',
        sources=[s for s in sources if s['dataset'] in names], limitation=limitation) for key,label,names,limitation in definitions]
    datasets.append(dict(key='school_capacity',label='Capacidade escolar e população por faixa etária',status='pending',sources=[],limitation='Sem integração validada; não permite calcular déficit de vagas.'))
    catalog = [dict(ibge=PA, name='Pouso Alegre', state='MG', coverage='partial',
                 description='Município inicial. A disponibilidade depende da fonte e do processamento; não há validação integral de todas as camadas.',
                 capabilities={'declared_studies':'available', 'territory':'partial', 'legal':'partial', 'market':'pending', 'school_capacity':'pending'},
                 sources=sources, datasets=datasets)]
    catalog += [dict(ibge=row.ibge,name=row.name,state=row.state,coverage='pending',
        description='Município cadastrado para estudos declarados; fontes territoriais e regras ainda não foram integradas e validadas.',
        capabilities={'declared_studies':'available','territory':'pending','legal':'pending','market':'pending','school_capacity':'pending'},sources=[],datasets=[])
        for row in db.query(SupportedMunicipality).order_by(SupportedMunicipality.name).all() if row.ibge != PA]
    return catalog


class MunicipalityInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ibge: str = Field(pattern=r'^\d{7}$')
    name: str = Field(min_length=2,max_length=120)
    state: str = Field(pattern=r'^[A-Z]{2}$')


@router.post('/municipalities',status_code=201)
def register_municipality(payload: MunicipalityInput, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if payload.ibge == PA or db.get(SupportedMunicipality,payload.ibge): raise HTTPException(409,'Município já cadastrado')
    if not payload.name.strip(): raise HTTPException(422,'Informe o nome do município')
    db.add(SupportedMunicipality(ibge=payload.ibge,name=payload.name.strip(),state=payload.state));db.commit()
    return dict(ibge=payload.ibge,name=payload.name.strip(),state=payload.state,coverage='pending')


@router.get('/cases')
def list_cases(kind: Kind | None = None, demonstration: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    teams = db.query(Membership.organization_id).filter(Membership.user_id == user.id)
    query = db.query(DecisionCase).filter(DecisionCase.demonstration == int(demonstration), or_(
        DecisionCase.project_id.in_(accessible_project_ids(db, user)),
        and_(DecisionCase.project_id.is_(None), or_(DecisionCase.organization_id.in_(teams), and_(DecisionCase.organization_id.is_(None), DecisionCase.owner_id == user.id)))))
    if kind: query = query.filter(DecisionCase.kind == kind)
    return [serialize(access(db, user, record.id), db, user) for record in query.order_by(DecisionCase.id.desc()).all()]


def insert_case(db, user, payload, demo_project=None):
    if payload.project_id: projects.owned(db, user, payload.project_id, write=True)
    if payload.organization_id: membership(db, payload.organization_id, user.id, write=True)
    document = dict(title=payload.title, inputs=payload.inputs, result=None, tasks=[], feedback=[], created_at=projects.now(), updated_at=projects.now())
    if demo_project: document['demo_project'] = demo_project
    record = DecisionCase(owner_id=user.id, organization_id=payload.organization_id, project_id=payload.project_id, kind=payload.kind,
                          city_ibge=payload.city_ibge, demonstration=int(payload.demonstration), revision=1,
                          document=json.dumps(document, ensure_ascii=False, allow_nan=False))
    db.add(record); db.flush(); snapshot(db, record, user, 'created')
    return record


@router.post('/cases', status_code=201)
def create_case(payload: CaseInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = insert_case(db, user, payload)
    db.commit()
    return serialize(access(db, user, record.id), db, user)


@router.get('/cases/{case_id}')
def read_case(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return serialize(access(db, user, case_id), db, user)


@router.patch('/cases/{case_id}')
def save_case(case_id: int, payload: CaseUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = access(db, user, case_id, write=True)
    if (payload.kind, payload.city_ibge, int(payload.demonstration)) != (record.kind, record.city_ibge, record.demonstration):
        raise HTTPException(409, 'Objetivo, município e modo são fixos. Crie outro caso para alterá-los.')
    linkage = None
    if payload.project_id != record.project_id:
        if record.project_id or not payload.project_id or record.demonstration: raise HTTPException(409, 'O projeto já vinculado não pode ser substituído')
        source = projects.owned(db, user, payload.project_id, write=True)
        if record.organization_id and record.organization_id != source.organization_id: raise HTTPException(409, 'O projeto deve pertencer à mesma equipe do caso')
        linkage = dict(project_id=payload.project_id, organization_id=None)
    elif payload.organization_id != record.organization_id:
        raise HTTPException(409, 'O contexto do caso não pode ser alterado nesta edição')
    document = json.loads(record.document)
    if document['inputs'] != payload.inputs or linkage:
        document['result'] = None
        require_task_review(document)
    document.update(title=payload.title, inputs=payload.inputs, updated_at=projects.now())
    return persist(db, record, payload.revision, document, user, 'project_linked' if linkage else 'updated', linkage=linkage)


def analyze_document(record, document, db, user):
    territory, diagnosis, project = [], None, None
    if record.project_id:
        if record.city_ibge != PA or not configured_for_pa(): raise HTTPException(422, 'A origem municipal do projeto legado precisa ser confirmada')
        project = projects.serialize(projects.owned(db, user, record.project_id))
    elif record.demonstration: project = document.get('demo_project')
    if document.get('result') and project and document['result'].get('source_project_revision') != project['revision']:
        require_task_review(document)
    if record.kind == 'negocios' and not record.demonstration: territory = territory_for_city(record.city_ibge)
    if record.kind == 'governo' and not record.demonstration and record.city_ibge == PA and configured_for_pa():
        try:
            from .government import public_service_diagnosis
            diagnosis = public_service_diagnosis('schools', document['inputs']['target_distance_m'])
        except HTTPException: pass
    if record.demonstration and record.city_ibge == PA:
        # Isolated fixtures never enter the territorial tables or real cases.
        from recomendacao_imobiliaria.case_demos import demo_context
        fixture = demo_context(record.kind)
        territory, diagnosis = fixture.get('territory', []), fixture.get('diagnosis')
    result = evaluate_case(record.kind, document['inputs'], city_ibge=record.city_ibge, project=project,
                           territory=territory, diagnosis=diagnosis, demonstration=bool(record.demonstration))
    municipality = db.get(SupportedMunicipality,record.city_ibge)
    result.update(captured_at=projects.now(), city_ibge=record.city_ibge,
                  municipality_name='Pouso Alegre' if record.city_ibge == PA else municipality.name if municipality else 'Município '+record.city_ibge,
                  sources=[] if record.demonstration or record.city_ibge != PA else source_catalog(db))
    result['tables'] = presentation_tables(record.kind, result)
    if record.city_ibge != PA:
        result['summary']['gaps'].append('Município sem cobertura territorial validada na Urbia; apenas informações declaradas foram consideradas.')
        result['summary']['data_status'] = 'partial'
    document['result'] = result
    existing = {task.get('suggestion_key') for task in document['tasks']}
    for suggestion in result['suggested_tasks']:
        if suggestion['key'] not in existing and len(document['tasks']) < 200:
            document['tasks'].append(dict(id=uuid4().hex, suggestion_key=suggestion['key'], title=suggestion['title'],
                evidence_required=suggestion['evidence_required'], assignee='', due_date=None, status='pending', evidence='', completed_at=None))
    document['updated_at'] = projects.now()
    return document


@router.post('/cases/{case_id}/analyze')
def analyze_case(case_id: int, payload: Revision, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = access(db, user, case_id, write=True)
    if record.revision != payload.revision: raise HTTPException(409, 'Caso alterado. Reabra antes de analisar.')
    document = analyze_document(record, json.loads(record.document), db, user)
    return persist(db, record, payload.revision, document, user, 'analyzed')


@router.post('/cases/{case_id}/tasks', status_code=201)
def add_task(case_id: int, payload: TaskInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = access(db, user, case_id, write=True)
    document = json.loads(record.document)
    if len(document['tasks']) >= 200: raise HTTPException(422, 'Limite de 200 tarefas por caso')
    task = dict(id=uuid4().hex, **payload.model_dump(mode='json', exclude={'revision'}), completed_at=projects.now() if payload.status == 'done' else None)
    document['tasks'].append(task); document['updated_at'] = projects.now()
    return persist(db, record, payload.revision, document, user, 'task_created')


@router.patch('/cases/{case_id}/tasks/{task_id}')
def update_task(case_id: int, task_id: str, payload: TaskInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = access(db, user, case_id, write=True)
    document = json.loads(record.document)
    task = next((task for task in document['tasks'] if task['id'] == task_id), None)
    if task is None: raise HTTPException(404, 'Tarefa não encontrada')
    completed = task.get('completed_at') if task.get('status') == 'done' else None
    task.update(**payload.model_dump(mode='json', exclude={'revision'}), completed_at=(completed or projects.now()) if payload.status == 'done' else None, review_required=False if payload.status == 'done' else task.get('review_required',False))
    document['updated_at'] = projects.now()
    return persist(db, record, payload.revision, document, user, 'task_updated')


@router.get('/cases/{case_id}/history')
def case_history(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    access(db, user, case_id)
    return [dict(revision=row.revision, action=row.action, occurred_at=row.occurred_at,
                 actor_name=(db.get(User,row.actor_id).name or 'Usuário')) for row in db.query(CaseVersion).filter_by(case_id=case_id).order_by(CaseVersion.revision.desc()).limit(100)]


@router.get('/cases/{case_id}/report')
def case_report(case_id: int, format: Literal['html', 'markdown'] = 'html', db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    data = serialize(access(db, user, case_id), db, user)
    if data['stale']: raise HTTPException(409, 'O projeto vinculado mudou. Recalcule o caso antes de exportar.')
    if not data.get('result'): raise HTTPException(422, 'Analise o caso antes de exportar.')
    if format == 'markdown': return Response(render_case_markdown(data), media_type='text/markdown; charset=utf-8')
    return HTMLResponse(render_case_html(data), headers={'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'"})


class Interaction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event: Literal['step_viewed', 'exported', 'partner_interest']
    step: int | None = Field(None, ge=1, le=4)


class Feedback(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: int = Field(ge=1)
    note: str = Field(min_length=1, max_length=2000)
    comprehension: Literal['clear', 'unclear'] = 'unclear'


@router.post('/cases/{case_id}/feedback', status_code=201)
def feedback(case_id: int, payload: Feedback, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = access(db, user, case_id, write=True)
    if not payload.note.strip(): raise HTTPException(422, 'Registre sua observação')
    document = json.loads(record.document)
    notes = document.setdefault('feedback', [])
    if len(notes) >= 50: raise HTTPException(422, 'Limite de 50 observações por caso')
    notes.append(dict(id=uuid4().hex, note=payload.note.strip(), comprehension=payload.comprehension, actor_id=user.id, occurred_at=projects.now()))
    document['updated_at'] = projects.now()
    return persist(db, record, payload.revision, document, user, 'feedback_recorded')


@router.post('/cases/{case_id}/interactions', status_code=204)
def interaction(case_id: int, payload: Interaction, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    access(db, user, case_id)
    db.add(CaseInteraction(case_id=case_id, event=payload.event, step=payload.step, occurred_at=projects.now()))
    db.commit()


@router.get('/case-operations/metrics')
def case_metrics(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    from sqlalchemy import func
    return dict(cases=db.query(DecisionCase).count(), analyzed=db.query(CaseVersion).filter_by(action='analyzed').count(),
                feedback=db.query(CaseVersion).filter_by(action='feedback_recorded').count(),
                steps=[dict(step=step,count=count) for step,count in db.query(CaseInteraction.step,func.count(CaseInteraction.id)).filter_by(event='step_viewed').group_by(CaseInteraction.step)],
                interactions=[dict(event=event, count=count) for event, count in db.query(CaseInteraction.event, func.count(CaseInteraction.id)).group_by(CaseInteraction.event)])


@router.post('/case-demos/{kind}', status_code=201)
def create_demo(kind: Kind, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from recomendacao_imobiliaria.case_demos import demo_inputs, demo_context
    payload = CaseInput(kind=kind, title='Demonstração · '+TITLES[kind], demonstration=True, inputs=demo_inputs(kind))
    record = insert_case(db, user, payload, demo_context(kind).get('project'))
    document = analyze_document(record, json.loads(record.document), db, user)
    return persist(db, record, 1, document, user, 'analyzed')


@router.post('/cases/{case_id}/reset-demo')
def reset_demo(case_id: int, payload: Revision, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = access(db, user, case_id, write=True)
    if not record.demonstration or record.project_id or record.organization_id: raise HTTPException(409, 'Somente demonstrações pessoais isoladas podem ser reiniciadas')
    from recomendacao_imobiliaria.case_demos import demo_inputs, demo_context
    document = json.loads(record.document)
    document.update(inputs=MODELS[record.kind].model_validate(demo_inputs(record.kind)).model_dump(mode='json'), tasks=[], demo_project=demo_context(record.kind).get('project'))
    return persist(db, record, payload.revision, analyze_document(record, document, db, user), user, 'demo_reset')
