# Urbia — implementação do primeiro lote

Data: 10 de outubro de 2026. Branch: `codex/urbia-integridade-dados`. Referência inicial: `4f3e3360`.

## Entrega e alcance

O primeiro lote do plano inicia EX-01 a EX-04. Implementa as correções de identidade territorial e os modos explícitos de dados, registra um snapshot demonstrativo e define os dois pilotos abaixo. As etapas EX-05 a EX-16 continuam no plano; organizações, migrations e novas jornadas ainda não foram implementadas.

| Item | Estado | Evidência / pendência |
| --- | --- | --- |
| EX-01 — linha de base | Parcial | Build inicial aprovado, inventário de 28 caminhos HTTP, checksums de configuração e fixtures numéricas; banco configurado indisponível para inventário efetivo |
| EX-02 — pilotos | Definição inicial | Saúde e terreno residencial como hipóteses; ainda requerem seleção de participantes, dados reais e validação de produto |
| EX-03 — identidade territorial | Código implementado; dados históricos pendentes | IBGE/CNES centralizados e respostas divergentes rejeitadas; auditoria somente de leitura disponível; sem invalidar ou reprocessar o banco indisponível |
| EX-04 — real, estimado e demo | Implementado no primeiro lote | Relatório não degrada para demo; RAG exige corpus verificado; população modelada acompanha procedência e limitações |

As alterações preexistentes em `frontend/node_modules`, `.claude`, `Claude outputs` e `tmp` foram preservadas. Não houve publicação, commit ou alteração do banco configurado. Um banco descartável é usado somente para testes de integração.

O [snapshot do lote](baseline_urbia_lote_01.json) identifica o instante de captura e inclui scores demonstrativos, risco sem evidências, casos legais e versões de configuração. Os módulos numéricos de scoring, risco e compatibilidade legal não foram alterados. O snapshot não comprova o estado de produção nem representa dados reais.

## Alterações funcionais

- `config/cities/pouso_alegre.json` é a origem compartilhada da identidade municipal. IBGE usa `3152501`; CNES deriva `315250`. Importação de bairros verifica a identidade do piloto.
- Respostas identificadas como outro município são rejeitadas antes de gravar os dados. Polígono municipal não é tratado como setor censitário; se o provedor não entrega setores utilizáveis, podem ser usados proxies declarados.
- A referência fixa do Censo 2022 foi corrigida para **152.217** conforme a [publicação do IBGE de 22/12/2023](https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Populacao_e_domicilios_Primeiros_resultados/Resultados_da_2a_apuracao_20231027/POP2022_Municipios_Primeiros_Resultados_20231222.pdf). É uma referência histórica, não uma observação atual.
- Proxies uniforme/NDBI conservam o total municipal após arredondamento. A distribuição espacial continua sendo uma estimativa. O método por interseção de setores requer avaliação própria de cobertura e reconciliação antes do piloto.
- População e seu registro de procedência são gravados na mesma transação. O registro inclui município, método, fonte, ano, qualidade e total de referência. Os registros de saúde distinguem CNES de mapeamento comunitário OSM; não afirmam capacidade disponível.
- `estimate-population` termina com erro se nenhuma célula é atualizada ou ocorre falha fatal. O pipeline deixa de informar sucesso nessa situação.
- `export-report` usa PostGIS por padrão. `auto` permanece como alias compatível de PostGIS, sem fallback. Fonte inválida, banco indisponível e base vazia não geram relatório demonstrativo.
- Demo exige `--source demo`; Markdown e CSV identificam a origem. API e relatório mostram quando a procedência populacional não foi verificada.
- Na tela de relatórios, “laudo” foi substituído por síntese preliminar. O download usa quebras de linha reais e o score residencial correto, em vez do maior score dos dois usos.
- RAG real exige corpus e manifesto com checksum, fonte oficial, município, versão e registro de aprovação. Índices antigos/demonstrativos são reconstruídos após validação; artigos recuperados precisam corresponder ao corpus aprovado. `--demo` é explícito e bloqueado em produção.

## Operação

Executar a partir da raiz do repositório com o ambiente Python do projeto e `PYTHONPATH=src;.` no Windows.

```powershell
$env:PYTHONPATH = 'src;.'
.venv\Scripts\python.exe -m recomendacao_imobiliaria.cli audit-territorial-data
.venv\Scripts\python.exe -m recomendacao_imobiliaria.cli export-report --source postgis
.venv\Scripts\python.exe -m recomendacao_imobiliaria.cli export-report --source demo --output-dir reports/demo
```

A auditoria abre transação `READ ONLY`, consulta tabelas e o registro de fontes e não altera registros. Dados populacionais existentes sem registro coerente recebem `unverified` e indicação de reprocessamento. Contagem e metadados não constituem validação metodológica completa; conferir também caches, fonte CNES e relatórios históricos. A tentativa no banco configurado retornou indisponibilidade; o schema e os dados desse ambiente permanecem desconhecidos.

Depois de disponibilizar um banco de desenvolvimento/staging: executar a auditoria, preservar dados e relatórios históricos, reprocessar população e saúde, conferir cobertura/totais e somente então recalcular features, scores e relatórios. Não executar `run-mvp` ou reset sobre produção como forma de corrigir o identificador.

### Corpus jurídico

Para `data/plano_diretor_corpus.json`, o manifesto deve ser `data/plano_diretor_corpus.json.manifest.json`. Campos obrigatórios:

