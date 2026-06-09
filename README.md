# Recomendação Imobiliária — Inteligência Territorial para Pouso Alegre

Plataforma de análise geoespacial para apoiar decisões de investimento imobiliário, crescimento urbano e implantação de estabelecimentos em Pouso Alegre, MG.

O sistema usa grade hexagonal H3, dados do OpenStreetMap, sensoriamento remoto Sentinel-2 e modelos de ML para responder:

- Onde estão as regiões mais promissoras para investimento?
- Para qual lado a cidade está crescendo?
- O Plano Diretor permite o uso que eu quero nessa área?
- Qual bairro tem carência de mercado, farmácia, escola?
- Quanto vale este imóvel?

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Stack                         │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────┐  │
│  │ Frontend │   │   API    │   │  MLflow  │   │ MinIO  │  │
│  │React+Vite│──▶│ FastAPI  │──▶│ tracking │   │ artefatos│ │
│  │  :80     │   │  :8000   │   │  :5000   │   │ :9000  │  │
│  └──────────┘   └────┬─────┘   └──────────┘   └────────┘  │
│                      │                                      │
│              ┌───────▼───────┐   ┌────────────┐            │
│              │  PostGIS :5433│   │  pgAdmin   │            │
│              │  ImobiliariaDB│   │   :5050    │            │
│              └───────────────┘   └────────────┘            │
└─────────────────────────────────────────────────────────────┘

Pipeline CLI (local → banco → modelo → API)
  OSM → H3 Grid → POIs → Features → Sentinel-2 → Scoring → LightGBM
```

### Principais tecnologias

| Camada | Tecnologia |
|---|---|
| Grade espacial | H3 resolução 8 (~711 células cobrindo Pouso Alegre) |
| Banco de dados | PostgreSQL 15 + PostGIS 3.5 |
| Sensoriamento remoto | Sentinel-2 L2A via Microsoft Planetary Computer (STAC) |
| Dados de POIs | OpenStreetMap via osmnx |
| ML de preços | LightGBM + Optuna (50 trials) + k-fold CV (5 folds) |
| MLOps | MLflow tracking + Model Registry |
| API | FastAPI + Pydantic |
| Frontend | React 18 + Vite + react-leaflet + h3-js |
| Infraestrutura | Docker Compose |

---

## Pré-requisitos

- Python 3.11+
- Docker Desktop rodando
- Git

---

## Início rápido — stack Docker completo

```powershell
git clone <url-do-repositorio>
cd RecomendacaoImobiliaria

# Copiar e revisar configurações
cp .env.example .env

# Subir todos os serviços
docker compose up -d
```

Serviços disponíveis:

| Serviço | URL | Credenciais padrão |
|---|---|---|
| Frontend (React) | http://localhost:80 | — |
| API (FastAPI) | http://localhost:8000 | — |
| API Docs | http://localhost:8000/docs | — |
| MLflow UI | http://localhost:5000 | — |
| PgAdmin | http://localhost:5050 | admin@local / admin |
| MinIO Console | http://localhost:9001 | gpminio / gpminio123 |
| PostgreSQL (host) | localhost:5433 | admin / admin123 |

> **Nota:** a porta do PostgreSQL no host é `5433` para não conflitar com uma instalação local na `5432`. Dentro da rede Docker, os containers se comunicam via `db:5432`.

---

## Desenvolvimento local (sem Docker)

### 1. Instalar dependências

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configurar ambiente

```powershell
cp .env.example .env
# Edite .env se necessário (banco local, porta, credenciais)
```

### 3. Definir PYTHONPATH

```powershell
$env:PYTHONPATH = 'src'
```

> Adicione ao perfil do PowerShell para não precisar repetir:
> ```powershell
> Add-Content $PROFILE "`n`$env:PYTHONPATH = 'src'"
> ```

### 4. Verificar instalação (sem banco)

```powershell
python -m recomendacao_imobiliaria.cli score-demo
```

Retorna JSON com scores e explicações para três células H3 de exemplo.

---

## Pipeline completo com dados reais

Execute em ordem — cada passo depende do anterior:

```powershell
$env:PYTHONPATH = 'src'

