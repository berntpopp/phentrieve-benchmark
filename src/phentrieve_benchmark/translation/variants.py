from pathlib import Path

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.pipeline import ProvenanceSubjectRole
from phentrieve_benchmark.models.translation import TranslationManifest
from phentrieve_benchmark.pipeline.state import StagePointer

TRANSLATION_VARIANTS: dict[str, str] = {
    "nmt": "translation.yaml",
    "tllm": "translation-llm.yaml",
}


def _recipe_filename(variant: str) -> str:
    try:
        return TRANSLATION_VARIANTS[variant]
    except KeyError:
        raise ValueError(f"unknown translation variant: {variant}") from None


def translation_recipe_path(dataset_root: Path, variant: str) -> Path:
    return dataset_root / "e3c-de" / _recipe_filename(variant)


def translation_view_destination(artifact_root: Path, variant: str) -> Path:
    _recipe_filename(variant)
    return artifact_root / "views" / f"e3c-de-{variant}"


def resolve_translation_pointer(
    *, artifact_root: Path, store: ArtifactStore, recipe_sha256: str
) -> StagePointer:
    """Find the published translation manifest produced by one recipe.

    Both variants publish into the same stage directory, so the newest file
    is not necessarily the requested one. Matching on the manifest's recipe
    hash identifies the variant without needing the Google project ID that
    the full semantic key contains.
    """
    state_root = artifact_root / "state" / "translate" / "e3c"
    candidates = sorted(
        state_root.glob("*.json"),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    for path in candidates:
        pointer = StagePointer.model_validate_json(path.read_bytes())
        if (
            pointer.subject_role
            is not ProvenanceSubjectRole.TRANSLATION_MANIFEST
        ):
            continue
        manifest = TranslationManifest.model_validate_json(
            store.read_bytes(pointer.subject_sha256), strict=True
        )
        if manifest.recipe_sha256 == recipe_sha256:
            return pointer
    raise ValueError(f"no published E3C translation for recipe {recipe_sha256}")
