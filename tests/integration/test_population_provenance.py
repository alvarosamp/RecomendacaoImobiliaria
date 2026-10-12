import os

import pytest
from sqlalchemy import text

from recomendacao_imobiliaria import ibge_collector, reporting
from recomendacao_imobiliaria.config import load_settings
from recomendacao_imobiliaria.db import make_engine
from recomendacao_imobiliaria.territorial_audit import audit_territorial_data


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGIS_INTEGRATION") != "1", reason="requer PostGIS isolado",
)


@pytest.fixture
def population_db():
    settings = load_settings()
    engine = make_engine(settings)
    ids = ["integration-pop-a", "integration-pop-b"]
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS zona TEXT"))
        for cell in ids:
            conn.execute(text("""
                INSERT INTO geo.grid_h3 (h3_id, res, geom) VALUES (:id, 8,
                ST_GeomFromText('POLYGON((-45.946 -22.226,-45.944 -22.226,-45.944 -22.224,-45.946 -22.224,-45.946 -22.226))',4326))
            """), {"id": cell})
            conn.execute(text("INSERT INTO geo.features (h3_id,pop_estimated) VALUES (:id,1)"), {"id": cell})
            conn.execute(text("INSERT INTO geo.scores (h3_id,score_residencial,score_comercial) VALUES (:id,10,20)"), {"id": cell})
    try:
        yield settings, engine, ids
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM geo.grid_h3 WHERE h3_id = ANY(:ids)"), {"ids": ids})
            conn.execute(text("DELETE FROM ops.data_sources WHERE source_name='integration-population'"))
        engine.dispose()


def test_population_provenance_reaches_query_and_read_only_audit(population_db, monkeypatch):
    settings, engine, ids = population_db
    estimate = ibge_collector.PopulationEstimate(10, "integration-population", 2022, "static_reference")
    ibge_collector._upsert_pop(engine, [{"h3_id": ids[0], "pop_estimated": 6},
                                     {"h3_id": ids[1], "pop_estimated": 4}],
                              settings=settings, method="uniform_proxy", estimate=estimate)
    monkeypatch.setattr(reporting, "_add_reference_neighborhoods", lambda frame: frame)
    monkeypatch.setattr(reporting, "_add_market_reference", lambda frame, settings: frame)
    frame = reporting.load_score_table(settings)
    assert set(frame.population_quality) == {"estimated"}
    assert set(frame.population_method) == {"uniform_proxy"}
    audit = audit_territorial_data(settings)
    assert audit["read_only"] and audit["population"]["status"] == "estimated"
    assert not audit["population"]["requires_reprocessing"]


def test_failed_provenance_write_rolls_back_population(population_db, monkeypatch):
    settings, engine, ids = population_db
    def fail(*args, **kwargs):
        raise RuntimeError("provenance write failed")
    monkeypatch.setattr(ibge_collector, "_record_population", fail)
    with pytest.raises(RuntimeError):
        ibge_collector._upsert_pop(engine, [{"h3_id": ids[0], "pop_estimated": 99}],
                                  settings=settings, method="uniform_proxy",
                                  estimate=ibge_collector.PopulationEstimate(99, "integration-population", 2022, "static_reference"))
    with engine.connect() as conn:
        assert conn.execute(text("SELECT pop_estimated FROM geo.features WHERE h3_id=:id"), {"id": ids[0]}).scalar() == 1
