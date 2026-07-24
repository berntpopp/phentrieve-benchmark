# E3C Google-NMT-Übersetzungsphase

## Ziel und Umfang

Die 30 Fälle der Auswahl `e3c-de-feasibility-30-v1` werden mit Google Cloud
Translation von Englisch, Französisch oder Spanisch nach Deutsch übersetzt.
Verwendet wird Cloud Translation Advanced v3 mit dem expliziten Modell
`general/nmt`. Die Übersetzungsphase erzeugt noch keine HPO-Zuordnungen,
fachliche Freigabe oder veröffentlichbaren Benchmarkdaten.

Die Auswahl umfasst:

| Quellsprache | Fälle | Wörter | Zeichen | Sätze |
|---|---:|---:|---:|---:|
| Englisch | 10 | 2.999 | 20.293 | 189 |
| Französisch | 10 | 2.870 | 19.039 | 123 |
| Spanisch | 10 | 3.108 | 20.185 | 129 |
| **Gesamt** | **30** | **8.977** | **59.517** | **441** |

Die Wortzahl entspricht `len(canonical_text.split())`; die Zeichenanzahl
entspricht der Anzahl der Unicode-Codepoints im kanonischen Quelltext.

## Google-NMT-Aufruf und Kosten

Jeder Fall wird mit expliziter Quellsprache (`en`, `fr` oder `es`), Zielsprache
`de` und Modell `general/nmt` übersetzt. Die Anwendung verwendet die
Advanced-v3-Textübersetzung und übermittelt reinen Text, kein XMI oder anderes
Markup.

Google berechnet Standard-NMT nach den übermittelten Eingabezeichen je
Zielsprache. Bei einem Listenpreis von 20 USD pro Million Zeichen ergibt sich
für 59.517 Zeichen eine rechnerische Kostenobergrenze von 1,19034 USD. Der
monatliche Freibetrag kann die tatsächliche Rechnung reduzieren, wird für die
Freigabeentscheidung aber nicht vorausgesetzt. Vor einem kostenpflichtigen
Lauf zeigt die Pipeline erneut Fallzahl, Zeichenmenge, verwendeten Preis und
Kostenobergrenze an und verlangt die bereits projektweit vorgesehene
ausdrückliche Bestätigung.

Die Preisannahme wird als Laufmetadatum gespeichert, damit die Schätzung auch
bei späteren Preisänderungen nachvollziehbar bleibt. Die tatsächliche
Cloud-Rechnung ist nicht Bestandteil des Datenartefakts.

## Artefaktmodell

Original und Übersetzung werden pro Fall als getrennte, unveränderliche
Artefakte im Git-ignorierten inhaltsadressierten Artefaktspeicher abgelegt.
Eine Korrektur oder erneute Übersetzung erzeugt eine neue Revision mit neuem
Hash; vorhandene Fassungen werden nicht überschrieben.

Das Originalartefakt enthält ausschließlich den kanonischen L1-Quelltext. Das
Übersetzungsartefakt enthält ausschließlich den von Google zurückgegebenen
deutschen Text. Lauf- und Providerinformationen liegen getrennt in einem
Übersetzungsdatensatz mit diesen Feldern:

- Schema-Version und Übersetzungs-ID
- Auswahl-ID und Fall-ID
- Quell- und Zielsprache
- Hash des Originalartefakts und Hash des Übersetzungsartefakts
- Provider `google-cloud-translation`
- API `v3` und Modell `general/nmt`
- Google-Projektkennung in nicht-geheimer, für Abrechnung geeigneter Form
- Region des API-Aufrufs
- Zeitpunkt des Aufrufs
- Eingabezeichen und zurückgegebene Ausgabezeichen
- verwendeter Preis pro Million Eingabezeichen
- geschätzte Maximalkosten des Aufrufs
- Vorgänger-ID bei einer neuen Revision
- Status und maschinenlesbare Prüfhinweise

Zugangsdaten, API-Schlüssel und Zugriffstoken werden weder in Artefakten noch
in Manifesten oder Logs gespeichert.

## Manifest im Repository

Nach einem vollständigen Lauf wird ein textfreies Manifest unter
`datasets/e3c-de/translations/` erzeugt. Es enthält pro Fall die Identitäten
der Original-, Übersetzungs- und Metadatenartefakte sowie Sprache, Modell,
Zeichenmengen, Status und Revisionsbeziehung. Es enthält keine Original- oder
Übersetzungstexte.

Das Manifest referenziert exakt die bestehende Auswahl und deren Hash. Ein
unvollständiger Lauf darf ein Arbeitsmanifest erzeugen, ersetzt aber nicht das
Manifest eines zuvor vollständig erfolgreichen Laufs.

