from __future__ import annotations

import json
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from recomendacao_imobiliaria.decision import enrich_opportunities
from recomendacao_imobiliaria.demo_data import sample_areas
from recomendacao_imobiliaria.ml import predict_prices
from recomendacao_imobiliaria.reporting import explain_to_text, load_score_table
from recomendacao_imobiliaria.scoring import score_area


st.set_page_config(page_title="Recomendacao Imobiliaria", layout="wide")


def main() -> None:
    st.title("Recomendacao Imobiliaria e Urbana")
    st.caption("Scores explicaveis para investimento, expansao urbana e implantacao de servicos.")

    source = st.sidebar.radio("Fonte de dados", ["Demo", "PostGIS"], horizontal=True)
    table, explain_lookup = load_dashboard_data(source)

    if table.empty:
        st.info("Nenhum score encontrado. Rode o pipeline antes de abrir o dashboard.")
        return

    filtered = sidebar_filters(table)
    render_kpis(filtered)

    tab_opportunities, tab_map, tab_explain, tab_price, tab_rag, tab_pipeline = st.tabs(
        ["Oportunidades", "Mapa H3", "Explicacao", "Preco ML", "RAG Juridico", "Pipeline"]
    )

    with tab_opportunities:
        render_opportunities(filtered)

    with tab_map:
        render_h3_map(filtered)

    with tab_explain:
        render_explain(filtered, explain_lookup)

    with tab_price:
        render_price_panel()

    with tab_rag:
        render_rag_panel()

    with tab_pipeline:
        render_pipeline_help()


@st.cache_data(show_spinner=False)
def load_dashboard_data(source: str) -> tuple[pd.DataFrame, dict[str, object]]:
    if source == "PostGIS":
        try:
            table = load_score_table()
            explain_lookup = dict(zip(table["h3_id"], table["explain_json"], strict=False))
            table["explicacao"] = table["explain_json"].apply(explain_to_text)
            return prepare_table(table), explain_lookup
        except Exception as exc:
            st.warning(f"Nao foi possivel ler o PostGIS. Usando demo. Detalhe: {exc}")

    table, explain_lookup = demo_table()
    return prepare_table(table), explain_lookup


def demo_table() -> tuple[pd.DataFrame, dict[str, object]]:
    results = [score_area(area) for area in sample_areas()]
    coordinates = {
        "demo-norte-01": (-22.205, -45.955),
        "demo-centro-01": (-22.230, -45.948),
        "demo-sul-01": (-22.255, -45.945),
    }
    rows = []
    explain_lookup = {}
    for result in results:
        lat, lon = coordinates[result.h3_id]
        explain_lookup[result.h3_id] = result.explain
        rows.append(
            {
                "h3_id": result.h3_id,
                "score_residencial": result.score_residencial,
                "score_comercial": result.score_comercial,
                "zona": result.explain["zoning"]["zona"],
                "ndvi_mean_90": result.explain["environmental_quality"],
                "ndvi_slope_180": None,
                "ndbi_mean_90": None,
                "ndbi_slope_180": None,
                "poi_supermarket_cnt": None,
                "poi_pharmacy_cnt": None,
                "poi_school_cnt": None,
                "latitude": lat,
                "longitude": lon,
                "explain_json": result.explain,
                "explicacao": explain_to_text(result.explain),
                "legal_status": _legal_status(result.explain),
            }
        )
    return pd.DataFrame(rows), explain_lookup


def prepare_table(table: pd.DataFrame) -> pd.DataFrame:
    prepared = enrich_opportunities(table)
    for column in ["score_residencial", "score_comercial"]:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce").fillna(0)
    prepared["best_score"] = prepared[["score_residencial", "score_comercial"]].max(axis=1)
    return prepared.sort_values("best_score", ascending=False)


