.PHONY: dev dev-down e2e prod prod-down generate test-api test-worker test-tools test-all lint-api logs shell-api check-openapi help

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start local development environment with hot-reload
	docker compose -f compose.yaml -f compose.dev.yaml --env-file .env up

dev-down: ## Stop local development environment
	docker compose -f compose.yaml -f compose.dev.yaml down

e2e: ## Run end-to-end tests in isolated environment (separate ports)
	docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e up -d --wait
	docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e run --rm --no-deps test-runner; EXIT=$$?; \
	docker compose -f compose.yaml -f compose.e2e.yaml --env-file .env.e2e down -v; \
	exit $$EXIT

prod: ## Start production environment
	docker compose -f compose.yaml -f compose.prod.yaml up -d

prod-down: ## Stop production environment (WARNING: do NOT add -v — it destroys volumes)
	docker compose -f compose.yaml -f compose.prod.yaml down

generate: ## Export OpenAPI spec and regenerate TypeScript client
	PYTHONPATH=api/src python3 api/scripts/export_openapi.py
	cd web && npm run generate

test-api: ## Run api pytest suite (requires dev environment running)
	docker compose -f compose.yaml -f compose.dev.yaml exec api python -m pytest tests/ -p no:cacheprovider

test-worker: ## Run worker pytest suite (requires dev environment running)
	docker compose -f compose.yaml -f compose.dev.yaml exec worker python -m pytest tests/ -p no:cacheprovider

test-tools: ## Run tools pytest suite (requires dev environment running)
	docker compose -f compose.yaml -f compose.dev.yaml exec tools python -m pytest tests/ -p no:cacheprovider

test-web: ## Run web jest suite
	cd web && npx jest

test-all: test-api test-worker test-tools test-web ## Run all pytest suites and web jest suite

lint-api: ## Lint OpenAPI spec with Redocly
	npx @redocly/cli lint openapi.json

logs: ## Tail logs from all dev services
	docker compose -f compose.yaml -f compose.dev.yaml logs -f

shell-api: ## Open bash shell in api container
	docker compose -f compose.yaml -f compose.dev.yaml exec api bash

check-openapi: ## Check if openapi.json is up to date with current FastAPI routes
	bash api/scripts/check_openapi_fresh.sh
