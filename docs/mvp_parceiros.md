# Urbia — demonstração dos seis ambientes

## O que foi implementado

O início de cada ambiente tem uma decisão principal. As ferramentas anteriores continuam em **Ferramentas e pesquisas complementares** e no menu. **Meus casos e decisões** permite salvar, retomar e comparar as informações sem depender da leitura de um mapa.

| Ambiente | Entrega principal | Limite desta versão |
| --- | --- | --- |
| Incorpora | Duas propostas com produto, áreas, custos, receitas, resultado, VPL e sensibilidade | Áreas declaradas; não calcula potencial construtivo legal validado |
| Obras | Evidências do projeto convertidas em plano de investigação com tarefas | Referências e infraestrutura declaradas, sem aprovação técnica |
| Invest | Até três alternativas de compra e revenda, orçamento, capital, sensibilidade e fluxo de desembolso/venda | Sem aluguel, financiamento ou valorização automática; ROI não anual |
| Mercado | Ficha comercial, comparáveis selecionados, diferenças, argumentos e perguntas ao proprietário | Referência descritiva dos anúncios; sem laudo ou preço de transação comprovado |
| Negócios | Até três pontos, aluguel/custos, visita, acesso, visibilidade e contexto territorial disponível | Sem demanda, faturamento ou autorização automática de funcionamento |
| Governo | Regiões para investigação escolar, justificativas, evidências e tarefas de vistoria | Sem déficit de vagas ou recomendação de construção de escolas |

Os quatro passos são **Seu objetivo → Informações essenciais → Confira os dados → Sua análise**. O resultado tem conclusão, até três motivos, consequências, pendências e próxima ação. Fontes, premissas e memória completa ficam nos detalhes.

A análise é produzida por regras e cálculos explícitos, sem depender de um serviço externo de linguagem. Não há percentual genérico de confiança nem vencedor universal entre alternativas.

## Casos reais, demonstrações e municípios

- **Conhecer exemplo demonstrativo** cria um caso pessoal isolado e já analisado. Seus valores e observações são fictícios, identificados na tela e no relatório. Não importa fixtures nas tabelas territoriais nem cria projetos de terreno reais.
- **Catálogo** separa casos reais de demonstrações. Reiniciar exige a revisão atual e funciona somente para uma demonstração pessoal sem vínculo institucional ou projeto real.
- Casos reais usam informações declaradas e, quando disponíveis, capturas territoriais do servidor. O exemplo isolado não é convertido silenciosamente em caso real.
- Pouso Alegre, código IBGE `3152501`, é a primeira integração. O catálogo exibe fontes registradas, referência, coleta, condição de uso e limitações por tema. Registro de carga não comprova cobertura integral ou validade de uma conclusão.
- Administradores podem cadastrar outros municípios em **Equipes e acesso**. O cadastro nasce com cobertura territorial pendente e permite estudos declarados. Integrar fontes locais e validar regras é uma etapa adicional; cadastrar um nome não habilita parâmetros de Pouso Alegre.
- Também é possível iniciar um caso com outro código IBGE. Sem cadastro, o nome será apresentado como município e código, com cobertura pendente. Códigos e nomes fornecidos pelo operador não são validados automaticamente no IBGE nesta entrega.
- A adaptação territorial atual funciona apenas para Pouso Alegre e quando a configuração da instância corresponde ao município. Outras cidades não recebem seus preços, indicadores ou regras por fallback.

## Colaboração e continuidade

Incorpora e Obras podem vincular um projeto de terreno. Premissas do terreno não são editadas novamente no caso; ficam no projeto original. Um caso salvo sem vínculo pode recebê-lo uma vez, com confirmação de que o histórico também passará a seguir as permissões atuais do projeto. Casos de equipe só podem receber projeto da mesma equipe.

O resultado guarda a revisão do projeto usada na captura. Se essa revisão mudar, a síntese fica desatualizada e o relatório exige novo cálculo. Remover um membro revoga seu acesso aos casos vinculados, incluindo tarefas e exportações. Leitores consultam e exportam; não editam ou recalculam.

