## 1. Visible-Text Normalization

- [x] 1.1 Implement block-aware HTML visible-text extraction that removes style, script, noscript,
  template, SVG, and comment content while preserving plain text inputs; verify focused unit tests
  pass for WordPress HTML, malformed HTML, Chinese/English prose, entities, and comparison symbols.
- [x] 1.2 Add regression fixtures based on the observed WordPress inline-CSS shape and verify a
  presentation-only CSS change produces identical readable normalized content.

## 2. Versioned Snapshot Baselines

- [x] 2.1 Add an incremental SQLite migration for `snapshots.normalizer_version`, leaving existing
  rows at version 1; verify migration tests cover both a fresh database and upgrade from schema v1.
- [x] 2.2 Store the current normalizer version and restrict previous-snapshot lookup to that version;
  verify the first version-2 fetch is an `ok` baseline and the next version-2 content change is
  detected normally.

## 3. Content Quality Defense

- [x] 3.1 Implement a shared deterministic content-quality classifier with reason codes; verify unit
  tests reject CSS, JavaScript, markup, and serialized-structure-dominant samples while accepting
  readable Chinese and English technical prose.
- [x] 3.2 Integrate quality classification into analysis so rejected evidence is suppressed and its
  brief is non-sendable; verify analyzer tests persist the suppressed status without a delivery.
- [x] 3.3 Add the final notifier admission guard so unsafe stored facts cannot create deliveries;
  verify notifier tests reject a forced sendable CSS brief and continue queuing a readable brief.

## 4. Periodic Reporting and Integration

- [x] 4.1 Update periodic status wording to describe the absence of reportable readable changes and
  verify a run containing only suppressed technical changes queues one safe status report.
- [x] 4.2 Add an end-to-end regression test from WordPress fetch through analysis and notification;
  verify no CSS tokens appear in the rendered outbound text and execution/delivery counts remain
  consistent.
- [x] 4.3 Run the complete Watchlight test suite, Ruff checks, and strict OpenSpec validation; verify
  all commands pass before marking the change complete.
