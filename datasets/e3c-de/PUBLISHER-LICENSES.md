# E3C publisher license check

The license each original report is published under, checked on 2026-10-06
against the publisher or archive copy, next to the `docLicense` value the
E3C corpus supplies (retained verbatim in [`ATTRIBUTION.md`](ATTRIBUTION.md)).

Evidence per source:

- Spanish reports come from the SPACCC corpus, released under CC BY 4.0
  (Zenodo record 10.5281/zenodo.2560316 and the SPACCC repository README).
- The Pan African Medical Journal reports: the license line of the article
  page at the supplied `docUrl`. Several PubMed Central copies of these
  articles state CC BY 2.0; the publisher page states CC BY 4.0.
- Reports linked through PubMed: the `<license>` element of the PubMed
  Central full text, retrieved through the Europe PMC REST API. Where that
  element names the Creative Commons Attribution License without a version
  or link, the version is recorded as not stated.

Findings: apart from versions the supplied value leaves unstated, the
supplied `docLicense` names the same license terms as the publisher for all
reports except five Journal of Orthopaedic Case Reports articles. E3C
supplies `CC BY-NC` for them; the articles are published under
CC BY-NC-SA 3.0 (ShareAlike). See [`LICENSES.md`](LICENSES.md).

| Case ID | Language | Supplied `docLicense` | Publisher license | Evidence |
|---|---|---|---|---|
| `EN100017` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100022` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100024` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100029` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100046` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100067` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100068` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100075` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100090` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100114` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100123` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100129` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100156` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100184` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100247` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100265` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100275` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100310` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100315` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100339` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100340` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100345` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100372` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100376` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100383` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100385` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100399` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100415` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100427` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100432` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100437` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100453` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100466` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100490` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100497` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100506` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100508` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100543` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100593` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100600` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100605` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100606` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100645` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100653` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100655` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100658` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100668` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100682` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100700` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN100705` | en | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `EN101114` | en | `CC BY` | CC BY 4.0 | PMC full text, PMC7275106 |
| `EN101318` | en | `CC BY` | CC BY 4.0 | PMC full text, PMC7137186 |
| `EN101783` | en | `CC BY` | CC BY 4.0 | PMC full text, PMC6815534 |
| `EN102305` | en | `CC BY-NC` | CC BY-NC-SA 3.0 | PMC full text, PMC6588156 |
| `EN103007` | en | `CC BY-NC` | CC BY-NC 4.0 | PMC full text, PMC6288500 |
| `EN103220` | en | `CC BY` | CC BY 4.0 | PMC full text, PMC6127913 |
| `EN103266` | en | `CC BY` | CC BY (no version stated) | PMC full text, PMC6091283 |
| `EN103442` | en | `CC BY` | CC BY 4.0 | PMC full text, PMC5984322 |
| `EN103589` | en | `CC BY-NC` | CC BY-NC 4.0 | PMC full text, PMC5874381 |
| `EN104179` | en | `CC BY-NC` | CC BY-NC-SA 3.0 | PMC full text, PMC5458686 |
| `EN104184` | en | `CC BY-NC` | CC BY-NC-SA 3.0 | PMC full text, PMC5458705 |
| `EN104263` | en | `CC BY-NC` | CC BY-NC-SA 3.0 | PMC full text, PMC5404161 |
| `EN104655` | en | `CC BY` | CC BY 4.0 | PMC full text, PMC5011863 |
| `EN104891` | en | `CC BY` | CC BY 4.0 | PMC full text, PMC4888307 |
| `EN105023` | en | `CC BY` | CC BY 4.0 | PMC full text, PMC4778297 |
| `EN105094` | en | `CC BY` | CC BY 4.0 | PMC full text, PMC4722727 |
| `EN105114` | en | `CC BY` | CC BY 4.0 | PMC full text, PMC4706661 |
| `EN105223` | en | `CC BY` | CC BY 4.0 | PMC full text, PMC4638088 |
| `EN105551` | en | `CC BY` | CC BY 4.0 | PMC full text, PMC4375850 |
| `EN105832` | en | `CC BY` | CC BY 4.0 | PMC full text, PMC4242601 |
| `EN106156` | en | `CC BY` | CC BY 2.0 | PMC full text, PMC4045944 |
| `EN106233` | en | `CC BY-NC` | CC BY-NC-SA 3.0 | PMC full text, PMC4719383 |
| `EN106489` | en | `CC BY` | CC BY 2.0 | PMC full text, PMC3835449 |
| `EN106841` | en | `CC BY` | CC BY 2.0 | PMC full text, PMC3570274 |
| `EN107021` | en | `CC BY` | CC BY 2.0 | PMC full text, PMC3482561 |
| `EN107405` | en | `CC BY` | CC BY 2.0 | PMC full text, PMC3180413 |
| `EN107423` | en | `CC BY` | CC BY 2.0 | PMC full text, PMC3174127 |
| `EN107424` | en | `CC BY` | CC BY 2.0 | PMC full text, PMC3171385 |
| `EN107465` | en | `CC BY` | CC BY 2.0 | PMC full text, PMC3141726 |
| `EN107559` | en | `CC BY` | CC BY 2.0 | PMC full text, PMC3108944 |
| `EN108055` | en | `CC BY` | CC BY 3.0 | PMC full text, PMC2827076 |
| `EN108139` | en | `CC BY` | CC BY 2.0 | PMC full text, PMC2806858 |
| `EN108254` | en | `CC BY` | CC BY 2.0 | PMC full text, PMC2804010 |
| `EN108798` | en | `CC BY` | CC BY 2.0 | PMC full text, PMC2636813 |
| `ES100001` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100002` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100030` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100042` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100050` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100051` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100063` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100064` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100079` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100091` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100098` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100112` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100143` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100163` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100177` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100178` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100182` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100214` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100259` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100273` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100278` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100280` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100284` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100304` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100310` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100320` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100363` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100410` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100412` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100417` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100420` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100423` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100445` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100447` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100513` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100519` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100521` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100526` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100552` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100561` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100569` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100571` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100578` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100587` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100594` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100605` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100631` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100633` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100634` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100642` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100650` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100659` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100663` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100686` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100688` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100705` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100713` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100715` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100727` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100736` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100737` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100760` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100775` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100778` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100789` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100791` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100797` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100803` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100809` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100819` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100832` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100840` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100848` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100896` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100924` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100937` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100946` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100947` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100962` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100978` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `ES100994` | es | `CC-BY` | CC BY 4.0 | SPACCC record, Zenodo 10.5281/zenodo.2560316 |
| `FR100003` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100078` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100092` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100120` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100130` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100132` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100142` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100161` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100168` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100185` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100227` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100255` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100275` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100276` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100282` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100283` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100296` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100314` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100344` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100346` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100360` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100361` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100371` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100400` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100439` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100448` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100453` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100480` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100510` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100515` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100517` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100519` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100579` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100589` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100597` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100603` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100611` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100614` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100620` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100623` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100629` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100632` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100658` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100663` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100666` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100683` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100688` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100689` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100697` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100708` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100717` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100748` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100766` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100780` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100806` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100814` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100826` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100845` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100849` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100870` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100874` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100882` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100883` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100894` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100903` | fr | `CC BY 4.0` | CC BY 4.0 | publisher article page |
| `FR100919` | fr | `CC BY` | CC BY 4.0 | PMC full text, PMC7864276 |
| `FR100921` | fr | `CC BY` | CC BY 4.0 | PMC full text, PMC7847211 |
| `FR100925` | fr | `CC BY` | CC BY 4.0 | PMC full text, PMC7680232 |
| `FR100930` | fr | `CC BY` | CC BY (no version stated) | PMC full text, PMC7170739 |
| `FR100932` | fr | `CC BY` | CC BY 2.0 | PMC full text, PMC7060905 |
| `FR100944` | fr | `CC BY` | CC BY (no version stated) | PMC full text, PMC6620063 |
| `FR100946` | fr | `CC BY` | CC BY 2.0 | PMC full text, PMC6607260 |
| `FR100959` | fr | `CC BY` | CC BY (no version stated) | PMC full text, PMC6430945 |
| `FR100960` | fr | `CC BY` | CC BY 2.0 | PMC full text, PMC6295300 |
| `FR100971` | fr | `CC BY` | CC BY (no version stated) | PMC full text, PMC5989195 |
| `FR100979` | fr | `CC BY` | CC BY (no version stated) | PMC full text, PMC5660323 |
| `FR100986` | fr | `CC BY` | CC BY (no version stated) | PMC full text, PMC5554668 |
| `FR100994` | fr | `CC BY` | CC BY 2.0 | PMC full text, PMC5398856 |
| `FR100996` | fr | `CC BY` | CC BY 2.0 | PMC full text, PMC5337274 |
| `FR100998` | fr | `CC BY` | CC BY (no version stated) | PMC full text, PMC5267844 |
| `FR101000` | fr | `CC BY` | CC BY (no version stated) | PMC full text, PMC5072859 |
