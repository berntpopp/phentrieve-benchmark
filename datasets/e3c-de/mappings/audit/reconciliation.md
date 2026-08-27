# Doppeltes E3C-UMLS-zu-HPO-Audit

## Umfang und Datenbasis

Zwei getrennte Agenten prüften unabhängig dieselben 458 `CLINENTITY`-
Annotationen aus 30 E3C-Layer-1-Fällen. Beide verwendeten die Originalspans
und Satzkontexte aus dem gepinnten E3C-ZIP.

Als einzige HPO-Terminologiequelle diente die offizielle lokale
`hp.obo`-Datei des Releases `v2026-06-23`:

- Pfad: `.artifacts/source-locks/hp-v2026-06-23.obo`
- SHA-256:
  `a5092cbdf605f568403cf7380d9173014015692433b2cc631bc5c1b053876b1b`
- 20.413 Terme, davon 19.836 aktiv
- 12.684 UMLS-CUIs mit HPO-xrefs

Jede ausgegebene HPO-ID, ihr Label, ihr aktiver Status und bei direkten
Mappings der `UMLS:<CUI>`-xref wurden nach Abschluss nochmals maschinell gegen
genau diese OBO-Datei validiert. Dabei wurden in beiden Audits keine
ungültigen HPO-Kandidaten oder falschen Summen gefunden.

## Ergebnisse der beiden unabhängigen Audits

| Auditklasse | Agent A | Agent B |
|---|---:|---:|
| Direkter xref, im Kontext gültig | 151 | 156 |
| Direkter xref, aber Kontextfehler | 11 | 6 |
| Mehrere direkte HPO-Ziele | 3 | 3 |
| Semantisch exakter HPO-Kandidat | 79 | 88 |
| Nur breiterer/engerer/verwandter Kandidat | 78 | 89 |
| Relevant, aber kein äquivalenter HPO-Term | 61 | 53 |
| Nicht HPO-/Retrieval-relevant | 64 | 58 |
| Ungültig und nicht sicher rettbar | 11 | 5 |
| **Summe** | **458** | **458** |

Eine sichere Eins-zu-eins-Konversion (`direct_valid` oder
`semantic_candidate_exact`) sah Agent A bei 230/458 (50,2 %) und Agent B bei
244/458 (53,3 %).

Die Auditklasse stimmt bei 358/458 Annotationen (78,2 %) exakt überein. Beide
Agenten stuften 215 Annotationen als sicher konvertierbar ein. Bei 210/458
(45,9 %) stimmte zusätzlich die konkrete HPO-Zielmenge überein. In fünf
weiteren Fällen hielten beide eine Konversion für möglich, wählten aber
unterschiedliche HPO-Spezifitäten. Weitere 44 Annotationen wurden nur von
einem der beiden Agenten als exakte Konversion akzeptiert. Diese 49
Ziel-/Äquivalenzkonflikte sollten vor einer Goldstandard-Freigabe manuell
entschieden werden.

## Sind die nicht sicher konvertierbaren Terme relevant?

| Bewertung unter den nicht sicher konvertierbaren Annotationen | Agent A | Agent B |
|---|---:|---:|
| Nicht sicher konvertierbar | 228 | 214 |
| Konzept weiterhin phänotypisch/review-relevant | 164 (71,9 %) | 156 (72,9 %) |
| Konzept nicht HPO-/Retrieval-relevant | 64 (28,1 %) | 58 (27,1 %) |
| Positiver Befund des Indexpatienten | 124 (54,4 %) | 111 (51,9 %) |

Damit ist ein fehlendes Mapping meistens kein Hinweis auf Irrelevanz: Rund
72 % der nicht sicher konvertierbaren Annotationen bezeichnen weiterhin ein
klinisch bzw. phänotypisch relevantes Konzept. Nach zusätzlicher Prüfung von
Negation, Unsicherheit, Verlauf und Subjekt bleiben rund 52–54 % als positive
Befunde des Indexpatienten übrig.

