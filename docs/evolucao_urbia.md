# Evolução da Urbia por ambientes de trabalho

Plano de referência: proposta de inteligência territorial por público fornecida pelo usuário.

## Implementado em 12/10/2026

- Entrada própria para Invest, Mercado, Incorpora e Governo, com duas decisões por ambiente.
- Jornadas com etapas navegáveis conectadas às ferramentas existentes.
- Início acessível mesmo quando o carregamento dos dados territoriais falha.
- Retorno ao início e descarte da jornada ao trocar o perfil.
- Navegação geral sem numeração universal de etapas.
- Resultados esperados e limitações descritos em cada jornada.

Essa entrega organiza a experiência. Não altera as metodologias de cálculo nem cria um estudo integrado persistente: as ferramentas mantêm seus próprios dados e filtros. Navegar por uma etapa não significa que ela foi concluída.

## Próximas entregas

1. Projetos persistentes com seleção de terreno/região compartilhada entre etapas e relatório integrado.
2. Jornada pública com população, capacidade de equipamentos, proveniência e critérios próprios de priorização.
3. Viabilidade de terrenos com restrições, infraestrutura, cenários e premissas financeiras documentadas.
4. Organizações, membros e permissões no backend, separadas do perfil de trabalho.
5. Ambientes Obras e Negócios e expansão dos módulos financeiros e comerciais.

Perfis disponíveis continuam sendo os quatro existentes. Não tratar seleção de perfil como autorização institucional.

## Estudos persistentes de terrenos

O ambiente Incorpora agora oferece **Projetos de terrenos**, acessível também pela jornada **Estudar a viabilidade de um terreno**. As quatro etapas compartilham a região escolhida e as premissas salvas:

1. Terreno e região: escolha de célula H3 no seletor ou mapa.
2. Premissas: dimensões informadas do lote, área prevista, pavimentos, tipologia, acabamento e observações.
3. Restrições e cenários: cálculo no servidor usando os indicadores territoriais atuais e a triagem legal existente.
4. Relatório: exportação Markdown única com premissas, evidências, artigos/fontes legais, cenários e limitações.

A tabela `land_studies` é criada junto com o schema de autenticação na primeira requisição ao banco. Projetos pertencem ao usuário autenticado; listar, ler, salvar, analisar e exportar exigem a propriedade do registro. A revisão controla concorrência: edição com revisão antiga retorna 409. Alterar a área, o uso ou premissas invalida a análise; alterar apenas nome/observações preserva as evidências. Um relatório sem análise atual identifica explicitamente a pendência. Não há salvamento automático: use **Salvar projeto** antes de sair da ferramenta.

O registro de análise contém uma cópia dos indicadores e fontes disponíveis na execução. Data de captura não representa atualização das fontes. Célula H3 não é polígono cadastral. Cenários reutilizam as heurísticas existentes e não comprovam permissibilidade urbanística nem substituem orçamento técnico. Projetos institucionais compartilhados e limites cadastrais continuam pendentes.

### Validação

- Build de produção do frontend com dependências instaladas em pasta temporária (o `node_modules` versionado permanece intacto).
- Testes da API: `python -m pytest tests/test_land_projects.py tests/test_api_auth.py tests/test_concept.py tests/test_legal_audit.py tests/test_plan_director.py -q`.
- Para testar persistência no PostgreSQL descartável, defina `URBIA_TEST_DATABASE_URL` antes de executar **apenas** `tests/test_land_projects.py`. Esse conjunto cria e remove schemas temporários próprios: use um banco descartável de testes.
- Testes de interface: iniciar `vite preview --host 127.0.0.1 --port 4175` e executar `node frontend/tests/workspaces.cjs` com Playwright disponível em `NODE_PATH` e Chrome instalado. O teste usa respostas controladas nas fronteiras HTTP; persistência e autenticação reais são verificadas separadamente nos testes da API/PostgreSQL.
- Verificação de desktop e celular, retomada após recarregar, exportação e oito entradas de jornadas.

As próximas prioridades passam a ser a jornada pública com metodologia própria e organizações/permissões. O estudo de terreno ainda pode evoluir com polígonos de lotes e fontes adicionais de infraestrutura e topografia.

