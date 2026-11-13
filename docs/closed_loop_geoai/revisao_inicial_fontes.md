# Registro da revisão inicial

Data de referência: 14/10/2026, horário de São Paulo. Busca exploratória pela web, com prioridade para artigos, registros dos autores, proceedings, repositórios oficiais e documentação de runtime. Não foi realizada revisão sistemática nem avaliação integral de todos os PDFs; não há base para afirmar exaustividade ou originalidade.

## Fontes e nível da consulta

| Fonte primária | Material consultado | Uso e pendência |
| --- | --- | --- |
| [Sen1Floods11 — CVF](https://openaccess.thecvf.com/content_CVPRW_2020/html/w11/Bonafilia_Sen1Floods11_A_Georeferenced_Dataset_to_Train_and_Test_Deep_Learning_CVPRW_2020_paper.html) | Página do artigo/resumo e metadados; extratos indexados do PDF | Motivação, composição e baselines. Conferir integralmente protocolo/código antes de reprodução exata |
| [Sen1Floods11 — código e documentação](https://github.com/cloudtostreet/Sen1Floods11) | README e docs/README na origem | Formato, unidades, classes, acesso e versão. Conteúdo real do bucket ainda não foi auditado |
| [Issue #18 — licença](https://github.com/cloudtostreet/Sen1Floods11/issues/18) | Relato público no repositório original | Pendência de licença; não equivale a parecer jurídico nem a licença dos dados |
| [U-Net](https://arxiv.org/abs/1505.04597) | Registro original e resumo | Baseline arquitetural |
| [WILDS](https://proceedings.mlr.press/v139/koh21a.html) | Página de proceedings/resumo | Justificativa metodológica de avaliação fora do domínio |
| [Failing Loudly](https://papers.neurips.cc/paper_files/paper/2019/hash/846c260d715e5b854ffad5f70a516c88-Abstract.html) | Resumo nos proceedings | Detecção de mudança e separação de objetivos; comparar métodos integralmente na próxima etapa |
| [Ekya](https://www.usenix.org/conference/nsdi22/presentation/bhardwaj) | Página USENIX/resumo | Atualização e recursos de borda; não transferir ganhos numéricos para SAR |
| [UrbanSARFloods](https://arxiv.org/abs/2406.04111) | Registro original/resumo | Limites urbanos e possível extensão; licença do dataset ainda a verificar |
| [Nie et al., 2026](https://www.mdpi.com/2072-4292/18/9/1418) | Conteúdo primário indexado, incluindo resumo e introdução; abertura direta retornou erro | Antecedente SAR/CPU diretamente relevante. Não foram auditadas tabelas, detalhes de benchmark ou código |
| [Chen et al., 2026](https://doi.org/10.1029/2025JH001145) | Página editorial, resumo e trechos do texto integral | Antecedente de adaptação entre eventos SAR; protocolo integral/código ainda a analisar |
| [Schmalstieg et al., 2026](https://arxiv.org/abs/2609.20441) | Registro primário e resumo | Preprint sobre destilação/INT8 e óptico/Jetson; não comparação direta com SAR/CPU |
| [Cross-Country Generalization, 2026](https://eartharxiv.org/repository/view/15258/) | Resumo e metadados indexados; abertura direta não trouxe texto útil | Preprint próximo da avaliação por países; autoria, protocolo integral e revisão por pares a conferir |
| [ONNX Runtime](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html) | Documentação técnica oficial | Calibração, INT8, dependência de hardware e limitações de aceleração |
| [Copernicus Sentinel-1](https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-1) | Coleção oficial | Produtos e acesso para extensão |
| [Termos Sentinel](https://cds.climate.copernicus.eu/licences/ec-sentinel) | Aviso oficial | Registrar atribuição/termos ao adquirir dados |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | Página oficial de licença/atribuição | Planejar uso de infraestrutura e governança de derivados |

## Estratégia para concluir a revisão

Strings exploratórias usadas incluíram `Sen1Floods11 dataset official paper`, `flood mapping SAR concept drift continual learning edge adaptive retraining`, `flood mapping quantization Sentinel edge`, `Sentinel-1 edge lightweight flood segmentation` e `Sen1Floods11 continual`.

Na próxima iteração, executar buscas separadas e rastreáveis para evitar que uma string ampla oculte resultados:

1. `(Sentinel-1 OR SAR) AND flood AND (drift OR domain adaptation OR continual learning)`.
2. `flood segmentation AND (edge OR CPU OR quantization OR lightweight)`.
3. `(retraining OR model update) AND (budget OR delayed labels OR active learning) AND distribution shift`.
4. Busca retroativa/prospectiva dos trabalhos mais próximos, incluindo sistemas de mapeamento operacional como contexto.

Critérios de inclusão: método verificável, dados/protocolo identificáveis e relação explícita com pelo menos um eixo da pergunta. Separar artigos revisados por pares, preprints e documentação. Excluir conteúdo sem fonte primária identificável; não usar páginas promocionais como evidência de resultados.

Extrair para cada trabalho: tarefa e definição de água/inundação, modalidades, datas, dados, unidade do split, acesso a rótulos no teste, política de adaptação, custo, dispositivo, métricas, código, licença e limitações. Registrar também falhas de reprodução e acesso.

**Decisão atual:** manter a contribuição como candidata. Se houver política equivalente já avaliada em SAR sob orçamento e atraso, reformular como reprodução/extensão comparativa, identificar uma condição ainda não testada ou reduzir a ambição. A ausência de um resultado na busca exploratória não é evidência de lacuna científica.
