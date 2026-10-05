# laya-router developer commands (Makefile launcher over `uv run`).
#
# The canonical gate is `make ci`: lint + format check + typecheck + fast tests.
# `make ci` never touches the network or a model — it uses the injected fake
# engine on purpose, so it stays fast and deterministic.
#
# Running against the **real** Laya model is symmetric across both modes of use
# (the embedded library and the `laya-serve` HTTP service). The model is a
# shared resource: download it once with `make models-pull`, then every target
# that needs it reads the same Hugging Face cache, offline.
#
#   MODEL ?= multilingual   # english | multilingual | typed-decisions

MODEL ?= multilingual
MODELS_DIR := $(HOME)/.cache/huggingface/hub
SERVE_HOST ?= 127.0.0.1
SERVE_PORT ?= 8000
# Development default; override in any real deployment (never commit a secret).
LAYA_API_KEY ?= dev-token
SERVE_LOG ?= /tmp/laya-serve.log
SERVE_PID ?= /tmp/laya-serve.pid

.PHONY: help
help: ## List every command
	@printf '%s\n' 'laya-router commands:' && grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  %-16s %s\n", $$1, $$2}'

# --------------------------------------------------------------------------- #
# Library (development)
# --------------------------------------------------------------------------- #

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
test: ## Fast tests (unit; the engine is faked, no model, no network)
	uv run pytest

.PHONY: test-integration
test-integration: ## Real-Laya tests with MODEL ($(MODEL)); needs `make models-pull`
	@$(MAKE) --no-print-directory models-check MODEL=$(MODEL)
	LAYA_ROUTER_MODEL=$(MODEL) uv run pytest -m integration

.PHONY: ci
ci: lint format-check typecheck test ## CI gate: lint + format + typecheck + fast tests (no model)

# --------------------------------------------------------------------------- #
# Models (shared by the library and the service)
# --------------------------------------------------------------------------- #

.PHONY: models-pull
models-pull: ## Download MODEL ($(MODEL)) into the Hugging Face cache
	@$(MAKE) --no-print-directory _models-fetch MODEL=$(MODEL)

.PHONY: _models-fetch
_models-fetch: ## (internal) fetch the MODEL subfolder with huggingface_hub
	@echo "pulling Laya checkpoint: $(MODEL)"
	uv run --with "laya[serve]" python -c "\
from huggingface_hub import snapshot_download; \
m='$(MODEL)'; \
sub=None if m=='english' else m; \
p=snapshot_download('convaiinnovations/laya', allow_patterns=(None if sub is None else [sub+'/*', sub])); \
print('downloaded:', p)"

.PHONY: models-list
models-list: ## List Laya checkpoints present in the Hugging Face cache
	@echo "cache: $(MODELS_DIR)"
	@find "$(MODELS_DIR)"/models--convaiinnovations--laya*/snapshots -mindepth 2 -maxdepth 2 -type d 2>/dev/null \
		| sed 's|.*/||' | sort -u | sed 's/^/  /' || true
	@test -d "$(MODELS_DIR)"/models--convaiinnovations--laya* || echo "  (none — run: make models-pull MODEL=$(MODEL))"

.PHONY: models-path
models-path: ## Print the Hugging Face cache directory for Laya
	@ls -d "$(MODELS_DIR)"/models--convaiinnovations--laya* 2>/dev/null || echo "(not downloaded)"

.PHONY: models-rm
models-rm: ## Remove the Laya checkpoints from the cache (frees disk)
	rm -rf "$(MODELS_DIR)"/models--convaiinnovations--laya*
	@echo "removed Laya checkpoints from the cache"

# --------------------------------------------------------------------------- #
# Service (laya-serve, the third-party HTTP server shipped by Laya)
# --------------------------------------------------------------------------- #