Mudanças de entradas invalidam a análise. Tarefas concluídas voltam a ficar pendentes de revisão, preservando a evidência anterior separadamente. Concluir novamente exige registrar evidência. Alteração concorrente retorna 409 e não cria uma revisão parcial.

Observações sobre compreensão e dúvidas ficam privadas no caso. Navegação registra somente evento, etapa, horário e identificador do caso. O endpoint administrativo de métricas retorna contagens, sem textos, documentos ou valores financeiros. Esses eventos medem utilização de casos salvos; não representam um estudo de comportamento de visitantes anônimos.

## Relatórios

**Abrir relatório para PDF** abre uma apresentação HTML da mesma captura salva. Use **Imprimir → Salvar como PDF** no navegador. Não há dependência de um serviço externo para essa exportação.

A primeira página é executiva. As seguintes trazem comparações, tarefas e anexo de premissas/fontes em linguagem legível. A memória integral, incluindo fluxos mensais financeiros, fica nos detalhes técnicos e no Markdown complementar. Observações privadas de feedback não entram no relatório comercial.

PDFs de conferência foram gerados com Chrome em A4, incluindo a marcação de simulação. O número de páginas depende do conteúdo. Não se trata de PDF assinado ou parecer profissional certificado.

## Roteiro de apresentação

1. Iniciar por **Incorpora → Comparar propostas → Conhecer exemplo demonstrativo**. Mostrar que custo, resultado e sensibilidade são leituras diferentes. Alterar uma premissa e explicar por que o resultado deve ser recalculado.
2. Trocar para **Obras → Preparar investigação**. Mostrar uma indisponibilidade e uma evidência desconhecida. Atribuir uma tarefa, prazo e referência de conferência. Explicar que completar tarefa não é aprovar o terreno.
3. Apresentar Invest: comparar orçamento e desembolso, deixando o usuário explicar qual hipótese de venda precisaria validar.
4. Apresentar Mercado: mostrar amostra selecionada, exclusões e perguntas ao proprietário. Referências de outra cidade, finalidade, tipo, área ou período não entram silenciosamente.
5. Apresentar Negócios: confrontar dois custos de ocupação e as lacunas da visita. Diferenciar observação de concorrentes, serviços mapeados e demanda não medida.
6. Apresentar Governo: selecionar regiões e justificar vistorias; capacidade escolar permanece pendente.
7. Abrir um relatório e perguntar: **“O que você entendeu, o que ainda falta e qual seria sua próxima ação?”** Registrar a resposta na observação privada do caso.
8. Perguntar: **“Você usaria isso em qual decisão real da sua operação?”** O botão de interesse registra um evento; não envia mensagem nem constitui compromisso comercial.

Metas ainda a validar com pessoas: compreender a síntese em um minuto, distinguir Incorpora de Obras, concluir o fluxo sem orientação contínua e obter ao menos dois parceiros dispostos a testar casos próprios. Nenhuma dessas metas é declarada atingida por testes automáticos. Preço e condições do piloto serão definidos após a validação.

## Ambiente de apresentação e recuperação de acesso

`docker-compose.partner-demo.yml` é uma stack separada, construída com o código atual. Banco e API não publicam portas. Caddy usa o `Caddyfile` existente para HTTPS; a emissão de certificado exige domínio real apontado para o servidor e portas acessíveis.

Preparação pelo operador:

1. Criar um arquivo de configuração privado **fora do repositório**, usando `deploy/partner-demo.env.example` como lista de campos. Substituir todos os exemplos, usar segredos aleatórios e manter o arquivo restrito.
2. Configurar domínio, email de operação, credenciais do banco, segredo JWT, `ADMIN_EMAILS` e um código privado de cadastro `DEMO_REGISTRATION_CODE`. `DEMO_ALLOWED_EMAILS` pode restringir também os emails dos parceiros; administradores configurados são aceitos na lista.
3. Validar com `docker compose -f docker-compose.partner-demo.yml --env-file /caminho/privado/partner.env config --quiet`.
4. No servidor autorizado, iniciar com `docker compose -f docker-compose.partner-demo.yml --env-file /caminho/privado/partner.env up -d --build`.
5. O operador cadastra sua conta com o email administrativo e o código de convite. Parceiros recebem o código por um canal verificado fora da plataforma. Sem essa configuração, a aplicação legada preserva o cadastro público; o Compose de parceiros exige o código.
6. Confirmar HTTPS e consultar `/api/readiness` (banco), além de `/health` na API (processo). O banco inicia sem dados territoriais carregados; as demonstrações isoladas funcionam assim, e estudos reais indicarão lacunas.

