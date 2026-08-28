# Recomendacao Imobiliaria

Plataforma de inteligencia territorial para apoio a decisao em investimento imobiliario, expansao urbana e implantacao de servicos em Pouso Alegre, MG.

O projeto combina dados geoespaciais, sensoriamento remoto, regras urbanisticas, indicadores de acessibilidade e modelos de machine learning para identificar regioes com potencial imobiliario e comercial. A proposta central nao e apenas gerar um score, mas apresentar uma recomendacao auditavel: por que determinada area e promissora, quais restricoes legais existem e quais dados sustentam a conclusao.

## Visao

Criar uma ferramenta de analise urbana que ajude investidores, planejadores, corretores, incorporadoras e gestores publicos a responder perguntas como:

- Quais regioes tem maior potencial para investimento imobiliario?
- Para qual direcao a cidade esta crescendo?
- Onde ha carencia de mercado, farmacia, escola, saude ou servicos de bairro?
- O Plano Diretor permite o uso pretendido naquela area?
- Quais fatores explicam a recomendacao?
- Como os atributos urbanos influenciam preco e valorizacao de imoveis?

## Problema

Decisoes imobiliarias costumam depender de informacoes dispersas: anuncios, mapas, percepcao local, legislacao, imagens de satelite, infraestrutura urbana e conhecimento empirico. Sem integrar essas camadas, ha risco de recomendar areas com baixa viabilidade, restricoes legais, pouca infraestrutura ou crescimento urbano mal interpretado.

Este projeto busca reduzir essa incerteza com uma base tecnica georreferenciada, explicavel e alinhada ao Plano Diretor.

## Solucao proposta

A plataforma avalia o territorio por celulas H3 e consolida diferentes sinais:

- uso e ocupacao do solo;
- zoneamento e Plano Diretor;
- POIs e servicos urbanos;
- acessibilidade a equipamentos essenciais;
- indicadores ambientais e urbanos, como NDVI e NDBI;
- dados de imoveis e atributos de mercado;
- regras de elegibilidade e restricao;
- modelos de predicao de preco.

Cada area recebe scores e justificativas para usos residenciais e comerciais. Areas bloqueadas ou condicionadas pelo Plano Diretor sao penalizadas, sinalizadas ou excluidas da recomendacao.

## Principios do produto

1. **Legalidade antes do score**  
   Nenhuma recomendacao deve ignorar Plano Diretor, zoneamento, restricoes ambientais ou regras urbanisticas.

2. **Explicabilidade**  
   Toda recomendacao precisa apresentar fatores positivos, negativos, restricoes e dados utilizados.

3. **Dados oficiais primeiro**  
   Zoneamento, limites, setores censitarios e parametros urbanisticos devem vir de fontes oficiais sempre que possivel.

4. **IA como camada de apoio**  
   Machine learning e modelos generativos devem apoiar analise e interpretacao, nao substituir validacao tecnica e legal.

5. **Evolucao incremental**  
   O MVP deve resolver bem uma pergunta urbana antes de tentar prever todo o mercado imobiliario.

## Capacidades atuais

### Inteligencia territorial

- Grade H3 para analise espacial.
- Coleta de POIs via OpenStreetMap.
- Calculo de distancias e carencia de servicos.
- Identificacao de oportunidades residenciais e comerciais.
- Classificacao de prioridade, risco e uso principal.

### Plano Diretor e zoneamento

- Matriz inicial de compatibilidade por zona.
- Avaliacao de uso pretendido contra regras urbanisticas.
- Estados legais: permitido, condicionado e bloqueado.
- Penalizacao automatica do score quando ha condicionantes.
- Bloqueio de recomendacoes em zonas restritivas.
- Inspecao de KML/KMZ oficial do PDPA com 22 zonas reconhecidas.
- Registro dos anexos legais prioritarios para uso, incomodidade, parametros urbanisticos e risco.

### Sensoriamento remoto

