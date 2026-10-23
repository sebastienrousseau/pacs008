.PHONY: help install dev test lint format type-check security clean docs docker smoke examples audit pip-compile

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

# Same paths CI lints, so a green `make lint` means a green lint job.
LINT_PATHS := pacs008/ tests/ examples/ benches/ scripts/

lint: ## Run linters (ruff + black check)
	$(POETRY) run ruff check $(LINT_PATHS)
	$(POETRY) run black --check $(LINT_PATHS)

format: ## Auto-format code (ruff fix + black)
	$(POETRY) run ruff check --fix $(LINT_PATHS)
	$(POETRY) run black $(LINT_PATHS)

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

REQS := .github/requirements
AUDIT_VENV := .venv-audit

audit: ## pip-audit poetry.lock and every hash-pinned CI requirements file
	python3 -m venv $(AUDIT_VENV)
	$(AUDIT_VENV)/bin/pip install --quiet --require-hashes -r $(REQS)/audit.txt
	$(AUDIT_VENV)/bin/poetry export --all-groups --all-extras \
		-f requirements.txt -o $(AUDIT_VENV)/poetry-lock.txt
	@for f in $(AUDIT_VENV)/poetry-lock.txt $(REQS)/*.txt; do \
		echo "--- $$f"; \
		$(AUDIT_VENV)/bin/pip-audit --progress-spinner off --require-hashes \
			--disable-pip -r "$$f" || exit 1; \
	done

pip-compile: ## Regenerate hash-pinned $(REQS)/*.txt from their .in files (needs uv)
	@command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/"; exit 1; }
	@for f in poetry audit; do \
		echo "compiling $(REQS)/$$f.in"; \
		uv pip compile --quiet --generate-hashes --universal \
			--python-version 3.10 $(REQS)/$$f.in -o $(REQS)/$$f.txt; \
	done
	uv pip compile --quiet --generate-hashes --python-version 3.12 --universal \
		$(REQS)/sbom.in -o $(REQS)/sbom.txt

check: lint type-check security test examples ## Run all checks
