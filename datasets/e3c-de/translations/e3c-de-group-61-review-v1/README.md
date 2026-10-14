# Medizinisches Review der deutschen E3C-Übersetzungen — Deutsche Annotationsgruppe (`tllm-full`, 61 Fälle)

Vollständige bilinguale medizinische Vorprüfung der **61 Berichte der deutschen Annotationsgruppe** (`e3c-annotation-groups-v1`) in der Variante `general/translation-llm` (`tllm-full`) durch zeilen- und satzweisen Abgleich von Quelltext und Übersetzung.

> **Provenienz- und Statushinweis:** Dieses Dokument dokumentiert die **maschinell gestützte medizinische Übersetzungsprüfung** der 61 Berichte der deutschen E3C-Annotationsgruppe (`antigravity-gemini-4-argon-pre-review-v1`, `2026-10-14`). Die geprüften deutschen Texte, die kanonischen Review-Einträge (`TranslationReviewRecord`), die Unified-Diffs (`UnifiedTextDiff`) und das Import-Manifest (`TranslationReviewImportManifest`) sind unter `datasets/e3c-de/translations/e3c-de-group-61-review-v1/` versioniert abgelegt; der ungeprüfte Roh-Snapshot unter `datasets/e3c-de/translations/e3c-de-full-246-google-tllm-v1/` bleibt unverändert erhalten. Die leere Original-Exportarbeitsmappe ist unter `.artifacts/review-workbooks/e3c-de-group-translation-review.blank-export.xlsx` gesichert; die ausgefüllte Arbeitsmappe liegt unter `.artifacts/review-workbooks/e3c-de-group-translation-review.xlsx`. Zuschreibung und Originallizenzen der Berichte sind in [`../../ATTRIBUTION.md`](../../ATTRIBUTION.md) und [`../../LICENSES.md`](../../LICENSES.md) dokumentiert.

## 1. Provenienz und Referenz-Identitäten

| Merkmal | Wert |
| --- | --- |
| **Annotationsgruppen-Manifest** | `datasets/e3c-de/selections/e3c-annotation-groups-v1.json` |
| **Gruppen-Manifest (SHA-256)** | `2c7e93761ebfc6320e998aa08f33d454a6c54920a5270bf5edc635342b2fbfb4` |
| **Gruppen-Aggregat-Hash** | `ecc29d7666715bf1fbc3339346da25289d2af82beae8fc35b1c866f1cbbd7896` |
| **Auswahl-ID im Export** | `e3c-de-full-246-v1` |
| **Übersetzungsrezept** | `e3c-de-full-246-google-tllm-v1` (`tllm-full`) |
| **Übersetzungsmanifest (SHA-256)** | `759f00260dab85a3fbeb24204683f790b4b14a18759c2bb80910ff1725b4451a` |
| **Provider / Modell / Region** | `google-cloud-translation` (`v3`), `general/translation-llm`, `us-central1` |
| **Workbook-Export-Manifest (SHA-256)** | `ce2736cfbfe17d96b59b2f74e4b10e61b71a722a3ae82803051c6287077af652` |
| **Review-Policy-ID** | `e3c:translation-review/v1` |
| **Review-Import-Manifest (SHA-256)** | `c83c4bb7f8fcca845a16f253f6a3821055f0946eb1130f055c910470f146ceb4` |
| **Annotationskorpus-Manifest (SHA-256)** | `ba3f557f2efa188c3be64db0ef4a7a81e628e2193f3899cfd9f9c003a8cd9b14` (`de=61 en=63 fr=61 es=61 pending_review=0`) |
| **Prüfer-ID** | `antigravity-gemini-4-argon-pre-review-v1` |
| **Qualifikation / Rolle** | Maschinelle medizinische Vorprüfung (LLM-gestützt, nicht ärztlich adjudiziert) |
| **Geprüfte Sprachrichtungen** | `en, es, fr -> de` |
| **Prüfdatum** | `2026-10-14` |
| **Prüfumfang** | Alle 61 Fälle der deutschen Gruppe (21 EN, 20 ES, 20 FR), vollständig Satz für Satz gelesen |

## 2. Gesamturteil und Kennzahlen

Die `tllm-full`-Übersetzungen der 61 Berichte der deutschen Annotationsgruppe zeigen dasselbe Qualitäts- und Fehlerprofil wie die Machbarkeitskohorte aus Phase 0: **hohe sprachliche Qualität, vollständiger Erhalt der Zeilenstruktur (61/61) und der Leitphänotypen, kein Fall mit Note 4 oder 5, jedoch vereinzelte klinisch relevante Präzisierungen/Verallgemeinerungen sowie regelmäßige stille Reparaturen von Quelldefekten.**

### Übersicht nach Entscheidung und Kategorie

| Kennzahl | Anzahl | Anteil |
| --- | :---: | :---: |
| **Geprüfte Fälle gesamt** | **61** | 100,0 % |
| — davon Englisch (`en`) / Spanisch (`es`) / Französisch (`fr`) | 21 / 20 / 20 | 34,4 % / 32,8 % / 32,8 % |
| **`unverändert akzeptiert`** (`clinical_change = keine`) | **35** | 57.4 % |
| **`korrigiert akzeptiert`** gesamt | **26** | 42.6 % |
| — davon **mit klinisch relevanter Änderung** (`vorhanden`) | **21** | 34.4 % |
| — davon rein sprachlich/orthografisch (`keine`) | **5** | 8.2 % |
| **`Rückfrage`** / **`abgelehnt`** | **0** / **0** | 0,0 % |
| **Automatisch markierte Fälle (`units_added`)** | **15** | 24,6 % (1 davon klinisch echter Einheitenfehler: `ES100631`) |

### Aufschlüsselung der 21 Fälle mit klinisch relevanter Korrektur nach Hauptkategorie

| Hauptkategorie | Anzahl | Betroffene Fälle |
| --- | :---: | --- |
| `Hinzufügung` | 4 | `EN100466`, `EN100682`, `ES100280`, `FR100185` |
| `Negation oder Aussagesicherheit` | 3 | `ES100809`, `FR100946`, `FR100998` |
| `Zahl oder Einheit` | 2 | `ES100304`, `ES100631` |
| `Anatomie oder Lateralität` | 3 | `ES100002`, `ES100513`, `FR100448` |
| `Terminologie` | 9 | `EN100184`, `EN107405`, `ES100214`, `ES100412`, `ES100571`, `FR100132`, `FR100255`, `FR100346`, `FR100780` |

### Notenverteilung der ungeprüften `tllm-full`-Ausgangsfassung

| Sprache | Note 1 | Note 2 | Note 3 | Note 4 | Note 5 | Mittelwert |
| --- | :---: | :---: | :---: | :---: | :---: | :---: |
| Englisch (21) | 11 | 10 | 0 | 0 | 0 | 1.48 |
| Spanisch (20) | 9 | 9 | 2 | 0 | 0 | 1.65 |
| Französisch (20) | 10 | 8 | 2 | 0 | 0 | 1.60 |
| **Gesamt (61)** | **30** | **27** | **4** | **0** | **0** | **1.57** |

## 3. Vollständige Fall- und Provenienztabelle (alle 61 Fälle)

