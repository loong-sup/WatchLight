# Web Content Normalization Specification

## Purpose

Ensure fetched web pages are represented as stable, human-readable visible text so technical page
structure and presentation assets cannot masquerade as user-relevant content changes.

## Requirements

### Requirement: Extract visible human-readable content
The system SHALL exclude non-visible and machine-oriented HTML content, including style rules,
scripts, templates, comments, SVG definitions, and fallback scripting nodes, from normalized page
content while retaining visible text.

#### Scenario: WordPress page contains inline theme CSS
- **WHEN** a fetched HTML page contains WordPress inline `<style>` blocks and visible article text
- **THEN** the normalized content contains the visible article text and contains none of the CSS
  declarations from those style blocks

#### Scenario: Page contains executable and template content
- **WHEN** a fetched HTML page contains script, noscript, template, comment, or SVG nodes
- **THEN** the normalized content excludes the contents of those nodes

#### Scenario: Plain text source is fetched
- **WHEN** fetched content is plain text rather than HTML
- **THEN** normalization preserves its readable text without interpreting comparison operators as
  HTML tags

### Requirement: Preserve meaningful comparison boundaries
The system SHALL preserve boundaries between visible headings, paragraphs, list items, table rows,
and other block content so change detection can compare readable units instead of a single
page-length line.

#### Scenario: Two article paragraphs differ
- **WHEN** only one visible paragraph changes between two versions of a page
- **THEN** change evidence is limited to the affected readable block and does not include unrelated
  page-wide content

### Requirement: Isolate normalizer versions
The system SHALL record the normalizer version used for every normalized snapshot and SHALL NOT
compare snapshots produced by incompatible normalizer versions.

#### Scenario: Existing source is first fetched after normalizer upgrade
- **WHEN** the latest stored snapshot uses an older normalizer version
- **THEN** the newly normalized snapshot becomes the baseline for the current version and produces
  no content-change signal solely because of the version upgrade

#### Scenario: Source is fetched again with the current normalizer
- **WHEN** a current-version baseline already exists for the source
- **THEN** the system compares the new normalized content with that baseline normally
