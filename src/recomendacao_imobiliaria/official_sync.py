"""Sincroniza camadas oficiais quando os arquivos foram disponibilizados no projeto."""
from __future__ import annotations

from .data_registry import record_data_source


def sync_official_layers() -> dict[str, object]:
    result: dict[str, object] = {"neighborhoods": "skipped", "zoning": "skipped"}
    try:
        from .neighborhood_import import default_neighborhood_file, import_neighborhoods
        result["neighborhoods"] = import_neighborhoods(default_neighborhood_file()).__dict__
    except (FileNotFoundError, ValueError) as exc:
        record_data_source("neighborhoods", "official", status="waiting_source", details={"expected": "data/official/bairros/*.gpkg ou *.geojson", "reason": str(exc)})
    try:
        from .zoning_import import default_zoning_file, import_zoning_file
        path = default_zoning_file()
        if "sample_zoning" in str(path):
            raise FileNotFoundError("somente exemplo disponível")
        result["zoning"] = import_zoning_file(path).__dict__
    except (FileNotFoundError, ValueError) as exc:
        record_data_source("zoning", "official_zoning", status="waiting_source", details={"expected": "data/official/zoneamento_oficial.*", "reason": str(exc)})
    return result
