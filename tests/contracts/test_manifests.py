import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

import phentrieve_benchmark.models as benchmark_models
from phentrieve_benchmark.models.annotation import AnnotationSet
from phentrieve_benchmark.models.manifest import (
    ProviderRunIdentity,
    ReleaseManifest,
    ReleaseRunLink,
    RunManifest,
    RunStatus,
    UsageMetrics,
)
from phentrieve_benchmark.provenance.digests import ComponentDigest


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


def test_models_package_exports_manifest_contracts() -> None:
    expected = {
        "ProviderRunIdentity",
        "ReleaseManifest",
        "ReleaseRunLink",
        "RunManifest",
        "RunStatus",
        "UsageMetrics",
    }

    assert expected <= set(benchmark_models.__all__)


def test_usage_metrics_default_cost_is_a_float_in_direct_and_json_models() -> None:
    direct = UsageMetrics()
    parsed = UsageMetrics.model_validate_json("{}")

    assert type(direct.estimated_cost) is float
    assert type(parsed.estimated_cost) is float


def test_release_canonical_bytes_and_hash_are_stable_fixture() -> None:
    release = ReleaseManifest(
        physician_review_coverage=0.1,
        review_policy_id="synthetic-review-v1",
        licensing_identity="synthetic-license-v1",
        selection_id="synthetic-v1",
        document_ids_sha256="d" * 64,
        gold_sha256="c" * 64,
        input_sha256="b" * 64,
        source_sha256="a" * 64,
        hpo_release="v2026-06-23",
        dataset_version="1.0.0",
        dataset_id="synthetic",
        bilingual_review_coverage=0.2,
    )

    assert release.canonical_bytes() == (
        b'{"bilingual_review_coverage":0.2,"dataset_id":"synthetic",'
        b'"dataset_version":"1.0.0","document_ids_sha256":"'
        + b"d" * 64
        + b'","gold_sha256":"'
        + b"c" * 64
        + b'","hpo_release":"v2026-06-23","input_sha256":"'
        + b"b" * 64
        + b'","licensing_identity":"synthetic-license-v1",'
        b'"physician_review_coverage":0.1,'
        b'"review_policy_id":"synthetic-review-v1",'
        b'"schema_version":"release-manifest/v1",'
        b'"selection_id":"synthetic-v1","source_sha256":"'
        + b"a" * 64
        + b'"}'
    )
    assert release.sha256() == (
        "d4b2375e418aae71f2403d13887f138c3d7470ac5925a9630b750ae70af7e4f8"
    )


def test_release_run_link_separates_execution_identity() -> None:
    release = release_manifest()
    first = ReleaseRunLink(
        release_sha256=release.sha256(),
        run_manifest_sha256=("f" * 64, "e" * 64),
    )
    second = ReleaseRunLink(
        release_sha256=release.sha256(),
        run_manifest_sha256=("e" * 64, "f" * 64),
    )
    third = ReleaseRunLink(
        release_sha256=release.sha256(),
        run_manifest_sha256=("d" * 64,),
    )

    assert first == second
    assert first.run_manifest_sha256 == ("e" * 64, "f" * 64)
    assert first != third
    assert first.release_sha256 == third.release_sha256 == release.sha256()


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


def test_equal_timestamps_and_unfinished_noncomplete_runs_are_valid() -> None:
    timestamp = datetime(2026, 7, 23, tzinfo=UTC)

    complete = run_manifest(started_at=timestamp, finished_at=timestamp)
    incomplete = run_manifest(status=RunStatus.INCOMPLETE, finished_at=None)
    failed = run_manifest(status=RunStatus.FAILED, finished_at=None)

    assert complete.finished_at == timestamp
    assert incomplete.finished_at is None
    assert failed.finished_at is None


def test_release_rejects_volatile_execution_fields() -> None:
    with pytest.raises(ValidationError, match="run_id"):
        ReleaseManifest(**release_manifest().model_dump(), run_id="run-1")


