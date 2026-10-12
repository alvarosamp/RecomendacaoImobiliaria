"""Auditoria somente de leitura para a correcao da identidade territorial."""
from __future__ import annotations

import json

from sqlalchemy import text

from .config import Settings, load_settings
from .db import make_engine
from .municipality import MUNICIPALITY


TABLES = ("geo.grid_h3", "geo.features", "geo.scores", "geo.census_h3", "geo.neighborhoods", "ops.data_sources")


def assess_population_provenance(records: list[dict], populated_cells: int) -> dict:
    """Sem registro verificavel, dados historicos permanecem pendentes de auditoria."""
    rows = [row for row in records if row.get("dataset") == "h3_population"]
    latest = rows[0] if rows else None  # caller ordena collected_at/id DESC
    details = latest.get("details", {}) if latest else {}
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except ValueError:
            details = {}
    if not isinstance(details, dict):
        details = {}
    valid = bool(latest and latest.get("status") == "ok"
                 and details.get("municipality_code") == MUNICIPALITY.ibge_code
                 and details.get("method") and details.get("quality") == "estimated"
                 and latest.get("row_count") == populated_cells)
    return {"status": "empty" if not populated_cells else "estimated" if valid else "unverified",
            "municipality_code": details.get("municipality_code"),
            "method": details.get("method"), "reference_year": details.get("reference_year"),
            "source": latest.get("source_name") if latest else None,
            "requires_reprocessing": bool(populated_cells and not valid)}


def audit_territorial_data(settings: Settings | None = None) -> dict:
    settings = settings or load_settings()
    result = {"municipality_code": MUNICIPALITY.ibge_code, "datasus_code": MUNICIPALITY.datasus_code,
              "read_only": True, "status": "unavailable", "tables": {}, "sources": [], "warnings": []}
    engine = make_engine(settings, connect_timeout=5)
    try:
        with engine.connect() as conn, conn.begin():
            conn.execute(text("SET TRANSACTION READ ONLY"))
            populated_cells = 0
            for table in TABLES:
                exists = conn.execute(text("SELECT to_regclass(:table)"), {"table": table}).scalar()
                result["tables"][table] = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() if exists else None
            has_population = conn.execute(text("""
                SELECT EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema='geo' AND table_name='features' AND column_name='pop_estimated')
            """)).scalar()
            if has_population:
                populated_cells = conn.execute(text("SELECT COUNT(*) FROM geo.features WHERE pop_estimated IS NOT NULL")).scalar()
            if result["tables"]["ops.data_sources"] is not None:
                records = conn.execute(text("""
                    SELECT dataset, source_name, status, row_count, details, reference_date, collected_at
                    FROM ops.data_sources ORDER BY collected_at DESC, id DESC
                """)).mappings().all()
                result["sources"] = [dict(row) for row in records]
            result["population"] = assess_population_provenance(result["sources"], populated_cells)
            if result["population"]["requires_reprocessing"]:
                result["warnings"].append("Populacao historica sem procedencia municipal verificada; reprocessar antes de usar em decisoes.")
            if result["tables"]["geo.neighborhoods"] is not None:
                codes = conn.execute(text("SELECT DISTINCT municipality_code FROM geo.neighborhoods")).scalars().all()
                if any(code != MUNICIPALITY.ibge_code for code in codes):
                    result["warnings"].append("Bairros com municipio divergente ou desconhecido.")
            for row in result["sources"]:
                details = row.get("details") or {}
                if isinstance(details, str):
                    details = json.loads(details)
                code = details.get("municipality_code") if isinstance(details, dict) else None
                if code is not None and str(code) != MUNICIPALITY.ibge_code:
                    result["warnings"].append(f"Fonte {row['dataset']} registrada com municipio divergente.")
            result["warnings"].append("Registros legados sem codigo municipal nao comprovam origem; conferir caches, CNES e relatorios derivados.")
            result["status"] = "review_required"
    except Exception as exc:
        # Nao imprimir DSN/credenciais em diagnosticos.
        result["warnings"].append(f"Banco indisponivel para auditoria ({type(exc).__name__}); nenhum dado foi alterado.")
    finally:
        engine.dispose()
    return result
