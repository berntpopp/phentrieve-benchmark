"""Generate the Excel review workbook and HTML reading view for the
E3C-DE annotation review (30-case cohort).

All prefilled rows are machine-generated proposals from the Phase 0
feasibility probe (see README.md in this directory) - not review data, not a
gold standard. Every proposed HPO ID/label is resolved exactly against the
pinned hp.obo v2026-06-23 (lexical, deterministic, no retrieval model).

Inputs: probe files in this directory; German case texts from the tracked
review snapshot; the pinned hp.obo from the local artifact store (a lookup
cache is built on first run). Outputs go to .artifacts/review-workbooks/.
Requires the xlsxwriter package (pip install xlsxwriter); openpyxl rich text
produced files Excel had to repair, xlsxwriter rich strings do not.
Run from the repository root:
python datasets/e3c-de/annotation-feasibility/make_annotation_review.py [en|es|fr]
Without an argument the workbook covers all 30 cases; with a language it
covers only that source language's 10 cases as an independent workbook.
"""
import collections
import html
import json
import math
import os
import re
import sys
from datetime import date

import xlsxwriter

PROBE = "datasets/e3c-de/annotation-feasibility"
TEXTS = "datasets/e3c-de/review/e3c-de-feasibility-30-v1"
HPO_OBO = (".artifacts/objects/sha256/a5/"
           "a5092cbdf605f568403cf7380d9173014015692433b2cc631bc5c1b053876b1b")
LOOKUP_CACHE = ".artifacts/review-workbooks/hpo-lookup.json"
OUT = ".artifacts/review-workbooks"
NCOL = 11  # A..K

_args = sys.argv[1:]
SOURCE_MODE = "--source" in _args
_args = [a for a in _args if a != "--source"]
LANG_FILTER = _args[0].lower() if _args else None
if LANG_FILTER not in (None, "en", "es", "fr"):
    raise SystemExit(f"Unbekannte Sprache: {LANG_FILTER} (erlaubt: en, es, fr)")
if SOURCE_MODE and LANG_FILTER != "en":
    raise SystemExit("--source ist bisher nur fuer en vorbereitet")
SUFFIX = LANG_FILTER if LANG_FILTER else "30"
BASENAME = (f"e3c-{LANG_FILTER}-annotation-review" if SOURCE_MODE
            else f"e3c-de-annotation-review-{SUFFIX}")
ZITAT_SPRACHE = "englisch" if SOURCE_MODE else "deutsch"

