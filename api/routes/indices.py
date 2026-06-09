from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/indices/timeseries")
def get_timeseries():
    """Return all NDVI/NDBI time-series records from geo.indices."""
    try:
        from sqlalchemy import text
        from recomendacao_imobiliaria.config import load_settings
        from recomendacao_imobiliaria.db import make_engine

        settings = load_settings()
        engine = make_engine(settings)
        try:
            with engine.connect() as conn:
                rows = conn.execute(
                    text(
                        "SELECT h3_id, date::text, ndvi, ndbi "
                        "FROM geo.indices "
                        "ORDER BY date"
                    )
                ).fetchall()
        finally:
            engine.dispose()

        dates = sorted({r[1] for r in rows})
        records = [
            {"h3_id": r[0], "date": r[1], "ndvi": r[2], "ndbi": r[3]}
            for r in rows
        ]
        return {"dates": dates, "records": records}

    except Exception as exc:
        return {"dates": [], "records": [], "error": str(exc)}
