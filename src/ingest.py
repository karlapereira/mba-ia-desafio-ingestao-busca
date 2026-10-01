import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

PDF_PATH = os.getenv("PDF_PATH", "document.pdf")
BATCH_SIZE = 50


def ingest_pdf():
    pdf = Path(PDF_PATH)
    if not pdf.is_absolute() and not pdf.exists():
        pdf = Path(__file__).resolve().parent.parent / PDF_PATH
    if not pdf.exists():
        sys.exit(f"PDF não encontrado: {PDF_PATH}")

    docs = PyPDFLoader(str(pdf)).load()
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150, add_start_index=False
    ).split_documents(docs)
    chunks = [c for c in chunks if c.page_content.strip()]
    if not chunks:
        sys.exit("Nenhum texto extraído do PDF.")

    embeddings = GoogleGenerativeAIEmbeddings(
        model=os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001")
    )
    store = PGVector(
        embeddings=embeddings,
        collection_name=os.environ["PG_VECTOR_COLLECTION_NAME"],
        connection=os.environ["DATABASE_URL"],
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
