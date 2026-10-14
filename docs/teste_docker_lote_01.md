# Validação Docker — 13/10/2026

Ambiente isolado: projeto Compose `urbia-validation-lote01`, PostGIS 15/3.5, imagens reais da API (Python 3.12) e frontend (Node 20/Nginx). O banco da aplicação não foi alterado.

A execução do primeiro lote terminou com **128 testes e 7 subtestes aprovados**. O script HTTP `scripts/test_docker_smoke.py` aprovou 9 verificações: saúde, HTML/assets/SPA, bloqueio anônimo, cadastro/login, consulta de scores, restrição administrativa, isolamento de leads, aviso de modelo ausente e endpoint legal. As contas e leads criados são sintéticos e permanecem apenas no banco isolado.

Comandos reproduzíveis:

```powershell
docker compose -p urbia-validation-lote01 -f compose.test.yaml build api frontend
docker compose -p urbia-validation-lote01 -f compose.test.yaml up -d db api frontend
docker compose -p urbia-validation-lote01 -f compose.test.yaml --profile checks run --rm tests
docker compose -p urbia-validation-lote01 -f compose.test.yaml port api 8000
docker compose -p urbia-validation-lote01 -f compose.test.yaml port frontend 80
# Informe as portas retornadas acima:
python scripts/test_docker_smoke.py --api-url http://127.0.0.1:PORTA_API --frontend-url http://127.0.0.1:PORTA_FRONTEND
docker compose -p urbia-validation-lote01 -f compose.test.yaml stop
```

Após incluir as migrations, a suíte completa passou com **131 testes e 7 subtestes aprovados**, incluindo criação de banco, preservação de dados na reaplicação, checksum, recusa de baseline e rollback. As novas migrations foram verificadas usando a imagem da API com `src` atualizado montado somente para leitura. Essa execução não equivale a reconstruir a imagem com as migrations. O bootstrap legado e os caminhos DDL do runtime continuam ativos conforme documentado em `migrations.md`.

Não houve coleta de fontes externas nem validação de dados territoriais reais. O sucesso HTTP não representa validação visual completa do navegador. Os avisos de dependências legadas e tamanho de bundle continuam pendentes.
