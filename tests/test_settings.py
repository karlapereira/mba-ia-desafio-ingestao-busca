import pytest
from pydantic import ValidationError

from settings import Settings

OBRIGATORIAS = {
    "google_api_key": "segredo",
    "database_url": "postgresql+psycopg://u:p@h/db",
    "pg_vector_collection_name": "colecao",
}


def _settings(monkeypatch, **kw):
    for var in ("GOOGLE_API_KEY", "DATABASE_URL", "PG_VECTOR_COLLECTION_NAME",
                "GOOGLE_EMBEDDING_MODEL", "GOOGLE_LLM_MODEL", "PDF_PATH"):
        monkeypatch.delenv(var, raising=False)
    return Settings(_env_file=None, **kw)


def test_valores_padrao(monkeypatch):
    s = _settings(monkeypatch, **OBRIGATORIAS)
    assert s.google_embedding_model == "models/gemini-embedding-001"
    assert s.google_llm_model == "gemini-3.5-flash-lite"
    assert s.pdf_path == "document.pdf"


def test_le_variaveis_de_ambiente(monkeypatch):
    for var in ("GOOGLE_API_KEY", "DATABASE_URL", "PG_VECTOR_COLLECTION_NAME"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "abc")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://x")
    monkeypatch.setenv("PG_VECTOR_COLLECTION_NAME", "col")
    monkeypatch.setenv("GOOGLE_LLM_MODEL", "outro-modelo")
    s = Settings(_env_file=None)
    assert s.google_api_key.get_secret_value() == "abc"
    assert s.pg_vector_collection_name == "col"
    assert s.google_llm_model == "outro-modelo"


@pytest.mark.parametrize("faltando", list(OBRIGATORIAS))
def test_variavel_obrigatoria_ausente_falha(monkeypatch, faltando):
    kw = {k: v for k, v in OBRIGATORIAS.items() if k != faltando}
    with pytest.raises(ValidationError):
        _settings(monkeypatch, **kw)


def test_api_key_nao_aparece_no_repr(monkeypatch):
    assert "segredo" not in repr(_settings(monkeypatch, **OBRIGATORIAS))
