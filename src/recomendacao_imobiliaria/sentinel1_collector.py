"""Coleta de recorrencia de agua por Sentinel-1 RTC/SAR."""
from __future__ import annotations

from pathlib import Path
import os
import numpy as np
import pandas as pd


def water_fraction(vv: np.ndarray, vh: np.ndarray, *, vv_threshold: float = 0.06, vh_threshold: float = 0.02) -> float:
    """Proporcao de pixels de baixo retroespalhamento, candidato a agua aberta.

    Os limiares devem ser calibrados com mapa oficial/local antes de qualquer
    decisao operacional. O resultado e somente uma evidencia de triagem.
    """
    valid = np.isfinite(vv) & np.isfinite(vh)
    if not valid.any():
        return 0.0
    return float(np.mean((vv[valid] <= vv_threshold) & (vh[valid] <= vh_threshold)))


def collect_water_recurrence_for_grid(output_csv: str = "data/risk_sentinel1_inputs.csv", *, months: int = 12, settings=None) -> str:
    """Coleta Sentinel-1 RTC e calcula recorrencia de agua por H3.

    A colecao exige credencial do Planetary Computer; sem ela a falha e explicita.
    """
    import datetime
    import h3
    import planetary_computer
    import pystac_client
    import stackstac
    from sqlalchemy import text
    from .config import load_settings
    from .db import db_engine

    settings = settings or load_settings()
    with db_engine(settings) as engine:
        h3_ids = [row[0] for row in engine.connect().execute(text("SELECT h3_id FROM geo.grid_h3"))]
    points = [point for cell in h3_ids for point in h3.cell_to_boundary(cell)]
    bbox = [min(p[1] for p in points), min(p[0] for p in points), max(p[1] for p in points), max(p[0] for p in points)]
    end = datetime.date.today()
    start = end - datetime.timedelta(days=30 * months)
    # O SDK solicita SAS anonimo por padrao. Uma chave e opcional e apenas
    # melhora limites/expiracao quando o usuario a tiver.
    subscription_key = os.getenv("PC_SDK_SUBSCRIPTION_KEY")
    if subscription_key:
        planetary_computer.set_subscription_key(subscription_key)
    catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
    try:
        items = [item for item in catalog.search(collections=["sentinel-1-rtc"], bbox=bbox, datetime=f"{start}/{end}", limit=48).items() if {"vv", "vh"}.issubset(item.assets)]
    except Exception as exc:
        raise RuntimeError(
            "Nao foi possivel acessar o Sentinel-1 RTC. A coleta tentou token SAS anonimo. "
            "Se a colecao exigir credencial para esta requisicao, defina PC_SDK_SUBSCRIPTION_KEY e tente novamente."
        ) from exc
    if not items:
        raise RuntimeError("Nenhuma cena Sentinel-1 RTC VV/VH encontrada ou autorizada.")
    observations = {cell: [] for cell in h3_ids}
    for item in items[::max(1, len(items) // 12)][:12]:
        try:
            da = stackstac.stack([item], assets=["vv", "vh"], bounds_latlon=bbox, epsg=4326, resolution=0.0002).squeeze("time")
        except Exception as exc:
            raise RuntimeError(
                "O catalogo respondeu, mas o raster Sentinel-1 RTC recusou a leitura anonima. "
                "Defina PC_SDK_SUBSCRIPTION_KEY somente se quiser acesso com limites ampliados."
            ) from exc
        vv, vh, xs, ys = da.sel(band="vv").values, da.sel(band="vh").values, da.coords["x"].values, da.coords["y"].values
        for cell in h3_ids:
            lat, lon = zip(*h3.cell_to_boundary(cell))
            yi, xi = np.where((ys >= min(lat)) & (ys <= max(lat)))[0], np.where((xs >= min(lon)) & (xs <= max(lon)))[0]
            if len(yi) and len(xi): observations[cell].append(water_fraction(vv[np.ix_(yi, xi)], vh[np.ix_(yi, xi)]))
    rows = [{"h3_id": c, "water_observation_rate": round(float(np.mean(v)), 4)} for c, v in observations.items() if v]
    output = Path(output_csv); output.parent.mkdir(parents=True, exist_ok=True); pd.DataFrame(rows).to_csv(output, index=False)
    return str(output)
