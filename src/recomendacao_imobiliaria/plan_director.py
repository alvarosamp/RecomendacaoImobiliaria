from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_RULES_PATH = Path("config/plan_director_pouso_alegre.json")
STATUS_WEIGHT = {
    "allowed": 1.0,
    "conditioned": 0.65,
    "blocked": 0.0,
}


@dataclass(frozen=True)
class PlanDecision:
    zone: str | None
    use: str
    status: str
    multiplier: float
    label: str
    notes: str
    articles: list[str]
    parameters: dict[str, object]
    sources: list[dict[str, str]]

    @property
    def allowed(self) -> bool:
        return self.status != "blocked"

    def articles_text(self) -> str:
        return "; ".join(self.articles) if self.articles else "—"


def evaluate_plan_compatibility(
    zone: str | None,
    intended_use: str,
    rules_path: str | Path = DEFAULT_RULES_PATH,
) -> PlanDecision:
    rules = load_plan_rules(rules_path)
    zone_key = normalize_zone(zone)
    use_key = normalize_use(intended_use)
    source_refs = rules.get("legal_sources", [])

    zone_rules = rules.get("rules", {}).get(zone_key)
    if not zone_rules:
        unknown = rules.get("unknown_zone_policy", {})
        status = str(unknown.get("status", "conditioned"))
        return PlanDecision(
            zone=zone_key,
            use=use_key,
            status=status,
            multiplier=STATUS_WEIGHT.get(status, 0.65),
            label="Zona nao cadastrada",
            notes=str(unknown.get("notes", "Validacao legal manual necessaria.")),
            articles=list(unknown.get("articles", [])),
            parameters={},
            sources=source_refs,
        )

    status = str(zone_rules.get(use_key, "conditioned"))
    return PlanDecision(
        zone=zone_key,
        use=use_key,
        status=status,
        multiplier=STATUS_WEIGHT.get(status, 0.65),
        label=str(zone_rules.get("label", zone_key)),
        notes=str(zone_rules.get("notes", "")),
        articles=list(zone_rules.get("articles", [])),
        parameters=dict(zone_rules.get("parameters", {})),
        sources=source_refs,
    )


def load_plan_rules(path: str | Path = DEFAULT_RULES_PATH) -> dict[str, object]:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_zone(zone: str | None) -> str | None:
    if zone is None:
        return None
    value = str(zone).strip().upper().replace("-", "")
    aliases = {
        "ZONA CENTRAL": "ZMC",
        "ZONA MISTA CENTRAL": "ZMC",
        "ZONA MISTA": "ZM",
        "ZONA DE EXPANSAO URBANA": "ZEU",
        "ZONA EXPANSAO": "ZEU",
        "RESTRICAO AMBIENTAL": "ZPA",
        "ZONA DE PRESERVACAO AMBIENTAL": "ZPA",
        "ZONA ESPECIAL DE INTERESSE SOCIAL": "ZEIS",
    }
    return aliases.get(value, value)


def normalize_use(intended_use: str) -> str:
    value = intended_use.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "residencial": "residencial",
        "moradia": "residencial",
        "habitacao": "residencial",
        "comercial": "comercial",
        "comercio": "comercial",
        "mercado": "servicos_bairro",
        "farmacia": "servicos_bairro",
        "escola": "servicos_bairro",
        "creche": "servicos_bairro",
        "servico": "servicos_bairro",
        "servicos": "servicos_bairro",
        "industrial": "industrial",
        "industria": "industrial",
    }
    return aliases.get(value, value)
