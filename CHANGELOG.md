# Changelog

All notable changes to this sample. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The assessment is a sample deliverable, so each release is a numbered report revision rather than a versioned API.

## Unreleased

### Added

- Synthetic assessment data for the fictional retailer Harbor Goods: answers across the six Well-Architected
  pillars and the DevOps lens, an evidence register, and deployment, incident and credential exports.
- Scripts that validate the data, score each pillar, count high-risk and medium-risk issues, and export a
  risk-rated backlog (CSV and Markdown) and a 30/60/90-day roadmap.
- `report/REPORT.md` with generated tables, and `report/REPORT.pdf` rendered from it.
- Tests that recompute the report numbers from the data, plus `make verify` and `make test-live`.
- Methodology, ADRs, diagrams and CI.

### To do

- Pin the reusable workflows from `gamaware/.github` to a commit SHA instead of `@main`.
