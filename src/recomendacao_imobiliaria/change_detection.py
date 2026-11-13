"""Deteccao de conversao de area vegetada em construida/exposta com Sentinel-2 a 10 m.

Dois niveis, calculados sobre as mesmas composicoes anuais:

* alta confianca (regra): NDVI maximo anual por pixel. Lavoura e pasto ficam
  verdes em algum mes; obra, terraplenagem e construcao nao. Marca o pixel que
  era vegetado no ano de referencia e nao ficou verde em nenhuma observacao
  valida do ano posterior. Alta precisao, baixo recall: perde casas pequenas e
  obras em terreno que ja estava sem vegetacao.
* provavel (classificador): LightGBM sobre estatisticas anuais de NDVI, bandas da
  data seca (antes/depois, 6 bandas), indices de solo exposto e contexto de
  vizinhanca. Recupera boa parte do que a regra perde, com mais falsos alertas.

A diferenca simples de indices entre duas datas foi avaliada e descartada: em
Pouso Alegre 2019-2023 teve precisao de 0,18 por bloco de 200 m e 66-83% da area
marcada era lavoura.

Os dois niveis sao triagem: nao distinguem obra de area deixada em pousio. O
classificador foi treinado contra um mapa de cobertura (ele proprio um modelo),
entao a concordancia com a referencia e um piso, nao medida de campo. Use
``validate_against_reference`` e a inspecao visual para acompanhar a qualidade.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

import numpy as np

STAC_URL = "https://earth-search.aws.element84.com/v1"
# Somente Collection 1: radiometria harmonizada (offset aplicado uma unica vez).
COLLECTION = "sentinel-2-c1-l2a"
RESOLUTION_M = 10
PIXEL_HA = (RESOLUTION_M * RESOLUTION_M) / 10_000.0
PLANETARY_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
PLANETARY_SIGN = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
# Mapa anual de cobertura a 10 m (Impact Observatory/Esri), usado so como referencia.
REFERENCE_COLLECTION = "io-lulc-annual-v02"
REFERENCE_BUILT, REFERENCE_CROPS, REFERENCE_RANGELAND = 7, 5, 11
DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "change_model"
FEATURE_BANDS = ("blue", "green", "red", "nir", "swir16", "swir22")
_GDAL_ENV = dict(
    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
    GDAL_HTTP_TIMEOUT="60",
    GDAL_HTTP_MAX_RETRY="3",
    GDAL_HTTP_RETRY_DELAY="2",
)


@dataclass(frozen=True)
class ChangeParams:
    # Vegetado no ano de referencia: NDVI maximo anual igual ou acima disto.
    before_ndvi_min: float = 0.45
    # Nunca verde no ano posterior: NDVI maximo anual igual ou abaixo disto.
    after_ndvi_max: float = 0.35
    # Observacoes validas minimas por pixel em cada ano.
    min_observations: int = 3
    max_scene_cloud_pct: float = 60.0
    # Uma data (a menos nublada) por janela, para cobrir estacao seca e chuvosa.
    windows: tuple[tuple[str, str], ...] = (
        ("01-01", "02-28"), ("03-01", "04-30"), ("05-01", "06-30"),
        ("07-01", "08-31"), ("09-01", "10-31"), ("11-01", "12-31"),
    )
    # Classes SCL aceitas: 4 vegetacao, 5 solo/nao vegetado, 7 nao classificado.
    valid_scl: tuple[int, ...] = (4, 5, 7)
    # Manchas menores que isto (em pixels de 10 m) sao descartadas como ruido.
    min_patch_pixels: int = 5


@dataclass
class AnnualComposite:
    year: int
    ndvi_max: np.ndarray
    observations: np.ndarray
    sources: list[dict]
    ndvi_min: np.ndarray | None = None
    ndvi_mean: np.ndarray | None = None
    # Reflectancia x 10000 (uint16) das 6 bandas na data seca menos nublada.
    dry: dict[str, np.ndarray] = field(default_factory=dict)
    dry_valid: np.ndarray | None = None


@dataclass
class ChangeResult:
    changed: np.ndarray
    valid: np.ndarray
    transform: object
    epsg: int
    year_before: int
    year_after: int
    sources: dict[str, list[dict]] = field(default_factory=dict)
    # Mascara do classificador (None quando nao ha modelo em config/change_model).
    probable: np.ndarray | None = None
    model_meta: dict | None = None


# ---------------------------------------------------------------------------
# Nucleo espectral (puro numpy, testavel sem rede)
# ---------------------------------------------------------------------------

def ndvi_of(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where((nir + red) > 0.02, (nir - red) / (nir + red), np.nan).astype("float32")


def accumulate_max(ndvi_max: np.ndarray, observations: np.ndarray, ndvi: np.ndarray, valid: np.ndarray) -> None:
    """Atualiza, no lugar, o maximo anual e a contagem de observacoes validas."""
    better = valid & (ndvi > ndvi_max)
    ndvi_max[better] = ndvi[better]
    observations += valid.astype(observations.dtype)


def annual_change(before_max: np.ndarray, before_obs: np.ndarray, after_max: np.ndarray, after_obs: np.ndarray,
                  params: ChangeParams | None = None) -> dict[str, np.ndarray]:
    """Pixels vegetados no ano de referencia que nao ficaram verdes no ano posterior."""
    params = params or ChangeParams()
    valid = (before_obs >= params.min_observations) & (after_obs >= params.min_observations)
    converted = valid & (before_max >= params.before_ndvi_min) & (after_max <= params.after_ndvi_max)
    return {"valid": valid, "changed": remove_small_patches(converted, params.min_patch_pixels)}


def remove_small_patches(mask: np.ndarray, min_pixels: int) -> np.ndarray:
    """Descarta manchas conectadas menores que ``min_pixels``."""
    if min_pixels <= 1 or not mask.any():
        return mask
    try:
        from scipy import ndimage
    except ImportError:  # sem scipy o filtro e ignorado, nunca inventado
        return mask
    labels, count = ndimage.label(mask)
    if count == 0:
        return mask
    sizes = np.bincount(labels.ravel())
    keep = sizes >= min_pixels
    keep[0] = False
    return keep[labels]


def block_counts(mask: np.ndarray, block: int) -> np.ndarray:
    """Soma de pixels verdadeiros por bloco ``block`` x ``block``."""
    rows, cols = (mask.shape[0] // block) * block, (mask.shape[1] // block) * block
    trimmed = mask[:rows, :cols].astype("int32")
    return trimmed.reshape(rows // block, block, cols // block, block).sum(axis=(1, 3))


def agreement_metrics(detected: np.ndarray, truth: np.ndarray, eligible: np.ndarray | None = None) -> dict[str, float | int]:
    """Precisao, recall e F1 entre dois mapas booleanos (por bloco)."""
    if eligible is not None:
        detected, truth = detected[eligible], truth[eligible]
    tp = int(np.sum(detected & truth))
    fp = int(np.sum(detected & ~truth))
    fn = int(np.sum(~detected & truth))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


# ---------------------------------------------------------------------------
# Catalogo e leitura das cenas
# ---------------------------------------------------------------------------

def select_scenes(bounds_ll: tuple[float, float, float, float], year: int, params: ChangeParams) -> list[list[dict]]:
    """Para cada janela do ano, a data menos nublada cujas cenas cobrem toda a area."""
    import requests
    from shapely.geometry import box, shape
    from shapely.ops import unary_union

    area = box(*bounds_ll)
    chosen: list[list[dict]] = []
    for start, end in params.windows:
        payload = {
            "collections": [COLLECTION],
            "bbox": list(bounds_ll),
            "datetime": f"{year}-{start}T00:00:00Z/{year}-{end}T23:59:59Z",
            "query": {"eo:cloud_cover": {"lt": params.max_scene_cloud_pct}},
            "limit": 100,
        }
        response = requests.post(f"{STAC_URL}/search", json=payload, timeout=90)
        response.raise_for_status()
        by_date: dict[str, list[dict]] = {}
        for item in response.json().get("features", []):
            by_date.setdefault(item["properties"]["datetime"][:10], []).append(item)
        candidates = []
        for stamp, items in by_date.items():
            if not unary_union([shape(item["geometry"]) for item in items]).buffer(1e-4).covers(area):
                continue
            cloud = float(np.mean([item["properties"].get("eo:cloud_cover", 100.0) for item in items]))
            candidates.append((cloud, stamp, items))
        if candidates:
            candidates.sort(key=lambda entry: (entry[0], entry[1]))
            chosen.append(candidates[0][2])
    if len(chosen) < params.min_observations:
        raise RuntimeError(
            f"Apenas {len(chosen)} data(s) utilizaveis em {year}; sao necessarias {params.min_observations}."
        )
    return chosen


def read_mosaic(items: list[dict], transform, width: int, height: int, epsg: int,
                bands: tuple[str, ...] = ("scl", "red", "nir", "swir16")) -> dict[str, np.ndarray]:
    """Le as bandas pedidas das cenas de uma data, na grade de 10 m pedida."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT

    scene: dict[str, np.ndarray] = {}
    with rasterio.Env(**_GDAL_ENV):
        for band in bands:
            mosaic = np.zeros((height, width), dtype="uint16")
            scale, offset = 0.0001, 0.0
            for item in items:
                asset = item["assets"][band]
                spec = (asset.get("raster:bands") or [{}])[0]
                scale, offset = spec.get("scale", scale), spec.get("offset", offset)
                with rasterio.open(asset["href"]) as source:
                    resampling = Resampling.nearest if band in ("scl", "red", "nir") else Resampling.bilinear
                    with WarpedVRT(source, crs=f"EPSG:{epsg}", transform=transform, width=width,
                                   height=height, resampling=resampling) as vrt:
                        data = vrt.read(1)
                mosaic = np.where(mosaic == 0, data, mosaic)
            if band == "scl":
                scene[band] = mosaic.astype("uint8")
            else:
                values = mosaic.astype("float32") * scale + offset
                values[mosaic == 0] = np.nan
                scene[band] = values
    usable = np.isin(scene["scl"], (4, 5))
    if usable.any() and float(np.mean(scene["red"][usable] < -0.01)) > 0.05:
        raise RuntimeError("Controle radiometrico falhou: reflectancia negativa acima do esperado.")
    return scene


