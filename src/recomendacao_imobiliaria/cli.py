from __future__ import annotations

import argparse
import json

from .demo_data import sample_areas
from .scoring import score_area


def score_demo() -> None:
    results = [score_area(area) for area in sample_areas()]
    payload = [
        {
            "h3_id": result.h3_id,
            "score_residencial": result.score_residencial,
            "score_comercial": result.score_comercial,
            "explain": result.explain,
        }
        for result in results
    ]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="imobiliaria")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- pipeline basico ---
    subparsers.add_parser("score-demo", help="Roda scoring com dados demonstrativos.")
    subparsers.add_parser("fetch-boundary", help="Busca limite municipal no OSM e salva no PostGIS.")
    subparsers.add_parser("build-grid", help="Gera grid H3 a partir do limite municipal.")
    subparsers.add_parser("fetch-pois", help="Busca POIs no OSM e salva no PostGIS.")
    subparsers.add_parser("build-features", help="Calcula features basicas de acessibilidade.")
    subparsers.add_parser("update-index-features", help="Atualiza features NDVI/NDBI a partir de geo.indices.")
    subparsers.add_parser("score-db", help="Calcula scores para as features do PostGIS.")
    subparsers.add_parser("run-mvp", help="Executa boundary, grid, POIs, features e scores.")

    # --- indices remotos ---
    indices_parser = subparsers.add_parser("import-indices", help="Importa CSV com NDVI/NDBI por H3.")
    indices_parser.add_argument("--csv", required=True, help="CSV com h3_id, date, ndvi, ndbi.")

    sample_indices_parser = subparsers.add_parser("write-sample-indices", help="Gera CSV exemplo de indices.")
    sample_indices_parser.add_argument("--path", default="data/sample_indices.csv")

    # --- ML de precos ---
    train_parser = subparsers.add_parser("train-price", help="Treina modelo inicial de preco.")
    train_parser.add_argument("--csv", required=True, help="CSV com anuncios/imoveis.")
    train_parser.add_argument("--model-path", default="models/price_model.joblib")
    train_parser.add_argument("--trials", type=int, default=50, help="Numero de trials Optuna para tuning.")
    train_parser.add_argument("--no-enrich", action="store_true", help="Nao enriquecer com PostGIS.")

    predict_parser = subparsers.add_parser("predict-price", help="Prediz precos usando modelo treinado.")
    predict_parser.add_argument("--csv", required=True, help="CSV com imoveis para prever.")
    predict_parser.add_argument("--model-path", default="models/price_model.joblib")
    predict_parser.add_argument("--output", default="data/processed/predicted_prices.csv")

    # --- Plano Diretor ---
    plan_parser = subparsers.add_parser("check-plan", help="Avalia compatibilidade de zona e uso.")
    plan_parser.add_argument("--zone", required=True, help="Codigo ou nome da zona.")
    plan_parser.add_argument("--use", required=True, help="Uso pretendido: residencial, comercial, etc.")

    # --- zoneamento oficial ---
    zoning_parser = subparsers.add_parser("import-zoning", help="Importa GeoJSON/Shapefile de zoneamento oficial.")
    zoning_parser.add_argument("--file", required=True, help="Caminho para GeoJSON ou Shapefile.")

    subparsers.add_parser("gen-sample-zoning", help="Gera GeoJSON de zoneamento de exemplo para testes.")

    # --- Sentinel-2 real ---
    sentinel_parser = subparsers.add_parser(
        "collect-sentinel2",
        help="Coleta NDVI/NDBI real via Sentinel-2 (Planetary Computer).",
    )
    sentinel_parser.add_argument("--start", help="Data inicial YYYY-MM-DD (padrao: 180 dias atras).")
    sentinel_parser.add_argument("--end", help="Data final YYYY-MM-DD (padrao: hoje).")
    sentinel_parser.add_argument("--output", default="data/sentinel2_indices.csv")
    sentinel_parser.add_argument("--max-cloud", type=float, default=30.0, help="Cobertura de nuvens maxima %%.")

    # --- anuncios reais via API ---
    ml_api_parser = subparsers.add_parser(
        "fetch-listings-ml",
        help="Busca anuncios reais de imoveis via API do Mercado Livre.",
    )
    ml_api_parser.add_argument("--query", default="Pouso Alegre MG", help="Consulta de busca.")
    ml_api_parser.add_argument("--max", type=int, default=200, help="Numero maximo de anuncios.")
    ml_api_parser.add_argument("--output", default="data/ml_listings.csv")
    ml_api_parser.add_argument("--token", default=None, help="OAuth access_token do Mercado Livre (ou defina ML_ACCESS_TOKEN).")

    subparsers.add_parser("fetch-ibge", help="Busca indicadores habitacionais do IBGE para Pouso Alegre.")

    # --- normalizacao de listings ---
    normalize_parser = subparsers.add_parser("normalize-listings", help="Normaliza CSV de portal para formato padrao.")
    normalize_parser.add_argument("--csv", required=True, help="CSV bruto de qualquer portal.")
    normalize_parser.add_argument("--output", default=None, help="CSV de saida (padrao: mesmo nome + _normalized).")

    subparsers.add_parser(
        "gen-listings",
        help="Gera CSV realista de imoveis para Pouso Alegre (para treinar o modelo sem dados reais).",
    )

    # --- RAG juridico ---
    subparsers.add_parser("build-rag-index", help="Indexa artigos do Plano Diretor para RAG juridico.")

    rag_parser = subparsers.add_parser("rag-query", help="Responde pergunta juridica sobre o Plano Diretor.")
    rag_parser.add_argument("--question", required=True, help="Pergunta em linguagem natural.")
    rag_parser.add_argument("--model", default="claude-haiku-4-5-20251001")

    args = parser.parse_args()

    # ---- score-demo ----
    if args.command == "score-demo":
        score_demo()
        return

    # ---- ML ----
    if args.command == "train-price":
        try:
            from .ml import train_price_model
        except ModuleNotFoundError as exc:
            _raise_missing_dependency(exc)
        result = train_price_model(
            args.csv,
            model_path=args.model_path,
            enrich=not args.no_enrich,
            n_trials=args.trials,
        )
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return

    if args.command == "predict-price":
        try:
            from .ml import predict_prices
        except ModuleNotFoundError as exc:
            _raise_missing_dependency(exc)
        result = predict_prices(args.csv, model_path=args.model_path, output_path=args.output)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return

    # ---- Plano Diretor ----
    if args.command == "check-plan":
        from .plan_director import evaluate_plan_compatibility
        result = evaluate_plan_compatibility(args.zone, args.use)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return

    # ---- zoneamento ----
    if args.command == "import-zoning":
        try:
            from .zoning_import import import_zoning_file
        except ModuleNotFoundError as exc:
            _raise_missing_dependency(exc)
        result = import_zoning_file(args.file)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return

    if args.command == "gen-sample-zoning":
        try:
            from .zoning_import import generate_sample_zoning_geojson
        except ModuleNotFoundError as exc:
            _raise_missing_dependency(exc)
        path = generate_sample_zoning_geojson()
        print(f"GeoJSON de zoneamento de exemplo criado em: {path}")
        return

    # ---- Sentinel-2 ----
    if args.command == "collect-sentinel2":
        try:
            from .satellite_collector import collect_for_grid
        except ModuleNotFoundError as exc:
            _raise_missing_dependency(exc)
        result = collect_for_grid(
            start_date=args.start,
            end_date=args.end,
            output_csv=args.output,
            max_cloud_pct=args.max_cloud,
        )
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return

    # ---- API de anuncios ----
    if args.command == "fetch-listings-ml":
        try:
            from .api_collector import fetch_ml_listings
        except ModuleNotFoundError as exc:
            _raise_missing_dependency(exc)
        result = fetch_ml_listings(city_query=args.query, max_results=args.max, output_csv=args.output, access_token=getattr(args, "token", None))
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return

    if args.command == "fetch-ibge":
        try:
            from .api_collector import fetch_ibge_housing_indicators
        except ModuleNotFoundError as exc:
            _raise_missing_dependency(exc)
        result = fetch_ibge_housing_indicators()
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return

    if args.command == "normalize-listings":
        from .listings_import import normalize_listings
        result = normalize_listings(args.csv, output_csv=args.output)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return

    if args.command == "gen-listings":
        from .listings_import import generate_realistic_listings
        path = generate_realistic_listings()
        print(f"CSV de imoveis gerado em: {path}")
        return

    # ---- RAG ----
    if args.command == "build-rag-index":
        try:
            from .rag_juridico import build_index
        except ModuleNotFoundError as exc:
            _raise_missing_dependency(exc)
        n = build_index()
        print(f"Indice RAG criado com {n} documentos.")
        return

    if args.command == "rag-query":
        try:
            from .rag_juridico import query
        except ModuleNotFoundError as exc:
            _raise_missing_dependency(exc)
        result = query(args.question, model=args.model)
        print(f"\nPERGUNTA: {result.question}\n")
        print(f"RESPOSTA:\n{result.answer}\n")
        print("FONTES:")
        for src in result.sources:
            print(f"  - {src['title']} ({src['lei']})")
        return

    # ---- indices remotos ----
    if args.command == "import-indices":
        try:
            from .remote_sensing import import_indices_csv
        except ModuleNotFoundError as exc:
            _raise_missing_dependency(exc)
        result = import_indices_csv(args.csv)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return

    if args.command == "write-sample-indices":
        try:
            from .remote_sensing import write_sample_indices_csv
        except ModuleNotFoundError as exc:
            _raise_missing_dependency(exc)
        path = write_sample_indices_csv(args.path)
        print(f"CSV exemplo criado em {path}.")
        return

    # ---- pipeline geoespacial ----
    try:
        from .geospatial import (
            build_features,
            build_h3_grid,
            fetch_city_boundary,
            fetch_osm_pois,
            run_mvp_pipeline,
            score_database,
        )
        from .remote_sensing import update_remote_sensing_features
    except ModuleNotFoundError as exc:
        _raise_missing_dependency(exc)

    if args.command == "fetch-boundary":
        fetch_city_boundary()
        print("Limite municipal salvo em geo.city_boundary.")
    elif args.command == "build-grid":
        count = build_h3_grid()
        print(f"Grid H3 gerado: {count} celulas.")
    elif args.command == "fetch-pois":
        count = fetch_osm_pois()
        print(f"POIs salvos: {count}.")
    elif args.command == "build-features":
        count = build_features()
        print(f"Features atualizadas: {count}.")
    elif args.command == "update-index-features":
        result = update_remote_sensing_features()
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
    elif args.command == "score-db":
        count = score_database()
        print(f"Scores atualizados: {count}.")
    elif args.command == "run-mvp":
        result = run_mvp_pipeline()
        print(json.dumps(result, ensure_ascii=False, indent=2))


def _raise_missing_dependency(exc: ModuleNotFoundError) -> None:
    package = exc.name or "dependencia"
    raise SystemExit(
        f"Dependencia ausente: {package}. Instale com: python -m pip install -r requirements.txt"
    ) from exc


if __name__ == "__main__":
    main()
