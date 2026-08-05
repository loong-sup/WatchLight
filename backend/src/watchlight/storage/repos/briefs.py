from __future__ import annotations

import json
from typing import Any

from watchlight.storage.repos import Repo
from watchlight.storage.store import Store, new_id


class BriefsRepo(Repo):
    @classmethod
    def for_user(cls, store: Store, user_id: str) -> BriefsRepo:
        return cls(store, user_id)

    def insert(self, values: dict[str, Any]) -> dict[str, Any]:
        brief_id = str(values.get("brief_id") or new_id())
        self.store.execute(
            "INSERT INTO briefs(brief_id,user_id,execution_id,signal_ids_json,facts_json,"
            "inferences_json,next_steps_json,source_refs_json,captured_at,uncertainty_level,"
            "sendable,failure_summary) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                brief_id,
                self.user_id,
                values["execution_id"],
                json.dumps(values.get("signal_ids", []), ensure_ascii=False),
                json.dumps(values.get("facts", []), ensure_ascii=False),
                json.dumps(values.get("inferences", []), ensure_ascii=False),
                json.dumps(values.get("next_steps", []), ensure_ascii=False),
                json.dumps(values.get("source_refs", []), ensure_ascii=False),
                values.get("captured_at"),
                values.get("uncertainty_level", "medium"),
                int(bool(values.get("sendable", False))),
                values.get("failure_summary"),
            ),
        )
        result = self.get(brief_id)
        assert result is not None
        return result

    def get(self, brief_id: str) -> dict[str, Any] | None:
        return self.one("SELECT * FROM briefs WHERE brief_id=? AND user_id=?", (brief_id,))

    def list_for_execution(self, execution_id: str) -> list[dict[str, Any]]:
        return self.all(
            "SELECT * FROM briefs WHERE execution_id=? AND user_id=? ORDER BY brief_id",
            (execution_id,),
        )