os.makedirs(OUT, exist_ok=True)
if not os.path.exists(LOOKUP_CACHE):
    obo = open(HPO_OBO, encoding="utf-8").read()
    terms, labels = {}, {}
    for block in obo.split("\n[Term]\n")[1:]:
        tid = re.search(r"^id: (HP:\d+)", block, re.M)
        name = re.search(r"^name: (.+)", block, re.M)
        obs = bool(re.search(r"^is_obsolete: true", block, re.M))
        if tid and name:
            terms[tid.group(1)] = {"name": name.group(1), "obsolete": obs}
            if not obs:
                labels[name.group(1).lower()] = tid.group(1)
                for syn in re.findall(r'^synonym: "([^"]+)" EXACT', block, re.M):
                    labels.setdefault(syn.lower(), tid.group(1))
    json.dump({"terms": terms, "labels": labels},
              open(LOOKUP_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
lk = json.load(open(LOOKUP_CACHE, encoding="utf-8"))
terms_db, labels_db = lk["terms"], lk["labels"]
bundle = json.load(open(f"{PROBE}/input/teil-a-faelle.json", encoding="utf-8"))
relevance = {(c["case_id"], t["annotation_id"]): t["relevance"]
             for c in bundle["cases"] for t in c["consensus_terms"]}

# --- Zeilen aufbauen -------------------------------------------------------
rows = []
for lang in ("en", "es", "fr"):
    d = json.load(open(f"{PROBE}/teil-a-{lang}.json", encoding="utf-8"))
    for c in d["cases"]:
        cid = c["case_id"]
        seen = set()
        for t in c["terms"]:
            if relevance.get((cid, t["annotation_id"])) != "positive_patient_phenotype":
                continue
            seen.add(t["hpo_id"])
            note = t["note"] or ""
            if t["verdict"] != "haelt":
                note = f"ACHTUNG ({t['verdict']}): {note}"
            rows.append(dict(case=cid, lang=lang, src="Audit-Konsens", hid=t["hpo_id"],
                             label=t["hpo_label"], quote=t["quote_de"] or "", note=note,
                             aid=t["annotation_id"]))
        for gap_index, g in enumerate(c["gaps"]):
            s = g.get("suggested_hpo") or {}
            hid, hlabel = s.get("id") or "", s.get("label") or ""
            # Halluzinations-Gate gegen gepinnte HPO
            if hid and hid in terms_db and not terms_db[hid]["obsolete"]:
                check = "ID geprüft"
                if (terms_db[hid]["name"].lower() != hlabel.lower()
                        and labels_db.get(hlabel.lower()) != hid):
                    hlabel = f"{hlabel} [HPO-Label: {terms_db[hid]['name']}]"
            elif hid:
                check, hid = "ID unbekannt, verworfen", ""
            elif hlabel and labels_db.get(hlabel.lower()):
                hid = labels_db[hlabel.lower()]
                check = "Label aufgelöst, ID ergänzt"
                hlabel = terms_db[hid]["name"]
            elif hlabel:
                check = "nur Label, nicht auflösbar"
            else:
                check, hlabel = "ohne Vorschlag", ""
            if hid and hid in seen:
                continue
            rows.append(dict(case=cid, lang=lang, src=f"Lücken-Vorschlag ({check})",
                             hid=hid, label=hlabel or g["description_de"],
                             quote=g["quote_de"] or "", note=g["description_de"],
                             gapi=gap_index))

# --- Audit-Einzelbestaetigungen (nur ein Pruefdurchgang) --------------------
AUDIT = "datasets/e3c-de/mappings/audit"
SAFE = {"direct_valid", "semantic_candidate_exact"}
KLASSE = {
    "direct_valid": "direkter Verweis gültig",
    "semantic_candidate_exact": "exakter Kandidat",
    "semantic_candidate_broader_or_narrower": "nur breiterer/engerer Kandidat",
    "no_hpo_but_relevant": "relevant, aber kein passender HPO-Begriff",
    "not_hpo_relevant": "nicht HPO-relevant",
    "direct_context_mismatch": "Verweis passt nicht zum Kontext",
    "ambiguous_direct": "mehrere direkte Ziele",
    "invalid_or_unrecoverable": "ungültige Quellangabe",
}


def _target(rec):
    c = rec.get("hpo_candidates") or []
    return (c[0]["hpo_id"], c[0]["label"]) if c else None


audit_a = json.load(open(f"{AUDIT}/agent-a.json", encoding="utf-8"))["records"]
audit_b = json.load(open(f"{AUDIT}/agent-b.json", encoding="utf-8"))["records"]
b_idx = {(r["case_id"], r["annotation_id"]): r for r in audit_b}
a_idx = {(r["case_id"], r["annotation_id"]): r for r in audit_a}
seen_by_case = collections.defaultdict(set)
for r in rows:
    if r["hid"]:
        seen_by_case[r["case"]].add(r["hid"])
lang_of = {r["case"]: r["lang"] for r in rows}
for ra in audit_a:
    rb = b_idx.get((ra["case_id"], ra["annotation_id"]))
    if rb is None:
        continue
    ta, tb = _target(ra), _target(rb)
    safe_a, safe_b = ra["audit_class"] in SAFE, rb["audit_class"] in SAFE
    if safe_a and safe_b and ta == tb:
        continue  # Konsens, bereits enthalten
    for rec, tgt, other, other_tgt in ((ra, ta, rb, tb), (rb, tb, ra, ta)):
        if not (rec["audit_class"] in SAFE and tgt):
            continue
        if rec["relevance"] != "positive_patient_phenotype":
            continue
        hid, hlabel = tgt
        if hid not in terms_db or terms_db[hid]["obsolete"]:
            continue  # Halluzinations-Gate
        cid = rec["case_id"]
        if hid in seen_by_case[cid]:
            continue
        seen_by_case[cid].add(hid)
        if other["audit_class"] in SAFE and other_tgt and other_tgt != tgt:
            anders = f"anderer Prüfdurchgang wählte {other_tgt[0]} ({other_tgt[1]})"
        else:
            anders = f"anderer Prüfdurchgang: {KLASSE.get(other['audit_class'], other['audit_class'])}"
        rows.append(dict(case=cid, lang=lang_of.get(cid, cid[:2].lower()),
                         src="Audit (einzeln bestätigt)", hid=hid,
                         label=terms_db[hid]["name"], quote="",
                         note=f"Quellspan: '{rec['span']}'; {anders}.",
                         aid=rec["annotation_id"]))

if LANG_FILTER:
    rows = [r for r in rows if r["lang"] == LANG_FILTER]

_RANK = {"Audit-Konsens": 0, "Audit (einzeln bestätigt)": 1}
rows.sort(key=lambda r: (r["case"], _RANK.get(r["src"], 2), r["hid"]))
for i, r in enumerate(rows, 1):
    r["nr"] = i

# --- Fundstellen lokalisieren ----------------------------------------------
gap_quotes = {}
if SOURCE_MODE:
    for cand in (f"{PROBE}/input/en-source-gap-quotes.json",
                 ".artifacts/reviews/e3c-de/probe-0/en-source-gap-quotes.json"):
        if os.path.exists(cand):
            gq = json.load(open(cand, encoding="utf-8"))
            gap_quotes = {(g["case_id"], g["gap_index"]): g.get("quote_en") or ""
                          for g in gq["gaps"] if g.get("found")}
            break
    else:
        raise SystemExit("en-source-gap-quotes.json fehlt (Gap-Relokalisierung)")

texts = {}
offset_mismatch = 0
for r in rows:
    cid = r["case"]
    if cid not in texts:
        fn = (f"{TEXTS}/{cid}/source.{r['lang']}.txt" if SOURCE_MODE
              else f"{TEXTS}/{cid}/tllm.de.txt")
        texts[cid] = open(fn, encoding="utf-8").read()
    txt = texts[cid]
    if SOURCE_MODE:
        rec = a_idx.get((cid, r.get("aid") or ""))
        if rec is not None:
            o = rec["source_offsets"]
            s, e = o["mapping_evidence_start"], o["mapping_evidence_end"]
            r["start"], r["end"], r["quote"] = s, e, txt[s:e]
            if txt[s:e].strip().lower() != (rec["span"] or "").strip().lower():
                offset_mismatch += 1
            continue
        r["quote"] = gap_quotes.get((cid, r.get("gapi")), "")
    q = r["quote"]
    pos = txt.find(q) if q else -1
    if pos < 0 and " ... " in q:
        q = max(q.split(" ... "), key=len)
        pos = txt.find(q)
    r["start"], r["end"] = (pos, pos + len(q)) if pos >= 0 else (None, None)
unlocated = [r["nr"] for r in rows if r["start"] is None and r["quote"]]
if offset_mismatch:
    print("WARNUNG: Offset/Span-Abweichungen:", offset_mismatch)

by_case = collections.defaultdict(list)
for r in rows:
    by_case[r["case"]].append(r)
case_order = sorted(by_case)


def merged_marks(cid):
    """Ueberlappende Fundstellen zu (start, end, rows)-Spannen zusammenfassen."""
    marks = sorted((r for r in by_case[cid] if r["start"] is not None),
                   key=lambda r: (r["start"], r["end"]))
    merged = []
    for r in marks:
        if merged and r["start"] < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], r["end"])
            merged[-1][2].append(r)
        else:
            merged.append([r["start"], r["end"], [r]])
    return merged


