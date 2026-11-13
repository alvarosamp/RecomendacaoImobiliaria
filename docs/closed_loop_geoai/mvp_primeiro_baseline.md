# MVP — primeiro baseline de segmentação SAR em CPU

**Objetivo:** preparar dados auditáveis e reproduzir uma avaliação de limiarização de água superficial no Sen1Floods11 antes de redes neurais e da infraestrutura de atualização. Este documento especifica o MVP; os comandos abaixo são interfaces propostas, ainda não implementadas nem executadas.

## 1. Resultado que o MVP deve produzir

Uma execução gera: manifesto com hashes; relatório de integridade e composição dos splits; limiar escolhido exclusivamente no desenvolvimento; máscaras GeoTIFF georreferenciadas; IoU/Dice/precision/recall por evento; matriz de confusão válida; tempos de CPU; e figuras VV/VH, referência, previsão e erros.

Começar com 5–10 pares para um teste técnico de leitura e escrita, sem inferência científica. Depois usar o subconjunto manual elegível, confirmando as contagens da versão. O baseline não terá treino de rede, serviço HTTP, dashboard, registry remoto ou atualização adaptativa nesta etapa.

## 2. Organização proposta para um repositório independente

```text
closed-loop-edge-geoai/
  README.md
  pyproject.toml
  configs/threshold_vh.yaml
  data/manifests/              # metadados versionados; rasters fora do Git
  protocols/splits/            # listas imutáveis e relatório de sobreposição
  src/edge_geoai/
    acquire.py
    audit.py
    raster_io.py
    splits.py
    threshold.py
    metrics.py
    evaluate.py
  tests/                      # verificações semânticas e geográficas
  outputs/<run_id>/
    resolved_config.yaml
    provenance.json
    metrics_by_event.csv
    confusion_counts.csv
    runtime.json
    masks/
    figures/
```

Esta proposta foi salva como documentação no workspace atual. A implementação deve ter ambiente e pacote próprios, sem depender do projeto imobiliário ou do projeto anterior de desmatamento.

## 3. Passos de implementação

### A. Fixar dados e ambiente

