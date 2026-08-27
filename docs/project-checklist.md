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
- [ ] Globale Testabdeckung wieder auf mindestens 90 % erhöhen; letzter
      vollständiger Lauf (2026-08-24): 815 Tests bestanden, 14
      plattformbedingt übersprungen, Coverage 88 %.
- [ ] Kostenpflichtige Operationen vor Ausführung grob kalkulieren und
      ausdrücklich bestätigen lassen.

## E3C – aktiv

Gestufte Strategie (2026-08-24): Stufe 1 liefert ein Dokument-Level-Gold auf
den deutschen Texten; Stufe 2 ergänzt Evidenzspannen nur für die
Single-Term-Teilmenge. Die Phase-0-Machbarkeitsprobe
(`datasets/e3c-de/annotation-feasibility/`) stützt diesen Weg.

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
      Dokument-Level-Ziel kein Engpass.
- [ ] Risikobasierten Übersetzungsreview durchführen: EN100593 gezielt
      (beide Probe-Befunde), Stichproben je Sprache; für den Vollkorpus
      später die 61 `units_added`-Fälle.
- [ ] Bei kritischen Fehlern eine Ausweitung des manuellen Reviews vorsehen.
- [ ] Reviewbefunde, Korrekturen und Entscheidungen getrennt dokumentieren.

### UMLS-zu-HPO-Mapping und deutsche Annotationen

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
      später und nur für die Single-Term-Teilmenge.
- [x] Phase-0-Probe zur Annotier-Machbarkeit: Gold-Kern aus 176 positiven
      Konsenstermen plus ~100 maschinell vorgeschlagenen Lückenkandidaten
      (81 gegen die gepinnte HPO aufgelöst); Engpass ist die
      Konzeptabdeckung, nicht die Sprache.
- [x] CUI-Triage der 200 häufigsten ungeklärten missing-CUIs: 83 kein
      Phänotyp, 64 Phänotyp ohne xref (55 Vorschläge maschinell gegen HPO
      validiert, 0 erfundene IDs), 48 zu generisch, 5 unklar.
- [ ] Konsolidiertes Vorschlags-Workbook je Fall erzeugen (Konsensterme +
      Lückenkandidaten, mit Herkunft und deutschem Zitat).
- [ ] Vorschläge ärztlich prüfen (bestätigen/verwerfen je Term); nicht
      verbalisierte Befunde nur per Notiz kennzeichnen, keine eigene Spalte.
- [ ] Akzeptierte Entscheidungen importieren und ein akzeptiertes
      deutsches Dokument-Level-Gold v1 erzeugen; Restlücke (zu generische
      und seltene CUIs) offen ausweisen.

### Single-Term-Aufgabe

- [ ] Single Terms ausschließlich aus den fertig kuratierten deutschen
      E3C-HPO-Annotationen ableiten (Stufe 2, nach dem Dokument-Level-Gold;
      erfordert Evidenzspannen nur für diese Teilmenge).
- [ ] Pro akzeptierter Annotation die deutsche phänotypische Formulierung und
      HPO-ID übernehmen.
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

- [ ] Akzeptierte deutsche E3C-Texte und HPO-Annotationen paketieren.
- [ ] Eingabeadapter für Phentrieve bereitstellen.
- [ ] Volltext-Benchmark definieren.
- [ ] E3C-Single-Term-Benchmark definieren.
- [ ] Benchmarkläufe reproduzierbar protokollieren.
- [ ] Qualitäts-, Review- und Abdeckungskennzahlen ausgeben.
- [ ] Release-Eignung anhand vollständiger Prüf- und Provenienzdaten prüfen.
- [x] ⚠ Die Lizenz- und Redistributionsentscheidung für den ungeprüften,
      nichtkommerziellen Review-Snapshot ist als dokumentierte
      Projektarbeitsannahme festgehalten, nicht als rechtliche Freigabe.
- [ ] Finale Lizenz- und Redistributionsentscheidung vor der Veröffentlichung
      eines akzeptierten Benchmark-Releases festhalten.
- [ ] Deterministische Release-Manifeste und Datenkarten erzeugen.
- [ ] Nur geprüfte und ausdrücklich freigegebene Artefakte veröffentlichen.

## Aktuelle Priorität

1. Konsolidiertes Annotationsvorschlags-Workbook für die 30er-Kohorte
   erzeugen und ärztlich prüfen.
2. Parallel den schlanken risikobasierten Übersetzungsreview durchführen
   (EN100593, Stichproben).
3. Akzeptierte Entscheidungen importieren, Dokument-Level-Gold v1 erzeugen,
   danach Benchmark-Definition und Phentrieve-Adapter.
4. CSC und GSC bleiben bis zu einer ausdrücklichen Wiederaufnahme pausiert.
