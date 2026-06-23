# Dados oficiais

Coloque aqui os arquivos oficiais baixados ou recebidos da Prefeitura, Camara, IBGE e IDE-Sisema.

Nomes recomendados:

- `zoneamento_oficial.geojson` ou `zoneamento_oficial.gpkg`
- `plano_diretor_lei_6476_2021.pdf`
- `uso_ocupacao_solo.pdf`
- `setores_censitarios.gpkg`
- `restricoes_ambientais.gpkg`

Validar:

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli validate-official-data
```

Importar zoneamento:

```powershell
python -m recomendacao_imobiliaria.cli import-zoning --file data/official/zoneamento_oficial.geojson
```
