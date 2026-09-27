# ADR 0005: Render the PDF from Markdown with pandoc and WeasyPrint

## Status

Accepted

## Context

Clients expect a PDF; reviewers want a diff-able source. Keeping two documents in step by hand fails quickly. A
LaTeX toolchain is large to install locally and in CI.

## Decision

`report/REPORT.md` is the canonical report. `make pdf` renders `report/REPORT.pdf` with pandoc, using WeasyPrint as
the PDF engine and `report/report.css` for layout. WeasyPrint is pinned in the `report` dependency group, so local
and CI builds use the same version. CI builds the PDF on every run and uploads it as an artifact.

## Consequences

- One source for both formats, and styling in plain CSS.
- WeasyPrint needs Pango on the host (Homebrew on macOS, preinstalled on GitHub-hosted Ubuntu runners).
- PDF bytes are not reproducible across machines (fonts, timestamps), so CI proves the PDF builds rather than
  comparing it byte for byte. The committed PDF is regenerated whenever the report changes.

## Compliance

The `report` job in `.github/workflows/ci.yml` fails if `make pdf` fails or produces an empty file.

## Notes

Typst and LaTeX engines were considered; both need a separate toolchain that pip cannot install.
