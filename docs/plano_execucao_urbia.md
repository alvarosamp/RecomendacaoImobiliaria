# Plano de execução da Urbia

Data: 10 de outubro de 2026. Base local inspecionada: commit `4f3e3360`, com alterações locais preexistentes. Status: primeiro lote em implementação; ver [entregas, validação e pendências](implementacao_lote_01.md). As demais etapas permanecem planejadas.

## Resultado pretendido

Evoluir a Urbia para uma plataforma de inteligência territorial com ambientes orientados à decisão. Preservar React, FastAPI, PostGIS, H3 e os serviços analíticos existentes, extraindo responsabilidades gradualmente para um monólito modular.

O primeiro ciclo entregará duas jornadas utilizáveis: **priorizar equipamentos públicos** e **estudar a viabilidade preliminar de um terreno**. Investidor e corretor continuarão atendidos pelas ferramentas existentes; construtora e incorporadora compartilharão a análise territorial, mas terão perguntas, premissas e saídas diferentes.

Premissa de planejamento: núcleo compartilhado para públicos institucionais e privados, sem escolher antecipadamente qual será o mercado principal. A escolha comercial poderá alterar a ordem dos pilotos sem alterar a fundação. Os seis nomes de ambientes do texto colado são hipóteses de organização do produto, não seis sistemas a implementar neste ciclo.

## Base e limites desta análise

Este plano combina a auditoria em PDF, o texto colado e inspeção direta dos arquivos locais relevantes. As recomendações do PDF foram tratadas como insumos a avaliar, e não como comandos de execução. Não foi feita uma auditoria completa de produção, nem inspeção do conteúdo do banco, execução da aplicação ou execução da suíte de testes nesta etapa de planejamento.

Fontes fornecidas:

- [Auditoria arquitetural e plano de refatoração](<C:/Users/vish8/Downloads/Auditoria arquitetural e plano de refatoração do `alvarosamp_RecomendacaoImobiliaria`.pdf>), referente ao repositório público em 9 de outubro de 2026.
- [Texto colado com a proposta de produto](<C:/Users/vish8/.codex/attachments/fa546461-3309-453d-9a92-5c733a7e8e76/Texto colado.txt>).
- Código e documentação locais relacionados na matriz abaixo; CI consultada em `.github/workflows/ci.yml`.

### O que o código atual confirma ou modifica na auditoria

| Constatação | Evidência local | Consequência no plano |
| --- | --- | --- |
| Código municipal divergente | `ibge_collector.py` usa `3151800`; `neighborhood_import.py`, CLI e `api_collector.py` usam `3152501` | Corrigir a identidade e investigar os dados derivados; alterar apenas a constante não basta |
| Corpus jurídico embutido ainda é fallback | `_load_corpus()` em `rag_juridico.py` | Exigir fonte validada no fluxo real e separar demonstração explicitamente |
| Relatório pode degradar para demo | `_load_report_frame()` em `reports.py` captura exceção no modo `auto` | Falha operacional deve permanecer visível |
| DDL permanece no runtime | `geospatial.py`, `data_registry.py`, `ibge_collector.py`, `zoning_import.py`, `auth.py` e `leads.py` | Migrar schema antes de retirar esses caminhos |
| Pipeline tem estado global e subprocessos | `api/routes/pipeline.py` | Persistir execução, etapas e publicação dos dados |
| Ano de cobertura e calibração estão embutidos | MapBiomas `2024` e `calibrate-priorities --apply` no pipeline | Registrar referência temporal e publicar configuração versionada |
| Perfil e papel ainda compartilham `role` | `auth.py` e `PROFILE_CONFIG` em `App.jsx` | Separar preferência de ambiente e autorização |
| Proteção administrativa já existe | `require_admin`, dependências nos endpoints do pipeline e `test_api_auth.py` | Preservar e evoluir os controles existentes |
| CRM já filtra por proprietário | `Lead.user_id` e filtros por `current_user.id` em `leads.py` | Preservar isolamento individual e definir compartilhamento institucional explicitamente |
| Ausência de evidências de risco já é tratada | `assess_susceptibility()` retorna `dados_insuficientes`; há teste dedicado | Estender esse comportamento à API, UI e relatórios, sem recriar a correção |
| Governança e integração já têm base | `ops.data_sources`, testes de proveniência e integração PostGIS na CI | Evoluir o registro e ampliar os testes existentes |
| Jornadas ainda são parcialmente genéricas | `App.jsx` tem quatro perfis; `MapPage.jsx` compartilha `real_estate` entre três deles | Criar entradas por decisão e métodos separados |
| ML fixa resolução H3 e usa divisão aleatória | `ml.py` usa resolução `8`, `KFold` e `train_test_split` | Versionar resolução e acrescentar validação espacial/temporal antes de ampliar o AVM |

