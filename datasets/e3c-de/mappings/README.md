# E3C UMLS-to-HPO mapping

These text-free outputs map every E3C Layer 1 `CLINENTITY` annotation against
exact `UMLS:` cross-references in the official HPO release `v2026-06-23`
(`hp.obo` SHA-256
`a5092cbdf605f568403cf7380d9173014015692433b2cc631bc5c1b053876b1b`).
The command is:

```text
uv run phentrieve-benchmark map-hpo e3c
```

The complete population contains 246 documents and 3,696 eligible source
annotations. Results are:

- 1,321 `unique_active`;
- 58 `ambiguous`;
- 1,925 `missing`;
- 0 `obsolete`; and
- 392 `invalid`.

`invalid` comprises source values without a valid `C` plus seven digits,
including 311 `CUILESS`, 78 absent identifiers, two `C036572` values, and one
`C0042963x` value.

The selected 30-case view contains 458 annotations: 162 `unique_active`, 3
`ambiguous`, 244 `missing`, 0 `obsolete`, and 49 `invalid`.

The pinned ontology contains one malformed cross-reference,
`HP:0034420 -> UMLS:0189573`. It is excluded rather than silently rewritten
to a different CUI and is retained as the deterministic ontology warning
`HP:0034420:malformed_umls_xref:0189573`.

`unique_active` records remain candidates rather than accepted clinical
annotations. All other classifications require review. No labels are used to
infer missing mappings, obsolete terms are not replaced automatically, and
this phase creates no German evidence spans.

## OxO2 probe

On 2026-07-25, the 945 unique valid CUIs behind the 1,925 `missing`
annotations were compared with all 4,520 `UMLS`-to-`HP` mappings returned by
the public, login-free OxO2 preview API:

`https://wwwdev.ebi.ac.uk/oxo2/api/v2/mappings/search`

The intersection covered 58 CUIs and 98 source annotations. Of these, 52 CUIs
had one HPO target and 6 had multiple targets. There were no direct
distance-1 mappings: all 91 returned rows were inferred mapping chains with
distances from 2 onward. Some candidates were plausible, while others were
too specific, for example `Aspergillosis -> Invasive pulmonary
aspergillosis`.

OxO2 is therefore considered only a possible review-candidate source. No
OxO2 result was incorporated into the mapping outputs automatically. The
former production OxO API was already retired at the time of this probe.

## Monarch/MedGen mapping probe

The public, login-free HPO-UMLS mapping published by Monarch and documented
by HPO was also tested:

`https://data.monarchinitiative.org/mappings/latest/umls_hp.sssom.tsv`

The file contained 19,213 mappings and was last modified on 2026-07-19. It
covered 113 of the 945 unique valid CUIs missing from the direct HPO
cross-references, corresponding to 230 source annotations. In the selected
30-case view, it covered 19 CUIs and 27 annotations. Every matched CUI had
exactly one target.

Validation against pinned HPO `v2026-06-23` found 108 active targets and five
obsolete targets. Each obsolete target had one explicit replacement:

| Obsolete target | Replacement |
| --- | --- |
| `HP:0025428` | `HP:4000007` |
| `HP:0002355` | `HP:0001288` |
| `HP:0100786` | `HP:0001262` |
| `HP:0008826` | `HP:0002827` |
| `HP:0031804` | `HP:0025240` |

All 113 source mappings are marked `semapv:MappingChaining`, rather than
directly curated matches, and the downloaded file declares its license as
`unspecified`.

### Plausibility review

A preliminary semantic review compared every one of the 113 mappings with
the actual E3C evidence span and used sentence context for borderline cases.
It classified 99 CUIs as plausible, 6 as related but not clearly equivalent,
and 8 as probably incorrect. By source-annotation count, these groups cover
198, 12, and 20 annotations respectively.

Examples of probably incorrect mappings include:

