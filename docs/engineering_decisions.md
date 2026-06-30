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

O comando `export-report` gera um Markdown executivo e um CSV analitico. Ele tenta usar PostGIS; se o banco nao estiver disponivel e a fonte for `auto`, usa dados demonstrativos.

## Fronteira entre produto e dado oficial

O sistema pode demonstrar valor com dados simulados, mas recomendacoes reais dependem do zoneamento oficial, anexos legais e validacao tecnica. Por isso, o Plano Diretor e o zoneamento sempre reduzem ou bloqueiam recomendacoes quando ha restricao.
