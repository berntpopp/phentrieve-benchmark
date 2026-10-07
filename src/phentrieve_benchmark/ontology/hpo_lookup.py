"""Search the pinned HPO release by label, synonym, or ID.

A lookup aid for the proposal subagents. It reads OBO term stanzas directly
(fast enough for repeated CLI calls); the validator still checks every
proposed ID against the strict HPO index. Text search lists only terms under
Phenotypic abnormality, the branch the annotation guideline covers (R0).
"""

import re
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace

_HPO_ID = re.compile(r"HP:[0-9]{7}", re.ASCII)
_IS_A = re.compile(r"^is_a: (HP:[0-9]{7})", re.ASCII)
_PHENOTYPIC_ABNORMALITY = "HP:0000118"
_WORD = re.compile(r"\w+")
_SYNONYM = re.compile(r'^synonym: "((?:[^"\\]|\\.)*)"')


@dataclass(frozen=True)
class HpoLookupEntry:
    hpo_id: str
    label: str
    synonyms: tuple[str, ...]
    obsolete: bool
    phenotypic: bool = False


@dataclass(frozen=True)
class HpoLookupMatch:
    entry: HpoLookupEntry
    matched: str


def _entry(lines: list[str]) -> tuple[HpoLookupEntry, tuple[str, ...]] | None:
    """Parse one term stanza into its entry and its parent IDs."""
    hpo_id = next((line[4:] for line in lines if line.startswith("id: ")), None)
    label = next((line[6:] for line in lines if line.startswith("name: ")), None)
    if hpo_id is None or label is None or _HPO_ID.fullmatch(hpo_id) is None:
        return None
    synonyms = tuple(
        match.group(1).replace('\\"', '"')
        for line in lines
        if (match := _SYNONYM.match(line)) is not None
    )
    parents = tuple(
        match.group(1) for line in lines if (match := _IS_A.match(line)) is not None
    )
    entry = HpoLookupEntry(
        hpo_id=hpo_id,
        label=label,
        synonyms=synonyms,
        obsolete="is_obsolete: true" in lines,
    )
    return entry, parents


def _phenotypic_ids(children: dict[str, list[str]]) -> set[str]:
    found = {_PHENOTYPIC_ABNORMALITY}
    pending = [_PHENOTYPIC_ABNORMALITY]
    while pending:
        for child in children.get(pending.pop(), ()):
            if child not in found:
                found.add(child)
                pending.append(child)
    return found


def read_lookup_entries(ontology_bytes: bytes) -> tuple[HpoLookupEntry, ...]:
    entries: list[HpoLookupEntry] = []
    children: defaultdict[str, list[str]] = defaultdict(list)
    stanza: list[str] | None = None
    for line in (*ontology_bytes.decode("utf-8").splitlines(), "[End]"):
        if line.startswith("["):
            if stanza is not None and (parsed := _entry(stanza)) is not None:
                entry, parents = parsed
                entries.append(entry)
                for parent in parents:
                    children[parent].append(entry.hpo_id)
            stanza = [] if line == "[Term]" else None
        elif stanza is not None:
            stanza.append(line)
    phenotypic = _phenotypic_ids(children)
    return tuple(
        replace(entry, phenotypic=entry.hpo_id in phenotypic) for entry in entries
    )


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    stripped = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(_WORD.findall(stripped))


def search_hpo(
    entries: Sequence[HpoLookupEntry], query: str, *, limit: int = 15
) -> tuple[HpoLookupMatch, ...]:
    """Return active phenotypic terms whose label or synonym has every query word.

    An exact HPO ID returns that term, obsolete or outside Phenotypic
    abnormality or not. Ranking: exact name,
    then names starting with the query, then other matches; shorter names
    first; HPO ID breaks ties.
    """
    stripped = query.strip()
    if _HPO_ID.fullmatch(stripped):
        return tuple(
            HpoLookupMatch(entry=entry, matched=entry.label)
            for entry in entries
            if entry.hpo_id == stripped
        )
    folded_query = _fold(stripped)
    tokens = folded_query.split()
    if not tokens:
        return ()
    ranked: list[tuple[tuple[int, int], str, HpoLookupMatch]] = []
    for entry in entries:
        if entry.obsolete or not entry.phenotypic:
            continue
        best: tuple[tuple[int, int], str] | None = None
        for name in (entry.label, *entry.synonyms):
            folded = _fold(name)
            if not all(token in folded for token in tokens):
                continue
            if folded == folded_query:
                position = 0
            elif folded.startswith(folded_query):
                position = 1
            else:
                position = 2
            rank = (position, len(name))
            if best is None or rank < best[0]:
                best = (rank, name)
        if best is not None:
            ranked.append(
                (best[0], entry.hpo_id, HpoLookupMatch(entry=entry, matched=best[1]))
            )
    ranked.sort(key=lambda item: (item[0], item[1]))
    return tuple(item[2] for item in ranked[:limit])
