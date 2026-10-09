# Hostinger — versão 20261005-v1

## Entrega

Cole compose.hostinger.yaml no Docker Manager e o conteúdo de hostinger.env no campo de variáveis de ambiente. Não é necessário enviar arquivos, código, Caddyfile, certificados ou executar builds na VPS. O Compose só referencia imagens publicadas; hostinger.env contém credenciais novas e é ignorado pelo Git. Nunca faça commit desse arquivo.

Projeto: ri-hostinger-20261005-a10dda. Se o painel solicitar nome do projeto, use esse nome. Os volumes e a rede recebem automaticamente o prefixo do projeto escolhido pelo Compose/painel. Não reutilize o nome de uma stack existente.

Única porta publicada: HOST_PORT, padrão 18087. Foi verificada livre no computador local; disponibilidade e firewall na VPS devem ser conferidos no painel. Se já ocupada, altere apenas HOST_PORT. Banco, API, MinIO e MLflow ficam na rede interna.

## Componentes preservados

- Frontend React/Vite + nginx, API FastAPI, cadastro/login e CRM de leads.
- PostGIS 15 com os 11 scripts Infra/initdb dentro da imagem, além da inicialização idempotente do registro de dados na API.
- Pipeline de coleta, processamento, análises e pontuação como subprocessos dentro da API; não há worker externo separado.
- MinIO para objetos e MLflow para métricas/artifacts; volumes para banco, dados, modelos, cache, saída, objetos e tracking.
- Mapa, oportunidades, auditoria legal, explicação de score, comparação de áreas, relatórios, avaliação de imóveis, CRM, conceitos, oportunidades comerciais e estudo de caso. A jornada atual foi preservada e os módulos existentes voltaram ao menu conforme o perfil.
- pgAdmin é ferramenta opcional de desenvolvimento, não uma dependência de produção.

Imagens linux/amd64, todas com a tag 20261005-v1:

- alvarocareli/ri-hostinger-a10dda-api
- alvarocareli/ri-hostinger-a10dda-frontend
- alvarocareli/ri-hostinger-a10dda-db
- alvarocareli/ri-hostinger-a10dda-mlflow
- alvarocareli/ri-hostinger-a10dda-minio

Os digests e a verificação anônima ficam em deploy/hostinger/published-images.json. MinIO é a republicação sem alterações da imagem oficial já instalada; origem e licença em deploy/hostinger/minio-source.md.

## Acesso e primeiro cadastro

1. Aguarde db, api e frontend iniciarem. Na primeira execução, PostgreSQL cria schema/tabelas e PostGIS automaticamente; a API inicializa as colunas do registro de fontes.
2. Abra http://IP_DA_VPS:18087/register (use a porta escolhida). Crie nome, e-mail, senha e perfil. Não existe conta administrativa ou senha padrão previamente cadastrada; o primeiro usuário também faz o cadastro normal.
3. Acesse /login e depois /app. O perfil Corretor inclui CRM, avaliação e conceitos; Investidor inclui avaliação e estudo de caso; Incorporadora inclui conceitos e estudo de caso; Poder Público inclui oportunidades comerciais e estudo de caso. Todos preservam a jornada territorial.
4. O banco começa vazio, sem clientes ou dados privados locais. Use a ação de configuração inicial mostrada em /app para coletar dados públicos e gerar a grade/pontuação. A coleta inicial preserva 12 meses de Sentinel-2 e pode demorar; acompanhe as etapas na interface. CRM, avaliação inicial e conceitos podem funcionar antes da coleta territorial terminar.
5. O login usa token Bearer armazenado no navegador, sem cookies de sessão. nginx preserva Host com porta e o protocolo; requisições de escrita com origem de outro site são rejeitadas. CORS_ORIGINS vazio funciona no acesso por IP e porta porque frontend e API compartilham a origem.

O Compose entregue atende HTTP por IP. HTTPS/domínio não foram configurados porque nenhum domínio/certificado foi fornecido. Antes de operar com credenciais reais e dados de clientes em uma rede pública, configure HTTPS no proxy/painel. Caso outro proxy termine TLS e envie HTTP ao nginx, inclua a origem HTTPS exata em CORS_ORIGINS (sem barra final).

## Imagens e dados

Dockerfiles de build em deploy/hostinger e contextos com allowlist. Nenhum .env, senha, token, banco local, CSV privado, modelo treinado local ou cliente foi copiado para as imagens. As únicas referências empacotadas são documentos e camadas oficiais públicos do PDPA e o GeoPackage público IBGE. A API copia as referências públicas para o volume persistente na inicialização e grava dados gerados em volumes.

