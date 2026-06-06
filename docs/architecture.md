# Arquitetura do MVP

## Objetivo

Construir uma ferramenta de inteligencia territorial que recomende areas para investimento imobiliario, crescimento urbano e implantacao de estabelecimentos, sempre com justificativa.

## Camadas

1. Dados brutos: Sentinel-2, OSM, IBGE, Plano Diretor, anuncios imobiliarios.
2. Banco geoespacial: Postgres/PostGIS com schemas `geo` e `public`.
3. Feature store: indicadores por celula H3, bairro ou lote.
4. Scoring e ML: regras explicaveis no MVP; modelos supervisionados quando houver historico confiavel.
5. UI/API: Streamlit no MVP; FastAPI quando a ferramenta virar servico.

## MVP recomendado

1. Gerar grid H3 para Pouso Alegre.
2. Carregar limite municipal, zoneamento e POIs.
3. Calcular features de acessibilidade e carencia.
4. Ingerir serie NDVI/NDBI para detectar crescimento.
5. Gerar scores residencial e comercial com `explain_json`.
6. Mostrar ranking e justificativas em Streamlit.

## Evolucao com IA

- ML de preco: regressao com anuncios, atributos do imovel, localizacao e features urbanas.
- ML de valorizacao: backtesting temporal com variacao historica de preco por regiao.
- RAG juridico: consulta ao Plano Diretor com artigos citados.
- Explainability: decomposicao do score e SHAP para modelos supervisionados.
