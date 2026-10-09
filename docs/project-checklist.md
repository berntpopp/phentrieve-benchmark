# Phentrieve Benchmark – Projektcheckliste

Status:

- `[x]` erledigt
- `[ ]` offen
- `⏸` pausiert
- `⚠` Entscheidung erforderlich

## Gemeinsame Infrastruktur

- [x] Python-Paket, CLI und reproduzierbare Abhängigkeiten einrichten.
- [x] Kanonische JSON-/JSONL-Serialisierung und SHA-256-Identitäten umsetzen.
- [x] Inhaltsadressierten lokalen Artefaktspeicher einrichten.
- [x] Download, Normalisierung, Auswahl und Vorbereitung als getrennte Stufen
      abbilden.
- [x] Deterministische Wiederverwendung mit erneuter Artefaktprüfung umsetzen.
- [x] Run-Manifeste und Provenienz-Links getrennt von deterministischen
      Datenmanifesten speichern.
- [x] Ein gemeinsames kuratiertes Annotationsformat für E3C, GSC und CSC mit
      Evidenzspannen, Kontext und typisierten Herleitungsquellen umsetzen.
- [x] Unabhängige Reviewentscheidungen und deren deterministische,
      konfliktbewahrende Zusammenführung als gemeinsames Format umsetzen.
- [x] Explizite datensatzweite Single-Term-Auswahl und deterministische
      Ableitung selbstständiger Single-Term-Datensätze implementieren.
- [x] Exakte Dokument-, Ontologie-, Quell-, Review- und Auswahlprovenienz
      sowie Run-Links für alle neuen Artefaktarten abbilden.
- [x] Gepinnte Quellrezepte, Checksummen und Lizenznachweise dokumentieren.
- [x] Offline-CI mit synthetischen Testdaten einrichten.
- [x] Expliziten Live-Smoke-Test für echte Downloads bereitstellen.
- Entfällt (2026-10-06): Mindest-Testabdeckung als CI-Grenze; Coverage wird
  nur noch berichtet (letzter Stand 88 %).
- [ ] Kostenpflichtige Operationen vor Ausführung grob kalkulieren und
      ausdrücklich bestätigen lassen.

## E3C – aktiv

Strategie (revidiert 2026-10-06):

- Alle 246 Texte werden geschichtet auf vier etwa gleich große
  Annotationsgruppen aufgeteilt: Deutsch (übersetzt), Englisch, Französisch,
  Spanisch (jeweils Original). Jeder Text wird in genau einer Sprache
  annotiert; die deutsche Gruppe speist sich zu gleichen Teilen aus allen
  drei Originalsprachen. Die Gruppen werden getrennt ausgewertet und nie
  zusammengerechnet. Ein späterer Qualitätscheck kann ungeeignete Texte
  herausfiltern.
- Annotiert wird von Anfang an spannenbasiert im Editor, mit allen Vorkommen
  je Annotation, nach der Richtlinie
  [`annotation-guidelines/hpo-span-annotation.md`](annotation-guidelines/hpo-span-annotation.md).
  Bewertet wird weiterhin auf Dokument-Ebene über HPO-IDs.
- Vorschläge entstehen in einem einheitlichen Schritt für alle Texte, ohne
  Hinweise aus UMLS-Mapping, E3C-Annotationen oder Phase-0-Audit; diese
  bleiben unabhängige Vergleichsquellen. Jeder Vorschlag bleibt bis zur
  Rohausgabe nachverfolgbar.

Umsetzungsentwurf:
[`superpowers/specs/2026-10-06-e3c-multilingual-span-annotation-design.md`](superpowers/specs/2026-10-06-e3c-multilingual-span-annotation-design.md).

Ersetzt sind damit die gestufte Strategie vom 2026-08-24 (zuerst
Dokument-Level-Gold ohne Spannen) und die 30er-Kohorte als Arbeitsmenge; die
30 Fälle waren willkürlich gewählt, ihre Phase-0-Ergebnisse bleiben als
Vergleichsdaten erhalten.

### Quelle, Normalisierung und Auswahl

- [x] E3C-Commit
      `f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc` festlegen und prüfen.
