# E3C Translation Review Workbook Design

## Goal

Provide a multilingual medical reviewer with a self-contained Excel workbook
for reviewing the 30 German E3C feasibility translations without requiring
access to the repository, Python, or command-line tools. The reviewer produces
a complete accepted or corrected German text for each case and explicitly
records only changes that affect clinical meaning.

The workbook is an interchange and editing interface. It is not the canonical
repository format. Import creates validated, versioned text and review
artifacts while preserving the original machine translations unchanged.

## Scope

This design covers the bilingual medical review of the existing
`e3c-de-feasibility-30-v1` translation snapshot.

The workbook is an internal review artifact, not a redistribution package.
Source provenance remains resolvable through case IDs, the export manifest,
and content hashes; license and attribution material is not duplicated in the
workbook.

It deliberately does not cover:

- HPO mapping or annotation adjudication, which will use a separate workflow;
- review by multiple independent reviewers;
- automated semantic scoring or automatic acceptance;
- macros, external links, or a web application;
- publication of an accepted benchmark release.

The first workflow assumes one multilingual medical professional. A later
workflow may add adjudication without changing the reviewed source artifacts.

## Translation Variant

Google `general/translation-llm` (`tllm`) is the primary review text. Existing
internal comparison work found 12 meaning-changing findings for `tllm` versus
24 for `general/nmt`, no `tllm` case with grade 4 or 5, no deleted leading
phenotypes, and preserved line structure in all 30 cases.

The standard workbook does not contain NMT. An explicit export option may add
NMT as a read-only column in the main review sheet. It is reference material,
not an alternative input that the reviewer must reconcile.

## Workbook Structure

The workbook contains two sheets.

### `Anleitung`

This sheet explains the workflow, allowed decisions, clinical-change policy,
and saving instructions in concise language. It contains these editable review
metadata fields:

- reviewer ID or name;
- medical qualification;
- languages reviewed;
- review date as text in `YYYY-MM-DD` form.

Export ID, dataset selection, and review-policy ID are exporter-owned,
read-only metadata. The import requires exact agreement with the authoritative
export manifest; the reviewer cannot choose or alter the applicable policy.
Reviewer identity may be pseudonymous, but it must be stable and non-empty.
Qualification is recorded separately from identity.

### `Review`

There is exactly one row per case. Source fields are read-only and input fields
use Excel validation lists where applicable.

| Column | Purpose | Editable |
| --- | --- | --- |
| `Fall-ID` | Stable source case ID | no |
| `Quellsprache` | `en`, `es`, or `fr` | no |
| `Originaltext` | Canonical E3C source report | no |
| `TLLM-Ausgangsfassung` | Unreviewed primary translation | no |
| `Korrigierte Endfassung` | Complete proposed German text, initially copied from TLLM | yes |
| `Entscheidung` | `unverändert akzeptiert`, `korrigiert akzeptiert`, `Rückfrage`, or `abgelehnt` | yes |
| `Klinisch relevante Änderung` | `keine` or `vorhanden` | yes |
| `Hauptkategorie` | Principal category for a clinically relevant change | conditionally |
| `Änderungsbegründung` | Short medical explanation | conditionally |
| `Reviewer-Kommentar` | Optional free-text note | yes |
| `NMT-Vergleich` | Optional NMT reference text, only when explicitly exported | no |

Allowed principal categories are:

- `Auslassung`;
- `Hinzufügung`;
- `Negation oder Aussagesicherheit`;
- `Zahl oder Einheit`;
- `Anatomie oder Lateralität`;
- `Terminologie`;
- `Quellproblem`.

If a case has several clinically relevant changes, the reviewer selects the
most consequential category and summarizes all relevant changes in
`Änderungsbegründung`. Linguistic cleanup does not require individual
classification. Every actual textual edit remains recoverable through an
automatically generated diff between TLLM and the corrected final text.

The allowed field combinations are normative:

