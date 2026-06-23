# Recomendacao Imobiliaria

Ferramenta de inteligencia territorial para Pouso Alegre, MG. O objetivo e apoiar decisoes de investimento imobiliario, crescimento urbano e implantacao de estabelecimentos, sempre respeitando o Plano Diretor, zoneamento e restricoes territoriais.

## O que este projeto faz

- Gera grade H3 para analisar a cidade por celulas.
- Coleta POIs do OpenStreetMap.
- Calcula carencia e acessibilidade por regiao.
- Importa NDVI/NDBI por H3 e calcula tendencias.
- Avalia compatibilidade com Plano Diretor e zoneamento.
- Gera score residencial e comercial explicavel.
- Treina e aplica modelo inicial de preco de imoveis.
- Mostra ranking, mapa e explicacoes no Streamlit.

## Onde conseguir Plano Diretor e zoneamento

Voce precisa de dois tipos de documento:

1. Texto legal: Plano Diretor, lei de uso e ocupacao do solo, anexos e alteracoes.
2. Arquivo geografico: mapa oficial de zoneamento em GeoJSON, SHP, GPKG ou KML.

Fontes recomendadas:

- Prefeitura de Pouso Alegre: https://pousoalegre.mg.gov.br/
- Camara/Legislador - Lei Ordinaria 6476/2021: https://www.legislador.com.br/legisladorweb.asp?ID=122&WCI=LeiTexto&aaLei=2021&inEspecieLei=1&nrLei=6476
- IBGE geociencias: https://www.ibge.gov.br/geociencias/downloads-geociencias.html
- IDE-Sisema MG: https://idesisema.meioambiente.mg.gov.br/

Se o arquivo geografico de zoneamento nao estiver disponivel no site, solicite a Prefeitura por e-SIC/Lei de Acesso a Informacao. Peca explicitamente:

```text
Arquivo georreferenciado do zoneamento urbano de Pouso Alegre, preferencialmente em Shapefile, GeoPackage, GeoJSON ou KML, com a sigla/codigo da zona e descricao, alem dos anexos do Plano Diretor e da lei de uso e ocupacao do solo em vigor.
```

Coloque os arquivos oficiais em:

```text
data/official/
```

Nomes recomendados:

- `data/official/zoneamento_oficial.geojson`
- `data/official/zoneamento_oficial.gpkg`
- `data/official/plano_diretor_lei_6476_2021.pdf`
- `data/official/uso_ocupacao_solo.pdf`

Verifique o que ja existe:

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli official-sources
python -m recomendacao_imobiliaria.cli validate-official-data
```

## Instalacao

```powershell
cd C:\Users\vish8\OneDrive\Documentos\RecomendacaoImobiliaria
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:PYTHONPATH='src'
```

## Teste rapido sem banco

```powershell
python -m recomendacao_imobiliaria.cli score-demo
python -m recomendacao_imobiliaria.cli check-plan --zone ZEU --use comercial
```

## Rodar o front

```powershell
$env:PYTHONPATH='src'
streamlit run app/streamlit_app.py
```

No front voce encontra:

- ranking de oportunidades;
- mapa;
- detalhe da area;
- explicacao do score;
- alertas de Plano Diretor;
- painel de predicao de preco.

## Rodar com PostGIS

Suba o banco:

```powershell
docker compose -f Infra/docker-compose.yml up -d
```

Pipeline basico:

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

Importar zoneamento oficial:

```powershell
python -m recomendacao_imobiliaria.cli import-zoning --file data/official/zoneamento_oficial.geojson
python -m recomendacao_imobiliaria.cli score-db
```

Se ainda nao tiver zoneamento oficial, gere um exemplo para testar:

```powershell
python -m recomendacao_imobiliaria.cli gen-sample-zoning
python -m recomendacao_imobiliaria.cli import-zoning --file data/sample_zoning.geojson
python -m recomendacao_imobiliaria.cli score-db
```

## ML de preco

Treinar com CSV exemplo:

```powershell
python -m recomendacao_imobiliaria.cli train-price --csv data/sample_properties.csv --no-enrich
```

Predizer:

```powershell
python -m recomendacao_imobiliaria.cli predict-price --csv data/sample_properties.csv
```

Quando tiver dados reais de anuncios, use um CSV com colunas como:

- `price`
- `area_m2`
- `bedrooms`
- `bathrooms`
- `parking_spaces`
- `latitude`
- `longitude`
- `property_type`
- `neighborhood`
- `zona`

## Estrutura importante

```text
app/                         Front Streamlit
config/                      Regras do Plano Diretor e configuracoes
data/official/               Arquivos oficiais da Prefeitura/Camara/IBGE
data/sample_*.csv            Dados de exemplo
docs/                        Documentacao tecnica
Infra/                       Docker Compose e SQL do PostGIS
src/recomendacao_imobiliaria Codigo Python do produto
tests/                       Testes automatizados
```

## Modulos principais

- `geospatial.py`: limite municipal, H3, POIs e features.
- `zoning_import.py`: importacao do zoneamento oficial.
- `plan_director.py`: compatibilidade zona + uso.
- `scoring.py`: score residencial/comercial explicavel.
- `decision.py`: prioridade, risco e resumo da oportunidade.
- `remote_sensing.py`: NDVI/NDBI e tendencias.
- `ml.py`: treino e predicao de preco.
- `reporting.py`: dados para dashboard.

## Estado atual

Ja existe um MVP funcional com dados demo e pipeline para PostGIS. Para virar produto confiavel, o proximo passo mais importante e importar o zoneamento oficial de Pouso Alegre e anexos legais. Sem isso, a ferramenta deve ser tratada como prototipo tecnico, nao como recomendacao juridicamente validada.

## Validacao

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -v
```

## Documentacao complementar

- `docs/codigo.md`
- `docs/pipeline.md`
- `docs/plano_diretor.md`
- `docs/data_model.md`
- `docs/roadmap.md`