Os Dockerfiles do frontend (desenvolvimento e Hostinger) usam Node 22, atendendo ao requisito de uma dependência presente no lockfile. O build também mostrou avisos de tamanho do bundle do mapa e alertas do `npm audit` nas dependências existentes; a atualização de dependências deve ser tratada em uma entrega própria, sem aplicar atualizações com quebra de compatibilidade automaticamente.

Resultado final: 35 testes relevantes da API/motores passaram; persistência e cadastro/login foram exercitados no PostgreSQL isolado em Docker. A imagem do frontend compilou com Node 22. O motor de cenários também foi corrigido para preservar scores e confiança iguais a zero, em vez de substituí-los pelos valores padrão.

## Diagnóstico de equipamentos — Urbia Governo

A jornada **Investigar carências de equipamentos públicos** agora abre um diagnóstico próprio, também disponível em **Equipamentos públicos**. Permite escolher escolas/creches ou atendimento hospitalar, informar uma referência exploratória de distância, filtrar prioridades, examinar as regiões no mapa e exportar a mesma captura em Markdown.

O endpoint autenticado `GET /api/government/diagnosis` lê `geo.features`, agrega `geo.census_h3` quando disponível e consulta fontes com status `ok` no registro existente. Não utiliza os scores imobiliários nem gera dados demonstrativos quando o banco falha (retorna 503).

Metodologia `triagem_acesso_v1`: 60 pontos para distância, limitada à referência informada, e 40 para contagem de estabelecimentos igual a zero. População positiva é necessária para ranquear e desempata resultados; não multiplica o score. Valores nulos, negativos ou não finitos permanecem pendentes. Uma população censitária igual a zero não é substituída por uma estimativa positiva. A fonte individual da população e o momento de processamento acompanham o registro exportado.

A distância é um parâmetro exploratório escolhido pelo usuário, não um padrão legal. Os indicadores atuais não distinguem oferta pública/privada e não possuem vagas, capacidade, faixa etária ou tempo de viagem. Consequentemente, o resultado prioriza investigação e não dimensiona necessidade de novas unidades. Capacidade e dados censitários por faixa etária permanecem pendentes de integração com fontes verificadas.

Alterar serviço ou distância invalida a apresentação/exportação anterior até gerar outro diagnóstico. O relatório é produzido no servidor junto com os resultados; o download preserva essa mesma captura.

Validação desta etapa: build do frontend aprovado; 48 testes relevantes aprovados (incluindo leitura no PostgreSQL isolado em Docker, tabelas opcionais e preservação de zeros); oito entradas de jornadas verificadas no navegador, com filtro de dados pendentes, atualização de parâmetros e exportação do diagnóstico. Layout conferido em desktop e celular. Nos testes de interface, respostas HTTP são controladas; a consulta ao banco é exercitada separadamente no teste de integração.

Para executar o teste de consulta, usar **somente um banco descartável** via `URBIA_GOV_TEST_DATABASE_URL` e rodar `tests/test_public_services_postgres.py`. O teste exige schemas `geo`/`ops` inexistentes, cria suas próprias tabelas e remove esses schemas no encerramento.

## Equipes e permissões — 14/10/2026

A página **Equipes e acesso**, disponível nos quatro perfis, permite criar equipes e incluir contas já cadastradas. Não envia convites ou emails. Uma equipe criada com nome institucional não representa validação da instituição.

Permissões próprias da equipe, consultadas no banco em cada requisição:

- Responsável (`owner`): gerencia membros e possui edição dos projetos compartilhados. Não pode remover/rebaixar a si próprio nesta versão, evitando equipes sem responsável.
- Editor (`editor`): cria, altera e recalcula projetos da equipe.
- Leitor (`viewer`): consulta projetos e exporta relatórios, sem edição ou recálculo.

O campo de perfil do usuário permanece usado pela navegação, mas não concede permissões de equipe. Apenas o responsável vê e gerencia a lista de membros. Rebaixar ou remover um membro altera o acesso nas próximas requisições, sem depender de renovar o token.

Projetos existentes continuam pessoais. Ao criar um estudo, o usuário pode escolher contexto pessoal ou uma equipe em que tem edição. Um projeto pessoal salvo pode ser compartilhado explicitamente, com confirmação de alcance e revisão atual. Projetos compartilhados passam a seguir exclusivamente as permissões da equipe: o autor removido perde acesso, mesmo sendo o criador. Nesta versão não há transferência entre equipes nem retorno automático ao contexto pessoal.

