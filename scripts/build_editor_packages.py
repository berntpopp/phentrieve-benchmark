"""Build ontocurator work packages (v2) from local benchmark data.

Converts benchmark data into ZIPs that the Ontocurator annotation editor
(sibling repository ``../ontocurator``) can import:

* ``e3c``: one package per annotation group (language) of
  ``datasets/e3c-de/proposals/current-proposals.json``. Documents are the
  corpus documents of the group; every validated proposal becomes a tool
  annotation with one evidence mention per occurrence, the guideline R3 axes
  and the verbalization axis. ``--no-proposals`` builds the same documents
  without annotations, for blinded annotation.
* ``gsc``: the RAG-HPO GSC documents with their gold HPO terms. GSC gold has no
  evidence spans, so the annotations are document-level.

ontocurator is deliberately not a dependency of this repository. Run the
script in an overlay environment that adds the editor checkout:

    uv run --with-editable ../ontocurator \
        python scripts/build_editor_packages.py e3c gsc \
        --hp ../phentrieve/data/hp.json

The HPO file must be OBO Graph JSON (the editor cannot read hp.obo). Packages
contain source texts and are written below the git-ignored ``.artifacts``.

Each E3C package gets a text-free build record in
``datasets/e3c-de/editor-packages/``. Its ``manifest_sha256`` is the value an
editor export reports as ``origin_manifest_hash``, so an export leads back to
the proposal index, ontology and guideline commits the package was built
from. The E3C build is deterministic: rebuilding from the same inputs gives
the same hash. A package whose content differs from its committed record is
refused; changed content needs a new ``--package-version``, as the editor
does not replace an imported package under the same ID.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ontocurator.domain.annotations import (
    ActorRef,
    Annotation,
    AnnotationSnapshot,
    Provenance,
    snapshot,
)
from ontocurator.domain.canonical import canonical_hash
from ontocurator.domain.documents import (
    Document as EditorDocument,
)
from ontocurator.domain.documents import (
    EvidenceMention,
    EvidenceRef,
    EvidenceSnapshot,
    Segment,
    snapshot_evidence,
)
from ontocurator.domain.profiles import (
    AnnotationTypeDefinition,
    AxisDefinition,
    LayerDefinition,
    OntologyDefinition,
    TaskProfile,
    profile_hash,
)
from ontocurator.packages.models import PackageManifest, ValidatedPackage
from ontocurator.packages.reader import PackageReader
from ontocurator.packages.writer import PackageWriter

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.annotation import AnnotationSet
from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.hpo_proposal import (
    ProposalRun,
    ProposalValidationReport,
    ValidatedProposal,
)
from phentrieve_benchmark.pipeline.proposals import read_corpus
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / ".artifacts"
E3C_PROPOSALS_DIR = REPO_ROOT / "datasets/e3c-de/proposals"
E3C_PROPOSAL_INDEX = E3C_PROPOSALS_DIR / "current-proposals.json"
E3C_BUILD_RECORD_DIR = REPO_ROOT / "datasets/e3c-de/editor-packages"
DEFAULT_OUTPUT_DIR = ARTIFACT_ROOT / "editor-packages"
HP_RESOURCE_PATH = "ontologies/hp.json"
LAYER_ID = "hpo-layer"
TYPE_ID = "phenotype"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_jsonl(raw: bytes) -> Iterable[dict[str, object]]:
    for line in raw.decode("utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def build_profile(
    hp_sha256: str,
    release: str,
    *,
    profile_id: str,
    axes: dict[str, list[str]],
    required: bool,
) -> TaskProfile:
    """One editable HPO layer; ``required`` enforces all axes and evidence."""
    phenotype = AnnotationTypeDefinition(
        type_id=TYPE_ID,
        label="Phenotype",
        axes=[
            AxisDefinition(
                id=axis_id,
                label=axis_id.capitalize(),
                options=options,
                allow_empty=not required,
            )
            for axis_id, options in axes.items()
        ],
        evidence_policy="required_on_complete" if required else "optional",
    )
    return TaskProfile(
        profile_id=profile_id,
        version="1.0.0",
        preset="hpo-clinical-phenotypes",
        ontologies=[
            OntologyDefinition(
                ontology_id="hp",
                label="Human Phenotype Ontology",
                release=release,
                sha256=hp_sha256,
                format="obo-graph-json",
                resource_path=HP_RESOURCE_PATH,
            )
        ],
        layers=[
            LayerDefinition(
                layer_id=LAYER_ID,
                label="Phenotypes",
                ontology_id="hp",
                access="editable",
                default_visible=True,
                default_type_id=TYPE_ID,
                annotation_types=[phenotype],
            )
        ],
        default_layer_id=LAYER_ID,
    )


# Guideline R3 values plus the verbalization axis (R6); all required.
E3C_AXES = {
    "assertion": ["present", "absent", "uncertain"],
    "experiencer": ["patient", "family_member", "other"],
    "temporality": ["current", "historical"],
    "verbalization": ["verbalized", "not_verbalized"],
}
GSC_AXES = {
    "assertion": ["present", "absent", "uncertain"],
    "experiencer": ["patient", "other"],
    "temporality": ["current", "historical", "future"],
}


class PackageBuilder:
    """Accumulates documents and annotation snapshots for one package."""

    def __init__(self, profile: TaskProfile) -> None:
        self.profile = profile
        self.documents: dict[str, EditorDocument] = {}
        self.annotations: dict[tuple[str, str], AnnotationSnapshot] = {}
        self.evidence: dict[tuple[str, str], EvidenceSnapshot] = {}

    def add_document(
        self, document_id: str, text: str, language: str
    ) -> EditorDocument:
        if document_id in self.documents:
            raise ValueError(f"duplicate document_id: {document_id}")
        document = EditorDocument(
            document_id=document_id,
            text=text,
            language=language,
            text_sha256=_sha256(text.encode("utf-8")),
        )
        self.documents[document_id] = document
        return document

    def add_annotation(
        self,
        document: EditorDocument,
        annotation_id: str,
        term_id: str,
        axes_values: dict[str, str | None],
        spans: list[tuple[int, int]],
        actor: ActorRef,
        method: str,
        source_refs: list[str],
    ) -> None:
        """Add one annotation; every span becomes its own evidence mention."""
        evidence = [
            snapshot_evidence(
                EvidenceMention(
                    evidence_id=f"{annotation_id}:m{number:02d}",
                    segments=[Segment(start=start, end=end)],
                ),
                document,
            )
            for number, (start, end) in enumerate(spans, start=1)
        ]
        annotation = Annotation(
            annotation_id=annotation_id,
            document_id=document.document_id,
            layer_id=LAYER_ID,
            type_id=TYPE_ID,
            term_id=term_id,
            axes_values=axes_values,
            evidence_refs=[
                EvidenceRef(evidence_id=e.mention.evidence_id, version=e.version)
                for e in evidence
            ],
            provenance=Provenance(actor=actor, method=method, source_refs=source_refs),
        )
        snap = snapshot(annotation, evidence, document, self.profile)
        self.annotations[(annotation_id, snap.version)] = snap
        for item in evidence:
            self.evidence[(item.mention.evidence_id, item.version)] = item

    def write(
        self, package_id: str, hp_raw: bytes, output: Path, created_at: str
    ) -> str:
        """Write the package and return its canonical manifest hash."""
        package = ValidatedPackage(
            manifest=PackageManifest(
                package_id=package_id,
                format_version="ontocurator-work-package/v2",
                document_order=list(self.documents),
                task_profile=self.profile,
                task_profile_sha256=profile_hash(self.profile),
                created_at=created_at,
            ),
            documents=self.documents,
            annotations=self.annotations,
            evidence=self.evidence,
            embedded_files={HP_RESOURCE_PATH: hp_raw},
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("wb") as stream:
            PackageWriter.write_to_stream(package, stream)
        # The editor hashes the manifest as stored, including the file hashes
        # the writer adds; an export reports this as origin_manifest_hash.
        written = PackageReader().read(output)
        manifest_hash: str = canonical_hash(written.manifest.model_dump())
        return manifest_hash


def _load_documents(store: ArtifactStore, digest: str) -> list[Document]:
    return [Document.model_validate(r) for r in _read_jsonl(store.read_bytes(digest))]


def _add_e3c_proposal(
    builder: PackageBuilder,
    document: EditorDocument,
    entry: dict[str, Any],
    proposal: ValidatedProposal,
) -> None:
    run_id, case_id = entry["run_id"], entry["source_case_id"]
    annotation_id = f"{run_id}:{case_id}:{proposal.proposal_id}"
    for mention in proposal.mentions:
        if document.text[mention.start : mention.end] != mention.phrase:
            raise SystemExit(f"span does not match its phrase in {annotation_id}")
    model_id = next(s["model_id"] for s in reversed(entry["steps"]) if s["model_id"])
    builder.add_annotation(
        document,
        annotation_id=annotation_id,
        term_id=proposal.hpo_id,
        axes_values={
            "assertion": proposal.assertion,
            "experiencer": proposal.experiencer,
            "temporality": proposal.temporality,
            "verbalization": "verbalized" if proposal.verbalized else "not_verbalized",
        },
        spans=[(mention.start, mention.end) for mention in proposal.mentions],
        actor=ActorRef(actor_id=f"phentrieve-benchmark/{model_id}", kind="tool"),
        method="+".join(step["step"] for step in entry["steps"]),
        # Raw proposal IDs restart in every report, so the case is part of
        # the reference: run/batch/case/proposal.
        source_refs=[
            f"{run_id}/{entry['batch_id']}/{case_id}/{source_id}"
            for source_id in proposal.source_proposal_ids
        ],
    )


def build_e3c_group(
    builder: PackageBuilder,
    store: ArtifactStore,
    entries: list[dict[str, Any]],
    *,
    with_proposals: bool,
    stats: Counter[str],
) -> dict[str, list[str]]:
    """Fill ``builder`` with one annotation group; return what it was built from."""
    runs: dict[str, tuple[ProposalRun, ProposalValidationReport]] = {}
    corpora: dict[str, dict[str, Document]] = {}
    for entry in entries:
        run_id = entry["run_id"]
        if run_id not in runs:
            run_dir = E3C_PROPOSALS_DIR / run_id
            run = ProposalRun.model_validate_json(
                (run_dir / "run.json").read_bytes(), strict=True
            )
            report = ProposalValidationReport.model_validate_json(
                (run_dir / "validation.json").read_bytes(), strict=True
            )
            runs[run_id] = (run, report)
            if run.corpus_manifest_sha256 not in corpora:
                corpora[run.corpus_manifest_sha256] = read_corpus(
                    store, run.corpus_manifest_sha256
                )[1]
        run, report = runs[run_id]
        source = corpora[run.corpus_manifest_sha256][entry["document_id"]]
        if source.document_sha256 != entry["document_sha256"]:
            raise SystemExit(f"corpus text hash mismatch for {source.document_id}")
        document = builder.add_document(
            source.document_id, source.text, source.language
        )
        stats["documents"] += 1
        if not with_proposals:
            continue
        validated = next(
            d for d in report.documents if d.document_id == source.document_id
        )
        for proposal in validated.proposals:
            _add_e3c_proposal(builder, document, entry, proposal)
            stats["proposals"] += 1
            stats["mentions"] += len(proposal.mentions)
            stats["proposals with notes (not exported)"] += bool(proposal.notes)
    return {
        "runs": sorted(runs),
        "corpus_manifest_sha256": sorted(corpora),
        "guideline_commits": sorted(
            {
                step["guideline_commit"]
                for entry in entries
                for step in entry["steps"]
                if step.get("guideline_commit")
            }
        ),
    }


def build_e3c(args: argparse.Namespace, hp_raw: bytes, store: ArtifactStore) -> None:
    index_raw = E3C_PROPOSAL_INDEX.read_bytes()
    documents: list[dict[str, Any]] = json.loads(index_raw)["documents"]
    languages = sorted({d["annotation_language"] for d in documents})
    if args.language:
        languages = [args.language]
    profile = build_profile(
        _sha256(hp_raw),
        args.hp_release,
        profile_id="hpo-span-annotation/v1",
        axes=E3C_AXES,
        required=True,
    )
    kind = "blind" if args.no_proposals else "proposals"
    for language in languages:
        entries = [d for d in documents if d["annotation_language"] == language]
        if not entries:
            raise SystemExit(f"no reports for annotation language {language}")
        if args.limit:
            entries = entries[: args.limit]
        stats: Counter[str] = Counter()
        builder = PackageBuilder(profile)
        sources = build_e3c_group(
            builder, store, entries, with_proposals=not args.no_proposals, stats=stats
        )
        name = f"e3c-{language}-{kind}-{args.package_version}"
        if args.limit:
            name += f"-first{args.limit}"
        package_id = f"phentrieve-benchmark-{name}"
        # Fixed so that a rebuild gives the same manifest hash: the date of
        # the newest proposal step of the group.
        newest = max(
            s["run_date"] for e in entries for s in e["steps"] if "run_date" in s
        )
        created_at = f"{newest}T00:00:00Z"
        output = args.output_dir / f"editor-{name}.zip"
        manifest_hash = builder.write(package_id, hp_raw, output, created_at)
        print(f"{output} ({output.stat().st_size} bytes)")
        for key, value in sorted(stats.items()):
            print(f"  {key}: {value}")
        if args.limit:
            print("  test package (--limit): no build record written")
            continue
        record = {
            "schema_version": "e3c-editor-package-build/v1",
            "package_id": package_id,
            "format_version": "ontocurator-work-package/v2",
            "manifest_sha256": manifest_hash,
            "created_at": created_at,
            "annotation_language": language,
            "with_proposals": not args.no_proposals,
            "documents": stats["documents"],
            "proposals": stats["proposals"],
            "mentions": stats["mentions"],
            "proposal_index": {
                "path": E3C_PROPOSAL_INDEX.relative_to(REPO_ROOT).as_posix(),
                "sha256": _sha256(index_raw),
            },
            "task_profile": {
                "profile_id": profile.profile_id,
                "sha256": profile_hash(profile),
            },
            "ontology": {"release": args.hp_release, "sha256": _sha256(hp_raw)},
            **sources,
        }
        record_path = E3C_BUILD_RECORD_DIR / f"{package_id}.json"
        if record_path.is_file():
            committed = json.loads(record_path.read_bytes())["manifest_sha256"]
            if committed != manifest_hash:
                raise SystemExit(
                    f"{package_id}: content differs from its build record "
                    f"{record_path.name}; pass a new --package-version"
                )
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_bytes(canonical_json_bytes(record) + b"\n")
        print(f"  build record: {record_path.relative_to(REPO_ROOT).as_posix()}")
        print(f"  manifest_sha256: {manifest_hash}")


def _latest_normalization_manifest(target: str) -> str:
    pointers = sorted(
        (ARTIFACT_ROOT / "state/normalize" / target).glob("*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    if not pointers:
        raise SystemExit(f"no normalization state for {target}; run prepare first")
    subject: str = json.loads(pointers[-1].read_text(encoding="utf-8"))[
        "subject_sha256"
    ]
    return subject


def build_gsc(
    builder: PackageBuilder,
    store: ArtifactStore,
    stats: Counter[str],
    manifest_sha256: str | None,
) -> None:
    manifest = json.loads(
        store.read_bytes(manifest_sha256 or _latest_normalization_manifest("gsc"))
    )
    documents = _load_documents(store, manifest["documents"]["sha256"])
    sets = {
        s.document_sha256: s
        for s in (
            AnnotationSet.model_validate(r)
            for r in _read_jsonl(store.read_bytes(manifest["annotations"]["sha256"]))
        )
    }
    actor = ActorRef(actor_id="raghpo-gsc-curators", kind="human")
    for source in documents:
        document = builder.add_document(
            source.document_id, source.text, source.language
        )
        annotation_set = sets.get(source.document_sha256)
        if annotation_set is None:
            stats["gsc documents without annotation set"] += 1
            continue
        for gold in annotation_set.annotations:
            spans = [(e.start_char, e.end_char) for e in gold.evidence_spans]
            builder.add_annotation(
                document,
                annotation_id=gold.annotation_id,
                term_id=gold.hpo_id,
                axes_values={
                    "assertion": gold.assertion,
                    "experiencer": gold.experiencer,
                    "temporality": gold.temporality,
                },
                spans=spans,
                actor=actor,
                method="curated-gold",
                source_refs=[annotation_set.annotation_set_id],
            )
            stats["gsc gold annotations"] += 1
            stats["gsc gold annotations without span"] += not spans


def build_gsc_package(
    args: argparse.Namespace, hp_raw: bytes, store: ArtifactStore
) -> None:
    stats: Counter[str] = Counter()
    profile = build_profile(
        _sha256(hp_raw),
        args.hp_release,
        profile_id="hpo-clinical-phenotypes/v1",
        axes=GSC_AXES,
        required=False,
    )
    builder = PackageBuilder(profile)
    build_gsc(builder, store, stats, args.gsc_manifest)
    output = args.output_dir / "editor-gsc-v2.zip"
    created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    builder.write("phentrieve-benchmark-gsc", hp_raw, output, created_at)
    print(f"{output} ({output.stat().st_size} bytes)")
    print(f"  documents: {len(builder.documents)}")
    for key, value in sorted(stats.items()):
        print(f"  {key}: {value}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("datasets", nargs="+", choices=["e3c", "gsc"])
    parser.add_argument(
        "--hp", type=Path, required=True, help="HPO release as OBO Graph JSON"
    )
    parser.add_argument("--hp-release", default="2026-06-23")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--gsc-manifest",
        help="sha256 of the GSC normalization manifest (default: newest)",
    )
    e3c = parser.add_argument_group("e3c")
    e3c.add_argument(
        "--language", help="only this annotation group (default: one package each)"
    )
    e3c.add_argument(
        "--no-proposals", action="store_true", help="documents only, for blinded work"
    )
    e3c.add_argument(
        "--package-version",
        default="v1",
        help="part of the package ID; raise it when the content changes",
    )
    e3c.add_argument(
        "--limit", type=int, help="first N reports per group; test packages only"
    )
    args = parser.parse_args(argv)

    hp_raw = args.hp.read_bytes().replace(b"\r\n", b"\n")
    if args.hp_release not in hp_raw[:4096].decode("utf-8", errors="replace"):
        raise SystemExit(f"{args.hp} does not look like HPO release {args.hp_release}")
    store = ArtifactStore(ARTIFACT_ROOT / "objects")

    for dataset in args.datasets:
        if dataset == "e3c":
            build_e3c(args, hp_raw, store)
        else:
            build_gsc_package(args, hp_raw, store)


if __name__ == "__main__":
    main()
