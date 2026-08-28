"""Parecer legal estruturado e auditavel para uma zona ou celula H3."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .legal_annexes import legal_annexes_as_dicts
from .plan_director import PlanDecision, evaluate_plan_compatibility


@dataclass(frozen=True)
class LegalAudit:
    zone: str | None
    intended_use: str
    status: str
    decision: str
    notes: str
    articles: list[str]
    parameters: dict[str, object]
    sources: list[dict[str, str]]
    overlays: list[dict[str, object]]
    spatial_overlays_verified: bool
    disclaimer: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_legal_audit(
    zone: str | None,
    intended_use: str,
    *,
    overlays: list[dict[str, object]] | None = None,
    spatial_overlays_verified: bool = False,
) -> LegalAudit:
    decision: PlanDecision = evaluate_plan_compatibility(zone, intended_use)
    active_overlays = overlays or []
    status = decision.status
    notes = decision.notes
    if any(str(item.get("status", "")).lower() == "blocked" for item in active_overlays):
        status = "blocked"
        notes = f"{notes} Restricao espacial bloqueante identificada: " + ", ".join(
            str(item.get("tipo", "restricao")) for item in active_overlays
            if str(item.get("status", "")).lower() == "blocked"
        )
    elif status == "allowed" and active_overlays:
        status = "conditioned"
        notes = f"{notes} Ha camadas espaciais que exigem validacao complementar."

    labels = {
        "allowed": "permitido",
        "conditioned": "condicionado",
        "blocked": "bloqueado",
    }
    return LegalAudit(
        zone=decision.zone,
        intended_use=decision.use,
        status=status,
        decision=labels[status],
        notes=notes,
        articles=decision.articles,
        parameters=decision.parameters,
        sources=decision.sources,
        overlays=active_overlays,
        spatial_overlays_verified=spatial_overlays_verified,
        disclaimer=(
            "Analise automatizada de apoio. Nao substitui consulta ao processo de aprovacao, "
            "aos anexos vigentes e a validacao por profissional habilitado."
        ),
    )


def annex_status() -> list[dict[str, object]]:
    return legal_annexes_as_dicts()