As tabelas `organizations`, `organization_members` e `project_organizations` são criadas no mesmo mecanismo de inicialização do schema já utilizado pela autenticação. A associação fica em tabela separada; não altera colunas ou conteúdo dos estudos legados. A atualização foi testada preservando nome, revisão e notas de um projeto legado.

O frontend identifica leitores e bloqueia campos, salvamento e recálculo, mantendo o download. Essas restrições também são verificadas pelo backend, inclusive em chamadas diretas às rotas. Os projetos pessoais de outros membros não se tornam visíveis ao entrar em uma equipe.

Testes de interface: `frontend/tests/teams.cjs` cobre criação, adição, mudança de acesso, remoção, leitura/exportação sem edição e celular; respostas HTTP são controladas. Testes reais de permissões e persistência são exercitados em schemas temporários do PostgreSQL no Docker. As oito jornadas anteriores também foram verificadas no navegador.

Limites desta entrega: as permissões se aplicam aos projetos de terrenos compartilhados. Diagnósticos públicos não foram transformados em documentos privados de equipe. Convites pendentes, transferência de responsabilidade, auditoria de alterações e verificação institucional continuam pendentes.

Resultado final desta etapa: 53 testes relevantes passaram, incluindo equipes, isolamento, leitor/editor, proteção do responsável, remoção do autor de projeto compartilhado, revisão concorrente e preservação de dados legados. Build de produção aprovado. Interface de equipes e leitura/exportação conferida em desktop e celular; jornadas anteriores continuam passando no teste de navegador.

## Estudo financeiro informado — 14/10/2026

Em **Projetos de terrenos → Premissas**, a opção **Incluir análise financeira** acrescenta aquisição do terreno, construção por m², outros custos, contingência, área vendável, preço de venda, despesas/tributos sobre vendas, prazo, taxa de desconto e variações para sensibilidade. Exige origem declarada e data de referência antes de calcular. Não preenche preços ou taxas automaticamente. Zeros explícitos são válidos onde fazem sentido; campos vazios mantêm o cálculo pendente.

O modelo `sale_cashflow_v1` é independente dos cenários heurísticos de tipologia. Mantém as áreas informadas e compara cenário base, pressão (construção mais cara e venda menor) e alívio (construção mais barata e venda maior), nas variações escolhidas pelo usuário. Calcula custo total, receita líquida, lucro, margem sobre venda bruta, ROI do empreendimento, preço de equilíbrio, valor presente líquido e déficit máximo do fluxo mensal.

Fluxo declarado: terreno no mês zero, construção e contingência distribuídas ao longo do prazo, outros custos no primeiro mês e venda integral no último. A taxa mensal é equivalente à anual informada. Os montantes e os rateios conciliam a centavos nos casos de teste. O modelo não calcula automaticamente financiamentos, inflação, pré-vendas ou tributos legais; estes últimos devem estar representados nas despesas informadas, sem duplicação. Não é uma previsão de mercado nem comprova aprovação urbanística.

As premissas e resultados ficam no JSON do projeto, com as permissões já existentes. Alterar premissas financeiras invalida os resultados anteriores; leitores consultam e exportam sem editar/recalcular. Estudos antigos sem o campo financeiro continuam utilizáveis. A área vendável não pode superar a área construída informada. O relatório Markdown inclui premissas, cenários, indicadores, limitações e o registro completo do fluxo de caixa.

Durante a regressão, a autenticação de projetos/equipes foi ordenada antes da inicialização do banco: requisições sem token agora retornam 401 mesmo sem banco disponível, sem tentar criar tabelas primeiro.

Validação: 69 testes relevantes passaram, incluindo contas e permissões anteriores, cálculo financeiro, desconto equivalente, perdas, sensibilidade extrema, dados pendentes, validações, rateio mensal e preservação/invalidação das premissas no PostgreSQL descartável do Docker. Build aprovado. A interface financeira foi verificada em desktop/celular com premissas e respostas HTTP controladas. `frontend/tests/financial.cjs` usa uma captura do motor em `URBIA_FINANCIAL_FIXTURE` (padrão temporário `/private/tmp/urbia-finance-fixture.json`), gerada com `evaluate_financial`. A consulta/persistência real é exercitada nos testes da API.

