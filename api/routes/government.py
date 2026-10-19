from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from recomendacao_imobiliaria.db import make_engine
from recomendacao_imobiliaria.public_services import build_diagnosis

router = APIRouter(tags=['government'])


def load_public_service_data():
    engine = make_engine()
    try:
        with engine.connect() as conn:
            census_exists = conn.execute(text("SELECT to_regclass('geo.census_h3')")).scalar() is not None
            registry_exists = conn.execute(text("SELECT to_regclass('ops.data_sources')")).scalar() is not None
            census_columns = "c.population_2022, c.source_name AS population_source, c.updated_at AS population_processed_at" if census_exists else "NULL AS population_2022, NULL AS population_source, NULL AS population_processed_at"
            census_join = "LEFT JOIN geo.census_h3 c ON c.h3_id = f.h3_id" if census_exists else ""
            rows = conn.execute(text(f"""
                SELECT f.h3_id, f.neighborhood, f.pop_estimated,
                       f.poi_school_cnt, f.dist_min_school_m, f.poi_hospital_cnt, f.dist_min_hospital_m,
                       {census_columns}
                  FROM geo.features f {census_join}
            """)).mappings().all()
            sources = conn.execute(text("""
                SELECT dataset, source_name, source_uri, reference_date, collected_at, status
                  FROM ops.data_sources WHERE status = 'ok' AND dataset IN ('pois', 'osm_pois', 'cnes', 'population', 'census', 'census_h3')
                 ORDER BY collected_at DESC LIMIT 30
            """)).mappings().all() if registry_exists else []
            def plain(row):
                return {key: value.isoformat() if hasattr(value, 'isoformat') else value for key, value in row.items()}
            return [plain(row) for row in rows], [plain(row) for row in sources]
    finally:
        engine.dispose()


@router.get('/government/diagnosis')
def public_service_diagnosis(service: Literal['schools', 'hospitals'] = 'schools', target_distance_m: float = Query(2000, ge=100, le=50000)):
    try:
        rows, sources = load_public_service_data()
    except Exception as exc:
        raise HTTPException(503, 'Dados territoriais indisponíveis. Não foi gerado um diagnóstico demonstrativo.') from exc
    return build_diagnosis(rows, service, target_distance_m, sources)