def sidebar_filters(table: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filtros")
    min_score = st.sidebar.slider("Score minimo", 0, 100, 0, 5)

    priorities = sorted([value for value in table.get("priority", pd.Series(dtype=str)).dropna().unique()])
    selected_priorities = st.sidebar.multiselect("Prioridade", priorities, default=priorities)

    uses = sorted([value for value in table.get("primary_use", pd.Series(dtype=str)).dropna().unique()])
    selected_uses = st.sidebar.multiselect("Uso principal", uses, default=uses)

    risks = sorted([value for value in table.get("risk_level", pd.Series(dtype=str)).dropna().unique()])
    selected_risks = st.sidebar.multiselect("Risco", risks, default=risks)

    filtered = table[table["best_score"] >= min_score].copy()
    if selected_priorities:
        filtered = filtered[filtered["priority"].isin(selected_priorities)]
    if selected_uses:
        filtered = filtered[filtered["primary_use"].isin(selected_uses)]
    if selected_risks:
        filtered = filtered[filtered["risk_level"].isin(selected_risks)]
    return filtered


def render_kpis(table: pd.DataFrame) -> None:
    cols = st.columns(5)
    cols[0].metric("Areas", len(table))
    cols[1].metric("Top residencial", _metric_max(table, "score_residencial"))
    cols[2].metric("Top comercial", _metric_max(table, "score_comercial"))
    cols[3].metric("Prioridade alta", int((table.get("priority") == "alta").sum()))
    cols[4].metric("Risco alto", int((table.get("risk_level") == "alto").sum()))


def render_opportunities(table: pd.DataFrame) -> None:
    st.subheader("Ranking de oportunidades")
    columns = [
        "h3_id",
        "priority",
        "primary_use",
        "risk_level",
        "legal_status",
        "best_score",
        "score_residencial",
        "score_comercial",
        "summary",
    ]
    st.dataframe(table[[c for c in columns if c in table.columns]], use_container_width=True, hide_index=True)

    if "primary_use" in table.columns:
        chart_data = table.groupby("primary_use", as_index=False)["best_score"].mean()
        st.bar_chart(chart_data, x="primary_use", y="best_score")


# ---------------------------------------------------------------------------
# Mapa H3 com Folium
# ---------------------------------------------------------------------------

_SCORE_COLORS = {
    "alta": "#1a9641",
    "media": "#fdae61",
    "baixa": "#d7191c",
    "investigar": "#7f7f7f",
}


def _score_to_color(score: float) -> str:
    if score >= 0.7:
        return "#1a9641"
    if score >= 0.45:
        return "#a6d96a"
    if score >= 0.25:
        return "#fdae61"
    return "#d7191c"


def _h3_polygon(h3_id: str) -> list[tuple[float, float]] | None:
    try:
        import h3
        boundary = h3.cell_to_boundary(h3_id)
        # h3 returns (lat, lon); folium expects [lat, lon]
        return [[lat, lon] for lat, lon in boundary]
    except Exception:
        return None


def _demo_polygon(lat: float, lon: float, size: float = 0.004) -> list[list[float]]:
    """Approximate hexagon-shaped polygon around a lat/lon for demo data."""
    import math
    pts = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        pts.append([lat + size * math.cos(angle), lon + size * math.sin(angle) * 0.7])
    pts.append(pts[0])
    return pts


def render_h3_map(table: pd.DataFrame) -> None:
    st.subheader("Mapa de calor H3 — polígonos por score")

    map_data = table.copy()
    if "latitude" in map_data.columns:
        map_data = map_data.dropna(subset=["latitude", "longitude"])

    if map_data.empty:
        st.info("Sem coordenadas para mapa.")
        return

    center_lat = float(map_data["latitude"].mean()) if "latitude" in map_data.columns else -22.23
    center_lon = float(map_data["longitude"].mean()) if "longitude" in map_data.columns else -45.95

    score_type = st.radio("Score para colorir", ["best_score", "score_residencial", "score_comercial"], horizontal=True)

    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="CartoDB positron")

    for _, row in map_data.iterrows():
        h3_id = str(row["h3_id"])
        score_val = float(row.get(score_type, row.get("best_score", 0)) or 0)
        color = _score_to_color(score_val)

        poly = _h3_polygon(h3_id)
        if poly is None:
            lat = row.get("latitude")
            lon = row.get("longitude")
            if lat is None or lon is None:
                continue
            poly = _demo_polygon(float(lat), float(lon))

        priority = str(row.get("priority", "—"))
        zona = str(row.get("zona", "—"))
        summary = str(row.get("summary", ""))

        popup_html = (
            f"<b>{h3_id}</b><br>"
            f"Score: <b>{score_val:.2f}</b><br>"
            f"Prioridade: {priority}<br>"
            f"Zona: {zona}<br>"
            f"{summary[:120]}"
        )

        folium.Polygon(
            locations=poly,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.55,
            weight=1.5,
            tooltip=f"{h3_id} | score={score_val:.2f} | {zona}",
            popup=folium.Popup(popup_html, max_width=280),
        ).add_to(fmap)

    # Legend
    legend_html = """
    <div style="position:fixed;bottom:40px;left:40px;z-index:1000;background:white;
                padding:10px;border-radius:6px;font-size:12px;border:1px solid #ccc;">
      <b>Score</b><br>
      <span style="color:#1a9641">&#9632;</span> &ge; 0.70 alto<br>
      <span style="color:#a6d96a">&#9632;</span> 0.45–0.70 medio<br>
      <span style="color:#fdae61">&#9632;</span> 0.25–0.45 baixo<br>
      <span style="color:#d7191c">&#9632;</span> &lt; 0.25 muito baixo
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(legend_html))

    st_folium(fmap, width="100%", height=520)

    st.dataframe(
        map_data[[c for c in ["h3_id", "zona", "best_score", "priority", "summary"] if c in map_data.columns]],
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------------------------
# Explicacao
# ---------------------------------------------------------------------------

def render_explain(table: pd.DataFrame, explain_lookup: dict[str, object]) -> None:
    st.subheader("Explicabilidade por area")
    selected = st.selectbox("Area", table["h3_id"].tolist())
    row = table[table["h3_id"] == selected].iloc[0]

    cols = st.columns(4)
    cols[0].metric("Score residencial", round(float(row["score_residencial"]), 2))
    cols[1].metric("Score comercial", round(float(row["score_comercial"]), 2))
    cols[2].metric("Prioridade", str(row.get("priority", "-")))
    cols[3].metric("Risco", str(row.get("risk_level", "-")))

    st.write(str(row.get("summary", "")))
    payload = explain_lookup.get(selected, {})
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {"raw": payload}

    # Show zoning articles if present
    zoning = payload.get("zoning", {}) if isinstance(payload, dict) else {}
    articles = zoning.get("articles", [])
    if articles:
        st.info("**Artigos aplicaveis:** " + " | ".join(articles))

    params = zoning.get("parameters", {})
    if params:
        st.caption("Parametros urbanisticos: " + " | ".join(f"{k}: {v}" for k, v in params.items()))

    legal_notes = zoning.get("legal_notes") or zoning.get("notes")
    if legal_notes:
        st.warning(str(legal_notes))

    st.json(payload)


# ---------------------------------------------------------------------------
# Preco ML
# ---------------------------------------------------------------------------

def render_price_panel() -> None:
    st.subheader("Predicao de preco")
    st.write("Use um modelo treinado para prever precos em um CSV de imoveis.")

    model_path = st.text_input("Modelo", "models/price_model.joblib")
    csv_path = st.text_input("CSV de entrada", "data/pouso_alegre_listings.csv")
    output_path = st.text_input("CSV de saida", "data/processed/predicted_prices.csv")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Predizer precos"):
            if not Path(model_path).exists():
                st.error("Modelo nao encontrado. Rode `train-price` primeiro.")
                return
            try:
                result = predict_prices(csv_path, model_path=model_path, output_path=output_path)
                st.success(f"Predicoes salvas em {result.output_path}. Linhas: {result.rows}.")
                st.dataframe(pd.read_csv(result.output_path), use_container_width=True, hide_index=True)
            except Exception as exc:
                st.error(f"Falha na predicao: {exc}")

    with col2:
        if st.button("Gerar CSV realista de imoveis"):
            try:
                from recomendacao_imobiliaria.listings_import import generate_realistic_listings
                path = generate_realistic_listings(n=500)
                st.success(f"CSV gerado: {path}")
            except Exception as exc:
                st.error(f"Erro: {exc}")


# ---------------------------------------------------------------------------
# RAG Juridico
# ---------------------------------------------------------------------------

def render_rag_panel() -> None:
    st.subheader("Consulta Juridica — Plano Diretor (RAG)")
    st.caption(
        "Faça perguntas em linguagem natural sobre a Lei 6476/2021. "
        "Requer `chromadb` e `anthropic` instalados, e variavel ANTHROPIC_API_KEY configurada."
    )

    question = st.text_input(
        "Pergunta",
        placeholder="Ex: Posso construir um predio de 10 andares na ZMC?",
    )

    model = st.selectbox(
        "Modelo Claude",
        ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-8"],
        index=0,
    )

    col_build, col_query = st.columns([1, 3])

    with col_build:
        if st.button("Reindexar artigos"):
            try:
                from recomendacao_imobiliaria.rag_juridico import build_index
                n = build_index()
                st.success(f"{n} artigos indexados.")
            except ImportError:
                st.error("Instale: pip install chromadb")
            except Exception as exc:
                st.error(f"Erro: {exc}")

    with col_query:
        if st.button("Perguntar", disabled=not question):
            if not question:
                st.warning("Digite uma pergunta.")
                return
            with st.spinner("Consultando..."):
                try:
                    from recomendacao_imobiliaria.rag_juridico import query
                    result = query(question, model=model)
                    st.markdown(f"**Resposta:**\n\n{result.answer}")
                    st.markdown("**Fontes consultadas:**")
                    for src in result.sources:
                        st.caption(f"• {src['title']} — Lei {src['lei']} — {src['chapter']}")
                except ImportError as exc:
                    st.error(f"Dependencia ausente: {exc}")
                except Exception as exc:
                    st.error(f"Erro: {exc}")

    with st.expander("Exemplos de perguntas"):
        st.markdown(
            """
