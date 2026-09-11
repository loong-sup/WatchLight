from __future__ import annotations

from watchlight.storage import Store, migrate
from watchlight.storage.migrations import SCHEMA_V1


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
    assert store.fetchone("SELECT COUNT(*) AS count FROM schema_version")["count"] == 2
    snapshot_columns = {
        str(row["name"]) for row in store.fetchall("PRAGMA table_info(snapshots)")
    }
    assert "normalizer_version" in snapshot_columns
    store.close()


def test_v1_database_upgrade_preserves_existing_snapshot_version() -> None:
    store = Store.open(":memory:")
    for statement in SCHEMA_V1.split(";"):
        if statement.strip():
            store.execute(statement)
    store.execute("INSERT INTO schema_version(version,applied_at) VALUES (1,1)")
    store.execute("PRAGMA foreign_keys=OFF")
    store.execute(
        "INSERT INTO snapshots(snapshot_id,user_id,execution_id,source_url,captured_at,"
        "content_hash,raw_ref,normalized_ref,previous_snapshot_id) "
        "VALUES ('s1','u1','e1','https://example.com',1,'hash','raw','normalized',NULL)"
    )

    migrate(store)

    snapshot = store.fetchone("SELECT * FROM snapshots WHERE snapshot_id='s1'")
    assert snapshot is not None
    assert snapshot["normalizer_version"] == 1
    assert store.fetchone("SELECT COUNT(*) AS count FROM schema_version")["count"] == 2
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
