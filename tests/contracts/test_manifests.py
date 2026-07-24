import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.models.annotation import AnnotationSet
from phentrieve_benchmark.models.manifest import (
    ProviderRunIdentity,
    ReleaseManifest,
    ReleaseRunLink,
    RunManifest,
    RunStatus,
    UsageMetrics,
)


def release_manifest() -> ReleaseManifest:
    return ReleaseManifest(
        dataset_id="synthetic",
        dataset_version="1.0.0",
        hpo_release="v2026-06-23",
        source_sha256="a" * 64,
        input_sha256="b" * 64,
        gold_sha256="c" * 64,
        document_ids_sha256="d" * 64,
        selection_id="synthetic-v1",
        licensing_identity="synthetic-license-v1",
        review_policy_id="synthetic-review-v1",
        bilingual_review_coverage=0.2,
        physician_review_coverage=0.1,
    )


def run_manifest(**updates: object) -> RunManifest:
    values: dict[str, object] = {
        "run_id": "run-1",
        "stage": "normalize",
        "status": RunStatus.COMPLETE,
        "started_at": datetime(2026, 7, 23, tzinfo=UTC),
        "finished_at": datetime(2026, 7, 23, 0, 1, tzinfo=UTC),
        "pipeline_commit": "a" * 40,
        "dirty_state": True,
        "code_sha256": "a" * 64,
        "config_sha256": "d" * 64,
        "provider": ProviderRunIdentity(
            provider="openai",
            engine="responses",
            requested_model="gpt-5.6-terra",
            returned_model="gpt-5.6-terra-2026-07-21",
            endpoint_class="standard",
            processing_mode="synchronous",
        ),
        "pricing_snapshot_id": "openai-2026-07-23",
        "usage": UsageMetrics(input_tokens=100, output_tokens=20, estimated_cost=0.01),
        "input_sha256": ("b" * 64,),
        "output_sha256": ("c" * 64,),
    }
    values.update(updates)
    return RunManifest(**values)


def test_release_bytes_ignore_execution_identity() -> None:
    release = release_manifest()
    first = ReleaseRunLink(
        release_sha256=release.sha256(),
        run_manifest_sha256=("e" * 64,),
    )
    second = ReleaseRunLink(
        release_sha256=release.sha256(),
        run_manifest_sha256=("f" * 64,),
    )

    assert release.canonical_bytes() == release.canonical_bytes()
    assert first != second
    assert first.release_sha256 == second.release_sha256


def test_run_manifest_retains_volatile_execution_fields() -> None:
    run = run_manifest()

    assert run.run_id == "run-1"
    assert run.started_at != run.finished_at
    assert run.provider is not None
    assert run.provider.returned_model == "gpt-5.6-terra-2026-07-21"


def test_complete_run_requires_finished_at_for_direct_construction() -> None:
    with pytest.raises(ValueError, match="complete run requires finished_at"):
        run_manifest(finished_at=None)


def test_complete_run_requires_finished_at_for_json_validation() -> None:
    payload = run_manifest().model_dump(mode="json")
    payload["finished_at"] = None

    with pytest.raises(ValueError, match="complete run requires finished_at"):
        RunManifest.model_validate_json(json.dumps(payload))


def test_run_rejects_finished_time_before_start() -> None:
    with pytest.raises(ValueError, match="finished_at cannot precede started_at"):
        run_manifest(finished_at=datetime(2026, 7, 22, tzinfo=UTC))


def test_release_rejects_volatile_execution_fields() -> None:
    with pytest.raises(ValidationError, match="run_id"):
        ReleaseManifest(**release_manifest().model_dump(), run_id="run-1")


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            AnnotationSet,
            {
                "annotation_set_id": "annotations-1",
                "document_sha256": "a" * 64,
                "hpo_release": "v\u0662\u0660\u0662\u0666-\u0660\u0666-\u0662\u0663",
                "annotations": [],
            },
        ),
        (
            ReleaseManifest,
            {
                **release_manifest().model_dump(mode="json"),
                "hpo_release": "v\u0662\u0660\u0662\u0666-\u0660\u0666-\u0662\u0663",
            },
        ),
    ],
)
def test_hpo_release_rejects_unicode_digits_in_direct_and_json_validation(
    model: type[AnnotationSet] | type[ReleaseManifest], payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError, match="hpo_release"):
        model(**payload)
    with pytest.raises(ValidationError, match="hpo_release"):
        model.model_validate_json(json.dumps(payload))
