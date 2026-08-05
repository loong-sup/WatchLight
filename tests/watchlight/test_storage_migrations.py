from __future__ import annotations

from watchlight.storage import Store, migrate


def test_migrate_is_idempotent_and_creates_business_tables() -> None:
    store = Store.open(":memory:")
    migrate(store)
    migrate(store)
    names = {
        str(row["name"])
        for row in store.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
    }
    expected = {
        "users",
        "channel_identities",
        "identity_events",
        "watch_tasks",
        "watch_task_versions",
        "executions",
        "source_hits",
        "snapshots",
        "snapshot_blobs",
        "changes",
        "signals",
        "briefs",
        "deliveries",
        "feedbacks",
        "preferences",
        "events",
    }
    assert expected <= names
    assert store.fetchone("SELECT COUNT(*) AS count FROM schema_version")["count"] == 1
    store.close()


def test_state_checks_reject_unknown_values() -> None:
    store = Store.open(":memory:")
    migrate(store)
    store.execute(
        "INSERT INTO users(user_id, display_name, timezone, created_at) VALUES ('u1','U','UTC',1)"
    )
    try:
        store.execute(
            "INSERT INTO watch_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            ("t1", "u1", "x", "{}", "{}", 900, "{}", "unknown", 1, None, 1, 1),
        )
    except Exception as exc:
        assert "CHECK constraint failed" in str(exc)
    else:
        raise AssertionError("invalid task status was accepted")
    store.close()