## Typische Probleme und Häufigkeiten

Problemkategorien können sich überlappen; Prozentwerte beziehen sich auf alle
458 Annotationen.

| Problem | Häufigkeit | Einordnung |
|---|---:|---|
| Kein direkter UMLS-xref in HPO | 244 (53,3 %) | Strukturelles Hauptproblem; ein Teil ist über den Text exakt rettbar, ein Teil nur verwandt oder gar nicht abbildbar. |
| Ungültige/fehlende Quell-CUI | 49 (10,7 %) | 44 `CUILESS`, fünf ohne CUI; Text und Kontext können einzelne Fälle trotzdem retten. |
| Negierter/abwesender Befund | 73–79 (15,9–17,2 %) | Semantische Mappbarkeit und positive Patientenannotation müssen getrennt bleiben. |
| Normalbefund | 10–16 (2,2–3,5 %) | Ein HPO-Term kann lexikalisch passen, darf aber nicht als vorhandener Phänotyp ausgegeben werden. |
| Unsicher/hypothetisch | 12–19 (2,6–4,1 %) | Verdacht, Möglichkeit und gesicherter Befund werden in E3C nicht durch das CUI-Mapping getrennt. |
| Nicht-Index-Subjekt/Familie | 15–18 (3,3–3,9 %) | Der Term betrifft teilweise Angehörige, andere Patienten oder allgemeine Aussagen. |
| Historisch/abgeklungen | 11–16 (2,4–3,5 %) | Der Befund ist nicht zwingend aktuell vorhanden. |
| Generische Aussage/Empfehlung | 11–13 (2,4–2,8 %) | Kein konkreter positiver Patientenbefund. |
| Direkter xref semantisch im Kontext falsch | 6–11 (1,3–2,4 %) | Mindestens fünf Fälle wurden von beiden Agenten als Kontextfehler bestätigt. |
| Mehrere direkte HPO-Ziele | 3 (0,7 %) | Der CUI-xref allein entscheidet nicht zwischen den HPO-Terms. |

Zusätzliche wiederkehrende Ursachen sind generische oder zusammengesetzte
Spans (`lesion`, `mass`, `swelling`, `signs`), verlorene Orts- oder
Schweregradinformation, Diagnosen statt einzelner Phänotypen sowie reine
Anatomie, Histologie, Genetik, Prozeduren oder Behandlungen.

## Repräsentative, von beiden Agenten bestätigte Beispiele

- `thyroid nodule` → `HP:0025388` (Thyroid nodule): kein direkter xref im
  Mappingmanifest, aber von beiden semantisch exakt bestätigt.
- `tea colored urine` → `HP:0040319` (Dark urine): trotz ungültiger
  Quell-CUI aus Span und Kontext sicher rettbar.
- `gum bleeding` → `HP:0000225` (Gingival bleeding): trotz fehlender CUI
  sicher rettbar.
- `odynophagia` → `HP:0032043` (Odynophagia): fehlender direkter xref, aber
  exakter aktiver HPO-Term.
- Tumoröse `swelling` mit direktem `HP:0000969` (Edema): beide Agenten
  verwarfen den direkten xref als kontextuell nicht äquivalent.
- `palidez` einer nicht blassen Papille mit direktem `HP:0000980` (Pallor):
  der xref ist semantisch zu allgemein und der konkrete Befund zudem
  verneint/normal.

## Schlussfolgerung

Eine rein mechanische UMLS-xref-Konversion ist für E3C nicht ausreichend.
Konservativ belastbar sind zunächst die 210 Annotationen, bei denen beide
Agenten dieselbe sichere HPO-Zielmenge fanden. Die 49 konfligierenden
Exaktentscheidungen benötigen fokussierte manuelle Prüfung. Bei allen
Mappings muss der Assertionsstatus separat erhalten werden; andernfalls
werden negierte, historische, unsichere oder fremdsubjektbezogene Konzepte zu
falschen positiven HPO-Annotationen.
