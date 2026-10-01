# Ingestão e Busca Semântica com LangChain e PostgreSQL

Aplicação em Python que implementa um pipeline de **RAG (Retrieval-Augmented Generation)** sobre um documento PDF: o conteúdo é ingerido em um banco vetorial (PostgreSQL + pgVector) e consultado por um chat no terminal, que responde **apenas com base no conteúdo do documento**.

## Sumário

- [Objetivo](#objetivo)
- [Como funciona](#como-funciona)
- [Tecnologias e bibliotecas](#tecnologias-e-bibliotecas)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Pré-requisitos](#pré-requisitos)
- [Como executar](#como-executar)
- [Configuração (variáveis de ambiente)](#configuração-variáveis-de-ambiente)
- [Comandos do Makefile](#comandos-do-makefile)
- [Testes](#testes)
- [Exemplo de uso](#exemplo-de-uso)
- [Decisões de projeto](#decisões-de-projeto)
- [Solução de problemas](#solução-de-problemas)

## Objetivo

- **Ingestão:** ler um arquivo PDF, dividi-lo em trechos (chunks), gerar embeddings e armazená-los no PostgreSQL com a extensão pgVector.
- **Busca:** permitir que o usuário faça perguntas via CLI e receba respostas fundamentadas exclusivamente no conteúdo do PDF. Perguntas fora do contexto devem ser recusadas, sem uso de conhecimento externo.

## Como funciona

```
                 INGESTÃO (src/ingest.py)
PDF ──► PyPDFLoader ──► TextSplitter ──► Embeddings (Gemini) ──► PGVector
                        (1000 / 150)

                 CONSULTA (src/chat.py ► src/search.py)
Pergunta ──► Embedding ──► busca por similaridade (k=10) ──► prompt + contexto ──► LLM (Gemini) ──► Resposta
```

1. **Ingestão** — o PDF é carregado página a página e dividido em chunks de **1000 caracteres com overlap de 150**. Cada chunk é transformado em vetor e gravado na collection configurada. A collection é recriada a cada execução, então reexecutar a ingestão não duplica dados.
2. **Consulta** — a pergunta é vetorizada, os **10 chunks mais similares** (`k=10`) são recuperados e concatenados como `CONTEXTO` em um prompt com regras estritas. A LLM responde somente com base nesse contexto; caso a informação não esteja presente, a resposta é: *"Não tenho informações necessárias para responder sua pergunta."*

## Tecnologias e bibliotecas

| Tecnologia / Lib | Uso | Por quê |
|---|---|---|
| **Python 3** | Linguagem | Padrão do ecossistema de IA e exigido pelo desafio |
| **LangChain** (`langchain`, `langchain-core`) | Orquestração (prompt + LLM) | Abstrai provedores de LLM/embeddings e compõe o fluxo de forma declarativa |
| **langchain-google-genai** | Embeddings e LLM Gemini | Integração oficial com a API do Google Gemini (provedor escolhido) |
| **langchain-community** (`PyPDFLoader`) + **pypdf** | Leitura do PDF | Loader pronto, com metadados de página |
| **langchain-text-splitters** (`RecursiveCharacterTextSplitter`) | Divisão em chunks | Quebra respeitando separadores naturais (parágrafos, frases), preservando coerência semântica |
| **langchain-postgres** (`PGVector`) + **psycopg 3** | Armazenamento e busca vetorial | Integração LangChain ↔ pgVector, com `similarity_search_with_score` |
| **PostgreSQL + pgVector** (imagem `pgvector/pgvector:pg17`) | Banco vetorial | Reaproveita um banco relacional maduro, sem infraestrutura adicional |
| **Docker / Docker Compose** | Execução do banco | Ambiente reproduzível com um único comando |
| **python-dotenv** | Variáveis de ambiente | Mantém segredos (API key) fora do código |
| **Make** | Automação | Simplifica setup e execução (`make run`) |

## Estrutura do projeto

```
├── docker-compose.yml     # PostgreSQL + pgVector
├── Makefile               # Atalhos de setup e execução
├── requirements.txt       # Dependências Python (versões fixadas)
├── requirements-dev.txt   # Dependências de teste (pytest, pytest-cov)
├── pytest.ini
├── .env.example           # Template das variáveis de ambiente
├── document.pdf           # PDF a ser ingerido
└── src/
    ├── ingest.py          # Ingestão: PDF → chunks → embeddings → pgVector
    ├── search.py          # Busca: recuperação + prompt + LLM
    └── chat.py            # CLI interativa
└── tests/                 # Testes unitários (pytest)
    ├── conftest.py
    ├── test_ingest.py
    ├── test_search.py
    └── test_chat.py
```

## Pré-requisitos

- Python 3.10+
- Docker e Docker Compose (daemon em execução)
- Make (opcional, mas recomendado)
- Uma **API Key do Google Gemini** — gere em [Google AI Studio](https://aistudio.google.com/apikey)

## Como executar

### Com Make (recomendado)

```bash
make setup      # cria o venv, instala dependências e gera o .env
# edite o .env e preencha GOOGLE_API_KEY
make run        # sobe o banco, ingere o PDF e abre o chat
```

### Passo a passo manual

```bash
# 1. Ambiente virtual e dependências
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Variáveis de ambiente
cp .env.example .env     # preencha GOOGLE_API_KEY

# 3. Banco de dados
docker compose up -d

# 4. Ingestão do PDF
python src/ingest.py

# 5. Chat
python src/chat.py
```

Para encerrar o chat, digite `sair` (ou use `Ctrl+C`).

## Configuração (variáveis de ambiente)

| Variável | Descrição | Valor sugerido |
|---|---|---|
| `GOOGLE_API_KEY` | Chave da API do Gemini (**obrigatória**) | — |
| `GOOGLE_EMBEDDING_MODEL` | Modelo de embeddings | `models/gemini-embedding-001` |
| `GOOGLE_LLM_MODEL` | Modelo de LLM para as respostas | `gemini-3.5-flash-lite` |
| `DATABASE_URL` | Conexão com o Postgres (driver `psycopg`) | `postgresql+psycopg://postgres:postgres@localhost:5432/rag` |
| `PG_VECTOR_COLLECTION_NAME` | Nome da collection de vetores | `document_chunks` |
| `PDF_PATH` | Caminho do PDF a ingerir | `document.pdf` |

## Comandos do Makefile

| Comando | Descrição |
|---|---|
| `make setup` | Cria o venv, instala dependências e gera o `.env` |
| `make up` / `make down` | Sobe / para o PostgreSQL |
| `make ingest` | Executa a ingestão do PDF |
| `make chat` | Inicia o chat |
| `make run` | `up` + `ingest` + `chat` |
| `make test` / `make test-cov` | Testes unitários / com cobertura |
| `make reset-db` | Remove containers e volume do banco |
| `make psql` / `make logs` | Acesso ao banco / logs |
| `make clean` | Remove o venv e caches |

Use `make help` para ver a lista completa.

## Testes

Os testes unitários usam **pytest** e isolam todas as dependências externas com mocks e fakes: **não precisam de API key, internet nem do banco no ar**.

```bash
make test        # executa os testes
make test-cov    # executa com relatório de cobertura
```

Ou manualmente: `pip install -r requirements-dev.txt && python -m pytest`.

| Arquivo | O que valida |
|---|---|
| `test_ingest.py` | PDF inexistente ou sem texto; chunks de no máximo 1000 caracteres com overlap; collection recriada antes da inserção; IDs únicos e inserção em lotes |
| `test_search.py` | Template com as regras e a mensagem de recusa; `k=10`; contexto concatenado e pergunta no prompt; temperatura 0; falha na inicialização retorna `None` |
| `test_chat.py` | Loop do chat: encerramento com `sair`/`Ctrl+C`/EOF, entradas vazias ignoradas, erro em uma pergunta não derruba a sessão |

> Os testes não avaliam a qualidade das respostas do Gemini; isso exige execução real com a API.

## Exemplo de uso

```
Faça sua pergunta (digite 'sair' para encerrar):

PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: O faturamento foi de 10 milhões de reais.

PERGUNTA: Quantos clientes temos em 2024?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

(Os valores dependem do conteúdo do `document.pdf` ingerido.)

## Decisões de projeto

- **Temperatura 0** na LLM, para respostas determinísticas e aderentes ao contexto.
- **Prompt restritivo** com regras e exemplos de perguntas fora de contexto, reduzindo alucinações.
- **Recriação da collection** na ingestão, garantindo idempotência.
- **Ingestão em lotes** para respeitar limites de requisições da API.
- **Modelos configuráveis por ambiente**, pois nomes e versões de modelos mudam com frequência.
- **Tratamento de erros no chat:** uma falha em uma pergunta (ex.: indisponibilidade da API) não encerra a sessão.

## Solução de problemas

- **`Cannot connect to the Docker daemon`** — inicie o Docker (ou Rancher Desktop). Se o contexto ativo não for o correto, use `make up COMPOSE="docker --context default compose"`.
- **Erro `429` / cota excedida** — o plano gratuito do Gemini possui limites de requisições. Aguarde alguns instantes e execute novamente a ingestão, ou consulte os [limites atuais](https://ai.google.dev/gemini-api/docs/rate-limits).
- **`404 model ... no longer available`** — o modelo foi descontinuado. Ajuste `GOOGLE_LLM_MODEL` / `GOOGLE_EMBEDDING_MODEL` no `.env` para um modelo disponível na sua conta.
- **Erro de dimensão de vetores** — ocorre ao trocar o modelo de embeddings com dados já ingeridos. Rode `make reset-db` (ou apague a collection) e refaça a ingestão.
- **Chat sem respostas relevantes** — confirme que a ingestão foi concluída com sucesso antes de iniciar o chat.