# --- Excel (xlsxwriter) ----------------------------------------------------
COLS = ["Nr", "Fall", "Sprache", "Herkunft", "HPO-ID", "HPO-Label",
        f"Zitat ({ZITAT_SPRACHE})", "Hinweis", "Entscheidung",
        "Korrektur (HPO-ID oder Name)", "Notiz"]
WIDTHS = (5, 10, 8, 26, 12, 30, 42, 40, 13, 22, 24)
CHARS_PER_LINE = 150  # gesamte Blattbreite (A..K verbunden)

info = [
    (f"Anleitung: Prüfung der Symptom-Zuordnungen ({len(case_order)} Fallberichte)", True),
    ("", False),
    ("Worum geht es?", True),
    ((f"{len(case_order)} klinische Fallberichte liegen im englischen Original vor. Zu"
      if SOURCE_MODE else
      f"{len(case_order)} klinische Fallberichte wurden maschinell ins Deutsche übersetzt. Zu"), False),
    ("jedem Text wurden automatisch Symptome bzw. Phänotypen als HPO-Begriffe", False),
    ("vorgeschlagen. Diese Vorschläge sind ungeprüft - erst Ihre Entscheidung", False),
    ("macht daraus verlässliche Daten.", False),
    ("", False),
    ("So ist das Blatt 'Review' aufgebaut:", True),
    ("1. Blauer Balken = Beginn eines Falls.", False),
    (("2. Darunter der vollständige englische Originaltext. Stellen, auf die sich ein"
      if SOURCE_MODE else
      "2. Darunter der vollständige deutsche Text. Stellen, auf die sich ein"), False),
    ("   Vorschlag bezieht, sind fett und rot markiert; die Nummer in eckigen", False),
    ("   Klammern, z. B. [12], verweist auf die Zeile Nr. 12 in der Tabelle.", False),
    ("3. Danach die Tabelle mit den Vorschlägen dieses Falls.", False),
    ("4. Gelbe Zeilen am Ende: Platz für eigene Ergänzungen.", False),
    ("", False),
    ("So prüfen Sie einen Fall:", True),
    ("1. Den Text vollständig lesen.", False),
    ("2. Für jede Tabellenzeile in der Spalte 'Entscheidung' wählen:", False),
    ("   übernehmen - der Begriff trifft für diesen Patienten zu.", False),
    ("   ändern - fast richtig, aber ein anderer HPO-Begriff passt besser;", False),
    ("     den besseren Begriff (ID oder Name) in die Spalte 'Korrektur'", False),
    ("     schreiben. Der ursprüngliche Vorschlag bleibt dokumentiert.", False),
    ("   verwerfen - trifft nicht zu.", False),
    ("   unsicher - nicht sicher entscheidbar; bitte kurze Begründung in", False),
    ("     der Spalte 'Notiz'.", False),
    ("3. Fehlt ein Symptom, das im Text steht, aber in keiner Zeile auftaucht?", False),
    ("   Bitte in eine gelbe Zeile eintragen (HPO-ID und/oder Name). Die", False),
    ("   Textstelle in 'Zitat' ist hilfreich, aber nicht nötig - ohne Zitat", False),
    ("   gilt der Begriff für den ganzen Text. Reichen die gelben Zeilen", False),
    ("   nicht, einfach weitere einfügen.", False),
    ("", False),
    ("Wichtige Hinweise:", True),
    ("- Es zählt nur, was der Text über den Patienten selbst positiv aussagt.", False),
    ("  Verneinte, frühere, unsichere oder auf Angehörige bezogene Befunde", False),
    ("  bitte nicht übernehmen.", False),
    ("- Steht im Text nur ein Messwert (z. B. 'CRP 3,7 mg/dl') ohne wertende", False),
    ("  Formulierung, den Begriff trotzdem beurteilen und in 'Notiz'", False),
    ("  'nicht verbalisiert' vermerken.", False),
    ("", False),
    ("Wie sind die Vorschläge entstanden? (Spalte 'Herkunft')", True),
    ("Die Fallberichte stammen aus dem frei verfügbaren E3C-Korpus. Dessen", False),
    ("Ersteller hatten medizinische Begriffe in den Texten markiert. Diese", False),
    ("Markierungen wurden automatisch in HPO-Begriffe übersetzt, danach haben", False),
    ("zwei voneinander unabhängige KI-Prüfungen jede markierte Stelle im", False),
    ("Satzzusammenhang beurteilt (passt der Begriff? ist der Befund verneint,", False),
    ("historisch, eine andere Person?). Zusätzlich hat eine KI-Durchsicht die", False),
    ("vollständigen Texte auf Symptome geprüft, die dabei noch fehlten.", False),
    ("Daraus ergeben sich die Werte in der Spalte 'Herkunft':", False),
    ("", False),
    ("- Audit-Konsens: Die Stelle war im E3C-Korpus markiert, und beide", False),
    ("  KI-Prüfungen kamen unabhängig zum selben HPO-Begriff.", False),
    ("  Die zuverlässigste Gruppe.", False),
    ("- Audit (einzeln bestätigt): Die Stelle war markiert, aber nur eine der", False),
    ("  beiden KI-Prüfungen hielt den Begriff für sicher; was die andere", False),
    ("  meinte, steht in der Spalte 'Hinweis'. Bitte besonders sorgfältig", False),
    ("  prüfen." + ("" if SOURCE_MODE else
     " Diese Zeilen haben kein deutsches Zitat und sind im Text"), False),
    (("" if SOURCE_MODE else
      "  nicht markiert; bitte im ganzen Text prüfen."), False),
    ("- Lücken-Vorschlag (ID geprüft): Diese Stelle war im E3C-Korpus NICHT", False),
    ("  markiert. Die KI-Durchsicht hat das Symptom zusätzlich gefunden und", False),
    ("  einen HPO-Begriff vorgeschlagen, der in der HPO existiert und aktiv", False),
    ("  ist.", False),
    ("- Lücken-Vorschlag (ohne Vorschlag): Zusätzlich gefundene Auffälligkeit,", False),
    ("  für die kein konkreter HPO-Begriff vorgeschlagen wurde - bitte selbst", False),
    ("  ergänzen oder die Zeile verwerfen.", False),
    ("- Ärztliche Ergänzung: leere gelbe Zeilen für Ihre eigenen Funde.", False),
    ("", False),
    ("Wichtig: Alle KI-Vorschläge sind ungeprüfte Hinweise, keine Diagnosen.", False),
    ("Jede vorgeschlagene HPO-ID wurde automatisch gegen die HPO-Version", False),
    ("v2026-06-23 abgeglichen; erfundene IDs sind ausgeschlossen. Ob der", False),
    ("Begriff inhaltlich stimmt, entscheiden allein Sie.", False),
    ("", False),
    ("Dieselbe Ansicht gibt es auch für den Browser:", False),
    (f"{BASENAME}.html (Markierungen als farbige Textmarker).", False),
    ("", False),
    (f"Automatisch erstellt am {date.today()}; Datengrundlage:", False),
    ("datasets/e3c-de/annotation-feasibility/", False),
]


