# Recomendacao Imobiliaria

Ferramenta de inteligencia territorial para apoiar decisoes de investimento imobiliario, crescimento urbano e implantacao de estabelecimentos.

O projeto usa dados geoespaciais, sensoriamento remoto, regras urbanisticas e modelos explicaveis para responder perguntas como:

- Onde existem regioes promissoras para investimento imobiliario?
- Quais areas tendem a valorizar?
- Para qual lado a cidade esta crescendo?
- O Plano Diretor permite ou restringe determinado uso?
- Qual bairro tem carencia de mercado, farmacia, escola, academia ou outro servico?

## Visao do produto

A ferramenta deve gerar recomendacoes com justificativa. A saida ideal nao e apenas um score, mas uma explicacao:

> Esta area tem potencial para comercio de bairro porque apresenta crescimento urbano recente, baixa oferta de farmacias, boa acessibilidade e zoneamento compativel.

## Objetivos

1. Indicar possiveis locais de investimento imobiliario.
2. Estimar preco e valorizacao de imoveis com machine learning.
3. Detectar vetores de crescimento urbano com NDVI/NDBI e outros sinais.
4. Cruzar recomendacoes com Plano Diretor, zoneamento e restricoes.
5. Sugerir estabelecimentos por bairro ou celula H3 com explicacao do motivo.

## Estado atual

Este repositorio agora esta organizado como uma base de MVP:

- `Infra/`: PostGIS, pgAdmin, MinIO e scripts SQL de inicializacao.
- `src/recomendacao_imobiliaria/`: codigo Python do dominio e scoring explicavel.
- `app/streamlit_app.py`: prototipo Streamlit com dados demonstrativos.
- `config/.env.example`: exemplo de configuracao local.
- `docs/`: arquitetura, modelo de dados e roadmap.
- `AcompanhametoNDVI.ipynb`: notebook exploratorio de NDVI com Google Earth Engine.

## Como rodar

### 1. Instalar dependencias

Com Poetry:

```powershell
poetry install
```

Ou com `requirements.txt`:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Configurar variaveis

Copie o exemplo:

```powershell
Copy-Item config/.env.example config/.env.local
```

Edite `config/.env.local` se precisar mudar banco, cidade ou resolucao H3.

### 3. Subir infraestrutura

```powershell
docker compose -f Infra/docker-compose.yml up -d
```

Servicos:

- PostGIS: `localhost:5432`
- pgAdmin: `http://localhost:5050`
- MinIO console: `http://localhost:9001`

### 4. Testar scoring demonstrativo

```powershell
poetry run imobiliaria-score-demo
```

Com pip/venv:

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli score-demo
```

### 5. Abrir prototipo Streamlit

```powershell
poetry run streamlit run app/streamlit_app.py
```

Com pip/venv:

```powershell
$env:PYTHONPATH='src'
streamlit run app/streamlit_app.py
```

## Pipeline MVP com dados reais

Depois de subir o PostGIS, rode os comandos em ordem:

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli fetch-boundary
python -m recomendacao_imobiliaria.cli build-grid
python -m recomendacao_imobiliaria.cli fetch-pois
python -m recomendacao_imobiliaria.cli build-features
python -m recomendacao_imobiliaria.cli score-db
```

Ou tudo de uma vez:

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli run-mvp
```

Esses comandos fazem:

- buscar o limite municipal via OSMnx;
- gerar celulas H3 dentro do municipio;
- buscar POIs do OpenStreetMap;
- calcular carencia e acessibilidade;
- salvar scores explicaveis em `geo.scores`.

Observacao: os comandos `fetch-boundary` e `fetch-pois` precisam de internet, pois consultam dados do OpenStreetMap.

## Modelo inicial de preco com ML

Quando houver um CSV de anuncios/imoveis, o projeto ja tem um treinador inicial:

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli train-price --csv data/imoveis.csv
```

Para testar o fluxo com dados artificiais:

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli train-price --csv data/sample_properties.csv
```

O CSV deve ter uma coluna `price`. As colunas abaixo sao usadas quando existirem:

- numericas: `area_m2`, `bedrooms`, `bathrooms`, `parking_spaces`, `latitude`, `longitude`, `score_residencial`, `score_comercial`, `ndvi_mean_90`, `ndbi_mean_90`, distancias a servicos;
- categoricas: `property_type`, `neighborhood`, `zona`.

O modelo salvo fica, por padrao, em `models/price_model.joblib`.

## Modelo conceitual

O sistema trabalha com celulas H3 como unidade de analise. Para cada celula, a ferramenta calcula:

- indices ambientais e urbanos: NDVI, NDBI, slopes temporais;
- acessibilidade: distancia ate mercado, farmacia, escola etc.;
- carencia comercial: baixa oferta de servicos;
- conformidade urbanistica: uso permitido, condicionado ou vetado;
- score residencial e comercial;
- `explain_json`: justificativa auditavel.

## IA e ML

No MVP, o scoring e heuristico e explicavel. Isso e importante porque permite validar a logica com especialistas antes de treinar modelos mais complexos.

Depois, com dados historicos, o projeto pode evoluir para:

- modelo de preco atual de imoveis;
- modelo de valorizacao futura;
- deteccao automatica de crescimento urbano;
- RAG sobre Plano Diretor e leis urbanisticas;
- explicabilidade com SHAP ou decomposicao de fatores.

## Banco de dados

As principais tabelas estao em `Infra/initdb`:

- `geo.city_boundary`
- `geo.grid_h3`
- `geo.osm_pois`
- `geo.indices`
- `geo.access`
- `geo.features`
- `geo.scores`
- `geo.zoning`
- `geo.overlays`
- `public.regs`

Veja tambem [docs/data_model.md](docs/data_model.md).

## Roadmap curto

1. Validar o pipeline OSM/H3 em Pouso Alegre.
2. Importar zoneamento/plano diretor real.
3. Transformar o notebook NDVI em pipeline.
4. Exibir mapa real no Streamlit.
5. Coletar anuncios imobiliarios para treinar e validar ML de preco.
6. Implementar RAG sobre Plano Diretor com artigos citados.

## Observacoes de seguranca

Nao comite credenciais reais. Use `config/.env.local` ou secrets do ambiente de deploy.
