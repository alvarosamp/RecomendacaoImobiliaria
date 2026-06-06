# Roadmap

## Fase 1 - Base funcional

- Corrigir schemas Postgres/PostGIS.
- Subir PostGIS via Docker.
- Criar grid H3 do municipio.
- Carregar POIs e zoneamento.
- Calcular score heuristico explicavel.
- Exibir ranking em Streamlit.

## Fase 2 - Sensoriamento remoto

- Automatizar coleta Sentinel-2.
- Persistir NDVI/NDBI por H3 e data.
- Detectar areas com perda de vegetacao e aumento de area construida.
- Validar visualmente vetores de crescimento urbano.

## Fase 3 - ML imobiliario

- Coletar anuncios historicos.
- Treinar modelo de preco atual.
- Treinar modelo de valorizacao temporal.
- Medir erro por bairro/faixa de preco.

## Fase 4 - Plano Diretor com IA

- Ingerir Plano Diretor e leis urbanisticas.
- Implementar busca semantica/RAG.
- Mostrar artigos citados nas recomendacoes.
