"""Evidence readiness for preliminary site review; no engineering approval."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Availability = Literal['unknown', 'reported_available', 'reported_unavailable']


class TechnicalInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    slope_pct: float | None = Field(None, ge=0, le=1000)
    road_access: Availability = 'unknown'
    water: Availability = 'unknown'
    sewer: Availability = 'unknown'
    power: Availability = 'unknown'
    drainage: Availability = 'unknown'
    registry_reference: str = Field('', max_length=2000)
    topography_reference: str = Field('', max_length=2000)
    geotechnical_reference: str = Field('', max_length=2000)
    source_note: str = Field('', max_length=4000)
    reference_date: date | None = None


LABELS = {'road_access': 'Acesso viário', 'water': 'Água', 'sewer': 'Esgoto', 'power': 'Energia', 'drainage': 'Drenagem',
          'registry_reference': 'Referência cadastral ou matrícula', 'topography_reference': 'Levantamento topográfico',
          'geotechnical_reference': 'Investigação geotécnica', 'slope_pct': 'Declividade medida',
          'source_note': 'Origem das informações', 'reference_date': 'Data de referência'}
LIMITATIONS = [
    'Disponibilidade e referências são declarações do usuário, não validações automáticas de redes ou documentos.',
    'A declividade é registrada sem aplicar limiares legais ou presumir custo de terraplenagem.',
    'Uma célula H3 não delimita um lote. Confirmar matrícula, limites e acesso com levantamento próprio.',
    'Referências textuais não comprovam autenticidade, validade, capacidade das redes ou adequação geotécnica.',
    'Dados declarados completos significam apenas prontidão documental para revisão profissional, não viabilidade ou aprovação.',
]


def evaluate_technical(raw, area, legal):
    if raw is None:
        return {'status': 'not_requested', 'methodology': 'site_evidence_v1', 'limitations': LIMITATIONS}
    data = TechnicalInput.model_validate(raw)
    checks = []
    for key in ['road_access', 'water', 'sewer', 'power', 'drainage']:
        value = getattr(data, key)
        checks.append({'key': key, 'label': LABELS[key], 'status': value})
    for key in ['registry_reference', 'topography_reference', 'geotechnical_reference', 'source_note', 'reference_date', 'slope_pct']:
        value = getattr(data, key)
        known = value is not None and (not isinstance(value, str) or bool(value.strip()))
        checks.append({'key': key, 'label': LABELS[key], 'status': 'provided' if known else 'unknown'})
    pending = [check['label'] for check in checks if check['status'] == 'unknown']
    unavailable = [check['label'] for check in checks if check['status'] == 'reported_unavailable']
    alerts = []
    if legal.get('status') == 'blocked': alerts.append('A triagem urbanística indica bloqueio; informações técnicas ou retorno financeiro não afastam essa restrição.')
    if not legal.get('spatial_overlays_verified'): alerts.append('Camadas espaciais da auditoria legal ainda não estão verificadas.')
    if area.get('official_risk_level') in {'alto', 'medio'}:
        alerts.append('Há indicação de suscetibilidade oficial; investigar incidência e limitações no lote com responsável técnico.')
    if area.get('satellite_risk_alert') in {'alto', 'medio'}:
        alerts.append('Há sinal territorial por satélite; ele não substitui estudo geotécnico ou vistoria.')
    return {'status': 'evidence_pending' if pending else 'constraints_reported' if unavailable else 'ready_for_review',
            'methodology': 'site_evidence_v1', 'assumptions': data.model_dump(mode='json'), 'checks': checks,
            'pending': pending, 'unavailable': unavailable, 'alerts': alerts, 'limitations': LIMITATIONS,
            'territorial_context': {key: area.get(key) for key in ['official_risk_level', 'official_susceptibility', 'satellite_risk_alert', 'satellite_risk_confidence']}}