def utm_epsg(lon: float, lat: float) -> int:
    zone = int((lon + 180) // 6) + 1
    return (32700 if lat < 0 else 32600) + zone


def target_grid(bounds_ll: tuple[float, float, float, float]):
    """Grade de 10 m alinhada a grade do Sentinel-2 (multiplos de 10 m em UTM)."""
    from pyproj import Transformer
    from rasterio.transform import from_origin

    epsg = utm_epsg((bounds_ll[0] + bounds_ll[2]) / 2, (bounds_ll[1] + bounds_ll[3]) / 2)
    to_utm = Transformer.from_crs(4326, epsg, always_xy=True)
    xs, ys = zip(*[to_utm.transform(x, y) for x in (bounds_ll[0], bounds_ll[2]) for y in (bounds_ll[1], bounds_ll[3])])
    xmin = np.floor(min(xs) / RESOLUTION_M) * RESOLUTION_M
    ymax = np.ceil(max(ys) / RESOLUTION_M) * RESOLUTION_M
    width = int(np.ceil((max(xs) - xmin) / RESOLUTION_M))
    height = int(np.ceil((ymax - min(ys)) / RESOLUTION_M))
    return from_origin(xmin, ymax, RESOLUTION_M, RESOLUTION_M), width, height, epsg


def _dry_index(scenes: list[list[dict]]) -> int:
    """Indice da data seca (jun-set) menos nublada: a unica lida com todas as bandas."""
    dry = [(float(np.mean([i["properties"].get("eo:cloud_cover", 100.0) for i in items])), index)
           for index, items in enumerate(scenes) if items[0]["properties"]["datetime"][5:7] in ("06", "07", "08", "09")]
    if not dry:
        raise RuntimeError("Nenhuma data da estacao seca (jun-set) disponivel para o ano.")
    return min(dry)[1]


def annual_composite(bounds_ll, year: int, params: ChangeParams | None = None, *, cache_dir: Path | None = None,
                     progress=print) -> AnnualComposite:
    """Estatisticas anuais de NDVI e bandas da data seca, por pixel de 10 m."""
    params = params or ChangeParams()
    transform, width, height, epsg = target_grid(bounds_ll)
    cache = None
    if cache_dir is not None:
        cache = Path(cache_dir) / f"composite_v2_{epsg}_{int(transform.c)}_{int(transform.f)}_{width}x{height}_{year}.npz"
        if cache.exists():
            stored = np.load(cache, allow_pickle=False)
            progress(f"  {year}: composicao lida do cache")
            return AnnualComposite(
                year, stored["ndvi_max"].astype("float32"), stored["observations"], json.loads(str(stored["sources"])),
                stored["ndvi_min"].astype("float32"), stored["ndvi_mean"].astype("float32"),
                {band: stored[f"dry_{band}"] for band in FEATURE_BANDS}, stored["dry_valid"],
            )
    ndvi_max = np.full((height, width), -1.0, dtype="float32")
    ndvi_min = np.full((height, width), 2.0, dtype="float32")
    ndvi_sum = np.zeros((height, width), dtype="float32")
    observations = np.zeros((height, width), dtype="uint8")
    dry: dict[str, np.ndarray] = {}
    dry_valid = None
    sources = []
    scenes = select_scenes(bounds_ll, year, params)
    dry_at = _dry_index(scenes)
    for index, items in enumerate(scenes):
        stamp = items[0]["properties"]["datetime"][:10]
        is_dry = index == dry_at
        progress(f"  {year}: lendo {stamp} ({len(items)} tile(s)){' [todas as bandas]' if is_dry else ''}...")
        bands = ("scl", "red", "nir") + (("blue", "green", "swir16", "swir22") if is_dry else ())
        scene = read_mosaic(items, transform, width, height, epsg, bands=bands)
        ndvi = ndvi_of(scene["red"], scene["nir"])
        valid = np.isin(scene["scl"], params.valid_scl) & np.isfinite(ndvi)
        accumulate_max(ndvi_max, observations, ndvi, valid)
        ndvi_min = np.where(valid & (ndvi < ndvi_min), ndvi, ndvi_min)
        ndvi_sum += np.where(valid, ndvi, 0.0)
        if is_dry:
            for band in FEATURE_BANDS:
                dry[band] = np.clip(np.nan_to_num(scene[band], nan=0.0) * 10000, 0, 65535).astype("uint16")
            dry_valid = valid
        sources.append({
            "date": stamp,
            "dry_season_bands": is_dry,
            "ids": [item["id"] for item in items],
            "scene_cloud_pct": [item["properties"].get("eo:cloud_cover") for item in items],
            "local_usable_pct": round(float(valid.mean() * 100), 2),
            "stac": [f"{STAC_URL}/collections/{COLLECTION}/items/{item['id']}" for item in items],
        })
    with np.errstate(invalid="ignore", divide="ignore"):
        ndvi_mean = np.where(observations > 0, ndvi_sum / np.maximum(observations, 1), np.nan).astype("float32")
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, ndvi_max=ndvi_max.astype("float16"), ndvi_min=ndvi_min.astype("float16"),
                            ndvi_mean=ndvi_mean.astype("float16"), observations=observations,
                            dry_valid=dry_valid, sources=json.dumps(sources),
                            **{f"dry_{band}": dry[band] for band in FEATURE_BANDS})
    return AnnualComposite(year, ndvi_max, observations, sources, ndvi_min, ndvi_mean, dry, dry_valid)