| Campo | Conteúdo |
| --- | --- |
| `municipality_code` | `3152501` |
| `source_uri` | URL HTTPS da publicação oficial em domínio `gov.br` |
| `checksum_sha256` | SHA-256 dos bytes exatos do corpus JSON |
| `approved_by` | Responsável que efetivamente revisou a extração |
| `approved_at` | Data da revisão |
| `rule_version` | Identificador da versão revisada |

Cada artigo precisa de `id`, `title`, `text`, `chapter` e `lei`, sem IDs repetidos. O manifesto registra a aprovação; não realiza automaticamente revisão jurídica nem autenticação do documento remoto. Nenhum manifesto oficial foi criado ou aprovado nesta implementação.

```powershell
.venv\Scripts\python.exe -m recomendacao_imobiliaria.cli build-rag-index --corpus data/plano_diretor_corpus.json
.venv\Scripts\python.exe -m recomendacao_imobiliaria.cli rag-query --corpus data/plano_diretor_corpus.json --question 'Qual regra se aplica?'
# Somente demonstracao fora de producao:
.venv\Scripts\python.exe -m recomendacao_imobiliaria.cli build-rag-index --demo
```

ChromaDB e Anthropic continuam dependências opcionais. A validação rejeita fonte ausente antes de inicializá-los. A consulta real ao modelo não foi realizada nesta etapa.

## Pilotos definidos como hipótese

### Prefeitura — investigar cobertura de saúde

Pergunta inicial: onde a cobertura espacial conhecida de serviços de saúde merece investigação? Não afirmar déficit de atendimento público sem distinguir natureza pública/privada dos estabelecimentos, capacidade e demanda.

Fluxo proposto: escolher saúde e área → consultar fonte/ano/qualidade → observar cobertura e distância → comparar regiões → registrar lacunas e exportar síntese.

Tela inicial proposta: “Investigar cobertura de saúde”, seguida de área e período. Resultado em mapa com lista de regiões, explicação por fator e painel de dados ausentes. Distância em linha reta, população distribuída por proxy e POIs OSM precisam de identificação explícita.

Pendências: cadastro com natureza pública/privada; capacidade e atividade dos equipamentos; demanda e deslocamento; participante municipal; exemplos de regiões validados. Até resolver essas pendências, o resultado é exploratório e não dimensiona vagas ou unidades necessárias.

### Incorporadora/construtora — estudar terreno residencial

Pergunta inicial: quais restrições e diligências precisam ser resolvidas antes de avançar com um terreno residencial?

Fluxo proposto: localizar terreno e informar uso → mostrar escala da evidência → verificar restrições e dados faltantes → conferir condicionantes técnicas → editar cenários → exportar síntese preliminar.

Tela inicial proposta: “Estudar terreno”, com localização/polígono e objetivo. Resultado com fontes, situação legal, condicionantes e diligências. Incorporadora vê premissas do empreendimento; construtora vê questões de implantação. Sem perímetro cadastral, a análise permanece agregada por H3.

Pendências: selecionar terrenos reais com perímetro e fontes disponíveis; validar parâmetros urbanísticos; obter referências de custo e participante técnico. As três áreas do snapshot são fixtures demonstrativas e não terrenos reais selecionados para o piloto.

## Validação e limitações

A suíte existente foi ampliada com rejeição de município incorreto, conservação do total populacional, transparência de demo, validação de corpus e proteção contra índices antigos/adulterados. Os testes de integração verificam SQL de leitura, auditoria e rollback da população quando a gravação da procedência falha.

Resultados locais: **125 testes aprovados**, 7 subtests aprovados e 3 integrações inicialmente ignoradas na execução sem banco; em seguida, **as 3 integrações passaram** no PostGIS 15/3.5 descartável. Build do frontend e lint Ruff dos arquivos Python alterados/aplicáveis aprovados. O banco de testes foi criado com os scripts existentes e removido após a validação. A CI passou a executar todo `tests/integration/`, incluindo as verificações de procedência e rollback.

O CLI foi exercitado com exportação demo identificada e rejeição de corpus ausente. Não foram realizadas chamadas ao modelo externo ou coleta/reprocessamento de dados reais. Os avisos de dependências legadas e tamanho do bundle já existiam; não impedem o build.

O ambiente local usa Python 3.14.3; a CI declara Python 3.12. Testes com `TestClient` precisaram executar fora do sandbox devido ao bloqueio de sockets locais no Windows; testes com arquivos temporários usaram `--basetemp` dentro de `tmp`. Nenhum contorno desses problemas foi introduzido no código da aplicação.

Próximo lote: baseline de migrations e DTOs versionados (EX-05/EX-06), antes de retirar DDL do runtime. Reprocessamento do banco configurado e validação dos participantes continuam pendentes.

### Validação Docker — atualização em 12/10/2026

As imagens da API (Python 3.12) e do frontend (Node 20/Nginx) foram construídas com sucesso. A execução completa dos testes e das verificações HTTP foi interrompida e não está aprovada: o PostGIS descartável falhou ao encerrar o servidor temporário da inicialização, e a API ainda não respondeu às requisições. Não houve alteração do banco de desenvolvimento/produção.

O arquivo `compose.test.yaml` fornece ambiente separado, portas aleatórias e volume próprio. O script `scripts/test_docker_smoke.py` verifica autenticação, permissões, isolamento de leads e proxy Nginx. A próxima execução deve confirmar a inicialização do banco e concluir a suíte e esse script antes de considerar Docker validado.
