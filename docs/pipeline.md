# Pipeline de dados

## Ordem recomendada

1. `fetch-boundary`: busca o limite municipal no OpenStreetMap.
2. `build-grid`: gera a grade H3 dentro do limite.
3. `fetch-pois`: busca estabelecimentos e servicos no OSM.
4. `build-features`: calcula contagens e distancias por H3.
5. `score-db`: gera scores explicaveis em `geo.scores`.

## Comandos

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli fetch-boundary
python -m recomendacao_imobiliaria.cli build-grid
python -m recomendacao_imobiliaria.cli fetch-pois
python -m recomendacao_imobiliaria.cli build-features
python -m recomendacao_imobiliaria.cli score-db
```

## Saidas principais

- `geo.city_boundary`: limite municipal.
- `geo.grid_h3`: celulas H3.
- `geo.osm_pois`: POIs normalizados.
- `geo.features`: features por celula.
- `geo.scores`: score residencial, score comercial e explicacao.

## Limites conhecidos

- OSM pode ter dados incompletos em alguns bairros.
- Sem zoneamento real carregado, o scoring assume uso permitido.
- NDVI/NDBI ainda depende do notebook exploratorio; a proxima etapa e transformar isso em script.
