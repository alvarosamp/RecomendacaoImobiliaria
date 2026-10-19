# Protótipo ISP na Hostinger com imagem do Docker Hub

Este pacote adiciona somente arquivos de implantação. Não altera a aplicação, o Dockerfile, o Compose local nem a stack imobiliária. Destina-se ao protótipo ISP da branch `codex/urbia-isp`, incluindo o guia Como usar.

## Arquivos para o Docker Manager

- `compose.yaml`: cole na configuração Compose de um **novo** projeto `urbia-isp-hostinger`.
- `isp-hostinger.env`: cole o conteúdo no campo de variáveis de ambiente do mesmo projeto.

Não é necessário enviar código para a VPS. Não há build, bind mounts, arquivos de configuração adicionais ou volumes persistentes. O protótipo contém dados demonstrativos e calcula os estudos sem gravar cadastro. O relatório é baixado no navegador.

**A referência `alvarocareli/urbia-isp:20261019-d3bcc02b` é a tag proposta para esta entrega. Este pacote não publica a imagem nem confirma sua disponibilidade no Docker Hub. A imagem precisa ser publicada antes de usar Deploy na Hostinger. As imagens do sistema imobiliário anterior não contêm este protótipo.**

## Publicar a imagem uma vez, no computador de desenvolvimento

Na raiz do worktree `codex/urbia-isp`, use uma conta com permissão de escrita no repositório Docker Hub informado:

```bash
docker login
docker buildx build --platform linux/amd64 \
  -f isp-demo/Dockerfile \
  -t alvarocareli/urbia-isp:20261019-d3bcc02b \
  --push isp-demo
```

O contexto é somente `isp-demo/`. O Dockerfile empacota servidor, planejador, interface e os três arquivos de dados da demonstração. Não inclui os arquivos `.env` da aplicação imobiliária. Se publicar em outro usuário/repositório ou tag, ajuste `ISP_IMAGE` nas variáveis da Hostinger.

Para repositório público, o pull dispensa login. Para repositório privado, configure as credenciais do registry no Docker Manager; não coloque a senha do Docker Hub no Compose ou nas variáveis da aplicação. Não é necessário informar tokens de satélite, banco, JWT ou ERP para este protótipo.

## Subir na VPS

1. Crie um projeto separado. Se já houver uma stack imobiliária, mantenha seu nome, imagens e volumes.
2. Cole o Compose e as variáveis. Não confunda variáveis do projeto usadas na interpolação com variáveis extras apenas do container. A interpolação precisa resolver `ISP_IMAGE`, `ISP_PUBLIC_PORT` e `ISP_BIND_IP`.
3. Após publicar a imagem, execute Deploy. Aguarde o serviço saudável.
4. Libere a porta escolhida no firewall da VPS e acesse `http://IP_DA_VPS:18089` (ou a porta configurada). Esse arquivo não configura DNS ou HTTPS.

Se preferir SSH, envie os dois arquivos para a mesma pasta e execute nela:

```bash
docker compose --env-file isp-hostinger.env -f compose.yaml config --quiet
docker compose --env-file isp-hostinger.env -f compose.yaml pull
docker compose --env-file isp-hostinger.env -f compose.yaml up -d
docker compose --env-file isp-hostinger.env -f compose.yaml ps
curl -fsS http://127.0.0.1:18089/health
```

`HOST` e `PORT` internos ficam fixos em `0.0.0.0:8080` para corresponder à imagem e ao healthcheck. Mude apenas a porta pública para evitar conflitos. O servidor não tem autenticação: este pacote é para apresentar a simulação, não para cadastrar clientes reais.

## Domínio e HTTPS, se desejado

Um proxy instalado diretamente na VPS pode encaminhar para `127.0.0.1:18089`; nesse caso, defina `ISP_BIND_IP=127.0.0.1` para acesso apenas pelo proxy. Se o proxy for outro container, o localhost dele não é o servidor: configure uma rede Docker compartilhada e encaminhe ao serviço na porta 8080, ou use um endereço da VPS que seja alcançável pelo proxy com a porta pública. A rede compartilhada depende da configuração existente e não foi presumida neste pacote.

## Validação desta entrega

O Compose foi validado com Docker Compose e o arquivo de variáveis fornecido. Ele contém somente o serviço ISP, sem dependência de código local. Não foram feitos push para registry, deploy remoto ou alterações no container local em execução.

Referências: [Docker Manager da Hostinger](https://www.hostinger.com/support/12040815-how-to-deploy-your-first-container-with-hostinger-docker-manager/) e [interpolação de variáveis no Docker Compose](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/).
