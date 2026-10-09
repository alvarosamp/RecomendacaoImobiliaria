# Bairros — Pouso Alegre

## Fonte municipal disponível

- Arquivo local: `mapa_urbano_pouso_alegre_2025.pdf`
- Publicador: Prefeitura Municipal de Pouso Alegre, Departamento de Informações Georreferenciadas
- Ano/escala declarados no documento: 2025, 1:15.000
- URL de origem: https://cmpousoalegre.gwlegis.com.br/arquivo/68dacdc5cd7e6.pdf
- Baixado em: 2026-08-21

O mapa é a referência municipal para a nomenclatura e a localização visual dos bairros/loteamentos. Ele não foi publicado como uma camada vetorial com polígonos de limites de bairros; por isso, **não deve ser importado como `geo.neighborhoods`**.

## Importação automática

Quando a Prefeitura disponibilizar uma camada GeoJSON, GeoPackage, Shapefile ou KML com limites, salve-a nesta pasta com um dos nomes abaixo e execute `import-neighborhoods` ou o refresh da aplicação:

- `bairros_oficiais.geojson`
- `bairros_oficiais.gpkg`

O importador registra a fonte, filtra Pouso Alegre pelo código IBGE `3152501` e substitui as referências aproximadas por nomes oficiais apenas para células cobertas por polígonos.

## Camada de referência OpenStreetMap

Enquanto não houver camada oficial, o mapa usa `osm_bairros_pouso_alegre.geojson`
(limites de bairro, quadrantes e pontos de bairro do OSM, licença ODbL) para rotular
o mapa e nomear as células H3. Polígonos importados em `geo.neighborhoods` têm
prioridade sobre ela no endpoint `/api/analytics/neighborhoods-geojson`.

Atualizar:

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli fetch-osm-neighborhoods
```

## Bairros dos Correios (área estimada)

`cep_bairros_pouso_alegre.geojson` cruza as ruas do OSM com o bairro que os Correios
(ViaCEP) atribuem a cada logradouro e divide a área urbana entre os bairros. É a camada
principal do mapa porque usa os mesmos nomes de endereços e anúncios; as áreas são
estimativas (`approximate: true`). Limites desenhados no OSM valem por cima dela.

Regerar (o cache do ViaCEP pode ficar em disco externo):

```powershell
$env:PYTHONPATH='src'
$env:VIACEP_CACHE='D:\Imobiliaria\bairros_cache\viacep_cache.json'
python -m recomendacao_imobiliaria.cli build-cep-neighborhoods
```
