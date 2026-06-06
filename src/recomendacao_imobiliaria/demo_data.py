from __future__ import annotations

from .scoring import AreaFeatures


def sample_areas() -> list[AreaFeatures]:
    return [
        AreaFeatures(
            h3_id="demo-norte-01",
            zona="Zona de Expansao Urbana",
            ndvi_mean_90=0.42,
            ndvi_slope_180=-0.035,
            ndbi_mean_90=0.31,
            ndbi_slope_180=0.052,
            poi_supermarket_cnt=0,
            poi_pharmacy_cnt=1,
            poi_school_cnt=1,
            dist_min_supermarket_m=2100,
            dist_min_pharmacy_m=900,
            dist_min_school_m=1200,
            residential_allowed=True,
            commercial_allowed=True,
        ),
        AreaFeatures(
            h3_id="demo-centro-01",
            zona="Zona Central",
            ndvi_mean_90=0.18,
            ndvi_slope_180=-0.005,
            ndbi_mean_90=0.58,
            ndbi_slope_180=0.008,
            poi_supermarket_cnt=4,
            poi_pharmacy_cnt=5,
            poi_school_cnt=3,
            dist_min_supermarket_m=250,
            dist_min_pharmacy_m=180,
            dist_min_school_m=600,
            residential_allowed=True,
            commercial_allowed=True,
        ),
        AreaFeatures(
            h3_id="demo-sul-01",
            zona="Restricao Ambiental",
            ndvi_mean_90=0.71,
            ndvi_slope_180=0.004,
            ndbi_mean_90=0.08,
            ndbi_slope_180=0.001,
            poi_supermarket_cnt=0,
            poi_pharmacy_cnt=0,
            poi_school_cnt=0,
            dist_min_supermarket_m=3500,
            dist_min_pharmacy_m=2800,
            dist_min_school_m=2600,
            residential_allowed=False,
            commercial_allowed=False,
        ),
    ]
