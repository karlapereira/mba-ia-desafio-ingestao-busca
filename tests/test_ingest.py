from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

import ingest
from settings import Settings


@pytest.fixture
def store():
    with patch.object(ingest, "PGVector") as pgvector, \
            patch.object(ingest, "GoogleGenerativeAIEmbeddings"):
        yield pgvector.return_value


def _settings(pdf_path):
    return Settings(
        google_api_key="k", database_url="postgresql+psycopg://u:p@h/db",
        pg_vector_collection_name="c", pdf_path=pdf_path,
    )


def _run(tmp_path, pages):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF")
    loader = MagicMock()
    loader.load.return_value = [Document(page_content=p) for p in pages]
    with patch.object(ingest, "get_settings", return_value=_settings(str(pdf))), \
            patch.object(ingest, "PyPDFLoader", return_value=loader):
        ingest.ingest_pdf()


def _added_chunks(store):
    return [d for call in store.add_documents.call_args_list for d in call.args[0]]


def test_pdf_inexistente_encerra_com_erro(store):
    with patch.object(ingest, "get_settings", return_value=_settings("/nao/existe.pdf")):
        with pytest.raises(SystemExit):
            ingest.ingest_pdf()
    store.add_documents.assert_not_called()


def test_pdf_sem_texto_encerra_com_erro(tmp_path, store):
    with pytest.raises(SystemExit):
        _run(tmp_path, ["   \n  "])
    store.add_documents.assert_not_called()


def test_chunks_respeitam_tamanho_maximo_de_1000(tmp_path, store):
    _run(tmp_path, ["palavra " * 1000])
    chunks = _added_chunks(store)
    assert len(chunks) > 1
    assert all(len(c.page_content) <= 1000 for c in chunks)


def test_chunks_consecutivos_possuem_overlap(tmp_path, store):
    _run(tmp_path, ["".join(f"w{i:04d} " for i in range(600))])
    chunks = _added_chunks(store)
    sobreposicao = set(chunks[0].page_content.split()) & set(chunks[1].page_content.split())
    assert sobreposicao
    assert len(sobreposicao) * 6 <= 150  # cada palavra tem 6 caracteres


def test_collection_e_recriada_antes_de_inserir(tmp_path, store):
    _run(tmp_path, ["conteúdo curto"])
    nomes = [c[0] for c in store.method_calls]
    assert nomes.index("delete_collection") < nomes.index("create_collection") < nomes.index("add_documents")


def test_ids_sao_unicos_e_inseridos_em_lotes(tmp_path, store):
    _run(tmp_path, ["palavra " * 20000])
    ids = [i for call in store.add_documents.call_args_list for i in call.kwargs["ids"]]
    assert len(ids) == len(set(ids)) == len(_added_chunks(store))
    assert all(len(c.args[0]) <= ingest.BATCH_SIZE for c in store.add_documents.call_args_list)
    assert store.add_documents.call_count > 1


def test_configuracao_invalida_encerra_com_erro():
    with patch.object(ingest, "get_settings", side_effect=ingest.ValidationError.from_exception_data("Settings", [])):
        with pytest.raises(SystemExit):
            ingest.ingest_pdf()
