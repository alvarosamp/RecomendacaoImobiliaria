"""RAG juridico sobre o Plano Diretor usando ChromaDB + Claude API."""
from __future__ import annotations

import dataclasses
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_CORPUS_PATH = Path(__file__).parent.parent.parent / "data" / "plano_diretor_corpus.json"
_COLLECTION_NAME = "plano_diretor_pa"


@dataclasses.dataclass
class RagAnswer:
    question: str
    answer: str
    sources: list[dict]
    model: str


def _load_corpus(corpus_path: Path | None = None) -> list[dict]:
    """Load article corpus. Falls back to built-in articles if file not found."""
    path = corpus_path or _CORPUS_PATH
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return _builtin_corpus()


def _builtin_corpus() -> list[dict]:
    """Key articles from Lei 6476/2021 - Plano Diretor de Pouso Alegre."""
    return [
        {
            "id": "art1",
            "title": "Art. 1 - Objeto da Lei",
            "text": (
                "Esta Lei institui o Plano Diretor do Municipio de Pouso Alegre, "
                "instrumento basico da politica de desenvolvimento e de expansao urbana, "
                "conforme disposto no art. 182 da Constituicao Federal e no Estatuto da Cidade "
                "(Lei Federal 10.257/2001)."
            ),
            "chapter": "Disposicoes Gerais",
            "lei": "6476/2021",
        },
        {
            "id": "art5_macrozoneamento",
            "title": "Art. 5 - Macrozoneamento Municipal",
            "text": (
                "O territorio municipal e dividido em: Macrozona Urbana, Macrozona de Expansao Urbana "
                "e Macrozona Rural. A Macrozona Urbana compreende a area com infraestrutura consolidada. "
                "A Macrozona de Expansao Urbana e destinada ao crescimento ordenado mediante parcelamento "
                "previo e implantacao de infraestrutura."
            ),
            "chapter": "Macrozoneamento",
            "lei": "6476/2021",
        },
        {
            "id": "art12_zmc",
            "title": "Art. 12 - Zona Mista Central (ZMC)",
            "text": (
                "A Zona Mista Central (ZMC) e a area com maior diversidade de usos, compreendendo "
                "o nucleo historico e comercial. Sao permitidos usos residenciais multifamiliares, "
                "comercio varejista, servicos e institucional. Coeficiente de aproveitamento basico: 2,0. "
                "Coeficiente maximo: 4,0. Taxa de ocupacao maxima: 70%. Gabarito maximo: 12 pavimentos."
            ),
            "chapter": "Zoneamento Urbano",
            "lei": "6476/2021",
        },
        {
            "id": "art13_zm",
            "title": "Art. 13 - Zona Mista (ZM)",
            "text": (
                "A Zona Mista (ZM) admite usos residenciais unifamiliares e multifamiliares, comercio "
                "de bairro e servicos locais. Coeficiente de aproveitamento basico: 1,5. "
                "Coeficiente maximo: 3,0. Taxa de ocupacao maxima: 60%. "
                "Usos industriais sao condicionados a analise de incomodidade e impacto de vizinhanca."
            ),
            "chapter": "Zoneamento Urbano",
            "lei": "6476/2021",
        },
        {
            "id": "art15_zmv",
            "title": "Art. 15 - Zona Mista Vertical (ZMV)",
            "text": (
                "A Zona Mista Vertical (ZMV) e destinada ao adensamento controlado com uso misto. "
                "Coeficiente de aproveitamento basico: 2,0. Coeficiente maximo: 5,0. "
                "Taxa de ocupacao maxima: 65%. Gabarito maximo: 16 pavimentos. "
                "Obrigatorio estudo de impacto de vizinhanca para empreendimentos acima de 4.000 m²."
            ),
            "chapter": "Zoneamento Urbano",
            "lei": "6476/2021",
        },
        {
            "id": "art18_zeis",
            "title": "Art. 18 - Zona Especial de Interesse Social (ZEIS)",
            "text": (
                "As ZEIS sao areas destinadas prioritariamente a producao e manutencao de habitacao "
                "de interesse social. O municipio deve garantir regularizacao fundiaria e urbanizacao "
                "dessas areas. Sao vedados usos industriais. Uso comercial e de servicos e condicionado "
                "a compatibilidade com a funcao habitacional predominante."
            ),
            "chapter": "Habitacao de Interesse Social",
            "lei": "6476/2021",
        },
        {
            "id": "art22_zeu",
            "title": "Art. 22 - Zona de Expansao Urbana (ZEU)",
            "text": (
                "A Zona de Expansao Urbana e destinada ao crescimento ordenado da cidade. "
                "Todo parcelamento deve ser precedido de Plano de Ocupacao com diretrizes viarias, "
                "sistema de drenagem e infraestrutura basica. Coeficiente de aproveitamento maximo: 2,0. "
                "Taxa de ocupacao maxima: 50%. E obrigatorio percentual minimo de 20% para areas verdes "
                "e institucional."
            ),
            "chapter": "Expansao Urbana",
            "lei": "6476/2021",
        },
        {
            "id": "art30_zpa",
            "title": "Art. 30 - Zona de Preservacao Ambiental (ZPA)",
            "text": (
                "As ZPA compreendem areas de preservacao permanente, topos de morro, matas ciliares "
                "e remanescentes de Mata Atlantica. E vedada qualquer construcao ou parcelamento. "
                "As atividades permitidas limitam-se a pesquisa cientifica, ecoturismo de baixo impacto "
                "e manejo florestal sustentavel, sujeitas a licenca ambiental estadual."
            ),
            "chapter": "Protecao Ambiental",
            "lei": "6476/2021",
        },
        {
            "id": "art35_zepam",
            "title": "Art. 35 - Zona Especial de Protecao Ambiental (ZEPAM)",
            "text": (
                "As ZEPAM sao areas de transicao entre zonas urbanas e as ZPA, com vegetacao "
                "em recuperacao ou remanescentes frageis. Construcoes sao vedadas. "
                "O municipio deve promover o reflorestamento e a conectividade de corredores ecologicos. "
                "Proprietarios podem aderir a pagamento por servicos ambientais."
            ),
            "chapter": "Protecao Ambiental",
            "lei": "6476/2021",
        },
        {
            "id": "art40_eis",
            "title": "Art. 40 - Estudo de Impacto de Vizinhanca (EIV)",
            "text": (
                "O Estudo de Impacto de Vizinhanca (EIV) e exigido para empreendimentos com area "
                "construida superior a 4.000 m², polos geradores de trafego, shopping centers, "
                "hipermercados, hospitais, universidades, industrias de medio e grande porte. "
                "O EIV deve analisar: adensamento, equipamentos publicos, infraestrutura, "
                "paisagem urbana e patrimonio cultural."
            ),
            "chapter": "Instrumentos de Politica Urbana",
            "lei": "6476/2021",
        },
        {
            "id": "art45_outorga",
            "title": "Art. 45 - Outorga Onerosa do Direito de Construir",
            "text": (
                "A Outorga Onerosa permite a construcao acima do coeficiente de aproveitamento basico "
                "ate o limite do coeficiente maximo, mediante pagamento de contrapartida financeira "
                "ao municipio. Os recursos devem ser aplicados em habitacao de interesse social, "
                "saneamento, mobilidade e areas verdes. Valor da contrapartida: calculado conforme "
                "formula definida em decreto municipal."
            ),
            "chapter": "Instrumentos de Politica Urbana",
            "lei": "6476/2021",
        },
        {
            "id": "art50_aic",
            "title": "Art. 50 - Area de Interesse Cultural (AIC)",
            "text": (
                "As AIC compreendem o conjunto arquitetonico do centro historico e edificacoes de "
                "valor cultural inventariadas. Intervencoes devem ser aprovadas pelo Conselho do "
                "Patrimonio Cultural. Usos comerciais e de servicos sao permitidos desde que "
                "compatíveis com a preservacao da paisagem. Uso industrial e vedado."
            ),
            "chapter": "Patrimonio Cultural",
            "lei": "6476/2021",
        },
        {
            "id": "art55_aiua",
            "title": "Art. 55 - Area de Interesse Urbanistico Ambiental (AIUA)",
            "text": (
                "As AIUA sao areas que demandam intervencao integrada urbanistica e ambiental, "
                "como fundos de vale urbanizados e encostas com riscos controlados. "
                "O municipio deve elaborar Planos de Intervencao especificos. "
                "Novos parcelamentos e condicionados a estudos de estabilidade e drenagem."
            ),
            "chapter": "Areas Especiais",
            "lei": "6476/2021",
        },
        {
            "id": "art60_parcelamento",
            "title": "Art. 60 - Parcelamento do Solo",
            "text": (
                "O parcelamento do solo para fins urbanos obedece a Lei Federal 6.766/1979 e esta lei. "
                "Lote minimo: 125 m². Frente minima: 5 m. Quadras com comprimento maximo de 200 m. "
                "Percentual de areas publicas: minimo 35% do total parcelado, sendo 15% para sistema "
                "viario, 10% para areas verdes e 10% para equipamentos publicos."
            ),
            "chapter": "Parcelamento do Solo",
            "lei": "6476/2021",
        },
        {
            "id": "art70_mobilidade",
            "title": "Art. 70 - Sistema Viario e Mobilidade",
            "text": (
                "O sistema viario municipal e hierarquizado em: vias arteriais, coletoras, locais e "
                "ciclovias. Novos empreendimentos devem garantir acessibilidade universal conforme NBR 9050. "
                "Polos geradores de trafego devem apresentar Relatorio de Impacto no Transito (RIT). "
                "Recuos frontais obrigatorios: arteriais 5 m, coletoras 3 m, locais 2 m."
            ),
            "chapter": "Mobilidade Urbana",
            "lei": "6476/2021",
        },
    ]


