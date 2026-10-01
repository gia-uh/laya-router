# laya-router developer commands (Makefile launcher over `uv run`).
# The canonical gate is `make ci`: lint + format check + typecheck + tests.

.PHONY: help
help: ## List every command
	@printf '%s\n' 'laya-router commands:' && grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  %-14s %s\n", $$1, $$2}'

.PHONY: sync
sync: ## Install dependencies from the lockfile (uv sync)
	uv sync

.PHONY: lint
lint: ## Lint: ruff check
	uv run ruff check .

.PHONY: format
format: ## Format: apply ruff format
	uv run ruff format .

.PHONY: format-check
format-check: ## Format gate: ruff format --check
	uv run ruff format --check .

.PHONY: typecheck
typecheck: ## Typecheck: pyright
	uv run pyright

.PHONY: test
test: ## Fast tests (unit; the engine is faked, no model download)
	uv run pytest

.PHONY: test-integration
test-integration: ## Real-Laya test (downloads the checkpoint; slow)
	uv run pytest -m integration

.PHONY: ci
ci: lint format-check typecheck test ## CI gate: lint + format + typecheck + fast tests
