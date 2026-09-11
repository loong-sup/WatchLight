from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class EvalSource:
    url: str
    previous_path: Path
    current_path: Path
    http_status: int = 200


@dataclass(frozen=True, slots=True)
class EvalCase:
    case_id: str
    task_id: str
    captured_at: int
    category: str
    trigger_condition: dict[str, list[str]]
    sources: tuple[EvalSource, ...]
    expected_notify: bool
    expected_facts: tuple[str, ...]
    expected_event_id: str | None = None


@dataclass(frozen=True, slots=True)
class EvalDataset:
    name: str
    version: str
    cases: tuple[EvalCase, ...]
    path: Path


def _require_text(value: object, field: str, line_number: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"line {line_number}: {field} must be a non-empty string")
    return value.strip()


def _load_source(value: object, root: Path, line_number: int) -> EvalSource:
    if not isinstance(value, dict):
        raise ValueError(f"line {line_number}: each source must be an object")
    url = _require_text(value.get("url"), "sources[].url", line_number)
    previous = root / _require_text(
        value.get("previous_path"), "sources[].previous_path", line_number
    )
    current = root / _require_text(
        value.get("current_path"), "sources[].current_path", line_number
    )
    if not previous.is_file():
        raise ValueError(f"line {line_number}: previous snapshot not found: {previous}")
    if not current.is_file():
        raise ValueError(f"line {line_number}: current snapshot not found: {current}")
    status = value.get("http_status", 200)
    if not isinstance(status, int) or not 100 <= status <= 599:
        raise ValueError(f"line {line_number}: sources[].http_status must be 100..599")
    return EvalSource(url, previous.resolve(), current.resolve(), status)


def _load_case(value: dict[str, Any], root: Path, line_number: int) -> EvalCase:
    case_id = _require_text(value.get("case_id"), "case_id", line_number)
    task_id = _require_text(value.get("task_id"), "task_id", line_number)
    category = _require_text(value.get("category"), "category", line_number)
    captured_at = value.get("captured_at")
    if not isinstance(captured_at, int) or captured_at <= 0:
        raise ValueError(f"line {line_number}: captured_at must be a positive Unix timestamp")
    expected_notify = value.get("expected_notify")
    if not isinstance(expected_notify, bool):
        raise ValueError(f"line {line_number}: expected_notify must be a boolean")

    raw_condition = value.get("trigger_condition", {})
    if not isinstance(raw_condition, dict):
        raise ValueError(f"line {line_number}: trigger_condition must be an object")
    condition: dict[str, list[str]] = {}
    for key in ("must_contain", "must_not_contain"):
        raw_terms = raw_condition.get(key, [])
        if not isinstance(raw_terms, list) or not all(isinstance(item, str) for item in raw_terms):
            raise ValueError(f"line {line_number}: trigger_condition.{key} must be strings")
        condition[key] = [str(item) for item in raw_terms]

    raw_sources = value.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError(f"line {line_number}: sources must be a non-empty list")
    sources = tuple(_load_source(item, root, line_number) for item in raw_sources)

    raw_facts = value.get("expected_facts", [])
    if not isinstance(raw_facts, list) or not all(isinstance(item, str) for item in raw_facts):
        raise ValueError(f"line {line_number}: expected_facts must be strings")
    event_id_value = value.get("expected_event_id")
    event_id = str(event_id_value) if event_id_value is not None else None
    return EvalCase(
        case_id=case_id,
        task_id=task_id,
        captured_at=captured_at,
        category=category,
        trigger_condition=condition,
        sources=sources,
        expected_notify=expected_notify,
        expected_facts=tuple(str(item) for item in raw_facts),
        expected_event_id=event_id,
    )


def load_dataset(path: Path | str) -> EvalDataset:
    dataset_path = Path(path).resolve()
    cases: list[EvalCase] = []
    name = dataset_path.stem
    version = "1"
    seen_ids: set[str] = set()
    for line_number, line in enumerate(
        dataset_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        value = json.loads(stripped)
        if not isinstance(value, dict):
            raise ValueError(f"line {line_number}: record must be an object")
        if value.get("record_type") == "metadata":
            name = _require_text(value.get("name"), "name", line_number)
            version = _require_text(value.get("version"), "version", line_number)
            continue
        case = _load_case(value, dataset_path.parent, line_number)
        if case.case_id in seen_ids:
            raise ValueError(f"line {line_number}: duplicate case_id {case.case_id}")
        seen_ids.add(case.case_id)
        cases.append(case)
    if not cases:
        raise ValueError(f"dataset contains no cases: {dataset_path}")
    cases.sort(key=lambda item: (item.captured_at, item.case_id))
    return EvalDataset(name, version, tuple(cases), dataset_path)
