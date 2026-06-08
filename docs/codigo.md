# Explicacao do codigo

Este documento explica como o projeto esta organizado e como as partes conversam entre si.

## Ideia central

O sistema transforma dados urbanos em recomendacoes explicaveis. A unidade principal de analise e a celula H3. Para cada H3, o projeto calcula indicadores, cruza restricoes urbanisticas e gera scores para uso residencial e comercial.

Fluxo resumido:

```text
OSM / NDVI / Plano Diretor / anuncios
        |
        v
PostGIS: geo.grid_h3, geo.osm_pois, geo.indices, geo.features
        |
        v
Scoring explicavel: geo.scores + explain_json
        |
        v
Streamlit / ML de preco / relatorios
```

## Modulos Python

### `config.py`

Le variaveis de ambiente e centraliza configuracoes:

- host/porta/nome do Postgres;
- usuario e senha;
- cidade alvo;
- latitude/longitude;
- resolucao H3.

Funcao principal:

- `load_settings()`: devolve um objeto `Settings`.

### `db.py`

Cria conexoes SQLAlchemy com o PostGIS.

Funcoes principais:

- `make_engine()`: cria engine do banco;
- `db_engine()`: abre e fecha a engine com seguranca.

### `geospatial.py`

Cuida do pipeline geoespacial baseado em OpenStreetMap, H3 e PostGIS.

Funcoes principais:

- `fetch_city_boundary()`: busca o limite municipal pelo OSMnx e grava em `geo.city_boundary`;
- `build_h3_grid()`: gera celulas H3 dentro do limite municipal e grava em `geo.grid_h3`;
- `fetch_osm_pois()`: busca POIs como escolas, farmacias, mercados e clinicas;
- `build_features()`: calcula contagens e distancias minimas por H3;
- `score_database()`: roda o scoring para todas as features;
- `run_mvp_pipeline()`: executa o pipeline basico de uma vez.

### `remote_sensing.py`

Transforma series NDVI/NDBI em features para o score.

Entrada esperada em CSV:

```csv
h3_id,date,ndvi,ndbi,bai,cloud_pct
demo-norte-01,2025-01-01,0.54,0.12,,8
```

Funcoes principais:

- `import_indices_csv()`: importa CSV para `geo.indices`;
- `compute_index_features()`: calcula media dos ultimos 90 dias e slope dos ultimos 180 dias;
- `update_remote_sensing_features()`: grava essas features em `geo.features`;
- `write_sample_indices_csv()`: gera um CSV de exemplo.

Como interpretar:

- `ndvi_mean_90` alto sugere mais vegetacao/qualidade ambiental;
- `ndvi_slope_180` negativo pode indicar perda de vegetacao;
- `ndbi_mean_90` alto sugere area mais construida;
- `ndbi_slope_180` positivo pode indicar adensamento/crescimento urbano.

### `scoring.py`

E o nucleo de decisao explicavel.

Entrada:

- features ambientais;
- distancias ate servicos;
- contagem de POIs;
- restricoes de zoneamento.

Saida:

- `score_residencial`;
- `score_comercial`;
- `explain`, um dicionario com fatores e recomendacoes.

Regras atuais:

- se o zoneamento veta o uso, o score daquele uso vira zero;
- carencia comercial aumenta quando ha poucos mercados/farmacias/escolas;
- crescimento urbano aumenta com NDBI subindo e NDVI caindo;
- residencial valoriza qualidade ambiental, acesso e crescimento moderado.

### `plan_director.py`

Le `config/plan_director_pouso_alegre.json` e avalia se uma zona permite, condiciona ou bloqueia um uso.

Funcoes principais:

- `evaluate_plan_compatibility()`: recebe zona e uso, devolve status legal e multiplicador do score;
- `normalize_zone()`: normaliza nomes e codigos de zonas;
- `normalize_use()`: transforma usos como mercado/farmacia em categorias urbanisticas.

### `decision.py`

Cria uma camada de inteligencia de decisao em cima dos scores.

Funcao principal:

- `enrich_opportunities()`: adiciona prioridade, uso principal, risco e resumo textual.

Campos adicionados:

- `priority`: `alta`, `media`, `baixa` ou `investigar`;
- `primary_use`: `residencial` ou `comercial`;
- `risk_level`: `baixo`, `medio` ou `alto`;
- `summary`: frase curta para o analista entender a oportunidade.

### `ml.py`

Treina um modelo inicial de preco de imoveis com Random Forest.

Entrada:

- CSV com coluna `price`;
- atributos do imovel;
- bairro/zona;
- scores e features urbanas quando existirem.

Comando:

```powershell
python -m recomendacao_imobiliaria.cli train-price --csv data/sample_properties.csv
```

Saida:

- modelo salvo em `models/price_model.joblib`;
- metricas `mae` e `r2`.

Tambem permite aplicar o modelo treinado:

```powershell
python -m recomendacao_imobiliaria.cli predict-price --csv data/sample_properties.csv
```

### `reporting.py`

Prepara dados para dashboard e relatorios.

Funcoes principais:

- `load_score_table()`: le scores, features e centroides H3 do PostGIS;
- `explain_to_text()`: transforma `explain_json` em texto curto.
- tambem aplica `decision.enrich_opportunities()` para alimentar o dashboard.

### `demo_data.py`

Contem dados falsos para testar o scoring sem banco, internet ou Docker.

### `cli.py`

Expoe comandos de terminal.

Comandos principais:

```powershell
python -m recomendacao_imobiliaria.cli score-demo
python -m recomendacao_imobiliaria.cli fetch-boundary
python -m recomendacao_imobiliaria.cli build-grid
python -m recomendacao_imobiliaria.cli fetch-pois
python -m recomendacao_imobiliaria.cli build-features
python -m recomendacao_imobiliaria.cli import-indices --csv data/sample_indices.csv
python -m recomendacao_imobiliaria.cli update-index-features
python -m recomendacao_imobiliaria.cli score-db
python -m recomendacao_imobiliaria.cli train-price --csv data/sample_properties.csv
python -m recomendacao_imobiliaria.cli predict-price --csv data/sample_properties.csv
```

## Frontend

O front principal fica em `app/streamlit_app.py`.

Ele tem cinco abas:

1. Oportunidades: ranking, prioridade, risco e resumo.
2. Mapa: pontos das celulas H3 quando o PostGIS possui geometria.
3. Explicacao: detalhes do score e `explain_json`.
4. Preco ML: usa um modelo treinado para prever precos em CSV.
5. Pipeline: mostra os comandos para rodar a base real.

O front tenta usar PostGIS quando selecionado. Se falhar, a fonte `Demo` continua funcionando para desenvolvimento.

## Banco de dados

### `geo.indices`

Guarda series temporais NDVI/NDBI por H3.

### `geo.features`

Guarda features consolidadas:

- contagens de POIs;
- distancias ate servicos;
- medias e tendencias NDVI/NDBI.

### `geo.scores`

Guarda o resultado do scoring:

- score residencial;
- score comercial;
- `explain_json`.

## Como a IA entra

Hoje existem duas camadas:

1. IA explicavel por regras: `scoring.py`.
2. ML supervisionado de preco: `ml.py`.

O proximo salto de IA sera:

- automatizar coleta NDVI/NDBI;
- treinar valorizacao temporal;
- criar RAG do Plano Diretor;
- adicionar explicabilidade do modelo de preco.