## Ablauf und Status

Für jeden ausgewählten Fall gilt folgender Ablauf:

1. Auswahl und Originalartefakt laden und deren Hashes prüfen.
2. Quellsprache aus der Auswahl übernehmen und nicht automatisch erkennen.
3. Zeichenmenge und anteilige Kostenobergrenze berechnen.
4. Google NMT genau einmal für den aktuellen Versuch aufrufen.
5. Antwort validieren und als neues unveränderliches Artefakt speichern.
6. Automatische Prüfungen ausführen.
7. Übersetzungsdatensatz und Laufprovenienz schreiben.

Ein Übersetzungsdatensatz verwendet genau einen dieser Statuswerte:

- `translated`: gültige Providerantwort gespeichert
- `automatic_check_failed`: mindestens eine automatische Mindestprüfung
  fehlgeschlagen
- `ready_for_review`: automatische Mindestprüfungen bestanden
- `reviewed`: ein vorgesehener manueller Review wurde dokumentiert
- `accepted`: Übersetzung nach dem vorgesehenen Review freigegeben

`pending` ist nur ein Planungszustand im Arbeitsmanifest und kein Ergebnis
eines Provideraufrufs. Provider- oder Transportfehler werden als
fehlgeschlagene Versuche in der Laufprovenienz erfasst und erzeugen keine
scheinbar erfolgreiche Übersetzungsrevision.

## Automatische Mindestprüfungen

Eine Providerantwort wird zurückgewiesen, wenn sie fehlt, leer ist, nur aus
Whitespace besteht oder nicht eindeutig dem angefragten Fall zugeordnet
werden kann. Danach prüfen deterministische Regeln mindestens:

- Zielsprachenerkennung ergibt Deutsch,
- Zahlen aus dem Original fehlen nicht unerklärt,
- Maßeinheiten und Prozentangaben fehlen nicht unerklärt,
- auffällige Längenabweichungen werden markiert,
- die Ausgabe entspricht nicht unverändert dem Original,
- alle 30 ausgewählten Fall-IDs sind im vollständigen Lauf genau einmal
  vertreten.

Diese Regeln ersetzen keine medizinische, bilinguale oder fachsprachliche
Prüfung. Negation, Auslassungen und Bedeutungsverschiebungen werden als
Prüfkategorien im Reviewmodell geführt; eine rein automatische Freigabe bis
`accepted` ist ausgeschlossen.

## Wiederaufnahme und Fehlerverhalten

Ein erneuter Lauf verwendet bereits vorhandene, vollständig validierte
Übersetzungsrevisionen nur dann wieder, wenn Auswahl-ID, Originalhash,
Quellsprache, Zielsprache, Provider, API-Version und Modell identisch sind.
Fehlgeschlagene Fälle können einzeln wiederholt werden. Erfolgreiche Fälle
werden dabei nicht erneut abgerechnet.

Unerwartete Providerantworten, Quotenfehler und Netzwerkfehler stoppen den
betroffenen Fall kontrolliert. Ein Laufbericht unterscheidet erfolgreiche,
fehlgeschlagene, wiederverwendete und noch ausstehende Fälle.

## Tests und Dokumentation

Offline-Tests verwenden einen simulierten Google-Client und prüfen
Requestparameter, Zeichen- und Kostenberechnung, Fehlerantworten,
Unveränderlichkeit, Wiederaufnahme sowie das textfreie Manifest. Ein
kostenpflichtiger Live-Test gehört nicht in die reguläre CI.

Die E3C-Dokumentation beschreibt den vorbereitenden Kostencheck, die
Authentifizierung über die von Google vorgesehenen Umgebungsmechanismen, den
Übersetzungslauf, die Artefaktgrenzen und die anschließende Reviewphase. Der
Umfang des bilingualen und medizinischen Reviews bleibt eine getrennte, vor
der Freigabe zu klärende Entscheidung.

## Abnahmekriterien

Die Übersetzungsphase ist technisch vorbereitet, wenn:

- alle 30 Fälle deterministisch aus der bestehenden Auswahl geladen werden,
- die Kostenobergrenze vor dem API-Aufruf ausgewiesen wird,
- ein bestätigter Lauf getrennte Original- und Übersetzungsartefakte erzeugt,
- keine Providerzugangsdaten persistiert werden,
- leere oder ungültige Antworten nicht als Erfolg gelten,
- Wiederholungen keine bestehenden Revisionen überschreiben,
- ein textfreies, auf die Auswahl zurückführbares Manifest entsteht und
- die Offline-Tests ohne Google-Zugriff laufen.
