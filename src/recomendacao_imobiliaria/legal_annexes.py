from __future__ import annotations

import dataclasses
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class LegalAnnex:
    key: str
    title: str
    purpose: str
    candidates: tuple[str, ...]
    priority: str = "high"


@dataclasses.dataclass(frozen=True)
class LegalAnnexStatus:
    key: str
    title: str
    purpose: str
    priority: str
    found: bool
    path: str | None


ANNEXES = [
    LegalAnnex(
        key="occupation_parameters",
        title="Anexo 6 - Quadro 2 - Parametros de Ocupacao do Solo",
        purpose="Coeficiente de aproveitamento, taxa de ocupacao, permeabilidade, gabarito e recuos por zona.",
        candidates=(
            "data/official/pdpa/anexo_6_quadro_2_parametros_ocupacao_solo.pdf",
            "data/official/plano_diretor/102_anexo_6_quadro_2_parametros_ocupacao_solo.pdf",
        ),
    ),
    LegalAnnex(
        key="non_residential_uses_mdu",
        title="Anexo 8 - Quadro 4B - Usos nao residenciais permitidos na MDU",
        purpose="Define compatibilidade de atividades comerciais e servicos por zona urbana.",
        candidates=(
            "data/official/pdpa/anexo_8_quadro_4b_usos_nao_residenciais_mdu.pdf",
            "data/official/plano_diretor/110_anexo_8_quadro_4b_usos_nao_residenciais_mdu.pdf",
        ),
    ),
    LegalAnnex(
        key="allowed_uses_mdu",
        title="Anexo 8 - Quadro 4C - Usos permitidos na MDU",
        purpose="Complementa a regra de usos permitidos por macrozona/zona.",
        candidates=(
            "data/official/pdpa/anexo_8_quadro_4c_usos_permitidos_mdu.pdf",
            "data/official/plano_diretor/111_anexo_8_quadro_4c_usos_mdu.pdf",
        ),
    ),
    LegalAnnex(
        key="nuisance_parameters",
        title="Anexo 9 - Quadro 7 - Parametros de Incomodidade",
        purpose="Classifica incomodidade e risco de atividades nao residenciais.",
        candidates=(
            "data/official/pdpa/anexo_9_quadro_7_parametros_incomodidade.pdf",
            "data/official/plano_diretor/112_anexo_9_quadro_7_parametros_incomodidade.pdf",
        ),
    ),
    LegalAnnex(
        key="installation_conditions",
        title="Anexo 9 - Quadro 8 - Condicoes de Instalacao de Atividades",
        purpose="Define condicionantes de instalacao para atividades e estabelecimentos.",
        candidates=(
            "data/official/pdpa/anexo_9_quadro_8_condicoes_instalacao.pdf",
            "data/official/plano_diretor/113_anexo_9_quadro_8_condicoes_instalacao_atividades.pdf",
        ),
    ),
    LegalAnnex(
        key="risk_map",
        title="Anexo IX - Mapa 6 - Areas de risco",
        purpose="Identifica inundacao, alagamento e deslizamento para penalizar risco territorial.",
        candidates=(
            "data/official/pdpa/anexo_ix_mapa_6_areas_risco.pdf",
            "data/official/plano_diretor/11_anexo_ix_mapa_6_riscos_inundacao_deslizamento.pdf",
        ),
        priority="medium",
    ),
]


def inspect_legal_annexes() -> list[LegalAnnexStatus]:
    statuses: list[LegalAnnexStatus] = []
    for annex in ANNEXES:
        found_path = next((Path(path) for path in annex.candidates if Path(path).exists()), None)
        statuses.append(
            LegalAnnexStatus(
                key=annex.key,
                title=annex.title,
                purpose=annex.purpose,
                priority=annex.priority,
                found=found_path is not None,
                path=str(found_path) if found_path else None,
            )
        )
    return statuses


def legal_annexes_as_dicts() -> list[dict[str, object]]:
    return [dataclasses.asdict(status) for status in inspect_legal_annexes()]