| Fall | Spr. | Quelle SHA-256 | TLLM SHA-256 | Endfassung SHA-256 | Auto-Check | Note | Entscheidung | Klin. Änderung | Hauptkategorie | Kurzcharakteristik |
| --- | :---: | --- | --- | --- | --- | :---: | --- | :---: | --- | --- |
| `EN100022` | `en` | `f3d2bd7a8983` | `3e52d3873692` | `3e52d3873692` | – | 1 | unverändert akzeptiert | keine | – | Inhaltlich vollständig deckungsgleich; nur stille Tippfehler-/Grammatikglättung der Quelle |
| `EN100024` | `en` | `8cc9a2ff48d8` | `4ebd3e08764c` | `4ebd3e08764c` | – | 1 | unverändert akzeptiert | keine | – | Publikationsreif; alle kardiovaskulären Befunde, Stent-/Bypass-Details und Zahlenwerte exakt erhalten |
| `EN100123` | `en` | `931db3011afd` | `1c2c87bc6d15` | `1c2c87bc6d15` | `units_added` | 2 | unverändert akzeptiert | keine | – | Klinisch vollständig erhalten; mehrere stille Einheiten-/Tippfehlerreparaturen der Quelle (units_added erklärbar) |
| `EN100184` | `en` | `ed7780fbe229` | `6b9f99e36a6f` | `40f0b7c22fcc` | – | 2 | korrigiert akzeptiert | vorhanden | `Terminologie` | „review of systems“ als „körperliche Untersuchung“ fehlübersetzt → „Systemanamnese“ |
| `EN100275` | `en` | `f89b81bc0c8f` | `2eaed3b2bda2` | `2eaed3b2bda2` | – | 2 | unverändert akzeptiert | keine | – | Klinisch treu; sprachlich stark fehlerhafte englische Quelle still geglättet, Verdachtsstatus erhalten |
| `EN100315` | `en` | `10b3e9244196` | `0350e93f8ed3` | `0350e93f8ed3` | – | 1 | unverändert akzeptiert | keine | – | Inhaltlich vollständig deckungsgleich; französisch geprägte Quellbegriffe präzise ins Deutsche übertragen |
| `EN100340` | `en` | `0f1e8e05be3e` | `d951f06ad457` | `d951f06ad457` | `units_added` | 2 | unverändert akzeptiert | keine | – | Gute Übersetzung; stille Reparatur des Quelltippfehlers „23 0000 platelets“ und zahlreicher Gallizismen |
| `EN100385` | `en` | `72e1365523a9` | `380dfabf2cae` | `380dfabf2cae` | – | 1 | unverändert akzeptiert | keine | – | Publikationsreif; alle klinischen, sonografischen, operativen und pathologischen Befunde exakt wiedergegeben |
| `EN100427` | `en` | `4dfba4710981` | `81d3bde03860` | `1fc07c6311c9` | – | 1 | korrigiert akzeptiert | keine | – | Inhaltlich einwandfrei; lediglich ein grammatischer Genusfehler („der linke Ovar“) korrigiert |
| `EN100466` | `en` | `dcc538c2fb1a` | `3477f733ca35` | `8f13d5fe2b3a` | `units_added` | 2 | korrigiert akzeptiert | vorhanden | `Hinzufügung` | Unbelegte Spezifizierung „ovarian malignancy“ -> „Ovarialkarzinom“ korrigiert; units_added durch „38.2 0 C“ und Normbereiche erklärbar |
| `EN100645` | `en` | `07a85d08ac0a` | `555ac3ed5656` | `555ac3ed5656` | – | 1 | unverändert akzeptiert | keine | – | Inhaltlich vollständig deckungsgleich; sämtliche OP-Schritte, Histologie- und IHC-Befunde exakt erhalten |
| `EN100653` | `en` | `fdcb98011109` | `f67a5a429e3b` | `f67a5a429e3b` | `units_added` | 2 | unverändert akzeptiert | keine | – | Vollständig und klinisch präzise; units_added durch reguläre Einheitenkonversion (UI/l -> U/l, u/day -> IE/Tag) und MCV-Reparatur (µ 3 -> µm³) |
| `EN100682` | `en` | `402f2daaed2f` | `0d97b5b9c41f` | `1f8fd156d2b5` | – | 2 | korrigiert akzeptiert | vorhanden | `Hinzufügung` | „sudden death“ zu „plötzlichem Herztod“ eingeengt; stille Reparatur von Quellgrammatikfehlern |
| `EN103220` | `en` | `ca49bcf3dd1a` | `bd31305da4ee` | `bd31305da4ee` | – | 1 | unverändert akzeptiert | keine | – | Publikationsreif; inhaltlich und terminologisch vollständig deckungsgleich (Abkürzung TKI einmalig aufgelöst) |
| `EN103442` | `en` | `baf85e1972ad` | `95b6b11edb77` | `95b6b11edb77` | `units_added` | 1 | unverändert akzeptiert | keine | – | Publikationsreif; units_added nur durch Bindestrichauflösung ('27-mm' -> '27 mm'); 'upper endoscopy' im Magenkontext als 'Gastroskopie' |
| `EN103589` | `en` | `5e4894c85bb3` | `29fcc15f9f42` | `29fcc15f9f42` | – | 2 | unverändert akzeptiert | keine | – | Inhaltlich vollständig und präzise; stille Reparatur des verstümmelten Quelltokens '50 an mm-size tumour' |
| `EN105023` | `en` | `cef973a2a24d` | `993cef644995` | `993cef644995` | – | 2 | unverändert akzeptiert | keine | – | Inhaltlich vollständig; Abkürzung 'PV' im Kontext mukokutaner Blasenbildung und folgender 'pemphigus'-Nennung zu 'Pemphigus vulgaris (PV)' aufgelöst |
| `EN106489` | `en` | `d9faff1c6a40` | `43a50386c977` | `43a50386c977` | – | 1 | unverändert akzeptiert | keine | – | Publikationsreif; sämtliche histopathologischen, immunhistochemischen und molekulargenetischen Befunde sowie Modalitäten exakt übertragen |
| `EN106841` | `en` | `b0277a3133c7` | `370922cfcc07` | `370922cfcc07` | – | 1 | unverändert akzeptiert | keine | – | Publikationsreif; leichte, anatomisch unbedenkliche Verallgemeinerung von 'percutaneous gastric feeds' zu 'perkutane Sondenernährung' |
| `EN107405` | `en` | `647b863bc7bf` | `975e2e978dad` | `cd5c1508322b` | – | 2 | korrigiert akzeptiert | vorhanden | `Terminologie` | Grammatische doppelte Verneinung ('keine ... weder ... noch') korrigiert; 'free' bei 'urinary free cortisol' an zwei Stellen ergänzt |
| `EN108798` | `en` | `3cf4a1cbf264` | `7c5a746452a5` | `7c5a746452a5` | – | 1 | unverändert akzeptiert | keine | – | Publikationsreif; anatomische und histopathologische Befunde vollständig und präzise übertragen ('CBD' -> 'Ductus choledochus') |
| `ES100002` | `es` | `55534d1da9e9` | `32ed0f26ebd4` | `f4a77a3771bb` | – | 2 | korrigiert akzeptiert | vorhanden | `Anatomie oder Lateralität` | Sehr gute Übersetzung; stille Reparatur des Tippfehlers „est:udio“ und fachlich präzisere, aber enge anatomische Übersetzung von „vías de uréter derecho“ korrigiert. |
| `ES100063` | `es` | `6ef917ea076a` | `077c528a0993` | `e5748cb2833a` | `units_added` | 2 | korrigiert akzeptiert | keine | – | Inhaltlich präzise Übersetzung; Satzfragment mit Auslassungspunkten („...von elastischer Konsistenz“) infolge des Punktes nach „cm.“ in der Quelle sprachlich geglättet. |
| `ES100064` | `es` | `064c6b08379e` | `1d118f9671ae` | `1d118f9671ae` | `units_added` | 2 | unverändert akzeptiert | keine | – | Klinisch vollständige Übersetzung; drei im Original einheitenlose Laborwerte (PSA, alkalische Phosphatase, GGT) wurden von TLLM mit Standardeinheiten ergänzt (`units_added`). |
| `ES100182` | `es` | `2341f4b6e1fc` | `ed46b71175ec` | `478b19b86531` | – | 1 | korrigiert akzeptiert | keine | – | Inhaltlich exakte Übersetzung; lediglich ein fehlender Artikel am Satzanfang („Eine nach Stabilisierung...“) sprachlich ergänzt. |
| `ES100214` | `es` | `266df6cb1c5f` | `9f478e19ac8c` | `f8e65bcb0f36` | – | 2 | korrigiert akzeptiert | vorhanden | `Terminologie` | Dichte pädiatrische Nephrologie-Passage exakt übertragen; Verallgemeinerung von „aclaramiento urinario de creatinina“ zu „renale Kreatinin-Clearance“ präzisiert. |
| `ES100259` | `es` | `4f7bebeedf93` | `b1f29b720cb4` | `b1f29b720cb4` | – | 1 | unverändert akzeptiert | keine | – | Publikationsreife, klinisch und numerisch vollständig deckungsgleiche Übersetzung ohne Korrekturbedarf. |
| `ES100280` | `es` | `a5b7d332ee60` | `fcee205e4352` | `603fdf1312db` | – | 1 | korrigiert akzeptiert | vorhanden | `Hinzufügung` | Vollständige und klinisch präzise Übersetzung; „efecto masa en hipogastrio“ näher am Original gefasst. |
| `ES100304` | `es` | `fcfb33154259` | `8b033a0540f9` | `0a3061558ef4` | – | 2 | korrigiert akzeptiert | vorhanden | `Zahl oder Einheit` | Sehr genaue Übersetzung mit sinnvoller stiller Reparatur des HGVS-Tippfehlers `c.q62G > A` zu `c.1162G > A`; ausgelassene Verteilungsangabe `(5-10 y 10 g)` ergänzt. |
| `ES100412` | `es` | `29b3ebcb0910` | `3d4bcc9ff9a4` | `e0943d5d57fd` | – | 2 | korrigiert akzeptiert | vorhanden | `Terminologie` | Sehr gute ophthalmologisch-pathologische Übersetzung; lediglich der formale Begriff „glaucoma agudo secundario“ präziser als „sekundäres akutes Glaukom“ gefasst. |
| `ES100513` | `es` | `cfadbeb462e5` | `a647e29f47c8` | `797f7e95eccf` | – | 2 | korrigiert akzeptiert | vorhanden | `Anatomie oder Lateralität` | Gute Übersetzung; „anquílosis mandibular“ präzise als „Unterkieferankylose“ statt einengend als „Kiefergelenksankylose“ übersetzt. |
| `ES100569` | `es` | `25fd097a93cf` | `631880804300` | `631880804300` | `units_added` | 1 | unverändert akzeptiert | keine | – | Vollständig und klinisch präzise; units_added (cm) durch Abkürzung von ausgeschriebenem „centímetros“ ausgelöst. |
| `ES100571` | `es` | `31078842a33e` | `f33b74a8bb64` | `891206fee495` | – | 2 | korrigiert akzeptiert | vorhanden | `Terminologie` | „adenocarcinoma de próstata“ zu „Prostatakarzinom“ verallgemeinert; Kasusfehler korrigiert |
| `ES100587` | `es` | `2fb2ff658cf4` | `9e6ee708944a` | `9e6ee708944a` | – | 1 | unverändert akzeptiert | keine | – | Publikationsreif; Abkürzung „DSG“ sachlich korrekt zu „glutenfreie Ernährung“ aufgelöst. |
| `ES100631` | `es` | `dc23f2490c2d` | `e637ff598b09` | `98a3eb28de23` | `units_added` | 3 | korrigiert akzeptiert | vorhanden | `Zahl oder Einheit` | Stille Einheitenänderung aller „UI/ml“-Laborwerte zu „U/l“ (Faktor 1.000, bei CA 19-9 sachlich falsch) auf Quellniveau „U/ml“ zurückgeführt. |
| `ES100688` | `es` | `ba749414b9bd` | `8c785fe295cd` | `8c785fe295cd` | – | 2 | unverändert akzeptiert | keine | – | Klinisch treffend; im Quelltext nicht eingeführte Abkürzungen „SMR“ und „QG“ kontextuell eindeutig aufgelöst. |
| `ES100727` | `es` | `96457f147de5` | `9f8c1fba7bbe` | `9f8c1fba7bbe` | – | 1 | unverändert akzeptiert | keine | – | Vollständige und präzise Übersetzung; kleinere Tippfehler der Quelle still geglättet. |
| `ES100775` | `es` | `3fd67377d9c0` | `5f530bb51e1a` | `5f530bb51e1a` | – | 1 | unverändert akzeptiert | keine | – | Vollständig und klinisch exakt; Erregername durch Markdown-Sternchen kursiviert. |
| `ES100789` | `es` | `34e2542bb907` | `c39b28985e4f` | `c39b28985e4f` | – | 1 | unverändert akzeptiert | keine | – | Vollständig und klinisch präzise übertragen; Trennungsartefakt „con-trol“ still geglättet. |
| `ES100809` | `es` | `79a66ed74c6f` | `f59d59bd9ee8` | `addd5b8335a8` | – | 3 | korrigiert akzeptiert | vorhanden | `Negation oder Aussagesicherheit` | Fehldeutung von „[radiografía] de pelvis“ als Ausschluss einer Beckenfraktur, Verkürzung von „rama isquiopubiana“ und Aufwertung von „policontusionado“ zu „Polytrauma“ korrigiert. |
| `ES100896` | `es` | `5ee1da6b3ef3` | `d90d90dfd2da` | `d90d90dfd2da` | `units_added` | 1 | unverändert akzeptiert | keine | – | Vollständig und klinisch präzise; units_added (mmhg) durch Zusammenschreibung von „mm Hg“ zu „mmHg“ ausgelöst. |
| `FR100132` | `fr` | `f3e107a8fb05` | `803d62e75781` | `2005e5a5f1aa` | `units_added` | 2 | korrigiert akzeptiert | vorhanden | `Terminologie` | Dermatologischer Fachterminus „peau de chagrin“ als „Haifischhaut“ fehlübersetzt; Standardeinheit mmHg beim Augeninnendruck ergänzt (units_added). |
| `FR100142` | `fr` | `8f49c11ab205` | `d59a68c21dfc` | `d59a68c21dfc` | `units_added` | 1 | unverändert akzeptiert | keine | – | Inhaltlich und numerisch vollständig korrekte Übersetzung; units_added-Warnung (IE) beruht auf regulärer Übersetzung von französisch UI/ml zu deutsch IE/ml. |
| `FR100185` | `fr` | `4f61dd20324f` | `2c9f6eac9685` | `e58fbd7911e7` | – | 3 | korrigiert akzeptiert | vorhanden | `Hinzufügung` | Unbelegte Malignitätspräzisierung („tumeur du sein“ -> „Mammakarzinom“) und Aufwertung der Aussagesicherheit im MRT („équivoque“ -> „verdächtig“). |
| `FR100255` | `fr` | `5cf590d3f68f` | `76c6b58d7ef2` | `8c68986cec61` | – | 2 | korrigiert akzeptiert | vorhanden | `Terminologie` | Geburtshilflicher Terminus „contracture utérine“ (Dauerkontraktion/Uteruskontraktur) zu „Uteruskontraktionen“ (Wehen) verwässert; unbelegte Projektionsangabe „a.p.-Aufnahme“. |
| `FR100314` | `fr` | `d75823ee8584` | `c343e1c63ff0` | `c343e1c63ff0` | – | 2 | unverändert akzeptiert | keine | – | Inhaltlich treue Übersetzung mit mehreren sachlich zwingenden stillen Reparaturen schwerer Quellkorruptionen („Accoure“, „le patient“, „signes isthmiques“). |
| `FR100346` | `fr` | `91223ec0b5b0` | `006e6aafffce` | `93fbf2939c75` | – | 2 | korrigiert akzeptiert | vorhanden | `Terminologie` | Expliziter Phänotypbegriff „polypnée“ zu neutraler Atemfrequenzangabe abgeschwächt, unbelegter Zeitbezug („ursprünglich“) beim MRT und Genusfehler bei „Angiomyolipom“. |
| `FR100360` | `fr` | `7bfa0fef0cff` | `5f0a7ded0097` | `5f0a7ded0097` | – | 1 | unverändert akzeptiert | keine | – | Vollständige und klinisch präzise Übersetzung; ein im Quelltext angelegter Seitenwiderspruch zwischen Schädel-CT und Schädel-MRT wurde originalgetreu bewahrt. |
| `FR100448` | `fr` | `add4fbab0a41` | `673ba6074586` | `6d54e6d4a437` | – | 3 | korrigiert akzeptiert | vorhanden | `Anatomie oder Lateralität` | Anatomische Fehllokalisation des Primärtumors: „au niveau du Fowler droit“ (apikales Unterlappensegment, Segment VI) wurde als „im rechten Lungenoberfeld“ übersetzt. |
| `FR100453` | `fr` | `5acf55bff1f2` | `0d2aeb370966` | `0d2aeb370966` | – | 1 | unverändert akzeptiert | keine | – | Publikationsreife, Satz für Satz und in allen klinischen Phänotypen sowie Negationen vollständig deckungsgleiche Übersetzung. |
| `FR100480` | `fr` | `4811e2cccf86` | `c1a6e7af3f0a` | `c1cfd57fef9f` | – | 1 | korrigiert akzeptiert | keine | – | Inhaltlich und klinisch vollständig treue Übersetzung; lediglich ein kleiner Schreibfehler („Positonen-Emissions-Tomographie“) korrigiert. |
| `FR100632` | `fr` | `1d9cc4d0ff52` | `27f5d1696e5c` | `56c1a8d911cd` | `units_added` | 2 | korrigiert akzeptiert | keine | – | Inhaltlich präzise; grammatischer Genusfehler („Der Thoraxübersichtsröntgen“) und unbelegte Projektionsspezifizierung („p.a.-Aufnahme“ für „de face“) korrigiert, stille Reparaturen und Einheitenkonvertierung (UI/l -> U/l) dokumentiert. |
| `FR100748` | `fr` | `8a5b2c6bb247` | `0e4ac133134d` | `0e4ac133134d` | `units_added` | 1 | unverändert akzeptiert | keine | – | Vollständige und klinisch präzise Übersetzung; `units_added`-Meldung (`mm, mmhg`) beruht auf der Normalisierung von `mm de Hg` zu `mmHg` und `55x45x50 mm`. |
| `FR100780` | `fr` | `1ca578b718db` | `d26a8eeb7717` | `a59f871acab3` | – | 2 | korrigiert akzeptiert | vorhanden | `Terminologie` | Zwei Korrekturen: widersprüchlicher Zusatz bei der Paritätsangabe entfernt und `détresse respiratoire` des Frühgeborenen von „Atemnot“ zu „Atemnotsyndrom“ präzisiert. |
| `FR100806` | `fr` | `14d89b05ec10` | `ef4b4650dd5f` | `ef4b4650dd5f` | `units_added` | 1 | unverändert akzeptiert | keine | – | Sehr genaue und vollständige Übersetzung; `units_added` (`ie`) resultiert aus der regulären Eindeutschung von `UI/l` zu `IE/l` bei der LDH. |
| `FR100814` | `fr` | `525f40f64e80` | `b7e80ef18f90` | `b7e80ef18f90` | – | 1 | unverändert akzeptiert | keine | – | Kurzer, bildgebungsfokussierter Fallbericht ohne sinnverändernde Abweichungen; leichte anatomische Explizierung dokumentiert. |
| `FR100874` | `fr` | `f7a3e1bf86c2` | `48723a57ca68` | `48723a57ca68` | – | 1 | unverändert akzeptiert | keine | – | Vollständige und präzise Übersetzung einschließlich aller Vitalparameter, Laborwerte und des 13-fachen PTH-Anstiegs. |
| `FR100882` | `fr` | `5ada5d626814` | `f683dff7e681` | `f683dff7e681` | – | 1 | unverändert akzeptiert | keine | – | Referenzfall aus der 30er-Machbarkeitskohorte (Note 1): inhaltlich vollständig und präzise; stille Reparatur von `anatonomo-cyto-pathologie` und `prise en neurochirurgicalement` dokumentiert. |
| `FR100883` | `fr` | `dee3fb193b90` | `c7a0ad1ef900` | `c7a0ad1ef900` | – | 1 | unverändert akzeptiert | keine | – | Vollständige und fehlerfreie Übersetzung; stille Reparatur des Quelltippfehlers `surface polyploïde` zu `polypöser Oberfläche` dokumentiert. |
| `FR100946` | `fr` | `dd73d626a118` | `dc0ee29bf74c` | `12bdc33e72ca` | – | 2 | korrigiert akzeptiert | vorhanden | `Negation oder Aussagesicherheit` | Aufwertung der Aussagesicherheit beim histopathologischen Befund (`était en faveur de` -> „bestätigte“) korrigiert und Pleonasmus „Gliom-Tumor“ geglättet; stille Reparatur von `doigt de gans` dokumentiert. |
| `FR100998` | `fr` | `0b17d0c9c367` | `b5966fd0d657` | `def2232bf765` | – | 2 | korrigiert akzeptiert | vorhanden | `Negation oder Aussagesicherheit` | Zeitlich-logische Verschiebung durch Fehlübersetzung von `alors que` als „nachdem“ korrigiert und `pronostique vital` zu „Überlebensprognose“ präzisiert. |