def build_workbook(path):
    wb = xlsxwriter.Workbook(path)
    f_bold = wb.add_format({"bold": True})
    f_mark = wb.add_format({"bold": True, "font_color": "#B00000"})
    f_case = wb.add_format({"bold": True, "font_color": "#FFFFFF",
                            "bg_color": "#305496", "font_size": 12})
    f_text = wb.add_format({"text_wrap": True, "valign": "top",
                            "bg_color": "#FAFAFA"})
    f_head = wb.add_format({"bold": True, "bg_color": "#D9D9D9"})
    f_cell = wb.add_format({"text_wrap": True, "valign": "top"})
    f_add = wb.add_format({"text_wrap": True, "valign": "top",
                           "bg_color": "#FDF2DC"})

    ws = wb.add_worksheet("Anleitung")
    ws.set_column(0, 0, 95)
    for i, (txt_, bold) in enumerate(info):
        if txt_:
            ws.write_string(i, 0, txt_, f_bold if bold else None)

    ws2 = wb.add_worksheet("Review")
    for c, w in enumerate(WIDTHS):
        ws2.set_column(c, c, w)

    r = 0
    for cid in case_order:
        txt = texts[cid]
        lang = by_case[cid][0]["lang"]
        marks = merged_marks(cid)

        ws2.merge_range(r, 0, r, NCOL - 1, f"Fall {cid}  ({lang})", f_case)
        r += 1

        offset = 0
        for par in txt.split("\n"):
            if par.strip():
                p_start, p_end = offset, offset + len(par)
                parts, pos, extra = [], p_start, 0
                for s, e, rs in marks:
                    if e <= p_start or s >= p_end:
                        continue
                    s2, e2 = max(s, p_start), min(e, p_end)
                    if txt[pos:s2]:
                        parts.append(txt[pos:s2])
                    parts.append(f_mark)
                    parts.append(txt[s2:e2])
                    ref = " [" + ",".join(str(x["nr"]) for x in rs) + "]"
                    parts.append(ref)
                    extra += len(ref)
                    pos = e2
                if txt[pos:p_end]:
                    parts.append(txt[pos:p_end])
                ws2.merge_range(r, 0, r, NCOL - 1, "", f_text)
                has_marks = any(not isinstance(p, str) for p in parts)
                if has_marks:
                    ws2.write_rich_string(r, 0, *parts, f_text)
                else:
                    ws2.write_string(r, 0, par, f_text)
                lines = max(1, math.ceil((len(par) + extra) / CHARS_PER_LINE))
                ws2.set_row(r, min(405, 14 * lines + 4))
                r += 1
            offset += len(par) + 1

        for c, h in enumerate(COLS):
            ws2.write_string(r, c, h, f_head)
        r += 1
        for row in by_case[cid]:
            vals = [row["nr"], cid, row["lang"], row["src"], row["hid"],
                    row["label"], row["quote"], row["note"], "", "", ""]
            for c, v in enumerate(vals):
                if isinstance(v, int):
                    ws2.write_number(r, c, v, f_cell)
                elif v:
                    ws2.write_string(r, c, v, f_cell)
                else:
                    ws2.write_blank(r, c, None, f_cell)
            r += 1
        for _ in range(3):
            vals = ["", cid, lang, "Ärztliche Ergänzung"] + [""] * 7
            for c, v in enumerate(vals):
                if v:
                    ws2.write_string(r, c, v, f_add)
                else:
                    ws2.write_blank(r, c, None, f_add)
            r += 1
        r += 1  # Trennzeile

    ws2.data_validation(0, 8, r, 8, {
        "validate": "list",
        "source": ["übernehmen", "ändern", "verwerfen", "unsicher"]})
    wb.close()
    return r


