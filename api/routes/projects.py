"""Private, versioned preliminary land studies using the existing analysis engine."""
from datetime import datetime, timezone
import json
import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from sqlalchemy import Column, ForeignKey, Integer, String, Text, update, or_, and_, UniqueConstraint
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import h3

from .auth import Base, User, get_current_user, get_db
from .concept import ConceptInput, analyze_concept
from .legal import assess_legal_compatibility
from .scores import get_scores
from recomendacao_imobiliaria.business_study import BusinessInput, evaluate_business
from recomendacao_imobiliaria.technical_study import TechnicalInput, evaluate_technical
from recomendacao_imobiliaria.financial_study import FinancialInput, evaluate_financial
from .organizations import Membership, ProjectOrganization, membership

router = APIRouter(tags=["projects"])


class LandStudy(Base):
    __tablename__ = "land_studies"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    revision = Column(Integer, nullable=False, default=1)
    document = Column(Text, nullable=False)


class StudyEvent(Base):
    __tablename__ = 'land_study_events'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('land_studies.id'), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    actor_name = Column(String(320), nullable=False)
    revision = Column(Integer, nullable=False)
    action = Column(String(32), nullable=False)
    occurred_at = Column(String(40), nullable=False)
    changed_fields = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint('project_id', 'revision'),)


class StudyVersion(Base):
    __tablename__ = 'land_study_versions'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('land_studies.id'), nullable=False, index=True)
    revision = Column(Integer, nullable=False)
    name = Column(String(160), nullable=False)
    document = Column(Text, nullable=False)
    saved_at = Column(String(40), nullable=False)
    restored_from_revision = Column(Integer, nullable=True)
    __table_args__ = (UniqueConstraint('project_id', 'revision'),)


class StudyInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    h3_id: str | None = None
    intended_use: Literal["residencial", "comercial", "misto", "industrial", "institucional"] = "residencial"
    premises: ConceptInput = Field(default_factory=ConceptInput)
    organization_id: int | None = Field(default=None, ge=1)
    financial: FinancialInput | None = None
    technical: TechnicalInput | None = None
    business: BusinessInput | None = None
    notes: str = Field(default="", max_length=10000)

    @model_validator(mode='after')
    def validate_saleable_area(self):
        if self.financial and (not math.isfinite(self.premises.buildArea) or self.premises.buildArea > 1e8):
            raise ValueError('Área construída fora do intervalo financeiro suportado')
        if self.financial and self.financial.saleable_area_m2 is not None and self.financial.saleable_area_m2 > self.premises.buildArea:
            raise ValueError('Área vendável não pode superar a área construída informada')
        return self

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("Informe um nome para o projeto")
        return value.strip()

    @field_validator("h3_id")
    @classmethod
    def valid_cell(cls, value):
        if value is not None and not h3.is_valid_cell(value):
            raise ValueError("Celula H3 invalida")
        return value


class StudyUpdate(StudyInput):
    revision: int = Field(ge=1)


class StudyRevision(BaseModel):
    revision: int = Field(ge=1)


def now():
    return datetime.now(timezone.utc).isoformat()


def owned(db, user, project_id, write=False):
    project = db.query(LandStudy).filter_by(id=project_id).first()
    if project is None: raise HTTPException(404, "Projeto nao encontrado")
    sharing = db.query(ProjectOrganization).filter_by(project_id=project_id).first()
    if sharing:
        member = membership(db, sharing.organization_id, user.id, write=write)
        project.organization_id = sharing.organization_id
        project.can_edit = member.role in {'owner', 'editor'}
    else:
        if project.user_id != user.id: raise HTTPException(404, "Projeto nao encontrado")
        project.organization_id = None
        project.can_edit = True
    return project


def serialize(project):
    return {"id": project.id, "name": project.name, "revision": project.revision, "organization_id": getattr(project, "organization_id", None), "can_edit": getattr(project, "can_edit", True), **json.loads(project.document)}


def record_event(db, project, actor, revision, action, fields):
    account = db.get(User, actor.id)
    db.add(StudyEvent(project_id=project.id, actor_id=actor.id, actor_name=(account.name or 'Usuário')[:320] if account else 'Usuário',
                      revision=revision, action=action, occurred_at=now(), changed_fields=json.dumps(fields, ensure_ascii=False)))


