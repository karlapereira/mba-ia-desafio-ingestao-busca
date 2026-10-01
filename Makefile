VENV    ?= venv
PYTHON  := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
# Sobrescreva se necessário, ex.: make up COMPOSE="docker --context default compose"
COMPOSE ?= docker compose

.DEFAULT_GOAL := help
.PHONY: help setup venv env up down reset-db ingest chat run test test-cov logs psql clean dev-deps

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: venv env ## Cria o venv, instala dependências e gera o .env

STAMP := $(VENV)/.installed

venv: $(STAMP)
$(STAMP): requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -q --upgrade pip
	$(PIP) install -r requirements.txt
	@touch $(STAMP)

env: ## Cria o .env a partir do .env.example (se não existir)
	@test -f .env || (cp .env.example .env && echo ".env criado: preencha GOOGLE_API_KEY")

up: ## Sobe o PostgreSQL + pgVector
	$(COMPOSE) up -d

down: ## Para os containers (mantém os dados)
	$(COMPOSE) down

reset-db: ## Apaga containers e volume do banco (refaça a ingestão depois)
	$(COMPOSE) down -v

ingest: venv ## Executa a ingestão do PDF
	$(PYTHON) src/ingest.py

chat: venv ## Inicia o chat no terminal
	$(PYTHON) src/chat.py

run: up ingest chat ## Sobe o banco, ingere o PDF e abre o chat

test: dev-deps ## Executa os testes unitários (sem API nem banco reais)
	$(PYTHON) -m pytest -v

test-cov: dev-deps ## Testes com relatório de cobertura
	$(PYTHON) -m pytest --cov=src --cov-report=term-missing

dev-deps: venv
	@$(PYTHON) -c "import pytest, pytest_cov" 2>/dev/null || $(PIP) install -q -r requirements-dev.txt

logs: ## Logs do banco
	$(COMPOSE) logs -f postgres

psql: ## Abre um psql no banco
	$(COMPOSE) exec postgres psql -U postgres -d rag

clean: ## Remove o venv e caches Python
	rm -rf $(VENV)
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
