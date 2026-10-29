# Urbia Telecom — protótipo ISP

Mapa e análise de **instalações de clientes e infraestrutura de rede**, em uma operação de provedor inteiramente fictícia em três cidades do Sul de Minas: Pouso Alegre, Santa Rita do Sapucaí e Itajubá.

Esta versão está na branch `codex/urbia-isp-vercel`, criada em worktree a partir do HEAD commitado de `main`. As alterações não commitadas do checkout original foram preservadas e não foram copiadas. O radar acrescenta imagens e índices reais, com identificação explícita de sua origem. O módulo é independente da aplicação imobiliária e pode ser integrado à Urbia depois da validação com um parceiro.

## Executar separado no Docker

Na raiz deste worktree:

```sh
docker compose -f docker-compose.isp.yml up -d --build
```

Abrir <http://localhost:18089>. Projeto Compose `urbia-isp-demo`, serviço `dashboard`, rede `urbia-isp-demo-net`. Não conecta ao banco, containers, portas ou volumes do projeto atual. A porta é publicada apenas no loopback. Para outra porta, definir `ISP_DEMO_PORT`.

```sh
docker compose -f docker-compose.isp.yml ps
docker compose -f docker-compose.isp.yml down
```

Não há credenciais, banco ou volume nesta demonstração de leitura. Os dados pertencem à imagem e não podem ser editados pela interface. O container executa sem root e com filesystem somente leitura. Não usar este protótipo para cadastrar dados pessoais de clientes.

Alternativa sem Docker, a partir de `isp-demo/`:

```sh
python3 server.py
```

## O que explorar

- **Visão geral:** indicadores territoriais, mapa de camadas, detalhes vinculados e histórico mensal de entradas/cancelamentos.
- **Rede e capacidade:** POPs, CTOs, enlaces, portas ocupadas/livres e ocorrências simuladas. Ao selecionar uma CTO, inspecionar as 16 portas e as instalações conectadas.
- **Instalações:** cadastro pesquisável por identificação, rua e CTO; situação ativa/suspensa/cancelada, plano, data de instalação, cancelamento e vínculo histórico de porta.
- **Oportunidades:** pedidos para vistoria, falta de porta, distância da rede e ocorrências para investigar. Toda recomendação descreve o critério e seus limites.
- **Dados e premissas:** referências, proveniência e hipóteses visíveis no produto.

Cidade e setor filtram os indicadores, o histórico e o território. Setores Norte/Sul/Leste/Oeste são quadrantes artificiais em relação ao POP, **não bairros oficiais**. Busca e situação filtram apenas a lista e os pontos de instalações; os indicadores mantêm o recorte territorial. A exportação CSV usa o mesmo recorte da lista de instalações.

O estado comercial não é disponibilidade técnica: contrato ativo pode estar vinculado a CTO indisponível. Suspensos mantêm a porta ocupada; cancelados a liberam. Portas reutilizadas preservam o histórico sem sobreposição de intervalos. Não existe monitoramento em tempo real.

## Dados e realismo

`data/roads.json` contém geometrias e nomes de vias consultados via Overpass/OpenStreetMap; data da consulta e licença estão registrados no arquivo. O cache está incluído: o gerador e o painel não dependem de nova consulta ao Overpass. A geometria viária e seus derivados estão sujeitos à atribuição e às condições ODbL do OpenStreetMap: <https://www.openstreetmap.org/copyright>.

`generate.py` usa semente fixa `3152501`, retrato de `18/10/2026`, grafo viário conectado por cidade e caminhos mínimos do POP às CTOs. Trechos compartilhados são contados uma única vez no comprimento da rede, sem drops ou folgas de instalação. Clientes são posicionados junto a segmentos próximos à CTO; não foram identificados domicílios ou postes reais. A rede não constitui projeto executivo.

O cenário contém três POPs e 80 CTOs de 16 portas. Quantidade de clientes, distribuição comercial, distribuição de planos, sinais ópticos, incidentes e pedidos são **hipóteses de demonstração**, não estimativas calibradas de um provedor real. Ruas reais não significam que exista imóvel ou rede naquela coordenada.

