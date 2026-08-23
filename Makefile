.PHONY: install dev test test-verbose lint run run-text run-web test-mic list-devices db-up db-down docker-up docker-down clean

install:
	pip install -r requirements.txt

dev:
	pip install -e ".[dev]"

test:
	python -m pytest

test-verbose:
	python -m pytest -v

lint:
	ruff check .
	ruff format --check .

run:
	python -m core.main

run-text:
	python -m core.main --text

run-web:
	python -m web.server

test-mic:
	python -m core.main --test-mic

list-devices:
	python -m core.main --list-devices

db-up:
	docker compose up -d db redis

db-down:
	docker compose down

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} +
	rm -rf .pytest_cache