- Importacao de series NDVI/NDBI por H3.
- Calculo de medias recentes e tendencias temporais.
- Sinalizacao de possivel expansao urbana com perda de vegetacao e aumento de area construida.

### Mercado imobiliario

- Modelo inicial de predicao de preco.
- Normalizacao de bases de anuncios.
- Estrutura para enriquecer imoveis com features urbanas.
- Base para evoluir para valorizacao temporal.

### Interface analitica

- Frontend web em evolucao.
- API para expor analises e recomendacoes.
- Ranking de oportunidades.
- Mapa de areas avaliadas.
- Painel de explicabilidade.
- Alertas de Plano Diretor.
- Painel de predicao de preco.

## Arquitetura conceitual

```text
Fontes oficiais e abertas
        |
        |-- Plano Diretor e zoneamento
        |-- Limites municipais e setores censitarios
        |-- OpenStreetMap e equipamentos urbanos
        |-- Sentinel-2 / NDVI / NDBI
        |-- Dados de anuncios imobiliarios
        v
PostGIS + Feature Store geoespacial
        |
        |-- geo.grid_h3
        |-- geo.zoning
        |-- geo.osm_pois
        |-- geo.indices
        |-- geo.features
        |-- geo.scores
        v
Motores de analise
        |
        |-- compatibilidade legal
        |-- scoring explicavel
        |-- classificacao de oportunidade
        |-- modelos de preco
        v
Dashboard e relatorios
```

## Componentes principais

| Componente | Responsabilidade |
|---|---|
| `geospatial.py` | Limite municipal, grid H3, POIs e features espaciais |
| `zoning_import.py` | Importacao de zoneamento oficial em GeoJSON, SHP, GPKG ou KML |
| `plan_director.py` | Regras de compatibilidade entre zona e uso pretendido |
| `scoring.py` | Score residencial/comercial e explicacao dos fatores |
| `decision.py` | Priorizacao, risco, uso principal e resumo da oportunidade |
| `remote_sensing.py` | Processamento de NDVI/NDBI e tendencias urbanas |
| `ml.py` | Treino e aplicacao de modelos de preco |
| `reporting.py` | Dados consolidados para dashboard e relatorios |
| `legal_annexes.py` | Registro dos anexos oficiais que sustentam parametros e usos |
| `api/` | Servico HTTP para integracao com o frontend |
| `frontend/` | Interface web do produto |

## Fontes oficiais prioritarias

Para evoluir de prototipo tecnico para ferramenta confiavel, os dados oficiais mais importantes sao:

- mapa georreferenciado de zoneamento urbano;
- Plano Diretor vigente e suas alteracoes;
- lei de uso e ocupacao do solo;
- anexos de parametros urbanisticos;
- limite municipal oficial;
- setores censitarios e dados socioeconomicos;
- camadas ambientais e areas de restricao.

Fontes recomendadas:

- Prefeitura de Pouso Alegre;
- Camara Municipal / Legislador;
- IBGE Geociencias;
- IDE-Sisema MG.

Caso o zoneamento georreferenciado nao esteja publicado, ele deve ser solicitado formalmente a Prefeitura por e-SIC ou Lei de Acesso a Informacao.

## Estado de maturidade

| Area | Estado |
|---|---|
| Estrutura do projeto | Implementada |
| Pipeline geoespacial | Implementado |
| Scoring explicavel | Implementado |
| Dashboard inicial | Implementado |
| Plano Diretor como regra de negocio | Parcialmente implementado |
| Importacao de zoneamento oficial | Inspecao implementada; importacao em banco preparada |
| Sensoriamento remoto | Parcialmente implementado |
| Modelo de preco | Baseline implementado |
| Valorizacao temporal | Pendente |
| RAG juridico com citacao legal | Pendente/experimental |
| Validacao com dados oficiais | Em andamento com arquivos oficiais do PDPA |

## Roadmap tecnico

### Fase 1: Confiabilidade territorial

- Importar zoneamento oficial.
- Cruzar cada celula H3 com zona urbana real.
- Associar regras do Plano Diretor a cada recomendacao.
- Mapear areas ambientais, APPs e restricoes relevantes.

