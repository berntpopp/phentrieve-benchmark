from hashlib import sha256

from phentrieve_benchmark.ontology.hpo import load_hpo_index
from phentrieve_benchmark.ontology.hpo_lookup import read_lookup_entries, search_hpo
from tests.fixtures.hpo import proposal_hpo_obo

_ENTRIES = read_lookup_entries(proposal_hpo_obo())


def _ids(query: str, limit: int = 15) -> list[str]:
    return [match.entry.hpo_id for match in search_hpo(_ENTRIES, query, limit=limit)]


def _term(hpo_id: str, name: str, parent: str = "HP:0000118") -> bytes:
    return f"[Term]\nid: {hpo_id}\nname: {name}\nis_a: {parent} ! parent\n\n".encode()


def test_fixture_is_a_valid_strict_hpo_index() -> None:
    body = proposal_hpo_obo()
    index = load_hpo_index(
        body, release="v2026-06-23", ontology_sha256=sha256(body).hexdigest()
    )
    assert index.alternate_to_primary["HP:0009998"] == "HP:0001945"


def test_reads_labels_synonyms_and_obsolete_flags() -> None:
    fever = next(entry for entry in _ENTRIES if entry.hpo_id == "HP:0001945")
    assert fever.label == "Fever"
    assert fever.synonyms == ("Pyrexia", "Hyperthermia")
    assert not fever.obsolete
    obsolete = next(entry for entry in _ENTRIES if entry.hpo_id == "HP:0009999")
    assert obsolete.obsolete


def test_text_search_skips_obsolete_terms() -> None:
    assert _ids("fever") == ["HP:0001945"]


def test_synonym_match_reports_the_synonym() -> None:
    (match,) = search_hpo(_ENTRIES, "muscle pain")
    assert match.entry.hpo_id == "HP:0003326"
    assert match.matched == "Muscle pain"


def test_all_tokens_must_match_and_accents_fold() -> None:
    assert _ids("F\u00e9brile convulsion") == ["HP:0002373"]
    assert _ids("joint fever") == []


def test_shorter_name_breaks_ties() -> None:
    assert _ids("pain") == ["HP:0002829", "HP:0003326"]
    assert _ids("pain", limit=1) == ["HP:0002829"]


def test_id_query_returns_the_term_even_if_obsolete() -> None:
    (match,) = search_hpo(_ENTRIES, " HP:0009999 ")
    assert match.entry.obsolete
    assert match.matched == "Obsolete fever variant"


def test_punctuation_hyphens_and_apostrophes_do_not_block_matches() -> None:
    assert _ids("febrile-convulsion.") == ["HP:0002373"]
    assert _ids("(fever)") == ["HP:0001945"]
    assert _ids("  joint   pain ") == ["HP:0002829"]
    entries = read_lookup_entries(
        _term("HP:0000001", "Raynaud's phenomenon")
        + _term("HP:0000002", "Fever-induced seizure")
    )
    curly = search_hpo(entries, "Raynaud\u2019s phenomenon")
    assert [m.entry.hpo_id for m in curly] == ["HP:0000001"]
    hyphen = search_hpo(entries, "fever induced seizure")
    assert [m.entry.hpo_id for m in hyphen] == ["HP:0000002"]


def test_punctuation_only_query_matches_nothing() -> None:
    assert _ids("...") == []
    assert _ids("   ") == []
    assert _ids("") == []


def test_exact_ranks_before_prefix_before_infix_regardless_of_length() -> None:
    entries = read_lookup_entries(
        _term("HP:0000001", "Big ab")
        + _term("HP:0000002", "Abnormal thing")
        + _term("HP:0000003", "Ab")
    )
    ids = [m.entry.hpo_id for m in search_hpo(entries, "ab")]
    assert ids == ["HP:0000003", "HP:0000002", "HP:0000001"]


def test_text_search_lists_only_phenotypic_abnormalities() -> None:
    assert _ids("stillbirth") == []
    assert _ids("clinical modifier") == []
    assert _ids("phenotypic abnormality") == ["HP:0000118"]


def test_descendants_of_phenotypic_abnormality_count_at_any_depth() -> None:
    entries = read_lookup_entries(
        _term("HP:0000001", "Parent finding")
        + _term("HP:0000002", "Child finding", parent="HP:0000001")
        + _term("HP:0000003", "Modifier finding", parent="HP:0012823")
    )
    ids = [m.entry.hpo_id for m in search_hpo(entries, "finding")]
    assert ids == ["HP:0000002", "HP:0000001"]


def test_id_query_returns_a_term_outside_phenotypic_abnormality() -> None:
    (match,) = search_hpo(_ENTRIES, "HP:0003826")
    assert match.entry.label == "Stillbirth"
    assert not match.entry.phenotypic
    (fever,) = search_hpo(_ENTRIES, "HP:0001945")
    assert fever.entry.phenotypic
