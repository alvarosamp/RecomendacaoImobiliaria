# ImobiliariaNovo

Visão geral
- Projeto: ImobiliariaNovo
- Propósito: Sistema para suportar decisões em planejamento urbano e mercado imobiliário (configurado para Pouso Alegre, MG, Brasil).
- Status: MVP com scripts base, configurações e .env. Próximos passos descritos em "Roadmap".

Pré-requisitos
- Git
- Python 3.9+ (recomendado)
- PostgreSQL (ex.: 12+)
- Ferramentas opcionais: virtualenv/venv, poetry ou pip-tools para gerenciar dependências

Configuração do ambiente (local)
1. Criar e ativar virtualenv (Windows):
   - python -m venv .venv
   - .venv\Scripts\activate
2. Atualizar pip:
   - python -m pip install --upgrade pip setuptools wheel
3. Instalar dependências (veja seção de resolução de conflitos abaixo para pins recomendados). Exemplo rápido:
   - python -m pip install -r requirements.txt
   (Se não houver requirements.txt, veja os pins sugeridos na seção "Resolução de conflitos".)

Variáveis de ambiente (segurança)
- Não armazene credenciais reais em arquivos versionados.
- Use um arquivo de exemplo (config/.env.example) com placeholders no repositório e crie localmente um arquivo não versionado (ex.: config/.env.local) com as credenciais reais.
- Certifique-se de que config/.env.local ou config/.env esteja listado em .gitignore.

Exemplo de fluxo seguro
1. Adicione ao repositório apenas config/.env.example (placeholders).
2. Localmente:
   - cp config/.env.example config/.env.local
   - editar config/.env.local para colocar credenciais reais
3. .gitignore:
   - adicione a linha: /config/.env.local
4. Em CI/CD, configure secrets no provedor (GitHub Actions Secrets, GitLab CI Variables, etc.) e injete em tempo de execução.

Exemplo de variáveis (placeholders)
- PG_HOST=localhost
- PG_PORT=5432
- PG_DB=ImobiliariaDB
- PG_USER=admin
- PG_PASS=<SEU_SEGREDO>
- CITY_NAME=Pouso Alegre, Minas Gerais, Brazil
- H3_RES=8

Observações
- Para produção, prefira secret managers (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault) e não arquivos planos.
- Se quiser, eu crio config/.env.example e um snippet .gitignore para você.

Banco de dados (PostgreSQL) — exemplo rápido
- Criar usuário e banco:
  - sudo -u postgres psql
  - CREATE USER admin WITH PASSWORD 'admin123';
  - CREATE DATABASE "ImobiliariaDB" OWNER admin;
  - ALTER ROLE admin CREATEDB;  -- opcional, conforme necessidade
- Conexão: use PG_HOST:PG_PORT/PG_DB com usuário PG_USER e PG_PASS.

Resolução de conflitos de dependências (problema relatado na instalação)
- Mensagem observada: conflitos de versões entre pacotes (pyjwt, cloudpickle, packaging, ml-dtypes, tensorboard, matplotlib).
- Recomendação: instale em um virtualenv limpo e aplique pins compatíveis. Exemplo:
  1. python -m venv .venv
  2. .venv\Scripts\activate
  3. python -m pip install --upgrade pip
  4. python -m pip install "pyjwt>=2.9.0" "cloudpickle>=3.0.0" "packaging<25" "ml-dtypes>=0.5.1,<1.0.0" "tensorboard==2.19.0" "matplotlib==3.10.0"
  5. Após instalação, execute: pip check
- Alternativa robusta: usar poetry/pip-tools to lock dependencies e garantir reprodutibilidade:
  - poetry init && poetry add <dependências>  (ou gerar requirements.txt com pip-compile)

Sugestão: adicionar um requirements.txt ou pyproject.toml/pipfile ao repositório para travar versões.

Sugestões de desenvolvimento
- Mantenha um ambiente isolado por projeto (.venv) para evitar conflitos globais.
- Adote um gerenciador de dependências (poetry ou pip-tools) e comprometa o lockfile.
- Documente scripts de inicialização no package manager (ex.: Makefile, scripts no pyproject).

