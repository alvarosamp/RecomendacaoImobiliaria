from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from recomendacao_imobiliaria.config import load_settings
from recomendacao_imobiliaria.db import make_engine
from recomendacao_imobiliaria.zoning_import import import_zoning_file


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGIS_INTEGRATION") != "1",
    reason="requer PostGIS real e RUN_POSTGIS_INTEGRATION=1",
)


def test_kml_is_imported_and_crossed_with_h3_features() -> None:
    settings = load_settings()
    engine = make_engine(settings)
    cells = {
        "integration-zeu": "POLYGON((-45.946 -22.226,-45.944 -22.226,-45.944 -22.224,-45.946 -22.224,-45.946 -22.226))",
        "integration-zepam": "POLYGON((-45.956 -22.236,-45.954 -22.236,-45.954 -22.234,-45.956 -22.234,-45.956 -22.236))",
        "integration-unmatched": "POLYGON((-46.01 -22.31,-46.00 -22.31,-46.00 -22.30,-46.01 -22.30,-46.01 -22.31))",
    }

    try:
        with engine.begin() as conn:
            for h3_id, polygon in cells.items():
                conn.execute(
                    text(
                        "INSERT INTO geo.grid_h3 (h3_id, res, geom) "
                        "VALUES (:h3_id, 8, ST_GeomFromText(:polygon, 4326)) "
                        "ON CONFLICT (h3_id) DO UPDATE SET geom = EXCLUDED.geom"
                    ),
                    {"h3_id": h3_id, "polygon": polygon},
                )
                conn.execute(
                    text(
                        "INSERT INTO geo.features (h3_id) VALUES (:h3_id) "
                        "ON CONFLICT (h3_id) DO NOTHING"
                    ),
                    {"h3_id": h3_id},
                )

        result = import_zoning_file("tests/fixtures/sample_zoning.kml", settings=settings)

        assert result.zones_imported == 2
        # A contagem e global; em bancos nao vazios outras celulas podem cair
        # dentro dos dois poligonos. As atribuicoes sentinela abaixo comprovam
        # o cruzamento espacial de forma deterministica.
        assert result.cells_assigned >= 2
        assert len(result.source_sha256) == 64

        with engine.connect() as conn:
            assigned = dict(
                conn.execute(
                    text(
                        "SELECT h3_id, zona FROM geo.features "
                        "WHERE h3_id = ANY(:ids) ORDER BY h3_id"
                    ),
                    {"ids": list(cells)},
                ).all()
            )
            source = conn.execute(
                text(
                    "SELECT source_name, checksum_sha256 "
                    "FROM ops.data_sources WHERE dataset = 'zoning' "
                    "ORDER BY collected_at DESC LIMIT 1"
                )
            ).one()

        assert assigned["integration-zeu"] == "ZEU"
        assert assigned["integration-zepam"] == "ZEPAM1"
        assert assigned["integration-unmatched"] is None
        assert source.source_name == "Prefeitura de Pouso Alegre - KML oficial"
        assert source.checksum_sha256 == result.source_sha256
    finally:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM geo.grid_h3 WHERE h3_id = ANY(:ids)"),
                {"ids": list(cells)},
            )
        engine.dispose()