## 4. Detaillierte Dokumentation aller vorgenommenen Textkorrekturen

Im Folgenden sind sämtliche Fälle aufgeführt, in denen die `Korrigierte Endfassung` gegenüber der `TLLM-Ausgangsfassung` angepasst wurde (`decision = korrigiert akzeptiert`), mit wörtlichem Originalzitat, TLLM-Formulierung, korrigierter Fassung und medizinischer Begründung.

### `EN100184` (EN) — Note 2 · Klinische Änderung: `Terminologie`

- **Zusammenfassende Änderungsbegründung:** „The review of systems“ im Anamneseabsatz bezeichnet die Systemanamnese und nicht die körperliche Untersuchung (die erst später im Text folgt).
- **Korrektur 1 (`moderate` / `Terminologie`):**
  - **Quelle:** `The review of systems was essentially normal;`
  - **TLLM:** „Die allgemeine körperliche Untersuchung (Organsysteme) war unauffällig;“
  - **Korrigiert:** „Die Systemanamnese war im Wesentlichen unauffällig;“
  - **Begründung:** „Review of systems“ bezeichnet die Systemanamnese; die Übersetzung als „allgemeine körperliche Untersuchung (Organsysteme)“ verwechselt Anamnese und Untersuchungsbefund.

### `EN100427` (EN) — Note 1 · Rein sprachlich/orthografisch (`clinical_change = keine`)

- **Korrektur 1 (`minor` / `Grammatik`):**
  - **Quelle:** `The left fallopian tube was grossly unremarkable and the left ovary was atrophied.`
  - **TLLM:** „Der linke Eileiter war makroskopisch unauffällig, der linke Ovar atrophiert.“
  - **Korrigiert:** „Der linke Eileiter war makroskopisch unauffällig, das linke Ovar atrophiert.“
  - **Begründung:** Korrektur des grammatischen Genus im Deutschen („das Ovar“, Neutrum statt Maskulinum).

### `EN100466` (EN) — Note 2 · Klinische Änderung: `Hinzufügung`

- **Zusammenfassende Änderungsbegründung:** Die Quelle nennt präoperativ allgemein „staging for ovarian malignancy“, während TLLM dies unbelegt zu „Ovarialkarzinom“ verengt (die spätere Histologie ergibt tatsächlich ein großzelliges B-Zell-Lymphom und kein Karzinom).
- **Korrektur 1 (`moderate` / `Hinzufügung`):**
  - **Quelle:** `The patient was taken for surgical exploration and staging for ovarian malignancy.`
  - **TLLM:** „Die Patientin wurde zur chirurgischen Exploration und zum Staging bei Verdacht auf ein Ovarialkarzinom aufgenommen.“
  - **Korrigiert:** „Die Patientin wurde zur chirurgischen Exploration und zum Staging bei Verdacht auf ein Ovarialmalignom aufgenommen.“
  - **Begründung:** „Ovarian malignancy“ bezeichnet allgemein ein Ovarialmalignom (zumal präoperativ auch AFP und Beta-HCG bestimmt wurden und die Histologie letztlich ein B-Zell-Lymphom ergab); die Verengung auf „Ovarialkarzinom“ fügt eine nicht quellenbelegte histologische Spezifizierung hinzu.

### `EN100682` (EN) — Note 2 · Klinische Änderung: `Hinzufügung`

- **Zusammenfassende Änderungsbegründung:** Rücknahme der unbelegten kardiologischen Spezifizierung „plötzlichem Herztod“ auf „plötzlichem Tod“ (sudden death, HP:0001699 vs. HP:0001645).
- **Korrektur 1 (`moderate` / `Hinzufügung`):**
  - **Quelle:** `He no family history of heart disease or sudden death.`
  - **TLLM:** „hinsichtlich Herzerkrankungen oder plötzlichem Herztod vor.“
  - **Korrigiert:** „hinsichtlich Herzerkrankungen oder plötzlichem Tod vor.“
  - **Begründung:** „Sudden death“ (HP:0001699) wird analog zu FR100275 nicht zu „plötzlichem Herztod“ (HP:0001645) spezifiziert, da Familienbefunde nach R0/R3 annotiert werden.

### `EN107405` (EN) — Note 2 · Klinische Änderung: `Terminologie`

- **Zusammenfassende Änderungsbegründung:** In der TLLM-Fassung entfiel an beiden Stellen das diagnostisch relevante Attribut 'freies' bei 'urinary free cortisol excretion rate' ('Cortisolausscheidung im Urin' statt 'Ausscheidungsrate von freiem Cortisol im Urin' / '24-Stunden-Ausscheidungsrate von freiem Cortisol im Urin'); zudem wurde die grammatisch fehlerhafte doppelte Negation 'keine erhöhte Stoffwechselaktivität weder in der Lungenläsion noch in der Hypophyse' korrigiert.
- **Korrektur 1 (`minor` / `Negation oder Aussagesicherheit`):**
  - **Quelle:** `failed to show increased metabolic activity in the lung lesion or in her pituitary gland.`
  - **TLLM:** „zeigten keine erhöhte Stoffwechselaktivität weder in der Lungenläsion noch in der Hypophyse.“
  - **Korrigiert:** „zeigten weder in der Lungenläsion noch in der Hypophyse eine erhöhte Stoffwechselaktivität.“
  - **Begründung:** Beseitigung der im Standarddeutschen grammatisch fehlerhaften und logisch doppelten Verneinung ('keine ... weder ... noch').
- **Korrektur 2 (`moderate` / `Terminologie`):**
  - **Quelle:** `Despite initial normalization of her urinary free cortisol excretion rate,`
  - **TLLM:** „Trotz einer anfänglichen Normalisierung der Cortisolausscheidung im Urin“
  - **Korrigiert:** „Trotz einer anfänglichen Normalisierung der Ausscheidungsrate von freiem Cortisol im Urin“
  - **Begründung:** Im Quelltext wird spezifisch die Ausscheidungsrate des freien Urincortisols ('urinary free cortisol excretion rate', UFC) genannt; 'freiem' war in der Übersetzung ausgelassen.
- **Korrektur 3 (`moderate` / `Terminologie`):**
  - **Quelle:** `normalization of our patient's 24-hour urinary free cortisol excretion rate`
  - **TLLM:** „Normalisierung der 24-Stunden-Cortisolausscheidung im Urin“
  - **Korrigiert:** „Normalisierung der 24-Stunden-Ausscheidungsrate von freiem Cortisol im Urin“
  - **Begründung:** Wiederherstellung des ausgelassenen Attributs 'freiem' ('urinary free cortisol excretion rate') analog zum ersten Vorkommen.

### `ES100002` (ES) — Note 2 · Klinische Änderung: `Anatomie oder Lateralität`

- **Zusammenfassende Änderungsbegründung:** Im Original steht „tumor de vías de uréter derecho“ (Urotheltumor des rechten Ureters), was TLLM zu „Tumor der rechten Harnwege“ verallgemeinert hat; auf „Urotheltumor des rechten Ureters“ präzisiert.
- **Korrektur 1 (`minor` / `Anatomie oder Lateralität`):**
  - **Quelle:** `la sospecha de tumor de vías de uréter derecho`
  - **TLLM:** „des Verdachts auf einen Tumor der rechten Harnwege“
  - **Korrigiert:** „des Verdachts auf einen Urotheltumor des rechten Ureters“
  - **Begründung:** Im Spanischen bezeichnet „tumor de vías“ verkürzt einen Urotheltumor („tumor de vías urinarias“) mit expliziter Lokalisation „de uréter derecho“. „Tumor der rechten Harnwege“ lässt die spezifische Ureterlokalisation fallen.

### `ES100063` (ES) — Note 2 · Rein sprachlich/orthografisch (`clinical_change = keine`)

- **Korrektur 1 (`minor` / `Grammatik / Satzbau`):**
  - **Quelle:** `una pieza de 6 x 8 cm. de consistencia elástica`
  - **TLLM:** „ein Präparat von 6 x 8 cm Größe. ...von elastischer Konsistenz“
  - **Korrigiert:** „ein Präparat von 6 x 8 cm Größe von elastischer Konsistenz“
  - **Begründung:** In der spanischen Quelle stand nach der Abkürzung „cm.“ ein Punkt, den TLLM fälschlich als Satzende interpretierte und mit „...von“ fortsetzte.

### `ES100182` (ES) — Note 1 · Rein sprachlich/orthografisch (`clinical_change = keine`)

- **Korrektur 1 (`minor` / `Grammatik / Satzbau`):**
  - **Quelle:** `Sin embargo, una vez estabilizadas las constantes vitales, se realiza cistoscopia que demuestra`
  - **TLLM:** „Nach Stabilisierung der Vitalparameter durchgeführte Zystoskopie ergab jedoch“
  - **Korrigiert:** „Eine nach Stabilisierung der Vitalparameter durchgeführte Zystoskopie ergab jedoch“
  - **Begründung:** Im Deutschen fehlte der Artikel vor der Partizipialkonstruktion „durchgeführte Zystoskopie“.

### `ES100214` (ES) — Note 2 · Klinische Änderung: `Terminologie`

- **Zusammenfassende Änderungsbegründung:** „aclaramiento urinario de creatinina“ bezeichnet spezifisch die über den Sammelurin gemessene urinäre Kreatinin-Clearance (in Abgrenzung zur peritonealen Clearance unter APD und zur berechneten Clearance nach Schwartz-Formel); die Übersetzung „renale Kreatinin-Clearance“ verwischt die Messmethode.
- **Korrektur 1 (`moderate` / `Terminologie`):**
  - **Quelle:** `por aclaramiento urinario de creatinina`
  - **TLLM:** „basierend auf der renalen Kreatinin-Clearance“
  - **Korrigiert:** „basierend auf der urinären Kreatinin-Clearance“
  - **Begründung:** Im Kontext der Peritonealdialyse unterscheidet „aclaramiento urinario de creatinina“ die direkt im Urin gemessene Kreatinin-Clearance von der peritonealen Clearance und der Schätzformel nach Schwartz.

### `ES100280` (ES) — Note 1 · Klinische Änderung: `Hinzufügung`

- **Zusammenfassende Änderungsbegründung:** „efecto masa en hipogastrio“ wurde zu „im Unterbauch war eine Raumforderung tastbar“ verengt; auf „Raumforderungseffekt im Unterbauch (Hypogastrium)“ korrigiert, da die Quelle die Untersuchungsmodalität (Palpation vs. klinischer/bildgebender Masseneffekt) offenlässt.
- **Korrektur 1 (`minor` / `Hinzufügung`):**
  - **Quelle:** `presentó dolor abdominal y efecto masa en hipogastrio.`
  - **TLLM:** „im Unterbauch war eine Raumforderung tastbar.“
  - **Korrigiert:** „zudem zeigte sich ein Raumforderungseffekt im Unterbauch (Hypogastrium).“
  - **Begründung:** Die Quelle nennt „efecto masa en hipogastrio“ (Raumforderungseffekt/Masseneffekt im Hypogastrium), ohne explizit „tastbar“ (palpatorisch) anzugeben.

### `ES100304` (ES) — Note 2 · Klinische Änderung: `Zahl oder Einheit`

- **Zusammenfassende Änderungsbegründung:** Die Aufteilung der täglichen Proteinmenge auf Frühstück, Mittag- und Abendessen `(5-10 y 10 g)` (d. h. 5, 10 und 10 g = 25 g/Tag) wurde im Deutschen zu `(5–10 g bzw. 10 g)` verkürzt, wodurch eine der drei Mahlzeitenangaben als Bereich statt als Einzelwert erschien.
- **Korrektur 1 (`minor` / `Zahl oder Einheit`):**
  - **Quelle:** `repartidas en desayuno, comida y cena (5-10 y 10 g)`
  - **TLLM:** „verteilt auf Frühstück, Mittag- und Abendessen (5–10 g bzw. 10 g).“
  - **Korrigiert:** „verteilt auf Frühstück, Mittag- und Abendessen (5, 10 und 10 g).“
  - **Begründung:** Im Spanischen steht „5-10 y 10 g“ für die drei Mahlzeiten Frühstück (5 g), Mittagessen (10 g) und Abendessen (10 g), passend zur Gesamtsumme von 20–25 g/Tag; „5–10 g bzw. 10 g“ gibt nur zwei Posten an.

### `ES100412` (ES) — Note 2 · Klinische Änderung: `Terminologie`

