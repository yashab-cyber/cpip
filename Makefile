.PHONY: help install dev server test lint format clean docker-up docker-down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install cpip client
	pip install -e .

dev: ## Install with all dev dependencies
	pip install -e ".[server,builder,agent,dev]"

server: ## Start the API server
	uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	pytest tests/ -v --tb=short

lint: ## Run linter
	ruff check .

format: ## Format code
	ruff format .

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

docker-up: ## Start full stack via Docker Compose
	docker compose up -d

docker-down: ## Stop Docker Compose stack
	docker compose down

docker-build: ## Build Docker images
	docker compose build

db-migrate: ## Run database migrations
	alembic upgrade head

db-revision: ## Create new migration
	alembic revision --autogenerate -m "$(msg)"