# ---------------------------------------------------------------------------
# Classificador (nivel "provavel")
# ---------------------------------------------------------------------------

def build_features(before: AnnualComposite, after: AnnualComposite) -> dict[str, np.ndarray]:
    """Atributos por pixel: estatisticas anuais, bandas secas, deltas e contexto."""
    from scipy import ndimage

    features: dict[str, np.ndarray] = {}
    for tag, comp in (("b", before), ("a", after)):
        features[f"{tag}_max"] = comp.ndvi_max.astype("float32")
        features[f"{tag}_min"] = comp.ndvi_min.astype("float32")
        features[f"{tag}_mean"] = comp.ndvi_mean.astype("float32")
        for band in FEATURE_BANDS:
            features[f"{tag}_{band}"] = comp.dry[band].astype("float32") / 10000.0
        with np.errstate(invalid="ignore", divide="ignore"):
            swir, nir, red, blue, green = (features[f"{tag}_{b}"] for b in ("swir16", "nir", "red", "blue", "green"))
            features[f"{tag}_ndbi"] = (swir - nir) / (swir + nir + 1e-6)
            features[f"{tag}_bsi"] = ((swir + red) - (nir + blue)) / ((swir + red) + (nir + blue) + 1e-6)
            features[f"{tag}_ndwi"] = (green - nir) / (green + nir + 1e-6)
        features[f"{tag}_amp"] = features[f"{tag}_max"] - features[f"{tag}_min"]
    for key in ("max", "min", "mean", "ndbi", "bsi", "swir16", "red", "amp"):
        features[f"d_{key}"] = features[f"a_{key}"] - features[f"b_{key}"]
    box = lambda mask, size: ndimage.uniform_filter(mask.astype("float32"), size=size)  # noqa: E731
    features["ctx_nonveg_b_300"] = box(features["b_max"] < 0.35, 61)
    features["ctx_nonveg_b_100"] = box(features["b_max"] < 0.35, 21)
    features["ctx_amax_100"] = box(features["a_max"], 21)
    features["ctx_dmax_100"] = box(features["d_max"], 21)
    features["ctx_amax_30"] = box(features["a_max"], 7)
    features["ctx_bright_a_50"] = box(features["a_red"], 11)
    return features