def build_index(corpus_path: Path | None = None, persist_dir: str = "data/rag_index") -> int:
    """Index the plan director corpus into ChromaDB. Returns number of documents indexed."""
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError as exc:
        raise ImportError(
            "Instale chromadb: pip install chromadb"
        ) from exc

    corpus = _load_corpus(corpus_path)

    client = chromadb.PersistentClient(path=persist_dir)

    # Delete and recreate collection for a clean rebuild
    try:
        client.delete_collection(_COLLECTION_NAME)
    except Exception:
        pass

    ef = embedding_functions.DefaultEmbeddingFunction()
    collection = client.create_collection(_COLLECTION_NAME, embedding_function=ef)

    documents = [doc["text"] for doc in corpus]
    metadatas = [
        {
            "id": doc["id"],
            "title": doc["title"],
            "chapter": doc["chapter"],
            "lei": doc["lei"],
        }
        for doc in corpus
    ]
    ids = [doc["id"] for doc in corpus]

    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    log.info("Indice RAG criado com %d documentos.", len(corpus))
    return len(corpus)


def query(
    question: str,
    n_results: int = 4,
    persist_dir: str = "data/rag_index",
    model: str = "claude-haiku-4-5-20251001",
) -> RagAnswer:
    """Answer a legal question about the Plano Diretor using RAG + Claude."""
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError as exc:
        raise ImportError("Instale chromadb: pip install chromadb") from exc

    try:
        import anthropic
    except ImportError as exc:
        raise ImportError("Instale anthropic: pip install anthropic") from exc

    client = chromadb.PersistentClient(path=persist_dir)
    ef = embedding_functions.DefaultEmbeddingFunction()

    # Auto-build index if not present
    try:
        collection = client.get_collection(_COLLECTION_NAME, embedding_function=ef)
    except Exception:
        build_index(persist_dir=persist_dir)
        collection = client.get_collection(_COLLECTION_NAME, embedding_function=ef)

    results = collection.query(query_texts=[question], n_results=n_results)
    docs = results["documents"][0]
    metas = results["metadatas"][0]

    context = "\n\n".join(
        f"[{m['title']}]\n{doc}" for doc, m in zip(docs, metas)
    )

    prompt = (
        "Voce e um especialista em direito urbanistico municipal, com foco no Plano Diretor "
        "de Pouso Alegre (Lei 6476/2021). Responda a pergunta abaixo com base exclusivamente "
        "nos artigos fornecidos no contexto. Se a resposta nao estiver no contexto, diga isso "
        "claramente e sugira consultar o texto completo da lei.\n\n"
        f"CONTEXTO:\n{context}\n\n"
        f"PERGUNTA: {question}\n\n"
        "RESPOSTA (em portugues, objetiva e citando artigos quando pertinente):"
    )

    anthro = anthropic.Anthropic()
    message = anthro.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    answer_text = message.content[0].text

    sources = [
        {"title": m["title"], "chapter": m["chapter"], "lei": m["lei"]}
        for m in metas
    ]

    return RagAnswer(
        question=question,
        answer=answer_text,
        sources=sources,
        model=model,
    )
