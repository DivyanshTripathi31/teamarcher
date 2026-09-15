.PHONY: help setup infra build archer backend frontend start stop test

SHELL := /bin/bash
ROOT_DIR := $(CURDIR)
PYTHON := $(ROOT_DIR)/backend/.venv/bin/python
CARGO := cargo

help:
	@echo "make setup    Install backend and frontend dependencies"
	@echo "make infra    Start PostgreSQL and MinIO"
	@echo "make build    Build Archer and the frontend"
	@echo "make archer   Build the Archer Rust analyzer"
	@echo "make backend  Start the FastAPI backend"
	@echo "make frontend Start the Vite frontend"
	@echo "make start    Start infrastructure, Archer, backend, and frontend"
	@echo "make stop     Stop Docker infrastructure"
	@echo "make test     Run backend and Archer tests"

setup:
	@test -x "$(PYTHON)" || (cd backend && python3 -m venv .venv)
	cd backend && .venv/bin/python -m pip install -r requirements.txt
	@cd frontend && npm install

infra:
	docker compose up -d

archer:
	cd archer-starter && $(CARGO) build

build: archer
	cd frontend && npm run build

backend:
	$(PYTHON) -m uvicorn --app-dir "$(ROOT_DIR)/backend" app.main:app --reload

frontend:
	cd frontend && npm run dev

start: infra archer
	@trap 'kill 0; docker compose stop' INT TERM EXIT; \
		$(PYTHON) -m uvicorn --app-dir "$(ROOT_DIR)/backend" app.main:app --reload & \
		(cd frontend && npm run dev) & \
		wait

stop:
	docker compose stop

test:
	cd archer-starter && $(CARGO) test
	cd backend && $(PYTHON) -m pytest
