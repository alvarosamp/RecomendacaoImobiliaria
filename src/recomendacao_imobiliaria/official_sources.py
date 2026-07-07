from __future__ import annotations

import dataclasses
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class OfficialSource:
    name: str
    what_to_get: str
    url: str
    expected_files: tuple[str, ...]
    notes: str


@dataclasses.dataclass(frozen=True)
class OfficialDataStatus:
    base_dir: str
    found_files: list[str]
    missing_recommended: list[str]
    ready_for_zoning_import: bool


OFFICIAL_SOURCES = [
    OfficialSource(
        name="Prefeitura de Pouso Alegre",
        what_to_get="Mapa oficial de zoneamento, anexos do Plano Diretor e arquivos georreferenciados.",
        url="https://pousoalegre.mg.gov.br/",
        expected_files=(
            "zoneamento_oficial.geojson",
            "zoneamento_oficial.shp",
            "zoneamento_oficial.gpkg",
            "zoneamento_oficial.kml",
            "zoneamento_oficial.kmz",
        ),
        notes=(
            "Procure por Secretaria de Planejamento, Desenvolvimento Urbano, "
            "Geoprocessamento, Cadastro Tecnico ou Portal da Transparencia. "
            "Se nao houver download publico, solicite por e-SIC/Lei de Acesso a Informacao."
        ),
    ),
    OfficialSource(
        name="Camara Municipal de Pouso Alegre / Legislador",
        what_to_get="Texto do Plano Diretor, leis de uso e ocupacao do solo, anexos e alteracoes.",
        url="https://www.legislador.com.br/legisladorweb.asp?ID=122&WCI=LeiTexto&aaLei=2021&inEspecieLei=1&nrLei=6476",
        expected_files=("plano_diretor_lei_6476_2021.pdf", "uso_ocupacao_solo.pdf"),
        notes="Use para conferir artigos, anexos, parametros urbanisticos e alteracoes legislativas.",
    ),
    OfficialSource(
        name="IBGE",
        what_to_get="Limite municipal, setores censitarios e dados socioeconomicos.",
        url="https://www.ibge.gov.br/geociencias/downloads-geociencias.html",
        expected_files=("setores_censitarios.gpkg", "limite_municipal.gpkg"),
        notes="Base util para populacao, renda, domicilios e validacao territorial.",
    ),
    OfficialSource(
        name="IDE-Sisema / Infraestrutura de Dados Espaciais de MG",
        what_to_get="Camadas ambientais, hidrografia, unidades de conservacao e restricoes.",
        url="https://idesisema.meioambiente.mg.gov.br/",
        expected_files=("restricoes_ambientais.gpkg",),
        notes="Use para cruzar recomendacoes com APP, areas protegidas e restricoes ambientais.",
    ),
]


def official_sources_as_dicts() -> list[dict[str, object]]:
    return [dataclasses.asdict(source) for source in OFFICIAL_SOURCES]


def validate_official_data(base_dir: str | Path = "data/official") -> OfficialDataStatus:
    base_path = Path(base_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    found = sorted(
        str(path.relative_to(base_path)).replace("\\", "/")
        for path in base_path.rglob("*")
        if path.is_file()
    )
    lower_found = {Path(item).name.lower() for item in found}
    zoning_ready = any(
        "zoneamento" in Path(item).name.lower()
        and Path(item).suffix.lower() in {".geojson", ".shp", ".gpkg", ".kml", ".kmz"}
        for item in found
    )

    recommended = {
        "zoneamento_oficial.geojson",
        "zoneamento_oficial.shp",
        "zoneamento_oficial.gpkg",
        "zoneamento_oficial.kml",
        "zoneamento_oficial.kmz",
        "plano_diretor_lei_6476_2021.pdf",
        "uso_ocupacao_solo.pdf",
    }
    zoning_names = {
        "zoneamento_oficial.geojson",
        "zoneamento_oficial.shp",
        "zoneamento_oficial.gpkg",
        "zoneamento_oficial.kml",
        "zoneamento_oficial.kmz",
    }
    missing = sorted(
        item
        for item in recommended
        if item not in lower_found and not (item in zoning_names and zoning_ready)
    )

    return OfficialDataStatus(
        base_dir=str(base_path),
        found_files=found,
        missing_recommended=missing,
        ready_for_zoning_import=zoning_ready,
    )
