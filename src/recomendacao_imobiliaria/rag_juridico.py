"""RAG juridico sobre o Plano Diretor usando ChromaDB + Claude API."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
from pathlib import Path
from urllib.parse import urlsplit

from .config import load_settings
from .municipality import MUNICIPALITY

log = logging.getLogger(__name__)

_CORPUS_PATH = Path(__file__).parent.parent.parent / "data" / "plano_diretor_corpus.json"
_COLLECTION_NAME = "plano_diretor_pa"


@dataclasses.dataclass
class RagAnswer:
    question: str
    answer: str
    sources: list[dict]
    model: str
    source_kind: str = "validated_corpus"
    warning: str | None = None


class LegalSourceUnavailable(ValueError):
    """Corpus ausente, sem aprovacao ou diferente da versao verificada."""


def _corpus_context(corpus_path: Path | None = None, *, demo: bool = False) -> tuple[list[dict], dict]:
    if demo:
        if load_settings().app_env in {"production", "prod"}:
            raise LegalSourceUnavailable("Corpus juridico demonstrativo nao permitido em producao.")
        if corpus_path is not None:
            raise LegalSourceUnavailable("--demo usa somente o corpus embutido, sem arquivo externo.")
        corpus = _builtin_corpus()
        raw = json.dumps(corpus, sort_keys=True).encode()
        context = {"source_kind": "demo", "source_uri": "embedded-demo",
                   "corpus_sha256": hashlib.sha256(raw).hexdigest(), "manifest_sha256": "demo"}
    else:
        path = Path(corpus_path or _CORPUS_PATH)
        manifest_path = path.with_name(path.name + ".manifest.json")
        if not path.is_file() or not manifest_path.is_file():
            raise LegalSourceUnavailable("Fonte juridica indisponivel: forneca corpus e manifesto aprovado.")
        try:
            raw = path.read_bytes()
            manifest_raw = manifest_path.read_bytes()
            corpus = json.loads(raw)
            manifest = json.loads(manifest_raw)
            if not isinstance(manifest, dict):
                raise ValueError("manifesto deve ser um objeto")
            MUNICIPALITY.validate_code(manifest.get("municipality_code", ""))
            digest = hashlib.sha256(raw).hexdigest()
            if manifest.get("checksum_sha256") != digest:
                raise ValueError("checksum do corpus diverge do manifesto")
            for field in ("approved_by", "approved_at", "rule_version"):
                if not isinstance(manifest.get(field), str) or not manifest[field].strip():
                    raise ValueError(f"manifesto sem {field}")
            uri = manifest.get("source_uri", "")
            parsed = urlsplit(uri)
            if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".gov.br"):
                raise ValueError("source_uri deve apontar para fonte oficial HTTPS gov.br")
            context = {"source_kind": "validated_corpus", "source_uri": uri,
                       "corpus_sha256": digest, "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest()}
        except (ValueError, TypeError, OSError) as exc:
            raise LegalSourceUnavailable(f"Corpus juridico nao verificado: {exc}") from exc
    if not isinstance(corpus, list) or not corpus:
        raise LegalSourceUnavailable("Corpus juridico vazio ou invalido.")
    ids = set()
    for doc in corpus:
        if not isinstance(doc, dict) or any(
            not isinstance(doc.get(key), str) or not doc[key].strip()
            for key in ("id", "title", "text", "chapter", "lei")
        ):
            raise LegalSourceUnavailable("Artigo sem identificacao, texto ou referencia legal.")
        if doc["id"] in ids:
            raise LegalSourceUnavailable("Identificador de artigo duplicado.")
        ids.add(doc["id"])
    context["municipality_code"] = MUNICIPALITY.ibge_code
    return corpus, context


def _load_corpus(corpus_path: Path | None = None, *, demo: bool = False) -> list[dict]:
    """Carrega corpus verificado; demonstracao exige opt-in explicito."""
    return _corpus_context(corpus_path, demo=demo)[0]


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


def build_index(corpus_path: Path | None = None, persist_dir: str = "data/rag_index", *, demo: bool = False) -> int:
    """Index the plan director corpus into ChromaDB. Returns number of documents indexed."""
    corpus, context = _corpus_context(corpus_path, demo=demo)
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError as exc:
        raise ImportError(
            "Instale chromadb: pip install chromadb"
        ) from exc

    client = chromadb.PersistentClient(path=persist_dir)

    # Delete and recreate collection for a clean rebuild
    try:
        client.delete_collection(_COLLECTION_NAME)
    except Exception:
        pass

    ef = embedding_functions.DefaultEmbeddingFunction()
    collection = client.create_collection(_COLLECTION_NAME, embedding_function=ef, metadata=context)

    documents = [doc["text"] for doc in corpus]
    metadatas = [
        {
            "id": doc["id"],
            "title": doc["title"],
            "chapter": doc["chapter"],
            "lei": doc["lei"],
            "source_uri": context["source_uri"],
            "source_kind": context["source_kind"],
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
    *,
    corpus_path: Path | None = None,
    demo: bool = False,
) -> RagAnswer:
    """Answer a legal question about the Plano Diretor using RAG + Claude."""
    corpus, context = _corpus_context(corpus_path, demo=demo)
    if n_results < 1:
        raise ValueError("n_results deve ser positivo")
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
        collection = None
    # Um indice legado/ demonstrativo nao pode contornar a validacao do corpus.
    if collection is None or any((collection.metadata or {}).get(k) != v for k, v in context.items()):
        build_index(corpus_path=corpus_path, persist_dir=persist_dir, demo=demo)
        collection = client.get_collection(_COLLECTION_NAME, embedding_function=ef)

    results = collection.query(query_texts=[question], n_results=min(n_results, len(corpus)))
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    verified = {doc["id"]: doc for doc in corpus}
    if not docs or len(docs) != len(metas):
        raise LegalSourceUnavailable("Indice sem artigos verificaveis.")
    for doc, meta in zip(docs, metas):
        original = verified.get(meta.get("id"))
        if original is None or original["text"] != doc or any(
            original[key] != meta.get(key) for key in ("title", "chapter", "lei")
        ):
            raise LegalSourceUnavailable("Indice diverge do corpus aprovado; reconstrua o indice.")

    retrieved_context = "\n\n".join(
        f"[{m['title']}]\n{doc}" for doc, m in zip(docs, metas)
    )

    prompt = (
        "Voce e um especialista em direito urbanistico municipal, com foco no Plano Diretor "
        "de Pouso Alegre (Lei 6476/2021). Responda a pergunta abaixo com base exclusivamente "
        "nos artigos fornecidos no contexto. Se a resposta nao estiver no contexto, diga isso "
        "claramente e sugira consultar o texto completo da lei.\n\n"
        f"CONTEXTO:\n{retrieved_context}\n\n"
        f"PERGUNTA: {question}\n\n"
        "RESPOSTA (em portugues, objetiva e citando artigos quando pertinente):"
    )
    warning = "DEMONSTRACAO: corpus embutido nao verificado; nao usar para decisoes reais." if demo else None
    if warning:
        prompt = warning + "\nIdentifique sua resposta como demonstrativa.\n" + prompt

    anthro = anthropic.Anthropic()
    message = anthro.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    answer_text = message.content[0].text

    sources = [
        {"title": m["title"], "chapter": m["chapter"], "lei": m["lei"],
         "source_uri": context["source_uri"], "source_kind": context["source_kind"]}
        for m in metas
    ]

    return RagAnswer(
        question=question,
        answer=answer_text,
        sources=sources,
        model=model,
        source_kind=context["source_kind"],
        warning=warning,
    )