- Qual o coeficiente de aproveitamento maximo na ZMV?
- Posso construir na Zona de Preservacao Ambiental?
- O que e necessario para parcelar terreno na ZEU?
- Quando e obrigatorio o Estudo de Impacto de Vizinhanca?
- Como funciona a Outorga Onerosa do Direito de Construir?
- Quais usos sao permitidos na ZEIS?
            """
        )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def render_pipeline_help() -> None:
    st.subheader("Comandos do pipeline")

    st.markdown("#### Pipeline basico")
    st.code(
        """
docker compose -f Infra/docker-compose.yml up -d
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli fetch-boundary
python -m recomendacao_imobiliaria.cli build-grid
python -m recomendacao_imobiliaria.cli fetch-pois
python -m recomendacao_imobiliaria.cli build-features
python -m recomendacao_imobiliaria.cli score-db
        """.strip(),
        language="powershell",
    )

    st.markdown("#### Zoneamento oficial")
    st.code(
        """
# Gerar GeoJSON de exemplo (para testes sem dado oficial)
python -m recomendacao_imobiliaria.cli gen-sample-zoning

# Importar zoneamento oficial (GeoJSON ou Shapefile)
python -m recomendacao_imobiliaria.cli import-zoning --file data/zoneamento_pouso_alegre.geojson
        """.strip(),
        language="powershell",
    )

    st.markdown("#### Sensoriamento remoto real (Sentinel-2)")
    st.code(
        """