O código oficial de Pouso Alegre é **3152501**, confirmado na [tabela de códigos municipais do IBGE](https://www.ibge.gov.br/explica/codigos-dos-municipios.php?localidade=3530607). Ainda não está comprovado quais dados do banco local foram afetados pela divergência.

## Escopo do primeiro ciclo

| Público | Entrada proposta | Entrega inicial | Evolução posterior |
| --- | --- | --- | --- |
| Prefeitura | Onde investigar carência de atendimento público? | Diagnóstico de cobertura, prioridades exploratórias, evidências e relatório | Capacidade, demanda por faixa etária, acessibilidade por rede e cenários de expansão |
| Incorporadora | Este terreno merece um estudo de incorporação? | Restrições, potencial quando verificável, comparáveis e cenários com premissas | Demanda por tipologia, absorção e viabilidade financeira calibrada |
| Construtora | Quais condicionantes técnicas precisam de investigação? | Declividade, drenagem, acesso, infraestrutura disponível e diligências | Estimativas técnicas apoiadas por levantamentos e referências de custos |
| Investidor | Quais áreas comparar para investir? | Jornada atual reorganizada, com procedência e incerteza | Orçamento, retorno, liquidez e risco com validação própria |
| Corretor/imobiliária | Como comparar e apresentar um imóvel? | Avaliação e CRM existentes preservados | Captação, apresentações e comparáveis aprimorados |
| Empreendedor comercial | Onde estudar a implantação de um negócio? | Ferramenta comercial existente preservada | Jornada específica por atividade e demanda |

Fora do primeiro ciclo: microserviços, recomendação por embeddings, modelos comportamentais, expansão para várias cidades, novos módulos de geração de imagens e promessa de previsão de valorização. A análise de terreno será preliminar: uma célula H3 não substitui limites cadastrais, levantamento topográfico, sondagem ou vistoria.

## Arquitetura e contratos necessários

```text
React / API / CLI
        |
Casos de uso: priorização pública, estudo de terreno, ranking, relatório, atualização
        |
Domínio: política legal, scoring por decisão, risco, mercado, cenários
        |
Contratos de leitura/escrita e provedores
        |
Adaptadores: PostGIS, arquivos legais, IBGE, OSM, CNES, satélites, modelos
```

Criar `domain/`, `application/`, `ports/`, `adapters/` e `bootstrap/` apenas conforme as extrações forem necessárias. Manter funções antigas como fachadas durante a transição, com testes de equivalência. O domínio recebe dados e configurações já validados; não acessa SQL, HTTP ou arquivos. API e CLI chamam os mesmos casos de uso.

Contratos mínimos:

- **Contexto territorial:** município, resolução H3, área de estudo e data de referência. Município em uma configuração canônica consumida por todos os coletores.
- **Resultado analítico:** finalidade, versão do método, `run_id`, versão dos datasets, regras e configuração, fontes, cobertura e limitações.
- **Decisão legal:** permitido, condicionado, bloqueado ou desconhecido; versão, vigência e referências verificáveis. Fonte incompleta produz estado desconhecido e diligências, sem afirmar autorização.
- **Risco:** sinal analítico separado de evidência oficial. Ausência de dados conserva o estado `dados_insuficientes` em toda a cadeia.
- **Explicação:** DTO versionado, com contribuições, fatores, limitações e referências. Compatibilidade com `explain_json` antigo mediante adaptador explícito.
- **Cenário financeiro:** premissas editáveis, unidades, data e origem. Valor estimado, score territorial e retorno simulado permanecem campos distintos.
- **Acesso:** usuário, organização, vínculo, papel de autorização e ambiente preferido como conceitos separados.

## Sequência de execução

Esforço estimado para uma pessoa desenvolvedora experiente: **41–64 dias úteis**, aproximadamente **9–13 semanas de trabalho integral**. É uma estimativa de engenharia, não um prazo contratado; obtenção de dados oficiais, revisão técnica e disponibilidade dos participantes podem ampliar o calendário. Reestimar após a primeira etapa. Os períodos abaixo são relativos ao início, sem datas de entrega fixadas.

| Etapa | Esforço | Depende de | Entrega verificável |
| --- | --- | --- | --- |
| 0. Linha de base e desenho das decisões | 2–3 dias | Nenhuma | Estado reproduzível e definição dos dois pilotos |
| 1. Integridade e demonstração explícita | 3–5 dias | 0 | Identidade territorial consistente e falhas transparentes |
| 2. Migrations, contratos e versões | 6–9 dias | 1 | Evolução de schema controlada e resultados rastreáveis |
| 3. Extração do domínio compartilhado | 6–9 dias | 2 | Regras únicas e casos de uso reutilizáveis |
| 4. Organizações e entrada por decisão | 5–8 dias | 2; integrar com 3 | Projetos isolados e ambientes específicos |
| 5. Pipeline durável e publicação | 5–8 dias | 2 e 3 | Atualizações recuperáveis sem perder a versão publicada |
| 6. Duas jornadas completas | 10–15 dias | 3, 4 e 5 | Diagnóstico público e estudo preliminar de terreno |
| 7. Piloto e estabilização | 4–7 dias | 6 | Aceite, operação documentada e próxima prioridade |

### Etapa 0 — Linha de base e definição dos pilotos

**EX-01 — Registrar o estado inicial.** Inventariar endpoints, schema efetivo, dependências, configuração e versões dos dados. Registrar alterações locais e separar a execução futura em branch `codex/` sem descartar trabalho preexistente. Executar testes existentes e build do frontend, classificando falhas anteriores. Capturar fixtures de resultados legais, scores, risco e explicações com datas fixas.

**EX-02 — Definir uma decisão por piloto.** Propor saúde como primeira necessidade pública porque há coletor CNES e sinais de serviços; escolher educação se houver fonte municipal mais completa. Selecionar terrenos com dados disponíveis para o outro piloto. Definir perguntas, usuários de validação e relatórios esperados. Desenhar as telas antes de implementá-las.

**Aceite:** inventário e linha de base registrados; uma necessidade pública e exemplos de terrenos escolhidos; dados ausentes explicitados. Não é necessário decidir o modelo de negócio para concluir esta etapa.

### Etapa 1 — Integridade dos dados e modos explícitos

**EX-03 — Corrigir a identidade municipal e seus efeitos.** Centralizar `3152501`; validar identificação nas respostas dos provedores e arquivos importados. Auditar cache, setores, população, features, scores e relatórios dependentes. Marcar versões afetadas como inválidas para uso decisório, preservando evidências; reprocessar em staging e reconciliar totais antes da publicação. Atualizar fixtures que reproduzem o identificador divergente quando pretendem representar Pouso Alegre.

**EX-04 — Separar real, estimado e demonstrativo.** Eliminar a conversão silenciosa de falha PostGIS em relatório demo; demonstração exige seleção explícita. No RAG real, exigir corpus aprovado, referências e checksum; corpus embutido pode permanecer apenas como fixture/demo. Identificar estimativas populacionais e o fallback hedônico já sinalizado pela API. Não transformar estimativa declarada em observação oficial.

**Aceite:** falha no banco não gera relatório sintético; fonte jurídica ausente gera indisponibilidade; demo aparece identificada na tela e no arquivo; dataset de outro município é rejeitado. A regra legal determinística permanece independente do RAG.

### Etapa 2 — Schema, contratos e versionamento

**EX-05 — Introduzir migrations.** Adotar Alembic ou SQL versionado com um único executor; preferência inicial por Alembic, dado o uso de SQLAlchemy. Comparar o banco real com scripts de inicialização antes da baseline. Aplicar marcação de versão somente se o schema for comprovadamente equivalente. Cobrir tabelas geográficas, mercado, operação, usuários e leads. Remover DDL do runtime após a migração e testar com credenciais da aplicação sem privilégio de alterar schema.

**EX-06 — Versionar configuração e resultados.** Evoluir `ops.data_sources` com versões de datasets e manifesto de execução. Validar configurações e caminhos independentemente do diretório de execução. Registrar referência MapBiomas explicitamente, preservando 2024 se for a camada validada disponível. Substituir calibração que sobrescreve JSON por proposta versionada e promoção registrada. Criar contrato de explicação e conversor do formato legado.

**Aceite:** banco vazio é criado por migrations; cópia de banco existente recebe atualização sem perda; relatório e API indicam versões e fontes; configuração inválida falha claramente; reinício não altera silenciosamente os parâmetros.

### Etapa 3 — Um domínio compartilhado

**EX-07 — Extrair regras de decisão.** Começar por `LegalPolicy`, `RiskAssessor`, `OpportunityScorer` e construção de explicações. Preservar resultados existentes nas entradas conhecidas. Mudanças de metodologia, como novos scores públicos, recebem nova versão e não ficam misturadas à refatoração.

**EX-08 — Criar casos de uso e adaptadores.** Encapsular consulta de features, regras e persistência em contratos; extrair de `geospatial.py` a orquestração e acesso ao banco gradualmente. Encaminhar scores, relatórios, API e CLI para a mesma regra. Retirar de `concept.py` os cálculos de viabilidade e cenários, mantendo imagem e geração de documento em serviços separados quando tocados pela jornada.

**Aceite:** domínio testável sem banco/rede; mesma entrada e versões produzem mesma classificação pela API, CLI e relatório; casos legais bloqueados não reaparecem como oportunidades elegíveis; valores desconhecidos não viram zero ou baixo risco por conveniência de apresentação.

### Etapa 4 — Acesso e ambientes de trabalho

**EX-09 — Separar persona e autorização.** Criar organizações, vínculos e projetos; preservar acesso dos usuários legados mediante mapeamento documentado. Manter administração da plataforma separada dos papéis de organização. Trocar ambiente preferido não concede participação numa prefeitura nem poder administrativo. Verificar autorização no backend em cada operação e leitura de objeto privado; não confiar no menu ou em `organization_id` enviado pelo cliente.

**EX-10 — Redesenhar entrada e navegação.** Criar página inicial com decisões relevantes por ambiente e extrair configuração de perfis de `App.jsx`. Acrescentar construtora como ambiente distinto. Apresentar uma jornada com passos: objetivo, área, evidências, comparação/cenários e relatório. Permitir iniciar o fluxo e visualizar pendências mesmo sem dados territoriais completos. Preservar mapa, filtros, CRM e avaliação existentes.

**Aceite:** dois usuários de organizações diferentes não leem ou alteram projetos entre si; troca de persona não altera privilégios; o CRM mantém isolamento; os quatro perfis atuais continuam funcionando; construtora e incorporadora têm objetivos distintos. Somente então salvar análises institucionais ou projetos privados para pilotos.

### Etapa 5 — Pipeline persistente e publicação segura

**EX-11 — Persistir execução e recuperação.** Criar `ops.pipeline_runs`, etapas e versões de datasets. Persistir estado antes de aceitar a execução, com chave de idempotência, lock por município/modo, lease e heartbeat. Um worker do mesmo código-base consome execuções; inicialmente pode usar Postgres como fila, sem acrescentar outro serviço de mensageria. API e CLI acionam o mesmo caso de uso; subprocessos podem permanecer temporariamente em etapas ainda não extraídas.

**EX-12 — Publicar snapshots e melhorar gargalos medidos.** Produzir dados em staging, validar e promover um manifesto/snapshot de modo atômico. Usar checkpoints por etapa e versão; cada etapa deve suportar repetição transacional/upsert. Começar operações em lote e joins espaciais pelo trecho de maior custo comprovado, especialmente comparáveis e população. Medir plano de consulta, memória e tempo antes/depois; adaptar índices ao tipo espacial usado na consulta.

**Aceite:** restart não perde histórico; uma execução interrompida é detectada e recuperável; duas solicitações simultâneas não duplicam o pipeline; repetir etapas não duplica dados; falha não substitui o último snapshot válido; leitores não veem resultados parciais. Persistir status sozinho não satisfaz esse aceite.

### Etapa 6 — Jornadas completas

**EX-13 — Priorização pública.** Implementar `PrioritizePublicFacilities`: tipo de equipamento, área, data e parâmetros de cobertura. Combinar população com qualidade declarada, equipamentos existentes, distâncias, crescimento e evidências ambientais pertinentes. Mostrar regiões para investigação, contribuições e lacunas; comparar alternativas e exportar relatório reproduzível.

Na ausência de capacidade das unidades, demanda por faixa etária e tempos de deslocamento, chamar o resultado de **indicador exploratório de cobertura**, sem quantificar déficit de vagas ou declarar localização ótima. Distância em linha reta deve ser identificada como tal. Estimativa de população por H3 não equivale a demanda observada. Score público mede necessidade/cobertura, não atratividade imobiliária; pesos iniciais serão hipóteses versionadas e revisadas pelo participante técnico.

**EX-14 — Estudo preliminar de terreno.** Implementar `AssessLandFeasibility`: localização ou polígono, uso pretendido e premissas. Separar evidência na escala do terreno de informação agregada por H3; zoneamento e sobreposições devem considerar o polígono quando disponível. Sem limites cadastrais, reduzir o alcance da conclusão. Mostrar restrições, declividade, drenagem, acesso, fontes, comparáveis e diligências.

Para construtora, enfatizar condicionantes de implantação e investigações técnicas. Para incorporadora, acrescentar parâmetros urbanísticos quando verificáveis e cenários editáveis de área, custo, receita e prazo. Não inferir custo de obra ou liquidez comprovada apenas de score territorial. Quantidades financeiras sem referência suficiente aparecem como hipótese do usuário ou cenário demonstrativo.

**Aceite comum:** usuário conclui entrada → evidências → comparação/cenários → relatório; pode salvar e reabrir projeto; alterações de premissas ficam registradas; fonte, período, método e limitações acompanham os resultados; área bloqueada e área com dados insuficientes têm tratamentos distintos. Um resultado exploratório útil é aceitável; não é aceitável ocultar dados ausentes para produzir conclusão definitiva.

### Etapa 7 — Piloto e operação

**EX-15 — Validar decisões com participantes.** Realizar sessões propostas com uma pessoa de planejamento público e uma de incorporação/construção, conforme disponibilidade. Registrar tarefa, resultado esperado, compreensão das limitações e pendências. Meta de aceite do piloto: cada participante conclui ao menos um caso com dados reais disponíveis, entende as fontes e identifica a diligência seguinte; ajustes críticos são resolvidos antes de ampliar o acesso.

**EX-16 — Estabilizar e documentar.** Atualizar `docs/architecture.md`, `docs/engineering_decisions.md`, roadmap, modelo de dados e guia de execução. Registrar promoção/rollback de datasets, recuperação de pipeline, backup/restauração e permissões. Revisar dependências e lockfile com grupos/extras compatíveis com o empacotamento. Logs estruturados por `run_id` e projeto permitem localizar falhas sem expor credenciais ou conteúdo privado.

**Aceite:** caminho principal e falhas previstas verificados em staging; restauração ensaiada; build e verificações de CI aprovados; participantes aceitam o alcance da entrega; backlog seguinte ordenado por evidência do piloto.

## Verificação durante a implementação

Ampliar os testes existentes conforme os riscos tocados, em vez de recriar a suíte inteira:

| Área | Evidência exigida |
| --- | --- |
| Município e provedores | Contratos com fixtures; identificação territorial validada; rejeição de município incorreto |
| Legal, score, risco | Fixtures antes/depois; bloqueios e desconhecidos; limites numéricos; ausência de dados conserva semântica |
| Contratos | Explicação legado → versão nova; campos obrigatórios; API e relatório com mesmas versões |
| Migrations | Banco novo e cópia com schema anterior; restauração; aplicação operando sem DDL |
| Pipeline/PostGIS | Dupla execução, concorrência, falha intermediária, restart e publicação atômica em dataset pequeno |
| Acesso | Organização A não acessa B; persona não concede privilégio; compatibilidade com usuários e leads legados |
| Frontend | Build e fluxos completos em desktop/mobile; erros, dados insuficientes e demo legíveis |
| Piloto | Relatórios comparados com fontes e interpretação revisada pelos participantes |

A CI atual já possui testes unitários, lint e integração PostGIS de zoneamento. Acrescentar verificação do frontend nos PRs e integrar os cenários acima conforme cada etapa entrar. Não condicionar o primeiro ciclo a novas metas artificiais de cobertura ou desempenho: definir baseline e orçamento de latência com os dados do piloto.

## Estratégia de entrega e reversão

Cada ticket deve produzir uma mudança pequena e revisável, com contrato, validação e notas de migração. Usar mudanças de schema aditivas, compatibilidade temporária para consumidores legados e ativação gradual dos novos ambientes. Só remover fachadas/colunas antigas depois de migrar consumidores e observar o uso.

Publicação de novas metodologias cria uma nova versão, preservando relatórios históricos. Em falha, reativar o snapshot anterior e a experiência anterior compatível. Migration destrutiva exige backup e plano próprio; a reversão preferida no primeiro ciclo é de aplicação/configuração/snapshot, sem apagar dados para tentar restaurar comportamento.

## Responsabilidades e decisões que podem mudar a ordem

| Responsabilidade | Participação necessária |
| --- | --- |
| Engenharia | Contratos, código, migrações, testes, operação e documentação |
| Responsável pelo produto | Escolher o público do primeiro piloto, validar perguntas e critérios de utilidade |
| Responsável pelos dados | Conferir município, fontes, cobertura, licenças e aprovação das versões |
| Participante técnico de urbanismo/obra | Revisar interpretação das evidências, alcance dos relatórios e diligências |

Uma pessoa pode acumular funções, mas aprovação de fonte e validação metodológica devem ficar registradas. Os principais bloqueios externos são dados de capacidade/demanda dos equipamentos, geometria e parâmetros legais oficiais, informação cadastral dos terrenos e disponibilidade de participantes. Se esses dados não chegarem, entregar análise exploratória com alcance explícito e registrar o que impede a evolução.

Se o foco comercial for definido como privado, executar o piloto de terrenos antes do público. Se for governo, priorizar cobertura pública. Em ambos os casos, manter integridade, contratos, acesso e publicação antes do uso institucional.

## Depois do primeiro ciclo

Expandir somente a partir dos resultados do piloto: educação com demanda/capacidade verificáveis; acessibilidade por rede; localização comercial por atividade; finanças e cenários mais completos; personalização por objetivo/orçamento. Antes de promover o AVM, alinhar resolução H3 entre treino e uso, acrescentar avaliação temporal e espacial e registrar erro por segmento. Intervalos e liquidez exigem evidência própria; não surgem apenas de reorganizar o código.

**Primeiro lote recomendado para implementação:** EX-01 a EX-04. Ele estabelece a linha de base, define os pilotos, corrige a identidade territorial e torna o uso de dados demonstrativos explícito. O restante avança pelos critérios de aceite, com reestimativa após esse lote.
