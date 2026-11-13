# Proposta de pesquisa — Closed-Loop Edge GeoAI

**Título:** Avaliação e atualização controlada de modelos compactos de segmentação de água em imagens SAR sob mudanças geográficas e restrições de CPU.

**Versão:** 0.1 — 14 de outubro de 2026. **Natureza:** proposta de pesquisa aplicada; nenhum resultado experimental foi produzido. Revisão bibliográfica inicial, não sistemática. Os valores de orçamento e margens abaixo são escolhas de desenho propostas, a serem verificadas em piloto e congeladas antes dos experimentos principais.

## 1. Resumo

Investigar quando vale a pena reavaliar e atualizar um modelo de segmentação de água superficial executado em CPU, diante de imagens Sentinel-1 provenientes de eventos e regiões diferentes. O estudo separará três questões: generalização geográfica, efeito da quantização e utilidade de uma política de avaliação/atualização sob orçamento. Serão comparados limiarização SAR, U-Net e uma variante compacta, inicialmente com rótulos manuais do Sen1Floods11. Um replay offline disponibilizará rótulos com atraso explícito para comparar modelo congelado, atualização periódica e avaliação acionada por mudança de distribuição. A promoção de modelos dependerá de validação independente e restrições de recursos. A contribuição pretendida é uma avaliação reproduzível desse compromisso em condições delimitadas; sua novidade e vantagem permanecem em investigação.

O cruzamento com infraestrutura será uma demonstração posterior de possível exposição espacial. Não validará dano, segurança estrutural ou risco operacional.

## 2. Problema e motivação

Uma segmentação precisa no domínio de treinamento pode falhar em outro evento. Por outro lado, atualizar sempre pode desperdiçar recursos e introduzir regressões. Um detector de mudança pode emitir alertas sem que a qualidade diminua; um modelo pode degradar sem que esse detector perceba. O problema de pesquisa é decidir **quando gastar recursos com avaliação rotulada e quando uma atualização é justificável**, mantendo um modelo que respeite o dispositivo de inferência.

O cenário de engenharia é uma estação terrestre ou computador local com CPU e conectividade limitada ou intermitente. As imagens chegam como produtos já disponibilizados; a proposta não assume processamento a bordo de satélite nem acesso instantâneo às aquisições. Treinamento e atualização podem ocorrer em uma máquina externa; inferência e telemetria serão locais. O custo de transferência e a demora até o recebimento do novo modelo serão contabilizados quando emulados.