- **Zusammenfassende Änderungsbegründung:** „glaucoma agudo secundario a dicha masa“ bezeichnet explizit ein sekundäres akutes Glaukom; im Deutschen wurde „sekundär“ nur frei über „ausgelöst durch“ umschrieben.
- **Korrektur 1 (`minor` / `Terminologie`):**
  - **Quelle:** `fue compatible con glaucoma agudo secundario a dicha masa presente en cámara anterior.`
  - **TLLM:** „entsprach einem akuten Glaukom, ausgelöst durch die Raumforderung in der Vorderkammer.“
  - **Korrigiert:** „entsprach einem sekundären akuten Glaukom infolge dieser Raumforderung in der Vorderkammer.“
  - **Begründung:** Erhalt des expliziten Fachterminus „sekundäres akutes Glaukom“ („glaucoma agudo secundario“).

### `ES100513` (ES) — Note 2 · Klinische Änderung: `Anatomie oder Lateralität`

- **Zusammenfassende Änderungsbegründung:** Im ersten Satz steht „anquílosis mandibular“ (Unterkieferankylose, HPO-relevant), während das Kiefergelenk („articulación témporomandibular“) erst im zweiten Satz genannt wird; TLLM hat bereits im ersten Satz zu „Kiefergelenksankylose“ spezifiziert.
- **Korrektur 1 (`minor` / `Anatomie oder Lateralität`):**
  - **Quelle:** `Mediante RMN confirmamos anquílosis mandibular`
  - **TLLM:** „Mittels MRT wurde eine Kiefergelenksankylose bestätigt,“
  - **Korrigiert:** „Mittels MRT wurde eine Unterkieferankylose (mandibuläre Ankylose) bestätigt,“
  - **Begründung:** Wahrung der exakten anatomischen Bezeichnung der Quelle („anquílosis mandibular“) im ersten Satz; die Spezifizierung auf das Kiefergelenk erfolgt im Original erst im darauffolgenden Satz.

### `ES100571` (ES) — Note 2 · Klinische Änderung: `Terminologie`

- **Zusammenfassende Änderungsbegründung:** Präzisierung von „Prostatakarzinoms“ auf „Adenokarzinoms der Prostata“ entsprechend dem Quelltext (adenocarcinoma de próstata, HP:0034925); zudem Korrektur eines deutschen Kasusfehlers.
- **Korrektur 1 (`moderate` / `Terminologie`):**
  - **Quelle:** `Intervenido de adenocarcinoma de próstata`
  - **TLLM:** „Er war zuvor wegen eines Prostatakarzinoms operiert worden“
  - **Korrigiert:** „Er war zuvor wegen eines Adenokarzinoms der Prostata operiert worden“
  - **Begründung:** Wahrung der histologischen Spezifität „Adenokarzinom der Prostata“ (HP:0034925) statt Verallgemeinerung auf „Prostatakarzinom“ (HP:0012125).
- **Korrektur 2 (`minor` / `Grammatik`):**
  - **Quelle:** `Una semana después del inicio del tratamiento, el paciente fue dado de alta`
  - **TLLM:** „Eine Woche nach Behandlungsbeginn wurde der Patienten entlassen;“
  - **Korrigiert:** „Eine Woche nach Behandlungsbeginn wurde der Patient entlassen;“
  - **Begründung:** Grammatikkorrektur im Deutschen (Nominativ Singular „der Patient“ statt „der Patienten“ im Passivsatz).

### `ES100631` (ES) — Note 3 · Klinische Änderung: `Zahl oder Einheit`

- **Zusammenfassende Änderungsbegründung:** TLLM hat sämtliche in der Quelle mit „UI/ml“ angegebenen Laborwerte (GOT, GPT, GGT, AP, LDH, IgG sowie CA 19-9) stillschweigend um drei Größenordnungen auf „U/l“ geändert und damit u. a. die bei CA 19-9 korrekte Einheit (82 U/ml) verfälscht.
- **Korrektur 1 (`critical` / `Zahl oder Einheit`):**
  - **Quelle:** `GOT 110 UI/ml, GPT 371 UI/ml, GGT 632 UI/ml, FA 787 UI/ml, LDH 394 UI/ml. Amilasa y lipasa fueron normales en todo momento. Destacaba también una hipergammaglobulinemia (gammaglobulina 1,56%), con IgG 1840 UI/ml (751-1.560 UI/ml). El marcador CA 19-9 era de 82 UI/ml.`
  - **TLLM:** „GOT 110 U/l, GPT 371 U/l, GGT 632 U/l, AP 787 U/l, LDH 394 U/l. Amylase- und Lipasewerte lagen durchgehend im Normbereich. Auffällig war zudem eine Hypergammaglobulinämie (Gammaglobulin 1,56 %) mit einem IgG-Wert von 1840 U/l (Normbereich: 751–1560 U/l). Der Tumormarker CA 19-9 lag bei 82 U/l.“
  - **Korrigiert:** „GOT 110 U/ml, GPT 371 U/ml, GGT 632 U/ml, AP 787 U/ml, LDH 394 U/ml. Amylase- und Lipasewerte lagen durchgehend im Normbereich. Auffällig war zudem eine Hypergammaglobulinämie (Gammaglobulin 1,56 %) mit einem IgG-Wert von 1840 U/ml (Normbereich: 751–1560 U/ml). Der Tumormarker CA 19-9 lag bei 82 U/ml.“
  - **Begründung:** Wiederherstellung der Quelleinheit U/ml (UI/ml): TLLM hatte alle Werte stillschweigend um drei Größenordnungen auf U/l verschoben und dabei insbesondere die klinisch korrekte Einheit von CA 19-9 (82 U/ml) zu 82 U/l verfälscht.

### `ES100809` (ES) — Note 3 · Klinische Änderung: `Negation oder Aussagesicherheit`

- **Zusammenfassende Änderungsbegründung:** Aufgrund eines fehlenden Kommas in der Quelle („sin fracturas costales de pelvis“) machte TLLM aus der Beckenröntgenaufnahme den negierten Befund „keine Rippen- oder Beckenfrakturen“ im Thoraxröntgen (im direkten Widerspruch zur nachfolgend beschriebenen Beckenfraktur), verkürzte „rama isquiopubiana“ auf „Schambeinast“ und wertete „policontusionado“ unzulässig zu einem „Polytrauma“ auf.
- **Korrektur 1 (`critical` / `Negation oder Aussagesicherheit`):**
  - **Quelle:** `a la realización de radiografía de tórax compatible con contusión pulmonar leve sin fracturas costales de pelvis y TAC cervical y abdominopélvico en los que se evidenció fractura de la rama isquiopubiana izquierda sin desplazamiento,`
  - **TLLM:** „Zudem wurden ein Thoraxröntgen (vereinbar mit einer leichten Lungenkontusion, keine Rippen- oder Beckenfrakturen) sowie CT-Aufnahmen der Halswirbelsäule und des Abdomens/Beckens durchgeführt. Letztere zeigten eine nicht dislozierte Fraktur des linken Schambeinastes,“
  - **Korrigiert:** „Zudem wurden ein Thoraxröntgen (vereinbar mit einer leichten Lungenkontusion ohne Rippenfrakturen), ein Beckenröntgen sowie CT-Aufnahmen der Halswirbelsäule und des Abdomens/Beckens durchgeführt. Letztere zeigten eine nicht dislozierte Fraktur des linken Sitz-Schambeinastes (Ramus ischiopubicus),“
  - **Begründung:** Korrektur der durch ein fehlendes Quellkomma („sin fracturas costales [,] de pelvis“) entstandenen widersprüchlichen Negation „keine Beckenfrakturen“ im Thoraxröntgen bei tatsächlich vorliegender Beckenfraktur sowie präzise anatomische Wiedergabe von „rama isquiopubiana“ als Sitz-Schambeinast (Ramus ischiopubicus).
- **Korrektur 2 (`moderate` / `Terminologie`):**
  - **Quelle:** `Siendo diagnosticado como policontusionado, ingresó en la Unidad de Cuidados Intensivos`
  - **TLLM:** „Nach der Diagnose eines Polytraumas (mit Schwerpunkt auf multiplen Kontusionen) erfolgte die Aufnahme auf die Intensivstation.“
  - **Korrigiert:** „Mit der Diagnose multipler Prellungen (Polycontusio) erfolgte die Aufnahme auf die Intensivstation.“
  - **Begründung:** „policontusionado“ bezeichnet multiple Prellungen/Kontusionen ohne lebensbedrohliche Verletzungsschwere und darf nicht zum klinischen Schwerstverletztenbegriff „Polytrauma“ aufgewertet werden.

### `FR100132` (FR) — Note 2 · Klinische Änderung: `Terminologie`

- **Zusammenfassende Änderungsbegründung:** Der dermatologische Phänotypbegriff „peau de chagrin“ (Chagrinlederhaut/Chagrinhaut bei Pseudoxanthoma elasticum) wurde im Deutschen unzutreffend als „Haifischhaut“ (Assoziation mit Ichthyosen) wiedergegeben.
- **Korrektur 1 (`moderate` / `Terminologie`):**
  - **Quelle:** `la peau avait un aspect de nappes fripées en "peau de chagrin" ou de "drapé"`
  - **TLLM:** „vergleichbar mit „Haifischhaut“ oder einem drapierten Stoff.“
  - **Korrigiert:** „vergleichbar mit „Chagrinlederhaut“ (Peau de chagrin) oder einem drapierten Stoff.“
  - **Begründung:** „Peau de chagrin“ bezeichnet in der Dermatologie die Chagrinlederhaut (genarbtes Leder, klassisch u. a. bei Pseudoxanthoma elasticum), während „Haifischhaut“ im Deutschen auf Ichthyosen verweist.

### `FR100185` (FR) — Note 3 · Klinische Änderung: `Hinzufügung`

- **Zusammenfassende Änderungsbegründung:** Die Quelle nennt anamnestisch lediglich „une tumeur du sein gauche“ (Tumor der linken Brust), woraus die Übersetzung ein „Mammakarzinom“ macht; zudem wird die unsichere MRT-Beurteilung „équivoque de métastase“ (nicht eindeutig / äquivok) zu „verdächtig auf eine ... Metastase“ aufgewertet.
- **Korrektur 1 (`critical` / `Hinzufügung`):**
  - **Quelle:** `suivie depuis quatre ans pour une tumeur du sein gauche`
  - **TLLM:** „wegen eines Mammakarzinoms der linken Brust“
  - **Korrigiert:** „wegen eines Tumors der linken Brust“
  - **Begründung:** Die Quelle verwendet den neutralen Begriff „tumeur“; die Spezifizierung als „Mammakarzinom“ ist im Text nicht explizit belegt, auch wenn Therapie und Verlauf für Malignität sprechen.
- **Korrektur 2 (`minor` / `Anatomie oder Lateralität`):**
  - **Quelle:** `une lourdeur du membre supérieur gauche`
  - **TLLM:** „ein Schweregefühl im linken Arm.“
  - **Korrigiert:** „ein Schweregefühl in der linken oberen Extremität.“
  - **Begründung:** Präzisierung der anatomischen Angabe „membre supérieur gauche“ analog zum Folgesatz („obere Extremität“).
- **Korrektur 3 (`critical` / `Negation oder Aussagesicherheit`):**
  - **Quelle:** `L'aspect IRM est équivoque de métastase envahissant le plexus brachial.`
  - **TLLM:** „Das MRT-Bild ist verdächtig auf eine den Plexus brachialis infiltrierende Metastase.“
  - **Korrigiert:** „Das MRT-Bild ist hinsichtlich einer den Plexus brachialis infiltrierenden Metastase nicht eindeutig (äquivok).“
  - **Begründung:** „Équivoque“ bedeutet mehrdeutig/nicht eindeutig. Die Übersetzung als „verdächtig auf“ wertet die diagnostische Sicherheit unzulässig auf.

### `FR100255` (FR) — Note 2 · Klinische Änderung: `Terminologie`

- **Zusammenfassende Änderungsbegründung:** „Sans saignement ni contracture utérine“ prüft bei Eklampsie das Fehlen einer pathologischen Uteruskontraktur (Dauerkontraktion als Zeichen einer vorzeitigen Plazentalösung); die Übersetzung „Uteruskontraktionen“ verwechselt dies mit regulärer Wehentätigkeit. Zudem spezifiziert „a.p.-Aufnahme“ für „de face“ unbelegt den Strahlengang.
- **Korrektur 1 (`moderate` / `Terminologie`):**
  - **Quelle:** `sans saignement ni contracture utérine.`
  - **TLLM:** „ohne Blutungen oder Uteruskontraktionen.“
  - **Korrigiert:** „ohne Blutungen oder Uteruskontraktur.“
  - **Begründung:** „Contracture utérine“ bezeichnet den pathologischen Uterushypertonus (Dauerkontraktion, z. B. bei Abruptio placentae), nicht normale „contractions utérines“ (Wehen).
- **Korrektur 2 (`minor` / `Hinzufügung`):**
  - **Quelle:** `Une radio pulmonaire de face`
  - **TLLM:** „Eine Röntgenaufnahme des Thorax (a.p.-Aufnahme)“
  - **Korrigiert:** „Eine Röntgenaufnahme des Thorax (Frontalaufnahme)“
  - **Begründung:** „De face“ gibt nur die frontale Aufnahmeebene an, legt aber nicht fest, ob der Strahlengang a.p. oder p.a. erfolgte.

### `FR100346` (FR) — Note 2 · Klinische Änderung: `Terminologie`

- **Zusammenfassende Änderungsbegründung:** Der explizite klinische Phänotyp „polypnée à 30 cycles/min“ wurde zu „eine Atemfrequenz von 30 Zügen/min“ neutralisiert, und „pneumopathie bilatérale“ wurde zu „beidseitige Lungenveränderung“ verallgemeinert. Zudem wurde beim zerebrospinalen MRT unbelegt „ursprünglich“ ergänzt.
- **Korrektur 1 (`moderate` / `Terminologie`):**
  - **Quelle:** `une polypnée à 30 cycles/min,`
  - **TLLM:** „eine Atemfrequenz von 30 Zügen/min,“
  - **Korrigiert:** „eine Polypnoe mit 30 Atemzügen/min,“
  - **Begründung:** „Polypnée“ ist ein expliziter pathologischer Phänotypbegriff (HP:0002789) und sollte für die HPO-Extraktion nicht auf den neutralen Vitalparameter „Atemfrequenz“ reduziert werden.
