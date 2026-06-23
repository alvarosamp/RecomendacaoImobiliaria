# Plano Diretor e regras legais

## Premissa

A recomendacao imobiliaria precisa seguir o Plano Diretor de Pouso Alegre e a legislacao urbanistica complementar. O score economico ou ambiental nao pode liberar uma area que a lei bloqueia, condiciona ou exige estudo especifico.

## Fontes iniciais

- Lei Ordinaria 6476/2021 - Plano Diretor de Pouso Alegre.
- Legislacao municipal de uso, ocupacao e parcelamento do solo.
- Camara Municipal de Pouso Alegre e SAPL como fontes de normas.

## Onde conseguir os documentos

Priorize fontes oficiais:

- Prefeitura de Pouso Alegre: https://pousoalegre.mg.gov.br/
- Camara/Legislador - Lei Ordinaria 6476/2021: https://www.legislador.com.br/legisladorweb.asp?ID=122&WCI=LeiTexto&aaLei=2021&inEspecieLei=1&nrLei=6476
- IBGE geociencias: https://www.ibge.gov.br/geociencias/downloads-geociencias.html
- IDE-Sisema MG: https://idesisema.meioambiente.mg.gov.br/

Se o mapa georreferenciado de zoneamento nao estiver publicado, solicite a Prefeitura por e-SIC/Lei de Acesso a Informacao. Texto sugerido:

```text
Solicito o arquivo georreferenciado do zoneamento urbano de Pouso Alegre, preferencialmente em Shapefile, GeoPackage, GeoJSON ou KML, contendo sigla/codigo da zona e descricao, alem dos anexos do Plano Diretor e da lei de uso e ocupacao do solo em vigor.
```

Salve os arquivos recebidos em `data/official/` e rode:

```powershell
$env:PYTHONPATH='src'
python -m recomendacao_imobiliaria.cli validate-official-data
```

## Como o codigo usa a lei

O arquivo `config/plan_director_pouso_alegre.json` guarda uma matriz inicial de compatibilidade por zona.

Cada zona pode marcar um uso como:

- `allowed`: permitido em principio;
- `conditioned`: depende de parametros, infraestrutura, impacto, licenciamento ou regra especifica;
- `blocked`: nao deve ser recomendado pela ferramenta.

O modulo `src/recomendacao_imobiliaria/plan_director.py` le essa matriz e devolve:

- status legal;
- multiplicador do score;
- observacao juridico-urbanistica;
- fontes legais.

## Efeito no score

- Uso `allowed`: score mantido.
- Uso `conditioned`: score reduzido por multiplicador conservador.
- Uso `blocked`: score zerado.

Isso evita que a IA recomende uma area ambiental, cultural ou especial como se fosse investimento comum.

## Limites atuais

Esta e uma matriz inicial conservadora. Para uso juridico/tecnico real, ainda falta:

1. importar o mapa oficial de zoneamento;
2. importar anexos/tabelas oficiais de parametros urbanisticos;
3. separar usos comerciais por grau de incomodidade;
4. cruzar APP, areas de risco, patrimonio, diretrizes viarias e infraestrutura;
5. citar artigo/anexo especifico no `explain_json`.

## Proxima evolucao

Transformar o Plano Diretor e leis complementares em uma base RAG:

- extrair artigos e anexos;
- salvar em `public.regs`;
- gerar embeddings;
- responder perguntas como "pode construir mercado na ZEU?";
- sempre devolver citacao legal e link da norma.