tmp = f"{OUT}/.{BASENAME}.tmp.xlsx"
total_rows = build_workbook(tmp)
target = f"{OUT}/{BASENAME}.xlsx"
try:
    os.replace(tmp, target)
    saved = os.path.basename(target)
except PermissionError:
    alt = f"{OUT}/{BASENAME}-v2.xlsx"
    os.replace(tmp, alt)
    saved = os.path.basename(alt) + " (Original gesperrt)"

# --- HTML-Lesensicht -------------------------------------------------------
def render_case(cid):
    txt = texts[cid]
    out, pos = [], 0
    for s, e, rs in merged_marks(cid):
        out.append(html.escape(txt[pos:s]))
        kinds = {x["src"].startswith("Audit") for x in rs}
        cls = "kons" if kinds == {True} else "gap" if kinds == {False} else "mixed"
        tip = " | ".join(f"Nr {x['nr']}: {x['hid'] or '?'} {x['label']}" for x in rs)
        sup = ",".join(str(x["nr"]) for x in rs)
        out.append(f'<mark class="{cls}" title="{html.escape(tip)}">'
                   f'{html.escape(txt[s:e])}</mark><sup>{sup}</sup>')
        pos = e
    out.append(html.escape(txt[pos:]))
    body = "".join(out).replace("\n", "<br>\n")
    tbl = "".join(
        f'<tr><td>{r["nr"]}</td>'
        f'<td class="{"kons" if r["src"].startswith("Audit") else "gap"}">'
        f'{html.escape(r["src"])}</td><td>{r["hid"]}</td>'
        f'<td>{html.escape(r["label"])}</td><td>{html.escape(r["note"])}</td>'
        f'<td>{"" if r["start"] is not None else ("ohne deutsches Zitat" if not r["quote"] else "Zitat nicht lokalisiert")}</td></tr>'
        for r in by_case[cid])
    return (f'<section id="{cid}"><h2>{cid}</h2><div class="text">{body}</div>'
            f'<table><tr><th>Nr</th><th>Herkunft</th><th>HPO-ID</th><th>Label</th>'
            f'<th>Hinweis</th><th></th></tr>{tbl}</table></section>')