def persist(db, project, revision, document, name=None, actor=None, action='updated', fields=None, restored_from_revision=None):
    previous_revision, previous_name, previous_document = project.revision, project.name, project.document
    # A conditional UPDATE also protects against concurrent edits from another tab.
    changed = db.execute(update(LandStudy).where(
        LandStudy.id == project.id, LandStudy.user_id == project.user_id,
        LandStudy.revision == revision,
    ).values(document=json.dumps(document, ensure_ascii=False, allow_nan=False),
             name=name or project.name, revision=revision + 1))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Projeto alterado em outra sessao. Reabra antes de salvar.")
    # Legacy records gain a baseline only on a successful mutation. Do not invent older values.
    if db.query(StudyVersion.id).filter_by(project_id=project.id, revision=previous_revision).first() is None:
        db.add(StudyVersion(project_id=project.id, revision=previous_revision, name=previous_name,
                            document=previous_document, saved_at=now()))
    db.add(StudyVersion(project_id=project.id, revision=revision + 1, name=name or previous_name,
                        document=json.dumps(document, ensure_ascii=False, allow_nan=False), saved_at=now(),
                        restored_from_revision=restored_from_revision))
    if actor is not None: record_event(db, project, actor, revision + 1, action, fields or [])
    db.commit()
    db.refresh(project)
    return serialize(project)


def input_document(payload):
    data = payload.model_dump(mode="json", exclude={"revision", "name", "organization_id"})
    # Generated images are not part of the analytical record.
    data["premises"].pop("exteriorImage", None)
    data["premises"].pop("interiorImage", None)
    return data


@router.get("/projects")
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    shared_ids = db.query(ProjectOrganization.project_id).join(Membership, Membership.organization_id == ProjectOrganization.organization_id).filter(Membership.user_id == user.id)
    all_shared = db.query(ProjectOrganization.project_id)
    rows = db.query(LandStudy).filter(or_(LandStudy.id.in_(shared_ids), and_(LandStudy.user_id == user.id, ~LandStudy.id.in_(all_shared)))).order_by(LandStudy.id.desc()).all()
    return [serialize(owned(db, user, p.id)) for p in rows]


