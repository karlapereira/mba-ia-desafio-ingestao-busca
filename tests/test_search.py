from unittest.mock import patch

import pytest
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel

import search

RECUSA = "Não tenho informações necessárias para responder sua pergunta."


@pytest.fixture
def deps():
    """Substitui embeddings, banco e LLM por fakes."""
    docs = [(Document(page_content="trecho A"), 0.1), (Document(page_content="trecho B"), 0.2)]
    with patch.object(search, "GoogleGenerativeAIEmbeddings"), \
            patch.object(search, "PGVector") as pgvector, \
            patch.object(search, "ChatGoogleGenerativeAI") as llm:
        pgvector.return_value.similarity_search_with_score.return_value = docs
        llm.return_value = FakeListChatModel(responses=["  resposta fake  "])
        yield pgvector.return_value, llm


def test_template_contem_regras_e_placeholders():
    t = search.PROMPT_TEMPLATE
    assert "{contexto}" in t and "{pergunta}" in t
    assert "Responda somente com base no CONTEXTO" in t
    assert RECUSA in t
    assert "Qual é a capital da França?" in t


def test_busca_usa_k_10(deps):
    store, _ = deps
    search.search_prompt("qualquer coisa")
    store.similarity_search_with_score.assert_called_once_with("qualquer coisa", k=10)


def test_com_pergunta_retorna_resposta_sem_espacos(deps):
    assert search.search_prompt("oi?") == "resposta fake"


def test_sem_pergunta_retorna_callable(deps):
    answer = search.search_prompt()
    assert callable(answer)
    assert answer("oi?") == "resposta fake"


def test_prompt_enviado_a_llm_contem_contexto_concatenado_e_pergunta(deps):
    _, llm = deps
    enviados = []
    original = llm.return_value

    def captura(prompt, *a, **k):
        enviados.append(prompt.to_string())
        return original.invoke(prompt)

    from langchain_core.runnables import RunnableLambda
    llm.return_value = RunnableLambda(captura)

    search.search_prompt("Qual o faturamento?")
    assert "trecho A\n\ntrecho B" in enviados[0]
    assert "Qual o faturamento?" in enviados[0]


def test_llm_usa_temperatura_zero(deps):
    _, llm = deps
    search.search_prompt()
    assert llm.call_args.kwargs["temperature"] == 0


def test_falha_na_inicializacao_retorna_none(capsys):
    with patch.object(search, "GoogleGenerativeAIEmbeddings"), \
            patch.object(search, "PGVector", side_effect=RuntimeError("banco fora")):
        assert search.search_prompt() is None
    assert "banco fora" in capsys.readouterr().out
