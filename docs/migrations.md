# Migrações SQL — fundação de EX-05

O comando `python -m recomendacao_imobiliaria.cli migrate-db` aplica os arquivos de `src/recomendacao_imobiliaria/migrations`, em ordem, numa única transação PostgreSQL. As versões e checksums ficam em `ops.schema_migrations`. Um lock transacional serializa executores concorrentes. Arquivos já aplicados não devem ser editados: alterações futuras recebem novo arquivo numerado.

Esta primeira entrega usa SQL versionado, alternativa permitida pelo plano, para reaproveitar a estrutura PostGIS existente sem depender de modelos ORM incompletos. Os scripts históricos de inicialização foram congelados nas versões 001–010; a versão 011 inclui as tabelas da aplicação e colunas de bairro. Alterar `Infra/initdb` não altera as migrations congeladas.

## Uso

Configure `PG_HOST`, `PG_PORT`, `PG_DB`, `PG_USER` e `PG_PASS` para um banco **vazio**, criado previamente pelo administrador. Execute `migrate-db` com uma conta autorizada a criar schema, tabelas e a extensão PostGIS. A segunda execução não reaplica versões. Falhas revertem todas as alterações daquela execução.

Não inicialize esse banco também com os scripts de `Infra/initdb`: uma base com tabelas da aplicação e sem registro de migrations é recusada. O comando não marca automaticamente bancos existentes como equivalentes. A adoção do banco atual exige comparação auditada de tabelas, tipos, constraints e índices, além de backup e validação em cópia.

## Pendências

EX-05 permanece parcial: ainda não foram retirados os caminhos DDL do runtime, nem substituído o bootstrap do compose de desenvolvimento. Não se deve remover essas compatibilidades antes da adoção auditada do banco existente. A conta de aplicação sem privilégios DDL será validada nessa etapa. Downgrade destrutivo não é fornecido; reversões dependem de backup ou de migration corretiva.

Os testes PostGIS criam bancos separados e verificam bootstrap, repetição sem perda de conta, recusa de baseline desconhecida, detecção de checksum alterado e rollback por erro SQL.