Recuperação assistida: em **Equipes e acesso**, um administrador emite código para a conta após verificar o titular. Em **Preciso recuperar meu acesso**, o usuário informa o código e uma nova senha. O código expira em 15 minutos, só pode ser usado uma vez e é armazenado como hash. A troca de senha invalida sessões anteriores. Não há envio de email/SMS nem serviço de identidade institucional integrado.

A API registra rota-modelo, status, duração e identificador de requisição. O nginx da imagem Hostinger omite query strings, e o início da API desativa o access log padrão do Uvicorn para evitar que URLs de ferramentas legadas gravem preços. Falhas recebem identificador sem expor documentos no erro operacional. Alertas externos e escala de operação precisam ser configurados pelo responsável pelo servidor.

**Publicação pública não executada:** domínio, DNS e acesso ao servidor não foram fornecidos nesta tarefa. A validação local não comprova emissão de certificado na VPS nem disponibilidade externa.

## Execução local atualizada no Docker

`docker-compose.local.yml` compila o código atual da API e da interface e mantém banco e arquivos em volumes próprios da stack `urbia-local`. A interface fica em **http://localhost:18088**, restrita à própria máquina. O banco começa vazio; crie sua conta e use os exemplos demonstrativos de cada ambiente. As fontes territoriais precisam ser importadas separadamente para estudos reais.

O arquivo privado `.env.docker.local` (ignorado pelo Git) deve conter `URBIA_LOCAL_DB_PASSWORD` e `URBIA_LOCAL_JWT_SECRET`, com valores aleatórios. `HF_TOKEN` é opcional para iniciar, mas necessário para gerar imagens novas. `ADMIN_EMAILS` permite definir o email da conta que poderá operar o pipeline. Preserve os valores do banco entre reinicializações.

```sh
docker compose --env-file .env.docker.local -f docker-compose.local.yml up -d --build
docker compose --env-file .env.docker.local -f docker-compose.local.yml ps
docker compose --env-file .env.docker.local -f docker-compose.local.yml stop
```

`stop` preserva os dados para a próxima execução. Essa configuração local não substitui a publicação com domínio e HTTPS.

Verificação local em 16/10/2026: API, interface e PostGIS iniciados e saudáveis. Cadastro e login exercitados pela interface; os seis exemplos foram abertos, tiveram síntese e relatório conferidos e foram reabertos após recarregar a página, sem erros de JavaScript. Sem `HF_TOKEN`, a tentativa de nova imagem retornou `missing_token` e mostrou o aviso na interface. O arquivo opcional de bairros IBGE não está nesta cópia; a imagem da API permite iniciar com as referências públicas disponíveis, mantendo a lacuna da fonte.

## Verificação de IA após a publicação

A pedido do responsável pelo projeto, a conferência da publicação deve incluir IA generativa e chatbot. Registrar ambiente, data e resultado de cada teste, sem guardar credenciais ou conteúdo privado em logs.

- **Geração de imagens existente:** configurar `HF_TOKEN` no arquivo privado do servidor e conferir modelo, provedor e limite diário. O Compose de parceiros encaminha essas opções à API. Entrar com uma conta autorizada no Estúdio de Conceito, solicitar uma nova variação e confirmar imagem visível e resposta `status: generated` em `/api/concept/generate-image`. Uma resposta `cached` comprova apenas a recuperação de imagem salva; não comprova acesso ao provedor. Conferir também imagem no relatório exportado e mensagem compreensível se o provedor falhar ou o limite for atingido. A geração real pode consumir créditos do provedor.
- **Chatbot pendente:** na inspeção de 16/10/2026 não foram encontrados interface, rota ou integração de chatbot no repositório. Esse item permanece pendente de implementação ou identificação de uma versão externa. Quando disponível, testar envio e resposta reais, continuidade de uma conversa, isolamento entre contas e mensagem de indisponibilidade. Não marcar o chatbot como funcionando apenas porque a aplicação iniciou ou a geração de imagens respondeu.

