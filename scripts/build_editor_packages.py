"""Build ontocurator work packages (v2) from local benchmark data.

Converts benchmark data into ZIPs that the Ontocurator annotation editor
(sibling repository ``../ontocurator``) can import:

* ``e3c``: the 30 E3C feasibility cases. English source texts carry the
  UMLS->HPO mapping candidates as tool proposals with evidence spans; the
  German TLLM review translations are added as unannotated documents.
* ``gsc``: the RAG-HPO GSC documents with their gold HPO terms. GSC gold has no
  evidence spans, so the annotations are document-level.

ontocurator is deliberately not a dependency of this repository. Run the
script in an overlay environment that adds the editor checkout:

    uv run --with-editable ../ontocurator \
        python scripts/build_editor_packages.py e3c gsc \
        --hp ../phentrieve/data/hp.json

The HPO file must be OBO Graph JSON (the editor cannot read hp.obo). Packages
contain source texts and are written below the git-ignored ``.artifacts``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from ontocurator.domain.annotations import (
    ActorRef,
    Annotation,
    AnnotationSnapshot,
    Provenance,
    snapshot,
)
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
from ontocurator.packages.writer import PackageWriter

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.annotation import AnnotationSet
from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.mapping import (
    MappingClassification,
    UmlsHpoMappingManifest,
    UmlsHpoMappingRecord,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / ".artifacts"
E3C_MAPPING = (
    REPO_ROOT
    / "datasets/e3c-de/mappings/e3c-feasibility-30-umls-hpo-v2026-06-23-v1.json"
)
E3C_REVIEW_DIR = REPO_ROOT / "datasets/e3c-de/review/e3c-de-feasibility-30-v1"
DEFAULT_OUTPUT_DIR = ARTIFACT_ROOT / "editor-packages"
HP_RESOURCE_PATH = "ontologies/hp.json"
LAYER_ID = "hpo-layer"
TYPE_ID = "phenotype"
PROPOSABLE = {MappingClassification.UNIQUE_ACTIVE, MappingClassification.AMBIGUOUS}


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_jsonl(raw: bytes) -> Iterable[dict[str, object]]:
    for line in raw.decode("utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def build_profile(hp_sha256: str, release: str) -> TaskProfile:
    def axis(axis_id: str, options: list[str]) -> AxisDefinition:
        return AxisDefinition(
            id=axis_id, label=axis_id.capitalize(), options=options, allow_empty=True
        )

    phenotype = AnnotationTypeDefinition(
        type_id=TYPE_ID,
        label="Phenotype",
        axes=[
            axis("assertion", ["present", "absent", "uncertain"]),
            axis("experiencer", ["patient", "other"]),
            axis("temporality", ["current", "historical", "future"]),
        ],
        evidence_policy="optional",
    )
    return TaskProfile(
        profile_id="hpo-clinical-phenotypes/v1",
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
        evidence: list[EvidenceSnapshot] = []
        if spans:
            mention = EvidenceMention(
                evidence_id=f"{annotation_id}:evidence",
                segments=[Segment(start=start, end=end) for start, end in spans],
            )
            evidence.append(snapshot_evidence(mention, document))
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

    def write(self, package_id: str, hp_raw: bytes, output: Path) -> None:
        package = ValidatedPackage(
            manifest=PackageManifest(
                package_id=package_id,
                format_version="ontocurator-work-package/v2",
                document_order=list(self.documents),
                task_profile=self.profile,
                task_profile_sha256=profile_hash(self.profile),
                created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
            documents=self.documents,
            annotations=self.annotations,
            evidence=self.evidence,
            embedded_files={HP_RESOURCE_PATH: hp_raw},
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("wb") as stream:
            PackageWriter.write_to_stream(package, stream)


def _load_documents(store: ArtifactStore, digest: str) -> list[Document]:
    return [Document.model_validate(r) for r in _read_jsonl(store.read_bytes(digest))]


def build_e3c(
    builder: PackageBuilder, store: ArtifactStore, stats: Counter[str]
) -> None:
    manifest = UmlsHpoMappingManifest.model_validate_json(E3C_MAPPING.read_bytes())
    cases = set(manifest.population_case_ids)
    sources = {
        d.source_case_id: d
        for d in _load_documents(store, manifest.documents_sha256)
        if d.source_case_id in cases and d.translation_status == "native"
    }
    missing = cases - sources.keys()
    if missing:
        raise SystemExit(f"E3C source documents not found: {sorted(missing)}")

    records_by_case: dict[str, list[UmlsHpoMappingRecord]] = {}
    for record in manifest.records:
        records_by_case.setdefault(record.source_case_id, []).append(record)

    actor = ActorRef(actor_id="phentrieve-benchmark/hpo-umls-xref", kind="tool")
    for case_id in sorted(cases):
        source = sources[case_id]
        document = builder.add_document(
            source.document_id, source.text, source.language
        )
        for record in records_by_case.get(case_id, []):
            stats[f"e3c records {record.classification.value}"] += 1
            if record.classification not in PROPOSABLE:
                continue
            if record.source_document_sha256 != source.document_sha256:
                raise SystemExit(f"text hash mismatch for {record.mapping_record_id}")
            for evidence in record.evidence:
                snippet = source.text[evidence.start_char : evidence.end_char]
                if _sha256(snippet.encode("utf-8")) != evidence.text_sha256:
                    stats["e3c evidence snippet hash mismatch"] += 1
            spans = [(e.start_char, e.end_char) for e in record.evidence]
            for index, candidate in enumerate(record.candidates):
                builder.add_annotation(
                    document,
                    annotation_id=f"{record.mapping_record_id}:{index:02d}",
                    term_id=candidate.hpo_id,
                    axes_values={"assertion": None},
                    spans=spans,
                    actor=actor,
                    method=record.mapping_method,
                    source_refs=[record.mapping_record_id],
                )
                stats["e3c proposals"] += 1

        translation = E3C_REVIEW_DIR / case_id / "tllm.de.txt"
        if translation.is_file():
            text = translation.read_text(encoding="utf-8").replace("\r\n", "\n")
            builder.add_document(f"{source.document_id}:review-tllm-de", text, "de")
            stats["e3c german translations"] += 1


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
    args = parser.parse_args(argv)

    hp_raw = args.hp.read_bytes().replace(b"\r\n", b"\n")
    if args.hp_release not in hp_raw[:4096].decode("utf-8", errors="replace"):
        raise SystemExit(f"{args.hp} does not look like HPO release {args.hp_release}")
    store = ArtifactStore(ARTIFACT_ROOT / "objects")

    for dataset in args.datasets:
        stats: Counter[str] = Counter()
        builder = PackageBuilder(build_profile(_sha256(hp_raw), args.hp_release))
        if dataset == "e3c":
            build_e3c(builder, store, stats)
        else:
            build_gsc(builder, store, stats, args.gsc_manifest)
        output = args.output_dir / f"editor-{dataset}-v2.zip"
        builder.write(f"phentrieve-benchmark-{dataset}", hp_raw, output)
        print(f"{output} ({output.stat().st_size} bytes)")
        print(f"  documents: {len(builder.documents)}")
        for key, value in sorted(stats.items()):
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