- **Korrektur 2 (`minor` / `Terminologie`):**
  - **Quelle:** `une pneumopathie bilatérale étendue et mal limitée.`
  - **TLLM:** „eine ausgedehnte, unscharf begrenzte beidseitige Lungenveränderung.“
  - **Korrigiert:** „eine ausgedehnte, unscharf begrenzte beidseitige Pneumopathie.“
  - **Begründung:** „Pneumopathie“ (hier im Kontext einer fieberhaften bakteriellen Infektion) wird durch „Lungenveränderung“ unnötig stark verallgemeinert.
- **Korrektur 3 (`minor` / `Hinzufügung`):**
  - **Quelle:** `L'IRM cérébro-médullaire, à la recherche de méningiome a montré`
  - **TLLM:** „Die MRT von Gehirn und Rückenmark, die ursprünglich zum Ausschluss eines Meningeoms durchgeführt worden war, zeigte“
  - **Korrigiert:** „Die zur Suche nach einem Meningeom durchgeführte MRT von Gehirn und Rückenmark zeigte“
  - **Begründung:** Die Quelle enthält keinen Hinweis darauf, dass die MRT „ursprünglich“ (zu einem früheren Zeitpunkt) erfolgte; die Suche nach Meningeomen ist Teil der aktuellen LAM-Abklärung.
- **Korrektur 4 (`minor` / `Terminologie`):**
  - **Quelle:** `un angiomyolipome rénal gauche`
  - **TLLM:** „einen linksseitigen renalen Angiomyolipom“
  - **Korrigiert:** „ein linksseitiges renales Angiomyolipom“
  - **Begründung:** Grammatikalische Korrektur des Genus im Deutschen (das Angiomyolipom, Neutrum).

### `FR100448` (FR) — Note 3 · Klinische Änderung: `Anatomie oder Lateralität`

- **Zusammenfassende Änderungsbegründung:** Das französische Eponym „Fowler droit“ (Segment de Fowler/Nelson = apikales Segment des Lungenunterlappens, Segment VI) wurde von TLLM fälschlich in das „rechte Lungenoberfeld“ verlegt.
- **Korrektur 1 (`minor` / `Terminologie`):**
  - **Quelle:** `Une hémi thyroïdectomie gauche a été réalisée.`
  - **TLLM:** „Es wurde eine linkseitige Hemithyreoidektomie durchgeführt.“
  - **Korrigiert:** „Es wurde eine linksseitige Hemithyreoidektomie durchgeführt.“
  - **Begründung:** Orthografische Korrektur („linksseitige“ statt „linkseitige“).
- **Korrektur 2 (`critical` / `Anatomie oder Lateralität`):**
  - **Quelle:** `au niveau du Fowler droit mesurant 40\50 mm`
  - **TLLM:** „im rechten Lungenoberfeld (Maße 40 x 50 mm)“
  - **Korrigiert:** „im rechten Fowler-Segment (apikales Unterlappensegment, Maße 40 x 50 mm)“
  - **Begründung:** „Fowler droit“ (Segment de Fowler) bezeichnet das apikale Segment des rechten Lungenunterlappens (Segment VI), nicht das rechte Lungenoberfeld.

### `FR100480` (FR) — Note 1 · Rein sprachlich/orthografisch (`clinical_change = keine`)

- **Korrektur 1 (`minor` / `Terminologie`):**
  - **Quelle:** `La Tomographie par émission de positons au 18-FDG`
  - **TLLM:** „Die 18-FDG-Positonen-Emissions-Tomographie (PET)“
  - **Korrigiert:** „Die 18-FDG-Positronen-Emissions-Tomographie (PET)“
  - **Begründung:** Rechtschreibkorrektur des Interferenzfehlers „Positonen“ (aus frz. „positons“) zu „Positronen“.

### `FR100632` (FR) — Note 2 · Rein sprachlich/orthografisch (`clinical_change = keine`)

- **Korrektur 1 (`minor` / `Terminologie`):**
  - **Quelle:** `La radiographie pulmonaire de face et la tomodensitométrie pulmonaire étaient normales.`
  - **TLLM:** „Der Thoraxübersichtsröntgen (p.a.-Aufnahme) und die Computertomographie (CT) des Thorax waren unauffällig.“
  - **Korrigiert:** „Die Thoraxröntgenaufnahme (im frontalen Strahlengang) und die Computertomographie (CT) des Thorax waren unauffällig.“
  - **Begründung:** Korrektur des falschen deutschen grammatischen Genus („Der Thoraxübersichtsröntgen“) sowie Rücknahme der nicht explizit belegten Festlegung auf „p.a.-Aufnahme“ zugunsten der quellengetreuen Frontalprojektion (`de face`).

### `FR100780` (FR) — Note 2 · Klinische Änderung: `Terminologie`

- **Zusammenfassende Änderungsbegründung:** Die Verwässerung von `détresse respiratoire` beim Frühgeborenen (1450 g) zum unspezifischen Alltagsbegriff „Atemnot“ wurde zu „Atemnotsyndrom“ korrigiert; zudem wurde der unbelegte und in sich widersprüchliche Zusatz „und hat bereits ein Kind zur Welt gebracht (Para 2)“ bereinigt.
- **Korrektur 1 (`moderate` / `Hinzufügung`):**
  - **Quelle:** `4ème gestes 2ème pare, un enfant vivant.`
  - **TLLM:** „Sie ist in ihrer vierten Schwangerschaft (Gravida 4) und hat bereits ein Kind zur Welt gebracht (Para 2); ein lebendes Kind ist vorhanden.“
  - **Korrigiert:** „Sie ist in ihrer vierten Schwangerschaft (Gravida 4, Para 2); ein lebendes Kind ist vorhanden.“
  - **Begründung:** Entfernung des in Zeile 2 nicht belegten und im unmittelbaren Zusammenspiel mit „(Para 2)“ selbstwidersprüchlichen Zusatzes „und hat bereits ein Kind zur Welt gebracht“.
- **Korrektur 2 (`moderate` / `Terminologie`):**
  - **Quelle:** `Le nouveau-né a été transféré en réanimation néonatal pour détresse respiratoire.`
  - **TLLM:** „Das Neugeborene wurde aufgrund einer Atemnot auf die neonatologische Intensivstation verlegt.“
  - **Korrigiert:** „Das Neugeborene wurde aufgrund eines Atemnotsyndroms auf die neonatologische Intensivstation verlegt.“
  - **Begründung:** Vermeidung der Phänotyp-Verwässerung: `détresse respiratoire` bezeichnet beim Frühgeborenen auf der neonatologischen Intensivstation ein neonatales Atemnotsyndrom (HP:0002643 / HP:0002098) und nicht lediglich unspezifische „Atemnot“ (Dyspnoe).

### `FR100946` (FR) — Note 2 · Klinische Änderung: `Negation oder Aussagesicherheit`

- **Zusammenfassende Änderungsbegründung:** Die Formulierung `L'analyse anatomopathologique était en faveur d'un tuberculome cérébral` wurde von „bestätigte das Vorliegen eines zerebralen Tuberkuloms“ auf die quellengetreue Modalität „sprach für ein zerebrales Tuberkulom“ zurückgeführt.
- **Korrektur 1 (`minor` / `Terminologie`):**
  - **Quelle:** `L'analyse de la spectroscopie était en faveur d'une tumeur gliale.`
  - **TLLM:** „Die spektroskopische Analyse sprach für einen Gliom-Tumor.“
  - **Korrigiert:** „Die spektroskopische Analyse sprach für einen glialen Tumor.“
  - **Begründung:** Stilistisch-terminologische Korrektur des Pleonasmus „Gliom-Tumor“ zu „glialen Tumor“ (`tumeur gliale`).
- **Korrektur 2 (`moderate` / `Negation oder Aussagesicherheit`):**
  - **Quelle:** `L'analyse anatomopathologique était en faveur d'un tuberculome cérébral.`
  - **TLLM:** „Die histopathologische Untersuchung bestätigte das Vorliegen eines zerebralen Tuberkuloms.“
  - **Korrigiert:** „Die histopathologische Untersuchung sprach für ein zerebrales Tuberkulom.“
  - **Begründung:** Rücknahme der unzulässigen Aufwertung der Aussagesicherheit: `était en faveur de` bedeutet „sprach für / war vereinbar mit“ (analog zum identisch formulierten Spektroskopie-Satz davor), nicht „bestätigte das Vorliegen“.

### `FR100998` (FR) — Note 2 · Klinische Änderung: `Negation oder Aussagesicherheit`

- **Zusammenfassende Änderungsbegründung:** Die Fehlübersetzung der adversativ-simultanen Konjunktion `alors qu'elle a développé une dyspnée` als Vorzeitigkeit („nachdem sie eine Dyspnoe entwickelt hatte“) verkehrte den zeitlichen Zusammenhang zwischen der Systemtherapie und der darunter aufgetretenen, therapierefraktären Dyspnoe.
- **Korrektur 1 (`moderate` / `Negation oder Aussagesicherheit`):**
  - **Quelle:** `alors qu'elle a développé une dyspnée actuellement classe III (classification NYHA).`
  - **TLLM:** „nachdem sie eine Dyspnoe entwickelt hatte, die aktuell dem Stadium III (nach NYHA-Klassifikation) entspricht.“
  - **Korrigiert:** „wobei sie jedoch eine Dyspnoe entwickelte, die aktuell dem Stadium III (nach NYHA-Klassifikation) entspricht.“
  - **Begründung:** Korrektur des zeitlich-kausalen Bezugs: `alors que` bezeichnet Gleichzeitigkeit bzw. einen adversativen Umstand („während / wobei sie jedoch“), nicht Vorzeitigkeit („nachdem ... entwickelt hatte“).
- **Korrektur 2 (`minor` / `Terminologie`):**
  - **Quelle:** `conditionne le pronostique vital à cours terme.`
  - **TLLM:** „bestimmt die kurzfristige Prognose.“
  - **Korrigiert:** „bestimmt die kurzfristige Überlebensprognose.“
  - **Begründung:** Erhalt der Spezifizierung `vital` (`pronostic vital` = Überlebensprognose / Prognose quoad vitam).

## 5. Auswertung aller 15 `units_added`-Prüfhinweise

In 15 der 61 Fälle hatte der automatische Check `units_added` angeschlagen (`status = automatic_check_failed`). Die Einzelprüfung ergab in **1 Fall (`ES100631`) einen klinisch relevanten Einheitenfehler** (Verschiebung von `UI/ml` zu `U/l` u. a. bei CA 19-9) und in **14 Fällen unkritische Auslöser** (Sprachkonversion `UI` → `IE`/`U`, Bindestrich-/Leerzeichennormalisierung `27-mm` → `27 mm`, Abkürzung von ausgeschriebenem `grams`/`centímetros`, Tippfehlerreparatur `38.2 0 C` → `38,2 °C` oder konventionell eindeutige Standardeinheiten wie `mmHg` beim Augeninnendruck bzw. `ng/ml` beim PSA):