### Fase 2: Oportunidade urbana

- Melhorar indicadores de acessibilidade.
- Incorporar densidade populacional e renda.
- Criar recomendacoes por tipo de estabelecimento.
- Gerar relatorios de top oportunidades por bairro/regiao.

### Fase 3: Mercado imobiliario

- Estruturar base real de anuncios.
- Treinar modelo robusto de preco.
- Avaliar erro por bairro, tipologia e faixa de preco.
- Evoluir para modelo de valorizacao temporal.

### Fase 4: Inteligencia juridica

- Indexar Plano Diretor e leis complementares.
- Citar artigos/anexos em cada recomendacao.
- Implementar busca semantica/RAG juridico.
- Criar trilha de auditoria legal por area.

### Fase 5: Produto

- Refinar experiencia do dashboard.
- Adicionar comparacao entre regioes.
- Gerar relatorios executivos.
- Preparar API para integracoes.
- Criar fluxo de atualizacao periodica dos dados.

## Criterios de qualidade

Uma recomendacao so deve ser considerada confiavel quando apresentar:

- score calculado;
- uso recomendado;
- zona urbana identificada;
- compatibilidade legal;
- fatores positivos;
- fatores negativos;
- dados utilizados;
- data de atualizacao;
- nivel de risco;
- justificativa textual.

## Avaliacao

O modelo de preco e acompanhado por MAE, R2 e validacao cruzada. Rankings de oportunidade devem ser avaliados com Precision@K, Recall@K, NDCG@K, Hit Rate@K e cobertura de catalogo; as funcoes reproduziveis estao em `recomendacao_imobiliaria.ranking_metrics`.

## Governanca e privacidade

Cada carga deve registrar fonte, data e status em `ops.data_sources`. A politica operacional de rastreabilidade e os requisitos de privacidade estao em [`docs/data_governance.md`](docs/data_governance.md).

## Auditoria legal

Use `GET /api/legal/assess?intended_use=comercial&h3_id=<celula>` para obter o status legal, artigos, parametros, fontes e a situacao das camadas espaciais. A consulta tambem aceita `zone` quando a celula ainda nao estiver disponivel. `GET /api/legal/annexes` mostra quais anexos oficiais fundamentam a analise.

## Alerta de suscetibilidade por satelite

`imobiliaria calculate-risk-signals` cria um sinal por H3 com os dados disponiveis. Series Sentinel-2 contribuem com pressao de urbanizacao (NDVI/NDBI); relevo, proximidade de drenagem e recorrencia de agua por Sentinel-1/SAR podem ser inseridos com `imobiliaria import-risk-inputs --csv arquivo.csv`. O resultado esta em `GET /api/analytics/risk-susceptibility` e e sempre um alerta analitico, nao um mapa oficial de risco.

Para automatizar relevo, execute `imobiliaria collect-dem-slope`, depois importe o CSV retornado. A coleta Sentinel-1 RTC tenta token SAS anonimo automaticamente. `PC_SDK_SUBSCRIPTION_KEY` e opcional e so deve ser configurada se voce possuir uma chave para ampliar limites de uso.

## Limitacoes atuais

O projeto ja reconhece o KML/KMZ oficial do PDPA e localiza anexos legais prioritarios, mas ainda precisa converter esses documentos em regras estruturadas completas e importar as geometrias em PostGIS para validar recomendacoes reais por coordenada. Enquanto essa etapa nao estiver fechada, os resultados devem ser tratados como demonstracao tecnica e apoio exploratorio, nao como parecer urbanistico ou recomendacao juridicamente validada.

## Direcao do produto

A direcao mais importante agora e fortalecer a base legal e territorial. O diferencial do projeto nao sera apenas usar IA, mas combinar IA com dados oficiais, regras urbanisticas e explicabilidade. Isso permite transformar o sistema em uma ferramenta de decisao urbana mais confiavel, auditavel e util para analise imobiliaria.
