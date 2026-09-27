.DEFAULT_GOAL := help
SHELL := bash
.SHELLFLAGS := -euo pipefail -c

UV ?= uv
RUN := $(UV) run --locked
PY := PYTHONPATH=scripts $(RUN) python -m wa_assess
# Same image and arguments as the shared report workflow in gamaware/.github, so CI and the committed PDF match.
PANDOC_IMAGE := pandoc/latex:3.11@sha256:cdbf139f607237498b412b3aa051008311d69b88006ab47550efba357af3b277
PANDOC_ARGS := --pdf-engine=xelatex -V geometry:margin=2.2cm --toc

.PHONY: help setup lint test check verify evidence pdf test-live clean

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup: ## Install the pinned Python toolchain into .venv
	$(UV) sync --locked

lint: ## Ruff lint and format check
	$(RUN) ruff check scripts tests
	$(RUN) ruff format --check scripts tests

test: ## Unit tests and report reproduction tests
	$(RUN) pytest

check: ## Fail if evidence/ or the report tables differ from what data/synthetic produces
	$(PY) check

verify: lint test check ## Everything CI runs on the code and data (offline)

evidence: ## Regenerate evidence/ and the generated blocks in report/REPORT.md
	$(PY) generate

pdf: ## Render report/REPORT.pdf from report/REPORT.md (pandoc + LaTeX in Docker)
	docker run --rm --platform linux/amd64 --user "$$(id -u):$$(id -g)" -e HOME=/tmp \
		-v "$(CURDIR):/data" -w /data/report $(PANDOC_IMAGE) REPORT.md $(PANDOC_ARGS) -o REPORT.pdf

test-live: ## Manual only: round-trip the answers through the AWS Well-Architected Tool in the dev account
	scripts/live/wa-tool-roundtrip.sh

clean: ## Remove caches and live-test output
	rm -rf .pytest_cache .ruff_cache live-output