- [x] Englische, französische und spanische Layer-1-XMI-Dateien laden.
- [x] 84 englische, 81 französische und 81 spanische Texte normalisieren.
- [x] UTF-16-Offsets auf NFC-normalisierten kanonischen Text abbilden.
- [x] Alle ausgewählten Texte als L1 behandeln.
- [x] Dokumentlänge selbst mit `len(canonical_text.split())` bestimmen.
- [x] Textfreies Inventar für 246 Dokumente erzeugen.
- [x] Kurze, mittlere und lange Dokumente deterministisch stratifizieren.
- [x] Machbarkeitskohorte mit 30 Fällen auswählen:
      10 je Sprache und je 3/4/3 kurze, mittlere und lange Fälle.
- [x] Auswahlverfahren, Seed, Merkmale und Grenzen dokumentieren.
- [x] Alle 246 Texte deterministisch (fester Seed, textfreies Manifest) auf
      die vier Annotationsgruppen aufteilen: je Originalsprache etwa ein
      Viertel ins Deutsche (ca. 21 EN, 20 FR, 20 ES), Rest im Original;
      geschichtet nach Länge und E3C-Annotationsdichte; Gruppen müssen nicht
      exakt gleich groß sein.

### Deutsche Übersetzung

- [x] Google Cloud Translation Advanced v3 mit `general/nmt` als
      Übersetzungsweg spezifizieren.
- [x] Textmenge der 30 Fälle bestimmen: 59.517 Zeichen und 8.977 Wörter.
- [x] Kostenobergrenze anhand des gepinnten Listenpreises grob bestimmen:
      1,19034 USD vor einem möglichen monatlichen Guthaben.
- [x] Getrennte unveränderliche Original- und Übersetzungsartefakte,
      textfreies Manifest und Revisionsmodell implementieren.
- [x] Kostenanzeige und ausdrückliche Bestätigung vor Erzeugung des
      Google-Clients implementieren.
- [x] Providerzugriff und Übersetzungsablauf offline testbar vorbereiten.
- [x] Die 30 ausgewählten englischen, französischen und spanischen Volltexte
      nach Deutsch übersetzen.
- [x] Originaltexte und deutsche Übersetzungen als getrennte unveränderliche
      Artefakte erhalten.
- [x] Übersetzungsmodell, Konfiguration, Eingabehash, Nutzung und Kosten
      protokollieren.
- [x] Fehlgeschlagene oder leere Providerantworten sicher zurückweisen.
- [x] Korrekturen als neue Artefakte speichern, ohne frühere Fassungen zu
      überschreiben.
- [x] Der zweite Übersetzungsweg mit `general/translation-llm` wurde als
      separate Rezeptidentität neben `general/nmt` bereitgestellt; die 30
      Fälle wurden damit übersetzt.
- [x] `general/translation-llm` als Grundlage des manuellen Reviews festlegen;
      NMT bleibt eine optionale Vergleichsspalte.
- [x] Explizite Vollkorpus-Variante `tllm-full` für alle 246 normalisierten
      Berichte vorbereiten; die 30 vorhandenen TLLM-Ergebnisse werden
      kompatibilitätsgeprüft wiederverwendet.
- [x] Auch die fünf automatisch markierten TLLM-Ausgaben als bereits erzeugte
      Provider-Ergebnisse wiederverwenden; Fehlerstatus und Prüfhinweise
      bleiben für den medizinischen Review unverändert sichtbar.
- [x] Kostenanzeige für die 216 verbleibenden Berichte verifizieren: 441.414
      Eingabezeichen, Kostenobergrenze 10,152522 USD.
- [x] Alle 246 Berichte nach ausdrücklicher Bestätigung der Kostenobergrenze
      11,521413 USD mit `tllm-full --retranslate-all` neu übersetzen. Manifest:
      `759f00260dab85a3fbeb24204683f790b4b14a18759c2bb80910ff1725b4451a`;
      185 bereit für Review, 61 mit `units_added`-Hinweis. Der Vergleich der
      vorhandenen 30 ergab 30 byte-identische und 0 veränderte Übersetzungen.

### Übersetzungsprüfung

- [x] Ein einfaches internes Zwei-Blatt-Excelprofil für die vollständige
      bilinguale medizinische Prüfung der 30 Fälle entwerfen.
- [x] Deterministischen Workbook-Export und transaktionalen Import in
      kanonische Text-, Review- und Diff-Artefakte implementieren.
