# Roadmap

## Fase 1 - Base funcional

- [x] Corrigir schemas Postgres/PostGIS.
- [x] Subir PostGIS via Docker.
- [x] Criar comando para buscar limite municipal.
- [x] Criar comando para gerar grid H3 do municipio.
- [x] Criar comando para carregar POIs via OSMnx.
- [x] Calcular score heuristico explicavel.
- [x] Criar prototipo Streamlit.
- [x] Criar front com filtros, ranking, mapa e explicabilidade.
- [x] Criar camada de decisao com prioridade, risco e resumo.
- [x] Criar comando de predicao de preco com modelo treinado.
- [ ] Importar zoneamento real.
- [ ] Exibir mapa real em Streamlit.

## Fase 2 - Sensoriamento remoto

- Automatizar coleta Sentinel-2.
- Persistir NDVI/NDBI por H3 e data.
- Detectar areas com perda de vegetacao e aumento de area construida.
- Validar visualmente vetores de crescimento urbano.

## Fase 3 - ML imobiliario

- Coletar anuncios historicos.
- Usar `imobiliaria train-price --csv data/imoveis.csv` para treinar o modelo inicial.
- Treinar modelo de valorizacao temporal.
- Medir erro por bairro/faixa de preco.

## Fase 4 - Plano Diretor com IA

- Ingerir Plano Diretor e leis urbanisticas.
- Implementar busca semantica/RAG.
- Mostrar artigos citados nas recomendacoes.
