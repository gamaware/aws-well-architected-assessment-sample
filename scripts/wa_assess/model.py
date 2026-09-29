"""Load the assessment data from YAML and reject anything the scoring rules cannot handle."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

STATUSES = ("met", "partial", "not_met", "not_applicable")
GAP_STATUSES = ("partial", "not_met")
RISKS = ("high", "medium", "low")
EFFORTS = ("S", "M", "L")

# Report order. The six Well-Architected pillars first, then the DevOps lens.
PILLARS = (
    "operational-excellence",
    "security",
    "reliability",
    "performance-efficiency",
    "cost-optimization",
    "sustainability",
    "devops",
)
FRAMEWORK_PREFIX = {
    "operational-excellence": "OPS",
    "security": "SEC",
    "reliability": "REL",
    "performance-efficiency": "PERF",
    "cost-optimization": "COST",
    "sustainability": "SUS",
}
FRAMEWORK_ID = re.compile(r"^(?P<question>(?P<prefix>[A-Z]+)\d{2})-BP\d{2}$")
DEVOPS_ID = re.compile(r"^(?P<question>(?P<prefix>OA|DL|QA|AG|O)\.[A-Z]+)\.\d+$")


class AssessmentError(ValueError):
    """The data breaks one or more rules. The message lists every problem found."""


@dataclass(frozen=True)
class Item:
    id: str
    pillar: str
    question: str
    title: str
    status: str
    observation: str
    evidence: tuple[str, ...]
    risk: str | None = None
    effort: str | None = None
    owner: str | None = None
    recommendation: str | None = None
    depends_on: tuple[str, ...] = ()

    @property
    def is_gap(self) -> bool:
        return self.status in GAP_STATUSES


@dataclass(frozen=True)
class Pillar:
    key: str
    name: str
    lens: str
    questions: dict[str, str]
    items: tuple[Item, ...]


@dataclass(frozen=True)
class Assessment:
    root: Path
    workload: dict
    evidence: dict[str, dict]
    pillars: tuple[Pillar, ...]

    def items(self) -> list[Item]:
        return [item for pillar in self.pillars for item in pillar.items]

    def item(self, item_id: str) -> Item:
        return next(item for item in self.items() if item.id == item_id)


def _read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise AssessmentError(f"{path}: expected a mapping at the top level")
    return data


def _text(raw: dict, key: str) -> str:
    """A field as single-spaced text; a missing or null field is empty, never the string "None"."""
    value = raw.get(key)
    return " ".join(str(value).split()) if value is not None else ""


def _ids(raw: dict, key: str) -> tuple[str, ...]:
    """A list-of-IDs field as a tuple. A scalar is rejected: iterating "EV-01" would yield single characters."""
    value = raw.get(key)
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise AssessmentError(f"{raw.get('id', '?')}: {key} must be a list of IDs, got {value!r}")
    return tuple(value)


def _item(raw: dict, pillar: str) -> Item:
    return Item(
        id=_text(raw, "id"),
        pillar=pillar,
        question=_text(raw, "question"),
        title=_text(raw, "title"),
        status=_text(raw, "status"),
        observation=_text(raw, "observation"),
        evidence=_ids(raw, "evidence"),
        risk=raw.get("risk"),
        effort=raw.get("effort"),
        owner=_text(raw, "owner") or None,
        recommendation=_text(raw, "recommendation") or None,
        depends_on=_ids(raw, "depends_on"),
    )


def _evidence(entries: list) -> dict[str, dict]:
    register: dict[str, dict] = {}
    for entry in entries:
        ev_id = entry.get("id") if isinstance(entry, dict) else None
        if not ev_id:
            raise AssessmentError(f"evidence.yaml: entry without an id: {entry!r}")
        if ev_id in register:
            raise AssessmentError(f"evidence.yaml: duplicate evidence ID {ev_id}")
        register[ev_id] = entry
    return register


def load(data_dir: Path) -> Assessment:
    """Read data/synthetic and return a validated assessment."""
    workload = _read_yaml(data_dir / "workload.yaml")
    evidence = _evidence(_read_yaml(data_dir / "evidence.yaml").get("evidence") or [])
    pillars = []
    for key in PILLARS:
        raw = _read_yaml(data_dir / "answers" / f"{key}.yaml")
        pillars.append(
            Pillar(
                key=_text(raw, "pillar"),
                name=_text(raw, "name"),
                lens=_text(raw, "lens"),
                questions={str(k): _text(raw["questions"], k) for k in raw.get("questions") or {}},
                items=tuple(_item(entry, key) for entry in raw.get("items") or ()),
            )
        )
    assessment = Assessment(root=data_dir, workload=workload, evidence=evidence, pillars=tuple(pillars))
    problems = validate(assessment, file_keys=PILLARS)
    if problems:
        raise AssessmentError("invalid assessment data:\n- " + "\n- ".join(problems))
    return assessment


def _id_problems(item: Item, pillar: Pillar) -> list[str]:
    pattern = DEVOPS_ID if pillar.lens == "devops" else FRAMEWORK_ID
    match = pattern.match(item.id)
    if not match:
        return [f"{item.id}: not a valid {pillar.lens} best-practice ID"]
    problems = []
    if pillar.lens == "wellarchitected" and match["prefix"] != FRAMEWORK_PREFIX.get(pillar.key):
        problems.append(f"{item.id}: belongs to another pillar than {pillar.key}")
    if match["question"] != item.question:
        problems.append(f"{item.id}: question should be {match['question']}, not {item.question}")
    return problems


def _field_problems(item: Item) -> list[str]:
    problems = []
    if item.status not in STATUSES:
        problems.append(f"{item.id}: unknown status {item.status!r}")
    if not item.title or not item.observation:
        problems.append(f"{item.id}: title and observation are required")
    if not item.evidence:
        problems.append(f"{item.id}: cites no evidence")
    if item.is_gap:
        if item.risk not in RISKS:
            problems.append(f"{item.id}: a gap needs a risk of {', '.join(RISKS)}")
        if item.effort not in EFFORTS:
            problems.append(f"{item.id}: a gap needs an effort of {', '.join(EFFORTS)}")
        if not item.owner or not item.recommendation:
            problems.append(f"{item.id}: a gap needs an owner and a recommendation")
    elif item.risk or item.effort or item.depends_on:
        problems.append(f"{item.id}: only gaps take risk, effort or depends_on")
    return problems


def _cycle(items: dict[str, Item]) -> list[str]:
    """Return one dependency cycle as a list of IDs, or an empty list."""
    state: dict[str, int] = {}
    path: list[str] = []

    def visit(item_id: str) -> list[str]:
        state[item_id] = 1
        path.append(item_id)
        for dep in items[item_id].depends_on:
            if dep not in items:
                continue
            if state.get(dep) == 1:
                return [*path[path.index(dep) :], dep]
            if dep not in state and (found := visit(dep)):
                return found
        path.pop()
        state[item_id] = 2
        return []

    for item_id in items:
        if item_id not in state and (found := visit(item_id)):
            return found
    return []


def _dependency_problems(items: dict[str, Item]) -> list[str]:
    problems = []
    for item in items.values():
        for dep in item.depends_on:
            if dep == item.id:
                problems.append(f"{item.id}: depends on itself")
            elif dep not in items:
                problems.append(f"{item.id}: depends on unknown item {dep}")
            elif not items[dep].is_gap:
                problems.append(f"{item.id}: depends on {dep}, which is already met")
    if cycle := _cycle(items):
        problems.append("dependency cycle: " + " -> ".join(cycle))
    return problems


def validate(assessment: Assessment, file_keys: tuple[str, ...] = PILLARS) -> list[str]:
    """Return every rule the data breaks. An empty list means the data is valid."""
    problems: list[str] = []
    items: dict[str, Item] = {}
    cited: set[str] = set()

    for key, pillar in zip(file_keys, assessment.pillars, strict=True):
        if pillar.key != key:
            problems.append(f"answers/{key}.yaml: pillar field says {pillar.key!r}")
        expected_lens = "devops" if key == "devops" else "wellarchitected"
        if pillar.lens != expected_lens:
            problems.append(f"answers/{key}.yaml: lens should be {expected_lens}")
        answered = {item.question for item in pillar.items}
        problems += [f"{key}: question {q} has no answers" for q in pillar.questions if q not in answered]
        for item in pillar.items:
            if item.id in items:
                problems.append(f"{item.id}: duplicate ID")
            items[item.id] = item
            if item.question not in pillar.questions:
                problems.append(f"{item.id}: question {item.question} is not listed in {key}")
            problems += _id_problems(item, pillar)
            problems += _field_problems(item)
            cited.update(item.evidence)
            problems += [
                f"{item.id}: cites unknown evidence {ev}" for ev in item.evidence if ev not in assessment.evidence
            ]

    problems += _dependency_problems(items)
    for ev_id, entry in assessment.evidence.items():
        if ev_id not in cited:
            problems.append(f"{ev_id}: evidence is never cited")
        source = entry.get("source")
        if source:
            exports = (assessment.root / "exports").resolve()
            path = (assessment.root.parent.parent / source).resolve()
            if not path.is_relative_to(exports):
                problems.append(f"{ev_id}: source {source} must sit under data/synthetic/exports")
            elif not path.is_file():
                problems.append(f"{ev_id}: source file {source} is missing")
    return problems
