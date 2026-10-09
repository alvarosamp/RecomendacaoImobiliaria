# Deploy de produção

Este documento descreve como publicar o stack com `docker-compose.prod.yml`,
e o que muda em relação ao ambiente de desenvolvimento (`docker-compose.yml`).

## O que mudou em relação ao dev

| | Dev (`docker-compose.yml`) | Produção (`docker-compose.prod.yml`) |
| --- | --- | --- |
| pgAdmin | exposto em `:5050` | **removido** — nunca deve ficar acessível |
| MinIO console/API | exposto em `:9000`/`:9001` | sem porta publicada, só rede interna |
| MLflow UI | exposto em `:5000` | sem porta publicada, só rede interna |
| API | exposta em `:8001` | sem porta publicada — só acessível via proxy interno do frontend (`/api`) |
| Frontend | exposto em `:80` sem TLS | atrás do Caddy, que expõe `:80`/`:443` com HTTPS automático (Let's Encrypt) |
| Restart | `unless-stopped` | `always` |
| Credenciais | podem usar defaults do `.env` | vêm só do `.env.prod`, sem defaults fracos |

Resultado: a única porta acessível de fora é a do Caddy (80/443). Tudo o
resto — banco, MinIO, MLflow, API — só é alcançável entre containers, na rede
`backend`.

## Passo a passo

1. Aponte o DNS do seu domínio para o IP deste host (A record).
2. Copie e preencha o arquivo de ambiente de produção:
   ```bash
   cp .env.prod.example .env.prod
   # edite .env.prod com valores reais (senhas fortes, domínio, etc.)
   ```
3. Gere segredos fortes, por exemplo:
   ```bash
   openssl rand -base64 48   # para JWT_SECRET
   openssl rand -base64 24   # para senhas de banco/MinIO
   ```
4. Suba o stack:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod pull
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
   ```
5. Acompanhe o Caddy emitir o certificado:
   ```bash
   docker compose -f docker-compose.prod.yml logs -f caddy
   ```

O deploy principal inicia apenas banco, API, frontend e Caddy. Para também
iniciar MinIO e MLflow, use `--profile tools`. A configuração atual usa a tag
`latest` das imagens publicadas no Docker Hub, conforme definido no
`.env.prod`.

## Ação pendente antes de ir pra produção: rotacionar o HF_TOKEN

O arquivo `.env` de desenvolvimento tem um `HF_TOKEN` da Hugging Face em
texto puro. Antes de publicar:

1. Revogue esse token em https://huggingface.co/settings/tokens.
2. Gere um novo token e coloque só no `.env.prod` (nunca no `.env` de dev
   nem em qualquer arquivo versionado).

O mesmo vale para as senhas default que aparecem em `.env` e em
`Infra/docker-compose.yml` (`admin123`, `gpminio123`, `admin`) — são
adequadas só para desenvolvimento local.

## Observação sobre `Infra/docker-compose.yml`

Esse arquivo é uma versão antiga/duplicada do compose (sem variáveis de
ambiente, com porta de Postgres divergente da raiz — `5432` em vez de
`5433`, e senhas fixas no arquivo). Não é referenciado por nenhum script,
workflow de CI ou documentação atual — recomendo removê-lo para evitar que
alguém suba a stack errada por engano, mas não apaguei sem confirmar com
vocês.

## Pendências de segurança que ficam fora deste MVP de deploy

Não fazem parte da mudança de infraestrutura, mas valem registrar:

- Nenhum dos containers roda como usuário non-root hoje (`Dockerfile`,
  `mlflow.Dockerfile`). Recomendado para o próximo passo de hardening.
- `docker-compose.prod.yml` não usa Docker secrets/Vault — os segredos vêm
  de variáveis de ambiente via `.env.prod`, adequado para um único host,
  mas vale revisar se migrarem para múltiplos hosts/orquestrador.