nav = " ".join(f'<a href="#{c}">{c}</a>' for c in case_order)
style = """
body{font-family:Georgia,serif;max-width:60rem;margin:2rem auto;padding:0 1rem;line-height:1.65}
header{border:2px solid #b00;padding:.7rem 1rem;background:#fff4f4;font-family:sans-serif}
nav{position:sticky;top:0;background:#fff;padding:.5rem 0;border-bottom:1px solid #ccc;font-family:sans-serif;font-size:.85rem}
nav a{margin-right:.55rem;text-decoration:none}
.text{background:#fafafa;border:1px solid #ddd;padding:1rem 1.3rem;border-radius:6px}
mark.kons{background:#c8e6c9} mark.gap{background:#ffe082} mark.mixed{background:#b3e5fc}
sup{font-family:sans-serif;font-size:.68em;color:#555}
table{border-collapse:collapse;font-family:sans-serif;font-size:.83rem;margin:1rem 0 2.5rem;width:100%}
td,th{border:1px solid #ccc;padding:.25rem .5rem;text-align:left;vertical-align:top}
td.kons{background:#e8f5e9} td.gap{background:#fff8e1}
h2{font-family:sans-serif;border-bottom:2px solid #333;padding-bottom:.2rem}
.legend span{padding:0 .5rem;margin-right:.7rem}
"""
page = (f'<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
        f'<title>E3C-DE Annotationsreview - Lesensicht ({len(case_order)} Faelle)</title>'
        f'<style>{style}</style></head><body>'
        f'<header><strong>Maschinell erzeugte Vorschlaege - keine Reviewdaten, '
        f'kein Goldstandard.</strong><br>Lesensicht zur Excel-Datei '
        f'<code>{BASENAME}.xlsx</code>; Entscheidungen bitte dort '
        f'eintragen (gleiche Nr.). Die Markierungen sind kein abgeschlossenes '
        f'Inventar: Beim Lesen vermisste Phaenotypen bitte im Excel in den Zeilen '
        f'"Aerztliche Ergaenzung" des Falls nachtragen (Zitat optional; ohne Zitat '
        f'gilt der Term fuer den ganzen Text). Alle HPO-IDs exakt gegen die '
        f'gepinnte HPO v2026-06-23 aufgeloest. '
        f'Erzeugt am {date.today()} von Claude (Opus 5).'
        f'<div class="legend"><span style="background:#c8e6c9">Audit-Konsens</span>'
        f'<span style="background:#ffe082">Luecken-Vorschlag</span>'
        f'<span style="background:#b3e5fc">beides</span></div></header>'
        f'<nav>{nav}</nav>{"".join(render_case(c) for c in case_order)}'
        f'</body></html>')
with open(f"{OUT}/{BASENAME}.html", "w", encoding="utf-8",
          newline="\n") as fh:
    fh.write(page)

src_stats = collections.Counter(r["src"] for r in rows)
print("gespeichert:", saved)
print("Zeilen:", len(rows))
for k, v in sorted(src_stats.items()):
    print(f"  {k}: {v}")
print("nicht lokalisierte Zitate:", unlocated or "keine")
