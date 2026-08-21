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