- [x] Automatische Prüfung auf leere Ausgabe, unveränderte Quelle,
      Längenverhältnis, erfundene Einheiten und Zielsprache; Absatzzahlen
      werden ohne Gate mitgeschrieben.
- ⚠ Zahlen werden nicht mehr automatisch geprüft. `numbers_preserved` und
  `units_preserved` verglichen Multimengen über Sprachgrenzen hinweg, maßen
  damit Typografie statt Bedeutung und markierten 28 von 30 Texten, ohne einen
  der 24 klinisch relevanten Fehler zu finden. Die Zahlentreue liegt jetzt beim
  manuellen Review.
- ⏸ Vollständigkeit, medizinische Bedeutung, Negation und Auslassungen sind
  regelbasiert nicht erreichbar; dafür ist eine semantische Prüfstufe
  (Rückübersetzung oder Entailment) zu entwerfen — offene Architekturfrage
  wegen Determinismus und gepinnter Modellidentität.
- [x] Phase-0-Machbarkeitsprobe (2026-08-24, maschinell, kein Gold): 208 von
      210 Audit-Konsens-Termen sind in den deutschen Übersetzungen klar
      ausgedrückt; der Aussagestatus blieb in allen 210 erhalten. Befund:
      `datasets/e3c-de/annotation-feasibility/`.
- [x] Entscheidung (2026-08-24): Der Übersetzungsreview bleibt schlank und
      risikobasiert statt anteilig-vollständig; die Übersetzung ist für das
      Dokument-Level-Ziel kein Engpass. Ersetzt am 2026-10-06 (nächster
      Punkt).
- [x] Entscheidung (2026-10-06): Jeder Text der deutschen Annotationsgruppe
      wird vor der Verwendung vollständig geprüft; ungeprüfte Übersetzungen
      werden nicht verwendet.
- [x] Workbook-Export auf die deutsche Annotationsgruppe (`tllm-full`) statt
      auf die 30er-Kohorte umstellen.
- [ ] Übersetzungsreview aller Texte der deutschen Gruppe durchführen und
      importieren.
- [ ] Je Fall die deutsche Textfassung festschreiben, bevor annotiert wird;
      eine spätere Korrektur erzeugt eine neue Fassung, deren Spannen neu
      verankert werden müssen (Richtlinie R7).
- Entfällt: Ausweitung des manuellen Reviews bei kritischen Fehlern; die
  deutsche Gruppe wird ohnehin vollständig geprüft.
- [ ] Reviewbefunde, Korrekturen und Entscheidungen getrennt dokumentieren.

### UMLS-zu-HPO-Mapping und Annotation

- [x] UMLS-CUIs aller 246 E3C-L1-Texte gegen die gepinnte HPO-Version auf
      HPO-Kandidaten abbilden.
- [x] Eindeutige, mehrdeutige, fehlende, obsolete und ungültige Zuordnungen
      unterscheiden.
- [x] Vollständiges textfreies Manifest und exakte 30-Fälle-Teilansicht
      erzeugen.
- [x] Problematische Zuordnungen zur manuellen Prüfung kennzeichnen.
- [x] Den einzelnen malformed HPO-Cross-Reference dokumentieren und ohne
      automatische Korrektur ausschließen.
- [x] Strategieentscheidung (2026-08-24): Zuerst ein Dokument-Level-Gold
      (HPO-Term-Mengen je deutschem Text, wie CSC/GSC); Evidenzspannen erst
      später und nur für die Single-Term-Teilmenge. Revidiert am 2026-10-06:
      spannenbasierte Annotation von Anfang an (siehe oben).
- [x] Markierungsregeln als Richtlinie festhalten (2026-10-06, Entwurf).
- [x] Phase-0-Probe zur Annotier-Machbarkeit: Gold-Kern aus 176 positiven
      Konsenstermen plus ~100 maschinell vorgeschlagenen Lückenkandidaten
      (81 gegen die gepinnte HPO aufgelöst); Engpass ist die
      Konzeptabdeckung, nicht die Sprache.
- [x] CUI-Triage der 200 häufigsten ungeklärten missing-CUIs: 83 kein
      Phänotyp, 64 Phänotyp ohne xref (55 Vorschläge maschinell gegen HPO
      validiert, 0 erfundene IDs), 48 zu generisch, 5 unklar.
