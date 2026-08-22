# E3C-UMLS-zu-HPO-Audit

## Ziel und Vorgehen

Untersucht wurde, inwieweit sich die UMLS-annotierten klinischen Begriffe in
E3C zuverlässig in HPO-Terme überführen lassen und ob nicht abbildbare
Begriffe für die Phänotyp-Extraktion überhaupt relevant sind.

Zwei Agenten prüften unabhängig dieselben 458 `CLINENTITY`-Annotationen aus
30 E3C-Layer-1-Texten. Berücksichtigt wurden jeweils der annotierte
Originalspan und sein Satzkontext. Als HPO-Quelle diente ausschließlich die
offizielle, lokal gepinnte Ontologie `v2026-06-23` mit 20.413 Termen, davon
19.836 aktiv. Die verwendete `hp.obo`-Datei hat den SHA-256
`a5092cbdf605f568403cf7380d9173014015692433b2cc631bc5c1b053876b1b`.
Alle vorgeschlagenen HPO-IDs, Labels, Statusangaben und direkten UMLS-xrefs
wurden abschließend nochmals maschinell gegen diese Datei validiert.

## Ergebnis

Agent A bewertete 230 von 458 Annotationen als sicher eins zu eins
konvertierbar, Agent B 244. Bei 210 Annotationen, entsprechend 45,9 %, kamen
beide unabhängig zum selben sicheren HPO-Ziel. Bei weiteren fünf
Annotationen hielten beide eine Konversion für möglich, wählten jedoch
unterschiedlich spezifische HPO-Terme. Weitere 44 Exaktentscheidungen wurden
nur von einem der beiden Agenten bestätigt. Insgesamt stimmte die
Auditklasse bei 358 von 458 Annotationen beziehungsweise 78,2 % überein.

| Auditklasse | Agent A | Agent B |
|---|---:|---:|
| Direkter xref, im Kontext gültig | 151 | 156 |
| Semantisch exakter zusätzlicher Kandidat | 79 | 88 |
| Nur breiterer, engerer oder verwandter Kandidat | 78 | 89 |
| Relevant, aber ohne äquivalenten HPO-Term | 61 | 53 |
| Nicht HPO-/Retrieval-relevant | 64 | 58 |
| Direkter xref mit Kontextfehler | 11 | 6 |
| Mehrere direkte HPO-Ziele | 3 | 3 |
| Ungültig und nicht sicher rettbar | 11 | 5 |

Die nicht sicher konvertierbaren Annotationen waren überwiegend nicht
irrelevant. Agent A bewertete 164 von 228 dieser Annotationen als weiterhin
phänotypisch relevant, Agent B 156 von 214. Das entspricht etwa 72 %. Nach
zusätzlicher Berücksichtigung von Negation, Unsicherheit, zeitlichem Verlauf
und Subjekt blieben jedoch nur 52–54 % als positive Befunde des
Indexpatienten übrig. Ein fehlendes Mapping ist somit meist ein
Abdeckungs- oder Granularitätsproblem, aber nicht automatisch ein Beleg für
Irrelevanz.

## Typische Probleme

| Problem | Häufigkeit |
|---|---:|
| Kein direkter UMLS-xref in HPO | 244 (53,3 %) |
| Negierter oder abwesender Befund | 73–79 (15,9–17,2 %) |
| Ungültige oder fehlende Quell-CUI | 49 (10,7 %) |
| Unsicher oder hypothetisch | 12–19 (2,6–4,1 %) |
| Nicht-Index-Subjekt oder Familie | 15–18 (3,3–3,9 %) |
| Normalbefund | 10–16 (2,2–3,5 %) |
| Historisch oder abgeklungen | 11–16 (2,4–3,5 %) |
| Generische Aussage oder Empfehlung | 11–13 (2,4–2,8 %) |
| Direkter xref im Kontext semantisch falsch | 6–11 (1,3–2,4 %) |
| Mehrere direkte HPO-Ziele | 3 (0,7 %) |

Die Kategorien können sich überlappen. Besonders problematisch sind
unspezifische oder zusammengesetzte Spans wie `lesion`, `mass`, `swelling`
oder `signs`. Auch Orts-, Schweregrad- und Histologieangaben gehen bei einer
reinen CUI-Konversion häufig verloren. Weitere nicht geeignete Annotationen
bezeichnen Diagnosen statt einzelner Phänotypen, reine Anatomie oder Genetik,
Prozeduren, Behandlungen oder allgemeine Aussagen.

Ein fehlender direkter xref schließt eine sichere Rettung aus dem Text nicht
aus. Von beiden Agenten bestätigte Beispiele sind:

- `thyroid nodule` → `HP:0025388` (Thyroid nodule)
- `tea colored urine` → `HP:0040319` (Dark urine)
- `gum bleeding` → `HP:0000225` (Gingival bleeding)
- `odynophagia` → `HP:0032043` (Odynophagia)

Umgekehrt kann ein vorhandener xref falsch sein. Eine tumoröse `swelling`
wurde beispielsweise direkt auf `HP:0000969` (Edema) abgebildet, obwohl der
Kontext keine Flüssigkeitseinlagerung bezeichnet. Auch formal passende
Terme dürfen nicht als positive HPO-Annotation übernommen werden, wenn der
Befund verneint, normal, historisch, unsicher oder einem anderen Subjekt
zugeordnet ist.

## Fazit

Eine rein mechanische UMLS-xref-Konversion reicht für E3C nicht aus. Als
konservativ belastbarer Ausgangspunkt gelten die 210 Annotationen, bei denen
beide Agenten dasselbe sichere HPO-Ziel fanden. Die 49 abweichenden
Exaktentscheidungen sollten vor einer Verwendung als Goldstandard manuell
geprüft werden. Zusätzlich muss der Assertionsstatus getrennt vom
Terminologie-Mapping erhalten bleiben, damit negierte, unsichere,
historische oder fremdsubjektbezogene Begriffe nicht zu falschen positiven
HPO-Annotationen werden.