| Decision | Final text | Clinical change | Category and rationale |
| --- | --- | --- | --- |
| `unverändert akzeptiert` | exactly TLLM | `keine` | empty |
| `korrigiert akzeptiert` | different from TLLM | `keine` | empty |
| `korrigiert akzeptiert` | different from TLLM | `vorhanden` | required |
| `Rückfrage` | same or different | `vorhanden` | required |
| `abgelehnt` | same or different | `vorhanden` | required |

Every other combination is invalid. Acceptance is derived only from
`Entscheidung`; `Rückfrage` maps to `changes_requested` and `abgelehnt` maps
to `rejected` in the generic release gate.

The longest current text is 4,266 characters, safely below Excel's 32,767
UTF-16-code-unit cell limit. Export and import validate every long-text cell
against that limit, including corrected text and optional NMT.

## Reviewer Workflow

1. Open the workbook and complete the reviewer metadata.
2. For each row, compare the full original report with the full TLLM text.
3. Edit `Korrigierte Endfassung` into the complete German text that should be
   retained. Do not enter a patch or isolated replacement phrase.
4. Select the decision and whether clinical meaning changed.
5. When clinical meaning changed, select the main category and explain the
   change briefly.
6. Use `Rückfrage` where the source or correct rendering cannot be resolved and
   `abgelehnt` where the case cannot be made suitable through review.
7. Save the workbook without changing its file type.

No row with `Rückfrage` or `abgelehnt` is release-eligible. The workbook does
not itself promote any case to a benchmark release.

## Export

Export first creates a canonical `translation-review-export/v1` JSON manifest.
It contains the selection ID, review-policy ID, ordered case IDs, source
languages, full source and TLLM artifact SHA-256 values, and, when requested,
the NMT recipe and artifact SHA-256 values. Its canonical JSON SHA-256 is the
export ID. The content-addressed artifact store is the authority for this
manifest and the referenced text; hashes copied into Excel are never trusted
on their own.

The workbook contains the export ID and is semantically deterministic for the
same manifest and export options. Byte-identical `.xlsx` ZIP output is not a
requirement because Office metadata and ZIP timestamps can differ. It has:

- frozen headers, filters, wrapped text, and practical column widths;
- protected source cells, unlocked review cells, and protection settings that
  still allow filtering, row navigation, and selection and copying of locked
  source, TLLM, and optional NMT cells;
- validation lists for controlled values;
- TLLM prefilled into every corrected-final-text cell;
- no formulas, macros, or external links;
- top-aligned text with a moderate fixed row height; the instructions tell the
  reviewer to use the formula bar or cell editor for text beyond the visible
  preview;
- review-date cells formatted and validated as text, not locale-dependent
  Excel date serials;
- `NMT-Vergleich` present if and only if the export manifest contains NMT
  references, with exactly one matching value per case.

Sheet protection improves usability but is not a security or integrity
boundary. Import resolves the export ID from the artifact store and compares
every immutable cell with the referenced canonical artifact. If NMT is
included, its displayed text is checked in the same way.

## Import and Canonical Artifacts

Import first parses and validates the entire workbook without publishing a
review manifest. It then stores content-addressed immutable objects and
publishes one canonical `translation-review-import/v1` manifest last. Objects
written before a failure are harmless and reusable because they are addressed
by content; without the final manifest, no review import exists.

A successful import produces for every row, including `Rückfrage` and
`abgelehnt`:

- one immutable proposed German text artifact;
- one `translation-review-record/v1`, containing `source_case_id` and bound to
  the export ID, source hash, reviewed TLLM hash, proposed-text hash, reviewer
  ID and qualification, languages, `review_date`, review-policy ID, decision,
  clinical-change flag, category, rationale, and comment;
- one deterministic `unified-text-diff/v1` from TLLM to proposed text;
- one import manifest whose ordered entries explicitly pair each
  `source_case_id` with its record and diff hashes.

Only proposed texts whose decision is one of the two accepted values are
eligible for downstream selection. Import time is operational provenance and
does not participate in content identity; the reviewer-provided `review_date`
is the only semantic review date.

Reimporting the same completed workbook produces the same content identities
and manifest. A workbook with revised imported semantic values produces a new
manifest and leaves the old one intact; formatting or Office-metadata-only
changes do not. Imports do not define a mutable `latest`; a later release must
explicitly select one import manifest.

