# ADR 0005: Render the PDF from Markdown with pandoc and WeasyPrint

## Status

Accepted

## Context

Clients expect a PDF; reviewers want a diff-able source. Keeping two documents in step by hand fails quickly. A
LaTeX toolchain is large to install on a maintainer machine.

## Decision

`report/REPORT.md` is the canonical report. `make pdf` renders `report/REPORT.pdf` with pandoc, using WeasyPrint as
the PDF engine and `report/report.css` for layout. The `report` dependency group pins WeasyPrint, so every
maintainer machine uses the same version. In CI, the shared `report` workflow from `gamaware/.github` renders the same
Markdown with its pinned pandoc container on every run and uploads that PDF as an artifact, the same check every
sample deliverable in the portfolio runs.

## Consequences

- One source for both formats, and styling in plain CSS.
- WeasyPrint needs Pango on the host (Homebrew on macOS).
- CI renders with a different engine (LaTeX in the shared container), so its artifact proves the Markdown renders
  but does not match the committed PDF's layout. PDF bytes are not reproducible across machines anyway (fonts,
  timestamps), so no job compares PDFs byte for byte. The maintainer regenerates the committed PDF with `make pdf`
  whenever the report changes.

## Compliance

The `report / pdf` check in `.github/workflows/ci.yml` fails if the report does not render or the PDF is empty. The
`report / evidence` check reruns `make evidence` and fails if `evidence/` differs from the commit.

## Notes

The team considered Typst and LaTeX engines; both need a separate toolchain that pip cannot install.
