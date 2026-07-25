from phentrieve_benchmark.models.pipeline import (
    ProvenanceRunLink,
    ProvenanceSubjectRole,
)


def test_curated_review_and_single_term_artifacts_have_run_link_roles() -> None:
    expected = {
        ProvenanceSubjectRole.CURATED_ANNOTATION_SET: "curated_annotation_set",
        ProvenanceSubjectRole.REVIEW_DECISION_SET: "review_decision_set",
        ProvenanceSubjectRole.SINGLE_TERM_SELECTION: "single_term_selection",
        ProvenanceSubjectRole.SINGLE_TERM_SET: "single_term_set",
    }

    for role, serialized in expected.items():
        link = ProvenanceRunLink(
            subject_role=role,
            subject_sha256="a" * 64,
            run_manifest_sha256="b" * 64,
        )
        assert link.model_dump(mode="json")["subject_role"] == serialized
        assert ProvenanceRunLink.model_validate_json(
            link.canonical_bytes()
        ) == link
