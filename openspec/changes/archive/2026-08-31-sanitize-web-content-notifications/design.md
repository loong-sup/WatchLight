## Context

See `proposal.md` for motivation. Snapshot normalization currently strips tags using a regular
expression and collapses the entire document to one line. The analyzer compares those lines and the
default brief provider copies evidence verbatim into `facts`. The notifier trusts the stored
`sendable` flag and does not independently validate fact quality.

SQLite already stores snapshot metadata while raw and normalized bodies live in the Blob store.
The repository targets Python 3.11+ and does not currently depend on an HTML extraction library.

## Goals / Non-Goals

**Goals:**

- Produce deterministic, readable normalized text without adding a network-dependent extraction
  service.
- Prevent a normalizer rollout from generating a false change for every existing source.
- Enforce content quality both before brief creation and immediately before queue admission.
- Keep readable Chinese and English content eligible for delivery.

**Non-Goals:**

- Full article extraction, browser rendering, or site-specific selector configuration.
- Retrofitting or deleting historical snapshots and already delivered messages.
- Using an LLM as the primary sanitation or safety mechanism.
- Redesigning source relevance scoring beyond rejection of clearly machine-oriented evidence.

## Decisions

### Use a deterministic HTML parser and block-aware text extraction

Implement a small standard-library `HTMLParser` extractor with character-reference conversion. It
tracks ignored-node depth for `style`, `script`, `noscript`, `template`, `svg`, and related
non-content nodes; ignores comments; and emits line boundaries for block elements. It applies
conservative whitespace cleanup per line and deduplicates empty boundaries.

This is preferred over another regular expression because nested content cannot be removed safely
with tag substitution. It is preferred over adding Beautiful Soup/lxml for this focused fix because
the required behavior is small, deterministic, and testable without a new packaged dependency.
Inputs that do not look like HTML use a plain-text normalization path so mathematical comparison
characters are preserved.

### Version the normalized representation in SQLite

Add `normalizer_version INTEGER NOT NULL DEFAULT 1` to `snapshots` in a new schema migration. New
snapshots use the current constant (version 2). Baseline lookup accepts a version and only returns a
snapshot created by that same version. If no current-version snapshot exists, the write is recorded
as an initial `ok` snapshot rather than `changed`.

This is preferred over rewriting historical blobs because reprocessing all existing raw snapshots
would be expensive, would modify audit history, and could still create ambiguous comparisons.
Storing a version is also reusable for future extraction improvements.

### Use structural-density heuristics for content quality

Introduce a pure content-quality classifier shared by analyzer and notifier. It evaluates strong
machine-text indicators such as CSS custom properties and declarations, selectors plus braces,
script keywords and statement punctuation, markup density, and serialized key/value structure.
Classification requires multiple indicators or high structural punctuation density; English text
alone is never an indicator. The classifier returns a reason code to support tests and diagnostics.

The analyzer marks rejected candidates `suppressed` and their briefs non-sendable. The notifier
parses `facts_json` and repeats the check before inserting `deliveries`, providing defense in depth
for existing rows or future regressions.

This is preferred over keyword-only blocking because legitimate articles may mention CSS or JSON,
and over LLM classification because queue safety must remain available when the model provider is
unavailable.

### Reuse periodic no-change reporting after suppression

If no safe sendable brief remains, the existing execution pipeline creates its configured periodic
status brief. Its wording will refer to no *reportable readable change*, avoiding the inaccurate
claim that no bytes changed. The status brief itself remains subject to the final quality guard.

## Risks / Trade-offs

- [A custom parser is less capable than full readability extraction] → Keep the extraction contract
  conservative, cover malformed and WordPress fixtures, and leave article-ranking out of scope.
- [Structural heuristics can suppress legitimate technical news] → Require combined/high-density
  indicators and add readable prose tests containing technical terms.
- [Normalizer v2 temporarily resets comparison history] → Treat the first v2 fetch as a baseline;
  the following scheduled fetch resumes normal comparisons without false notifications.
- [Old v1 blobs consume storage] → Retain them as audit history; future retention cleanup can remove
  unreferenced historical blobs separately.
- [A queue guard can hide upstream regressions] → Return/store a reason through signal status or
  diagnostic events and assert the behavior in end-to-end tests.

## Migration Plan

1. Apply schema migration adding `snapshots.normalizer_version` with existing rows defaulted to 1.
2. Deploy parser and set the current writer version to 2.
3. On each source's first successful v2 fetch, store a baseline without emitting a change.
4. Observe suppressed-evidence reason counts and delivery queue results during the first full cycle.
5. Rollback can restore the old writer while leaving the additive column in place; v2 snapshots
   remain valid historical rows and are ignored by a v1-only lookup.
