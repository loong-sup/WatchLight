## Why

Watchlight currently removes HTML tags with a regular expression but leaves the contents of
`<style>` and `<script>` nodes intact. A minor WordPress theme change can therefore be classified
as a user-relevant change and delivered to Feishu as thousands of characters of CSS or other
machine-oriented text.

## What Changes

- Replace tag-only stripping with deterministic visible-text extraction that removes non-content
  HTML nodes and preserves meaningful block boundaries.
- Version normalized snapshots so a normalizer upgrade establishes a fresh baseline instead of
  comparing incompatible representations and creating a one-time false alert.
- Add an evidence quality gate that suppresses CSS-, JavaScript-, and markup-dominant changes
  before they can become sendable briefs.
- Add a final notification-body guard so malformed or machine-oriented evidence cannot enter the
  delivery queue even if an upstream filter regresses.
- Add WordPress/CSS regression fixtures and end-to-end tests covering snapshot, analysis, queue,
  and user-visible notification behavior.

## Capabilities

### New Capabilities

- `web-content-normalization`: Extract stable, human-readable visible text from fetched HTML and
  safely establish baselines across normalizer versions.
- `notification-content-quality`: Prevent code- or structure-dominant change evidence from being
  queued and sent as a user notification.

### Modified Capabilities

None. This repository does not yet contain existing OpenSpec capability specifications.

## Impact

- Affects snapshot normalization and metadata in `collector/snapshot.py`, snapshot persistence and
  the SQLite migration set, change analysis, brief sendability, and notification queue admission.
- Existing raw blobs remain unchanged; new normalized snapshots use the new normalizer version.
- The first successful fetch for a source after the version upgrade becomes a baseline and must not
  emit a false change notification solely because the normalization algorithm changed.
- No external API contract changes are required. Database migration and regression tests are
  required.
