import hashlib
import json
import sys
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from recomendacao_imobiliaria import rag_juridico as rag
from recomendacao_imobiliaria.config import Settings


@pytest.fixture
def corpus_file(tmp_path):
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps([{"id": "art1", "title": "Art. 1", "text": "Texto de teste",
                                  "chapter": "Capitulo I", "lei": "teste"}]), encoding="utf-8")
    manifest = {"municipality_code": "3152501", "source_uri": "https://pousoalegre.mg.gov.br/lei.pdf",
                "approved_by": "revisor de teste", "approved_at": "2026-10-10", "rule_version": "test-v1",
                "checksum_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    path.with_name(path.name + ".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_missing_corpus_does_not_use_embedded_articles(tmp_path):
    with pytest.raises(rag.LegalSourceUnavailable):
        rag._load_corpus(tmp_path / "missing.json")


def test_external_corpus_requires_manifest(tmp_path):
    path = tmp_path / "corpus.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(rag.LegalSourceUnavailable):
        rag._load_corpus(path)


def test_approved_checksum_loads_corpus(corpus_file):
    assert rag._load_corpus(corpus_file)[0]["id"] == "art1"


def test_tampered_corpus_is_rejected(corpus_file):
    corpus_file.write_text("[]", encoding="utf-8")
    with pytest.raises(rag.LegalSourceUnavailable, match="checksum"):
        rag._load_corpus(corpus_file)


@pytest.mark.parametrize("change", [{"municipality_code": "3151800"}, {"approved_by": ""},
                                  {"source_uri": "https://example.com/law"}])
def test_unverified_manifest_is_rejected(corpus_file, change):
    path = corpus_file.with_name(corpus_file.name + ".manifest.json")
    manifest = json.loads(path.read_text())
    manifest.update(change)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(rag.LegalSourceUnavailable):
        rag._load_corpus(corpus_file)


def test_demo_is_explicit_and_not_allowed_in_production(monkeypatch):
    monkeypatch.setattr(rag, "load_settings", lambda: Settings())
    assert rag._load_corpus(demo=True)
    monkeypatch.setattr(rag, "load_settings", lambda: replace(Settings(), app_env="production"))
    with pytest.raises(rag.LegalSourceUnavailable, match="producao"):
        rag._load_corpus(demo=True)


def test_cached_index_cannot_bypass_missing_corpus(tmp_path):
    # A validacao ocorre antes de abrir Chroma ou chamar o modelo.
    with pytest.raises(rag.LegalSourceUnavailable):
        rag.query("Pode construir?", persist_dir=str(tmp_path / "old-index"),
                  corpus_path=tmp_path / "missing.json")


def fake_rag_modules(monkeypatch, collection):
    client = SimpleNamespace(get_collection=lambda *a, **k: collection)
    monkeypatch.setitem(sys.modules, "chromadb", SimpleNamespace(PersistentClient=lambda **k: client))
    monkeypatch.setitem(sys.modules, "chromadb.utils", SimpleNamespace(
        embedding_functions=SimpleNamespace(DefaultEmbeddingFunction=lambda: None)))
    model = MagicMock()
    model.messages.create.return_value.content = [SimpleNamespace(text="Resposta de teste")]
    factory = MagicMock(return_value=model)
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=factory))
    return factory


def test_query_returns_verified_source_references(corpus_file, monkeypatch):
    corpus, context = rag._corpus_context(corpus_file)
    collection = SimpleNamespace(metadata=context, query=lambda **k: {
        "documents": [[corpus[0]["text"]]], "metadatas": [[corpus[0]]]})
    fake_rag_modules(monkeypatch, collection)
    answer = rag.query("Pergunta", corpus_path=corpus_file)
    assert answer.answer == "Resposta de teste"
    assert answer.sources[0]["source_uri"] == context["source_uri"]
    assert answer.source_kind == "validated_corpus" and answer.warning is None


def test_query_rejects_index_text_that_differs_from_approved_corpus(corpus_file, monkeypatch):
    corpus, context = rag._corpus_context(corpus_file)
    collection = SimpleNamespace(metadata=context, query=lambda **k: {
        "documents": [["Texto adulterado"]], "metadatas": [[corpus[0]]]})
    factory = fake_rag_modules(monkeypatch, collection)
    with pytest.raises(rag.LegalSourceUnavailable, match="diverge"):
        rag.query("Pergunta", corpus_path=corpus_file)
    factory.assert_not_called()


def test_query_rebuilds_legacy_index_before_use(corpus_file, monkeypatch):
    corpus, context = rag._corpus_context(corpus_file)
    collection = SimpleNamespace(metadata={"source_kind": "demo"}, query=lambda **k: {
        "documents": [[corpus[0]["text"]]], "metadatas": [[corpus[0]]]})
    fake_rag_modules(monkeypatch, collection)
    rebuild = MagicMock(side_effect=lambda **k: setattr(collection, "metadata", context))
    monkeypatch.setattr(rag, "build_index", rebuild)
    assert rag.query("Pergunta", corpus_path=corpus_file).source_kind == "validated_corpus"
    rebuild.assert_called_once()