Teste e validação
- Após instalar dependências: pip check
- Execute a suíte de testes do projeto (se houver) e pipelines locais.

Contribuição
- Fork & pull request
- Abra issues para bugs e features
- Siga padrões de commit e mantenha descrições claras

Boas práticas e segurança
- Não comitar credenciais reais
- Use variáveis de ambiente para segredos
- Para deploy, considere um serviço de secrets (HashiCorp Vault, AWS Secrets Manager, etc.)

Licença
- Adicione a licença apropriada (MIT, Apache-2.0, etc.) conforme desejar — não incluída neste repositório por padrão.

Contato
- Mantenha informações de contato ou link do repositório/issue tracker conforme seu fluxo de trabalho.

## Visão técnica: do dado bruto ao mapa de recomendação

1) Propósito técnico
- Construir um sistema de suporte à decisão que integra sensoriamento remoto (Sentinel-2/MODIS), POIs (OSM/CNAE), dados socioeconômicos (IBGE) e regras urbanísticas (Plano Diretor), calcula features por grade H3 e gera scores explicáveis (residencial/comercial) com mapa interativo e APIs.

2) Arquitetura (camadas)
- Coleta → Lago bruto → ETL / Feature Store → Modelos / Scoring → API / UI
- Fontes: Earth Engine / STAC (Sentinel-2), Overpass/OSMnx, IBGE/SIDRA, shapefiles de zoneamento.
- Armazenamento: Postgres + PostGIS (+ pgvector para embeddings).
- Orquestração: scripts Python (Poetry); Prefect/Airflow opcional.
- UI: Streamlit (Folium/Leaflet); API: FastAPI (fase 2).

3) Modelagem espacial: H3 como unidade de análise
- Uso de H3 (resolução 8/9) para agregação temporal e espacial.
- Tabelas sugeridas:
  - geo.grid_h3(h3_id, res, geom)
  - geo.indices(h3_id, date, ndvi, ndbi, bai, cloud_pct)
  - geo.osm_pois(name, category, subcategory, geom)
  - geo.features(h3_id, …features…)
  - geo.scores(h3_id, score_residencial, score_comercial, explain_json)
  - geo.zoning(zona, usos_*, gabarito, coef_aprov, recuos, geom)
  - public.regs(doc, artigo, texto, embedding)

4) Sensoriamento remoto e índices
- NDVI = (B8 - B4) / (B8 + B4); NDBI ≈ (B11 - B8) / (B11 + B8) (Sentinel-2 L2A).
- Filtragem por nuvem (cloud_pct < 20%), agregação temporal (mediana/mean por mês/quinzena).
- Estatísticas: mean/median/std/slope (Theil-Sen/OLS), percentis p10/p90.
- Dados persistidos em `geo.indices` e derivados em `geo.features`.

5) POIs, acessibilidade e carência
- Normalizar POIs OSM por category/subcategory.
- Agregação por H3: contagem e distância mínima (sjoin_nearest, CRS 3857).
- Resultados em `geo.access` e colunas agregadas em `geo.features`.
- Fase 2: tempo de viagem na rede (OSMnx).

6) Socioeconômico e LULC
- IBGE/SIDRA por setor censitário — areal intersection com H3 (ponderação por área).
- MapBiomas para proporção de classes LULC por H3.
- Footprints (buildings) para densidade construída.

7) Conformidade urbanística (RAG)
- Regras hard: interseção H3↔zoning — usos vetados => score=0.
- Regras soft: RAG textual com embeddings em `public.regs` para responder consultas legais e extrair artigos citados.
- `scores.explain_json` guarda trilha de auditoria e decisões (✅/⚠️/⛔ badges no mapa).

8) Engenharia de features (exemplos)
- Séries: ndvi_mean_90, ndvi_slope_180, ndbi_mean_90, ndbi_slope_180.
- Acessibilidade: dist_min_supermarket_m, dist_min_pharmacy_m, dist_min_school_m.
- Oferta/Concorrência: poi_supermarket_cnt, poi_pharmacy_cnt.
- Mudança: deltas T-3m/T-6m, detecção de changepoints (CUSUM/PELT).

