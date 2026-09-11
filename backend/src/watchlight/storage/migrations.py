from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from watchlight.storage.store import Store


SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    created_at INTEGER NOT NULL,
    deleted_at INTEGER
);
CREATE TABLE IF NOT EXISTS channel_identities (
    channel_key TEXT NOT NULL,
    channel_user_id TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(user_id),
    status TEXT NOT NULL CHECK(status IN ('pending','bound','unbinding')),
    confirmed_at INTEGER,
    confirm_token TEXT UNIQUE,
    confirm_expires_at INTEGER,
    PRIMARY KEY(channel_key, channel_user_id)
);
CREATE TABLE IF NOT EXISTS identity_events (
    event_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id),
    event_type TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS watch_tasks (
    task_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id),
    target TEXT NOT NULL,
    source_scope_json TEXT NOT NULL,
    trigger_condition_json TEXT NOT NULL,
    frequency_seconds INTEGER NOT NULL CHECK(frequency_seconds BETWEEN 900 AND 604800),
    notification_policy_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active','paused','deleted','draining')),
    version INTEGER NOT NULL,
    current_version_id TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS watch_task_versions (
    version_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES watch_tasks(task_id),
    user_id TEXT NOT NULL REFERENCES users(user_id),
    version INTEGER NOT NULL,
    modifier_user_id TEXT NOT NULL,
    modified_at INTEGER NOT NULL,
    snapshot_json TEXT NOT NULL,
    UNIQUE(task_id, version)
);
CREATE TABLE IF NOT EXISTS executions (
    execution_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES watch_tasks(task_id),
    user_id TEXT NOT NULL REFERENCES users(user_id),
    task_version_id TEXT,
    scheduled_at INTEGER NOT NULL,
    started_at INTEGER,
    ended_at INTEGER,
    status TEXT NOT NULL CHECK(status IN (
        'pending','running','succeeded','partial','failed','cancelled','timed_out','recovered'
    )),
    source_count INTEGER NOT NULL DEFAULT 0,
    change_count INTEGER NOT NULL DEFAULT 0,
    signal_count INTEGER NOT NULL DEFAULT 0,
    delivery_count INTEGER NOT NULL DEFAULT 0,
    failure_summary TEXT,
    triggered_by TEXT NOT NULL CHECK(triggered_by IN ('cron','manual','bootstrap')),
    heartbeat_at INTEGER,
    status_history_json TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS source_hits (
    hit_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL REFERENCES executions(execution_id),
    user_id TEXT NOT NULL REFERENCES users(user_id),
    source_url TEXT NOT NULL,
    fetched_at INTEGER,
    status TEXT NOT NULL CHECK(status IN (
        'ok','unchanged','changed','unreachable','unparseable','blocked'
    )),
    http_status INTEGER,
    snapshot_id TEXT,
    error_code TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    robots_disallowed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id),
    execution_id TEXT NOT NULL REFERENCES executions(execution_id),
    source_url TEXT NOT NULL,
    captured_at INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    raw_ref TEXT NOT NULL,
    normalized_ref TEXT NOT NULL,
    previous_snapshot_id TEXT
);
CREATE TABLE IF NOT EXISTS snapshot_blobs (
    blob_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    ref TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS changes (
    change_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id),
    execution_id TEXT NOT NULL REFERENCES executions(execution_id),
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    previous_snapshot_id TEXT,
    change_type TEXT NOT NULL CHECK(change_type IN ('added','removed','modified')),
    evidence_ref TEXT NOT NULL,
    uncertainty_level TEXT NOT NULL CHECK(uncertainty_level IN ('high','medium','low'))
);
CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL REFERENCES executions(execution_id),
    task_id TEXT NOT NULL REFERENCES watch_tasks(task_id),
    user_id TEXT NOT NULL REFERENCES users(user_id),
    change_ids_json TEXT NOT NULL,
    source_urls_json TEXT NOT NULL,
    captured_at INTEGER NOT NULL,
    relevance REAL NOT NULL,
    importance REAL NOT NULL,
    novelty REAL NOT NULL,
    source_credibility REAL NOT NULL,
    uncertainty_level TEXT NOT NULL CHECK(uncertainty_level IN ('high','medium','low')),
    status TEXT NOT NULL CHECK(status IN ('proposed','suppressed','notified','deduped','expired')),
    dedup_key TEXT NOT NULL,
    status_history_json TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS briefs (
    brief_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id),
    execution_id TEXT NOT NULL REFERENCES executions(execution_id),
    signal_ids_json TEXT NOT NULL,
    facts_json TEXT NOT NULL,
    inferences_json TEXT NOT NULL,
    next_steps_json TEXT NOT NULL,
    source_refs_json TEXT NOT NULL,
    captured_at INTEGER,
    uncertainty_level TEXT NOT NULL CHECK(uncertainty_level IN ('high','medium','low')),
    sendable INTEGER NOT NULL CHECK(sendable IN (0,1)),
    failure_summary TEXT
);
CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id TEXT PRIMARY KEY,
    signal_id TEXT NOT NULL REFERENCES signals(signal_id),
    brief_id TEXT NOT NULL REFERENCES briefs(brief_id),
    channel_key TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(user_id),
    status TEXT NOT NULL CHECK(status IN (
        'queued','sending','delivered','retry','failed','deferred','suppressed'
    )),
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    scheduled_send_at INTEGER NOT NULL,
    sent_at INTEGER,
    UNIQUE(signal_id, channel_key)
);
CREATE TABLE IF NOT EXISTS feedbacks (
    feedback_id TEXT PRIMARY KEY,
    delivery_id TEXT NOT NULL REFERENCES deliveries(delivery_id),
    user_id TEXT NOT NULL REFERENCES users(user_id),
    rating TEXT NOT NULL CHECK(rating IN ('useful','useless','too_frequent')),
    reason TEXT,
    created_at INTEGER NOT NULL,
    applied_preference_id TEXT
);
CREATE TABLE IF NOT EXISTS preferences (
    preference_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id),
    task_id TEXT NOT NULL REFERENCES watch_tasks(task_id),
    scope TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('include','exclude','frequency_cap')),
    value_json TEXT NOT NULL,
    created_from_feedback_id TEXT,
    created_at INTEGER NOT NULL,
    revoked_at INTEGER
);
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    execution_id TEXT,
    task_id TEXT,
    user_id TEXT NOT NULL REFERENCES users(user_id),
    event_type TEXT NOT NULL,
    stage TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON watch_tasks(user_id, status);
