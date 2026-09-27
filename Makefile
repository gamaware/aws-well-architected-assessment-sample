.DEFAULT_GOAL := help
SHELL := bash
.SHELLFLAGS := -euo pipefail -c

UV ?= uv
RUN := $(UV) run --locked
PY := PYTHONPATH=scripts $(RUN) python -m wa_assess
# Homebrew keeps Pango outside the default macOS library path; WeasyPrint needs it for the PDF.
PDF_ENV := DYLD_FALLBACK_LIBRARY_PATH=$${DYLD_FALLBACK_LIBRARY_PATH:-/opt/homebrew/lib}

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

pdf: ## Render report/REPORT.pdf from report/REPORT.md (pandoc + WeasyPrint)
	$(PDF_ENV) $(UV) run --locked --group report pandoc report/REPORT.md \
		--from gfm --standalone --embed-resources --resource-path=report \
		--metadata pagetitle="Harbor Goods Well-Architected and DevOps assessment" \
		--css report/report.css --pdf-engine=weasyprint --output report/REPORT.pdf

test-live: ## Manual only: round-trip the answers through the AWS Well-Architected Tool in the dev account
	scripts/live/wa-tool-roundtrip.sh

clean: ## Remove caches and live-test output
	rm -rf .pytest_cache .ruff_cache live-output