@pytest.mark.parametrize("coverage", [0.0, 1.0])
def test_release_accepts_coverage_boundaries(coverage: float) -> None:
    release = ReleaseManifest(
        **{
            **release_manifest().model_dump(),
            "bilingual_review_coverage": coverage,
            "physician_review_coverage": coverage,
        }
    )

    assert release.bilingual_review_coverage == coverage
    assert release.physician_review_coverage == coverage


@pytest.mark.parametrize("coverage", [-0.01, 1.01])
def test_release_rejects_coverage_outside_boundaries(coverage: float) -> None:
    with pytest.raises(ValidationError):
        ReleaseManifest(
            **{
                **release_manifest().model_dump(),
                "bilingual_review_coverage": coverage,
            }
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_usage_metrics_rejects_nonfinite_cost_direct_and_json(value: float) -> None:
    with pytest.raises(ValidationError, match="estimated_cost"):
        UsageMetrics(estimated_cost=value)
    with pytest.raises(ValidationError, match="estimated_cost"):
        UsageMetrics.model_validate_json(json.dumps({"estimated_cost": value}))


def test_usage_metrics_has_a_finite_json_round_trip() -> None:
    usage = UsageMetrics(input_tokens=100, output_tokens=20, estimated_cost=0.01)

    round_tripped = UsageMetrics.model_validate_json(json.dumps(usage.model_dump()))

    assert round_tripped == usage


@pytest.mark.parametrize(
    ("model", "direct_payload", "json_payload"),
    [
        (
            RunManifest,
            {"dirty_state": 1},
            {"dirty_state": 1},
        ),
        (
            UsageMetrics,
            {"input_tokens": True},
            {"input_tokens": "100"},
        ),
        (
            ReleaseManifest,
            {"bilingual_review_coverage": True},
            {"bilingual_review_coverage": "0.2"},
        ),
        (
            RunManifest,
            {"started_at": 1_785_000_000},
            {"started_at": 1_785_000_000},
        ),
        (
            RunManifest,
            {"retry_count": True},
            {"retry_count": True},
        ),
    ],
)
def test_persisted_models_reject_coercive_scalars_direct_and_json(
    model: type[RunManifest] | type[UsageMetrics] | type[ReleaseManifest],
    direct_payload: dict[str, object],
    json_payload: dict[str, object],
) -> None:
    if model is RunManifest:
        direct_values = run_manifest().model_dump()
        json_values = run_manifest().model_dump(mode="json")
    elif model is UsageMetrics:
        direct_values = UsageMetrics().model_dump()
        json_values = UsageMetrics().model_dump(mode="json")
    else:
        direct_values = release_manifest().model_dump()
        json_values = release_manifest().model_dump(mode="json")
    direct_values.update(direct_payload)
    json_values.update(json_payload)

    with pytest.raises(ValidationError):
        model(**direct_values)
    with pytest.raises(ValidationError):
        model.model_validate_json(json.dumps(json_values))


def test_json_validation_accepts_iso_aware_timestamps() -> None:
    payload = run_manifest().model_dump(mode="json")

    validated = RunManifest.model_validate_json(json.dumps(payload))

    assert validated.started_at == datetime(2026, 7, 23, tzinfo=UTC)


def test_nested_component_digest_rejects_coercive_scalars() -> None:
    source = {"role": 1, "stable_id": "case-1", "sha256": "a" * 64}

    with pytest.raises(ValidationError):
        run_manifest(source=(source,))
    payload = run_manifest().model_dump(mode="json")
    payload["source"] = [source]
    with pytest.raises(ValidationError):
        RunManifest.model_validate_json(json.dumps(payload))


def test_set_like_run_collections_are_normalized_and_sorted() -> None:
    source_first = ComponentDigest(
        role="source", stable_id="cafe\u0301", sha256="a" * 64
    )
    source_second = ComponentDigest(role="source", stable_id="alpha", sha256="b" * 64)
    environment_first = ComponentDigest(
        role="python", stable_id="3.12", sha256="c" * 64
    )
    environment_second = ComponentDigest(
        role="platform", stable_id="windows", sha256="d" * 64
    )
    first = run_manifest(
        source=(source_first, source_second),
        environment=(environment_first, environment_second),
        input_sha256=("e" * 64, "a" * 64),
        output_sha256=("f" * 64, "b" * 64),
        error_codes=("zeta", "alpha"),
    )
    second = run_manifest(
        source=(source_second, source_first),
        environment=(environment_second, environment_first),
        input_sha256=("a" * 64, "e" * 64),
        output_sha256=("b" * 64, "f" * 64),
        error_codes=("alpha", "zeta"),
    )

    assert first == second
    assert first.source[1].stable_id == "café"
    assert first.environment[0].role == "platform"
    assert first.input_sha256 == ("a" * 64, "e" * 64)
    assert first.output_sha256 == ("b" * 64, "f" * 64)
    assert first.error_codes == ("alpha", "zeta")


@pytest.mark.parametrize(
    "updates",
    [
        {
            "source": (
                ComponentDigest(role="source", stable_id="café", sha256="a" * 64),
                ComponentDigest(
                    role="source", stable_id="cafe\u0301", sha256="b" * 64
                ),
            )
        },
        {
            "environment": (
                ComponentDigest(role="python", stable_id="3.12", sha256="a" * 64),
            )
            * 2
        },
        {"input_sha256": ("a" * 64,) * 2},
        {"output_sha256": ("a" * 64,) * 2},
        {"error_codes": ("retry", "retry")},
    ],
)
def test_run_rejects_duplicate_set_like_collections(updates: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="duplicate"):
        run_manifest(**updates)


def test_release_run_link_sorts_and_rejects_duplicate_contributing_runs() -> None:
    first = ReleaseRunLink(
        release_sha256="a" * 64,
        run_manifest_sha256=("c" * 64, "b" * 64),
    )
    second = ReleaseRunLink(
        release_sha256="a" * 64,
        run_manifest_sha256=("b" * 64, "c" * 64),
    )

    assert first == second
    assert first.run_manifest_sha256 == ("b" * 64, "c" * 64)
    with pytest.raises(ValueError, match="duplicate"):
        ReleaseRunLink(
            release_sha256="a" * 64,
            run_manifest_sha256=("b" * 64, "b" * 64),
        )


@pytest.mark.parametrize(
    ("model", "factory", "schema_version"),
    [
        (RunManifest, run_manifest, "run-manifest/v1"),
        (ReleaseManifest, release_manifest, "release-manifest/v1"),
        (
            ReleaseRunLink,
            lambda: ReleaseRunLink(
                release_sha256="a" * 64, run_manifest_sha256=("b" * 64,)
            ),
            "release-run-link/v1",
        ),
    ],
)
def test_manifest_schema_versions_are_literal_and_persisted(
    model: type[RunManifest] | type[ReleaseManifest] | type[ReleaseRunLink],
    factory: object,
    schema_version: str,
) -> None:
    instance = factory()  # type: ignore[operator]
    payload = instance.model_dump(mode="json")

    assert payload["schema_version"] == schema_version
    payload["schema_version"] = "unsupported/v1"
    with pytest.raises(ValidationError, match="schema_version"):
        model(**{**instance.model_dump(), "schema_version": "unsupported/v1"})
    with pytest.raises(ValidationError, match="schema_version"):
        model.model_validate_json(json.dumps(payload))


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


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            AnnotationSet,
            {
                "annotation_set_id": "annotations-1",
                "document_sha256": "a" * 64,
                "hpo_release": "v2026-02-30",
                "annotations": [],
            },
        ),
        (
            ReleaseManifest,
            {
                **release_manifest().model_dump(mode="json"),
                "hpo_release": "v2026-02-30",
            },
        ),
    ],
)
def test_hpo_release_rejects_impossible_calendar_dates_direct_and_json(
    model: type[AnnotationSet] | type[ReleaseManifest], payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError, match="hpo_release"):
        model(**payload)
    with pytest.raises(ValidationError, match="hpo_release"):
        model.model_validate_json(json.dumps(payload))