| Fall | Gemeldete Tokens | Befund im Text | Bewertung & Maßnahme |
| --- | --- | --- | --- |
| `EN100123` | `g, ie, μg` | `sedation (midazolam 30 mcg/kg/hr c.iv), analgesia (fentanyl 3 mcg/kg/min c.iv), triple antibiotic regimen with meropenem 2gr q8h i.v.` → „Sedierung (Midazolam 30 µg/kg/h i.v.), eine Analgesie (Fentanyl 3 µg/kg/min i.v.), eine Dreifach-Antibiotikatherapie (Meropenem 2 g alle 8 Std. i.v.“ / `with only bemiparine 2500 b.i.d. s.c.` → „mit Bemiparin (2500 IE zweimal täglich s.c.)“ | Auslöser für units_added („g“, „µg“): „2gr“ wurde zu „2 g“ und „mcg“ zu „µg“ standardisiert. Auslöser für units_added („ie“): Konventionell eindeutige Ergänzung der Standardeinheit „IE“ (Anti-Xa-Einheiten) zur einheitenlosen Dosisangabe 2500. |
| `EN100340` | `g` | `weighing 2750 grams` → „(Gewicht: 2750 g)“ | Auslöser für units_added („g“): Das ausgeschriebene „grams“ der Quelle wurde im Deutschen als Standardeinheit „g“ abgekürzt. |
| `EN100466` | `ng, °c` | `She was febrile with a temperature of 38.2 0 C` → „Sie war fiebrig (38,2 °C)“ / `a slightly elevated cancer antigen 125 of 44U/ml (NR 0-35), serum beta human chorionic gonadotropin (HCG) of 0.258mIU/ml (NR 0-5) and alpha fetoprotein of 7 ng/ml (NR < 10).` → „einen leicht erhöhten CA-125-Wert von 44 U/ml (Normbereich: 0–35 U/ml), Serum-Beta-HCG von 0,258 mIU/ml (Normbereich: 0–5 mIU/ml) und Alpha-Fetoprotein von 7 ng/ml (Normbereich: < 10 ng/ml).“ | Auslöser für units_added („°c“) und zugleich stille Reparatur des Quelltippfehlers „38.2 0 C“ (Ziffer 0 statt Gradzeichen) zu „38,2 °C“. Auslöser für units_added („ng“): Konventionelle Wiederholung der jeweiligen Messeinheit innerhalb der Normbereichsangabe. |
| `EN100653` | `ie, u/l` | `Alcaline phosphatase was 420 UI/l. ... Vitamin D 400u/day for osteoporosis.` → „Die alkalische Phosphatase betrug 420 U/l. ... Vitamin D (400 IE/Tag) erforderlich.“ | Der automatische Check 'units_added' (ie, u/l) schlug an, weil die französisch geprägte Quelleinheit 'UI/l' in den deutschen Standard 'U/l' und das kleingeschriebene '400u/day' in '400 IE/Tag' übertragen wurde. |
| `EN103442` | `mm` | `Computed tomography showed a 27-mm, hyper-enhancing tumor in the prepyloric antrum.` → „Die Computertomografie zeigte einen 27 mm großen, stark kontrastmittelaufnehmenden Tumor im präpylorischen Antrum.“ | Falsch-positiver 'units_added'-Befund für 'mm': Im Quelltext steht '27-mm' mit Bindestrich, sodass der Tokenizer 'mm' erst in der deutschen Fassung ('27 mm') als eigenständiges Einheitentoken erkennt. |
| `ES100063` | `cm` | `aproximadamente 6x6 cm. ... una pieza de 6 x 8 cm. de consistencia elástica` → „etwa 6 x 6 cm. ... ein Präparat von 6 x 8 cm Größe“ | Der automatische Check `units_added: cm` ist ein Fehlalarm durch veränderte Wortgrenzen (`6x6` -> `6 x 6 cm`). Die Einheit `cm` steht an beiden Stellen im Original. |
| `ES100064` | `ng, u/l` | `con PSA de 794, fosfatasas alcalinas de 870 ... en sangre destacaba GGT de 86, fosfatasa alcalina de 1145, y un PSA de 121'02.` → „der PSA-Wert lag bei 794 ng/ml, die alkalische Phosphatase bei 870 U/l ... ergaben einen GGT-Wert von 86 U/l, eine alkalische Phosphatase von 1145 U/l und einen PSA-Wert von 121,02 ng/ml.“ | TLLM ergänzt bei den im Original einheitenlosen Werten für PSA (`ng/ml`, analog zu den übrigen PSA-Angaben im selben Fall) sowie alkalischer Phosphatase und GGT (`U/l`) die klinischen Standardeinheiten. |
| `ES100569` | `cm` | `una lesión quística hepática de 8 centímetros ... una lesión quística de unos 10 centímetros de diámetro` → „eine 8 cm große, multilokuläre zystische Leberläsion ... eine zystische Läsion mit einem Durchmesser von etwa 10 cm“ | Ausgeschriebene Maßangabe „centímetros“ im Deutschen standardkonform als „cm“ abgekürzt; dadurch schlug der automatische Token-Check units_added für „cm“ an. |
| `ES100631` | `u/l` | `GOT 110 UI/ml, GPT 371 UI/ml, GGT 632 UI/ml, FA 787 UI/ml, LDH 394 UI/ml ... IgG 1840 UI/ml (751-1.560 UI/ml). El marcador CA 19-9 era de 82 UI/ml.` → „GOT 110 U/l, GPT 371 U/l, GGT 632 U/l, AP 787 U/l, LDH 394 U/l ... IgG-Wert von 1840 U/l (Normbereich: 751–1560 U/l). Der Tumormarker CA 19-9 lag bei 82 U/l.“ | units_added (u/l) hat zurecht angeschlagen, da TLLM „UI/ml“ pauschal in „U/l“ umgewandelt hatte (in edits auf „U/ml“ korrigiert). |
| `ES100896` | `mmhg` | `presión arterial de 101/85 mm Hg` → „Blutdruck 101/85 mmHg“ | Orthografische Normalisierung von „mm Hg“ (mit Leerzeichen) zu „mmHg“ (ohne Leerzeichen) löste den Token-Check units_added für „mmhg“ aus. |
| `FR100132` | `mmhg` | `une tension oculaire de 13 pour les deux yeux` → „einen Augeninnendruck von 13 mmHg beidseits“ | Konventionell eindeutige Standardeinheit (mmHg) für die applanatorische Tonometrie ergänzt; klinische Aussage unverfälscht. |
| `FR100142` | `ie` | `le taux sérique des CA 19-9 à 163 UI/ml (valeur normale < 30 UI/ml) ... passé à 41.4UI/ml puis à 24.9UI/ml` → „der Serumspiegel von CA 19-9 bei 163 IE/ml lag (Normwert < 30 IE/ml) ... auf 41,4 IE/ml beziehungsweise 24,9 IE/ml“ | Keine hinzugefügte Einheit: Französisch „UI/ml“ wurde lediglich in das deutsche Äquivalent „IE/ml“ übertragen. |
| `FR100632` | `u/l` | `des ASAT à 16 UI/l, des ALAT à 20 UI/l, des phosphatases alcalines à 239 UI/l, et des gammaglutamyl transférase à 9 UI/l.` → „ASAT 16 U/l, ALAT 20 U/l, alkalische Phosphatase 239 U/l und Gamma-Glutamyltransferase 9 U/l.“ | Auslöser von `units_added: u/l`: Die französische Einheit `UI/l` (Unités Internationales par litre) wurde standardkonform in `U/l` überführt. |
| `FR100748` | `mm, mmhg` | `entre 130/80 mm de Hg et 190/120 mm de Hg ... une masse surrénalienne de 55x45x50 mm ... entre 119/110 et 130/80 mm de Hg.` → „zwischen 130/80 mmHg und 190/120 mmHg ... eine 55 x 45 x 50 mm große Raumforderung ... zwischen 119/110 und 130/80 mmHg.“ | Auslöser von `units_added: mm, mmhg`: Die im Französischen getrennt geschriebene Einheit `mm de Hg` wurde im Deutschen regulär zu `mmHg` zusammengezogen. |
| `FR100806` | `ie` | `les LDH à 600 UI/l` → „die LDH lagen bei 600 IE/l“ | Auslöser von `units_added: ie`: Konventionsgemäße Übertragung von `UI/l` (Unités Internationales par litre) in das deutsche Äquivalent `IE/l` (Internationale Einheiten pro Liter). |

## 6. Dokumentierte stille Reparaturen und Explizierungen (im Text belassen)

Gemäß Review-Richtlinie wurden sachlich zutreffende Glättungen von Quell-Tippfehlern/OCR-Defekten sowie konventionell eindeutige Standardeinheiten und Abkürzungsauflösungen im deutschen Text belassen, hier jedoch vollständig für die Provenienz und Nachprüfbarkeit gegen das Original protokolliert:

- **`EN100022` (EN):**
  - *[silent_repair]* `for septic shock with hematesis.` → „aufgrund eines septischen Schocks mit Hämatemesis“ — Stille, sachlich eindeutige Korrektur des Quelltippfehlers „hematesis“ zu „Hämatemesis“ (im weiteren Quelltext korrekt als „hematemesis“ geschrieben).
  - *[silent_repair]* `Biopsie specimens were showed necrotic debris, mucosal submucosal necrosis` → „Biopsieproben zeigten nekrotisches Material sowie Nekrosen der Schleimhaut und Submukosa“ — Stille Glättung der defekten englischen Verbkonstruktion „Biopsie specimens were showed“.
  - *[explicitation]* `blood urea of 1,2 g/l (0,18-0,45 g/L), and a creatinine level of 68 mg/L (7-13 mg/L).` → „ein Harnstoffwert von 1,2 g/l (Norm: 0,18–0,45 g/l) sowie ein Kreatininwert von 68 mg/l (Norm: 7–13 mg/l).“ — Unmarkierte, aber konventionell eindeutige Explizierung der eingeklammerten Referenzbereiche durch den Zusatz „Norm:“.
- **`EN100024` (EN):**
  - *[explicitation]* `Left Descending Coronary Artery (LAD)` → „linken vorderen absteigenden Arterie (LAD)“ — Sachlich korrekte Ergänzung von „vorderen“ passend zum Akronym LAD (Left Anterior Descending).
  - *[silent_repair]* `delayed by the need to achieve glycaecmic control.` → „verzögerte sich aufgrund der erforderlichen Einstellung des Blutzuckerspiegels.“ — Stille Reparatur des Quelltippfehlers „glycaecmic“.
- **`EN100123` (EN):**
  - *[silent_repair]* `(weight 67kg, height 171cm, BMI 22.91kg/cm 2)` → „(Gewicht 67 kg, Körpergröße 171 cm, BMI 22,91 kg/m²)“ — Stille, rechnerisch eindeutige Korrektur der fehlerhaften Quelleinheit „kg/cm 2“ zu „kg/m²“ (67 / 1,71² = 22,91).
  - *[silent_repair]* `marked neutrophilic leukocytosis (WBC 23.400 /lt).` → „ausgeprägte neutrophile Leukozytose (Leukozyten 23.400/µl).“ — Stille Reparatur der unplausiblen Quelleinheit „/lt“ zu „/µl“ passend zur genannten ausgeprägten Leukozytose von 23.400/µl.
  - *[silent_repair]* `Candida albicans, Staphylococcus epidermidis and Klebsiella pneumonia ;` → „*Candida albicans*, *Staphylococcus epidermidis* und *Klebsiella pneumoniae*.“ — Stille orthografische Korrektur von „Klebsiella pneumonia“ zu „Klebsiella pneumoniae“ unter Hinzufügung von Markdown-Kursivierung.
  - *[explicitation]* `a second CT and an obstetrical consultation were conducted` → „eine weitere CT-Untersuchung sowie ein gynäkologisch-geburtshilfliches Konsil durchgeführt“ — Leichte Erweiterung von „obstetrical consultation“ zu „gynäkologisch-geburtshilfliches Konsil“.
- **`EN100184` (EN):**
  - *[explicitation]* `patching of the right eye for a period of 3-4 hours every day (after school).` → „das rechte Auge täglich für 3 bis 4 Stunden (nach der Schule) abzukleben (Okklusionstherapie).“ — Ergänzung des Fachbegriffs „(Okklusionstherapie)“ zur Beschreibung des Abklebens.
- **`EN100275` (EN):**
  - *[silent_repair]* `CT-Scan examination showed that bilateral ethmoidal sinusitis and pituitary gland was within normal limits.` → „Die CT-Untersuchung zeigte eine beidseitige Sinusitis ethmoidalis, während sich die Hypophyse unauffällig darstellte.“ — Sachlich plausible syntaktische Entflechtung des defekten Quellsatzes.
  - *[silent_repair]* `because after 14 days of progesterone consumption the prothyra is not bleeding.` → „da auch 14 Tage nach der Progesteroneinnahme keine Menstruationsblutung einsetzte.“ — Stille Glättung der stark fehlerhaften Quellformulierung „the prothyra is not bleeding“.
  - *[silent_repair]* `FSH: 8.71 MIU/mL` → „FSH 8,71 mIU/ml“ — Stille Korrektur der Großschreibung „MIU/mL“ zur korrekten Einheit „mIU/ml“.
  - *[terminology_note]* `macroscopic observation showed visible network of approximately 0.3 cm and 0.4 cm in diameter` → „Die makroskopische Untersuchung ergab ein sichtbares Netzwerk mit einem Durchmesser von etwa 0,3 cm bzw. 0,4 cm“ — Wörtliche Übernahme des Quellfehlers „visible network“ (im indonesischen Original wahrscheinlich Fehlübersetzung von „jaringan“ = Gewebe/Netzwerk).
- **`EN100315` (EN):**
  - *[silent_repair]* `with the presence of the humeral pulse` → „(bei tastbarem A.-brachialis-Puls)“ — Fachlich korrekte Übertragung des Gallizismus „humeral pulse“ (frz. pouls huméral) als „A.-brachialis-Puls“.
  - *[silent_repair]* `In the decline of 2 years, we haven't noticed any recidivism` → „Im Verlauf von zwei Jahren traten keine Rezidive auf“ — Stille Reparatur des sinnentstellten wörtlichen Gallizismus „In the decline of 2 years“ (frz. „Avec un recul de 2 ans“ = Nachbeobachtungszeitraum von 2 Jahren).
  - *[terminology_note]* `Revised after a month, showed a stable left hip on the clinical examination.` → „Bei der Nachuntersuchung nach einem Monat zeigte sich eine stabile linke Hüfte.“ — Quellgetreue Wiedergabe von „left hip“ (obwohl initial die rechte Hüfte luxiert war; Seitenverwechslung liegt bereits im Originaltext vor).
- **`EN100340` (EN):**
  - *[silent_repair]* `highlighted severe thrombocytopenia 23 0000 platelets` → „zeigte eine schwere Thrombozytopenie (23.000 Thrombozyten/µl)“ — Stille Reparatur des Quelltippfehlers „23 0000“ zu „23.000“ (da ausdrücklich als „severe thrombocytopenia“ bezeichnet) sowie Ergänzung der Standardeinheit „/µl“.
  - *[silent_repair]* `His medical history was featureless.` → „Ihre Krankengeschichte war unauffällig.“ — Stille Korrektur des fehlerhaften maskulinen Pronomens „His“ (aus frz. „Son“) bei einer Gebärenden.
  - *[silent_repair]* `The balance sheet of the coagulation was normal` → „Die Gerinnungsparameter waren normal“ — Stille Glättung der wörtlichen Fehlübersetzung aus dem Französischen („bilan de la coagulation“ -> „balance sheet of the coagulation“).
  - *[silent_repair]* `the presence of arterial vessels proliferation homes large and small caliber` → „Herde mit Proliferation arterieller Gefäße unterschiedlichen Kalibers (groß und klein)“ — Stille Rekonstruktion des verstümmelten Gallizismus „proliferation homes“ (aus frz. „foyers de prolifération“ = Proliferationsherde).
- **`EN100385` (EN):**
  - *[silent_repair]* `The procedure was post postponed until after she delivered` → „Der Eingriff wurde auf die Zeit nach der Entbindung verschoben“ — Stille Glättung der Wortdoppelung „post postponed“ in der Quelle.
  - *[explicitation]* `marked splenic atrophy with several splenules.` → „ausgeprägte Milzatrophie mit mehreren akzessorischen Milzen (Splenuli).“ — Konventionelle deutsche Auflösung von „splenules“ mit Beibehaltung des Fachterminus in Klammern.
- **`EN100427` (EN):**
  - *[explicitation]* `carcinoembryonic antigen, CA 19-9, CA 125, and human epididymis protein 4` → „das karzinoembryonale Antigen (CEA), CA 19-9, CA 125 und das humane Epididymis-Protein 4 (HE4)“ — Übliche Ergänzung der Standardabkürzungen CEA und HE4 in Klammern.
- **`EN100645` (EN):**
  - *[silent_repair]* `There was a distribution of the lymph node with metastasis and distribution of the external auditory canal with mucoepidermoid carcinoma.` → „Es zeigten sich Lymphknotenmetastasen sowie ein Befall des äußeren Gehörgangs durch ein Mukoepidermoidkarzinom.“ — Stille sprachliche Glättung der unidiomatischen englischen Formulierung „distribution of ... with ...“ bei vollständigem Erhalt der pathologischen Aussage.
- **`EN100653` (EN):**
  - *[silent_repair]* `MCV at 85 µ 3, lymphopenia at 400/mm 3, while platelets were normal 450 000/mm 3.` → „ein MCV von 85 µm³ und eine Lymphopenie (400/mm³), während die Thrombozytenzahl mit 450.000/mm³ im Normbereich lag.“ — Stille Reparatur des verstümmelten Quelltokens '85 µ 3' (fehlende Einheit 'm' und abgetrennte Hochzahl) zu '85 µm³' (= fl).
  - *[explicitation]* `Intact parathyroid hormone (iPTH) was high 628 pg/ml.` → „Der Spiegel des intakten Parathormons (iPTH) war mit 628 pg/ml stark erhöht.“ — Leichte graduelle Verstärkung ('high' -> 'stark erhöht'); bei 628 pg/ml klinisch eindeutig, Phänotyp und Zahlenwert unverändert.
- **`EN100682` (EN):**
  - *[silent_repair]* `He no family history of heart disease or sudden death. ... grade III atrioventricular (AV) bloc` → „es lagen keine familiären Vorbelastungen hinsichtlich Herzerkrankungen oder plötzlichem Herztod vor. ... AV-Block III. Grades“ — Stille Glättung des fehlenden Verbs ('He no family history') und der französischen Schreibweise 'bloc' im englischen Quelltext; zudem konventionelle Explizierung von 'sudden death' zu 'plötzlichem Herztod' im kardiologischen Kontext.
  - *[explicitation]* `All serological tests (chlamydia, coxiella, mycoplasma, rickettsia, lyme and bartonella) obtained during the hospitalization were negative.` → „Alle während des Krankenhausaufenthalts durchgeführten serologischen Tests (auf Chlamydien, Coxiellen, Mykoplasmen, Rickettsien, Borrelien/Lyme-Borreliose und Bartonellen) waren negativ.“ — Präzisierung von 'lyme' zu 'Borrelien/Lyme-Borreliose' passend zur Reihe der bakteriellen Erregernamen.
- **`EN103220` (EN):**
  - *[explicitation]* `Monotherapy with TKI sorafenib was prescribed to the patient` → „Dem Patienten wurde eine Monotherapie mit dem Tyrosinkinase-Inhibitor (TKI) Sorafenib verordnet“ — Konventionelle Auflösung der Standardabkürzung 'TKI' bei Erstnennung unter Beibehaltung des Kürzels.
- **`EN103442` (EN):**
  - *[terminology_note]* `Upper endoscopy also showed a submucosal tumor causing subtotal obstruction of the gastric outlet.` → „Auch die Gastroskopie ergab einen submukösen Tumor, der eine subtotale Obstruktion des Magenausgangs verursachte.“ — Kontextadäquate Wiedergabe von 'upper endoscopy' als 'Gastroskopie' bei Magentumor.
- **`EN103589` (EN):**
  - *[silent_repair]* `A smooth, solid right ovarian 50 an mm-size tumour, as well as small amount of fluid in the Douglas pouch, was found` → „wurde ein glatter, solider Tumor des rechten Ovars (Größe 50 mm) sowie eine geringe Menge Flüssigkeit im Douglas-Raum festgestellt.“ — Stille Reparatur des korrupten Quelltokens '50 an mm-size tumour' zu '(Größe 50 mm)'.
- **`EN105023` (EN):**
  - *[explicitation]* `admitted for widespread mucocutaneous blistering diagnosed as PV by histology and immunofluorescence. ... while treatment for pemphigus was escalated` → „aufgrund ausgedehnter mukokutaner Blasenbildung stationär aufgenommen; histologisch und mittels Immunfluoreszenz wurde die Diagnose Pemphigus vulgaris (PV) gestellt.“ — Vorweggenommene Auflösung der Abkürzung 'PV' zu 'Pemphigus vulgaris (PV)', gestützt durch den Befund mukokutaner Blasenbildung und die explizite Nennung von 'pemphigus' im vierten Satz.
- **`EN106841` (EN):**
  - *[terminology_note]* `dysphagia requiring percutaneous gastric feeds. While at the nursing home, she had recurrent aspiration pneumonia and large tube-feed residuals` → „Dysphagie geführt hatte und eine perkutane Sondenernährung erforderlich machte. Während ihres Aufenthalts im Pflegeheim litt sie unter rezidivierenden Aspirationspneumonien sowie großen Magenrestvolumina bei der Sondenernährung“ — 'percutaneous gastric feeds' wird leicht verallgemeinert zu 'perkutane Sondenernährung' (PEG), während der gastrale Bezug im Folgesatz bei 'Magenrestvolumina' explizit erhalten bleibt.
- **`EN107405` (EN):**
  - *[terminology_note]* `Biochemical evaluation confirmed adrenocorticotropic hormone -dependent Cushing's syndrome.` → „Die biochemische Abklärung bestätigte ein ACTH-abhängiges Cushing-Syndrom.“ — Verwendung der im Deutschen universell üblichen Fachabkürzung 'ACTH' für 'adrenocorticotropic hormone' (auch in den Folgesätzen).
- **`EN108798` (EN):**
  - *[terminology_note]* `Computed tomography (CT) revealed a markedly dilated common bile duct (CBD)` → „Die Computertomographie (CT) zeigte einen deutlich erweiterten Ductus choledochus“ — Standardmäßige Übertragung von 'common bile duct (CBD)' in den deutschen anatomischen Fachterminus 'Ductus choledochus'.
- **`ES100002` (ES):**
  - *[silent_repair]* `Ocho meses antes, est:udio ecográfico y U.I.V. sin hallazgos patológicos.` → „Acht Monate zuvor waren Ultraschall und IVP ohne pathologischen Befund.“ — Der OCR-/Tippfehler „est:udio“ in der Quelle wurde still und sachlich korrekt geglättet.
  - *[terminology_note]* `Compatible con carcinoma de células transicionales de bajo grado.` → „Vereinbar mit einem niedriggradigen (low-grade) Urothelkarzinom.“ — „Carcinoma de células transicionales“ (Übergangszellkarzinom) wurde mit dem aktuellen deutschen Standardbegriff „Urothelkarzinom“ wiedergegeben.
  - *[explicitation]* `a nivel de uréter sacro-ilíaco derecho` → „im Bereich des rechten Ureters (auf Höhe des Iliosakralgelenks)“ — Die topografische Angabe „uréter sacro-ilíaco“ wurde im Deutschen expliziert als „im Bereich des rechten Ureters (auf Höhe des Iliosakralgelenks)“.
- **`ES100063` (ES):**
  - *[explicitation]* `El índice mitótico es elevado ( 7 m/ 10 campos de gran aumento).` → „Der Mitoseindex ist erhöht (7 Mitosen/10 Gesichtsfelder bei starker Vergrößerung).“ — Die Abkürzung „7 m/“ im Kontext des Mitoseindex wurde konventionell eindeutig als „7 Mitosen/“ ausgeschrieben.
- **`ES100064` (ES):**
  - *[silent_repair]* `ácido zoledrómico 4 mg ... La obliteración de la grasa de la grasa extraconal superior` → „Zoledronsäure (4 mg ... Die Verdrängung des oberen extrakonalen Fettgewebes“ — Der Tippfehler „zoledrómico“ (statt zoledrónico) und die Dittographie „de la grasa de la grasa“ wurden still geglättet.
- **`ES100214` (ES):**
  - *[explicitation]* `Se inicia DPA a las 36 h` → „Nach 36 Stunden wurde eine automatisierte Peritonealdialyse (APD) eingeleitet“ — Die spanische Abkürzung „DPA“ (diálisis peritoneal automática) wurde sachlich korrekt aufgelöst und mit dem deutschen Kürzel APD versehen.
  - *[terminology_note]* `por fórmula de Schwarz` → „nach der Schwarz-Formel“ — Die im spanischen Original verwendete Schreibweise „Schwarz“ (eigentlich pädiatrische GFR-Formel nach Schwartz) wurde wörtlich übernommen.
- **`ES100259` (ES):**
  - *[silent_repair]* `bordeaba la aorta en 180o englobando a la arteria mesentérica inferior` → „die Aorta über einen Winkel von 180° umschloss und die Arteria mesenterica inferior einbezog“ — Das als Kleinbuchstabe „o“ gesetzte Gradzeichen (`180o`) wurde still zu `180°` normalisiert.
- **`ES100280` (ES):**
  - *[silent_repair]* `8 por Staphilococcus aureus` → „davon acht durch *Staphylococcus aureus*“ — Der Quelltippfehler „Staphilococcus“ wurde still zur korrekten taxonomischen Schreibweise korrigiert.
  - *[explicitation]* `Durante los 5 años que permaneció en DP ... se transfirió a HD.` → „Während der fünfjährigen Dauer der Peritonealdialyse (PD) ... auf Hämodialyse (HD) umgestellt wurde.“ — Konventionell eindeutige Auflösung der Standardabkürzungen DP (Peritonealdialyse) und HD (Hämodialyse).
- **`ES100304` (ES):**
  - *[silent_repair]* `c.165delT (p.Phe55fs) / c.q62G > A (p.Val388Met)` → „c.165delT (p.Phe55fs) / c.1162G > A (p.Val388Met)“ — Der OCR-Fehler `c.q62G > A` im PAH-Gen wurde anhand der korrespondierenden Proteinänderung `p.Val388Met` (Kodon 388 -> Nukleotidposition 1162) still und molekulargenetisch exakt zu `c.1162G > A` korrigiert.
  - *[silent_repair]* `para descatar una posible respuesta` → „um ein mögliches Ansprechen auf diese pharmakologische Behandlung zu prüfen“ — Der Tippfehler „descatar“ (für „descartar“, hier im Sinne von abklären/prüfen) wurde still geglättet.
- **`ES100412` (ES):**
  - *[silent_repair]* `que protuía a cámara anterior` → „die in die Vorderkammer vorwölbte“ — Der spanische Tippfehler „protuía“ (statt „protruía“) wurde still korrigiert.
- **`ES100571` (ES):**
  - *[explicitation]* `Los anticuerpos anti-nucleares, anti-mitocondriales y anti-músculo liso fueron negativos` → „Antinukleäre Antikörper (ANA), antimitochondriale Antikörper (AMA) und Antikörper gegen glatte Muskulatur (ASMA) waren negativ“ — Konventionelle deutsche Standardabkürzungen (ANA, AMA, ASMA) klärend in Klammern ergänzt.
- **`ES100587` (ES):**
  - *[explicitation]* `Está con DSG desde hace 2 años, con buena respuesta clínica y analítica.` → „Seit zwei Jahren glutenfreie Ernährung mit gutem klinischen und laborchemischen Ansprechen.“ — Konventionelle Auflösung der spanischen Abkürzung „DSG“ (dieta sin gluten) zu „glutenfreie Ernährung“.
- **`ES100631` (ES):**
  - *[silent_repair]* `virus de la parotidis ... y tinción Zielh negativa` → „Mumpsvirus ... und die Ziehl-Färbung war negativ“ — Stille, sachlich korrekte Glättung der Quelltippfehler „parotidis“ (statt parotiditis) und „Zielh“ (statt Ziehl-Neelsen).
  - *[explicitation]* `con la sospecha de pancreatitis autoinmune ... Con el diagnóstico de probable PAI` → „der Verdacht auf eine Autoimmunpankreatitis (AIP) bestand ... mit der Diagnose einer wahrscheinlichen AIP“ — Einführung des deutschen Akronyms „(AIP)“ bei Erstnennung der Autoimmunpankreatitis zur Vorbereitung des späteren Kürzels „PAI“.
- **`ES100688` (ES):**
  - *[explicitation]* `con diagnóstico de SMR ... siendo diagnosticado histopatológicamente como una QG asociada a un SMR` → „mit der Diagnose eines Melkersson-Rosenthal-Syndroms (MRS) ... die histopathologisch eine granulomatöse Cheilitis (Cheilitis granulomatosa) in Verbindung mit einem MRS ergab“ — Im Quelltext nicht ausgeschriebene Abkürzungen „SMR“ (Síndrome de Melkersson-Rosenthal) und „QG“ (Queilitis granulomatosa) kontextuell eindeutig aufgelöst.
  - *[terminology_note]* `Levotiroxina 100 mg 1 comp/día` → „Levothyroxin (100 mg, 1 Tablette/Tag)“ — Quellfehler „100 mg“ (klinisch gemeint 100 µg bei Levothyroxin) wurde von TLLM ohne stille Veränderung quellgetreu übernommen.
- **`ES100727` (ES):**
  - *[silent_repair]* `síndrome de Beckwith-Wiedmann ... Obwegeser et al. (1964)10 ... tratamiento fonoaudilógico` → „Beckwith-Wiedemann-Syndroms ... Obwegeser et al. (1964) ... in logopädischer“ — Stille Bereinigung von Rechtschreibfehlern („Beckwith-Wiedmann“, „fonoaudilógico“) und einer angehängten Literaturverweisziffer („(1964)10“) der Quelle.
  - *[terminology_note]* `disector quirúrgico eléctrico (aguja colrado, Stryker Corporation®)` → „elektrischen chirurgischen Dissektor (Colrado-Nadel, Stryker Corporation®)“ — Quelltippfehler „colrado“ (gemeint: Colorado-Nadel) wurde von TLLM wörtlich als „Colrado-Nadel“ übernommen.
- **`ES100775` (ES):**
  - *[terminology_note]* `se realiza serología a Bartonella henselae ... la serología a Bartonella henselae.` → „es wurde eine Serologie auf *Bartonella henselae* durchgeführt ... der *Bartonella-henselae*-Serologie bestätigt.“ — Typografische Hervorhebung des Speziesnamens durch Markdown-Sternchen im Zieltext.
- **`ES100789` (ES):**
  - *[silent_repair]* `con aceptable con-trol del dolor(EVA, 3)` → „die Schmerzkontrolle ist akzeptabel (VAS 3)“ — Stille Glättung des Trennungsartefakts „con-trol“ aus dem Quelltext.
- **`FR100142` (FR):**
  - *[silent_repair]* `Les marqueurs tomoraux (ACE, α foetoprotéine, NSE)` → „Die Tumormarker (CEA, Alpha-Fetoprotein, NSE)“ — Stille Korrektur des Quell-Tippfehlers „tomoraux“ zu „Tumormarker“ sowie standardkonforme Übertragung von „ACE“ zu „CEA“.
  - *[explicitation]* `une anémie normochrome normocytaire arégénérative à 7.8 g/dl` → „eine normochrome, normozytäre, aregenerative Anämie (Hämoglobin 7,8 g/dl)“ — Konventionell eindeutige Explizierung des Parameters „Hämoglobin“ bei einer Anämieangabe in g/dl.
- **`FR100185` (FR):**
  - *[terminology_note]* `une amyotrophie de la main` → „eine Atrophie der Handmuskulatur“ — Durch den Zusatz „der Handmuskulatur“ bleibt der muskuläre Phänotyp („amyotrophie“) im Deutschen eindeutig erhalten.
- **`FR100255` (FR):**
  - *[explicitation]* `La confirmation d'une grossesse non évolutive de 36 semaines d'aménorrhées` → „wurde eine nicht mehr intakte Schwangerschaft (keine fetale Vitalität) in der 36. Schwangerschaftswoche bestätigt“ — Kontextuell zutreffende Erläuterung von „grossesse non évolutive“ im 3. Trimenon bei zuvor negativen fetalen Herztönen.
- **`FR100314` (FR):**
  - *[silent_repair]* `Accoure de son hospitalisation le patient a présenté des signes isthmiques de membre supérieur droit` → „Im weiteren Verlauf des Krankenhausaufenthalts entwickelte die Patientin Anzeichen einer Ischämie des rechten Arms“ — Stille Reparatur dreier Quelldefekte in einem Satz: „Accoure“ -> „Au cours“, „le patient“ -> „die Patientin“ sowie „signes isthmiques“ -> „Anzeichen einer Ischämie“ (aus dem Kontext von Gefäßthrombose und Amputation eindeutig als „ischémiques“ rekonstruierbar).
  - *[terminology_note]* `Il n'y avait pas de signe de détresse respiratoire ou hémodynamique` → „Es zeigten sich keine Anzeichen einer respiratorischen oder hämodynamischen Instabilität“ — In der negierten Zeugmakonstruktion („détresse respiratoire ou hémodynamique“) ist die Wiedergabe als fehlende respiratorische oder hämodynamische Instabilität klinisch adäquat.
- **`FR100360` (FR):**
  - *[terminology_note]* `Une tomodensitométrie cérébrale avait objectivé une lésion fronto-pariétale gauche ... IRM cérébrale a confirmé la présence d'un processus tumoral pariéto-occipital droit` → „Eine Computertomographie (CT) des Schädels zeigte eine linksseitige frontoparietale Läsion ... Magnetresonanztomographie (MRT) des Schädels bestätigte das Vorliegen eines rechtsseitigen parieto-okzipitalen Tumorprozesses“ — Inhärente Diskrepanz der Lokalisation/Lateralität im französischen Ausgangstext, die in der Übersetzung unverändert und quellengetreu erhalten bleibt.
  - *[silent_repair]* `classée stade IA/ selon la classification de la FIGO 2009` → „gemäß der FIGO-Klassifikation von 2009 in das Stadium IA eingestuft“ — Stille Bereinigung des überzähligen Schrägstrichs nach „IA/“.
- **`FR100448` (FR):**
  - *[terminology_note]* `apparition d'une masse cervicale droite. L'examen clinique initial trouve une tuméfaction ... au niveau du lobe gauche de la thyroïde.` → „mit einer Raumforderung am rechten Hals ... Schwellung im Bereich des linken Schilddrüsenlappens.“ — Bereits im französischen Quelltext vorhandene Lateralitätsdiskrepanz zwischen anamnestischer Halsraumforderung rechts und Untersuchungsbefund am linken Schilddrüsenlappen.
- **`FR100480` (FR):**
  - *[silent_repair]* `a poussé la patiente a consulté dans notre formation` → „veranlasste die Patientin, unsere Einrichtung aufzusuchen“ — Stille Glättung des französischen Grammatikfehlers „a consulté“ (statt „à consulter“).
- **`FR100632` (FR):**
  - *[silent_repair]* `un taux de bilirubine totale à 5,081m/l, Bilirubine direct: 2,09mg/l` → „Gesamtbilirubin 5,08 mg/l, direktes Bilirubin 2,09 mg/l“ — Stille Reparatur der verstümmelten Quellangabe `5,081m/l` zu `5,08 mg/l` (analog zur nachfolgenden Angabe `2,09mg/l` und konsistent mit dem anikterischen Verlauf).
  - *[silent_repair]* `Mycoplasmapneumoniae, la Borreliaburgdoferi, Rickettsiaconorii, le virus d'Epstein-Barr, l'herpes virus (1 et 2) ... hépatite aiguë A anectérique. L epatient` → „*Mycoplasma pneumoniae*, *Borrelia burgdorferi*, *Rickettsia conorii*, Epstein-Barr-Virus, Herpes-simplex-Virus (Typ 1 und 2) ... akuten anikterischen Hepatitis A. Der Patient“ — Stille Glättung mehrerer Tipp- und Spatienfehler der Quelle (`présentantune`, `sanguineet`, Erregernamen, `anectérique` statt `anictérique`, `L epatient`) sowie eindeutige Präzisierung von `l'herpes virus (1 et 2)` zu `Herpes-simplex-Virus (Typ 1 und 2)`.
- **`FR100748` (FR):**
  - *[silent_repair]* `L'intubation a été facile avec une sonde 7,0 CH avec ballonnet.` → „Die Intubation verlief problemlos unter Verwendung eines Tubus der Größe 7,0 (mit Cuff).“ — Stille Reparatur eines Quellfehlers: Endotrachealtuben für Erwachsene werden in Millimetern Innendurchmesser (Größe 7,0) und nicht in Charrière (`7,0 CH` entspräche ca. 2,3 mm Außendurchmesser) angegeben.
  - *[silent_repair]* `Le dosage de l'acide vanyl-mandélique urinaire (VMA) objectivait 11,8mg/24heures.` → „Die Bestimmung der Vanillinmandelsäure (VMS) im Urin ergab einen Wert von 11,8 mg/24 Stunden.“ — Stille Glättung der unüblichen französischen Schreibweise `acide vanyl-mandélique` zu `Vanillinmandelsäure (VMS)`.
- **`FR100780` (FR):**
  - *[explicitation]* `une tension artérielle à 18/10 cmHg sans signes neurosensoriels.` → „Blutdruck 180/100 mmHg (18/10 cmHg), keine neurosensorischen Auffälligkeiten.“ — Sachlich korrekte Umrechnung der im Französischen üblichen Angabe `18/10 cmHg` in `180/100 mmHg` unter Beibehaltung des Originalwerts in Klammern.
  - *[explicitation]* `sur une durée de 4 heures avec une quantité de 2,5 litres.` → „mit einer Dauer von 4 Stunden und einem Flüssigkeitsentzug von 2,5 Litern.“ — Kontextuell eindeutige Explizierung von `une quantité de 2,5 litres` im Rahmen der Hämodialyse als Ultrafiltrationsvolumen (`Flüssigkeitsentzug von 2,5 Litern`).
- **`FR100806` (FR):**
  - *[silent_repair]* `un abdomen souple, mât, augmenté de volume, sensible dans son ensemble avec un cri de l'ombilic.` → „einen weichen, vergrößerten Bauch mit gedämpftem Klopfschall und diffuser Druckempfindlichkeit sowie einen positiven Nabeldruckschmerz.“ — Stille Reparatur des orthografischen Quellfehlers `mât` (statt `mat`, gedämpfter Perkussionsschall bei Aszites/Hämoperitoneum) sowie klinisch treffende Wiedergabe von `cri de l'ombilic` als `positiven Nabeldruckschmerz`.
- **`FR100814` (FR):**
  - *[explicitation]* `un processus centré sur l'échancrure sciatique droite à cheval sur le canal sous pyramidal` → „einen Prozess, der auf die rechte Incisura ischiadica (große Ischiadikuskerbe) zentriert ist und sich über den infra-piriformen Raum (Foramen infrapiriforme) erstreckt“ — Ergänzung der Fachtermini `Incisura ischiadica (große Ischiadikuskerbe)` und `Foramen infrapiriforme`; durch die Lage am `canal sous pyramidal` ist eindeutig das Foramen ischiadicum majus bzw. die Incisura ischiadica major gemeint.
- **`FR100874` (FR):**
  - *[terminology_note]* `Le transit œsogastroduodénale objectivait un refoulement de la portion cervicale de l'œsophage` → „Die Ösophagus-Breischluck-Untersuchung (Transit) zeigte eine Verdrängung des zervikalen Ösophagusabschnitts“ — Fokussierende Wiedergabe von `transit œsogastroduodénale` (obere Magen-Darm-Passage) als `Ösophagus-Breischluck-Untersuchung (Transit)` entsprechend dem beschriebenen zervikalen Ösophagusbefund.
- **`FR100882` (FR):**
  - *[silent_repair]* `L'examen anatonomo-cyto-pathologie réalisée, devant la suspicion de signe de malignité, sur la pièce de biopsie lors du temps opératoire` → „Die aufgrund des Verdachts auf Malignität durchgeführte anatomopathologische Untersuchung des intraoperativ gewonnenen Biopsiematerials“ — Stille Reparatur des Quelltippfehlers `anatonomo-cyto-pathologie` (frz. Standardbezeichnung `anatomo-cyto-pathologie`) zu `anatomopathologische Untersuchung` unter Wegfall der zytologischen Namenskomponente bei einer intraoperativen Gewebebiopsie.
  - *[silent_repair]* `elle a été prise en neurochirurgicalement pour une laminectomie dorsale en regard de T7` → „erfolgte zunächst eine neurochirurgische Intervention mittels dorsaler Laminektomie auf Höhe von T7“ — Stille Glättung der defekten französischen Konstruktion `prise en [charge] neurochirurgicalement`.
- **`FR100883` (FR):**
  - *[silent_repair]* `un épaississement de la muqueuse de la cloison nasale de surface polyploïde de 14mm d'épaisseur.` → „eine 14 mm dicke Verdickung der Nasenseptumschleimhaut mit polypöser Oberfläche.“ — Stille Reparatur des Quelltippfehlers `polyploïde` (polyploid) zum im makroskopisch-radiologischen Schleimhautkontext gemeinten `polypoïde` (`mit polypöser Oberfläche`).
- **`FR100946` (FR):**
  - *[silent_repair]* `un œdème péri-lésionnel en doigt de gans en séquence FLAIR` → „Die FLAIR-Sequenz zeigte ein fingerförmiges periläsionales Ödem“ — Stille Reparatur des französischen Tippfehlers `en doigt de gans` (statt `en doigt de gant`, handschuhfingerförmiges vasogenes Ödem).
- **`FR100998` (FR):**
  - *[explicitation]* `suivie pour VUH depuis 20 ans. Le diagnostic était retenu sur les lésions urticariennes, l'inflammation occulaire, le test positif C1q-p par immunodiffusion` → „die seit 20 Jahren wegen einer hypokomplementämischen urtikariellen Vaskulitis (VUH) in Behandlung ist. Die Diagnose stützte sich auf urtikarielle Läsionen, eine Augenentzündung sowie einen positiven C1q-Präzipitin-Test (C1q-p) mittels Immundiffusion“ — Vorweggenommene Auflösung der im Quelltext erst in Satz 6 ausgeschriebenen Abkürzung `VUH` sowie fachlich korrekte Auflösung von `C1q-p` als `C1q-Präzipitin-Test (C1q-p)`.
  - *[silent_repair]* `l'inflammation occulaire ... avec un faible du taux de C1q ... conditionne le pronostique vital à cours terme.` → „eine Augenentzündung ... bei gleichzeitig erniedrigtem C1q-Spiegel ... bestimmt die kurzfristige Prognose.“ — Stille Glättung mehrerer orthografischer und grammatischer Quelldefekte (`occulaire` statt `oculaire`, `un faible du taux` statt `un faible taux`, `pronostique` statt `pronostic`, `à cours terme` statt `à court terme`).
