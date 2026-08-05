from __future__ import annotations

from typing import Any

TASK_TEMPLATES: dict[str, dict[str, Any]] = {
    "tech_updates": {
        "target": "关注技术项目的重要发布",
        "source_scope": {"keywords": [], "urls": []},
        "trigger_condition": {"must_contain": ["发布", "release"], "must_not_contain": []},
    },
    "page_change": {
        "target": "关注指定公开页面的关键变化",
        "source_scope": {"keywords": [], "urls": []},
        "trigger_condition": {"must_contain": [], "must_not_contain": []},
    },
    "job_search": {
        "target": "关注符合条件的新岗位",
        "source_scope": {"keywords": [], "urls": []},
        "trigger_condition": {"must_contain": [], "must_not_contain": []},
    },
}


def get_template(name: str) -> dict[str, Any]:
    try:
        return dict(TASK_TEMPLATES[name])
    except KeyError as exc:
        raise ValueError(f"unknown task template: {name}") from exc
