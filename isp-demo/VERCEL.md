# Publicar o protótipo ISP na Vercel

Esta opção publica o **protótipo ISP**, não o sistema imobiliário completo. Mantém mapa, instalações, oportunidades, planejador, radar histórico, inspeção simulada, guia e exportações. Não utiliza Docker, imagem do Docker Hub, banco ou variáveis secretas.

## Importação pelo GitHub

1. Na Vercel, escolha **Add New → Project** e importe `alvarosamp/RecomendacaoImobiliaria`.
2. Selecione a branch **`codex/urbia-isp-vercel`**. Caso a importação inicialmente use `main`, configure **Settings → Environments → Production → Branch Tracking** para esta branch antes de publicar a versão de produção. Se a primeira tentativa tiver usado `main`, não reutilize esse resultado: faça um novo deploy da branch correta.
3. Defina **Root Directory = `isp-demo`**. Não selecione a raiz do repositório ou `web`: o projeto precisa da função Python e dos dados demonstrativos. Desmarque **Include source files outside of the Root Directory in the Build Step**, pois este módulo é independente do restante do repositório.
4. Selecione **Framework Preset = Other**. O arquivo `vercel.json` configura o build `python3 build_vercel.py`, saída `public` e a função em `api/plan.py`. Não há instalação de dependências extras; Python 3.12 está indicado em `.python-version`.
5. **Environment Variables: nenhuma necessária.** Não copie os envs da Hostinger ou do sistema imobiliário. Clique em **Deploy**.

A API e a interface usam o mesmo domínio HTTPS. Teste `/health`, abra **Planejar expansão**, selecione um pedido e compare alternativas. Uma configuração de acesso protegido da conta Vercel pode pedir login ao visitante; isso é separado da autenticação do aplicativo.

## Arquitetura

- O build copia apenas assets estáticos autorizados de `web/` e três snapshots JSON para `public/`.
- `/api/simulation`, `/api/roads`, `/api/radar` e `/health` são reescritos para arquivos estáticos. Não executam coleta de satélite.
- `POST /api/plan` é uma função Python. O adaptador reutiliza a validação HTTP e o motor existentes do Docker, sem duplicar o algoritmo. O grafo é carregado a partir dos arquivos empacotados; não depende do diretório de execução nem de um processo de longa duração.
- `GET` e `HEAD` da função retornam 405; ela não serve código-fonte ou arquivos do sistema.
- A inspeção e o download de relatórios continuam no navegador. Não há sessões de servidor ou armazenamento persistente.
- `.vercelignore` restringe o upload ao módulo ISP, aos arquivos necessários e aos dados sintéticos; caches brutos de satélite e coletores ficam fora. A função exclui assets estáticos do seu pacote.
- O Docker local e os arquivos da Hostinger não precisam ser alterados.

## Verificação local

```bash
cd isp-demo
python3 build_vercel.py
python3 -m unittest test_vercel.py test_planner.py
```

`public/` é uma pasta gerada, substituída a cada build e ignorada pelo Git. Não edite arquivos nela; edite a origem em `web/` ou `data/`.

## CLI e publicação temporária

Com uma conta conectada, execute a partir de `isp-demo`:

```bash
npx vercel@64.5.0
```

A CLI também documenta uma publicação temporária sem login, sujeita à disponibilidade:

```bash
npx vercel@64.5.0 deploy --temporary --yes
```

**Na validação desta entrega, a Vercel recusou o modo temporário e solicitou autenticação; não foi criada uma publicação remota.** Nesse caso, execute `npx vercel@64.5.0 login` no seu computador ou use a importação pelo GitHub.

Se o modo temporário estiver disponível, use a URL e o link de transferência/claim retornados pela CLI para experimentar e associar o deploy à sua conta. A validade é a informada pela Vercel no momento da publicação; uma URL temporária não é promessa de hospedagem permanente nem conecta automaticamente as atualizações do GitHub. Para implantação durável e atualizações a cada push, importe a branch como descrito acima.

## Limites

Os dados operacionais continuam fictícios. Não há cadastro/login, conexão com ERP ou coleta recorrente nesta versão. Chamadas ao cálculo podem ter latência maior na primeira execução; `maxDuration` foi definido em 30 segundos. A função não mantém tarefas em segundo plano. Os mapas base ainda dependem da disponibilidade dos tiles públicos do OpenStreetMap.

Referências: [Python Functions em /api](https://vercel.com/docs/functions/runtimes/python/api-directory), [runtime Python e leitura de arquivos](https://vercel.com/docs/functions/runtimes/python) e [vercel.json](https://vercel.com/docs/project-configuration/vercel-json).
