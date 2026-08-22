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
and saving instructions in concise language. It also contains editable review
metadata:

- reviewer ID or name;
- medical qualification;
- languages reviewed;
- review date in `YYYY-MM-DD` form;
- review-guideline version.

Export identity, dataset selection, and source hashes are shown as read-only
metadata. Reviewer identity may be pseudonymous, but it must be stable and
non-empty.

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

The longest current text is 4,266 characters, safely below Excel's 32,767
character cell limit.

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

Export is deterministic for the same selection, translation artifacts,
guideline version, and export options. It writes an `.xlsx` file with:

- frozen headers, filters, wrapped text, and practical column widths;
- protected source cells and editable review cells;
- validation lists for controlled values;
- TLLM prefilled into every corrected-final-text cell;
- no formulas, macros, or external links;
- workbook metadata binding each row to the full SHA-256 identities of its
  source and TLLM artifacts;
- NMT omitted by default and added only through an explicit option.

Sheet protection improves usability but is not a security or integrity
boundary. Import verifies immutable values and hashes independently.

## Import and Canonical Artifacts

Import is transactional: it validates the entire workbook before writing any
artifact. A successful import produces:

- one immutable corrected German text artifact per accepted case;
- one canonical review record per case, bound to the reviewed TLLM hash and
  corrected-text hash;
- reviewer role, stable reviewer identity, decision time, policy version,
  clinical-change flag, category, rationale, and comment;
- an automatically derived TLLM-to-final-text diff for audit and reporting;
- a deterministic import manifest linking the workbook export identity to all
  produced artifacts.

The `.xlsx` file may be retained as supporting evidence, but downstream code
consumes canonical JSON and UTF-8 text artifacts rather than Excel cells.
Original source, TLLM, and optional NMT files are never overwritten.

The implementation introduces a translation-review schema for the reviewed
text identity, clinical-change fields, and decision. It may embed or reference
the existing generic `ReviewRecord` for the common acceptance gate, but it does
not encode translation decisions as annotation-review scopes.

## Validation and Failure Handling

Import rejects the workbook as a whole when any of these conditions holds:

- workbook identity, required sheet, header, or required column is missing;
- case IDs are missing, duplicated, added, or not part of the export;
- source language, source text, TLLM text, or embedded hash differs from the
  export;
- controlled values are empty or invalid;
- corrected final text is empty;
- `vorhanden` lacks a category or rationale;
- `keine` carries a clinical-change category or rationale;
- `unverändert akzeptiert` has a corrected text different from TLLM;
- `korrigiert akzeptiert` has a corrected text identical to TLLM;
- reviewer identity, qualification, languages, date, or policy version is
  missing;
- a formula, macro, or external link occurs in an accepted input field;
- a row marked `Rückfrage` or `abgelehnt` is presented as accepted.

Validation reports identify the sheet, row, case ID, and field with a concise
remediation message. Failed validation performs no partial import.

## Testing

Automated tests cover:

- deterministic workbook content for fixed inputs;
- exactly 30 unique cases in the current snapshot;
- default omission and explicit inclusion of the NMT column;
- preservation of multiline Unicode medical text;
- correct locking, validation lists, and prefilled final text;
- successful round-trip of unchanged and corrected cases;
- derived diff generation;
- each validation failure above;
- atomic behavior when one row is invalid;
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
