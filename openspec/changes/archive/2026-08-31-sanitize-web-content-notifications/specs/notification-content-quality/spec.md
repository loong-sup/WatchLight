## Purpose

Ensure user notification queues contain concise human-readable findings rather than CSS,
JavaScript, markup, serialized structures, or other machine-oriented extraction artifacts.

## ADDED Requirements

### Requirement: Reject machine-oriented change evidence
The system SHALL classify change evidence for content quality before marking it sendable and SHALL
suppress evidence dominated by CSS, JavaScript, HTML markup, or serialized structural syntax.
Natural-language content SHALL NOT be rejected merely because it is written in English.

#### Scenario: CSS dominates detected evidence
- **WHEN** detected evidence contains CSS selectors, declarations, custom properties, or rule syntax
  at machine-oriented density
- **THEN** the evidence is not included in a sendable brief

#### Scenario: Human-readable English article changes
- **WHEN** detected evidence is readable English prose with ordinary punctuation
- **THEN** it remains eligible for notification

#### Scenario: Human-readable Chinese article changes
- **WHEN** detected evidence is readable Chinese prose with ordinary punctuation
- **THEN** it remains eligible for notification

### Requirement: Guard delivery queue admission
The system SHALL perform a final quality check on rendered brief facts before creating a delivery.
A brief that fails this check SHALL create no outbound delivery, even if it was incorrectly marked
sendable upstream.

#### Scenario: Upstream sendable brief contains CSS
- **WHEN** a sendable brief reaches the notifier with facts dominated by CSS syntax
- **THEN** no delivery is queued for any channel

#### Scenario: Normal readable brief reaches notifier
- **WHEN** a sendable brief contains readable facts and valid source references
- **THEN** the normal channel delivery is queued without altering the readable facts

### Requirement: Preserve safe periodic reporting
The system SHALL continue to produce a readable periodic status report when a task is configured to
report every run and no safe user-relevant change remains after quality filtering.

#### Scenario: Only technical page structure changed
- **WHEN** all detected changes are suppressed as machine-oriented and the task reports every run
- **THEN** the user receives a concise status report stating that no reportable readable change was
  found, rather than the suppressed technical content