# 1. Limite do município via OpenStreetMap
python -m recomendacao_imobiliaria.cli fetch-boundary

# 2. Grade hexagonal H3 (res=8, ~711 células)
python -m recomendacao_imobiliaria.cli build-grid

# 3. POIs: mercados, farmácias, escolas, academias etc.
python -m recomendacao_imobiliaria.cli fetch-pois

# 4. Features de acessibilidade e carência por célula
python -m recomendacao_imobiliaria.cli build-features

# 5. Índices de vegetação/urbanização via Sentinel-2 (recomendado)
python -m recomendacao_imobiliaria.cli collect-sentinel2 \
    --start 2025-06-01 --end 2025-06-07 --max-cloud 20 \
    --output data/sentinel2_indices.csv

# 5b. Alternativa: índices sintéticos (sem internet)
python -m recomendacao_imobiliaria.cli write-sample-indices --path data/sample_indices.csv

# 6. Importar índices para o banco
python -m recomendacao_imobiliaria.cli import-indices --csv data/sentinel2_indices.csv

# 7. Calcular médias e tendências NDVI/NDBI por célula
python -m recomendacao_imobiliaria.cli update-index-features

# 8. Importar zoneamento do Plano Diretor
python -m recomendacao_imobiliaria.cli import-zoning --file data/sample_zoning.geojson

# 9. Calcular e persistir todos os scores
python -m recomendacao_imobiliaria.cli score-db
```

Atalho — tudo de uma vez:

```powershell
python -m recomendacao_imobiliaria.cli run-mvp
```

---

## Modelo de ML — preço de imóveis

### Coletar dados de imóveis

**Opção A — Gerar dataset sintético realista (sem internet):**
```powershell
python -m recomendacao_imobiliaria.cli gen-listings
# → data/pouso_alegre_listings.csv (500 imóveis)
```

**Opção B — Dados do IBGE (gratuito):**
```powershell
python -m recomendacao_imobiliaria.cli fetch-ibge
# → data/ibge_housing.csv
```

**Opção C — Anúncios do Mercado Livre (requer token OAuth gratuito):**
```powershell
# Crie um app em developers.mercadolibre.com.br e obtenha o access_token
$env:ML_ACCESS_TOKEN = 'SEU_TOKEN'
python -m recomendacao_imobiliaria.cli fetch-listings-ml --max 200
```

**Opção D — Normalizar CSV de qualquer portal (OLX, ZAP, VivaReal):**
```powershell
python -m recomendacao_imobiliaria.cli normalize-listings --csv data/meu_export.csv
```

### Treinar e usar o modelo

```powershell
# Treinar: LightGBM + Optuna (50 trials) + k-fold CV (5 folds)
# Enriquece automaticamente com features do PostGIS (NDVI, scores, zona)
python -m recomendacao_imobiliaria.cli train-price --csv data/pouso_alegre_listings.csv

# Prever preços
python -m recomendacao_imobiliaria.cli predict-price --csv data/pouso_alegre_listings.csv
# → data/processed/predicted_prices.csv
```

**Features usadas pelo modelo:**

| Tipo | Colunas |
|---|---|
| Numéricas | `area_m2`, `bedrooms`, `bathrooms`, `parking_spaces`, `latitude`, `longitude`, `score_residencial`, `score_comercial`, `ndvi_mean_90`, `ndvi_slope_180`, `ndbi_mean_90`, `ndbi_slope_180`, distâncias a serviços |
| Categóricas | `property_type`, `neighborhood`, `zona` |

O modelo salvo fica em `models/price_model.joblib` e é rastreado automaticamente no MLflow.

**Resultados obtidos com dataset de Pouso Alegre:**

| Métrica | Valor |
|---|---|
| CV MAE (5-fold) | R$ 104.461 ± R$ 7.675 |
| R² holdout | 0.694 |

---

## Plano Diretor e zoneamento

```powershell
# Verificar compatibilidade de uso por zona
python -m recomendacao_imobiliaria.cli check-plan --zone ZMC --use residencial
python -m recomendacao_imobiliaria.cli check-plan --zone ZEU --use comercial
python -m recomendacao_imobiliaria.cli check-plan --zone ZPA --use residencial

