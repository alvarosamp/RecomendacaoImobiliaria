# Decisoes de engenharia

## Configuracao fora do codigo

Os pesos de scoring ficam em `config/scoring_weights.json`. Isso permite ajustar a importancia de crescimento urbano, acessibilidade, carencia comercial e qualidade ambiental sem alterar o codigo-fonte.

## Scoring explicavel

O score nao retorna apenas numeros. O `explain_json` inclui:

- fatores positivos;
- fatores de atencao;
- contribuicoes ponderadas;
- multiplicador do Plano Diretor;
- confianca analitica;
- recomendacoes de uso.

## Healthcheck

O comando `healthcheck` verifica:

- arquivos de configuracao;
- dados oficiais em `data/official`;
- conexao com PostGIS;
- existencia e preenchimento das tabelas principais.

## Relatorios

O comando `export-report` gera um Markdown executivo e um CSV analitico. PostGIS e a fonte padrao; `auto` e um alias de PostGIS. Falhas e base vazia interrompem a exportacao. Dados demonstrativos exigem `--source demo` e sao identificados no Markdown e no CSV.

## Identidade territorial e procedencia

O piloto compartilha a identidade de `config/cities/pouso_alegre.json`: IBGE de sete digitos e CNES derivado de seis digitos. Respostas municipais divergentes sao rejeitadas. Populacao por H3 continua estimada, com metodo, fonte e ano registrados em `ops.data_sources`; dados legados sem registro verificavel aparecem como procedencia pendente. A auditoria `audit-territorial-data` e somente de leitura.

## Corpus juridico

O RAG real exige corpus acompanhado de manifesto aprovado e checksum. Corpus embutido exige `--demo`, bloqueado em producao. O indice persistido precisa corresponder ao corpus validado; RAG nao altera a regra legal deterministica. Veja `docs/implementacao_lote_01.md` para operacao e limitacoes.

## Fronteira entre produto e dado oficial

O sistema pode demonstrar valor com dados simulados, mas recomendacoes reais dependem do zoneamento oficial, anexos legais e validacao tecnica. Por isso, o Plano Diretor e o zoneamento sempre reduzem ou bloqueiam recomendacoes quando ha restricao.
