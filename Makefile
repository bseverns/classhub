SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help smoke-golden smoke-a11y smoke-full stability-evidence stability-cycle-closeout ops-readiness

SMOKE_COMPOSE_MODE ?= prod
SMOKE_BASE_URL ?=
SMOKE_TIMEOUT_SECONDS ?= 20
SMOKE_INSECURE_TLS ?= 0
SMOKE_HELPER_MESSAGE ?= Help me with AP calculus limits.
SMOKE_INSTALL_BROWSERS ?= 1
SMOKE_FAIL_IMPACT ?= critical
SMOKE_A11Y_TIMEOUT_MS ?= 30000
STABILITY_RELEASE_DATE ?= $(shell date +%F)
STABILITY_SKIP_DOCKER_CHECKS ?= 0
TELEMETRY_WINDOW_DAYS ?= 7
STABILITY_SKIP_KIOSK ?= 0
OPS_READINESS_PROFILE ?= baseline
OPS_READINESS_ENV_FILE ?= compose/.env
SMOKE_FULL_LOCAL_OLLAMA_MODEL ?= llama3.2:1b

INSECURE_TLS_FLAG :=
ifeq ($(SMOKE_INSECURE_TLS),1)
INSECURE_TLS_FLAG := --insecure-tls
endif

INSTALL_BROWSERS_FLAG :=
ifeq ($(SMOKE_INSTALL_BROWSERS),1)
INSTALL_BROWSERS_FLAG := --install-browsers
endif

SKIP_DOCKER_CHECKS_FLAG :=
ifeq ($(STABILITY_SKIP_DOCKER_CHECKS),1)
SKIP_DOCKER_CHECKS_FLAG := --skip-docker-checks
endif

BASE_URL_FLAG :=
ifneq ($(strip $(SMOKE_BASE_URL)),)
BASE_URL_FLAG := --base-url "$(SMOKE_BASE_URL)"
endif

SKIP_KIOSK_FLAG :=
ifeq ($(STABILITY_SKIP_KIOSK),1)
SKIP_KIOSK_FLAG := --skip-kiosk
endif

help:
	@echo "ClassHub operator shortcuts:"
	@echo "  make smoke-full"
	@echo "  make smoke-golden"
	@echo "  make smoke-a11y"
	@echo "  make stability-evidence"
	@echo "  make stability-cycle-closeout"
	@echo "  make ops-readiness"
	@echo ""
	@echo "Optional overrides:"
	@echo "  SMOKE_COMPOSE_MODE=prod|dev"
	@echo "  SMOKE_BASE_URL=http://localhost"
	@echo "  SMOKE_TIMEOUT_SECONDS=20"
	@echo "  SMOKE_INSECURE_TLS=0|1"
	@echo "  SMOKE_INSTALL_BROWSERS=0|1"
	@echo "  SMOKE_FAIL_IMPACT=minor|moderate|serious|critical"
	@echo "  SMOKE_FULL_LOCAL_OLLAMA_MODEL=llama3.2:1b"
	@echo "  STABILITY_RELEASE_DATE=YYYY-MM-DD"
	@echo "  STABILITY_SKIP_DOCKER_CHECKS=0|1"
	@echo "  STABILITY_SKIP_KIOSK=0|1"
	@echo "  TELEMETRY_WINDOW_DAYS=7"
	@echo "  OPS_READINESS_PROFILE=baseline|release"
	@echo "  OPS_READINESS_ENV_FILE=compose/.env"

smoke-golden:
	bash scripts/system_doctor.sh \
	  --build \
	  --compose-mode "$(SMOKE_COMPOSE_MODE)" \
	  --smoke-mode golden \
	  --timeout-seconds "$(SMOKE_TIMEOUT_SECONDS)" \
	  --helper-message "$(SMOKE_HELPER_MESSAGE)" \
	  $(INSECURE_TLS_FLAG) \
	  $(BASE_URL_FLAG)

smoke-a11y:
	bash scripts/a11y_smoke.sh \
	  --compose-mode "$(SMOKE_COMPOSE_MODE)" \
	  --fail-impact "$(SMOKE_FAIL_IMPACT)" \
	  --timeout-ms "$(SMOKE_A11Y_TIMEOUT_MS)" \
	  $(INSTALL_BROWSERS_FLAG) \
	  $(BASE_URL_FLAG)

smoke-full: export HELPER_LLM_BACKEND=ollama
smoke-full: export OLLAMA_BASE_URL=http://ollama:11434
smoke-full: export OLLAMA_MODEL=$(SMOKE_FULL_LOCAL_OLLAMA_MODEL)
smoke-full: export HELPER_REMOTE_MODE_ACKNOWLEDGED=0
smoke-full: export COMPOSE_LOCAL_OLLAMA_AUTO=1
smoke-full: smoke-golden smoke-a11y
	@echo "[smoke-full] PASS"

stability-evidence:
	bash scripts/stability_release_evidence.sh \
	  --release-date "$(STABILITY_RELEASE_DATE)" \
	  --compose-mode "$(SMOKE_COMPOSE_MODE)" \
	  --timeout-seconds "$(SMOKE_TIMEOUT_SECONDS)" \
	  --helper-message "$(SMOKE_HELPER_MESSAGE)" \
	  --fail-impact "$(SMOKE_FAIL_IMPACT)" \
	  --a11y-timeout-ms "$(SMOKE_A11Y_TIMEOUT_MS)" \
	  $(INSTALL_BROWSERS_FLAG) \
	  $(SKIP_DOCKER_CHECKS_FLAG) \
	  $(BASE_URL_FLAG)

stability-cycle-closeout:
	bash scripts/stability_phase1_closeout.sh \
	  --release-date "$(STABILITY_RELEASE_DATE)" \
	  --compose-mode "$(SMOKE_COMPOSE_MODE)" \
	  --window-days "$(TELEMETRY_WINDOW_DAYS)" \
	  --timeout-seconds "$(SMOKE_TIMEOUT_SECONDS)" \
	  --helper-message "$(SMOKE_HELPER_MESSAGE)" \
	  --fail-impact "$(SMOKE_FAIL_IMPACT)" \
	  --a11y-timeout-ms "$(SMOKE_A11Y_TIMEOUT_MS)" \
	  $(INSTALL_BROWSERS_FLAG) \
	  $(SKIP_KIOSK_FLAG) \
	  $(BASE_URL_FLAG)

ops-readiness:
	bash scripts/ops_readiness_check.sh "$(OPS_READINESS_PROFILE)" "$(OPS_READINESS_ENV_FILE)"
