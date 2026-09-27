# CLAUDE.md

Project instructions for Claude Code in `aws-well-architected-assessment-sample`.

## Overview

A fictional sample deliverable: an AWS Well-Architected and DevOps lens assessment of the invented retailer Harbor
Goods. Answers live as YAML in `data/synthetic/`; `scripts/wa_assess` scores them and writes `evidence/` plus the
generated blocks in `report/REPORT.md` and `README.md`.

## Structure

- `data/synthetic/answers/<pillar>.yaml`: one entry per best practice (status, risk, effort, owner, evidence).
- `data/synthetic/exports/*.csv`: synthetic exports; observations quote them through `{group.name}` placeholders.
- `scripts/wa_assess/`: `model` (load and validate), `metrics`, `scoring`, `backlog`, `render`, `__main__`.
- `scripts/live/`: manual Well-Architected Tool round trip (`make test-live`).
- `tests/reference.py`: an independent implementation of the rules. Keep it free of imports from `wa_assess`.

## Working rules

- Never edit `evidence/`, `report/REPORT.pdf` or text between `BEGIN GENERATED` and `END GENERATED` markers by hand.
  Change the data or the scripts, then run `make evidence` (and `make pdf` when the report changes).
- A rule change in `scripts/` needs the same change in `tests/reference.py`, `docs/methodology.md` and the ADR.
- Best-practice IDs and titles must match the current AWS Well-Architected Framework or DevOps Guidance exactly.
- Only AWS documentation example account IDs (`111122223333`, `444455556666`, `123456789012`) and `example.com`.
- Keep prose free of numbers that the data produces; put them in generated blocks instead.
- Never run anything against AWS except `make test-live`, and only when the maintainer asks.

## Verification

`make verify` must pass before every commit: ruff, pytest, and `python -m wa_assess check`.

## Git workflow

Conventional commits, feature branches, squash merge. Pre-commit hooks: file hygiene, detect-secrets, gitleaks,
markdownlint, actionlint, zizmor, shellcheck, shellharden, ruff, conventional-pre-commit.

## Claude Code hooks

- `PreToolUse` (`.claude/hooks/protect-files.sh`): blocks edits to generated files and exported diagrams.
- `PostToolUse` (`.claude/hooks/post-edit.sh`): formats edited shell, Markdown and Python files.

## CI and code review

`.github/workflows/ci.yml` calls the shared workflows in `gamaware/.github` and runs `make verify` and `make pdf`.
CodeRabbit (`.coderabbit.yaml`) and GitHub Copilot (`.github/copilot-instructions.md`) review every pull request.
