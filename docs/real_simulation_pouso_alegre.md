# Simulacao real - Pouso Alegre

Data da validacao: 2026-08-05

## Ambiente Docker

Servicos iniciados com `docker compose up -d --build`:

- PostGIS: saudavel em `localhost:5433`
- API: saudavel em `http://127.0.0.1:8001`
- Frontend: saudavel em `http://127.0.0.1`
- MLflow: saudavel em `http://127.0.0.1:5000`
- MinIO: ativo em `http://127.0.0.1:9000`
- pgAdmin: ativo em `http://127.0.0.1:5050`

## Carga de dados validada

Contagens no PostGIS:

- Celulas H3: 711
- Leituras Sentinel-2 importadas: 711
- Zonas carregadas: 22
- POIs carregados: 609

Endpoints testados:

- `/health`: 200
- `/api/scores`: 711 areas retornadas
- `/api/analytics/zoning-geojson`: 22 zonas
- `/api/analytics/pois-geojson`: 609 pontos
- `/api/indices/timeseries`: 711 registros apos importacao de `data/sentinel2_indices.csv`

## Resultado da simulacao

Classificacao geral das 711 areas:

- Prioridade alta: 0
- Prioridade media: 27
- Risco baixo: 112
- Risco medio: 505
- Risco alto: 94

Uso principal:

- Comercial: 395
- Residencial: 222
- Analise legal: 94

Top 5 areas por maior score geral na simulacao:

| H3 | Zona | Prioridade | Risco | Score residencial | Score comercial | NDVI 90d | NDBI 90d |
|---|---|---|---|---:|---:|---:|---:|
| 88a8aca163fffff | ZMV | media | baixo | 60.17 | 20.07 | 0.2600 | 0.0111 |
| 88a8aca14bfffff | ZMV | media | baixo | 58.55 | 20.82 | 0.1481 | 0.0583 |
| 88a8aca15dfffff | ZMV | media | baixo | 58.37 | 21.99 | 0.0998 | 0.1461 |
| 88a8aca143fffff | ZMV | media | baixo | 58.22 | 22.04 | 0.0880 | 0.1459 |
| 88a8aca109fffff | ZMV | media | baixo | 58.14 | 21.24 | 0.1218 | 0.1014 |

## Comparacao com fontes oficiais

O cadastro local da cidade usa o codigo IBGE `3152501`, que bate com a pagina oficial do IBGE para Pouso Alegre.

O projeto esta coerente ao tratar o Plano Diretor como regra central: a Lei Municipal 6.476/2021 define o Plano Diretor como instrumento basico da politica territorial e aplica-se a totalidade do territorio municipal. A lei tambem lista as classes de zoneamento urbano, incluindo ZER, ZM, ZEU, ZC, ZMV, ZEP, ZEEP, ZEPU, ZEIS, ZEPEC e ZEPAM.

A Prefeitura disponibiliza anexos vigentes do PDPA, incluindo Mapa 4 de Zoneamento Urbano, versao sobre satelite e Zoneamento Urbano em KML/KMZ. Isso confirma que a arquitetura do projeto deve priorizar a ingestao oficial desses anexos.

## O que bate

- Codigo IBGE da cidade.
- Existencia oficial do Plano Diretor vigente.
- Existencia oficial de mapas/anexos de zoneamento.
- Classes de zona usadas pelo sistema aparecem alinhadas com as classes previstas na lei.
- A decisao de bloquear/condicionar areas sem certeza legal faz sentido para uma ferramenta auditavel.

## O que ainda nao bate perfeitamente

- Muitas celulas ainda estao sem zona: 311 de 711. Isso reduz confianca e explica a grande quantidade de risco medio.
- A serie Sentinel-2 carregada possui apenas duas datas (`2025-03-01` e `2025-05-20`). Serve para demonstracao, mas ainda e curta para afirmar tendencia urbana com robustez.
- O score ficou conservador: nenhuma area entrou como prioridade alta. Isso pode ser correto, mas tambem pode indicar necessidade de calibrar pesos apos validar zoneamento oficial, populacao, renda e mercado.
- O endpoint de serie temporal ficou vazio antes da importacao manual dos indices. O pipeline completo deve incorporar essa importacao automaticamente.

## Recomendacoes tecnicas

1. Tornar obrigatoria a importacao do KML/KMZ oficial do zoneamento antes de qualquer apresentacao comercial.
2. Adicionar populacao, renda e setores censitarios do IBGE ao score.
3. Expandir Sentinel-2 para uma serie de pelo menos 12 a 24 meses.
4. Criar indicador de cobertura legal: percentual de celulas com zona conhecida.
5. Mostrar na interface um alerta quando a cidade ainda estiver com zoneamento parcial.
6. Automatizar a carga de `data/sentinel2_indices.csv` no pipeline Docker.

## Fontes consultadas

- IBGE Cidades: https://www.ibge.gov.br/cidades-e-estados/mg/pouso-alegre.html
- Prefeitura de Pouso Alegre - Plano Diretor: https://pousoalegre.mg.gov.br/pagina-site-submenu/87
- Lei Municipal 6.476/2021 compilada: https://www.legislador.com.br/legisladorweb.asp?ID=122&WCI=LeiTexto&aaLei=2021&inEspecieLei=1&nrLei=6476