@router.post("/projects", status_code=201)
def create_project(payload: StudyInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.organization_id is not None: membership(db, payload.organization_id, user.id, write=True)
    document = {**input_document(payload), "created_at": now(), "updated_at": now(), "analysis": None}
    project = LandStudy(user_id=user.id, name=payload.name, revision=1, document=json.dumps(document, ensure_ascii=False))
    db.add(project)
    db.flush()
    db.add(StudyVersion(project_id=project.id, revision=1, name=project.name, document=project.document, saved_at=now()))
    if payload.organization_id is not None: db.add(ProjectOrganization(project_id=project.id, organization_id=payload.organization_id))
    record_event(db, project, user, 1, 'created', ['name', 'premises', 'financial', 'technical', 'business'])
    db.commit()
    db.refresh(project)
    return serialize(owned(db, user, project.id))


@router.get("/projects/{project_id}")
def read_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return serialize(owned(db, user, project_id))


@router.patch("/projects/{project_id}")
def save_project(project_id: int, payload: StudyUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = owned(db, user, project_id, write=True)
    if payload.organization_id != project.organization_id: raise HTTPException(409, "O contexto do projeto não pode ser alterado nesta edição")
    previous = json.loads(project.document)
    inputs = input_document(payload)
    unchanged = all(previous.get(key) == value for key, value in inputs.items() if key != "notes")
    document = {**inputs, "created_at": previous["created_at"], "updated_at": now(),
                "analysis": previous.get("analysis") if unchanged else None}
    changed = [key for key, value in inputs.items() if previous.get(key) != value]
    if payload.name != project.name: changed.append('name')
    return persist(db, project, payload.revision, document, payload.name, actor=user, fields=changed)


@router.post("/projects/{project_id}/analyze")
def analyze_project(project_id: int, payload: StudyRevision, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = owned(db, user, project_id, write=True)
    if project.revision != payload.revision:
        raise HTTPException(409, "Projeto alterado. Reabra antes de analisar.")
    document = json.loads(project.document)
    cell_id = document.get("h3_id")
    if not cell_id:
        raise HTTPException(422, "Selecione uma area antes de analisar")
    area = next((row for row in get_scores() if row["h3_id"] == cell_id), None)
    if area is None:
        raise HTTPException(404, "Area nao encontrada nos dados territoriais atuais")
    legal = assess_legal_compatibility(intended_use=document["intended_use"], h3_id=cell_id)
    premises = ConceptInput(**document["premises"])
    # Territorial values are resolved server-side instead of trusting browser scores.
    premises = premises.model_copy(update={
        "zone": area.get("zona"), "residentialScore": area.get("score_residencial"),
        "commercialScore": area.get("score_comercial"), "riskLevel": area.get("risk_level"),
        "riskConfidence": area.get("satellite_risk_confidence"), "riskAlert": area.get("satellite_risk_alert"),
        "growthSignal": area.get("growth_signal"),
    })
    document["analysis"] = {"mode":"territorial", "captured_at": now(), "area": area, "legal": legal,
                            "concept": analyze_concept(premises), "premises_used": premises.model_dump(),
                            "financial": evaluate_financial(document.get("financial"), premises.buildArea),
                            "technical": evaluate_technical(document.get("technical"), area, legal),
                            "business": evaluate_business(document.get("business"), area, legal)}
    document["updated_at"] = now()
    return persist(db, project, payload.revision, document, actor=user, action='analyzed', fields=['analysis'])


def render_report(project):
    data = serialize(project)
    analysis = data.get("analysis")
    lines = ["# Estudo preliminar de terreno — Urbia", "", data["name"],
             f"Projeto: {data['id']} · revisão {data['revision']}", f"Atualizado em: {data['updated_at']}",
             f"Área H3: {data.get('h3_id') or 'não selecionada'}", f"Uso pretendido: {data['intended_use']}",
             "", "## Premissas informadas", "```json", json.dumps(data["premises"], ensure_ascii=False, indent=2), "```",
             "", "## Observações do responsável", data["notes"] or "Não informadas."]
    if analysis:
        area, legal = analysis["area"], analysis["legal"]
        lines += ["Modo da análise: " + ("Somente premissas declaradas; contexto territorial não consultado." if analysis.get("mode") == "premises_only" else "Contexto territorial consultado na captura.")]
        lines += ["", "## Contexto territorial", f"Dados capturados em: {analysis['captured_at']}",
                  "Data de captura não equivale à data de atualização das fontes.",
                  f"Zona: {area.get('zona') or 'não identificada'}",
                  f"Score residencial: {area.get('score_residencial')}", f"Score comercial: {area.get('score_comercial')}",
                  f"Risco: {area.get('risk_level') or 'não classificado'}"]
        lines += [f"- {item.get('label')}: {item.get('value')}" for item in area.get("explainability", [])]
        lines += ["", "## Triagem urbanística", f"Status: {legal.get('status')}", legal.get("notes") or "",
                  "Camadas espaciais verificadas: " + str(legal.get("spatial_overlays_verified", False)),
                  "### Artigos e fontes"]
        lines += [f"- {article}" for article in legal.get("articles", [])]
        lines += [f"- {source.get('title', '')}: {source.get('url', '')}" for source in legal.get("sources", [])]
        lines += ["", "## Cenários preliminares", "Valores heurísticos, não orçamento de obra nem retorno garantido."]
        for scenario in analysis["concept"].get("scenarios", []):
            lines += [f"- {scenario.get('label')}: área {scenario.get('buildArea')} m²; custo estimado R$ {scenario.get('cost')}; prazo {scenario.get('months')} meses; ROI anual estimado {scenario.get('roiYear')}%."]
        technical = analysis.get('technical', {})
        lines += ['', '## Evidências técnicas do terreno', f"Status documental: {technical.get('status', 'não solicitado')}"]
        for item in technical.get('checks', []): lines.append(f"- {item['label']}: {item['status']}")
        lines += ['- ' + item for item in technical.get('alerts', []) + technical.get('limitations', [])]
        if technical.get('assumptions'): lines += ['```json', json.dumps(technical['assumptions'], ensure_ascii=False, indent=2), '```']
        business = analysis.get('business', {})
        lines += ['', '## Localização comercial', f"Status: {business.get('status', 'não solicitado')}"]
        if business.get('assumptions'):
            lines += ['```json', json.dumps(business['assumptions'], ensure_ascii=False, indent=2), '```',
                      f"Setor: {business['sector_label']} · população estimada: {business['population_estimate']} · estabelecimentos: {business['mapped_establishments']} · menor distância (m): {business['nearest_distance_m']}"]
            lines += [f"- {item['label']}: {item['status']}" for item in business['checks']]
            lines += ['Dados pendentes: ' + ', '.join(business['missing_data'])] if business.get('missing_data') else []
            lines += ['Critérios pendentes: ' + ', '.join(business['missing_criteria'])] if business.get('missing_criteria') else []
            lines += ['Processamento dos indicadores (não equivale à coleta dos estabelecimentos): ' + str(business.get('processing_timestamp') or 'não disponível')]
        lines += ['- ' + item for item in business.get('alerts', []) + business.get('limitations', [])]
        financial = analysis.get('financial', {})
        lines += ['', '## Estudo financeiro informado', f"Status: {financial.get('status', 'não solicitado')}"]
        if financial.get('status') == 'complete':
            lines += ['Premissas declaradas (não verificadas):', '```json', json.dumps(financial['assumptions'], ensure_ascii=False, indent=2), '```']
            for scenario in financial['scenarios']:
                lines += [f"- {scenario['label']}: custo R$ {scenario['total_cost']}; receita líquida R$ {scenario['net_revenue']}; lucro R$ {scenario['profit']}; VPL R$ {scenario['npv']}; margem {scenario['margin_pct']}%; ROI do empreendimento {scenario['roi_pct']}%; equilíbrio R$/m² {scenario['break_even_price_m2']}; déficit mensal máximo R$ {scenario['peak_monthly_deficit']}."]
        elif financial.get('missing'):
            lines += ['Premissas pendentes: ' + ', '.join(financial['missing'])]
        lines += ['- ' + limitation for limitation in financial.get('limitations', [])]
        lines += ["", "### Registro das evidências", "```json", json.dumps(analysis, ensure_ascii=False, indent=2), "```"]
    else:
        lines += ["", "## Análise pendente", "Os dados ainda não foram analisados ou as premissas mudaram. Execute a análise para obter evidências atuais."]
    history = getattr(project, 'audit_history', [])
    lines += ['', '## Atividades registradas (até 100 mais recentes)', 'Histórico disponível apenas desde a implantação desta funcionalidade.']
    for event in history:
        origin = f" · premissas recuperadas da revisão {event['restored_from_revision']}" if event.get('restored_from_revision') else ''
        lines.append(f"- Revisão {event['revision']} · {event['occurred_at']} · {event['actor_name']} · {event['action']}{origin} · campos: {', '.join(event['changed_fields'])}")
    lines += ["", "## Limitações e conclusão preliminar", "A célula H3 representa uma região, não o limite cadastral de um lote. Dimensões são premissas fornecidas pelo responsável. A triagem não constitui aprovação urbanística. Confirmar matrícula, levantamento topográfico, infraestrutura, fontes oficiais e viabilidade técnica/financeira. Cenários não comprovam compatibilidade legal."]
    return "\n".join(lines)


@router.get("/projects/{project_id}/report")
def project_report(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = owned(db, user, project_id)
    project.audit_history = history_rows(db, project_id, 100)
    return Response(render_report(project), media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="urbia-projeto-{project.id}.md"'})


class ShareInput(BaseModel):
    organization_id: int = Field(ge=1)
    revision: int = Field(ge=1)


@router.post('/projects/{project_id}/share')
def share_project(project_id: int, payload: ShareInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = owned(db, user, project_id, write=True)
    if project.organization_id is not None: raise HTTPException(409, 'Este projeto já pertence a uma equipe')
    membership(db, payload.organization_id, user.id, write=True)
    db.add(ProjectOrganization(project_id=project_id, organization_id=payload.organization_id))
    try:
        persist(db, project, payload.revision, json.loads(project.document), actor=user, action='shared', fields=['organization_id'])
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Projeto já compartilhado. Atualize a lista.') from exc
    return serialize(owned(db, user, project_id))


def history_rows(db, project_id, limit, before_revision=None):
    query = db.query(StudyEvent).filter_by(project_id=project_id)
    if before_revision is not None: query = query.filter(StudyEvent.revision < before_revision)
    events = query.order_by(StudyEvent.revision.desc()).limit(limit).all()
    versions = {version.revision: version for version in db.query(StudyVersion).filter(
        StudyVersion.project_id == project_id, StudyVersion.revision.in_([event.revision for event in events])).all()}
    return [{'revision': event.revision, 'actor_name': event.actor_name, 'occurred_at': event.occurred_at,
             'action': event.action, 'changed_fields': json.loads(event.changed_fields),
             'snapshot_available': event.revision in versions,
             'restored_from_revision': versions[event.revision].restored_from_revision if event.revision in versions else None}
            for event in events]


@router.get('/projects/{project_id}/history')
def project_history(project_id: int, before_revision: int | None = Query(None, ge=1, le=2147483647), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned(db, user, project_id)
    rows = history_rows(db, project_id, 51, before_revision)
    baseline = db.query(StudyVersion).outerjoin(StudyEvent, and_(StudyEvent.project_id == StudyVersion.project_id,
        StudyEvent.revision == StudyVersion.revision)).filter(StudyVersion.project_id == project_id,
        StudyEvent.id.is_(None)).order_by(StudyVersion.revision).first()
    return {'items': rows[:50], 'next_before_revision': rows[49]['revision'] if len(rows) > 50 else None,
            'baseline_snapshot': {'revision': baseline.revision, 'saved_at': baseline.saved_at} if baseline else None}


def version_inputs(name, document):
    return {'name': name, **{key: document.get(key) for key in StudyInput.model_fields if key not in {'name', 'organization_id'}}}


def input_differences(previous, current, prefix=''):
    differences = []
    for key in sorted(previous.keys() | current.keys()):
        old, new = previous.get(key), current.get(key)
        field = f'{prefix}.{key}' if prefix else key
        if isinstance(old, dict) and isinstance(new, dict):
            differences.extend(input_differences(old, new, field))
        elif old != new:
            differences.append({'field': field, 'historical': old, 'current': new})
    return differences


def find_version(db, project_id, revision):
    version = db.query(StudyVersion).filter_by(project_id=project_id, revision=revision).first()
    if version is None: raise HTTPException(404, 'Conteúdo desta revisão não foi preservado')
    return version


@router.get('/projects/{project_id}/versions/{version_revision}')
def project_version(project_id: int, version_revision: int = Path(ge=1, le=2147483647), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = owned(db, user, project_id)
    version = find_version(db, project_id, version_revision)
    document = json.loads(version.document)
    inputs = version_inputs(version.name, document)
    return {'revision': version.revision, 'saved_at': version.saved_at, 'name': version.name,
            'inputs': inputs, 'analysis': document.get('analysis'), 'current_revision': project.revision,
            'differences': input_differences(inputs, version_inputs(project.name, json.loads(project.document))),
            'restored_from_revision': version.restored_from_revision}


@router.post('/projects/{project_id}/versions/{version_revision}/restore')
def restore_project_version(project_id: int, payload: StudyRevision, version_revision: int = Path(ge=1, le=2147483647), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = owned(db, user, project_id, write=True)
    if project.revision != payload.revision: raise HTTPException(409, 'Projeto alterado. Reabra antes de recuperar premissas.')
    if version_revision == project.revision: raise HTTPException(409, 'Esta já é a revisão atual')
    version = find_version(db, project_id, version_revision)
    current = json.loads(project.document)
    try:
        # Revalidate historical inputs under today's schema. Team membership is never restored.
        inputs = StudyInput.model_validate({**json.loads(version.document), 'name': version.name,
                                            'organization_id': project.organization_id})
    except ValidationError as exc:
        raise HTTPException(422, 'Premissas antigas incompatíveis com as validações atuais. Revise os dados manualmente.') from exc
    document = {**input_document(inputs), 'created_at': current['created_at'], 'updated_at': now(), 'analysis': None}
    differences = input_differences(version_inputs(project.name, current), version_inputs(inputs.name, document))
    fields = sorted({item['field'].split('.')[0] for item in differences} | {'analysis'})
    return persist(db, project, payload.revision, document, inputs.name, actor=user, action='restored',
                   fields=fields, restored_from_revision=version_revision)


@router.post('/projects/{project_id}/analyze-premises')
def analyze_declared_premises(project_id: int, payload: StudyRevision, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = owned(db, user, project_id, write=True)
    if project.revision != payload.revision: raise HTTPException(409, 'Projeto alterado. Reabra antes de analisar.')
    document = json.loads(project.document)
    if all(document.get(key) is None for key in ['financial','technical','business']):
        raise HTTPException(422, 'Preencha um bloco técnico, comercial ou financeiro antes de calcular as premissas')
    premises = ConceptInput(**document['premises'])
    legal = {'status':'analisar', 'zone':None, 'articles':[], 'sources':[], 'spatial_overlays_verified':False,
             'notes':'Cálculo somente de premissas declaradas. Zoneamento, localização e restrições espaciais não foram consultados nesta execução.',
             'disclaimer':'Consultar o contexto territorial e o processo oficial antes de decidir sobre implantação.'}
    area = {'h3_id':document.get('h3_id')}
    document['analysis'] = {'mode':'premises_only', 'captured_at':now(), 'area':area, 'legal':legal,
                            'concept':{'scenarios':[]}, 'premises_used':premises.model_dump(),
                            'financial':evaluate_financial(document.get('financial'), premises.buildArea),
                            'technical':evaluate_technical(document.get('technical'), area, legal),
                            'business':evaluate_business(document.get('business'), area, legal)}
    document['updated_at'] = now()
    return persist(db, project, payload.revision, document, actor=user, action='premises_analyzed', fields=['analysis'])
