"""Command line: `python -m wa_assess generate` writes the outputs; `check` fails if any committed output is stale."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wa_assess.model import AssessmentError, load
from wa_assess.render import Renderer

# Markdown files whose BEGIN/END GENERATED blocks are rendered from the data. The report must exist; the README is
# optional so the tests can work on a copy of data/ and report/ alone.
REPORT = "report/REPORT.md"
README = "README.md"


def outputs(repo_root: Path) -> dict[str, str]:
    renderer = Renderer(load(repo_root / "data" / "synthetic"), repo_root)
    files = renderer.files()
    files[REPORT] = renderer.report((repo_root / REPORT).read_text(encoding="utf-8"))
    if (repo_root / README).is_file():
        files[README] = renderer.report((repo_root / README).read_text(encoding="utf-8"))
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wa_assess", description=__doc__)
    parser.add_argument("command", choices=("generate", "check"))
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: current directory)")
    args = parser.parse_args(argv)

    try:
        files = outputs(args.root)
    except (AssessmentError, KeyError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    stale = []
    for relative, content in files.items():
        path = args.root / relative
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current == content:
            continue
        if args.command == "check":
            stale.append(relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"wrote {relative}")

    if stale:
        print("stale outputs (run `make evidence` and commit):", *stale, sep="\n  ", file=sys.stderr)
        return 1
    if args.command == "check":
        print(f"ok: {len(files)} outputs match data/synthetic")
    return 0


if __name__ == "__main__":
    sys.exit(main())