- Entfällt: Konsolidiertes Vorschlags-Workbook je Fall (erzeugt wurde nur
  die englische Quelltext-Variante). Für die Volltext-Annotation abgelöst
  durch den Editor (2026-10-06); Excel bleibt nur für den Übersetzungsreview.
- [ ] Einheitlichen Vorschlagsschritt für alle 246 Texte durchführen
      (Entscheidungen 2026-10-06):
  - Claude-Subagenten lesen jeden Text in seiner Annotationssprache und
    schlagen nach der Richtlinie HPO-Terme mit Spannen (R2/R4, alle
    Vorkommen) und vorbelegtem Status vor;
  - ohne Hinweise: keine UMLS-Kandidaten, E3C-Stellen oder
    Phase-0-Ergebnisse als Eingabe, damit diese später unabhängig verglichen
    werden können;
  - deterministische Prüfung: HPO-ID aktiv in der gepinnten Version, jede
    Spanne wörtlich im Text; Verworfenes mit Grund protokollieren;
  - Nachverfolgbarkeit: Modell-ID, versionierte Prompt-Datei,
    Richtlinienversion, Prüfsumme jedes Eingabetexts, unveränderte Ausgabe je
    Batch mit Vermerk „maschinell, kein Gold“, Prüfbericht; jeder Vorschlag
    im Editor-Paket verweist auf Batch und Eintrag.
- [ ] Editor-Pakete je Annotationsgruppe bauen: je Vorkommen eine eigene
      Belegstelle; Achsen als Pflicht; Spannen beim Abschluss erzwingen;
      Pflichtachse `verbalized`/`not_verbalized`, vorbelegt mit `verbalized`.
  - [x] Builder `scripts/build_editor_packages.py e3c` und Pakete für
        Englisch, Französisch und Spanisch (2026-10-08), je Paket ein
        Build-Protokoll in `datasets/e3c-de/editor-packages/`.
  - [x] Ablauf im Editor mit Testpaketen geprüft (2026-10-08): zwei
        Reviewer, drei Sprachen, bis zum Export; Folgerungen für den Import
        im Umsetzungsentwurf, Abschnitt 8.2.
  - [ ] Paket der deutschen Gruppe, sobald ihre Korpusdokumente vorliegen.
  - [ ] Vorbelegung mit `verbalized` klären: Vorschläge bringen den Wert
        mit, neu angelegte Annotationen starten leer, weil das
        Aufgabenprofil des Editors keinen Standardwert kennt; der Editor
        lehnt leere Achsen beim Abschluss ab.
- [x] `make_annotation_review.py` löschen und
      `annotation-feasibility/README.md` anpassen; das Skript wird für den
      einheitlichen Vorschlagsschritt nicht mehr gebraucht, und seine 31
      ruff-Fehler halten CI auf `main` derzeit rot.
- [ ] Festgeschriebene deutsche Texte als benchmark-`Document`s
      (`translated`) erzeugen; bisher erzeugt keine Stufe übersetzte
      Dokumente, ein deutsches Annotationsset hat also kein Bezugsdokument.
- [ ] `curated-annotation-set/v2` einführen: Merkmal „nicht verbalisiert“
      (Richtlinie R6) und eine Herkunftsart für LLM-Vorschläge; v1 kennt
      keine passende Herleitungsquelle.
- [ ] Pilot des menschlichen Ablaufs: 2–3 Texte je Originalsprache Ende zu
      Ende durch Editor, Export, Import und Gold v1, bevor die volle
      Annotation beginnt; die deutsche Gruppe folgt nach ihren ersten
      geprüften Texten.
- [ ] Vorschläge im Editor ärztlich prüfen und Spannen nach der Richtlinie
      setzen; nicht verbalisierte Befunde strukturiert kennzeichnen.
- Optional, nicht geplant: Doppelannotation einer Teilmenge mit Paketen ohne
  Vorschläge, Schlichtung und Übereinstimmungsmaß. Bis dahin beruht das Gold
  auf einer ärztlichen Prüfung je Text; diese Einschränkung wird berichtet.
- [ ] Editor-Export importieren und je Annotationsgruppe ein akzeptiertes
      Gold v1 erzeugen.
      Der Import lehnt unterbrochene Belegstellen ab, fasst bestätigte
      Vorschläge mit gleichem Term und Status zu einer Annotation zusammen,
      führt das Editor-Ergebnis „uncertain“ als Rückfrage (nicht Gold) und
      ergänzt Prüfer-Metadaten aus einer Konfiguration. Je Gruppe entsteht
      eine Prüfstatistik (bestätigt, geändert, verworfen, ärztlich ergänzt).

