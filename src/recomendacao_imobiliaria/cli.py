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

    subparsers.add_parser("score-demo", help="Roda scoring com dados demonstrativos.")
    subparsers.add_parser("fetch-boundary", help="Busca limite municipal no OSM e salva no PostGIS.")
    subparsers.add_parser("build-grid", help="Gera grid H3 a partir do limite municipal.")
    subparsers.add_parser("fetch-pois", help="Busca POIs no OSM e salva no PostGIS.")
    subparsers.add_parser("build-features", help="Calcula features basicas de acessibilidade.")
    subparsers.add_parser("score-db", help="Calcula scores para as features do PostGIS.")
    subparsers.add_parser("run-mvp", help="Executa boundary, grid, POIs, features e scores.")

    train_parser = subparsers.add_parser("train-price", help="Treina modelo inicial de preco.")
    train_parser.add_argument("--csv", required=True, help="CSV com anuncios/imoveis.")
    train_parser.add_argument("--model-path", default="models/price_model.joblib")

    args = parser.parse_args()

    if args.command == "score-demo":
        score_demo()
        return

    if args.command == "train-price":
        try:
            from .ml import train_price_model
        except ModuleNotFoundError as exc:
            _raise_missing_dependency(exc)

        result = train_price_model(args.csv, model_path=args.model_path)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return

    try:
        from .geospatial import (
            build_features,
            build_h3_grid,
            fetch_city_boundary,
            fetch_osm_pois,
            run_mvp_pipeline,
            score_database,
        )
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
