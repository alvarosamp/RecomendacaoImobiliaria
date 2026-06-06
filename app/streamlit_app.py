from __future__ import annotations

import pandas as pd
import streamlit as st

from recomendacao_imobiliaria.demo_data import sample_areas
from recomendacao_imobiliaria.scoring import score_area


st.set_page_config(page_title="Recomendacao Imobiliaria", layout="wide")

st.title("Recomendacao Imobiliaria e Urbana")

results = [score_area(area) for area in sample_areas()]
rows = [
    {
        "area": result.h3_id,
        "score_residencial": result.score_residencial,
        "score_comercial": result.score_comercial,
        "zona": result.explain["zoning"]["zona"],
        "sinal_crescimento": result.explain["growth_signal"],
        "carencia_comercial": result.explain["commercial_gap"],
        "acessibilidade": result.explain["mixed_access"],
    }
    for result in results
]

st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

selected = st.selectbox("Area", [result.h3_id for result in results])
result = next(item for item in results if item.h3_id == selected)

left, right = st.columns(2)
left.metric("Score residencial", result.score_residencial)
right.metric("Score comercial", result.score_comercial)

st.subheader("Explicacao")
st.json(result.explain)