9) Scoring (MVP heurístico explicável)
- Comercial: combina carência, acessibilidade, crescimento urbano e máscara de zoneamento.
  - carência = max(0, alvo_cnt - poi_cnt)
  - Score_bruto = w1*carencia_norm + w2*acess_norm + w3*cresc_norm
  - Score_final = Score_bruto * allowed(use)
- Residencial: qualidade ambiental (NDVI), acessibilidade mista, oferta construída moderada.
- Calibração: A/B testing, especialistas; fase 2: modelos supervisionados (XGBoost, Bayesian opt).

10) Banco de dados e desempenho
- PostGIS com índices GiST em geom e B-tree em (h3_id, date).
- PK composta em geo.indices para upsert eficientes.
- Views materializadas: v_pois_by_h3, v_ndvi_latest, v_h3_zona.
- Particionamento por date (mensal) se necessário.

11) UI/UX (Streamlit)
- Camadas: boundary, grid H3, POIs (clusters), heatmaps (NDVI/score), badge de conformidade.
- Painéis: ranking top-K para abertura de comércio ou localização residencial, filtros por zona/score/datas.
- Explicabilidade: mostrar razões (carência/acesso/crescimento + citações legais).

12) Qualidade, validação e métricas
- Validação espacial: inspeção visual e comparação com eventos futuros (Precision@K, nDCG).
- Validação temporal: backtesting com janelas deslizantes.
- Auditoria em scores.explain_json; KPIs: cobertura H3, latência ETL, acurácia (RMSE/MAPE), Precision@K.

13) Operação e automação
- Use Poetry (pyproject.toml) para dependências e isolamento.
- Orquestração futura: Prefect/Airflow para pipelines de coleta e recomputo.
- Armazenamento de artefatos: MinIO; CI/CD: GitHub Actions (tests/lint/containers).

14) Segurança e conformidade
- Não comitar credenciais; usar `.env` local ou secret manager em produção.
- Respeitar limites e licenças (OSM ODbL, Sentinel Copernicus, MapBiomas).

15) Roadmap (curto → médio prazo)
1. Consolidar geo.indices (NDVI/NDBI por H3 e data).
2. Rodar features (slopes/médias + distâncias/contagens).
3. Gerar scores + badge de conformidade.
4. Expor no Streamlit com ranking e "ver base legal".
5. RAG textual (OCR+embeddings) e tempo de viagem em rede.
6. Modelos de valorização e explainability (SHAP).

## Como aplicar no seu repo (prático)
- Passe os scripts de ingestão/ETL para rodar por H3 e date; grave em `geo.indices`.
- Crie funções de agregação para `geo.features` (slopes, percentis).
- Script de scoring que produz `geo.scores` e `explain_json`.
- Streamlit usa `geo.scores` + `geo.features` + `public.regs` para UI e explicabilidade.

## Variáveis de ambiente (atual)
- Arquivo: config/.env
  - PG_HOST=localhost
  - PG_PORT=5432
  - PG_DB=ImobiliariaDB
  - PG_USER=admin
  - PG_PASS=admin123
  - CITY_NAME=Pouso Alegre, Minas Gerais, Brazil
  - H3_RES=8

## Resolução de conflitos de dependências (sugestão)
- Use virtualenv limpo + pins em requirements.txt ou Poetry.
- Exemplos de pins (conforme conflito reportado):
  - pyjwt>=2.9.0
  - cloudpickle>=3.0.0
  - packaging<25 (ex.: 24.3)
  - ml-dtypes>=0.5.1,<1.0.0
  - tensorboard==2.19.0
  - matplotlib==3.10.0

## Contribuição
- Fork → branch → PR; abra issues para mudanças maiores.
- Adote linters (ruff/flake8) e formatação (black).

---

Se desejar, gero:
- scripts base (ingestão NDVI → geo.indices, agregação → geo.features, scoring → geo.scores),
- um pyproject.toml (Poetry) com pins sugeridos,
- ou um prototype do Streamlit que exibe grid H3, heatmap e badges.