# Modelo de dados

## Tabelas principais

- `geo.city_boundary`: limite municipal.
- `geo.grid_h3`: grade H3 usada como unidade de analise.
- `geo.osm_pois`: pontos de interesse normalizados.
- `geo.indices`: series temporais NDVI/NDBI/BAI por H3.
- `geo.access`: metricas de distancia ate servicos.
- `geo.features`: indicadores consolidados por H3.
- `geo.scores`: scores residencial/comercial e explicacao em JSON.
- `geo.zoning`: zoneamento urbano.
- `geo.overlays`: restricoes e camadas especiais.
- `public.regs`: base textual do Plano Diretor e leis relacionadas.

## Principio

Tudo que entra no score deve ser auditavel. A ferramenta precisa armazenar tanto o resultado quanto os fatores que levaram a recomendacao.
