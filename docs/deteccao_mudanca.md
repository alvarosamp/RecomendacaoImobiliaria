# Deteccao de mudanca por satelite

Modulo: `src/recomendacao_imobiliaria/change_detection.py`. Tabela: `geo.urban_change_h3`.
Modelo: `config/change_model/` (`model.txt`, LightGBM em texto, e `meta.json`).

## O que mede

Area que era vegetada (ou terra) e virou obra, terraplenagem, loteamento em implantacao ou
construcao nova entre dois anos. E triagem, nao laudo: area deixada em pousio e galpao agricola
tambem entram.

## Dois niveis

| Nivel | Coluna | Como | Perfil |
|---|---|---|---|
| Alta confianca | `changed_*` | NDVI maximo anual por pixel: era verde (>= 0,45) e nao ficou verde (<= 0,35) em nenhuma observacao valida do ano seguinte | Poucos alarmes falsos; perde casas pequenas e obra em terreno que ja estava exposto |
| Provavel | `probable_*` | Classificador LightGBM: estatisticas anuais de NDVI, 6 bandas da data seca (antes e depois), indices de solo exposto e vizinhanca | Recupera a maior parte do que a regra perde; marca 2 a 3 vezes mais area do que a referencia confirma |

O score usa o nivel provavel (fracao da celula alterada) quando existe; senao, o de alta confianca.

## Dados

Sentinel-2 L2A Collection 1 (Earth Search), 10 m, municipio inteiro (mosaico de tiles). Uma data por
bimestre (a menos nublada), mascara de nuvem/sombra/agua por pixel (SCL), pelo menos 3 observacoes
validas por pixel em cada ano. A data seca (jun-set) menos nublada e a unica lida com todas as bandas.
Agregacao pelo poligono exato de cada celula H3.

## Qualidade medida

Referencia: mapa anual de cobertura a 10 m da Impact Observatory (Planetary Computer, CC BY 4.0),
classe "construida" que surge entre os anos; so existe ate 2023. **A referencia tambem e um modelo e erra
nos dois sentidos**, entao os numeros sao um piso. O MapBiomas deixou de aceitar acesso anonimo
(HTTP 403, 10/11/2026).

Treino em Pouso Alegre (2019 -> 2023, metade oeste; limiar escolhido na metade leste). Teste em
**Santa Rita do Sapucai, cidade que o modelo nunca viu**:

| Santa Rita 2019 -> 2023 | Alta confianca | Provavel |
|---|---|---|
| Blocos de 200 m: precisao / recall | 0,38 / 0,19 | 0,31 / 0,78 |
| Area marcada | 94 ha | 948 ha |
| Area nova segundo a referencia | 520 ha | 520 ha |
| Por celula (~74 ha): correlacao de Spearman com a construcao nova | 0,50 | **0,70** |
| Por celula: acerto no decil superior | 0,36 | **0,52** |

Pontos importantes:

- A correlacao por celula e a metrica que importa para o score. Em Pouso Alegre (parcialmente em
  amostra) foi 0,60 -> 0,79.
- Em blocos de 200 m o nivel provavel tem precisao baixa (0,31): so 15% da area marcada e construcao nova
  segundo a referencia, 23% era ja construida antes e 55% e lavoura ou pasto. Use-o como ordenacao, nao
  como mapa de obras.
- Em celulas ja urbanizadas (> 10% construido) o nivel provavel marca 1,3 a 2 vezes mais do que a
  referencia (7-8% contra 4-5%).
- A correlacao do nivel provavel com a fracao ja construida (0,65-0,71) e proxima da da propria referencia
  (0,75-0,77): construcao nova nasce perto de cidade. Nao e viés de marcar cidade consolidada.
- Rodada operacional 2025 -> 2026 em Pouso Alegre: 1.496 ha provaveis (158 ha de alta confianca); nas 49
  celulas urbanas consolidadas a mediana e 2,3% por celula.
- Inspecao visual (leitura minha, subjetiva, 24 trechos de Santa Rita): entre o que o classificador marca
  e a referencia confirma, a maioria e mudanca real; entre o que so ele marca, cerca de 1 em 3. Das seis
  celulas com maior pontuacao comercial em 2025 -> 2026, cinco mostram construcao nova clara (galpoes).

### Erro que ja aconteceu

A primeira versao do treino excluia as areas ja construidas segundo a referencia. O modelo nunca viu cidade
consolidada como negativo e marcou 56% dela como mudanca (5.197 ha em um ano). O treino atual usa todos os
pixels validos. A metrica "ja_construida_antes" existe para pegar isso de novo.

## Por que nao diferenca de indices

Metodo do radar da versao de provedores (diferenca de NDVI/NDBI entre duas datas da estacao seca), testado
no municipio inteiro: precisao 0,18 por bloco de 200 m, 4.171 ha marcados, 66-83% lavoura. Descartado.

## Uso

```bash
python -m recomendacao_imobiliaria.cli detect-change --before 2025 --after 2026 --output-dir data/processed/mudanca
python -m recomendacao_imobiliaria.cli detect-change --before 2019 --after 2023 --validate
python -m recomendacao_imobiliaria.cli validate-change --bbox OESTE SUL LESTE NORTE --before 2019 --after 2023
python -m recomendacao_imobiliaria.cli train-change-model --bbox OESTE SUL LESTE NORTE --before 2019 --after 2023
```

GeoTIFF de saida: 0 sem mudanca, 1 provavel, 2 alta confianca, 255 sem observacao valida.

No score, o sinal de crescimento so e aplicado dentro do perimetro zoneado e quando a celula tem pelo
menos 50% de area observada; 15% da celula alterada (nivel provavel) equivale ao sinal maximo
(`growth_change_fraction_full`).

## Limites conhecidos

- Nao detecta construcao sobre terreno que ja estava sem vegetacao (nivel de alta confianca).
- 10 m nao conta edificacoes; confirmar com imagem de maior resolucao ou vistoria.
- O modelo foi treinado com um par de anos 4 anos distantes; pares de 1 ano (a rodada operacional) nao
  tem taxa de acerto medida, e as datas secas dos dois anos nem sempre coincidem.
- Treinado em uma cidade (Pouso Alegre) contra uma referencia enviesada; mais cidades no treino devem
  ajudar, mas deixam de ser teste fora da amostra.
- Os alarmes incluem galpoes agricolas e industriais, nao so uso residencial ou comercial.
