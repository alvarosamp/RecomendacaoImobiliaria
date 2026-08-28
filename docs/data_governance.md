# Governanca de dados e privacidade

## Regra de uso

Dados territoriais, cadastrais e de mercado so podem alimentar uma recomendacao quando sua origem, data de referencia e condicao de uso estiverem registradas. Dados demonstrativos nunca devem ser exibidos como fonte oficial.

## Registro de fonte

A tabela `ops.data_sources` registra cada carga com dataset, origem, URL ou arquivo, data de referencia, quantidade de registros e status. Para cargas relevantes, preencha tambem:

- `checksum_sha256`: identidade imutavel do arquivo importado;
- `license_name`: licenca ou termo de uso da fonte;
- `schema_version`: versao do layout recebido;
- `legal_basis`: fundamento de tratamento quando houver dados pessoais.

## LGPD

O produto deve coletar apenas o necessario para a funcionalidade solicitada. Historico de navegacao, favoritos e leads sao dados vinculados a uma conta e exigem aviso de privacidade, consentimento quando aplicavel e mecanismos para acesso, correcao, exportacao e exclusao. Dados usados para treino devem ser pseudonimizados e separados de identificadores diretos.

## Ciclo operacional

1. Validar schema, coordenadas, geometrias e duplicidades antes da carga.
2. Registrar a fonte e o resultado da validacao.
3. Versionar o dataset e o modelo associado ao treinamento.
4. Exibir data de atualizacao, fonte e nivel de confianca no resultado.
5. Suspender a fonte quando expirada, sem licenca conhecida ou com falha de qualidade.
