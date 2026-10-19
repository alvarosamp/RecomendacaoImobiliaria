# Validação do protótipo — 18/10/2026

## Verificações de dados

Seis testes em `test_simulation.py`: ausência de ocupação simultânea de uma mesma porta durante todo o histórico; integridade de cliente → CTO → POP e capacidade; balanço mensal de entradas e cancelamentos; enlaces únicos e conectividade das CTOs ao POP; coerência da triagem de pedidos; identificação de dados sintéticos e reprodução determinística.

Retrato: três cidades, três POPs, 80 CTOs, 1.280 portas, 2.121 segmentos únicos de enlaces, 1.289 registros de instalação, 881 contratos ativos, 63 suspensos e 345 cancelados. Total conectado: 944; portas livres: 336. Há 108 pedidos fictícios. Preços e velocidades usam as referências comerciais descritas no README; registros e distribuição são simulados.

## Verificações no navegador

- Recorte de Pouso Alegre: 36 CTOs, 420 instalações conectadas e 156 portas livres.
- Tela de rede: lista de capacidade; inspeção de CTO com 16 portas e acesso às instalações vinculadas.
- Instalação: situação comercial, datas, plano, porta, CTO e leitura óptica explicitamente simulada.
- Busca de canceladas da `CTO-POU-001`: três registros. CSV baixado e conferido com as mesmas três linhas, situação, vínculo e flag de simulação.
- Busca inexistente: estado vazio e paginação sem registros.
- Filtros combinados em Santa Rita do Sapucaí, setor Norte: quatro CTOs, 50 conectadas e 14 portas livres.
- Itajubá: oportunidades, abertura de pedido para vistoria e exibição da distância/CTO sem afirmar viabilidade.
- Dados e premissas: fontes e limites disponíveis na interface.
- Tela de 390 × 844: largura do documento igual à viewport, sem rolagem horizontal global.
- Mapa base desabilitado: vias armazenadas localmente, enlaces e pontos continuam visíveis. Não foi simulada falha geral de rede do sistema operacional.

Uma falha na navegação encontrada na primeira passagem foi corrigida antes da entrega. A imagem Docker foi reconstruída após as correções.

## Isolamento

Compose `urbia-isp-demo`, container `urbia-isp-demo-dashboard-1`, rede `urbia-isp-demo-net`, porta `127.0.0.1:18089`. Não usa banco, volumes ou rede da stack imobiliária. Endpoint `/health` retorna `synthetic-demo`. A interface é somente leitura e não tem integração com operação real.

## Inspeção ao vivo simulada

- Oito testes Node verificaram estados de sessão, pausa/retomada, interrupção parcial, duração de 24 amostras, cenários, exclusão de cancelados/suspensos dos testes de conectividade, ausência de sinal/latência ficticiamente zerados e preservação do inventário.
- No navegador, sessão de degradação pausada em 18 segundos e retomada até 24; relatório JSON baixado e conferido, com cenário, alvo, 24 amostras, marcação sintética e eventos de pausa/retomada.
- Cenário de rompimento pela condição da CTO indisponível: sinal e latência sem leitura, perda fictícia de 100% e zero respostas de 11 instalações testáveis.
- Sair da tela pausou a sessão; encerrá-la apresentou evidência parcial. Acesso pela ficha da CTO selecionou o alvo correto.
- A sessão não consulta equipamentos nem persiste alterações no cadastro. Recarregar a página descarta a sessão em memória.


## Radar com imagens reais

- Sete testes verificaram sinais repetidos em duas observações posteriores, ausência de sinal em superfície estável, exclusão de nuvens/sombras/água/nodata, rejeição da coleção legada, datas/qualidade radiométrica, cálculo das áreas a partir dos recortes e coerência dos vínculos com CTOs/pedidos fictícios.
- Os oito testes existentes do motor de inspeção também passaram após a integração.
- Inspeção visual das composições RGB e verificação de metadados STAC. A versão preliminar de catálogo legado foi descartada; somente Collection 1 integra os arquivos entregues.
- No navegador: imagens das duas épocas carregadas, divisória comparada nos extremos, troca de cidade, filtros de distância/ação, paginação e ausência legítima de candidatos.
- Exportação GeoJSON baixada no recorte “Priorizar visita” de Pouso Alegre: quatro áreas, polígonos fechados em longitude/latitude, marcação de satélite real e operação fictícia, fontes e validação pendente. Arquivo conferido após o download.
- Botão “Ver CTO no mapa” abriu CTO-POU-013 com cinco portas livres, coerente com a evidência comercial do radar.
- As contagens são de células espectrais exploratórias, não de construções comprovadas. Não houve validação de campo, medida de precisão de classificação ou comprovação de demanda.
- Layout verificado em 1280 e 390 pixels: largura do documento igual à viewport, sem rolagem horizontal global; comparação e detalhes reorganizam-se na tela pequena. Tamanho original do navegador restaurado.
- Imagem Docker final: endpoint `/api/radar` e seis PNGs conferidos; cache científico ausente no container. Serviço permanece no Compose isolado e porta local 18089.


## Planejador de atendimento e ampliação — 19/10/2026

- Nove testes passaram: caminhos por ruas (incluindo rota em U), componentes desconectados, projeção no mesmo segmento, capacidade/estado das CTOs, incidências, custos e reserva, pedidos únicos sem contar o atual, validação de entrada e preservação do inventário. Nas três cidades, segmentos de rota foram conferidos contra a geometria das vias.
- No navegador: troca de pedido e premissas ocultou o estudo anterior; custos opcionais, prioridade de agrupamento e comparação de alternativas funcionaram. Busca local de rua preservou o ponto do pedido; clique no mapa mudou para ponto manual e invalidou o resultado antigo.
- Pedido demonstrativo PED-0003: com custos exclusivamente de teste (drop R$ 2,50/m, fibra R$ 9/m, CTO instalada R$ 700 e reserva de 10%), uma alternativa apresentou 117,1 m de drop + 111 m de extensão e R$ 2.120,93; outra apresentou 0 m de drop + 167,5 m de extensão e R$ 2.358,25. Ambas tinham dois outros pedidos compatíveis, limitados por portas. Esses preços não são referências de mercado e os custos ficam vazios por padrão.
- Percursos de fibra/drop exibidos no mapa com cores distintas e itinerário de ruas. Arquivo JSON exportado e conferido: pedido, parâmetros, custos, caminhos, alternativa selecionada, inventário fictício e engenharia pendente.
- Não foram validados postes, dutos, permissões, fibras livres, split ou orçamento óptico. Satélite histórico foi mantido como contexto separado, sem contagem de futuros clientes.

- API na imagem Docker final: cálculo com custos, entradas inválidas retornando HTTP 400, ocorrência próxima orientando investigação e endpoints de saúde/radar preservados.
- Layout a 390 pixels: documento com 390 pixels de largura e formulário com 358 pixels, sem rolagem horizontal global. Exportação e marcação de novo ponto conferidas no navegador; custos de teste não são valores padrão.
- Com limite adotado de 500 m, PED-0003 apresentou atendimento por CTO-POU-011 com 390,2 m de percurso e uma porta disponível. Restaurado o limite de 250 m, o estudo passou a comparar ampliações. Nenhuma dessas alternativas constitui viabilidade óptica validada.