CREATE INDEX IF NOT EXISTS idx_exec_due ON executions(status, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_exec_user_task ON executions(user_id, task_id);
CREATE INDEX IF NOT EXISTS idx_hits_exec ON source_hits(execution_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_url ON snapshots(user_id, source_url, captured_at);
CREATE INDEX IF NOT EXISTS idx_signals_dedup ON signals(user_id, task_id, dedup_key, captured_at);
CREATE INDEX IF NOT EXISTS idx_deliveries_due ON deliveries(status, scheduled_send_at);
CREATE INDEX IF NOT EXISTS idx_events_exec ON events(user_id, execution_id, created_at);
"""

SCHEMA_V2 = """
ALTER TABLE snapshots ADD COLUMN normalizer_version INTEGER NOT NULL DEFAULT 1;
CREATE INDEX IF NOT EXISTS idx_snapshots_url_version
ON snapshots(user_id, source_url, normalizer_version, captured_at);
"""


MIGRATIONS: tuple[tuple[int, str], ...] = ((1, SCHEMA_V1), (2, SCHEMA_V2))


def migrate(store: Store) -> None:
    store.execute(
        "CREATE TABLE IF NOT EXISTS schema_version "
        "(version INTEGER PRIMARY KEY, applied_at INTEGER NOT NULL)"
    )
    applied = {int(row["version"]) for row in store.fetchall("SELECT version FROM schema_version")}
    from watchlight.storage.store import utc_now

    for version, script in MIGRATIONS:
        if version in applied:
            continue
        with store.transaction():
            for statement in script.split(";"):
                if statement.strip():
                    store.execute(statement)
            store.execute(
                "INSERT INTO schema_version(version, applied_at) VALUES (?, ?)",
                (version, utc_now()),
            )
