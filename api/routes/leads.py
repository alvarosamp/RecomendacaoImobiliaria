from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Session

from .auth import Base, User, engine, get_current_user, get_db

log = logging.getLogger(__name__)

router = APIRouter()


# --- DB Model -----------------------------------------------------------

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    budget = Column(Float, nullable=True)
    zone = Column(String, nullable=True)
    property_type = Column(String, default="casa")
    financing_status = Column(String, default="nao_iniciado")
    timeline = Column(String, default="pesquisando")
    visits_done = Column(Integer, default=0)
    motivation = Column(String, nullable=True)
    source = Column(String, nullable=True)
    returning_client = Column(Boolean, default=False)

    score = Column(Float, nullable=False)
    label = Column(String, nullable=False)
    explain = Column(Text, nullable=False)  # JSON-encoded list[{label, value}]

    status = Column(String, default="novo")
    notes = Column(Text, nullable=True)


# Cria a tabela `leads` (a tabela `users` ja foi criada no import de auth.py).
# Mesmo padrao de degradacao graciosa usado em auth.py: nao derruba a importacao
# se o Postgres nao estiver acessivel agora.
try:
    Base.metadata.create_all(bind=engine)
except Exception as exc:
    log.warning("Nao foi possivel criar/verificar a tabela leads no Postgres: %s", exc)


# --- Pydantic models -----------------------------------------------------

class LeadInput(BaseModel):
    name: str = Field(..., min_length=1)
    email: str | None = None
    phone: str | None = None
    budget: float | None = None
    zone: str | None = None
    property_type: str = "casa"
    financing_status: str = "nao_iniciado"
    timeline: str = "pesquisando"
    visits_done: int = 0
    motivation: str | None = None
    source: str | None = None
    returning_client: bool = False
    notes: str | None = None


class LeadStatusUpdate(BaseModel):
    status: str


FINANCING_SCORE = {
    "aprovado": 25,
    "a_vista": 25,
    "em_analise": 12,
    "nao_iniciado": 0,
}

TIMELINE_SCORE = {
    "imediato": 25,
    "1_3_meses": 16,
    "3_6_meses": 8,
    "pesquisando": 0,
}

MOTIVATION_SCORE = {
    "mudanca_urgente": 10,
    "primeira_moradia": 7,
    "investimento": 5,
    "apenas_pesquisando": -10,
}

MOTIVATION_LABEL = {
    "mudanca_urgente": "Mudanca urgente",
    "primeira_moradia": "Primeira moradia",
    "investimento": "Investimento",
    "apenas_pesquisando": "Apenas pesquisando",
}


def _score_lead(data: LeadInput) -> dict[str, Any]:
    """Heuristica de qualificacao BANT (Budget, Authority/financiamento, Need/motivacao,
    Timeline). Nao ha dado historico de conversao para treinar um modelo supervisionado,
    entao o score e explicito e auditavel — mesma filosofia de `concept.py`.
    """
    explain: list[dict[str, str]] = []
    total = 0.0

    if data.budget and data.budget > 0:
        total += 25
        explain.append({"label": "Orcamento", "value": "Definido (+25)"})
    else:
        explain.append({"label": "Orcamento", "value": "Nao informado (+0)"})

    financing_pts = FINANCING_SCORE.get(data.financing_status, 0)
    total += financing_pts
    financing_desc = {
        "aprovado": "Aprovado",
        "a_vista": "Compra a vista",
        "em_analise": "Em analise",
        "nao_iniciado": "Nao iniciado",
    }.get(data.financing_status, "Nao informado")
    explain.append({"label": "Financiamento", "value": f"{financing_desc} (+{financing_pts})"})

    timeline_pts = TIMELINE_SCORE.get(data.timeline, 0)
    total += timeline_pts
    timeline_desc = {
        "imediato": "Imediato (<1 mes)",
        "1_3_meses": "1 a 3 meses",
        "3_6_meses": "3 a 6 meses",
        "pesquisando": "Sem prazo definido",
    }.get(data.timeline, "Nao informado")
    explain.append({"label": "Prazo", "value": f"{timeline_desc} (+{timeline_pts})"})

    visits_pts = min(max(data.visits_done, 0), 3) * 5
    total += visits_pts
    if data.visits_done > 0:
        explain.append({"label": "Visitas", "value": f"{data.visits_done} realizada(s) (+{visits_pts})"})

    if data.motivation and data.motivation in MOTIVATION_SCORE:
        motivation_pts = MOTIVATION_SCORE[data.motivation]
        total += motivation_pts
        sign = "+" if motivation_pts >= 0 else ""
        explain.append({"label": "Motivacao", "value": f"{MOTIVATION_LABEL[data.motivation]} ({sign}{motivation_pts})"})

    if data.returning_client:
        total += 5
        explain.append({"label": "Perfil", "value": "Cliente recorrente/indicado (+5)"})

    score = max(0, min(100, total))
    if score >= 70:
        label = "Alta chance"
    elif score >= 40:
        label = "Media chance"
    else:
        label = "Baixa chance"

    return {"score": round(score, 1), "label": label, "explain": explain}


def _serialize(lead: Lead) -> dict[str, Any]:
    return {
        "id": lead.id,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "budget": lead.budget,
        "zone": lead.zone,
        "property_type": lead.property_type,
        "financing_status": lead.financing_status,
        "timeline": lead.timeline,
        "visits_done": lead.visits_done,
        "motivation": lead.motivation,
        "source": lead.source,
        "returning_client": lead.returning_client,
        "score": lead.score,
        "label": lead.label,
        "explain": json.loads(lead.explain),
        "status": lead.status,
        "notes": lead.notes,
    }


# --- Routes ---------------------------------------------------------------

@router.post("/leads")
def create_lead(payload: LeadInput, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = _score_lead(payload)
    lead = Lead(
        user_id=current_user.id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        budget=payload.budget,
        zone=payload.zone,
        property_type=payload.property_type,
        financing_status=payload.financing_status,
        timeline=payload.timeline,
        visits_done=payload.visits_done,
        motivation=payload.motivation,
        source=payload.source,
        returning_client=payload.returning_client,
        score=result["score"],
        label=result["label"],
        explain=json.dumps(result["explain"], ensure_ascii=False),
        notes=payload.notes,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return _serialize(lead)


@router.get("/leads")
def list_leads(
    status: str | None = None,
    label: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Lead).filter(Lead.user_id == current_user.id)
    if status:
        query = query.filter(Lead.status == status)
    if label:
        query = query.filter(Lead.label == label)
    leads = query.order_by(Lead.score.desc()).all()
    return [_serialize(lead) for lead in leads]


@router.patch("/leads/{lead_id}/status")
def update_lead_status(
    lead_id: int,
    payload: LeadStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == current_user.id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nao encontrado")
    lead.status = payload.status
    db.commit()
    db.refresh(lead)
    return _serialize(lead)
