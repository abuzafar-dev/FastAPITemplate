.PHONY: help install run test 

help:
	@echo "make run      — serverni ishga tushirish (http://127.0.0.1:8000/docs)"
	@echo "make test     — testlar"
	@echo "make install  — .venv va kutubxonalar"

run: install .env
	@echo "==> Swagger: http://127.0.0.1:8000/docs"
	.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

PY := .venv/bin/python

.venv/bin/python:
	@if command -v uv >/dev/null 2>&1; then uv venv -q --python 3.12 .venv; else python3 -m venv .venv; fi

.venv/.installed: requirements.txt | .venv/bin/python
	@echo "==> kutubxonalar o'rnatilmoqda"
	@if command -v uv >/dev/null 2>&1; then uv pip install -q -p $(PY) -r requirements.txt; else $(PY) -m pip install -q -r requirements.txt; fi
	@touch $@

install: .venv/.installed

.env:
	@cp .env.example .env
	@sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')|" .env
	@echo "==> .env yaratildi (.env.example asosida)"

test: install
	@bash scripts/ci.sh