def _classifier_valid(before: AnnualComposite, after: AnnualComposite, params: ChangeParams) -> np.ndarray:
    return ((before.observations >= params.min_observations) & (after.observations >= params.min_observations)
            & before.dry_valid & after.dry_valid)


def load_change_model(model_dir: Path | str | None = None):
    """(booster, meta) de config/change_model, ou None se ainda nao foi treinado."""
    folder = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
    model_file, meta_file = folder / "model.txt", folder / "meta.json"
    if not (model_file.exists() and meta_file.exists()):
        return None
    import lightgbm as lgb

    return lgb.Booster(model_file=str(model_file)), json.loads(meta_file.read_text(encoding="utf-8"))


def predict_probability(booster, names: list[str], features: dict[str, np.ndarray], valid: np.ndarray,
                        chunk: int = 2_000_000) -> np.ndarray:
    """Probabilidade por pixel valido; zero fora da mascara de validade."""
    missing = [name for name in names if name not in features]
    if missing:
        raise ValueError(f"Atributos ausentes para o modelo: {missing}")
    height, width = valid.shape
    probability = np.zeros(height * width, dtype="float32")
    indices = np.flatnonzero(valid.ravel())
    flat = {name: features[name].ravel() for name in names}
    for start in range(0, len(indices), chunk):
        part = indices[start:start + chunk]
        probability[part] = booster.predict(np.stack([flat[name][part] for name in names], axis=1))
    return probability.reshape(height, width)