Próximas frentes do plano: viabilidade técnica com dados de lote/infraestrutura/topografia e ambientes Obras/Negócios; dados públicos de capacidade e faixa etária; auditoria de alterações e colaboração institucional mais completa.

Na conferência visual, foi corrigida a largura interna do painel financeiro: a tabela mantém rolagem horizontal própria, sem alargar cartões ou cortar valores no celular. O teste verifica também o limite do painel dentro do contêiner, além da largura geral da página.

## Obras, Negócios e estudos comparáveis — 15/10/2026

Os seis ambientes estão disponíveis no cadastro e no seletor **Modo de trabalho**: Invest, Mercado, Incorpora, Governo, Obras e Negócios. Cada ambiente tem duas jornadas de entrada. Todos podem acessar projetos e comparações. Trocar o modo muda a navegação; as permissões continuam definidas pelo proprietário e pela equipe. A preferência é persistida em `user_workspaces`, separada do papel de conta legado, preservando administradores existentes. Contas novas usam papel interno `client`; selecionar Governo não concede autoridade institucional.

**Urbia Obras:** novos estudos incluem um dossiê técnico com declividade informada, acesso, água, esgoto, energia, drenagem, referências cadastrais, topográficas e geotécnicas, origem e data. Cada informação pode permanecer desconhecida. O resultado identifica pendências e indisponibilidades declaradas; documentação preenchida significa prontidão para revisão, sem aprovação técnica automática. Referências são textos, sem upload ou autenticação de documentos nesta etapa. Alertas legais e territoriais permanecem visíveis.

**Urbia Negócios:** novos estudos partem do uso comercial e de critérios persistentes para farmácia ou mercado. O usuário escolhe população mínima da célula, distância mínima ao serviço, justificativa e data. A triagem `commercial_criteria_v1` confronta esses critérios com população estimada, quantidade de estabelecimentos mapeados e menor distância disponíveis na captura territorial. Dados ausentes permanecem pendentes; zero é preservado. Não calcula demanda, área de influência, faturamento, concorrência efetiva ou recomendação de abertura. A data de processamento dos indicadores não representa coleta dos POIs. Bloqueio na triagem legal não é afastado pelo atendimento aos critérios comerciais.

**Cálculo sem dados territoriais:** a ação **Calcular somente premissas declaradas** permite preparar os blocos financeiro, técnico e comercial sem região selecionada ou banco geográfico disponível. A captura é marcada `premises_only`, não consulta fontes espaciais, mantém a triagem legal por analisar e não produz cenários territoriais heurísticos. Indicadores comerciais ausentes ficam pendentes. A análise integrada continua exigindo uma região disponível no servidor. As duas ações exigem edição e revisão atual do projeto.

**Comparação:** até três estudos pessoais ou compartilhados podem ser confrontados, com revisão, região, uso, captura, modo de cálculo, triagem legal, evidências técnicas, setor, indicadores e critérios comerciais, áreas, premissas e indicadores financeiros. A comparação usa a última análise salva, não recalcula nem escolhe vencedor. Datas, áreas e taxas diferentes exigem atenção do usuário. Há exportação Markdown e rolagem própria no celular.

**Histórico:** criação, edição, análises e compartilhamento registram ator, horário UTC, revisão, ação e campos alterados em `land_study_events`, na mesma transação da alteração. Conflitos não geram eventos. A consulta verifica acesso atual; remover um membro também revoga o histórico. A interface pagina 50 eventos, sem duplicar revisões; o relatório inclui até 100 recentes. Projetos legados começam a registrar eventos nas próximas alterações, sem reconstruir atividades passadas. É um registro de atividades, sem cópias históricas dos valores, restauração de versões ou assinatura contra adulteração.

**Continuidade da edição:** alterações não salvas pedem confirmação ao navegar, trocar modo, abrir outro estudo ou sair. Operações em andamento impedem navegação conflitante. Cancelar a saída mantém a sessão e o rascunho. Alterar dados relevantes, inclusive critérios comerciais, invalida resultados até novo cálculo; editar apenas observações preserva a análise.

**Validação:** 102 testes relevantes passaram, com persistência e permissões em schemas temporários de PostgreSQL 17 no Docker, testes dos motores, relatórios, invalidação, histórico, paginação, preferência sem promoção de conta e cálculo sem consulta territorial. Build de produção aprovado. Os testes de navegador usam respostas controladas; não comprovam cobertura geográfica em produção. A consulta real e a persistência são exercitadas separadamente na integração.

