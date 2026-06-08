# Pipeline de dados

## Ordem recomendada

1. `fetch-boundary`: busca o limite municipal no OpenStreetMap.
2. `build-grid`: gera a grade H3 dentro do limite.
3. `fetch-pois`: busca estabelecimentos e servicos no OSM.
4. `build-features`: calcula contagens e distancias por H3.
5. `import-indices`: importa NDVI/NDBI por H3 quando houver CSV.
6. `update-index-features`: calcula medias e tendencias de sensoriamento remoto.
7. `score-db`: gera scores explicaveis em `geo.scores`.

## Comandos

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

## Saidas principais

- `geo.city_boundary`: limite municipal.
- `geo.grid_h3`: celulas H3.
- `geo.osm_pois`: POIs normalizados.
- `geo.features`: features por celula.
- `geo.scores`: score residencial, score comercial e explicacao.

## Plano Diretor

Antes de salvar o score, o sistema consulta `config/plan_director_pouso_alegre.json`.

- Zonas permitidas mantem o score.
- Zonas condicionadas reduzem o score e geram alerta.
- Zonas bloqueadas zeram o score para o uso afetado.

## Limites conhecidos

- OSM pode ter dados incompletos em alguns bairros.
- Sem zoneamento real carregado, o scoring assume uso permitido.
- O CSV de NDVI/NDBI ja e suportado; a proxima etapa e automatizar a coleta via Earth Engine ou STAC.
