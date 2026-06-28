# DVAP Security Platform
# Makefile
#
# Targets:
#   up            — build and start the full stack (docker compose up -d)
#   down          — stop and remove containers
#   reset         — full teardown + rebuild (removes volumes/images)
#   sample-iac    — submit IaC external-checks sample, show result
#   sample-sca    — submit SCA setup-exec sample, show result
#   sample-secrets — submit secrets symlink sample, show result
#   test          — run unit tests for all Python services + frontend
#   e2e           — run e2e suite against the running stack
#   lint          — ruff + black check + eslint across all services
#   typecheck     — mypy (Python services) + tsc --noEmit (frontend)
#   canarytokens  — generate local Canarytokens.org AWS seed overlay

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_URL     ?= http://127.0.0.1:8000
COMPOSE     := docker compose
DC_FILES    := -f docker-compose.yml
DC_TEST     := -f docker-compose.yml -f docker-compose.test.yml
PYTHON      ?= python3

PYTHON_SERVICES := api worker listener
FRONTEND_DIR    := frontend

.PHONY: up down reset sample-iac sample-sca sample-secrets \
        test e2e lint typecheck canarytokens _wait-api

# ---------------------------------------------------------------------------
# Stack lifecycle
# ---------------------------------------------------------------------------

up:
	$(COMPOSE) $(DC_FILES) up --build -d
	@echo ""
	@echo "DVAP is up:"
	@echo "  UI       -> http://127.0.0.1:8080"
	@echo "  API      -> http://127.0.0.1:8000"
	@echo "  Listener -> http://127.0.0.1:9000 (debug)"

down:
	$(COMPOSE) $(DC_FILES) down

reset:
	$(COMPOSE) $(DC_FILES) down --volumes --remove-orphans
	docker image rm -f dvap-api dvap-worker dvap-listener dvap-frontend 2>/dev/null || true
	@echo "Stack reset. Run 'make up' to rebuild."

canarytokens:
	$(PYTHON) scripts/create_canarytokens.py

# ---------------------------------------------------------------------------
# Sample targets — zero live typing; each submits a known sample and prints the
# result from the API. (SPEC §13)
# ---------------------------------------------------------------------------

_wait-api:
	@echo "Waiting for API to be healthy..."
	@for i in $$(seq 1 30); do \
		curl -sf $(API_URL)/api/healthz > /dev/null 2>&1 && break; \
		sleep 2; \
	done
	@curl -sf $(API_URL)/api/healthz > /dev/null || (echo "API not healthy" && exit 1)

sample-iac: _wait-api
	@echo "=== IaC Sample: checkov_external_checks ==="
	@echo "Step 1: Submit IaC external-checks sample"
	@curl -sf -X POST $(API_URL)/api/scans \
		-H 'Content-Type: application/json' \
		-d '{"module":"iac","vector":"checkov_external_checks","source_type":"sample"}' \
		| python3 -m json.tool
	@echo ""
	@echo "Step 2: Recent callback events"
	@sleep 3
	@curl -sf "$(API_URL)/api/beacons" | python3 -m json.tool

sample-sca: _wait-api
	@echo "=== SCA Sample: setup_py_exec ==="
	@echo "Step 1: Submit SCA setup-exec sample"
	@curl -sf -X POST $(API_URL)/api/scans \
		-H 'Content-Type: application/json' \
		-d '{"module":"sca","vector":"setup_py_exec","source_type":"sample"}' \
		| python3 -m json.tool
	@echo ""
	@echo "Step 2: Recent callback events"
	@sleep 3
	@curl -sf "$(API_URL)/api/beacons" | python3 -m json.tool

sample-secrets: _wait-api
	@echo "=== Secrets Sample: symlink_traversal ==="
	@echo "Step 1: Submit secrets symlink sample"
	@curl -sf -X POST $(API_URL)/api/scans \
		-H 'Content-Type: application/json' \
		-d '{"module":"secrets","vector":"symlink_traversal","source_type":"sample"}' \
		| python3 -m json.tool
	@echo ""
	@echo "Step 2: Recent callback events"
	@sleep 3
	@curl -sf "$(API_URL)/api/beacons" | python3 -m json.tool

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

test:
	@echo "=== Running Python unit tests ==="
	@set -e; for svc in $(PYTHON_SERVICES); do \
		if [ -d "$$svc" ]; then \
			echo "--- pytest: $$svc ---"; \
			(cd $$svc && $(PYTHON) -m pytest -v --tb=short); \
		fi; \
	done
	@echo ""
	@echo "=== Running frontend unit tests ==="
	@if [ -d "$(FRONTEND_DIR)" ]; then \
		cd $(FRONTEND_DIR) && npm run test -- --run; \
	fi

e2e:
	$(COMPOSE) $(DC_TEST) down --volumes --remove-orphans
	$(COMPOSE) $(DC_TEST) up --build --abort-on-container-exit --exit-code-from e2e
	$(COMPOSE) $(DC_TEST) down --volumes --remove-orphans

# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------

lint:
	@echo "=== Lint: Python services (ruff + black check) ==="
	@set -e; for svc in $(PYTHON_SERVICES); do \
		if [ -d "$$svc" ]; then \
			echo "--- ruff: $$svc ---"; \
			(cd $$svc && $(PYTHON) -m ruff check . && $(PYTHON) -m black --check .); \
		fi; \
	done
	@echo ""
	@echo "=== Lint: frontend (eslint + prettier) ==="
	@if [ -d "$(FRONTEND_DIR)" ]; then \
		cd $(FRONTEND_DIR) && npm run lint && npm run format:check; \
	fi

# ---------------------------------------------------------------------------
# Type checking
# ---------------------------------------------------------------------------

typecheck:
	@echo "=== Type check: Python services (mypy strict) ==="
	@set -e; for svc in $(PYTHON_SERVICES); do \
		if [ -d "$$svc" ]; then \
			echo "--- mypy: $$svc ---"; \
			(cd $$svc && $(PYTHON) -m mypy .); \
		fi; \
	done
	@echo ""
	@echo "=== Type check: frontend (tsc --noEmit) ==="
	@if [ -d "$(FRONTEND_DIR)" ]; then \
		cd $(FRONTEND_DIR) && npm run typecheck; \
	fi
