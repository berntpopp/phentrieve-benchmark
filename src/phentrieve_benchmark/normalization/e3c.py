from collections import Counter
from collections.abc import Mapping
from pathlib import PurePosixPath
from xml.etree.ElementTree import Element

from defusedxml import ElementTree  # type: ignore[import-untyped]
from defusedxml.common import DefusedXmlException  # type: ignore[import-untyped]

from phentrieve_benchmark.acquisition.recipes import (
    E3cAdapterContract,
    E3cLanguagePath,
    E3cSemanticType,
    SourceRecipe,
)
from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.source_annotation import (
    SourceAnnotation,
    SourceAnnotationSet,
    SourceAttribute,
    SourceRelation,
    SourceRelationArgument,
    validate_source_annotation_set,
)
from phentrieve_benchmark.normalization.contracts import NormalizedTarget
from phentrieve_benchmark.normalization.text import (
    TextBoundaryError,
    canonicalize_source_text,
)

_XMI = "http://www.omg.org/XMI"
_CAS = "http:///uima/cas.ecore"
_CUSTOM = "http:///webanno/custom.ecore"
_XMI_ID = f"{{{_XMI}}}id"


class E3cNormalizationError(ValueError):
    """An E3C Layer 1 document violates its pinned XMI contract."""


def _split_tag(tag: str) -> tuple[str, str]:
    if not tag.startswith("{") or "}" not in tag:
        return "", tag
    namespace, local = tag[1:].split("}", 1)
    return namespace, local


def _language_for_path(
    path: str, language_paths: tuple[E3cLanguagePath, ...]
) -> str | None:
    candidate = PurePosixPath(path)
    matches = [
        item.language
        for item in language_paths
        if candidate.match(item.path_pattern)
    ]
    if len(matches) > 1:
        raise E3cNormalizationError("source path matches multiple languages")
    return matches[0] if matches else None


def _required_attribute(element: Element, name: str) -> str:
    value = element.attrib.get(name)
    if value is None:
        raise E3cNormalizationError(f"XMI element lacks {name}")
    return value


def _source_attributes(
    element: Element, semantic_type: E3cSemanticType
) -> tuple[SourceAttribute, ...]:
    result: list[SourceAttribute] = []
    for name in semantic_type.allowed_attributes:
        value = element.attrib.get(name)
        if value not in {None, ""}:
            result.append(
                SourceAttribute(namespace="e3c", name=name, value=value)
            )
    return tuple(result)


def _parse_document(
    payload: bytes,
    *,
    path: str,
    language: str,
    contract: E3cAdapterContract,
    source_schema_id: str,
) -> tuple[Document, SourceAnnotationSet, Counter[str], int]:
    try:
        root = ElementTree.fromstring(payload)
    except (ElementTree.ParseError, DefusedXmlException) as error:
        raise E3cNormalizationError("unsafe or malformed E3C XML") from error
    if root.tag != f"{{{_XMI}}}XMI":
        raise E3cNormalizationError("root element is not XMI")

    sofas = [
        element
        for element in root
        if _split_tag(element.tag) == (_CAS, "Sofa")
    ]
    if len(sofas) != 1:
        raise E3cNormalizationError("XMI must contain exactly one Sofa")
    source_text = _required_attribute(sofas[0], "sofaString")
    text_map = canonicalize_source_text(
        source_text, remove_terminal_format_newline=True
    )
    source_case_id = PurePosixPath(path).stem
    document = Document.from_text(
        source_case_id=source_case_id,
        case_group_id=f"e3c:v2.0.0:{source_case_id}",
        document_id=f"e3c:v2.0.0:{language}:{source_case_id}:native",
        language=language,
        translation_status=TranslationStatus.NATIVE,
        text=text_map.canonical_text,
    )

    registry = {item.name: item for item in contract.semantic_types}
    annotation_types = {
        name: item for name, item in registry.items() if item.kind == "annotation"
    }
    relation_types = {
        name: item for name, item in registry.items() if item.kind == "relation"
    }
    annotations: list[SourceAnnotation] = []
    relations_pending: list[tuple[Element, E3cSemanticType]] = []
    xmi_to_annotation: dict[str, str] = {}
    counts: Counter[str] = Counter()
    sentence_count = 0

    for element in root:
        namespace, local = _split_tag(element.tag)
        if namespace == _CUSTOM:
            if local in contract.structural_types:
                continue
            semantic_type = registry.get(local)
            if semantic_type is None:
                raise E3cNormalizationError(
                    f"unknown custom XMI type: {local}"
                )
            counts[local] += 1
            if local in annotation_types:
                xmi_id = _required_attribute(element, _XMI_ID)
                if xmi_id in xmi_to_annotation:
                    raise E3cNormalizationError("duplicate semantic XMI ID")
                try:
                    begin = int(
                        _required_attribute(
                            element, semantic_type.begin_attribute or ""
                        )
                    )
                    end = int(
                        _required_attribute(
                            element, semantic_type.end_attribute or ""
                        )
                    )
                    span = text_map.utf16_span(begin, end)
                except (ValueError, TextBoundaryError) as error:
                    raise E3cNormalizationError(
                        "malformed semantic annotation offsets"
                    ) from error
                concept = (
                    element.attrib.get(semantic_type.concept_attribute)
                    if semantic_type.concept_attribute is not None
                    else None
                )
                source_id = xmi_id
                xmi_to_annotation[xmi_id] = source_id
                annotations.append(
                    SourceAnnotation(
                        source_annotation_id=source_id,
                        source_type=local,
                        source_concept_id=concept or None,
                        attributes=_source_attributes(element, semantic_type),
                        evidence_spans=(span,),
                    )
                )
            elif local in relation_types:
                relations_pending.append((element, semantic_type))
        elif local in contract.structural_types:
            if local == "Sentence":
                sentence_count += 1
            try:
                text_map.utf16_span(
                    int(_required_attribute(element, "begin")),
                    int(_required_attribute(element, "end")),
                )
            except (ValueError, TextBoundaryError) as error:
                raise E3cNormalizationError(
                    "malformed structural annotation offsets"
                ) from error

    relations: list[SourceRelation] = []
    for element, semantic_type in relations_pending:
        xmi_id = _required_attribute(element, _XMI_ID)
        if set(semantic_type.argument_attributes) != {"role", "target"}:
            raise E3cNormalizationError("unsupported relation argument contract")
        role = _required_attribute(element, "role")
        target = _required_attribute(element, "target")
        referenced = xmi_to_annotation.get(target)
        if referenced is None:
            raise E3cNormalizationError(
                "relation target does not resolve in annotation set"
            )
        relations.append(
            SourceRelation(
                source_relation_id=xmi_id,
                source_type=semantic_type.name,
                arguments=(
                    SourceRelationArgument(
                        role=role,
                        referenced_annotation_id=referenced,
                    ),
                ),
            )
        )

    annotation_set = SourceAnnotationSet(
        annotation_set_id=(
            f"e3c:v2.0.0:{language}:{source_case_id}:source:v1"
        ),
        document_sha256=document.document_sha256,
        source_schema_id=source_schema_id,
        annotations=tuple(annotations),
        relations=tuple(relations),
    )
    validate_source_annotation_set(document, annotation_set)
    return document, annotation_set, counts, sentence_count


