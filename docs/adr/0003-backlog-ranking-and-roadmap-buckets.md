# 0003. Rank the backlog by risk and effort, and pull dependencies forward on the roadmap

## Status

Accepted

## Context

A list of findings is not a plan. The team needs to know what to do first, and some fixes only make sense after
others (automatic rollback needs a health signal to roll back on). A roadmap drawn by hand tends to put a
prerequisite after the work that needs it.

## Decision

- Backlog order: risk (high, medium, low), then effort (S, M, L) so quick wins lead each risk band, then pillar
  order, then best-practice ID. Keys `HG-nn` follow that order.
- Roadmap: a starting bucket of 30, 60 or 90 days from risk and effort (high S/M in 30 days; high L and medium S/M
  in 60; the rest in 90). Any item that others depend on moves forward to the earliest bucket among its dependants.
  Inside a bucket, dependencies come before the items that need them.
- Validation rejects dependency cycles and dependencies on practices that are already met.

## Consequences

- The plan never schedules work before its prerequisites.
- Some low or medium items appear in early buckets; the roadmap marks them "moved forward" so the reason is visible.
- The rules ignore team capacity. The first 30 days can fill up, and the readout adjusts them with the team.

## Compliance

`tests/test_backlog.py` covers the ordering, the bucket table, chains of dependencies and an item that two
others need, and checks that no roadmap item comes before its dependencies. `tests/test_report.py` recomputes
the order and every `roadmap_days` value in `evidence/backlog.csv` with the independent reference implementation.

## Notes

The team rejected pushing dependants later instead of pulling dependencies forward: it delayed high-risk fixes
behind small medium-risk tasks, the opposite of what the ranking asks for.
