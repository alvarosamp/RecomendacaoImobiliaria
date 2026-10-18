# Urbia Telecom — protótipo ISP

Mapa e análise de **instalações de clientes e infraestrutura de rede**, em uma operação integralmente fictícia de três cidades do Sul de Minas: Pouso Alegre, Santa Rita do Sapucaí e Itajubá.

Esta versão está na branch `codex/urbia-isp`, criada em worktree a partir do HEAD commitado de `main`. As alterações não commitadas do checkout original foram preservadas e não foram copiadas. O módulo é independente da aplicação imobiliária e pode ser integrado à Urbia depois da validação com um parceiro.

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
