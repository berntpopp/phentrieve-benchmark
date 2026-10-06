"""Prepare and validate proposal runs on disk.

The run directory datasets/e3c-de/proposals/<run_id>/ is tracked in Git:
prompt.md (the committed template), run.json, batch-NN.prompt.md (the exact
prompt per batch; paths, IDs, and hashes, no report text), batch-NN.json (the
unchanged subagent output), and validation.json. Full texts for the
subagents are written only below the local artifact root.
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.annotation_corpus import AnnotationCorpusManifest
from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.hpo_proposal import (
    ProposalBatch,
    ProposalRun,
    ProposalValidationReport,
)
from phentrieve_benchmark.ontology.hpo import HpoIndex
from phentrieve_benchmark.ontology.hpo_lookup import read_lookup_entries
from phentrieve_benchmark.proposals.run import (
    pilot_case_ids,
    plan_batches,
    render_batch_prompt,
    select_run_entries,
)
from phentrieve_benchmark.proposals.validate import validate_proposal_run
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    AnnotationLanguage,
)

PROPOSALS_DIRECTORY = Path("e3c-de/proposals")
PROMPT_TEMPLATE = Path("configs/prompts/hpo-span-proposal-v3.md")
GUIDELINE = Path("docs/annotation-guidelines/hpo-span-annotation.md")


@dataclass(frozen=True)
class GuidelineVersion:
    path: str
    commit: str
    sha256: str


def read_corpus(
    store: ArtifactStore, corpus_manifest_sha256: str
) -> tuple[AnnotationCorpusManifest, dict[str, Document]]:
    manifest = AnnotationCorpusManifest.model_validate_json(
        store.read_bytes(corpus_manifest_sha256), strict=True
    )
    documents: dict[str, Document] = {}
    for line in store.read_bytes(manifest.documents_sha256).splitlines():
        if line:
            document = Document.model_validate_json(line, strict=True)
            documents[document.document_id] = document
    return manifest, documents


def _display(path: Path, repository_root: Path) -> str:
    """Repo-relative POSIX path; tracked prompts must not hold machine paths."""
    try:
        return path.resolve().relative_to(repository_root.resolve()).as_posix()
    except ValueError:
        raise ValueError(
            f"{path} is outside the repository root {repository_root}"
        ) from None


def _write_batch_inputs(
    *,
    batch: ProposalBatch,
    run_id: str,
    template: str,
    documents: dict[str, Document],
    repository_root: Path,
    run_directory: Path,
    input_directory: Path,
) -> None:
    """Write the texts (local only) and the rendered prompt (tracked)."""
    batch_directory = input_directory / batch.batch_id
    batch_directory.mkdir(parents=True, exist_ok=True)
    listing: list[str] = []
    for number, entry in enumerate(batch.documents, start=1):
        text_path = batch_directory / f"{entry.source_case_id}.txt"
        text_path.write_bytes(documents[entry.document_id].text.encode("utf-8"))
        listing.append(
            f"{number}. document_id `{entry.document_id}`, "
            f"document_sha256 `{entry.document_sha256}`, "
            f"language `{entry.annotation_language}`, "
            f"text file `{_display(text_path, repository_root)}`"
        )
    prompt = render_batch_prompt(
        template,
        run_id=run_id,
        batch_id=batch.batch_id,
        output_path=_display(
            run_directory / f"{batch.batch_id}.json", repository_root
        ),
        documents="\n".join(listing),
    )
    (run_directory / f"{batch.batch_id}.prompt.md").write_bytes(
        prompt.encode("utf-8")
    )


def prepare_proposal_run(
    *,
    store: ArtifactStore,
    repository_root: Path,
    corpus_manifest_sha256: str,
    groups: AnnotationGroupManifest,
    run_id: str,
    model_id: str,
    run_date: date,
    prompt_template: bytes,
    guideline: GuidelineVersion,
    hpo_release: str,
    ontology_sha256: str,
    languages: Collection[AnnotationLanguage] | None,
    pilot: bool,
    case_ids: Collection[str] | None,
    batch_size: int,
    run_directory: Path,
    input_directory: Path,
) -> ProposalRun:
    """Write run.json, prompt.md, the batch prompts, and the local texts.

    `prompt_template` and `guideline.sha256` must come from the committed
    blobs, not the working tree (line endings differ under core.autocrlf).
    A run covers the pilot reports, the named cases, or every corpus document
    of the selected languages.
    """
    if run_directory.exists():
        raise FileExistsError(f"proposal run {run_id} already exists")
    if pilot and case_ids is not None:
        raise ValueError("the pilot selects its own reports")
    for path in (run_directory, input_directory):
        _display(path, repository_root)
    corpus, documents = read_corpus(store, corpus_manifest_sha256)
    if pilot:
        case_ids = pilot_case_ids(corpus, groups)
    entries = select_run_entries(corpus, languages=languages, case_ids=case_ids)
    german_selected = case_ids is None and (languages is None or "de" in languages)
    run = ProposalRun(
        run_id=run_id,
        run_date=run_date,
        model_id=model_id,
        corpus_manifest_sha256=corpus_manifest_sha256,
        documents_sha256=corpus.documents_sha256,
        hpo_release=hpo_release,
        ontology_sha256=ontology_sha256,
        prompt_sha256=sha256_bytes(prompt_template),
        guideline_path=guideline.path,
        guideline_commit=guideline.commit,
        guideline_sha256=guideline.sha256,
        batches=plan_batches(entries, batch_size=batch_size),
        pending_review=corpus.pending_review if german_selected else (),
    )
    template = prompt_template.decode("utf-8")
    run_directory.mkdir(parents=True)
    (run_directory / "prompt.md").write_bytes(prompt_template)
    (run_directory / "run.json").write_bytes(run.canonical_bytes())
    for batch in run.batches:
        _write_batch_inputs(
            batch=batch,
            run_id=run_id,
            template=template,
            documents=documents,
            repository_root=repository_root,
            run_directory=run_directory,
            input_directory=input_directory,
        )
    return run


def validate_run_directory(
    *, run_directory: Path, store: ArtifactStore, hpo_index: HpoIndex
) -> tuple[ProposalValidationReport, str]:
    """Validate a run's batch outputs and write validation.json.

    Batch files are only read. Returns the report and the SHA-256 of the
    canonical validation.json bytes. An earlier validation.json is removed
    first, so a failed validation never leaves a stale report behind. The
    pinned ontology is read from the store to tell which terms lie under
    Phenotypic abnormality.
    """
    validation_path = run_directory / "validation.json"
    validation_path.unlink(missing_ok=True)
    run_bytes = (run_directory / "run.json").read_bytes()
    run = ProposalRun.model_validate_json(run_bytes, strict=True)
    if sha256_bytes((run_directory / "prompt.md").read_bytes()) != run.prompt_sha256:
        raise ValueError("prompt.md differs from the prompt recorded in run.json")
    corpus, documents = read_corpus(store, run.corpus_manifest_sha256)
    if corpus.documents_sha256 != run.documents_sha256:
        raise ValueError("corpus documents differ from the run")
    outputs = {
        path.stem: path.read_bytes()
        for path in sorted(run_directory.glob("batch-*.json"))
    }
    phenotypic_ids = frozenset(
        entry.hpo_id
        for entry in read_lookup_entries(store.read_bytes(run.ontology_sha256))
        if entry.phenotypic
    )
    report = validate_proposal_run(
        run=run,
        run_sha256=sha256_bytes(run_bytes),
        batch_outputs=outputs,
        documents=documents,
        hpo_index=hpo_index,
        phenotypic_ids=phenotypic_ids,
    )
    payload = report.canonical_bytes()
    validation_path.write_bytes(payload)
    return report, sha256_bytes(payload)
