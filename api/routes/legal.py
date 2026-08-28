from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from recomendacao_imobiliaria.config import load_settings
from recomendacao_imobiliaria.db import make_engine
from recomendacao_imobiliaria.legal_audit import annex_status, build_legal_audit

router = APIRouter(tags=["legal"])


def _spatial_context(h3_id: str) -> tuple[str | None, list[dict[str, object]], bool]:
    settings = load_settings()
    engine = make_engine(settings)
    try:
        with engine.connect() as conn:
            cell = conn.execute(
                text("SELECT h3_id FROM geo.grid_h3 WHERE h3_id = :h3_id"),
                {"h3_id": h3_id},
            ).mappings().first()
            if cell is None:
                raise HTTPException(status_code=404, detail="Celula H3 nao encontrada")
            zone = conn.execute(
                text("SELECT zona FROM geo.v_h3_zona WHERE h3_id = :h3_id LIMIT 1"),
                {"h3_id": h3_id},
            ).scalar()
            overlay_count = conn.execute(text("SELECT COUNT(*) FROM geo.overlays")).scalar() or 0
            overlays = conn.execute(
                text("""
                    SELECT tipo, COALESCE(regras, '{}'::jsonb) AS rules
                    FROM geo.overlays o
                    JOIN geo.grid_h3 g ON g.h3_id = :h3_id
                    WHERE ST_Intersects(ST_Centroid(g.geom), o.geom)
                """),
                {"h3_id": h3_id},
            ).mappings().all()
    finally:
        engine.dispose()
    normalized = [
        {"tipo": row["tipo"], **(dict(row["rules"]) if isinstance(row["rules"], dict) else {})}
        for row in overlays
    ]
    return zone, normalized, bool(overlay_count)


@router.get("/legal/assess")
def assess_legal_compatibility(
    intended_use: str = Query(..., min_length=3),
    zone: str | None = None,
    h3_id: str | None = None,
):
    """Retorna a justificativa legal de um uso por zona ou por celula H3."""
    if not zone and not h3_id:
        raise HTTPException(status_code=422, detail="Informe zone ou h3_id")
    overlays: list[dict[str, object]] = []
    overlays_verified = False
    if h3_id:
        found_zone, overlays, overlays_verified = _spatial_context(h3_id)
        zone = found_zone or zone
    return build_legal_audit(
        zone,
        intended_use,
        overlays=overlays,
        spatial_overlays_verified=overlays_verified,
    ).as_dict()


@router.get("/legal/annexes")
def list_legal_annexes():
    """Mostra disponibilidade dos anexos que fundamentam a analise."""
    return annex_status()
