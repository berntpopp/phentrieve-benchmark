from hashlib import sha256
from pathlib import Path

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.ontology.hpo import HpoSourceRecipe
from phentrieve_benchmark.pipeline.map_hpo import load_or_acquire_hpo


def test_hpo_acquisition_reuses_verified_local_source_lock(
    tmp_path: Path,
) -> None:
    body = b"format-version: 1.4\nontology: hp\n"
    source_locks = tmp_path / "source-locks"
    source_locks.mkdir()
    (source_locks / "hp-v2026-06-23.obo").write_bytes(body)
    recipe = HpoSourceRecipe(
        release="v2026-06-23",
        url=(
            "https://github.com/obophenotype/human-phenotype-ontology/"
            "releases/download/v2026-06-23/hp.obo"
        ),
        expected_byte_length=len(body),
        maximum_byte_length=100,
        sha256=sha256(body).hexdigest(),
        format="obo-1.4",
        parser="pronto-2",
    )
    store = ArtifactStore(tmp_path / "objects")

    digest = load_or_acquire_hpo(
        recipe,
        artifact_root=tmp_path,
        store=store,
        downloader=lambda _recipe: (_ for _ in ()).throw(
            AssertionError("network must not be used")
        ),
    )

    assert digest == recipe.sha256
    assert store.read_bytes(digest) == body