Arquivos de conferência no navegador: `frontend/tests/workspaces.cjs`, `teams.cjs`, `financial.cjs`, `expansion.cjs` e `business.cjs`. O gerador `frontend/tests/generate_fixtures.py` produz capturas controladas dos motores financeiro, técnico e comercial. Executar a partir da raiz com `PYTHONPATH=src python frontend/tests/generate_fixtures.py --output-dir /private/tmp`; os três scripts correspondentes aceitam `URBIA_FINANCIAL_FIXTURE`, `URBIA_TECHNICAL_FIXTURE` e `URBIA_BUSINESS_FIXTURE`. Os scripts esperam a interface em `http://127.0.0.1:4175`, Playwright disponível e Chrome instalado.

Próximas frentes ainda dependentes de desenvolvimento ou fontes verificadas: capacidade pública e população por faixa etária, validação das regras e camadas oficiais por município, dados comerciais de fluxo/renda/cobertura com origem e atualização, anexos documentais e colaboração institucional mais completa. Nenhuma implantação em produção foi realizada nesta etapa.

## Revisões consultáveis e recuperação de premissas — 15/10/2026

O **Histórico de atividades** dos estudos agora permite abrir o conteúdo das revisões preservadas. A tela apresenta diferenças de premissas em relação à revisão atual salva, todos os valores de entrada e, quando existentes, os resultados financeiros, técnicos e comerciais históricos. A data da análise histórica permanece explícita; consultar uma revisão não recalcula seus resultados. Alterações ainda não salvas não entram na comparação.

**Recuperar premissas desta revisão** cria uma nova revisão com nome, região, uso, observações e premissas da revisão escolhida. Mantém o identificador, a criação e o compartilhamento atuais do projeto. A análise fica sempre pendente, mesmo quando a captura antiga tinha resultados; é necessário calcular novamente. A revisão de origem é registrada no histórico e no relatório. A recuperação exige confirmação na interface, edição autorizada, ausência de rascunho pendente e revisão atual. Leitores podem consultar versões, mas não recuperá-las. Conflitos retornam 409 e preservam o conteúdo atual.

A tabela adicional `land_study_versions` armazena nome, documento, revisão, momento de preservação e eventual revisão de origem. Cada alteração bem-sucedida grava a captura, o registro de atividade e o documento atual na mesma transação. Não há endpoint para alterar capturas antigas. As premissas são revalidadas pelo schema atual antes da recuperação; conteúdo incompatível retorna 422 sem gravar alterações. A leitura e recuperação sempre verificam as permissões atuais: retirar um membro revoga também seu acesso às versões antigas.

**Compatibilidade:** projetos novos têm captura desde a criação. Ao alterar um projeto existente, a última revisão ainda disponível é preservada como captura inicial, além da nova revisão. Revisões anteriores cujo conteúdo já foi sobrescrito não são reconstruídas; atividades antigas sem captura continuam no histórico. Uma captura inicial sem evento original aparece separadamente, sem inventar autor ou data da alteração antiga. O momento de preservação não é apresentado como momento original de criação da revisão. O compartilhamento avisa que histórico e versões preservadas passam a ser acessíveis à equipe, inclusive conteúdo anterior ao compartilhamento.

Não há limpeza automática das capturas nem assinatura contra alterações administrativas diretas no banco. Esta entrega recupera premissas do estudo, sem restaurar permissões, membros de equipes ou análises antigas como resultados atuais. Anexos documentais e integrações de dados oficiais permanecem nas próximas frentes.

**Validação:** 108 testes relevantes passaram, incluindo seis novos testes de recuperação e suas transações no PostgreSQL descartável do Docker. Foram exercitados preservação de valores e zeros, diferenças, resultados históricos, conflitos, acessos privados e compartilhados, leitor, revogação, captura inicial de projeto legado e revalidação de premissas antigas. Build de produção aprovado. `frontend/tests/versions.cjs` verifica interface com respostas controladas, cancelamento, rascunho pendente, conflito, recuperação, consulta de leitor e celular. A regressão de seis ambientes, histórico e navegação de `frontend/tests/expansion.cjs` também passou.