def normalize_e3c_members(
    members: Mapping[str, bytes],
    *,
    source_recipe: SourceRecipe,
) -> NormalizedTarget:
    contract = source_recipe.adapter_contract
    if not isinstance(contract, E3cAdapterContract):
        raise ValueError("E3C adapter contract required")
    documents: list[Document] = []
    annotation_sets: list[SourceAnnotationSet] = []
    identities: set[tuple[str, str]] = set()
    language_documents: Counter[str] = Counter()
    semantic_counts: dict[str, Counter[str]] = {
        item.language: Counter() for item in contract.language_paths
    }
    structure_counts: list[tuple[str, str, str, int]] = []

    for path, payload in sorted(members.items()):
        if path == "README.md":
            continue
        language = _language_for_path(path, contract.language_paths)
        if language is None:
            raise E3cNormalizationError(
                f"source path is outside exact Layer 1 contract: {path}"
            )
        source_case_id = PurePosixPath(path).stem
        identity = (language, source_case_id)
        if identity in identities:
            raise E3cNormalizationError("duplicate E3C case identity")
        identities.add(identity)
        document, annotation_set, counts, sentence_count = _parse_document(
            payload,
            path=path,
            language=language,
            contract=contract,
            source_schema_id=source_recipe.source_schema_id,
        )
        documents.append(document)
        annotation_sets.append(annotation_set)
        language_documents[language] += 1
        semantic_counts[language].update(counts)
        structure_counts.append(
            (language, source_case_id, "sentences", sentence_count)
        )

    for language_path in contract.language_paths:
        language = language_path.language
        if language_documents[language] != language_path.expected_documents:
            raise E3cNormalizationError(
                f"E3C document count mismatch for {language}"
            )
        expected = {
            item.name: item.count
            for item in language_path.expected_semantic_counts
        }
        if expected and dict(semantic_counts[language]) != expected:
            raise E3cNormalizationError(
                f"E3C semantic count mismatch for {language}"
            )

    return NormalizedTarget(
        documents=tuple(
            sorted(documents, key=lambda document: document.document_id)
        ),
        source_annotation_sets=tuple(
            sorted(
                annotation_sets,
                key=lambda value: value.annotation_set_id,
            )
        ),
        source_structure_counts=tuple(sorted(structure_counts)),
        counts=tuple(
            sorted(
                [
                    ("documents", len(documents)),
                    (
                        "source_annotations",
                        sum(
                            len(value.annotations)
                            for value in annotation_sets
                        ),
                    ),
                    (
                        "source_relations",
                        sum(
                            len(value.relations)
                            for value in annotation_sets
                        ),
                    ),
                ]
            )
        ),
    )