Referências consultadas:

- IBGE, contexto municipal: <https://www.ibge.gov.br/cidades-e-estados/mg/pouso-alegre.html>. População não foi convertida em clientes.
- Anatel, coleta de acessos: <https://www.gov.br/anatel/pt-br/regulado/universalizacao/coletas-de-dados-de-acessos>. Não foi importada base de acessos de nenhuma operadora, nem inferida cobertura por rua a partir de estatísticas municipais.
- Furukawa/Lightera, caixa FK-CTO-16MC com até 16 posições: <https://www.furukawalatam.com/pt-br/versao-et-pdf/caixa-de-terminacao-optica-fk-cto-16mc>.
- Rede Brasil, ofertas de 250 Mbps a R$ 79,90 e 500 Mbps a R$ 99,90 consultadas em 18/10/2026: <https://redebrasil.net.br/>.
- Alares em Pouso Alegre, referência de 800 Mbps a R$ 109,99 com fatura digital em dia: <https://www.alaresinternet.com.br/mg/pouso-alegre/planos-de-internet/1250>.
- OpenStreetMap, geografia real: <https://www.openstreetmap.org/copyright>.

Os valores de planos são inspirados nessas ofertas públicas para tornar o cenário plausível; não são média de mercado, preço contratado real nem oferta da SerraLink. As condições comerciais das fontes podem mudar e não foram reproduzidas integralmente.

Os tiles do mapa base são solicitados ao OpenStreetMap pelo navegador e exigem internet. Leaflet 1.9.4 está incluído com sua licença em `web/vendor`. Se os tiles não carregarem, as vias locais e as camadas do cenário continuam visíveis. Nenhum dado é enviado a um sistema de gestão de provedor.

## Reproduzir e verificar

Executar em `isp-demo/`, somente com Python padrão:

```sh
python3 generate.py
python3 -m unittest -v test_simulation.py
```

O gerador salva `simulation.json` e CSVs de instalações, CTOs, POPs e pedidos. Testes verificam ausência de dupla ocupação de portas em todo o histórico, integridade de vínculos, capacidade, balanço mensal, conectividade da rede, ausência de trechos duplicados, coerência da triagem e reprodução exata dos dados.

`fetch_roads.py` é uma ferramenta opcional de atualização do cache público; exige internet. Ao atualizar as vias, a simulação pode mudar mesmo com a mesma semente. Sempre regenerar, testar e reconstruir a imagem após uma atualização.

## Evolução do produto

1. Validar com um parceiro as perguntas de operação e as prioridades comerciais usando este cenário.
2. Definir contrato de importação de instalações, CTOs, capacidade e rede; validar coordenadas e manter dados desconhecidos como pendentes.
3. Acrescentar persistência, contas/equipes, permissões, trilha de alterações e importação revisável antes de receber dados reais.
4. Integrar ERP/inventário com atualização identificada por origem e horário; definir a fonte de verdade de capacidade e situação.
5. Validar rota de atendimento, projeto óptico e custos antes de recomendar expansão ou apresentar viabilidade de instalação.

O MVP atual entrega exploração e triagem do cenário sintético; não inclui autenticação, edição, importação real, ERP, OLT/SNMP, orçamento de expansão ou aprovação automática de atendimento.


## Inspeção ao vivo simulada

Abrir **Inspeção ao vivo** no menu ou selecionar uma CTO no mapa e usar **Iniciar inspeção simulada**. Escolher alvo e cenário, iniciar e acompanhar as quatro etapas por 24 segundos simulados. Há operação normal, degradação óptica e rompimento. A opção de condição do cadastro converte CTO operacional/manutenção/indisponível nos três cenários correspondentes.

Os valores são produzidos no navegador, uma amostra por segundo: sinal óptico, latência, perda de pacotes e respostas de contratos ativos. Não são enviados pacotes reais nem consultados OLT, ONU, SNMP ou sistemas externos. Ausência de leitura usa `null`, nunca zero. Suspensos reservam porta e ficam fora dos testes de sessão; cancelados não ocupam porta.

