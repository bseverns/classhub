SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help smoke-golden smoke-a11y smoke-full

SMOKE_COMPOSE_MODE ?= prod
SMOKE_BASE_URL ?=
SMOKE_TIMEOUT_SECONDS ?= 20
SMOKE_INSECURE_TLS ?= 0
SMOKE_HELPER_MESSAGE ?= Help me with AP calculus limits.
SMOKE_INSTALL_BROWSERS ?= 1
SMOKE_FAIL_IMPACT ?= critical
SMOKE_A11Y_TIMEOUT_MS ?= 30000

INSECURE_TLS_FLAG :=
ifeq ($(SMOKE_INSECURE_TLS),1)
INSECURE_TLS_FLAG := --insecure-tls
endif

INSTALL_BROWSERS_FLAG :=
ifeq ($(SMOKE_INSTALL_BROWSERS),1)
INSTALL_BROWSERS_FLAG := --install-browsers
endif

BASE_URL_FLAG :=
ifneq ($(strip $(SMOKE_BASE_URL)),)
BASE_URL_FLAG := --base-url "$(SMOKE_BASE_URL)"
endif

help:
	@echo "ClassHub operator shortcuts:"
	@echo "  make smoke-full"
	@echo "  make smoke-golden"
	@echo "  make smoke-a11y"
	@echo ""
	@echo "Optional overrides:"
	@echo "  SMOKE_COMPOSE_MODE=prod|dev"
	@echo "  SMOKE_BASE_URL=http://localhost"
	@echo "  SMOKE_TIMEOUT_SECONDS=20"
	@echo "  SMOKE_INSECURE_TLS=0|1"
	@echo "  SMOKE_INSTALL_BROWSERS=0|1"
	@echo "  SMOKE_FAIL_IMPACT=minor|moderate|serious|critical"

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

smoke-full: smoke-golden smoke-a11y
	@echo "[smoke-full] PASS"