# Importar zoneamento real da prefeitura
# A coluna deve se chamar: zona, sigla, codigo ou cod_zona
python -m recomendacao_imobiliaria.cli import-zoning --file data/zoneamento_oficial.geojson
```

---

## RAG jurídico sobre o Plano Diretor (opcional)

Requer chave da API da Anthropic (Claude).

```powershell
pip install chromadb anthropic

$env:ANTHROPIC_API_KEY = 'sua-chave-aqui'

# Indexar artigos da Lei 6476/2021
python -m recomendacao_imobiliaria.cli build-rag-index

# Fazer consultas jurídicas
python -m recomendacao_imobiliaria.cli rag-query --question "Posso construir um prédio de 10 andares na ZMC?"
```

---

## Sentinel-2 via Planetary Computer

A coleta usa o [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/) — gratuito, sem cadastro.

O coletor agrupa as ~711 células H3 por tile MGRS (4–6 tiles), faz **uma única busca por tile** e extrai todos os valores via operações vetorizadas com `stackstac`. Isso reduz as chamadas à API de 711 para ~4–6.

**Índices calculados por célula H3:**
- `ndvi_mean_90` — média NDVI dos últimos 90 dias
- `ndvi_slope_180` — tendência NDVI dos últimos 180 dias (positivo = revegetação)
- `ndbi_mean_90` — média NDBI dos últimos 90 dias
- `ndbi_slope_180` — tendência NDBI (positivo = urbanização)

```powershell
# Instalar dependências extras (≈1 GB)
pip install pystac-client planetary-computer stackstac rioxarray

python -m recomendacao_imobiliaria.cli collect-sentinel2 \
    --start 2025-01-01 --end 2025-06-30 \
    --max-cloud 20 \
    --output data/sentinel2_indices.csv
```

---

## Estrutura do projeto

```
RecomendacaoImobiliaria/
├── .env                        # Configurações locais (não versionado)
├── .env.example                # Template de configuração
├── docker-compose.yml          # Stack completo (db, api, frontend, mlflow, minio)
├── Dockerfile                  # Imagem da API Python
├── mlflow.Dockerfile           # Imagem do MLflow
│
├── src/recomendacao_imobiliaria/
│   ├── cli.py                  # Todos os comandos CLI
│   ├── config.py               # Settings via .env
│   ├── db.py                   # Engine SQLAlchemy
│   ├── geospatial.py           # H3 grid, OSM, POIs
│   ├── satellite_collector.py  # Sentinel-2 via Planetary Computer
│   ├── scoring.py              # Scoring heurístico explicável
│   ├── ml.py                   # LightGBM + Optuna + MLflow
│   ├── plan_director.py        # Plano Diretor / zoneamento
│   ├── zoning_import.py        # Importação de GeoJSON de zoneamento
│   ├── rag_juridico.py         # RAG sobre legislação
│   ├── api_collector.py        # Coleta Mercado Livre
│   └── listings_import.py      # Normalização de CSV de imóveis
│
├── api/
│   ├── main.py                 # FastAPI app + CORS
│   └── routes/
│       ├── scores.py           # GET /api/scores
│       ├── predict.py          # POST /api/predict
│       └── mlops.py            # GET /api/mlops/runs
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # 4 abas: Mapa, Oportunidades, Preço, MLOps
│   │   ├── components/
│   │   │   ├── H3Map.jsx       # Mapa Leaflet com hexágonos coloridos
│   │   │   ├── OpportunitiesTable.jsx
│   │   │   ├── PricePanel.jsx  # Formulário de estimativa de preço
│   │   │   └── MlopsPanel.jsx  # Tabela de experimentos MLflow
│   │   └── api.js              # Calls para o backend
│   ├── nginx.conf              # Proxy /api → FastAPI
│   └── Dockerfile              # Multi-stage: node builder → nginx
│
├── Infra/
│   └── initdb/                 # Scripts SQL de criação do schema
│       ├── 001_schemas.sql     # Schemas e tabelas principais
│       ├── 002_schemas.sql     # Tabelas geo.*
│       ├── 003_zoning_regs.sql # Regulamentos de zoneamento
│       └── 010_views.sql       # Views analíticas
│
├── data/
│   ├── sentinel2_indices.csv   # Índices Sentinel-2 coletados
│   ├── pouso_alegre_listings.csv
│   └── processed/
│
├── models/
│   └── price_model.joblib      # Modelo treinado (não versionado)
│
├── config/
│   └── plan_director_pouso_alegre.json
│
├── docs/
│   ├── architecture.md
│   ├── data_model.md
│   ├── codigo.md
│   ├── plano_diretor.md
│   ├── pipeline.md
│   └── roadmap.md
│
├── tests/
└── app/
    └── streamlit_app.py        # Dashboard alternativo (Streamlit)
