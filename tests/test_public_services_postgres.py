"""Run only against a disposable database via URBIA_GOV_TEST_DATABASE_URL."""
import os
import pytest
from sqlalchemy import create_engine, text
from api.routes import government


@pytest.mark.skipif(not os.getenv('URBIA_GOV_TEST_DATABASE_URL'), reason='Disposable PostgreSQL not configured')
def test_database_optional_census_and_registry(monkeypatch):
    engine = create_engine(os.environ['URBIA_GOV_TEST_DATABASE_URL'])
    # No destructive initialization: fail if schemas already exist.
    with engine.begin() as conn:
        conn.execute(text('CREATE SCHEMA geo'))
        conn.execute(text('CREATE SCHEMA ops'))
        conn.execute(text('CREATE TABLE geo.features (h3_id text, neighborhood text, pop_estimated integer, poi_school_cnt integer, dist_min_school_m float, poi_hospital_cnt integer, dist_min_hospital_m float)'))
        conn.execute(text("INSERT INTO geo.features VALUES ('test-cell', 'Bairro de teste', 120, 0, 3000, 1, 500)"))
    # The reader disposes each engine; its pool reconnects on the next call.
    monkeypatch.setattr(government, 'make_engine', lambda: engine)
    try:
        records, sources = government.load_public_service_data()
        assert records[0]['population_2022'] is None
        assert records[0]['pop_estimated'] == 120
        assert sources == []
        with engine.begin() as conn:
            conn.execute(text('CREATE TABLE geo.census_h3 (h3_id text, population_2022 float, source_name text, updated_at timestamptz DEFAULT now())'))
            conn.execute(text("INSERT INTO geo.census_h3(h3_id,population_2022,source_name) VALUES ('test-cell',0,'Fonte de teste')"))
            conn.execute(text('CREATE TABLE ops.data_sources (dataset text, source_name text, source_uri text, reference_date date, collected_at timestamptz DEFAULT now(), status text)'))
            conn.execute(text("INSERT INTO ops.data_sources(dataset,source_name,status) VALUES ('pois','Coleta válida','ok'),('pois','Coleta falhou','failed')"))
        records, sources = government.load_public_service_data()
        result = government.build_diagnosis(records, 'schools', 2000, sources)
        assert result['rows'][0]['population'] == 0
        assert result['rows'][0]['rank'] is None
        assert records[0]['population_source'] == 'Fonte de teste'
        assert len(sources) == 1
        assert sources[0]['source_name'] == 'Coleta válida'
    finally:
        with engine.begin() as conn:
            conn.execute(text('DROP SCHEMA geo CASCADE'))
            conn.execute(text('DROP SCHEMA ops CASCADE'))
        engine.dispose()
