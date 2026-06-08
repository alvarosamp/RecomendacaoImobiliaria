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

## Passo a passo para rodar o projeto

### Requisitos

- Python 3.11 ou superior
- Docker Desktop instalado e rodando
- Git

---

### Passo 1 — Clonar e instalar dependencias

```powershell
git clone <url-do-repositorio>
cd RecomendacaoImobiliaria

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt
```

> Defina o PYTHONPATH antes de qualquer comando Python:
>
> ```powershell
> $env:PYTHONPATH = 'src'
> ```

---

### Passo 2 — Subir a infraestrutura (Docker)

```powershell
docker compose -f Infra/docker-compose.yml up -d
```

Aguarde alguns segundos. Servicos disponiveis:

| Servico | Endereco | Usuario / Senha padroes |
| ------- | -------- | ----------------------- |
| PostGIS | `localhost:5432` | `postgres` / `postgres` |
| pgAdmin | `http://localhost:5050` | `admin@admin.com` / `admin` |
| MinIO | `http://localhost:9001` | `minioadmin` / `minioadmin` |

Para verificar se o banco subiu:

```powershell
docker ps
```

---

### Passo 3 — Configurar variaveis de ambiente

```powershell
Copy-Item config/.env.example config/.env.local
```

O arquivo padrao ja funciona para o Docker local. So edite se mudar porta, usuario ou quiser usar outra cidade.

---

### Passo 4 — Testar sem banco (modo Demo)

Confirme que a instalacao esta correta rodando o scoring local com dados sinteticos:

```powershell
python -m recomendacao_imobiliaria.cli score-demo
```

Saida esperada: JSON com scores e explicacoes para tres celulas H3 de exemplo (norte, centro, sul).

---

### Passo 5 — Abrir o dashboard Streamlit

```powershell
streamlit run app/streamlit_app.py
```

Acesse `http://localhost:8501` no navegador.

- Selecione **Demo** na barra lateral para ver o dashboard sem banco.
- Explore as abas: **Oportunidades**, **Mapa H3**, **Explicacao**, **Preco ML**, **RAG Juridico**, **Pipeline**.

---

### Passo 6 — Rodar o pipeline com dados reais (PostGIS)

Execute em ordem — cada passo depende do anterior:

```powershell
# 6.1 Busca o limite do municipio de Pouso Alegre no OpenStreetMap
python -m recomendacao_imobiliaria.cli fetch-boundary

# 6.2 Gera o grid de hexagonos H3 dentro do municipio
python -m recomendacao_imobiliaria.cli build-grid

# 6.3 Busca mercados, farmacias, escolas etc. no OpenStreetMap
python -m recomendacao_imobiliaria.cli fetch-pois

# 6.4 Calcula acessibilidade e carencia para cada celula H3
python -m recomendacao_imobiliaria.cli build-features

# 6.5 Gera CSV de indices de vegetacao sinteticos (para teste)
python -m recomendacao_imobiliaria.cli write-sample-indices --path data/sample_indices.csv

# 6.6 Importa o CSV de indices para o banco
python -m recomendacao_imobiliaria.cli import-indices --csv data/sample_indices.csv

# 6.7 Calcula medias e tendencias NDVI/NDBI por celula
python -m recomendacao_imobiliaria.cli update-index-features

# 6.8 Calcula e salva todos os scores no PostGIS
python -m recomendacao_imobiliaria.cli score-db
```

Depois mude a fonte de dados para **PostGIS** no Streamlit para ver os dados reais.

> Atalho — tudo de uma vez:
>
> ```powershell
> python -m recomendacao_imobiliaria.cli run-mvp
> ```

---

### Passo 7 — Importar zoneamento oficial

```powershell
# Gera um GeoJSON de exemplo para testar o fluxo
python -m recomendacao_imobiliaria.cli gen-sample-zoning

# Importa para o PostGIS e faz o join com as celulas H3
python -m recomendacao_imobiliaria.cli import-zoning --file data/sample_zoning.geojson
```

Para usar o zoneamento oficial da prefeitura, substitua o arquivo `.geojson` pelo arquivo real.
A coluna deve se chamar `zona`, `sigla`, `codigo` ou `cod_zona`.

---

### Passo 8 — Verificar compatibilidade com o Plano Diretor

```powershell
# Consulta uma zona e uso especifico
python -m recomendacao_imobiliaria.cli check-plan --zone ZMC --use residencial
python -m recomendacao_imobiliaria.cli check-plan --zone ZEU --use comercial
python -m recomendacao_imobiliaria.cli check-plan --zone ZPA --use residencial
```

Retorna: status (allowed/conditioned/blocked), artigos aplicaveis, parametros urbanisticos (CA, TO, gabarito).

---

### Passo 9 — Coleta de dados de imoveis

**Opcao A — Gerar dataset sintetico realista (sem internet):**

```powershell
python -m recomendacao_imobiliaria.cli gen-listings
# Gera data/pouso_alegre_listings.csv com 500 imoveis
```

**Opcao B — Buscar dados reais do IBGE (gratuito, sem cadastro):**

```powershell
python -m recomendacao_imobiliaria.cli fetch-ibge
# Salva populacao, PIB per capita e dados municipais em data/ibge_housing.csv
```

**Opcao C — Buscar anuncios do Mercado Livre (requer token OAuth gratuito):**

