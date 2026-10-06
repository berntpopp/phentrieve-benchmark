from hashlib import sha256

from phentrieve_benchmark.ontology.hpo import load_hpo_index
from phentrieve_benchmark.ontology.hpo_lookup import read_lookup_entries, search_hpo
from tests.fixtures.hpo import proposal_hpo_obo

_ENTRIES = read_lookup_entries(proposal_hpo_obo())


def _ids(query: str, limit: int = 15) -> list[str]:
    return [match.entry.hpo_id for match in search_hpo(_ENTRIES, query, limit=limit)]


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


def test_exact_label_ranks_before_partial_matches() -> None:
    assert _ids("pain") == ["HP:0002829", "HP:0003326"]
    assert _ids("pain", limit=1) == ["HP:0002829"]


def test_id_query_returns_the_term_even_if_obsolete() -> None:
    (match,) = search_hpo(_ENTRIES, " HP:0009999 ")
    assert match.entry.obsolete
    assert match.matched == "Obsolete fever variant"
