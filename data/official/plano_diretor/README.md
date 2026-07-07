# Plano Diretor - arquivos oficiais baixados

Arquivos baixados da pagina oficial do Plano Diretor:

https://pousoalegre.mg.gov.br/pagina-site-submenu/87

Conteudo principal:

- mapas de zoneamento, macrozoneamento, eixos, riscos e polos;
- quadros de parametros urbanisticos;
- quadros de usos permitidos;
- parametros de incomodidade;
- condicoes de instalacao de atividades;
- termos de referencia EIC, EIR e EIV.

Manifestos:

- `manifest_quadros.csv`
- `manifest_mapas_estrategicos.csv`

Pendencia importante:

- baixar manualmente os arquivos KML/KMZ de zoneamento urbano no Google Drive indicado em `google_drive_kml_kmz_links.txt`;
- salvar como `data/official/zoneamento_oficial.kml` ou `data/official/zoneamento_oficial.kmz`;
- importar com `python -m recomendacao_imobiliaria.cli import-zoning --file data/official/zoneamento_oficial.kml`.