É possível pausar, retomar, encerrar e exportar relatório JSON marcado como simulação, com alvo, cenário, amostras, eventos e indicação de conclusão ou evidência parcial. Ao sair da tela ou ocultar a aba, a sessão pausa. Filtros territoriais e alvo ficam bloqueados enquanto a sessão está em andamento ou pausada; encerrar libera uma nova seleção. A sessão está apenas na memória da página e é perdida ao recarregar; exportar permite conservar o resultado. O inventário original não é modificado.

Os gráficos e portas mostram hipóteses do cenário; não há limiar de aceitação técnica ou diagnóstico automático de causa. A hora de abertura usa Brasília; os segundos são relativos à simulação e podem demorar mais sob carga do navegador. Os testes do motor não exigem dependências externas:

```sh
node --test test_inspection.cjs
```


## Radar de crescimento próximo à rede

**Radar de crescimento** compara composições reais Sentinel-2 Collection 1 de julho–setembro de 2024 e 2025 nas três cidades. As imagens, cenas e índices são reais; a infraestrutura e os pedidos sobrepostos continuam fictícios, no retrato de 18/10/2026. A análise é histórica e não descreve mudanças em 2026.

A interface permite comparar antes/depois com uma divisória, ligar/desligar áreas e rede, filtrar a distância ao traçado fictício, consultar os motivos de cada próxima ação, abrir a CTO correspondente e exportar as áreas filtradas em GeoJSON. As fontes STAC, datas, qualidade, limiares e limitações estão nos detalhes do radar. O estado vazio é legítimo: não são inventadas áreas para preencher o painel.

### Método e limites

- Duas cenas de referência e duas posteriores por cidade, com pelo menos dez dias entre observações da mesma época. As cenas são selecionadas por nuvem global e cobertura do recorte; o produto registra também a qualidade local.
- Grade comum de **20 m**, respeitando a banda SWIR, e células analíticas de **200 × 200 m** (4 ha). Bandas de 10 m são agregadas a 20 m; SCL usa vizinho mais próximo.
- Usar apenas classes SCL 4 e 5 (vegetação/superfície não vegetada), com pixel válido nas quatro cenas. Células com menos de 80% de pixels utilizáveis são excluídas.
- NDVI = (NIR−red)/(NIR+red); NDBI = (SWIR−NIR)/(SWIR+NIR). Sinal exploratório: aumento de NDBI ≥ 0,10 e queda de NDVI ≤ −0,12 nas **duas** observações posteriores, contra a mediana das anteriores. Uma célula precisa de ao menos 12 pixels sinalizados (0,48 ha).
- “Superfície sinalizada” soma pixels que passam nessa regra; não é área construída comprovada. Não há classificador urbano treinado ou validado. Solo exposto, agricultura, sazonalidade e diferenças de cena podem criar falsos positivos.
- RGB usa a mesma escala fixa para as duas épocas e é reprojetado a Web Mercator para alinhamento das sobreposições; o cálculo de área e distância ocorre em UTM 23S.
- Distâncias são entre o centro da célula e segmentos de fibra/CTOs. Pedidos são procurados em raio geométrico de 500 m. O painel conta IDs únicos de pedidos, sem somar repetidamente o mesmo pedido entre células vizinhas.
- A consulta de portas considera somente a CTO mais próxima. “Priorizar visita” exige rede e CTO a até 500 m, pedido próximo, CTO operacional e porta livre no inventário fictício. A regra não escolhe rota de drop, não valida potência, não estima vendas e não aprova expansão.
- A ordenação coloca prioridades de visita primeiro, depois presença de pedidos, proximidade de 500 m, distância da rede e área sinalizada; não há um percentual de confiança ou score de retorno.

O resultado atual tem **80 células candidatas** antes dos filtros: Pouso Alegre 31, Santa Rita do Sapucaí 25, Itajubá 24. No recorte padrão até 500 m da rede fictícia, são 11, 4 e 1 respectivamente. Essas contagens não são quantidade de bairros, construções, clientes ou oportunidades comerciais confirmadas.