def train_change_model(bounds_ll, year_before: int, year_after: int, output_dir: Path | str | None = None, *,
                       params: ChangeParams | None = None, cache_dir: Path | None = None, progress=print) -> dict:
    """Treina o classificador contra o mapa de referencia e grava em config/change_model.

    Aprende na metade oeste da area; o limiar e escolhido por F1 (blocos de 200 m)
    na metade leste. O rotulo e a classe "construida" que surge entre os dois anos
    na referencia, entao o modelo herda os vieses dela.
    """
    import lightgbm as lgb

    params = params or ChangeParams()
    folder = Path(output_dir) if output_dir else DEFAULT_MODEL_DIR
    transform, width, height, epsg = target_grid(tuple(bounds_ll))
    before = annual_composite(tuple(bounds_ll), year_before, params, cache_dir=cache_dir, progress=progress)
    after = annual_composite(tuple(bounds_ll), year_after, params, cache_dir=cache_dir, progress=progress)
    features = build_features(before, after)
    names = list(features)
    valid = _classifier_valid(before, after, params)
    progress("  lendo referencia...")
    ref_before = read_reference(year_before, tuple(bounds_ll), transform, width, height, epsg)
    ref_after = read_reference(year_after, tuple(bounds_ll), transform, width, height, epsg)
    truth = (ref_after == REFERENCE_BUILT) & (ref_before != REFERENCE_BUILT)
    # Todos os pixels validos entram, inclusive a cidade ja consolidada como negativo:
    # no uso real nao ha mapa de referencia para excluir o que ja era construido, e um
    # modelo que nunca viu area urbana estavel a marca inteira como mudanca.
    candidate = valid
    columns = np.arange(width)[None, :].repeat(height, 0)
    fit_region, tune_region = columns < width // 2, columns >= width // 2

    rng = np.random.default_rng(0)
    positives = np.flatnonzero((candidate & truth & fit_region).ravel())
    negatives = np.flatnonzero((candidate & ~truth & fit_region).ravel())
    if len(positives) < 500:
        raise RuntimeError(f"Poucos exemplos positivos para treinar ({len(positives)}).")
    negatives = rng.choice(negatives, size=min(len(negatives), 8 * len(positives)), replace=False)
    rows = np.concatenate([positives, negatives])
    x = np.stack([features[name].ravel()[rows] for name in names], axis=1)
    y = np.r_[np.ones(len(positives)), np.zeros(len(negatives))]
    progress(f"  treinando com {len(positives)} positivos e {len(negatives)} negativos...")
    model = lgb.LGBMRegressor(objective="binary", n_estimators=300, learning_rate=0.05, num_leaves=31,
                              min_child_samples=200, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                              reg_lambda=5, verbosity=-1, n_jobs=4).fit(x, y)
    probability = predict_probability(model.booster_, names, features, valid)

    def score(threshold: float) -> dict:
        mask = remove_small_patches(probability >= threshold, params.min_patch_pixels) & tune_region
        detected = block_counts(mask, 20) >= 5
        reference = block_counts(truth & tune_region, 20) >= 9
        eligible = block_counts(valid & tune_region, 20) >= 200
        return agreement_metrics(detected, reference, eligible)

    scored = {threshold: score(threshold) for threshold in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)}
    threshold = max(scored, key=lambda key: scored[key]["f1"])
    folder.mkdir(parents=True, exist_ok=True)
    model.booster_.save_model(str(folder / "model.txt"))
    meta = {
        "version": "change-clf-v1",
        "features": names,
        "threshold": threshold,
        "min_patch_pixels": params.min_patch_pixels,
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "trained_on": {"bounds": list(bounds_ll), "year_before": year_before, "year_after": year_after,
                       "positives": int(len(positives)), "negatives": int(len(negatives))},
        "reference": f"{REFERENCE_COLLECTION}, classe construida que surge entre os anos (licenca CC BY 4.0)",
        "tuning_half_metrics": scored[threshold],
        "tuning_half_threshold_scan": {str(key): value["f1"] for key, value in scored.items()},
    }
    (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def detect_change(bounds_ll, year_before: int, year_after: int, params: ChangeParams | None = None, *,
                  cache_dir: Path | None = None, model_dir: Path | str | None = None, progress=print) -> ChangeResult:
    """Compara as composicoes anuais e devolve as mascaras de conversao a 10 m."""
    params = params or ChangeParams()
    transform, _, _, epsg = target_grid(bounds_ll)
    before = annual_composite(bounds_ll, year_before, params, cache_dir=cache_dir, progress=progress)
    after = annual_composite(bounds_ll, year_after, params, cache_dir=cache_dir, progress=progress)
    valid = _classifier_valid(before, after, params)
    rule = annual_change(before.ndvi_max, before.observations, after.ndvi_max, after.observations, params)
    changed = rule["changed"] & valid
    probable, meta = None, None
    loaded = load_change_model(model_dir)
    if loaded is not None:
        booster, meta = loaded
        progress("  classificador: calculando atributos...")
        features = build_features(before, after)
        probability = predict_probability(booster, meta["features"], features, valid)
        probable = remove_small_patches(probability >= meta["threshold"], meta.get("min_patch_pixels", params.min_patch_pixels))
        del features
    return ChangeResult(changed, valid, transform, epsg, year_before, year_after,
                        {"before": before.sources, "after": after.sources}, probable, meta)


# ---------------------------------------------------------------------------
# Agregacao por celula H3 e persistencia
# ---------------------------------------------------------------------------

def rasterize_cells(cells: dict[str, object], transform, width: int, height: int) -> tuple[np.ndarray, list[str]]:
    """Raster de rotulos (1..n) com o poligono exato de cada celula, nao o retangulo."""
    from rasterio.features import rasterize

    ids = list(cells)
    labels = rasterize(
        [(cells[h3_id], index + 1) for index, h3_id in enumerate(ids)],
        out_shape=(height, width), transform=transform, fill=0, dtype="int32",
    )
    return labels, ids


def aggregate_to_cells(changed: np.ndarray, valid: np.ndarray, labels: np.ndarray, ids: list[str],
                       probable: np.ndarray | None = None):
    import pandas as pd

    size = len(ids) + 1
    total = np.bincount(labels.ravel(), minlength=size)[1:]
    valid_px = np.bincount(labels.ravel(), weights=valid.ravel(), minlength=size)[1:]
    changed_px = np.bincount(labels.ravel(), weights=changed.ravel(), minlength=size)[1:]
    columns = {
        "h3_id": ids,
        "cell_area_ha": total * PIXEL_HA,
        "valid_area_ha": valid_px * PIXEL_HA,
        "changed_area_ha": changed_px * PIXEL_HA,
        "valid_fraction": np.where(total > 0, valid_px / np.maximum(total, 1), 0.0),
        "changed_fraction": np.where(valid_px > 0, changed_px / np.maximum(valid_px, 1), 0.0),
    }
    if probable is not None:
        probable_px = np.bincount(labels.ravel(), weights=probable.ravel(), minlength=size)[1:]
        columns["probable_area_ha"] = probable_px * PIXEL_HA
        columns["probable_fraction"] = np.where(valid_px > 0, probable_px / np.maximum(valid_px, 1), 0.0)
    frame = pd.DataFrame(columns)
    return frame.round({name: 5 if name.endswith("fraction") and name.startswith(("changed", "probable")) else 4
                        if name.endswith("fraction") else 2 for name in frame.columns if name != "h3_id"})


def ensure_change_schema(conn) -> None:
    from sqlalchemy import text

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS geo.urban_change_h3 (
            h3_id TEXT NOT NULL REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE,
            year_before INTEGER NOT NULL,
            year_after INTEGER NOT NULL,
            cell_area_ha DOUBLE PRECISION NOT NULL,
            valid_area_ha DOUBLE PRECISION NOT NULL,
            changed_area_ha DOUBLE PRECISION NOT NULL,
            valid_fraction DOUBLE PRECISION NOT NULL,
            changed_fraction DOUBLE PRECISION NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (h3_id, year_before, year_after)
        )
    """))
    # Nivel "provavel" (classificador); nulo quando nao ha modelo treinado.
    conn.execute(text("ALTER TABLE geo.urban_change_h3 ADD COLUMN IF NOT EXISTS probable_area_ha DOUBLE PRECISION"))
    conn.execute(text("ALTER TABLE geo.urban_change_h3 ADD COLUMN IF NOT EXISTS probable_fraction DOUBLE PRECISION"))


def _load_grid(settings):
    """Limite municipal (lon/lat) e poligonos das celulas em UTM."""
    import pandas as pd
    from pyproj import Transformer
    from shapely import wkt
    from shapely.ops import transform as shapely_transform

    from .db import db_engine

    with db_engine(settings) as engine:
        boundary = pd.read_sql("SELECT ST_AsText(ST_Union(geom)) AS wkt FROM geo.city_boundary", engine)
        grid = pd.read_sql("SELECT h3_id, ST_AsText(geom) AS wkt FROM geo.grid_h3", engine)
    if boundary.empty or not boundary.loc[0, "wkt"] or grid.empty:
        raise RuntimeError("Limite municipal ou grade H3 ausentes. Rode fetch-boundary e build-grid.")
    city = wkt.loads(boundary.loc[0, "wkt"])
    epsg = utm_epsg(city.centroid.x, city.centroid.y)
    project = Transformer.from_crs(4326, epsg, always_xy=True).transform
    cells = {row.h3_id: shapely_transform(project, wkt.loads(row.wkt)) for row in grid.itertuples()}
    return city, shapely_transform(project, city), cells


def run_change_detection(year_before: int, year_after: int, *, settings=None, params: ChangeParams | None = None,
                         output_dir: str | None = None, validate: bool = False, progress=print) -> dict[str, object]:
    """Detecta mudanca no municipio inteiro, agrega por H3 e grava em geo.urban_change_h3."""
    from sqlalchemy import text

    from .config import load_settings
    from .data_registry import record_data_source
    from .db import db_engine

    settings = settings or load_settings()
    params = params or ChangeParams()
    city_ll, city_utm, cells = _load_grid(settings)
    cache_dir = Path(output_dir) / "cache" if output_dir else None
    result = detect_change(city_ll.bounds, year_before, year_after, params, cache_dir=cache_dir, progress=progress)
    height, width = result.changed.shape
    labels, ids = rasterize_cells(cells, result.transform, width, height)
    frame = aggregate_to_cells(result.changed, result.valid, labels, ids, result.probable)
    has_probable = result.probable is not None

    with db_engine(settings) as engine, engine.begin() as conn:
        ensure_change_schema(conn)
        conn.execute(text("DELETE FROM geo.urban_change_h3 WHERE year_before = :b AND year_after = :a"),
                     {"b": year_before, "a": year_after})
        for row in frame.to_dict(orient="records"):
            row.setdefault("probable_area_ha", None)
            row.setdefault("probable_fraction", None)
            conn.execute(text("""
                INSERT INTO geo.urban_change_h3
                (h3_id, year_before, year_after, cell_area_ha, valid_area_ha, changed_area_ha,
                 valid_fraction, changed_fraction, probable_area_ha, probable_fraction, updated_at)
                VALUES (:h3_id, :b, :a, :cell_area_ha, :valid_area_ha, :changed_area_ha,
                        :valid_fraction, :changed_fraction, :probable_area_ha, :probable_fraction, now())
            """), {**row, "b": year_before, "a": year_after})

    inside = labels > 0
    summary: dict[str, object] = {
        "year_before": year_before,
        "year_after": year_after,
        "resolution_m": RESOLUTION_M,
        "cells": int(len(frame)),
        "cells_with_change": int((frame["changed_area_ha"] > 0).sum()),
        "changed_area_ha": round(float(result.changed[inside].sum() * PIXEL_HA), 2),
        "cells_with_probable": int((frame["probable_area_ha"] > 0).sum()) if has_probable else None,
        "probable_area_ha": round(float(result.probable[inside].sum() * PIXEL_HA), 2) if has_probable else None,
        "classifier": result.model_meta and {key: result.model_meta[key] for key in ("version", "threshold", "trained_at")},
        "valid_pct": round(float(result.valid[inside].mean() * 100), 2),
        "params": asdict(params),
        "sources": result.sources,
    }
    if output_dir:
        summary["outputs"] = write_outputs(result, Path(output_dir))
    if validate:
        summary["validation"] = validate_against_reference(result, labels > 0, progress=progress)
    record_data_source(
        "urban_change", "Sentinel-2 L2A Collection 1 (Earth Search)", source_uri=STAC_URL,
        reference_date=date.fromisoformat(max(item["date"] for item in result.sources["after"])),
        row_count=len(frame), details={k: v for k, v in summary.items() if k != "outputs"},
        license_name="Copernicus Sentinel data (uso livre com atribuicao)", schema_version="urban-change-v3-regra-e-classificador",
        settings=settings,
    )
    return summary


def write_outputs(result: ChangeResult, output_dir: Path) -> dict[str, str]:
    """Grava a mascara em GeoTIFF para inspecao em SIG."""
    import rasterio

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"mudanca_{result.year_before}_{result.year_after}.tif"
    # 0 sem mudanca, 1 provavel (classificador), 2 alta confianca (regra), 255 sem observacao valida.
    level = result.changed.astype("uint8") * 2
    if result.probable is not None:
        level = np.where(result.changed, 2, result.probable.astype("uint8"))
    data = np.where(result.valid, level, 255).astype("uint8")
    with rasterio.open(target, "w", driver="GTiff", height=data.shape[0], width=data.shape[1], count=1,
                       dtype="uint8", crs=f"EPSG:{result.epsg}", transform=result.transform,
                       nodata=255, compress="deflate") as dst:
        dst.write(data, 1)
    meta = output_dir / f"mudanca_{result.year_before}_{result.year_after}.json"
    meta.write_text(json.dumps({"generated_at": datetime.utcnow().isoformat() + "Z", "sources": result.sources},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    return {"geotiff": str(target), "metadata": str(meta)}


# ---------------------------------------------------------------------------
# Validacao contra mapa anual de cobertura independente
# ---------------------------------------------------------------------------

def read_reference(year: int, bounds_ll, transform, width: int, height: int, epsg: int) -> np.ndarray:
    """Mapa anual de cobertura a 10 m (Impact Observatory) na grade da deteccao."""
    import rasterio
    import requests
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT

    response = requests.post(f"{PLANETARY_STAC}/search", json={
        "collections": [REFERENCE_COLLECTION], "bbox": list(bounds_ll),
        "datetime": f"{year}-06-01T00:00:00Z", "limit": 10,
    }, timeout=60)
    response.raise_for_status()
    items = response.json().get("features", [])
    if not items:
        raise RuntimeError(f"Mapa de referencia indisponivel para {year} (serie cobre 2017-2023).")
    mosaic = np.zeros((height, width), dtype="uint8")
    with rasterio.Env(**_GDAL_ENV):
        for item in items:
            signed = requests.get(PLANETARY_SIGN, params={"href": item["assets"]["data"]["href"]}, timeout=60)
            signed.raise_for_status()
            with rasterio.open(signed.json()["href"]) as source:
                with WarpedVRT(source, crs=f"EPSG:{epsg}", transform=transform, width=width, height=height,
                               resampling=Resampling.nearest) as vrt:
                    data = vrt.read(1)
            mosaic = np.where(mosaic == 0, data, mosaic)
    return mosaic


def bounds_of(result: ChangeResult) -> tuple[float, float, float, float]:
    from pyproj import Transformer

    height, width = result.changed.shape
    to_ll = Transformer.from_crs(result.epsg, 4326, always_xy=True)
    xmin, ymax = result.transform.c, result.transform.f
    xs, ys = zip(*[to_ll.transform(x, y) for x in (xmin, xmin + width * RESOLUTION_M)
                   for y in (ymax, ymax - height * RESOLUTION_M)])
    return min(xs), min(ys), max(xs), max(ys)


def validate_against_reference(result: ChangeResult, inside: np.ndarray | None = None, *, block_m: int = 200,
                               min_detected_px: int = 5, min_truth_px: int = 9, progress=print) -> dict[str, object]:
    """Compara a deteccao com a area que virou "construida" no mapa de referencia.

    A comparacao e por blocos (200 m por padrao). A referencia tambem erra e so
    marca area construida consolidada, entao os numeros sao um piso de qualidade,
    nao uma medida de campo. So existe ate 2023.
    """
    height, width = result.changed.shape
    bounds = bounds_of(result)
    inside = np.ones((height, width), dtype=bool) if inside is None else inside
    progress(f"  lendo referencia {result.year_before} e {result.year_after}...")
    before = read_reference(result.year_before, bounds, result.transform, width, height, result.epsg)
    after = read_reference(result.year_after, bounds, result.transform, width, height, result.epsg)
    built_before = before == REFERENCE_BUILT
    new_built = (after == REFERENCE_BUILT) & ~built_before

    block = block_m // RESOLUTION_M
    truth_blocks = block_counts(new_built & inside, block) >= min_truth_px
    eligible = block_counts(result.valid & inside, block) >= (block * block) // 2

    def level_metrics(mask: np.ndarray) -> dict[str, object]:
        detected = mask & inside
        total = int(detected.sum())
        share = lambda ref: round(float((detected & ref).sum() / total), 3) if total else 0.0  # noqa: E731
        blocks = block_counts(detected, block) >= min_detected_px
        return {
            "blocks_detected": int((blocks & eligible).sum()),
            **agreement_metrics(blocks, truth_blocks, eligible),
            "detected_area_ha": round(total * PIXEL_HA, 2),
            # Partes que somam 1: construida antes (alarme falso grave), construcao nova segundo a
            # referencia, lavoura e pasto/campo no ano posterior, e o restante.
            "detected_area_by_reference_class": {
                "ja_construida_antes": share(built_before),
                "construida_nova": share(new_built),
                "lavoura": share(~built_before & ~new_built & (after == REFERENCE_CROPS)),
                "pasto_campo": share(~built_before & ~new_built & (after == REFERENCE_RANGELAND)),
                "outras": share(~built_before & ~new_built & ~np.isin(after, (REFERENCE_CROPS, REFERENCE_RANGELAND))),
            },
        }

    report = {
        "reference": f"Impact Observatory LULC anual 10 m, classe construida, {result.year_before}->{result.year_after}",
        "block_m": block_m,
        "blocks_evaluated": int(eligible.sum()),
        "blocks_new_built": int((truth_blocks & eligible).sum()),
        "reference_new_built_ha": round(float((new_built & inside).sum() * PIXEL_HA), 2),
        "high_confidence": level_metrics(result.changed),
    }
    if result.probable is not None:
        report["probable"] = level_metrics(result.probable | result.changed)
    return report


def validate_bounds(bounds_ll, year_before: int, year_after: int, *, params: ChangeParams | None = None,
                    cache_dir: str | None = None, progress=print) -> dict[str, object]:
    """Deteccao e validacao para um retangulo qualquer, sem depender do banco."""
    result = detect_change(tuple(bounds_ll), year_before, year_after, params,
                           cache_dir=Path(cache_dir) if cache_dir else None, progress=progress)
    return {
        "bounds": list(bounds_ll), "year_before": year_before, "year_after": year_after,
        "params": asdict(params or ChangeParams()),
        "dates": {period: [item["date"] for item in items] for period, items in result.sources.items()},
        "validation": validate_against_reference(result, progress=progress),
    }
