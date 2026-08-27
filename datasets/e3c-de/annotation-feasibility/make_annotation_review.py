"""Generate the Excel review workbook and HTML reading view for the
E3C annotation review (30-case cohort).

All prefilled rows are machine-generated proposals - not review data, not a
gold standard. Every proposed HPO ID/label is resolved exactly against the
pinned hp.obo v2026-06-23 (lexical, deterministic, no retrieval model).

Each row carries two orthogonal facts:
- "Ableitung": how the HPO term came to be - "Referenz" (deterministic
  UMLS-to-HPO cross-reference), "KI (E3C-Stelle)" (LLM proposal for an
  E3C-annotated span), "KI (Volltext)" (LLM full-text sweep), "Ärztlich"
  (reviewer addition), or "-" (E3C span without a usable term).
- "Einschätzung": the contextual assessment (2/2 or 1/2 passes confirmed,
  contradiction with context, ambiguous, only-similar term, no term, not a
  phenotype, verified ID, no proposal).

Inputs: probe files in this directory; case texts from the tracked review
snapshot; the cohort mapping manifest; the pinned hp.obo from the local
artifact store (a lookup cache is built on first run). Outputs go to
.artifacts/review-workbooks/. Requires the xlsxwriter package.
Run from the repository root:
python datasets/e3c-de/annotation-feasibility/make_annotation_review.py [en|es|fr] [--source]
Without arguments the workbook covers all 30 cases on the German
translations; with a language plus --source it covers that language's
cases on the original source texts.
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
MAPPING_30 = "datasets/e3c-de/mappings/e3c-feasibility-30-umls-hpo-v2026-06-23-v1.json"
AUDIT = "datasets/e3c-de/mappings/audit"
HPO_OBO = (".artifacts/objects/sha256/a5/"
           "a5092cbdf605f568403cf7380d9173014015692433b2cc631bc5c1b053876b1b")
LOOKUP_CACHE = ".artifacts/review-workbooks/hpo-lookup.json"
OUT = ".artifacts/review-workbooks"
NCOL = 12  # A..L

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

# Deterministische Querverweis-Ziele je (Fall, Annotation)
mapping = json.load(open(MAPPING_30, encoding="utf-8"))
xref_target = {
    (r["source_case_id"], r["source_annotation_id"]): r["candidates"][0]["hpo_id"]
    for r in mapping["records"]
    if r["classification"] == "unique_active" and r["candidates"]
}


def ableitung(case, aid, hid):
    return "Referenz" if xref_target.get((case, aid)) == hid else "KI (E3C-Stelle)"


bundle = json.load(open(f"{PROBE}/input/teil-a-faelle.json", encoding="utf-8"))
relevance = {(c["case_id"], t["annotation_id"]): t["relevance"]
             for c in bundle["cases"] for t in c["consensus_terms"]}

# --- Zeilen aufbauen: Konsens und Volltext-Luecken --------------------------
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
            rows.append(dict(case=cid, lang=lang,
                             abl=ableitung(cid, t["annotation_id"], t["hpo_id"]),
                             eins="2/2 bestätigt", hid=t["hpo_id"],
                             label=t["hpo_label"], quote=t["quote_de"] or "",
                             note=note, aid=t["annotation_id"]))
        for gap_index, g in enumerate(c["gaps"]):
            s = g.get("suggested_hpo") or {}
            hid, hlabel = s.get("id") or "", s.get("label") or ""
            # Halluzinations-Gate gegen gepinnte HPO
            if hid and hid in terms_db and not terms_db[hid]["obsolete"]:
                eins = "ID verifiziert"
                if (terms_db[hid]["name"].lower() != hlabel.lower()
                        and labels_db.get(hlabel.lower()) != hid):
                    hlabel = f"{hlabel} [HPO-Label: {terms_db[hid]['name']}]"
            elif hid:
                eins, hid = "ohne Vorschlag", ""  # unbekannte ID verworfen
            elif hlabel and labels_db.get(hlabel.lower()):
                hid = labels_db[hlabel.lower()]
                eins = "ID verifiziert"
                hlabel = terms_db[hid]["name"]
            else:
                eins = "ohne Vorschlag"
            if hid and hid in seen:
                continue
            rows.append(dict(case=cid, lang=lang, abl="KI (Volltext)", eins=eins,
                             hid=hid, label=hlabel or g["description_de"],
                             quote=g["quote_de"] or "", note=g["description_de"],
                             gapi=gap_index))

# --- Audit-Daten: einzeln bestaetigte und nicht ueberfuehrbare Stellen ------
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
REL_TXT = {
    "uncertain_patient_phenotype": " Befund laut KI unsicher.",
    "not_positive_patient_phenotype": " Befund laut KI nicht positiv.",
    "historical_or_resolved_patient_phenotype":
        " Befund laut KI historisch/ausgeheilt.",
    "non_index_subject": " Befund laut KI nicht der Indexpatient.",
    "generic_not_patient_assertion": " Laut KI generische Aussage.",
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
    cid, aid = ra["case_id"], ra["annotation_id"]
    lang = lang_of.get(cid, cid[:2].lower())
    ta, tb = _target(ra), _target(rb)
    safe_a, safe_b = ra["audit_class"] in SAFE, rb["audit_class"] in SAFE

    if safe_a and safe_b and ta == tb:
        continue  # Konsens: bereits enthalten

    if safe_a or safe_b:
        # Nur ein Pruefdurchgang sicher (oder beide sicher, aber verschieden)
        for rec, tgt, other, other_tgt in ((ra, ta, rb, tb), (rb, tb, ra, ta)):
            if not (rec["audit_class"] in SAFE and tgt):
                continue
            if rec["relevance"] != "positive_patient_phenotype":
                continue
            hid = tgt[0]
            if hid not in terms_db or terms_db[hid]["obsolete"]:
                continue  # Halluzinations-Gate
            if hid in seen_by_case[cid]:
                continue
            seen_by_case[cid].add(hid)
            if other["audit_class"] in SAFE and other_tgt and other_tgt != tgt:
                anders = f"andere Prüfung wählte {other_tgt[0]} ({other_tgt[1]})"
            else:
                anders = ("andere Prüfung: "
                          f"{KLASSE.get(other['audit_class'], other['audit_class'])}")
            rows.append(dict(case=cid, lang=lang,
                             abl=ableitung(cid, aid, hid), eins="1/2 bestätigt",
                             hid=hid, label=terms_db[hid]["name"], quote="",
                             note=f"Quellspan: '{rec['span']}'; {anders}.",
                             aid=aid))
        continue

    # Keine Pruefung sicher: E3C-Stelle ohne sichere HPO-Entsprechung
    cls_a = ra["audit_class"]
    if cls_a == "direct_context_mismatch":
        abl, eins = "Referenz", "Widerspruch zum Kontext"
    elif cls_a == "ambiguous_direct":
        abl, eins = "Referenz", "mehrdeutig"
    elif cls_a == "semantic_candidate_broader_or_narrower":
        abl, eins = "KI (E3C-Stelle)", "nur ähnlicher Term"
    elif cls_a == "no_hpo_but_relevant":
        abl, eins = "-", "kein Term gefunden"
    elif cls_a == "invalid_or_unrecoverable":
        abl, eins = "-", "Quellcode ungültig"
    else:  # not_hpo_relevant
        abl, eins = "-", "kein Phänotyp"
    hid = hlabel = ""
    cand = _target(ra)
    if cand and abl != "-":
        cand_id = cand[0]
        if cand_id in terms_db and not terms_db[cand_id]["obsolete"]:
            hid, hlabel = cand_id, terms_db[cand_id]["name"]
    note = KLASSE.get(cls_a, cls_a)
    if rb["audit_class"] != cls_a:
        note += f"; andere Prüfung: {KLASSE.get(rb['audit_class'], rb['audit_class'])}"
    note += REL_TXT.get(ra["relevance"], "")
    rows.append(dict(case=cid, lang=lang, abl=abl, eins=eins, hid=hid,
                     label=hlabel, quote="", note=note, aid=aid))

if LANG_FILTER:
    rows = [r for r in rows if r["lang"] == LANG_FILTER]

_ABL_RANK = {"Referenz": 0, "KI (E3C-Stelle)": 1, "-": 2,
             "KI (Volltext)": 3, "Ärztlich": 4}
_EINS_RANK = {"2/2 bestätigt": 0, "1/2 bestätigt": 1, "ID verifiziert": 0,
              "Widerspruch zum Kontext": 2, "mehrdeutig": 3,
              "nur ähnlicher Term": 4, "kein Term gefunden": 5,
              "Quellcode ungültig": 6, "kein Phänotyp": 7, "ohne Vorschlag": 8}
rows.sort(key=lambda r: (r["case"], _ABL_RANK.get(r["abl"], 9),
                         _EINS_RANK.get(r["eins"], 9), r["hid"]))
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
COLS = ["Nr", "Fall", "Sprache", "Ableitung", "Einschätzung", "HPO-ID",
        "HPO-Label", f"Zitat ({ZITAT_SPRACHE})", "Hinweis", "Entscheidung",
        "Korrektur (HPO-ID oder Name)", "Notiz"]
WIDTHS = (5, 10, 8, 14, 20, 12, 28, 38, 34, 13, 22, 22)
CHARS_PER_LINE = 150  # gesamte Blattbreite (A..L verbunden)

info = [
    ("h", f"ANLEITUNG - Prüfung der Symptom-Zuordnungen ({len(case_order)} Fallberichte)"),
    ("p", ""),
    ("h", "WAS IST DAS?"),
    ("p", ("Fallberichte aus dem E3C-Korpus im englischen Original." if SOURCE_MODE
           else "Fallberichte aus dem E3C-Korpus, maschinell ins Deutsche übersetzt.")),
    ("p", "Jede Zeile im Blatt 'Review' ist ein maschinell erzeugter VORSCHLAG für"),
    ("p", "einen HPO-Begriff - erst Ihre Entscheidung macht daraus verlässliche Daten."),
    ("p", ""),
    ("h", "AUFBAU JE FALL"),
    ("p", "1. Blauer Balken = neuer Fall"),
    ("p", "2. Vollständiger Text; Fundstellen fett/rot, dahinter [Nr] = Zeilen-Nr."),
    ("p", "3. Tabelle mit den Vorschlägen dieses Falls"),
    ("p", "4. Gelbe Zeilen = Platz für eigene Ergänzungen"),
    ("p", ""),
    ("h", "WOHER KOMMT DER HPO-BEGRIFF? (Spalte 'Ableitung')"),
    ("p", "Die E3C-Ersteller hatten medizinische Begriffe in den Texten mit"),
    ("p", "UMLS-Codes versehen. Daraus entstehen die Vorschläge auf zwei Wegen:"),
    ("t", "Referenz", "deterministisch: der UMLS-Code der Stelle führt über den offiziellen Querverweis direkt zu diesem HPO-Begriff. Keine KI an der Begriffswahl beteiligt."),
    ("t", "KI (E3C-Stelle)", "für eine E3C-Stelle ohne (eindeutigen) Querverweis hat die KI einen Begriff vorgeschlagen"),
    ("t", "KI (Volltext)", "die KI-Durchsicht des ganzen Textes fand das Symptom zusätzlich - die Stelle war im Korpus gar nicht erfasst"),
    ("t", "-", "E3C-Stelle, für die kein brauchbarer Begriff vorliegt (Details in 'Einschätzung')"),
    ("t", "Ärztlich", "Ihre eigenen Ergänzungen (gelbe Zeilen)"),
    ("p", ""),
    ("h", "WIE SICHER IST ER? (Spalte 'Einschätzung')"),
    ("p", "Zwei unabhängige KI-Prüfungen haben jede E3C-Stelle im Satzzusammenhang"),
    ("p", "beurteilt (passt der Begriff? verneint? historisch? andere Person?):"),
    ("t", "2/2 bestätigt", "beide Prüfungen: passt im Kontext - zuverlässigste Gruppe"),
    ("t", "1/2 bestätigt", "nur eine Prüfung sicher; die Sicht der anderen steht im 'Hinweis'"),
    ("t", "Widerspruch zum Kontext", "der Querverweis existiert, aber der Begriff passt nicht zur Bedeutung im Satz (z. B. 'swelling' als Tumor, Verweis zeigt auf Ödem)"),
    ("t", "mehrdeutig", "mehrere direkte Querverweis-Ziele möglich"),
    ("t", "nur ähnlicher Term", "HPO hat nur einen breiteren/engeren Begriff; er ist als unsicherer Vorschlag vorbefüllt"),
    ("t", "kein Term gefunden", "relevanter Befund, aber kein passender Begriff in der HPO"),
    ("t", "kein Phänotyp", "laut KI Diagnose/Anatomie/Prozedur, kein Symptom"),
    ("t", "ID verifiziert", "(Volltext-Funde) die vorgeschlagene HPO-ID existiert und ist aktiv"),
    ("t", "ohne Vorschlag", "(Volltext-Funde) Auffälligkeit ohne konkreten Begriff - bitte ergänzen oder verwerfen"),
    ("p", ""),
    ("h", "IHRE ENTSCHEIDUNG (Spalte 'Entscheidung')"),
    ("t", "übernehmen", "Begriff trifft für diesen Patienten zu"),
    ("t", "ändern", "anderer HPO-Begriff passt besser - diesen in 'Korrektur' eintragen; der ursprüngliche Vorschlag bleibt dokumentiert"),
    ("t", "verwerfen", "trifft nicht zu"),
    ("t", "unsicher", "nicht entscheidbar - kurze Begründung in 'Notiz'"),
    ("t", "leer lassen", "erlaubt bei Zeilen ohne Bestätigung (Einschätzung 'Widerspruch…' bis 'kein Phänotyp'): zur Kenntnis genommen"),
    ("p", ""),
    ("h", "FEHLT ETWAS IM TEXT?"),
    ("p", "Symptome, die im Text stehen, aber in keiner Zeile auftauchen: in eine"),
    ("p", "gelbe Zeile eintragen (HPO-ID und/oder Name; Zitat optional - ohne Zitat"),
    ("p", "gilt der Begriff für den ganzen Text). Bei Bedarf weitere Zeilen einfügen."),
    ("p", ""),
    ("h", "WAS SIE HIER NICHT SEHEN"),
    ("p", "- E3C-Stellen, deren Befund verneint, ausgeheilt, unsicher oder auf"),
    ("p", "  Angehörige bezogen ist (kein positiver Patientenbefund)."),
    ("p", "- Die KI-Volltextdurchsicht war bewusst konservativ (nur klare Fälle) -"),
    ("p", "  deshalb sind Ihre eigenen Ergänzungen wichtig."),
    ("p", ""),
    ("h", "REGELN"),
    ("p", "- Es zählt nur, was der Text über den Patienten selbst positiv aussagt."),
    ("p", "- Nur Messwert ohne Wertung (z. B. 'CRP 3,7 mg/dl'): Begriff trotzdem"),
    ("p", "  beurteilen und in 'Notiz' 'nicht verbalisiert' vermerken."),
    ("p", "- Jede vorgeschlagene HPO-ID wurde automatisch gegen die HPO-Version"),
    ("p", "  v2026-06-23 abgeglichen; erfundene IDs sind ausgeschlossen. Ob der"),
    ("p", "  Begriff inhaltlich stimmt, entscheiden allein Sie."),
    ("p", ""),
    ("p", f"Browser-Ansicht mit farbigen Markierungen: {BASENAME}.html"),
    ("p", f"Automatisch erstellt am {date.today()}; Datengrundlage:"),
    ("p", "datasets/e3c-de/annotation-feasibility/"),
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
    f_tkey = wb.add_format({"bold": True, "bg_color": "#F2F2F2",
                            "border": 1, "valign": "top"})
    f_tval = wb.add_format({"border": 1, "valign": "top", "text_wrap": True})

    ws = wb.add_worksheet("Anleitung")
    ws.set_column(0, 0, 26)
    ws.set_column(1, 1, 78)
    for i, entry in enumerate(info):
        if entry[0] == "t":
            _, key, val = entry
            ws.write_string(i, 0, key, f_tkey)
            ws.write_string(i, 1, val, f_tval)
            if len(val) > 78:
                ws.set_row(i, 14 * (len(val) // 78 + 1) + 4)
        elif entry[1]:
            ws.write_string(i, 0, entry[1], f_bold if entry[0] == "h" else None)

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
            vals = [row["nr"], cid, row["lang"], row["abl"], row["eins"],
                    row["hid"], row["label"], row["quote"], row["note"],
                    "", "", ""]
            for c, v in enumerate(vals):
                if isinstance(v, int):
                    ws2.write_number(r, c, v, f_cell)
                elif v:
                    ws2.write_string(r, c, v, f_cell)
                else:
                    ws2.write_blank(r, c, None, f_cell)
            r += 1
        for _ in range(3):
            vals = ["", cid, lang, "Ärztlich"] + [""] * 8
            for c, v in enumerate(vals):
                if v:
                    ws2.write_string(r, c, v, f_add)
                else:
                    ws2.write_blank(r, c, None, f_add)
            r += 1
        r += 1  # Trennzeile

    ws2.data_validation(0, 9, r, 9, {
        "validate": "list",
        "source": ["übernehmen", "ändern", "verwerfen", "unsicher"]})
    wb.close()
    return r


tmp = f"{OUT}/.{BASENAME}.tmp.xlsx"
build_workbook(tmp)
target = f"{OUT}/{BASENAME}.xlsx"
try:
    os.replace(tmp, target)
    saved = os.path.basename(target)
except PermissionError:
    alt = f"{OUT}/{BASENAME}-v2.xlsx"
    os.replace(tmp, alt)
    saved = os.path.basename(alt) + " (Original gesperrt)"


# --- HTML-Lesensicht -------------------------------------------------------
def _kind(r):
    if r["eins"] == "2/2 bestätigt":
        return "kons"
    if r["abl"] == "KI (Volltext)":
        return "gap"
    return "e3c"


def render_case(cid):
    txt = texts[cid]
    out, pos = [], 0
    for s, e, rs in merged_marks(cid):
        out.append(html.escape(txt[pos:s]))
        kinds = {_kind(x) for x in rs}
        cls = kinds.pop() if len(kinds) == 1 else "mixed"
        tip = " | ".join(f"Nr {x['nr']}: {x['hid'] or '?'} {x['label']}" for x in rs)
        sup = ",".join(str(x["nr"]) for x in rs)
        out.append(f'<mark class="{cls}" title="{html.escape(tip)}">'
                   f'{html.escape(txt[s:e])}</mark><sup>{sup}</sup>')
        pos = e
    out.append(html.escape(txt[pos:]))
    body = "".join(out).replace("\n", "<br>\n")
    tbl = "".join(
        f'<tr><td>{r["nr"]}</td>'
        f'<td class="{_kind(r)}">{html.escape(r["abl"])}</td>'
        f'<td>{html.escape(r["eins"])}</td><td>{r["hid"]}</td>'
        f'<td>{html.escape(r["label"])}</td><td>{html.escape(r["note"])}</td>'
        f'<td>{"" if r["start"] is not None else ("ohne Zitat" if not r["quote"] else "Zitat nicht lokalisiert")}</td></tr>'
        for r in by_case[cid])
    return (f'<section id="{cid}"><h2>{cid}</h2><div class="text">{body}</div>'
            f'<table><tr><th>Nr</th><th>Ableitung</th><th>Einschätzung</th>'
            f'<th>HPO-ID</th><th>Label</th><th>Hinweis</th><th></th></tr>{tbl}</table></section>')


nav = " ".join(f'<a href="#{c}">{c}</a>' for c in case_order)
style = """
body{font-family:Georgia,serif;max-width:60rem;margin:2rem auto;padding:0 1rem;line-height:1.65}
header{border:2px solid #b00;padding:.7rem 1rem;background:#fff4f4;font-family:sans-serif}
nav{position:sticky;top:0;background:#fff;padding:.5rem 0;border-bottom:1px solid #ccc;font-family:sans-serif;font-size:.85rem}
nav a{margin-right:.55rem;text-decoration:none}
.text{background:#fafafa;border:1px solid #ddd;padding:1rem 1.3rem;border-radius:6px}
mark.kons{background:#c8e6c9} mark.gap{background:#ffe082} mark.mixed{background:#b3e5fc} mark.e3c{background:#e1bee7}
sup{font-family:sans-serif;font-size:.68em;color:#555}
table{border-collapse:collapse;font-family:sans-serif;font-size:.83rem;margin:1rem 0 2.5rem;width:100%}
td,th{border:1px solid #ccc;padding:.25rem .5rem;text-align:left;vertical-align:top}
td.kons{background:#e8f5e9} td.gap{background:#fff8e1} td.e3c{background:#f3e5f5}
h2{font-family:sans-serif;border-bottom:2px solid #333;padding-bottom:.2rem}
.legend span{padding:0 .5rem;margin-right:.7rem}
"""
page = (f'<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
        f'<title>E3C Annotationsreview - Lesensicht ({len(case_order)} Faelle)</title>'
        f'<style>{style}</style></head><body>'
        f'<header><strong>Maschinell erzeugte Vorschlaege - keine Reviewdaten, '
        f'kein Goldstandard.</strong><br>Lesensicht zur Excel-Datei '
        f'<code>{BASENAME}.xlsx</code>; Entscheidungen bitte dort eintragen '
        f'(gleiche Nr.). Alle vorgeschlagenen HPO-IDs exakt gegen die gepinnte '
        f'HPO v2026-06-23 aufgeloest. Erzeugt am {date.today()}.'
        f'<div class="legend"><span style="background:#c8e6c9">2/2 bestaetigt</span>'
        f'<span style="background:#ffe082">KI-Volltextfund</span>'
        f'<span style="background:#e1bee7">unsichere E3C-Stelle</span>'
        f'<span style="background:#b3e5fc">gemischt</span></div></header>'
        f'<nav>{nav}</nav>{"".join(render_case(c) for c in case_order)}'
        f'</body></html>')
with open(f"{OUT}/{BASENAME}.html", "w", encoding="utf-8",
          newline="\n") as fh:
    fh.write(page)

stats = collections.Counter((r["abl"], r["eins"]) for r in rows)
print("gespeichert:", saved)
print("Zeilen:", len(rows))
for (abl, eins), v in sorted(stats.items()):
    print(f"  {abl:16} | {eins:24} | {v}")
print("nicht lokalisierte Zitate:", unlocated or "keine")