**Delimitação semântica:** a máscara binária manual descrita no repositório do Sen1Floods11 distingue água, não água e pixels inválidos. A tarefa inicial será chamada de **segmentação de água superficial em cenas de eventos de inundação**. Identificar inundação nova exige uma referência anterior de água permanente e validação própria. Subtrair uma máscara histórica fornece apenas uma estimativa, sujeita a desalinhamento e diferenças sazonais. [Documentação oficial do dataset](https://github.com/cloudtostreet/Sen1Floods11).

## 3. Pergunta e objetivos

**Pergunta principal:** em um replay de eventos SAR não usados no treinamento inicial, uma política que aciona avaliação rotulada a partir de sinais de mudança de distribuição consegue preservar a IoU de água com menor custo total de avaliação e atualização do que uma política periódica, sob o mesmo acesso a rótulos, atraso de feedback e limites de inferência em CPU?

**Objetivo geral:** medir a fronteira entre qualidade, custo de atualização e recursos de inferência, com decisões causais em relação ao tempo do replay.

**Objetivos específicos:**

1. Auditar os dados e reproduzir baselines com separação verificável por eventos e regiões.
2. Quantificar a diferença entre desempenho no domínio e em eventos retidos.
3. Comparar FP32 e INT8 no mesmo dispositivo e com o mesmo pipeline.
4. Medir a relação entre alertas de drift e degradação observada posteriormente.
5. Comparar políticas com orçamento e feedback equivalentes, incluindo falhas de adaptação.
6. Demonstrar implantação versionada, aprovação e rollback sem confundir essa demonstração com evidência científica de superioridade.

## 4. Hipóteses e critérios de decisão

As margens a seguir são provisórias e expressas em pontos absolutos de IoU na escala 0–1. Serão mantidas ou revistas com justificativa usando apenas o piloto de desenvolvimento; alterações terão registro anterior ao teste principal.

| Hipótese | Comparação e desfecho | Evidência necessária |
| --- | --- | --- |
| H1 — quantização oferece uma configuração mais eficiente | Mesmo checkpoint FP32 versus INT8; margem de não inferioridade de 0,02 na IoU macro por evento | Limite inferior do IC de ΔIoU acima de −0,02, redução de tamanho e redução mensurável em P95 ou pico de memória; ganhos declarados por recurso, sem exigir que todos melhorem |
| H2 — mudança de domínio está associada a pior generalização | U-Net fixa: eventos retidos versus validação no domínio, com prevalência e contexto descritos | ΔIoU por evento e IC; uma queda média de 0,05 é uma referência de relevância prática, não um resultado esperado garantido nem prova causal do fator geográfico |
| H3 — política adaptativa melhora o compromisso qualidade–custo | Adaptativa versus periódica, mesmo modelo inicial, orçamento e atraso | Não inferioridade de 0,02 na IoU agregada do replay e menor custo total; reportar ICs, orçamento efetivamente gasto e fronteira de Pareto |

H1 pode falhar por operadores, calibração ou CPU. H2 pode não se verificar nos eventos disponíveis. H3 pode ser rejeitada se monitoramento e falsas solicitações custarem mais que a economia. Ausência de evidência de inferioridade não será tratada como demonstração de não inferioridade: o intervalo precisa sustentar a margem. Se houver poucas unidades independentes, a conclusão será inconclusiva ou descritiva.

## 5. Revisão inicial e contribuição a demonstrar

| Trabalho ou recurso | O que já existe | Relação e limite para esta proposta |
| --- | --- | --- |
| Bonafilia et al., Sen1Floods11, CVPR Workshops 2020 | Dataset georreferenciado e comparação de segmentação aprendida com limiarização SAR | Dados e baselines de partida; usar esse dataset ou aplicar CNN a SAR não constitui novidade. [Artigo](https://openaccess.thecvf.com/content_CVPRW_2020/html/w11/Bonafilia_Sen1Floods11_A_Georeferenced_Dataset_to_Train_and_Test_Deep_Learning_CVPRW_2020_paper.html) |
| Ronneberger et al., U-Net, 2015 | Arquitetura de segmentação com caminhos de contração e expansão | Baseline consolidado; sua aplicação isolada não é a contribuição. [Preprint original](https://arxiv.org/abs/1505.04597) |
| Koh et al., WILDS, ICML 2021 | Benchmark de mudanças de distribuição reais, incluindo imagens de satélite | Referência metodológica para avaliação fora do domínio; não é benchmark específico de inundação. [Artigo](https://proceedings.mlr.press/v139/koh21a.html) |
| Rabanser et al., Failing Loudly, NeurIPS 2019 | Avaliação de métodos de detecção de dataset shift | Motiva comparar testes em atributos/representações; detecção não substitui avaliação rotulada. [Artigo](https://papers.neurips.cc/paper_files/paper/2019/hash/846c260d715e5b854ffad5f70a516c88-Abstract.html) |
| Bhardwaj et al., Ekya, NSDI 2022 | Aprendizado contínuo para análise de vídeo em servidores de borda, considerando treinamento e inferência | Evidência de que o compromisso atualização–qualidade na borda já é estudado; cenário de vídeo e servidor difere da inferência SAR em CPU. [Artigo](https://www.usenix.org/conference/nsdi22/presentation/bhardwaj) |
| Zhao et al., UrbanSARFloods, EarthVision/CVPR Workshops 2024 | Benchmark com intensidade e coerência SAR para áreas urbanas e abertas | Explicita desafios urbanos; possível extensão, com diferenças de entrada que impedem comparação direta sem harmonização. [Artigo](https://arxiv.org/abs/2406.04111) |
| Nie et al., Remote Sensing 2026 | Modelo CNN–Transformer leve para SAR e inferência em CPU em terminais de emergência | Antecedente diretamente próximo; “modelo leve de inundação em CPU” já foi estudado. Página primária indexada consultada; leitura técnica integral ainda pendente. [Artigo](https://www.mdpi.com/2072-4292/18/9/1418) |
| Chen et al., JGR: Machine Learning and Computation, agosto de 2026 | CIM-TTDA: adaptação em teste para inundação costeira usando SAR sem novos rótulos | Adaptação entre eventos SAR também já existe. Comparar pressupostos e custos; não assumir que atualização supervisionada atrasada é equivalente a TTDA. [Artigo](https://doi.org/10.1029/2025JH001145) |
| Schmalstieg et al., setembro de 2026, preprint | Destilação de modelo geoespacial e implantação INT8 em Jetson, com imagens Sentinel-2 | Antecedente de compressão para inundação na borda; modalidade óptica e GPU diferem do foco SAR/CPU. O registro consultado é preprint. [Registro primário](https://arxiv.org/abs/2609.20441) |
| Evaluating Cross-Country Generalization…, setembro de 2026, preprint | Comparação de splits aleatórios e por países no Sen1Floods11 | Retenção geográfica isolada também tem antecedente recente. Consulta limitada ao resumo indexado; revisão por pares não foi confirmada. [Registro primário](https://eartharxiv.org/repository/view/15258/) |

**Lacuna candidata, ainda não estabelecida:** avaliação conjunta de uma política que solicita avaliação rotulada sob orçamento, promove atualizações apenas após validação e contabiliza monitoramento, rotulagem, atualização e transferência, em segmentação SAR compacta sob mudanças entre eventos. A busca inicial não demonstra ausência de trabalhos equivalentes.

**Contribuições condicionais:** um protocolo de replay sem antecipação de rótulos; uma comparação controlada de políticas; e evidência sobre quando alertas justificam avaliação. A arquitetura de software será um artefato de engenharia. Só haverá contribuição algorítmica se uma política nova for formalizada e superar alternativas próximas em comparação justa. Resultados negativos ou ausência de dominância também serão relatados.

Antes de fixar a reivindicação científica, completar a matriz de trabalhos com leituras integrais, referências anteriores/posteriores e busca de literatura de 2020–14/10/2026 sobre SAR, atualização, drift, aprendizado ativo e restrições de recursos. O registro de busca acompanha esta proposta.

## 6. Dados, proveniência e auditoria

| Fonte | Uso e características verificadas | Auditoria necessária |
| --- | --- | --- |
| Sen1Floods11 | O artigo apresenta 11 eventos, 4.831 chips e subconjunto de 446 chips manuais; não são 4.831 amostras com rótulos manuais independentes | Confirmar contagens da versão baixada, datas por evento, qualidade e separações. O artigo e o conteúdo real devem ser conciliados. [Artigo](https://openaccess.thecvf.com/content_CVPRW_2020/html/w11/Bonafilia_Sen1Floods11_A_Georeferenced_Dataset_to_Train_and_Test_Deep_Learning_CVPRW_2020_paper.html) |
| Sentinel-1/Copernicus | Extensão futura com novos eventos; registrar produto e processamento | Fixar IDs, datas, órbita, polarização, calibração, terreno e unidade; o catálogo tem diferentes modos/produtos. [Coleção oficial](https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-1) |
| OpenStreetMap | Demonstração posterior com objetos de energia/transporte | Registrar data do extrato, consultas, IDs, tags, completude e licença ODbL, incluindo atribuição e obrigações aplicáveis à redistribuição. [Licença e atribuição](https://www.openstreetmap.org/copyright) |
| UrbanSARFloods | Extensão opcional para contextos urbanos | Confirmar licença, acesso e comparabilidade; coerência/interferometria introduz entradas ausentes no MVP. [Artigo](https://arxiv.org/abs/2406.04111) |

Na versão inicial: entradas VV/VH em dB, chips 512 × 512 e rótulo manual; a documentação descreve −1 como inválido, 0 como não água e 1 como água. Confirmar essa convenção nos arquivos de fato usados. O README declara grade em EPSG:4326 e amostragem nominal de 10 m; verificar transformações reais e não confundir amostragem com resolução efetiva. Registrar datas de aquisição de S1 e S2 e o descompasso entre elas. [README oficial](https://github.com/cloudtostreet/Sen1Floods11).

**Licenças:** não atribuir CC BY aos rótulos com base em espelhos de terceiros. A consulta localizou uma issue aberta sobre ausência de LICENSE no repositório original; isso documenta uma pendência, não determina sozinho os termos do bucket. Registrar a evidência do provedor e esclarecer permissões antes de redistribuir rótulos ou derivados sujeitos a licença. Enquanto isso, planejar publicação de código, manifests e instruções, condicionada às permissões aplicáveis. [Issue oficial #18](https://github.com/cloudtostreet/Sen1Floods11/issues/18). Para novas imagens Sentinel, guardar o aviso de uso e a atribuição exigida. [Termos Sentinel](https://cds.climate.copernicus.eu/licences/ec-sentinel).

O manifesto conterá `sample_id`, evento, cena de origem quando disponível, região, data, órbita, polarizações, caminhos/URIs, SHA-256, CRS, transformação, bounds, tamanho, unidade, estatísticas de validade, origem do rótulo, partição e evidência de licença. Ausência de metadados será explicitada, nunca preenchida por suposição silenciosa.

## 7. Protocolo experimental

### 7.1 Separação dos dados

Estabelecer duas trilhas independentes, com manifests e resultados separados:

1. **Reprodução:** usar os splits publicados para comparar com o trabalho de origem, depois de auditar sua composição. Não presumir independência geográfica porque o split é oficial.
2. **Estudo principal:** dividir por evento/cena e região antes de recortar ou aumentar dados. Criar grupos de sobreposição/proximidade espacial; cenas relacionadas, chips contíguos relevantes e versões da mesma amostra permanecem no mesmo grupo. Verificar interseção e distância em CRS métrico apropriado. Testar sensibilidade a um buffer definido no piloto.

Distribuir grupos entre treinamento inicial, desenvolvimento, fluxo de avaliação adaptativa e teste geográfico final intocado. A quantidade de eventos por partição será decidida com o inventário, sem observar resultados dos candidatos. Se não houver diversidade suficiente para quatro conjuntos informativos, reduzir a ambição: priorizar generalização/quantização e tratar H3 como exploratória. Não anunciar H3 confirmatória com poucas transições artificiais.

Usar validação por grupos dentro do desenvolvimento para hiperparâmetros e limiares. Reservar eventos finais que nunca forneçam calibração INT8, limiares de drift, treinamento, seleção, aprovação ou rollback. Avaliá-los uma vez após congelar decisões; uma mudança de protocolo depois disso exige novo teste externo ou relato explícito de análise exploratória.

### 7.2 Baselines e treinamento

| ID | Método | Escolhas controladas |
| --- | --- | --- |
| B0 | Preditor constante sem água | Sanidade das métricas e efeito do desequilíbrio |
| B1 | Limiar VH global: `água = VH_dB < τ` | Escolher τ apenas em desenvolvimento; mesmo τ para todos os eventos de teste |
| B2 | Otsu em cada chip/cena | Não usa rótulos; escolher previamente unidade espacial, máscara válida, bins e fallback para histogramas degenerados |
| B3 | U-Net, duas entradas VV/VH | Arquitetura explícita, treinamento do zero, perda BCE + Dice com máscara de validade |
| B4 | U-Net com largura reduzida | Mesma família para isolar capacidade/custo; arquitetura móvel adicional só com justificativa |
| B5 | B3/B4 em ONNX FP32 e INT8 | Mesmo checkpoint de origem; calibração sem teste; verificar execução real dos operadores |

B1 é um baseline reproduzível inspirado em limiarização SAR. Só será chamado de reprodução exata do baseline publicado após conferir código, unidade, limiar, máscaras e pós-processamento originais. Metadados do evento podem conter limiares de referência: não usá-los no teste sem esclarecer sua origem e eventual acesso aos rótulos.

Plano inicial B3/B4: Adam, taxa 0,001, limite de 100 épocas, early stopping de 10 épocas por IoU de validação, aumentos espaciais aplicados conjuntamente a imagem e máscara. Seeds principais 17, 42 e 2026; cinco seeds apenas se o piloto justificar o custo. Fixar canais, normalização estimada no treino, batch, tamanho de patch e política de bordas na configuração. Limitar a busca a até seis configurações por família, com igual oportunidade de ajuste; registrar também o custo dessa busca. Seeds quantificam variabilidade de treinamento, não criam novos eventos independentes.

### 7.3 Quantização e inferência

Comparar PyTorch FP32, ONNX Runtime FP32 e quantização estática INT8 pós-treino. O ONNX Runtime documenta calibração estática, sugere essa abordagem para CNNs e alerta que aceleração depende do hardware. Portanto, tamanho menor não será usado como prova de inferência mais rápida. QAT será uma extensão se a quantização pós-treino falhar; incluir seu custo. [Documentação primária](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html).

Benchmark proposto: batch 1, entrada fixa 512 × 512, 50 aquecimentos, pelo menos 200 inferências e cinco sessões em processos novos. Publicar P50/P95, dispersão entre sessões e número de amostras. Separar tempo do núcleo, pipeline completo de um chip (leitura, normalização, inferência e escrita) e inicialização fria. Fixar threads, provider, versões, energia/modo do sistema e processos concorrentes; registrar CPU/ISA, RAM e SO. Variar ordem dos candidatos entre sessões para reduzir efeito térmico/cache.

Medir RSS de pico em processo isolado, tamanho do artefato e throughput com batch/concorrência explícitos. Registrar separadamente footprint de execução e memória de treinamento. Restringir threads/RAM em desktop caracteriza experimento limitado nesse host; não simula de modo fiel uma CPU ARM. Executar e identificar hardware ARM real quando disponível. Energia só será publicada com instrumento/API de medição descrito, limites de medição e repetição; tempo de CPU não equivale a joules. Se indisponível, registrar “não medido”.

## 8. Replay e política adaptativa

### 8.1 Separação entre mudança e degradação

Drift de entrada corresponde a evidência de mudança em `P(X)`; uma mudança em `P(Y|X)` não é identificável apenas por observar entradas. Degradação será definida por métricas contra rótulos liberados, com incerteza. Entropia de saída é um sinal auxiliar e não garante erro nem calibração.

Detector inicial simples: distância entre histogramas fixos de VV/VH e referência de treino, calculada por chip e agregada em janela. Uma extensão poderá usar teste de duas amostras em representações congeladas. Calibrar limiar por janelas de desenvolvimento, preservando blocos espaciais, e registrar alertas por 100 janelas. Evitar testes que tratem todos os pixels correlacionados como observações independentes. Controlar repetição de alertas com persistência, cooldown e orçamento; a taxa de falsos alertas será medida, não inferida de um único p-valor.

### 8.2 Políticas comparadas

| Política | Decisão | Controle de comparação |
| --- | --- | --- |
| P0 — congelada | Nenhuma atualização | Mesmo modelo inicial, inferência e auditoria comum |
| P1 — periódica | Avaliar a cada k janelas e treinar se houver degradação | k escolhido no desenvolvimento; mesmo orçamento máximo |
| P2 — adaptativa | Solicitar avaliação quando houver drift persistente; treinar só após degradação confirmada | Mesmos dados elegíveis, atraso, orçamento e regra de promoção |
| P3 — avaliação periódica com atualização sempre que elegível | Treinar em toda oportunidade periódica com rótulos suficientes | Referência de atualização mais frequente, limitada ao mesmo orçamento |
| P4 — acionamento aleatório | Solicitar avaliação em instantes sorteados, sob o mesmo orçamento | Verifica se o ganho vem do sinal de drift ou apenas da quantidade de oportunidades |

Comparar também curvas qualidade–custo para frequências/orçamentos escolhidos previamente no desenvolvimento. Igualar orçamento disponível e contabilizar gasto real; não dar à política adaptativa mais rótulos, épocas ou tentativas. Um oráculo que conhece erros futuros, se usado, será apenas um limite informativo separado.

### 8.3 Ordem de cada janela

1. Receber um lote de chips agrupados por aquisição/evento. Emitir e persistir previsões com o modelo ativo **antes** de acessar os rótulos desse lote.
2. Registrar telemetria e calcular drift sem rótulos. A política decide se solicita avaliação, respeitando saldo de orçamento.
3. Liberar somente o feedback autorizado cuja data de disponibilidade tenha chegado. Cenário inicial: atraso de uma janela; sensibilidades de zero e três janelas, com o caso zero liberado somente após a previsão. São atrasos sintéticos, não observações de operação real.
4. Manter uma amostra de auditoria independente, reservada para o avaliador, que não alimenta política, treinamento ou promoção. A política recebe apenas rótulos explicitamente liberados para ela.
5. Dentro dos rótulos solicitados e liberados, respeitar partições por grupos para diagnóstico, adaptação e aceitação. Não reutilizar a amostra que treinou o candidato como evidência de aceitação. Se o lote for insuficiente, adiar a atualização.
6. Se a avaliação confirmar degradação além da margem pré-fixada de 0,05 e houver orçamento, treinar um candidato com receita fixa, dados novos elegíveis e replay de dados históricos de treino. Quantizar e validar o artefato final.
7. Promover somente se cumprir critérios de aceitação. O modelo novo valerá para janelas futuras; não substituir retroativamente previsões que já contam para as métricas.

O Sen1Floods11 contém eventos separados, não uma série operacional longa e contínua. Quando datas permitirem, usar ordem cronológica; não apresentar uma permutação arbitrária como cronologia real. Sequências alternativas e perturbações de aquisição serão testes sintéticos de sensibilidade, sem aumentar artificialmente o número de eventos independentes. Se não houver rótulos novos, o replay poderá emular sua liberação a partir de dados reservados; sem esses rótulos será possível avaliar alertas e engenharia, mas não comprovar benefício supervisionado de atualização.

### 8.4 Aceitação, custos e rollback

Antes do replay final, congelar uma regra única para todas as políticas: ganho mínimo de 0,01 em IoU na aceitação do domínio recente, regressão máxima de 0,02 na suíte histórica de aceitação, compatibilidade do artefato e limites de P95/memória definidos pelo dispositivo no piloto. Usar IC quando a amostra permitir; caso contrário, declarar a regra como heurística exploratória. Impor máximo de tentativas por candidato e por janela para reduzir sobreajuste ao conjunto de aceitação.

Rejeitar promoção com entradas inválidas, falhas do runtime ou regressão acima do limite. Registrar estado anterior, hashes, config e decisão. Na demonstração, promoção exige aprovação registrada e troca atômica de versão; rollback restaura o artefato anterior por falha de integridade/runtime ou por degradação observada em feedback independente posterior. No estudo offline, aplicar a mesma regra determinística de aprovação emulada a todas as políticas. Isso não representa autorização para operação crítica real.

O custo será um vetor: tempo de monitoramento/avaliação, chips ou pixels anotados, tempo e hardware de treinamento/calibração/validação, bytes transferidos e tempo de implantação. Somar tempos apenas quando forem medidos em condições comparáveis; manter CPU e GPU separados ou usar conversão de custo explicitada. Rotulagem já existente terá custo operacional **emulado**, expresso em unidades de anotação; não atribuir horas humanas fictícias. Se usar escalar `C = Σ w_i C_i`, fixar pesos e unidades antes e publicar sensibilidade. A análise principal mostrará custos separados e fronteira de Pareto.

## 9. Métricas e análise

Para pixels válidos da classe água: `IoU = TP/(TP+FP+FN)` e `Dice/F1 = 2TP/(2TP+FP+FN)`. Reportar precision e recall e prevalência por evento. Em segmentação binária, Dice e F1 representam a mesma quantidade sob a mesma agregação; não serão tratados como evidências independentes.

**Desfecho primário de qualidade:** IoU de água calculada com contagens agregadas dentro de cada evento, seguida de média não ponderada entre eventos. Publicar também IoU global ponderada por pixels e resultados completos por evento. Se o denominador de IoU for zero, marcar indefinido e informar quantas unidades foram excluídas; se houver falso positivo em cena sem água, IoU é zero. Pixels inválidos não entram na perda nem na matriz de confusão. Publicar cobertura válida.

**Para replay:** métricas das previsões originais antes de atualização; média por evento e por janela, pior evento, custo total e por atualização, quantidade de avaliações, candidatos rejeitados, promoções, regressões e rollbacks. Relatar atraso até detectar degradação e até promover, além de alertas sem degradação rotulada posterior. Sem rótulos suficientes, o estado será “não verificável”, não falso positivo presumido.

**Para robustez:** resultados por região/órbita/data quando houver amostras suficientes; perturbações radiométricas plausíveis separadas de mudanças naturais. Não alegar efeito causal da órbita quando região e órbita estiverem confundidas. Calibração probabilística, Brier ou ECE poderão ser desfechos secundários com bins e amostragem definidos no desenvolvimento.

**Estatística:** comparar candidatos de modo pareado nos mesmos eventos e seeds. Usar IC de 95% para diferenças, com bootstrap em blocos por evento/cena; manter seeds como repetição interna e não como nova região. Descrever a instabilidade com poucos eventos; apresentar pontos individuais. Para replay, preservar dependência da trajetória e repetir sequências pré-especificadas sem tratar permutações como replicações independentes. Evitar teste por pixel. Reportar tamanho de efeito e relevância prática; p-valor isolado não sustentará conclusão. Se houver testes múltiplos confirmatórios, limitar comparações principais e aplicar Holm; marcar o restante como exploratório.

**Ablações mínimas:** sem detector versus detector; histogramas versus representação, se implementada; sem cooldown; atraso de rótulos; orçamento; atualização com e sem replay histórico; FP32 versus INT8; largura original versus reduzida. Executar progressivamente, evitando uma busca combinatória que consuma o orçamento e o conjunto de aceitação.

## 10. Arquitetura de engenharia

Fluxo alvo: ingestão → pré-processamento versionado → treino → validação → registro → implantação local → inferência → telemetria → alerta de drift → avaliação com rótulos disponíveis → candidato → testes e aceitação → aprovação → implantação/rollback.

Separar `experiments/` (protocolos, scripts, manifests, métricas e estatística) de `system/` (serviço, telemetria e mecanismo de atualização). O registro inicial pode ser um diretório imutável com JSON e hashes; um servidor de registry só será introduzido quando houver necessidade concreta. Inferência continuará possível sem conexão com o registro. A telemetria registrará versão do modelo e processamento, IDs das entradas, latência, memória e resumo de distribuição, permitindo reproduzir uma decisão.

O demonstrador geográfico adicionará interseções de água estimada com instalações ou vias, respeitando CRS, geometria, data e cobertura. Informará incerteza posicional e sensibilidade a buffers; não escolherá um buffer como limiar comprovado de risco. Sem referência de água permanente, usará o rótulo “possível exposição à água superficial mapeada”.

## 11. Ameaças à validade

| Ameaça | Consequência | Mitigação e limite remanescente |
| --- | --- | --- |
| Vazamento espacial, cenas repetidas e rótulos fracos | Resultados otimistas e circularidade com limiar SAR | Agrupar antes do split, auditar sobreposição e origem; teste principal manual; não avaliar limiarização contra seus próprios pseudorrótulos |
| Poucos eventos | ICs instáveis e baixa generalização | Unidades por evento, incerteza explícita; extensão externa se viável, sem prometer representatividade global |
| Rótulos ruidosos e aquisição óptica/SAR desencontrada | Erro de referência confundido com falha do modelo | Auditoria visual e temporal, estratos de qualidade; não remover casos difíceis após observar erros sem análise de sensibilidade |
| Água permanente versus inundação transitória | Alegação semântica incorreta | Nomear tarefa real; avaliar separação temporal em estudo adicional |
| Ambiguidade SAR urbana/vegetada, sombra e relevo | Água omitida ou falsos positivos próximos de infraestrutura | Análise estratificada e exemplos; limitações do sensor permanecem |
| Drift benigno ou detector insensível | Avaliações desperdiçadas ou degradação não detectada | Comparar com rótulos posteriores e controle aleatório/periódico |
| Sobreajuste à aceitação e esquecimentos | Promoções aparentes que pioram outros domínios | Limitar tentativas, replay histórico e teste final intocado; aceitação repetida continua sendo limitação |
| Hardware e runtime específicos | Ganhos de INT8 não transferíveis | Medição no host real, versões/provider fixos, distinguir CPU de GPU e emulação de hardware real |
| Replay curto e atraso simulado | Benefício sem validade operacional | Documentar sequência e feedback; não equiparar a implantação real |
| Dados OSM incompletos ou atuais para evento antigo | Exposição atribuída a ativo inexistente naquela data | Extrato datado/histórico quando disponível; sem isso, apenas ilustração |
| Seleção e múltiplas comparações | Vantagem produzida por ajuste de protocolo | Pré-registro, orçamento igual, resultados negativos e trilha de decisões |
| Pendências de licença | Reprodutibilidade e redistribuição limitadas | Evidência por componente e publicação condicionada a termos verificáveis |

## 12. Fases, entregáveis e critérios para avançar

Estimativa de planejamento para uma pessoa em dedicação parcial: 20–26 semanas, dependente de disponibilidade de dados e computação; não é previsão garantida.

| Fase | Faixa estimada | Entrega e critério de passagem |
| --- | --- | --- |
| 1 — revisão/protocolo | 2–3 semanas | Matriz de antecedentes, pergunta refinada, custos/margens e limites registrados; lacuna tratada como candidata |
| 2 — auditoria/MVP | 2–3 semanas | Manifest, licença documentada, splits auditados e limiarização reproduzível; ver plano do MVP |
| 3 — baselines/geografia | 3–4 semanas | U-Net e relatório por evento; dados suficientes para estimar variabilidade |
| 4 — edge | 3–4 semanas | FP32/INT8 e modelo compacto com benchmark no hardware identificado |
| 5 — replay/atualização | 5–6 semanas | Políticas sob orçamento e feedback equivalentes; promoções e rejeições auditáveis |
| 6 — análise/escrita | 5–6 semanas | Ablações priorizadas, limitações, tabelas geradas por código e relatório técnico |

Publicar código reprodutível, scripts de dados, manifests, configs, ambientes fixados, checkpoints quando permitido, resultados brutos e tabelas. Escrever artigo científico em LaTeX somente depois de obter e analisar resultados. Nenhuma promessa de originalidade, publicação ou sucesso em candidaturas decorre deste planejamento.

**Primeiro marco:** reproduzir uma máscara e uma tabela de limiarização SAR em CPU com dados válidos, partição registrada e nenhuma decisão tomada sobre o teste final. A implementação completa de MLOps começa apenas depois de esse marco e os baselines estarem verificáveis.