```

---

## Banco de dados — tabelas principais

Todas as tabelas ficam no schema `geo`:

| Tabela | Conteúdo |
|---|---|
| `geo.city_boundary` | Limite do município (PostGIS geometry) |
| `geo.grid_h3` | ~711 células hexagonais H3 res=8 |
| `geo.osm_pois` | POIs do OpenStreetMap com categoria |
| `geo.indices` | Séries temporais NDVI/NDBI por célula |
| `geo.features` | Features agregadas por célula (NDVI médio, distâncias, zona) |
| `geo.scores` | Score residencial/comercial + explain_json + risk_level |
| `geo.zoning` | Zoneamento do Plano Diretor (geometrias) |
| `public.regs` | Parâmetros urbanísticos (CA, TO, gabarito) por zona |

---

## API — endpoints

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/health` | Status da API |
| `GET` | `/api/scores` | Scores de todas as células H3 |
| `POST` | `/api/predict` | Estimar preço de um imóvel |
| `GET` | `/api/mlops/runs` | Últimas 10 execuções do MLflow |

**Exemplo — estimar preço:**

```bash
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "area_m2": 120,
    "bedrooms": 3,
    "bathrooms": 2,
    "parking_spaces": 1,
    "property_type": "apartamento",
    "latitude": -22.230278,
    "longitude": -45.948889
  }'
```

Documentação interativa: http://localhost:8000/docs

---

## Configuração via `.env`

```bash
# PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_DB=ImobiliariaDB
PG_USER=admin
PG_PASS=admin123

# Cidade
CITY_NAME=Pouso Alegre, Minas Gerais, Brazil
CITY_LAT=-22.230278
CITY_LON=-45.948889
H3_RES=8

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# API
MODEL_PATH=models/price_model.joblib

# MinIO
MINIO_ROOT_USER=gpminio
MINIO_ROOT_PASSWORD=gpminio123
```

> No ambiente Docker, a API usa `PG_HOST=db` automaticamente (sobrescreve o `.env`).

---

## Solução de problemas

| Problema | Solução |
|---|---|
| `ModuleNotFoundError: recomendacao_imobiliaria` | `$env:PYTHONPATH = 'src'` |
| Banco não conecta | `docker compose up -d` e aguarde 10s |
| `403` no Mercado Livre | API requer token OAuth — veja opção C acima |
| `chromadb not found` | `pip install chromadb anthropic` |
| `pystac_client not found` | `pip install pystac-client planetary-computer stackstac rioxarray` |
| Frontend retorna dados vazios | O banco Docker está vazio — rode o pipeline apontando para ele |
| `port is already allocated` (5432) | Postgres local já usa a porta; o Docker expõe na 5433 |

---

## Roadmap

- [ ] Popular banco Docker via pipeline automatizado no `docker compose up`
- [ ] Coletar anúncios reais de imóveis de Pouso Alegre
- [ ] Importar zoneamento oficial da Prefeitura (shapefile real)
- [ ] Série temporal Sentinel-2 completa (2 anos) para detectar vetor de crescimento
- [ ] SHAP values para explicabilidade do modelo de preço
- [ ] Notificações de alertas de oportunidade por e-mail/webhook
- [ ] Suporte a outras cidades (parametrizado via `.env`)

---

## Segurança

Nunca versione credenciais reais. O arquivo `.env` está no `.gitignore`. Use `.env.example` como referência e preencha o `.env` local com valores reais.
