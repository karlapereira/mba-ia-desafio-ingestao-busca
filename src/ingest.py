import sys
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import ValidationError

from settings import ROOT_DIR, get_settings

BATCH_SIZE = 50


def ingest_pdf():
    try:
        settings = get_settings()
    except ValidationError as e:
        sys.exit(f"Configuração inválida (verifique o .env):\n{e}")

    pdf = Path(settings.pdf_path)
    if not pdf.is_absolute() and not pdf.exists():
        pdf = ROOT_DIR / settings.pdf_path
    if not pdf.exists():
        sys.exit(f"PDF não encontrado: {settings.pdf_path}")

    docs = PyPDFLoader(str(pdf)).load()
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150, add_start_index=False
    ).split_documents(docs)
    chunks = [c for c in chunks if c.page_content.strip()]
    if not chunks:
        sys.exit("Nenhum texto extraído do PDF.")

    embeddings = GoogleGenerativeAIEmbeddings(
        model=settings.google_embedding_model,
        google_api_key=settings.google_api_key,
    )
    store = PGVector(
        embeddings=embeddings,
        collection_name=settings.pg_vector_collection_name,
        connection=settings.database_url,
        use_jsonb=True,
    )
    # Reexecuções não duplicam dados: recria a collection antes de inserir.
    store.delete_collection()
    store.create_collection()

    ids = [f"{pdf.stem}-{i}" for i in range(len(chunks))]
    for i in range(0, len(chunks), BATCH_SIZE):
        store.add_documents(chunks[i:i + BATCH_SIZE], ids=ids[i:i + BATCH_SIZE])
    print(f"Ingestão concluída: {len(chunks)} chunks de {len(docs)} páginas.")


if __name__ == "__main__":
    ingest_pdf()
