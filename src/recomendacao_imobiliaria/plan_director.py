from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


# Resolve relative to source file so it works regardless of CWD (Docker, tests, etc.)
_HERE = Path(__file__).parent
DEFAULT_RULES_PATH = _HERE.parent.parent / "config" / "plan_director_pouso_alegre.json"
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
        return "; ".join(self.articles) if self.articles else "-"


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
        unknown = infer_zone_policy(zone_key, rules)
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
    raw = str(zone).strip().upper()
    value = re.sub(r"[^A-Z0-9]", "", raw)
    aliases = {
        "ZMC": "ZC",
        "ZONA CENTRAL": "ZC",
        "ZONAS CENTRAIS": "ZC",
        "ZONA MISTA CENTRAL": "ZC",
        "ZONA MISTA": "ZM",
        "ZONA DE EXPANSAO URBANA": "ZEU",
        "ZONA EXPANSAO": "ZEU",
        "RESTRICAO AMBIENTAL": "ZEPAM1",
        "ZONA DE PRESERVACAO AMBIENTAL": "ZEPAM1",
        "ZONA ESPECIAL DE INTERESSE SOCIAL": "ZEIS",
    }
    return aliases.get(raw, aliases.get(value, value))


def infer_zone_policy(zone_key: str | None, rules: dict[str, object]) -> dict[str, object]:
    unknown = dict(rules.get("unknown_zone_policy", {}))
    if not zone_key:
        return unknown

    if zone_key.startswith("ZEPAM"):
        return {
            "status": "blocked",
            "label": "Zona Especial de Preservacao Ambiental",
            "notes": "Zona ambiental oficial do PDPA. Recomendacoes imobiliarias devem ser bloqueadas ate validacao ambiental especifica.",
            "articles": unknown.get("articles", []),
        }
    if zone_key.startswith("ZEPU") or zone_key.startswith("ZEPEC") or zone_key in {"ZEIS", "ZEIS1", "ZEIS2", "ZERF"}:
        return {
            "status": "conditioned",
            "label": "Zona especial do PDPA",
            "notes": "Zona especial. Uso e ocupacao dependem de regras especificas dos anexos e validacao tecnica.",
            "articles": unknown.get("articles", []),
        }
    if zone_key == "ZER":
        return {
            "status": "conditioned",
            "label": "Zona Exclusivamente Residencial",
            "notes": "Zona residencial restritiva. Usos comerciais e nao residenciais exigem verificacao nos quadros oficiais.",
            "articles": unknown.get("articles", []),
        }
    if zone_key.startswith("ZM") or zone_key in {"ZC", "ZMV"}:
        return {
            "status": "conditioned",
            "label": "Zona urbana mista/central do PDPA",
            "notes": "Zona urbana identificada no KML oficial. Aplicar quadros de usos permitidos, incomodidade e parametros urbanisticos.",
            "articles": unknown.get("articles", []),
        }
    if zone_key in {"ZEP", "ZEEP", "ZEU"}:
        return {
            "status": "conditioned",
            "label": "Zona de expansao ou empreendimento",
            "notes": "Zona com potencial de ocupacao condicionada a parametros urbanisticos, infraestrutura e restricoes ambientais.",
            "articles": unknown.get("articles", []),
        }
    return unknown


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
