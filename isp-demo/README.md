# Urbia Telecom — protótipo ISP

Mapa e análise de **instalações de clientes e infraestrutura de rede**, em uma operação de provedor inteiramente fictícia em três cidades do Sul de Minas: Pouso Alegre, Santa Rita do Sapucaí e Itajubá.

Esta versão está na branch `codex/urbia-isp`, criada em worktree a partir do HEAD commitado de `main`. As alterações não commitadas do checkout original foram preservadas e não foram copiadas. O radar acrescenta imagens e índices reais, com identificação explícita de sua origem. O módulo é independente da aplicação imobiliária e pode ser integrado à Urbia depois da validação com um parceiro.

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