## MVP de demonstração: seis entregas próprias — 16/10/2026

A entrada de cada ambiente passou a oferecer uma decisão principal com quatro passos e uma síntese explicada. As ferramentas anteriores permanecem disponíveis como pesquisas complementares. Incorpora compara duas propostas de empreendimento; Obras organiza investigação técnica e tarefas; Invest compara até três compras/revendas e orçamento; Mercado prepara apresentação com comparáveis selecionados; Negócios compara pontos e visitas; Governo organiza investigação escolar.

A camada adicional de casos preserva título, tipo de decisão, município, entradas específicas, captura de resultado, tarefas, feedback privado e revisões. Projetos de terrenos não foram duplicados: Incorpora e Obras os referenciam, seguem suas permissões atuais e invalidam a apresentação quando a revisão de origem muda. Uma tarefa concluída volta a pedir revisão quando as premissas relevantes mudam, preservando a referência anterior separadamente.

A interface distingue demonstrações, declarações, fontes registradas e informações ausentes. A primeira leitura mostra conclusão, até três motivos, consequências, pendências e próxima ação; códigos e memória técnica ficam nos detalhes. Comparáveis de outro município, finalidade, tipo, área ou período são excluídos com explicação. A comparação legada também foi restringida e deixou de ampliar amostras silenciosamente.

Pouso Alegre continua sendo a primeira integração territorial. Administradores podem cadastrar outras cidades para estudos declarados, sempre com cobertura pendente. O cadastro não ativa regras ou preços de Pouso Alegre. O catálogo de fontes expõe referência, coleta, condição de uso e limitações; não representa certificação de cobertura integral.

Cada ambiente tem exemplo isolado, editável, retomável e reiniciável. Os exemplos são fictícios e explicitamente identificados; não entram nas tabelas geográficas reais. Há apresentação HTML imprimível/salvável em PDF, com página executiva, comparação, tarefas e anexo legível. A memória completa permanece no Markdown e nos detalhes técnicos.

Para apresentação a parceiros: Compose separado com Caddy/HTTPS, cadastro por código de convite e opção de lista de emails, recuperação de acesso assistida por administrador com código de uso único, invalidação de sessões após troca de senha, métricas agregadas e logs operacionais sem corpo ou parâmetros de consulta. A emissão real de certificado e a implantação pública continuam dependentes de domínio, DNS e acesso ao servidor.

A rotina de backup foi validada com dados sintéticos de integração e restauração em banco novo descartável: um usuário, sete casos e 32 revisões. Não houve restauração sobre o banco de origem nem implantação em produção. Os seis fluxos foram exercitados no navegador com API autenticada e PostgreSQL reais de teste, incluindo salvamento, reabertura, cálculo, tarefas, PDF, teclado, celular, dúvidas privadas e interesse. As regressões anteriores de jornadas, equipes, finanças, comercial e revisões também passaram. Build local, build da imagem de frontend com Node 22, configuração nginx e Compose de parceiros foram aprovados.

O guia de produto, roteiro de apresentação, interfaces, operação e limitações está em [mvp_parceiros.md](mvp_parceiros.md). Metas de compreensão em um minuto e interesse de dois parceiros continuam sendo hipóteses a validar com pessoas; testes automáticos não comprovam valor comercial.

Resultado final de validação desta entrega: **152 testes relevantes passaram**, incluindo integração PostgreSQL, proteção das rotas, comparáveis e precisão numérica, registro de municípios, convite para cadastro, recuperação de acesso, privacidade dos logs e os mecanismos anteriores. Permanecem dois avisos de depreciação de dependências no ambiente de testes. Não foram alteradas as dependências versionadas em `frontend/node_modules`.

## Apresentação visual — 18/10/2026

A identidade visual passou a usar verde, superfícies claras, tipografia sem serifa e ícones vetoriais consistentes. A página pública apresenta as seis entregas próprias, um percurso em quatro etapas e ilustração territorial explicitamente identificada. A página de cada ambiente destaca a ação principal, o que será entregue e as pesquisas complementares. A troca de perfil está no topo do menu.

Login, cadastro, formulários, etapas e síntese compartilham a mesma apresentação. Os exemplos continuam identificados como simulações; não foram criados indicadores, avaliações ou fontes para compor o visual. O nome e o ícone da aba foram atualizados para Urbia. A atualização local preserva o banco, as contas e os casos existentes.