Nenhuma chamada real ao provedor foi executada nesta conferência. A disponibilidade de IA no ambiente publicado depende da credencial, das permissões e do serviço externo; deve ser confirmada naquele ambiente antes da apresentação aos parceiros.

## Backup e verificação de restauração

`tools/partner_backup.py` usa os utilitários do próprio container PostgreSQL. O arquivo é criado sem sobrescrever outro, com permissão 0600. Armazenar fora do repositório e copiar para local protegido conforme a rotina do operador.

```sh
python tools/partner_backup.py backup --container NOME_DO_CONTAINER_DB --archive /caminho/privado/urbia.backup
python tools/partner_backup.py restore-check --container NOME_DO_CONTAINER_DB --archive /caminho/privado/urbia.backup
```

`restore-check` cria um banco de nome aleatório, restaura nele, consulta as tabelas da aplicação e remove somente esse banco ao terminar. Não restaura sobre a origem. O parâmetro `--schema` existe para testes isolados; o backup operacional sem ele abrange o banco completo. Arquivos dos volumes de armazenamento/modelos exigem cópia própria; este utilitário faz backup do PostgreSQL, não de todos os volumes ou da configuração do servidor.

A rotina foi exercitada com dados sintéticos de integração: um usuário, sete casos e 32 revisões recuperados em outro banco descartável. Isso não substitui um ensaio com os volumes e dados reais do futuro ambiente público.

## Interfaces e validação técnica

- Casos: `GET/POST /api/cases`, `GET/PATCH /api/cases/{id}`, `POST .../analyze`, `GET .../report?format=html|markdown`, `GET .../history`.
- Tarefas: `POST .../tasks` e `PATCH .../tasks/{task_id}`, sempre com revisão atual; conclusão exige evidência.
- Demonstrações: `POST /api/case-demos/{kind}` e `POST /api/cases/{id}/reset-demo`.
- Municípios: `GET /api/municipalities` e cadastro administrativo `POST /api/municipalities`, sempre em cobertura pendente fora de Pouso Alegre.
- Feedback privado: `POST .../feedback`. Eventos sem texto livre: `POST .../interactions`. Métricas agregadas: `GET /api/case-operations/metrics`, somente administrador.
- Recuperação: emissão administrativa em `/api/auth/recovery/issue` e conclusão pública por código em `/api/auth/recovery/complete`.

As tabelas adicionais usam o mecanismo aditivo de inicialização já existente na autenticação. Rotas e projetos legados permanecem disponíveis. A comparação legada de mercado passou a exigir metadados adequados, filtrar tipo/município/finalidade/área/período e pedir autorização explícita para ampliar amostra ao município. Referências antigas sem metadados ficam pendentes, em vez de misturar amostras.

Testes de navegador novos: iniciar `tests/case_browser_server.py` com `PYTHONPATH=.:src` e `URBIA_TEST_DATABASE_URL` apontando para PostgreSQL **descartável**, servir o frontend compilado em `127.0.0.1:4175` e rodar `node frontend/tests/decision-cases.cjs` com Playwright e Chrome disponíveis. O servidor cria schema aleatório e o remove ao encerrar. O navegador usa a API real de testes, com autenticação e persistência; geometrias de fundo não participam da demonstração.

Os scripts anteriores de jornadas, equipes, financeiro, comercial e revisões continuam como regressão. A emissão real de TLS, entrevistas com parceiros e verificação das fontes locais não são substituídas por testes de software.

Resultado de validação em 16/10/2026: **152 testes relevantes aprovados**, seis jornadas conferidas com API e PostgreSQL reais de teste, seis PDFs gerados e inspecionados, regressões anteriores de navegador aprovadas, build local e imagem de frontend com Node 22 aprovados, configuração nginx e Compose validados, backup/restauração exercitados em banco descartável. Os relatórios ilustrativos tiveram de três a seis páginas, com síntese executiva separada do anexo.
