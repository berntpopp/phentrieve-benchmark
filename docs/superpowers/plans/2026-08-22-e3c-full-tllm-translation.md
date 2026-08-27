# E3C Full-Corpus TLLM Translation Plan

**Goal:** Translate the 216 E3C reports not present in the existing 30-case TLLM snapshot while reusing those 30 translations byte-for-byte.

**KISS/YAGNI design:** Add one explicit `tllm-full` recipe/variant. Its input is the complete verified E3C normalization inventory (246 reports); the inventory artifact is also its reproducible selection identity. Do not add a generic cohort/scope framework or another selection algorithm.

## Single implementation task

**Files:**
- Modify `src/phentrieve_benchmark/pipeline/translate.py`
- Modify `src/phentrieve_benchmark/translation/e3c.py`
- Modify `src/phentrieve_benchmark/translation/variants.py`
- Modify focused translation/CLI/contract tests
- Create `datasets/e3c-de/translation-llm-full.yaml`
- Update `datasets/e3c-de/translations/README.md` and `docs/project-checklist.md`

**Required behavior:**

1. `--variant tllm-full` loads a pinned recipe with selection ID `e3c-de-full-246-v1`, model `general/translation-llm`, location `us-central1`, and the existing pinned TLLM pricing.
2. Preparation reads all normalized E3C documents and binds `selection_sha256` to the verified inventory artifact. It never contacts Google.
3. Preparation first reuses a compatible published `tllm-full` manifest for the same Google project, including across code-hash changes. On the first run it may seed reuse from the published 30-case `tllm` manifest for that project.
4. Cross-selection reuse requires identical source hash/language, target, provider, API, model, project, and location plus a completed provider output. `automatic_check_failed` is reusable but remains failed: its warnings and checks stay visible for medical review. Reused bytes/checks remain unchanged, while records are rebound to the full recipe selection identity with provenance to the prior translation ID. Same-selection reuse leaves the record unchanged.
5. The cost preview reports only non-reusable cases/codepoints. With the current artifacts it must report 216 cases, 441,414 input codepoints, and the pinned upper bound USD 10.152522.
6. The paid provider remains behind the existing explicit CLI confirmation. No paid call occurs in tests or implementation.
7. Tests cover variant/recipe identity, full input preparation, 30-case reuse, cross-selection rebinding, billable-only estimate, and denial before provider construction. Run focused tests, `ruff check src tests`, `mypy`, and full `pytest -q`.

After all implementation, review, and documentation commits, rerun `acquire e3c` and `normalize e3c` with the same dataset/artifact roots because verified upstream pointers are code-hash-bound. These stages do not invoke the paid translation provider. Then run the real CLI preview, stop at its confirmation prompt, and obtain explicit user approval for the displayed cost before invoking Google.