The `.xlsx` file may be retained as supporting evidence, but downstream code
consumes canonical JSON and UTF-8 text artifacts rather than Excel cells.
Original source, TLLM, and optional NMT files are never overwritten.

The translation-review record maps its decision to the existing generic
`ReviewRecord` acceptance gate. It does not encode translation decisions as
annotation-review scopes.

| Generic `ReviewRecord` field | Translation-review value |
| --- | --- |
| `subject_sha256` | proposed-text SHA-256 |
| `review_kind` | `bilingual` |
| `review_policy_id` | exporter-owned policy ID |
| `manual_requirement` | `required` |
| `reviewer_role` | recorded medical qualification |
| `manual_status` for `unverändert akzeptiert` | `accepted` |
| `manual_status` for `korrigiert akzeptiert` | `accepted` |
| `manual_status` for `Rückfrage` | `changes_requested` |
| `manual_status` for `abgelehnt` | `rejected` |

## Text and Diff Canonicalization

Cell text is normalized with the repository's existing
`canonical_text_bytes`: Unicode NFC, CRLF and CR converted to LF, UTF-8 without
a BOM, and no implicit trimming. Equality and hashes use those canonical
bytes. This prevents Excel newline conventions from creating false changes
while preserving intentional leading or trailing whitespace edits.

`unified-text-diff/v1` is a deterministic line-based unified diff over the
canonical TLLM and proposed-text strings, with fixed labels `tllm` and
`reviewed`, three context lines, LF endings, and no timestamps. The schema and
algorithm version are stored with the diff so a future renderer does not alter
existing audit identities.

## Validation and Failure Handling

Import rejects the workbook as a whole when any of these conditions holds:

- the file is not `.xlsx`, the two required sheets are not the only sheets, or
  a required header or column is missing;
- the export ID does not resolve to a valid authoritative export manifest;
- case IDs are missing, duplicated, added, or not part of the export;
- source language, source text, TLLM text, or optional NMT text differs from
  the export manifest's referenced artifacts;
- presence of the `NMT-Vergleich` column differs from the export manifest;
- a controlled value is missing where required or is outside its enum;
- corrected final text is empty;
- any row violates the decision table above;
- reviewer identity, qualification, languages, or valid `YYYY-MM-DD` review
  date is missing;
- the read-only review-policy ID differs from the export manifest;
- any cell contains a formula, or the workbook contains VBA, external links,
  or unexpected sheets; Excel data-validation rules generated by the exporter
  remain allowed;
- any long-text value exceeds Excel's 32,767 UTF-16-code-unit limit.

Validation reports identify the sheet, row, case ID, and field with a concise
remediation message. Failed validation performs no partial import.

## Testing

Automated tests cover:

- deterministic export manifest and semantic workbook content for fixed
  inputs;
- exactly 30 unique cases in the current snapshot;
- default omission and explicit inclusion of the NMT column;
- preservation of multiline Unicode medical text;
- correct locking, validation lists, and prefilled final text;
- selection and copying, but not editing, of locked text cells;
- successful round-trip of unchanged and corrected cases;
- every allowed and forbidden decision-table combination;
- canonical newline, Unicode, UTF-8, and derived-diff behavior;
- each validation failure above;
- no manifest publication when validation or an injected object write fails;
- identical semantic reimport and distinct semantically revised import;
- optional-NMT tampering, extra sheets, formulas, macros, and external links;
- text-length boundaries and accepted Excel text-date forms;
- unchanged source and machine-translation artifact bytes after import.

A manual smoke test opens the generated workbook in current Excel, edits and
saves representative English, Spanish, and French cases, and confirms that the
saved file imports without repair warnings or formatting loss.

## Follow-up Boundary

After accepted German texts exist, HPO identity, assertion, temporality,
experiencer, and evidence review will be designed as a separate workbook or
interface. Translation review establishes the reviewed text identity that the
later annotation decisions must reference; it does not combine both decisions
into one spreadsheet.