Usar o repositório/bucket oficial do [Sen1Floods11](https://github.com/cloudtostreet/Sen1Floods11), fixando versão e revisão da documentação. Listar primeiro os objetos necessários e copiar apenas S1, rótulos manuais, splits e metadados. Não baixar o bucket inteiro por padrão. O README distingue a versão 1.1 e há inconsistência de grafia do bucket em um trecho; verificar o endpoint pelos objetos reais antes de gravá-lo no manifest.

Registrar licença por componente, inclusive a [pendência relatada no repositório original](https://github.com/cloudtostreet/Sen1Floods11/issues/18). Não tratar a licença declarada por um mirror como autorização do provedor. Confirmar os termos antes de redistribuir rótulos.

Bibliotecas mínimas candidatas: Python, NumPy, Rasterio, pandas, Matplotlib e pytest. Fixar versões compatíveis após um teste de instalação no ambiente real. Não é necessário PyTorch nesta etapa.

### B. Auditar rasters e partições

Verificar pareamento por ID, bandas VV/VH, unidade dB, dimensões, CRS, transformação, bounds, dtype, NoData, finitude e valores únicos do rótulo. Não aplicar conversão logarítmica duas vezes. Não filtrar valores negativos em dB: são fisicamente esperados. Apenas pixels válidos entram nas métricas; distinguir NoData dos valores de retroespalhamento baixos.

Produzir duas listas: split oficial para reprodução e split por grupos para o estudo posterior. Confirmar que um chip, sua cena e sua versão recortada não aparecem em partições distintas. Mapear footprints e avaliar sobreposição/proximidade em projeção métrica. Publicar quais verificações foram possíveis quando a cena de origem não estiver identificada.

O teste geográfico principal permanecerá reservado. Para o MVP usar validação ou um holdout dedicado à reprodução; não consumir o teste científico antes de congelar o estudo.

### C. Implementar B0 e B1

**B0:** prever não água em todos os pixels válidos. Deve expor o efeito do desequilíbrio e servir de controle das métricas.

**B1:** `pred = VH_dB < tau`. Escolher `tau` por maior IoU macro por evento no desenvolvimento. Grade piloto proposta: −35 a −5 dB, passo de 0,5 dB. Se a auditoria indicar que o intervalo não cobre valores relevantes, alterá-lo e registrar a razão antes de qualquer avaliação final. No empate escolher o menor limiar, regra fixa que tende a predizer menos água. O limiar é global e permanece congelado no conjunto de avaliação.

Não usar o limiar ótimo por evento de teste como baseline operacional; isso seria um oráculo com rótulos. Não usar máscaras fracas criadas por limiarização para avaliar o próprio B1. Desabilitar morfologia e filtros no primeiro resultado, para reduzir parâmetros e ambiguidade.

Esse método é uma reprodução conceitual de limiarização SAR. Para reprodução exata do artigo, inspecionar código original, banda, unidade, limiar e pós-processamento e documentar as diferenças. Não atribuir ao artigo um resultado produzido por configuração diferente.

### D. Adicionar B2 depois que B1 funcionar

Otsu por chip será a primeira alternativa sem rótulos. Fixar 256 bins em faixa documentada pelo desenvolvimento e usar só valores válidos. Chip sem pixels válidos será marcado como não avaliável. Histograma constante receberá um fallback explícito, por exemplo B1 global. Registrar fallback e seu número de ocorrências. Otsu por cena inteira é outra configuração e exige agregação de cena; não misturar as duas sob o mesmo nome.

### E. Avaliar e verificar as saídas

Salvar TP, FP, FN e TN por chip/evento; derivar métricas a partir dessas contagens. IoU e Dice de água não são “acurácia geral”. Preservar NoData nas máscaras gravadas e reabrir o GeoTIFF para conferir transformação e alinhamento com a entrada. Para distância/área, reprojetar adequadamente; não multiplicar pixels em graus por uma área fixa suposta.

Publicar macro por evento e micro por pixels. Casos sem denominador válido ficam indefinidos e contados; falsos positivos em cenas vazias resultam em IoU zero. Mostrar exemplos escolhidos por regra fixa de IDs e também casos difíceis; não apenas imagens favoráveis.

Medir leitura, inferência e escrita separadamente. Para um limiar, a leitura pode dominar o custo: reportar tempo total e do operador. Registrar CPU, RAM, SO, threads, arquivos e repetições. Não reportar energia sem medição nem chamar desktop limitado de dispositivo ARM simulado fielmente.

## 4. Interfaces de execução pretendidas

Exemplo da interface que a implementação deverá oferecer; estes comandos não estão disponíveis neste workspace:

```bash
python -m edge_geoai.acquire --config configs/threshold_vh.yaml
python -m edge_geoai.audit --manifest data/manifests/manual.csv
python -m edge_geoai.splits --config configs/threshold_vh.yaml
python -m edge_geoai.threshold --mode select --config configs/threshold_vh.yaml
python -m edge_geoai.evaluate --config outputs/selected/resolved_config.yaml
```

Cada execução terá identificador único e registrará commit, config resolvida, versões de dependências, hashes das partições, entrada e saída. Uma segunda execução com os mesmos dados/config deve reproduzir as contagens de confusão; tempos podem variar.

## 5. Verificações necessárias e critérios de conclusão

As verificações têm propósito científico, não apenas cobertura de implementação:

- Máscara perfeita produz IoU/Dice 1; água omitida produz FN; água espúria produz FP; invalidar um pixel o remove de ambas as contagens.
- Um chip todo inválido não entra silenciosamente com score zero ou um; um chip vazio com falsos positivos tem IoU zero.
- Limiar em dB opera sem transformação adicional; bandas trocadas são detectadas pelo contrato de entrada.
- Nenhum ID/grupo/footprint proibido cruza partições; estatísticas e escolha de limiar não leem rótulos do teste.
- A máscara gravada reabre com dimensões, CRS, transformação e NoData esperados.

O MVP está concluído quando uma execução documentada, em ambiente limpo, gera todos os artefatos; a seleção do limiar pode ser rastreada ao desenvolvimento; o relatório mostra resultados por evento, inclusive falhas; e outra execução reproduz as contagens. Não há uma IoU mínima obrigatória: um resultado fraco, se correto, é um baseline válido.

**Estimativa:** duas a três semanas em dedicação parcial, incluindo auditoria. A primeira entrega técnica pode ser feita com poucos pares; ela não comprova desempenho científico. Depois desse marco, implementar U-Net com as mesmas máscaras de validade, partições e métricas.