### Single-Term-Aufgabe

- [ ] Single Terms ausschließlich aus den Spannen der fertig kuratierten
      E3C-HPO-Annotationen ableiten; kein eigener Spannen-Durchgang
      (Auswahlregeln: Richtlinie, Abschnitt „Single-term derivation“).
- [x] Entscheidung (2026-10-06): Single-Term-Fälle werden aus allen vier
      Annotationsgruppen abgeleitet, je Sprache als eigene Gruppe.
- [x] Entscheidung (2026-10-06): Nur klare Befunde (`present`, Patient)
      gehen in den Single-Term-Benchmark ein.
- [ ] Pro akzeptierter Annotation die phänotypische Formulierung in der
      Annotationssprache und die HPO-ID übernehmen.
- [ ] Single-Term-Fälle erst nach Übersetzung, Mapping und Annotation-Review
      freigeben.
- [ ] Ableitung und Verbindung zum zugehörigen Volltextfall dokumentieren.

## CSC – pausiert

Bis zur Wiederaufnahme werden keine HPO-Revisionen, Textverbesserungen oder
kuratierten CSC-Fassungen erzeugt.

### Quelle und Normalisierung

- [x] RAG-HPO-Commit
      `080fc3a04c91ee45c8986076765f4d4b4f14ddd9` festlegen und prüfen.
- [x] Excel-Arbeitsmappe als maßgebliche CSC-Quelle festlegen.
- [x] Abweichung durch doppelte CSV-Fälle dokumentieren.
- [x] 116 Texte aus `CSC Input` normalisieren.
- [x] 1.789 Quellzeilen zu 1.795 HPO-Annotationen auflösen.
- [x] Fehlende Evidenzspannen ausdrücklich dokumentieren.

### HPO-Revision

- [x] IDs gegen HPO `v2026-06-23` auditieren.
- [x] 1.779 aktive Annotationen identifizieren.
- [x] 15 obsolete Annotationen mit eindeutigem `replaced_by` identifizieren.
- [x] `HP:0025237` als obsolet mit ausschließlich
      `consider: HP:0000708` identifizieren.
- [x] Textfreies Audit und konservative Revisionsregeln dokumentieren.
- ⏸ Die 15 eindeutigen Änderungsvorschläge fachlich prüfen.
- ⏸ Den `consider`-Fall manuell beurteilen.
- ⏸ Kontrollieren, ob der jeweilige Text den vorgeschlagenen HPO-Term
  tatsächlich ausdrückt.
- ⏸ Originalannotation und revidierte Fassung getrennt erhalten.
- ⏸ Einen geprüften revidierten CSC-Goldstandard erzeugen.

### Textverbesserung

- ⏸ Technische und sprachliche Qualitätsprobleme der CSC-Texte untersuchen.
- ⚠ Vor Wiederaufnahme festlegen, ob nur technische Bereinigung oder auch
  sprachliche Überarbeitung erlaubt ist.
- ⏸ Originaltext und verbesserte Fassung getrennt erhalten.
- ⏸ Jede Textänderung gegen Fall-ID und HPO-Annotationen prüfen.

## GSC – pausiert

Bis zur Wiederaufnahme werden keine Textverbesserungen oder kuratierten
GSC-Fassungen erzeugt.

### Quelle und Normalisierung

- [x] Den gemeinsamen verifizierten RAG-HPO-Snapshot verwenden.
- [x] 114 Texte aus `GSC Input` normalisieren.
- [x] 1.012 Quellzeilen und 1.012 HPO-Annotationen übernehmen.
- [x] Zusammengesetzte Fallidentitäten exakt erhalten.
- [x] Fehlende Evidenzspannen ausdrücklich dokumentieren.

### HPO-Revision

- [x] Alle GSC-IDs gegen HPO `v2026-06-23` auditieren.
- [x] Bestätigen, dass alle 1.012 Annotationen aktuell sind.
- [x] Bestätigen, dass keine HPO-ID-Änderung erforderlich ist.
- ⏸ Bei einer späteren Textbearbeitung die Text-HPO-Konsistenz erneut prüfen.

