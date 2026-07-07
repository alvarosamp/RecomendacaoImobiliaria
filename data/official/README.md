# Dados oficiais

Pasta para arquivos oficiais baixados ou recebidos da Prefeitura, Camara, IBGE e IDE-Sisema.

## Organizacao recomendada

- `pdpa/`: arquivos do Plano Diretor de Pouso Alegre, incluindo KML/KMZ e anexos legais.
- `plano_diretor/`: espelho dos anexos baixados da pagina oficial da Prefeitura.
- `ibge/`: limites municipais, setores censitarios e dados socioeconomicos.
- `ambiental/`: camadas ambientais, APP, risco, hidrografia e restricoes.

Arquivos prioritarios:

- `pdpa/zoneamento_pdpa.kml`
- `pdpa/zoneamento_pdpa.kmz`
- `pdpa/anexo_6_quadro_2_parametros_ocupacao_solo.pdf`
- `pdpa/anexo_8_quadro_4b_usos_nao_residenciais_mdu.pdf`
- `pdpa/anexo_8_quadro_4c_usos_permitidos_mdu.pdf`
- `pdpa/anexo_9_quadro_7_parametros_incomodidade.pdf`
- `pdpa/anexo_9_quadro_8_condicoes_instalacao.pdf`
- `pdpa/anexo_ix_mapa_6_areas_risco.pdf`

Validar:

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli validate-official-data
```

Importar zoneamento:

```powershell
python -m recomendacao_imobiliaria.cli inspect-zoning --file data/official/pdpa/zoneamento_pdpa.kml
python -m recomendacao_imobiliaria.cli import-official-zoning
```