1. Acesse [developers.mercadolibre.com.br](https://developers.mercadolibre.com.br) e crie um app gratuito.
2. Obtenha o `access_token`.
3. Execute:

```powershell
python -m recomendacao_imobiliaria.cli fetch-listings-ml --token SEU_TOKEN --max 200
# Ou defina: $env:ML_ACCESS_TOKEN = 'SEU_TOKEN'
```

**Opcao D — Normalizar CSV de qualquer portal (OLX, ZAP, VivaReal, Imovelweb):**

```powershell
python -m recomendacao_imobiliaria.cli normalize-listings --csv data/meu_export_portal.csv
# Detecta automaticamente colunas de preco, area, quartos, bairro etc.
```

---

### Passo 10 — Treinar e usar o modelo de precos

```powershell
# Treinar com o dataset gerado no passo 9
python -m recomendacao_imobiliaria.cli train-price --csv data/pouso_alegre_listings.csv

# Prever precos para novos imoveis
python -m recomendacao_imobiliaria.cli predict-price --csv data/pouso_alegre_listings.csv
# Resultado salvo em data/processed/predicted_prices.csv
```

---

### Passo 11 — RAG juridico sobre o Plano Diretor (opcional)

Requer uma chave da API da Anthropic (Claude).

```powershell
# Instalar dependencias extras
pip install chromadb anthropic

# Configurar chave
$env:ANTHROPIC_API_KEY = 'sua-chave-aqui'

# Indexar os artigos da Lei 6476/2021
python -m recomendacao_imobiliaria.cli build-rag-index

# Fazer uma pergunta juridica
python -m recomendacao_imobiliaria.cli rag-query --question "Posso construir um predio de 10 andares na ZMC?"
python -m recomendacao_imobiliaria.cli rag-query --question "O que e necessario para parcelar um terreno na ZEU?"
```

A aba **RAG Juridico** no Streamlit tambem oferece essa funcionalidade com interface grafica.

---

### Passo 12 — NDVI/NDBI real via Sentinel-2 (opcional, avancado)

Requer ambiente com mais dependencias (~1 GB):

```powershell
pip install pystac-client planetary-computer stackstac rioxarray

# Coleta NDVI/NDBI dos ultimos 6 meses para todas as celulas H3 do grid
python -m recomendacao_imobiliaria.cli collect-sentinel2 --output data/sentinel2_indices.csv

# Depois importa normalmente
python -m recomendacao_imobiliaria.cli import-indices --csv data/sentinel2_indices.csv
python -m recomendacao_imobiliaria.cli update-index-features
```

---

### Resumo do fluxo completo

```text
Instalar deps → Docker up → score-demo (teste) → Streamlit (Demo)
     ↓
fetch-boundary → build-grid → fetch-pois → build-features
     ↓
[import-indices ou collect-sentinel2] → update-index-features
     ↓
[import-zoning] → score-db → Streamlit (PostGIS)
     ↓
gen-listings → train-price → predict-price
     ↓
build-rag-index → rag-query
```

---

### Solucao de problemas comuns

| Problema | Solucao |
| -------- | ------- |
| `ModuleNotFoundError: recomendacao_imobiliaria` | Execute `$env:PYTHONPATH = 'src'` antes do comando |
| `connection refused` no PostGIS | Execute `docker compose -f Infra/docker-compose.yml up -d` e aguarde 10s |
| `403 Forbidden` no Mercado Livre | A API requer token OAuth — veja o Passo 9 Opcao C |
| `chromadb not found` para RAG | Execute `pip install chromadb anthropic` |
| `pystac_client not found` para Sentinel | Execute `pip install pystac-client planetary-computer stackstac rioxarray` |

---

### Como rodar (versao curta — so o dashboard Demo)

```powershell
git clone <url>
cd RecomendacaoImobiliaria
python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = 'src'
streamlit run app/streamlit_app.py
```

Acesse `http://localhost:8501` e selecione **Demo**.

---

## Pipeline MVP com dados reais

Depois de subir o PostGIS, rode os comandos em ordem:

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli fetch-boundary
python -m recomendacao_imobiliaria.cli build-grid
python -m recomendacao_imobiliaria.cli fetch-pois
python -m recomendacao_imobiliaria.cli build-features
python -m recomendacao_imobiliaria.cli import-indices --csv data/sample_indices.csv
python -m recomendacao_imobiliaria.cli update-index-features
python -m recomendacao_imobiliaria.cli score-db
```

Ou tudo de uma vez:

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli run-mvp
```

## Modelo inicial de preco com ML

Quando houver um CSV de anuncios/imoveis, o projeto ja tem um treinador inicial:

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli gen-listings
python -m recomendacao_imobiliaria.cli train-price --csv data/pouso_alegre_listings.csv
python -m recomendacao_imobiliaria.cli predict-price --csv data/pouso_alegre_listings.csv
```

O CSV deve ter uma coluna `price`. As colunas abaixo sao usadas quando existirem:

- numericas: `area_m2`, `bedrooms`, `bathrooms`, `parking_spaces`, `latitude`, `longitude`, `score_residencial`, `score_comercial`, `ndvi_mean_90`, `ndbi_mean_90`, distancias a servicos;
- categoricas: `property_type`, `neighborhood`, `zona`.

O modelo salvo fica, por padrao, em `models/price_model.joblib`.

## Documentacao do codigo

Veja [docs/codigo.md](docs/codigo.md) para entender modulo por modulo, comandos do CLI, tabelas tocadas e o fluxo interno da ferramenta.

Veja tambem [docs/plano_diretor.md](docs/plano_diretor.md) para entender como a ferramenta considera o Plano Diretor de Pouso Alegre.

## Modelo conceitual

O sistema trabalha com celulas H3 como unidade de analise. Para cada celula, a ferramenta calcula:

- indices ambientais e urbanos: NDVI, NDBI, slopes temporais;
- acessibilidade: distancia ate mercado, farmacia, escola etc.;
- carencia comercial: baixa oferta de servicos;
- conformidade urbanistica: uso permitido, condicionado ou vetado;
- compatibilidade com Plano Diretor e zoneamento;
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