| CUI | E3C meaning | Proposed HPO target |
| --- | --- | --- |
| `C0010051` | nonspecific coronary lesion | Coronary artery aneurysm |
| `C0038994` | general hyperhidrosis | Gustatory sweating |
| `C0085593` | painful neuropathic cold sensation | Chills |
| `C0151799` | necrosis within a tumour | Cutaneous necrosis |
| `C0242301` | furuncle-like appearance of a myiasis lesion | Furuncle |
| `C0333440` | renal hyaline/amyloid deposit | Civatte bodies |
| `C0917799` | hypersomnia | Excessive daytime somnolence |
| `C1542178` | upper- and lower-extremity fractures | Fractured lower leg |

The six mappings retained for focused review are congenital malformation to
Fetal anomaly, depapillated tongue to Geographic tongue, hyperpathia to
Dysesthesia, meningism to Nuchal rigidity, periodontal disease to
Periodontitis, and sensory or gustatory loss to Ageusia. Assertion polarity
is separate from mapping plausibility and must remain preserved, for example
when a semantically mappable expression is negated in the source text.

No Monarch/MedGen mapping, including a plausible one, has been incorporated
into the mapping outputs.

## Direct and still-unmapped examples

Examples of clear direct mappings present as `UMLS:` cross-references in the
pinned HPO are:

| UMLS CUI | HPO target |
| --- | --- |
| `C0018681` | `HP:0002315` Headache |
| `C0015967` | `HP:0001945` Fever |
| `C0003962` | `HP:0001541` Ascites |
| `C0019209` | `HP:0002240` Hepatomegaly |
| `C0020538` | `HP:0000822` Hypertension |
| `C0011849` | `HP:0000819` Diabetes mellitus |
| `C0028754` | `HP:0001513` Obesity |
| `C0042963` | `HP:0002013` Vomiting |

After taking the union of the Monarch/MedGen and OxO2 candidates, 805 of the
945 initially missing CUIs remain without any mapping in the three tested
sources. They account for 1,650 source annotations. Frequent examples are
`C0221198` (lesion; 75 annotations), `C0577559` (mass/lump; 74),
`C0019080` (bleeding; 33), `C0038999` (swelling; 29), `C0332448`
(infiltration; 27), `C0018944` (hematoma; 21), and `C0010709` (cyst; 17).
Many are generic findings, processes, or diseases for which a safe one-to-one
HPO assignment should not be assumed.

## Source-annotation granularity

The missing mappings are not solely a coverage problem in the mapping
sources. E3C sometimes assigns a generic UMLS concept even when the text
contains a more specific description. For example, all 75 annotations of
`C0221198` represent only `lesion`, although their contexts include lytic,
necrotic, vascular, cystic, furuncle-like, and expansile lesions. These
qualifiers are not consistently represented by separate CUIs.

Of the 75 `C0221198` annotations, 47 have at least one other valid coded
clinical concept in the same sentence and 28 do not. The additional concept
is not necessarily a refinement of the lesion: it may instead denote a
comorbidity, symptom, investigation result, or later diagnosis. Even when a
useful refinement is present, the source annotation does not explicitly link
it to the generic lesion annotation. A CUI-only conversion would therefore
lose clinically relevant specificity and cannot safely infer number,
negation, or lesion type from `C0221198`.

This differs from CSC and GSC, whose manual annotations already assign
case-level HPO terms. Against HPO `v2026-06-23`, all 1,012 GSC annotations are
active; CSC has 1,779 active annotations, 15 obsolete annotations with a
single proposed successor, and one obsolete annotation requiring focused
review. They are consequently stronger than E3C at the concept-selection
level.

The comparison also exposes a complementary limitation: the CSC/GSC workbook
does not provide text offsets. Its HPO annotations cannot be tied
automatically to an exact evidence span or checked locally for wording,
negation, uncertainty, and subject context. CSC/GSC should therefore be
treated as curated case-level HPO gold annotations, while E3C provides
span-level source evidence with less reliable concept granularity. Neither
source alone is a complete span-based HPO gold standard.