### Proveniência e reprodução

Fonte: catálogo público [Earth Search / Element 84](https://earth-search.aws.element84.com/v1), coleção `sentinel-2-c1-l2a`. Contém dados Copernicus Sentinel modificados (2024–2025). Os IDs e links das 12 observações (algumas cenas se repetem entre cidades), ativos, escala/offset, qualidade local e datas estão em `data/radar.json` e nos metadados de `data/radar-cache-c1/`.

A coleção legada `sentinel-2-l2a` foi descartada na preparação por inconsistência de escala/offset; o coletor e os testes só aceitam Collection 1. Valores físicos são calculados com escala/offset dos ativos STAC; há uma verificação para interromper a coleta diante de refletância vermelha excessivamente negativa. Referência sobre a migração: [Element 84 / Earth Search](https://github.com/Element84/earth-search).

Os recortes espectrais comprimidos de 20 m em `data/radar-cache-c1/` permitem reproduzir o cálculo sem consultar novamente as imagens originais. São derivados científicos, não imagens criadas por IA. As composições PNG em `web/radar-assets/` e o catálogo JSON são incluídos no Docker; o navegador não precisa acessar o catálogo STAC. O cache científico fica fora da imagem Docker.

Para preparar ou recalcular, em um ambiente Python separado com as dependências de `requirements-radar.txt`, a partir de `isp-demo/`:

```sh
# Reproduzir usando os recortes incluídos, sem internet:
python3 collect_radar.py --cached
python3 -m unittest -v test_radar.py

# Atualizar os recortes públicos (exige internet):
python3 collect_radar.py
```

As janelas históricas estão definidas em `PERIODS` no coletor. Alterar datas, parâmetros ou inventário exige recolher/recalcular, executar os testes e reconstruir o Docker. Não existe atualização automática nem agenda de coleta nesta entrega. A avaliação de falsos positivos e o confronto com visitas ou cadastros reais ainda precisam ser feitos com um parceiro.


## Planejar atendimento e ampliação

O menu **Planejar expansão** acrescenta um estudo de rota e distribuição para um pedido selecionado ou marcado no mapa. Não cadastra clientes nem instala equipamentos.

1. Escolher a cidade e um pedido demonstrativo, ou localizar uma rua pelo nome completo e clicar na posição aproximada do cliente. Também é possível informar latitude/longitude. A busca é local no cache OSM: não geocodifica número de imóvel.
2. Adotar um limite de percurso de drop e uma reserva de cabo. Os padrões de 250 m e 10% são hipóteses editáveis, não regras técnicas ou certificação de potência.
3. Escolher entre priorizar o atendimento atual e agrupar outros pedidos. Opcionalmente informar custos de drop instalado/m, fibra instalada/m e CTO instalada. Nenhum preço de mercado é presumido.
4. Comparar até duas alternativas de CTO existente e duas de nova CTO. Inspecionar os percursos por rua, a origem da extensão, os pedidos próximos pelo grafo e as limitações de portas; alternar a rota no mapa.
5. Exportar o estudo JSON para conservar parâmetros, caminhos, alternativa selecionada, custos e pendências. Alterar o ponto ou premissas invalida o resultado anterior.

### Lógica de roteamento e candidatos

`planner.py` usa apenas a biblioteca padrão do Python. O endpoint de cálculo local é `POST /api/plan`; não existe chamada a roteador ou geocodificador externo, nem gravação do pedido no servidor.

O grafo usa os segmentos e vértices das ruas OSM já armazenadas. Distâncias são aproximadas em projeção métrica local por cidade. O grafo é não direcionado, não modela níveis de viadutos nem sentidos de tráfego, e não serve como instrução de condução de veículo. Coordenadas comuns são tratadas como conexão geométrica; vias sem conexão permanecem separadas.

O ponto do pedido é projetado no segmento viário mais próximo. Acesso superior a 150 m é recusado como insuficiência da malha disponível. O acesso entre a rua e o ponto fica separado como guia tracejado, contado na metragem de cabo, sem comprovar passagem física. Não se inventa uma ligação direta em linha reta entre componentes desconectados.

- **Atendimento existente:** caminhos mínimos por ruas para CTOs operacionais com porta livre; percurso e acessos dentro do limite adotado. Cancelados não ocupam porta; suspensos continuam reservando. Avalia CTOs elegíveis e mantém até duas conforme a prioridade.
- **Nova CTO:** busca até 24 vértices de ruas, espaçados pelo menos 45 m, que mantenham o pedido atual dentro do limite de drop. Usa busca de múltiplas origens para o caminho mínimo até um vértice do traçado de fibra cadastrado. Mantém até duas alternativas com pelo menos 75 m entre si. Não é otimização global, nem identifica postes reais.
- **Origem da extensão:** representa somente um ponto geométrico no traçado fictício. Derivação, fibra livre, split, alimentação, porta PON e orçamento óptico permanecem desconhecidos. CTO com 16 portas é hipótese da alternativa; a existência do cabo na rua não autoriza uma derivação.
- **Próximos pedidos:** IDs únicos de outros pedidos fictícios alcançáveis por ruas a partir da CTO, no limite de percurso adotado. O pedido atual é excluído quando selecionado por ID. O teto inicial é o menor entre essa quantidade e as portas restantes após o pedido atual. Não é previsão de vendas ou ocupação garantida.
- **Satélite:** células históricas do radar de 2024/2025 a até 500 m em linha reta do local, apresentadas separadamente. Elas não são somadas a clientes e não entram na quantidade de adesões.
- **Ocorrências:** sem opção direta elegível e com CTO indisponível/em manutenção próxima, a conclusão pede investigar a ocorrência antes de decidir uma ampliação. Construir outra CTO não é apresentado como solução comprovada de falha.

Na prioridade de atendimento, opções existentes vêm primeiro, seguidas das ampliações; dentro dessa ordem compara-se metragem ou custos, e pedidos adicionais. Na prioridade de agrupamento, compara-se primeiro o teto de outros pedidos pelas portas, depois custo/metros e tipo. A métrica de desempate só é monetária se os três custos estiverem presentes, evitando misturar reais e metros.

Orçamento: drop × (1 + reserva) × R$/m; em nova CTO, acrescentar extensão × (1 + reserva) × R$/m e CTO instalada. Atendimento existente pode ter orçamento apenas com custo de drop; nova CTO requer os três valores. Campos ausentes deixam o orçamento correspondente pendente. As estimativas excluem postes, travessias, permissões, equipamentos ativos, deslocamentos, impostos e contingências. Não são ROI, payback nem aprovação de investimento.

### Validação

```sh
python3 -m unittest -v test_planner.py
```

Nove testes cobrem rota em U em vez de atalho reto, projeção de dois pontos no mesmo segmento, componentes desconectados, CTOs cheias/indisponíveis, reserva de portas suspensas, ocorrências, custos com reserva, campos ausentes, exclusão do pedido atual, limites de portas, dados inválidos, reprodução e preservação do inventário. Casos das três cidades verificam que os segmentos de rota pertencem às vias armazenadas.

O estudo não reserva portas, não altera CTOs, não valida infraestrutura física nem estima conversão comercial. Para uso real, precisa de inventário auditado de postes/dutos, fibras/portas de origem, permissões, medições ópticas e custos completos.

### Ajuda no painel

Use **Como usar** no menu ou no cabeçalho para abrir o roteiro de operação, atendimento de pedidos, expansão, radar e inspeção. O guia contém atalhos para as telas e um glossário de CTO, POP, drop e reserva de cabo. As instruções distinguem dados reais de simulação e estudo preliminar de validação técnica em campo.

### Vercel

Para publicar somente o protótipo ISP, importe a branch `codex/urbia-isp-vercel` com **Root Directory = `isp-demo`** e preset **Other**. Não exige Docker ou envs. A interface e os snapshots são estáticos; `POST /api/plan` roda como função Python reutilizando o motor atual. Configuração e passo a passo em [VERCEL.md](VERCEL.md).


## Leis e dados reais — 20/10/2026

O menu **Leis e dados reais** reúne a camada de endereços do IBGE, 12 referências legais/técnicas e três referências históricas de projetos regionais. As leis municipais localizadas são 6.553/2022 (Pouso Alegre), 5.406/2021 (Santa Rita do Sapucaí) e 3.469/2022 (Itajubá). Cada cartão contém fonte oficial, trecho de referência, data da consulta e limites de aplicação. A consulta ao texto não certifica consolidação ou enquadramento da obra; as normas municipais incluem ETR/antenas, portanto não são aplicadas como obrigação automática para toda CTO ou fibra.

`data/territory.json` contém **136.269 endereços únicos mapeados**, dos quais **112.356 de domicílio particular**, em 7.008 células de 200 m nas três cidades. Fonte: IBGE CNEFE/Censo 2022, edição GeoJSON municipal de 10/09/2024, coletada em 20/10/2026. Deduplicação por COD_UNICO_ENDERECO; somente coordenadas originais NV_GEO_COORD=1; finalidade residencial COD_ESPECIE=1. Coordenadas estimadas/centroides foram excluídas. Os metadados registram contagens brutas, repetidas, excluídas, link do arquivo original e SHA-256. A camada publica apenas contagens agregadas, sem nomes, números, logradouros ou identificadores individuais. Os endereços são históricos, não assinantes ou previsão de adesão.

Para reproduzir a camada, em `isp-demo/`:

```sh
python3 collect_territory.py --download
python3 -m unittest -v test_knowledge.py test_planner.py test_vercel.py
```

O coletor usa três arquivos públicos do FTP do IBGE e conserva os ZIPs em `data/territory-cache/` (ignorados por Git, Docker e Vercel). Nenhuma coleta externa é executada no build ou em uma requisição. O snapshot versionado é suficiente para operar o painel. A reprodução foi comparada byte a byte com os arquivos originais.

No planejador, o **Contexto regulatório do estudo** identifica implantação aérea/subterrânea, detentora declarada, intervenção em espaço público, travessia e área protegida. A API associa cada alternativa às verificações e fontes pertinentes; Cemig ND-6.6 só é aplicada quando a detentora é declarada como Cemig. Ausência declarada de condição não equivale a validação por mapa. Não há aprovação automática, verificação de documentos ou cruzamento com zoneamento, postes, áreas protegidas e faixas de domínio.

Cada alternativa mostra a contagem de endereços residenciais em células com centro no raio em linha reta da CTO e uma faixa geométrica aproximada pelas bordas das células. Essa faixa não é intervalo estatístico; o raio não equivale a percurso de cabo ou alcance técnico. As contagens não entram na ordenação nem aumentam os pedidos compatíveis ou as portas. O estudo JSON inclui esses dados, as premissas e suas fontes; a tela de dados permite exportar células GeoJSON.

`data/regulations.json` é o catálogo curado de fontes, sem consultas externas durante o cálculo. O acompanhamento da revisão de postes fica separado das regras aplicadas; não se presume dispensa SCM por porte, preço de compartilhamento ou disponibilidade de rede de terceiros. Projetos históricos são referências documentais, não rede cadastrada. Números municipais da Anatel não foram importados. A rede operacional e os pedidos continuam fictícios.


## Gestão — 28/10/2026

O menu **Gestão** reúne quatro ferramentas sobre o mesmo recorte de cidade/setor. Nada é enviado a servidor; o motor de cálculo é `web/management-engine.js`, sem dependências.

- **Receita e base:** receita recorrente faturável (mensalidades hipotéticas de contratos sem suspensão), receita em risco (suspensos, que continuam ocupando porta), ticket médio, churn mensal (cancelamentos do mês ÷ base no fim do mês anterior) e quebras por cidade e plano. Outubro é parcial até o retrato. Não é DRE, previsão de faturamento nem ERP.
- **Território e penetração:** cruza as células de 200 m do IBGE/CNEFE 2022 (real), as instalações conectadas (fictícias) e as áreas do radar Sentinel-2 (real). Penetração = instalações ÷ endereços de domicílio particular na célula. Ações, com raio em linha reta, meta e mínimo de domicílios editáveis: *campanha comercial* (CTO operacional com porta no raio e penetração abaixo da meta), *ampliar capacidade* (CTO no raio, nenhuma operacional com porta) e *estudar expansão* (nenhuma CTO no raio, rede a até 1,5 km). O sinal de satélite a até 300 m é contexto e desempate; não muda a ação. Cada célula abre o planejador no seu centro ou gera uma ordem de vistoria. Exportação CSV.
- **Capacidade das CTOs:** saldo de instalações − cancelamentos em 90 dias, extrapolado linearmente para estimar quando cada caixa esgota; pedidos cuja CTO mais próxima é a caixa elevam o risco. Tendência, não previsão de vendas; não considera splitters, orçamento óptico ou portas PON.
- **Ordens de serviço:** geradas do retrato (ocorrência → corretiva; sinal simulado < −25 dBm → preventiva; pedido em vistoria → vistoria; pedido sem porta → projeto; suspenso → retenção, de escritório) com SLA por prioridade (4 h / 24 h / 72 h / 5 dias) no relógio do retrato, 18/10/2026 18h. Quadro por situação, distribuição automática balanceada entre as equipes fictícias da cidade, ordens manuais (também pelo painel de detalhe de CTO/instalação), exportação CSV e **roteiro do dia**: críticas e altas primeiro, depois vizinho mais próximo a partir do POP, em linha reta — não é trajeto viário.

Situação, equipe e ordens manuais ficam salvas apenas no `localStorage` deste navegador (`urbia-isp-gestao-v1`); não há contas, sincronização entre usuários ou trilha de auditoria. “Restaurar retrato” descarta essas alterações. Não registrar dados pessoais reais nas ordens.

```sh
node --test test_management.cjs
```

Os testes cobrem receita com suspensos e meses sem instalação, conciliação com o inventário, ordenação de risco de capacidade, localização das instalações nas células do IBGE sem dupla contagem, critérios das ações territoriais, independência da ação em relação ao satélite, unicidade e SLA das ordens, distribuição restrita à cidade e balanceada, e prioridade no roteiro.

### Mercado real · Anatel

A aba **Gestão › Mercado real · Anatel** usa dados públicos reais: acessos de banda larga fixa que cada prestadora declara à Anatel, por município e mês. Mostra total de acessos e variação em 12 meses, participação por prestadora (CNPJ), concentração HHI por grupo econômico (só dentro de um município), tecnologia, pessoa física/jurídica, a série mensal e, à parte, as prestadoras que declararam nos 6 meses anteriores e não aparecem no mês de referência. Também compara os acessos de pessoa física com os domicílios do IBGE (um teto, não uma taxa exata) e indica quanto a SerraLink fictícia representaria do total real. A rede e os clientes continuam fictícios.

Snapshot: `data/market.json` (cerca de 40 KB), mês de referência 08/2026, arquivo da Anatel de 08/10/2026 coletado em 28/10/2026, com SHA-256 nos metadados. Fonte: <https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_banda_larga_fixa.zip>.

```sh
# Recoletar (cerca de 1 GB; cache em data/market-cache/, ignorado por Git, Docker e Vercel):
python3 collect_market.py --download
# ou com um arquivo já baixado:
python3 collect_market.py --zip /caminho/acessos_banda_larga_fixa.zip --last-modified "<Last-Modified do arquivo>"
python3 -m unittest -v test_market.py
```

Limites: acessos não são domicílios nem cobertura por rua. Meses com queda brusca seguida de recuperação e prestadoras que somem costumam ser declaração ausente; em Pouso Alegre, por exemplo, três prestadoras com cerca de 8,4 mil acessos deixaram de declarar entre 05 e 08/2026, o que explica boa parte da queda do total. Variação por CNPJ pode refletir troca de CNPJ ou incorporação.
