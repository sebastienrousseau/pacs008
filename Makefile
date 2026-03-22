.PHONY: help install dev test lint format type-check security clean docs docker smoke examples

PYTHON ?= python3
POETRY ?= poetry

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(POETRY) install --only main

dev: ## Install all dependencies (including dev)
	$(POETRY) install

test: ## Run tests with coverage
	$(POETRY) run pytest tests/ -v

test-fast: ## Run tests without coverage (faster)
	$(POETRY) run pytest tests/ -v --no-cov

test-parallel: ## Run tests in parallel
	$(POETRY) run pytest tests/ -v -n auto

lint: ## Run linters (ruff + black check)
	$(POETRY) run ruff check pacs008/ tests/
	$(POETRY) run black --check pacs008/ tests/

format: ## Auto-format code (ruff fix + black)
	$(POETRY) run ruff check --fix pacs008/ tests/
	$(POETRY) run black pacs008/ tests/

type-check: ## Run mypy type checking
	$(POETRY) run mypy pacs008/

security: ## Run security scan (bandit)
	$(POETRY) run bandit -r pacs008/ -c pyproject.toml 2>/dev/null || \
		$(POETRY) run bandit -r pacs008/ -ll

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .eggs/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/
	rm -rf coverage.xml .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

docs: ## Build Sphinx documentation
	$(POETRY) run sphinx-build -b html docs/ docs/_build/html

docker: ## Build Docker image
	docker build -t pacs008:latest .

docker-run: ## Run Docker container
	docker run -p 8000:8000 pacs008:latest

smoke: ## Run smoke tests only
	$(POETRY) run pytest tests/ -m smoke -v --no-cov

examples: ## Verify example scripts run
	$(POETRY) run python examples/generate_xml.py
	$(POETRY) run python examples/swift_compliance.py
	@rm -f output_pacs008.xml

check: lint type-check security test examples ## Run all checks
