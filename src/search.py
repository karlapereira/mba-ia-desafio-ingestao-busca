from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector

from settings import get_settings

PROMPT_TEMPLATE = """
CONTEXTO:
{contexto}

REGRAS:
- Responda somente com base no CONTEXTO.
- Se a informação não estiver explicitamente no CONTEXTO, responda:
  "Não tenho informações necessárias para responder sua pergunta."
- Nunca invente ou use conhecimento externo.
- Nunca produza opiniões ou interpretações além do que está escrito.

EXEMPLOS DE PERGUNTAS FORA DO CONTEXTO:
Pergunta: "Qual é a capital da França?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Quantos clientes temos em 2024?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Você acha isso bom ou ruim?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

PERGUNTA DO USUÁRIO:
{pergunta}

RESPONDA A "PERGUNTA DO USUÁRIO"
"""

def search_prompt(question=None):
    try:
        settings = get_settings()
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
        llm = ChatGoogleGenerativeAI(
            model=settings.google_llm_model,
            google_api_key=settings.google_api_key,
            temperature=0,
        )
    except Exception as e:
        print(f"Erro de inicialização: {e}")
        return None

    chain = PromptTemplate.from_template(PROMPT_TEMPLATE) | llm

    def answer(q):
        results = store.similarity_search_with_score(q, k=10)
        contexto = "\n\n".join(doc.page_content for doc, _ in results)
        resp = chain.invoke({"contexto": contexto, "pergunta": q})
        return resp.content.strip() if isinstance(resp.content, str) else str(resp.text()).strip()

    return answer(question) if question else answer