# Instalar dependencias extras
pip install pystac-client planetary-computer stackstac rioxarray

# Coletar NDVI/NDBI dos ultimos 6 meses para todas as celulas H3
python -m recomendacao_imobiliaria.cli collect-sentinel2 --output data/sentinel2_indices.csv

# Ou usar CSV sintetico para testes
python -m recomendacao_imobiliaria.cli write-sample-indices --path data/sample_indices.csv
python -m recomendacao_imobiliaria.cli import-indices --csv data/sample_indices.csv
python -m recomendacao_imobiliaria.cli update-index-features
        """.strip(),
        language="powershell",
    )

    st.markdown("#### Anuncios reais via API")
    st.code(
        """
# Buscar anuncios do Mercado Livre (API publica, sem chave)
python -m recomendacao_imobiliaria.cli fetch-listings-ml --query "Pouso Alegre MG" --max 200

# Indicadores habitacionais do IBGE (gratuito)
python -m recomendacao_imobiliaria.cli fetch-ibge

# Normalizar CSV de qualquer portal (OLX, ZAP, VivaReal...)
python -m recomendacao_imobiliaria.cli normalize-listings --csv data/meu_export.csv

# Gerar dataset realista para treinar o modelo sem dados reais
python -m recomendacao_imobiliaria.cli gen-listings
        """.strip(),
        language="powershell",
    )

    st.markdown("#### Modelo de preco")
    st.code(
        """
python -m recomendacao_imobiliaria.cli gen-listings
python -m recomendacao_imobiliaria.cli train-price --csv data/pouso_alegre_listings.csv
python -m recomendacao_imobiliaria.cli predict-price --csv data/pouso_alegre_listings.csv
        """.strip(),
        language="powershell",
    )

    st.markdown("#### RAG Juridico (Plano Diretor)")
    st.code(
        """
pip install chromadb anthropic
$env:ANTHROPIC_API_KEY="sua-chave-aqui"

python -m recomendacao_imobiliaria.cli build-rag-index
python -m recomendacao_imobiliaria.cli rag-query --question "Posso construir na ZPA?"
        """.strip(),
        language="powershell",
    )

    st.markdown("#### Plano Diretor — verificacao de zona")
    st.code(
        """
python -m recomendacao_imobiliaria.cli check-plan --zone ZMC --use residencial
python -m recomendacao_imobiliaria.cli check-plan --zone ZEU --use comercial
python -m recomendacao_imobiliaria.cli check-plan --zone ZPA --use residencial
        """.strip(),
        language="powershell",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _metric_max(table: pd.DataFrame, column: str) -> float:
    if table.empty or column not in table.columns:
        return 0.0
    return round(float(table[column].max()), 2)


def _legal_status(explain: dict[str, object]) -> str:
    zoning = explain.get("zoning", {}) if isinstance(explain, dict) else {}
    statuses = {
        str(zoning.get("residential_plan_status", "allowed")),
        str(zoning.get("commercial_plan_status", "allowed")),
    }
    if "blocked" in statuses:
        return "bloqueado"
    if "conditioned" in statuses:
        return "condicionado"
    return "permitido"


if __name__ == "__main__":
    main()