### Textverbesserung

- ⏸ Technische und sprachliche Qualitätsprobleme der GSC-Texte untersuchen.
- ⚠ Vor Wiederaufnahme festlegen, ob nur technische Bereinigung oder auch
  sprachliche Überarbeitung erlaubt ist.
- ⏸ Originaltext und verbesserte Fassung getrennt erhalten.
- ⏸ Jede Textänderung gegen Fall-ID und HPO-Annotationen prüfen.

## Benchmark, Validierung und Veröffentlichung – später

- [ ] Akzeptierte E3C-Texte und HPO-Annotationen je Annotationsgruppe
      paketieren.
- [ ] Eingabeadapter für Phentrieve bereitstellen.
- [ ] Volltext-Benchmark definieren.
- [ ] E3C-Single-Term-Benchmark definieren.
- [ ] Benchmarkläufe reproduzierbar protokollieren.
- [ ] Qualitäts-, Review- und Abdeckungskennzahlen ausgeben.
- [ ] Release-Eignung anhand vollständiger Prüf- und Provenienzdaten prüfen.
- [x] ⚠ Die Lizenz- und Redistributionsentscheidung für den ungeprüften,
      nichtkommerziellen Review-Snapshot ist als dokumentierte
      Projektarbeitsannahme festgehalten, nicht als rechtliche Freigabe.
- [ ] Qualitätsfilter für ungeeignete Texte vor oder nach dem ärztlichen
      Review anwenden, in jedem Fall vor Beginn der Benchmark-Analyse;
      ausgeschlossene Texte mit Begründung gelistet lassen.
- [ ] Bewertungsregeln nach der Annotation festlegen. Der Datensatz
      unterstützt mindestens eine Sicht „nur vorhandene Befunde des
      Patienten“ (vergleichbar mit GSC/CSC) und eine aussagebewusste Sicht
      (HPO-ID und Aussagestatus).
- [x] Achsen und Vollständigkeit festgelegt (2026-10-06, Richtlinie R0/R3):
      betroffene Person `patient`/`family_member`/`other`, Zeitbezug
      `current`/`historical`, kein „ausgeheilt“, kein Aussagekontext;
      hypothetische und allgemeine Aussagen werden nicht annotiert, alle
      übrigen Phänotyp-Befunde jeder Person und jedes Status schon.
- [x] Issue #2 auf diesen Stand gebracht (Kommentar vom 2026-10-06).
- [ ] Lizenznachweis (`license-evidence.yaml`) auf den versionierten
      246-Texte-Snapshot erweitern; bisher begründet er nur den
      30-Fälle-Snapshot. Dabei die Lizenz der deutschen Übersetzungen der
      fünf CC-BY-NC-SA-3.0-Berichte festlegen (ShareAlike, siehe
      `datasets/e3c-de/PUBLISHER-LICENSES.md`).
- [x] Gelieferte `docLicense`-Werte aller 246 Berichte gegen Verlag/Archiv
      geprüft (2026-10-06): fünf JOCR-Berichte sind CC BY-NC-SA 3.0 statt
      `CC BY-NC`; alle übrigen stimmen in den Lizenzbedingungen überein.
- [ ] Finale Lizenz- und Redistributionsentscheidung vor der Veröffentlichung
      eines akzeptierten Benchmark-Releases festhalten.
- [ ] Deterministische Release-Manifeste und Datenkarten erzeugen.
- [ ] Nur geprüfte und ausdrücklich freigegebene Artefakte veröffentlichen.

## Aktuelle Priorität

1. Die gesamte Pipeline nach dem Umsetzungsentwurf bauen und Ende-zu-Ende
   testen (Aufteilung, Korpus, Vorschlagsschritt mit Pilot, Editor-Pakete,
   Format v2 und Import), bevor menschliche Arbeit beginnt.
2. Übersetzungsreview aller Texte der deutschen Gruppe durchführen.
3. Vorschläge für alle Gruppen erzeugen, Editor-Pakete bauen und im Editor
   spannenbasiert ärztlich prüfen.
4. Editor-Export importieren, Gold v1 je Gruppe erzeugen, danach
   Benchmark-Definition und Phentrieve-Adapter.
5. CSC und GSC bleiben bis zu einer ausdrücklichen Wiederaufnahme pausiert.