.PHONY: models-check
models-check: ## (internal) fail with a clear hint when MODEL is not cached
	@if [ "$(MODEL)" = "english" ]; then \
		need="encoder"; \
	else \
		need="$(MODEL)"; \
	fi; \
	found=""; \
	for path in "$(MODELS_DIR)"/models--convaiinnovations--laya*/snapshots/*/"$$need"; do \
		[ -d "$$path" ] && found="$$path" && break; \
	done; \
	if [ -z "$$found" ]; then \
		echo "model '$(MODEL)' is not downloaded."; \
		echo "run: make models-pull MODEL=$(MODEL)"; \
		exit 1; \
	fi

.PHONY: serve-up
serve-up: ## Start laya-serve (MODEL=$(MODEL)) in the background, token = LAYA_API_KEY
	@$(MAKE) --no-print-directory models-check MODEL=$(MODEL)
	@if [ -f "$(SERVE_PID)" ] && kill -0 "$$(cat $(SERVE_PID))" 2>/dev/null; then \
		echo "laya-serve already running (pid $$(cat $(SERVE_PID)))"; exit 0; fi
	@LAYA_MODELS=$(MODEL) LAYA_DEVICE=cpu LAYA_PRELOAD=1 LAYA_API_KEY=$(LAYA_API_KEY) \
		LAYA_HOST=$(SERVE_HOST) LAYA_PORT=$(SERVE_PORT) \
		HF_HUB_DISABLE_XET=1 \
		nohup uv run --with "laya[serve]" laya-serve > $(SERVE_LOG) 2>&1 & echo $$! > $(SERVE_PID)
	@echo "laya-serve starting on http://$(SERVE_HOST):$(SERVE_PORT) (log: $(SERVE_LOG))"
	@$(MAKE) --no-print-directory serve-wait

.PHONY: serve-wait
serve-wait: ## Wait until the service answers (with the token)
	@for i in $$(seq 1 60); do \
		if curl -sf -o /dev/null -H "Authorization: Bearer $(LAYA_API_KEY)" http://$(SERVE_HOST):$(SERVE_PORT)/health; then \
			echo "laya-serve is up"; exit 0; fi; \
		sleep 2; \
	done; \
	echo "laya-serve did not come up; see $(SERVE_LOG)"; tail -20 $(SERVE_LOG); exit 1

.PHONY: serve-down
serve-down: ## Stop laya-serve
	@if [ -f "$(SERVE_PID)" ]; then \
		pid=$$(cat $(SERVE_PID)); \
		pkill -TERM -P "$$pid" 2>/dev/null || true; \
		kill "$$pid" 2>/dev/null || true; \
		rm -f "$(SERVE_PID)"; echo "laya-serve stopped"; \
	else echo "no pid file ($(SERVE_PID))"; fi

.PHONY: serve-logs
serve-logs: ## Follow the laya-serve log
	tail -f $(SERVE_LOG)

.PHONY: serve-smoke
serve-smoke: ## Check the service contract: 401 without token, 200 with token, one choice
	@echo "== unauthenticated /v1/systemone expects 401 =="
	@code=$$(curl -s -o /dev/null -w '%{http_code}' -X POST http://$(SERVE_HOST):$(SERVE_PORT)/v1/systemone \
		-H 'Content-Type: application/json' \
		-d '{"state":{"document":"x"},"questions":{"q":{"type":"choice","instructions":"pick","criteria":{"a":"x","b":"y"}}}}'); \
		test "$$code" = "401" && echo "  ok: 401" || { echo "  FAIL: got $$code"; exit 1; }
	@echo "== authenticated choice returns a label =="
	@curl -s -X POST http://$(SERVE_HOST):$(SERVE_PORT)/v1/systemone \
		-H 'Content-Type: application/json' -H "Authorization: Bearer $(LAYA_API_KEY)" \
		-d '{"state":{"document":"Tengo que comprar leche y llamar al fontanero, y terminar el informe."},"questions":{"pipeline":{"type":"choice","instructions":"Which processing fits this note best?","criteria":{"to_do":"a list of tasks to do","reminder":"an event with a date or time","idea":"an idea or reflection"}}}}' \
		| uv run python -c "import sys,json;d=json.load(sys.stdin)['answers']['pipeline'];print('  ok: choice=%s confidence=%.3f' % (d['choice'], d['answer_confidence']))"

# --------------------------------------------------------------------------- #
# Library CLI against the real model
# --------------------------------------------------------------------------- #

.PHONY: classify
classify: ## Real classification: make classify LABELS=file.yaml TEXT="..."
	@test -n "$(LABELS)" || { echo "usage: make classify LABELS=labels.yaml TEXT=\"...\""; exit 1; }
	@test -n "$(TEXT)" || { echo "usage: make classify LABELS=labels.yaml TEXT=\"...\""; exit 1; }
	@$(MAKE) --no-print-directory models-check MODEL=$(MODEL)
	HF_HUB_DISABLE_XET=1 uv run python -c "from laya_router.categories import load_labels; from laya_router.classifier import Classifier; import json; r=Classifier(load_labels('$(LABELS)')).classify('''$(TEXT)'''); print(json.dumps({'label':r.label,'confidence':r.confidence,'below_threshold':r.below_threshold,'scores':r.scores}, ensure_ascii=False, indent=2))"

.PHONY: bench-http
bench-http: ## Per-call latency + accuracy of the running service: make bench-http LABELS=… DATASET=…
	@test -n "$(LABELS)" || { echo "usage: make bench-http LABELS=labels.yaml DATASET=eval.jsonl"; exit 1; }
	@test -n "$(DATASET)" || { echo "usage: make bench-http LABELS=labels.yaml DATASET=eval.jsonl"; exit 1; }
	uv run --with httpx python scripts/bench_http.py \
		--base-url http://$(SERVE_HOST):$(SERVE_PORT) --token $(LAYA_API_KEY) \
		--labels $(LABELS) --dataset $(DATASET)