A integração de imagens foi migrada do endpoint hf-inference descontinuado para o SDK oficial (huggingface-hub 2.1.1) com HF_IMAGE_PROVIDER=auto e modelo/provedor configuráveis no Compose. Geração real de uma imagem FLUX.1-schnell, cache sem consumo adicional e PDF com a imagem foram validados.

HF_TOKEN foi reutilizado do .env local conforme autorização e validado em /api/whoami-v2 (200). ML_ACCESS_TOKEN permanece vazio; anúncios de mercado aguardam credencial e dados reais. A avaliação usa a estimativa hedônica quando não há modelo treinado. Comparação de mercado retorna 503 explícito quando a base local de comparáveis está ausente.

O arquivo IBGE de bairros fornecido não contém o município 3152501 (Pouso Alegre): a importação registra a ausência da fonte e não inventa bairros. A população pode usar o fallback já existente quando a fonte IBGE de setores não responde. Os coletores dependem da disponibilidade dos serviços públicos e da rede da VPS.

## Validação executada

Compose validado sem build, env_file, bind mounts, âncoras, aliases ou blocos x-*. Stack isolada ri-hostinger-test-a10dda com volumes novos; banco inicializado do zero e migrações automáticas verificadas antes dos testes.

71 testes do projeto (incluindo regressões de meses Sentinel-2 vazios) e 7 subtestes passaram com integração PostGIS ativada na API final; Avisos de depreciação das dependências registrados na execução. 28 verificações pelo nginx passaram: SPA, cadastro/login, autenticação, senha incorreta, origem estrangeira, CRM, isolamento entre usuários, atualização de status, estimativa, análise de conceito, PDF, avaliação legal/anexos, séries temporais, status de pipeline, MLops e GeoJSONs. A ausência de base de mercado foi validada como 503 esperado.

O mapa base CARTO retornava imagens exigindo API key; foi substituído pelos tiles padrão OpenStreetMap, com atribuição preservada e cache normal do navegador. Política do provedor: https://operations.osmfoundation.org/policies/tiles/ .

No navegador, cadastro/login, dashboard, criação de lead, score e alteração de status, avaliação e conceitos foram verificados. O acesso real http://192.168.0.107:18087 funcionou com login e dados persistidos após reinício; uma origem sem a porta correta foi rejeitada com 403. Nenhum Set-Cookie é usado pelo login.

MinIO: criação de bucket, PUT/GET autenticados de objeto sintético. MLflow: criação de experimento/run, gravação e leitura de métrica. Saúde dos cinco serviços e persistência PostgreSQL verificadas. Dependências Python e imports nativos rasterio/rioxarray/stackstac/LightGBM/MLflow verificados. Auditoria da imagem final confirmou ausência de envs, bancos, chaves e dados privados.

Coleta real inicial: limite municipal, grade de 711 células, 484 POIs, 125 estabelecimentos de saúde, hidrografia (1565 feições), suscetibilidade SGB/CPRM (3922 feições), MapBiomas (711 células), features, 22 zonas oficiais (400 células atribuídas; 311 fora do zoneamento), população e atualização das views materializadas. Risco, scores e calibração foram executados sobre as camadas reais para 711 células; o processamento de índices também foi verificado. A coleta inicial de 12 meses Sentinel-2 não foi concluída integralmente: uma janela sem cenas úteis expôs EmptyDataError, corrigido com schema vazio válido e regressões que verificam 12 meses vazios e a preservação de meses válidos. Uma janela real de um mês foi testada após a correção: CLI terminou com sucesso, 711 células e nenhuma cena disponível no período, sem fabricar índices. O estado anterior à correção foi registrado em tmp/hostinger-validation/pipeline-before-final-update.json. Não se afirma cobertura histórica real completa ou qualidade suficiente de todos os indicadores.

Todas as imagens tiveram pull Docker sem credenciais usando um diretório de configuração separado e manifests/camadas verificados com token público anônimo. Isso confirma disponibilidade pública para a Hostinger baixar; não representa teste dentro da VPS, à qual não houve acesso. Recursos, arquitetura real e firewall da VPS não foram inspecionados.

## Limpeza

Somente containers, rede e sete volumes da stack ri-hostinger-test-a10dda são removidos após validar. Nenhum docker prune, compose existente ou volume de outra stack é alterado. Imagens publicadas e arquivos de implantação permanecem. Contas/contatos e objetos sintéticos pertencem exclusivamente aos volumes temporários removidos.