A conferência automatizada está em `frontend/tests/presentation.cjs`: navegador real conectado ao Docker, cadastro/login, seis ambientes, exemplos, relatórios, larguras de celular e ausência de erros de JavaScript. Capturas permitem inspecionar página inicial, acesso, ambiente e síntese. Executar com Playwright e Chrome disponíveis; a URL é configurável por `URBIA_PRESENTATION_URL` e a pasta de capturas por `URBIA_SCREENSHOTS`. Cada execução cria uma conta sintética própria.

## Primeiro uso e biblioteca de casos — 18/10/2026

Após o relato de desorientação em “Meus casos e decisões”, a entrada passou a apresentar dois caminhos: conhecer um exemplo preenchido ou escolher o trabalho de um caso real. A lista usa cartões dos seis ambientes, com situação da análise e separação explícita entre casos reais e exemplos. Abrir um caso com resultado atualizado leva à síntese; casos incompletos ou desatualizados voltam ao preenchimento. O formulário usa o tipo do caso aberto, independentemente do modo de trabalho da conta.

O exemplo explica por onde ler e oferece atalhos para os dados e relatório. Cada etapa orienta o que informar e o que separar para a próxima. Projeto e equipe ficam em opções complementares; campos ausentes não recebem dados fictícios. A ação principal na página inicial continua abrindo um caso novo do ambiente escolhido. Voltar à biblioteca pede confirmação se houver alterações não salvas.

`frontend/tests/case-library.cjs` verifica a biblioteca vazia, o exemplo e seu relatório, filtros de dados reais/simulados, criação sem copiar valores demonstrativos, seleção de outro ambiente, salvamento, reabertura, leitura direta de análise e proteção de alterações. A verificação usa uma conta sintética própria na API Docker local; não altera contas existentes.

### Redução da carga visual na navegação

A biblioteca passou a se chamar “Minhas análises”, com uma ação principal “Nova análise”, um atalho compacto para exemplo preenchido e uma lista de trabalhos salvos. A escolha entre as seis decisões abre uma tela própria, com perguntas concretas em vez de apresentar todos os caminhos junto com o histórico. Trabalhos salvos aparecem em linhas com situação legível: falta preencher, resultado pronto ou revisar dados. As ferramentas complementares do menu ficam recolhidas em “Mais ferramentas”, acessíveis por teclado. Campos principais usam a palavra “análise” para manter o mesmo vocabulário da entrada ao salvamento.

## Retomada local e navegação — 19/10/2026

Os três serviços locais estavam parados e foram reiniciados, preservando os volumes. Foi reproduzido e corrigido um retorno sem efeito: clicar em “Minhas análises” enquanto o editor já estava aberto agora retorna à biblioteca e mantém a confirmação de descarte quando há rascunho. No celular, cancelar a navegação mantém o menu e o rascunho disponíveis. Ferramentas sem dados territoriais permitem abrir a explicação da indisponibilidade e voltar às análises.

`frontend/tests/navigation.cjs` passou com API e banco locais reais; somente a resposta de scores é substituída por lista vazia para testar a falta de dados. Cobertura: retorno pelo próprio item do menu, cancelamento/aceitação de descarte, orientação em ferramenta sem dados e navegação móvel. API, banco e interface saudáveis ao final.

## Guia Como usar — 19/10/2026

“Como usar” fica no menu principal de todos os ambientes. O guia abre sobre a tela atual, com fechamento por botão ou Escape, sem apagar o rascunho. Quatro passos explicam exemplo preenchido, criação com dados próprios, leitura da síntese e salvamento/reabertura/PDF. O preparo sugerido acompanha o ambiente atual e as dúvidas comuns explicam campos ausentes, escolha entre as seis jornadas e falta de dados no mapa.

Os atalhos abrem um exemplo isolado, uma análise nova do ambiente atual ou a biblioteca. A abertura de outro trabalho mantém a confirmação de descarte; cancelar mantém o guia aberto. Um clique no exemplo cria uma única demonstração. Testes de navegador em `frontend/tests/help.cjs` verificam esses fluxos com API real, leitura sem perder rascunho, Escape, celular e conteúdo por ambiente. As contas e os estudos existentes são preservados.
