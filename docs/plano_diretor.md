# Plano Diretor e regras legais

## Premissa

A recomendacao imobiliaria precisa seguir o Plano Diretor de Pouso Alegre e a legislacao urbanistica complementar. O score economico ou ambiental nao pode liberar uma area que a lei bloqueia, condiciona ou exige estudo especifico.

## Fontes iniciais

- Lei Ordinaria 6476/2021 - Plano Diretor de Pouso Alegre.
- Legislacao municipal de uso, ocupacao e parcelamento do solo.
- Camara Municipal de Pouso Alegre e SAPL como fontes de normas.

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
