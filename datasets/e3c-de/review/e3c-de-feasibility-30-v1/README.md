# E3C German translation review snapshot

This directory contains the 30 cases selected by
`e3c-de-feasibility-30-v1`. It makes the source reports and two unreviewed
machine translations directly available for non-commercial scientific review.

Each case directory contains:

- `source.<language>.txt`: the canonical E3C source report;
- `nmt.de.txt`: the German Google `general/nmt` output;
- `tllm.de.txt`: the German Google `general/translation-llm` output.

The general translation filename is `<variant>.de.txt`, so later variants can
be added without changing the case-oriented layout.

All translations are unreviewed machine translations. Automatic checks do
not establish clinical correctness: each current variant has 25 records marked
`ready_for_review` and 5 marked `automatic_check_failed`. Both statuses still
require bilingual or clinical subject-matter review.
These texts must not be used for clinical decisions.

Attribution: E3C Corpus, hltfbk/E3C-Corpus, commit
f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc, CC BY-NC (version unspecified).
The [pinned upstream README](https://github.com/hltfbk/E3C-Corpus/blob/f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc/README.md)
declares CC BY-NC without identifying a license version; the repository's
[license evidence](../../license-evidence.yaml) records the redistribution
decision. This review snapshot follows the project's documented working
assumption that attributed, non-commercial scientific review is permitted.
Preserve the E3C attribution when sharing or discussing these materials.

The files preserve the original machine outputs. Corrections, preferences, and
accepted benchmark texts will be recorded separately rather than overwriting
this snapshot.

<!-- BEGIN E3C REPORT ATTRIBUTION -->
## Original-report attribution and adaptation notice

Every German `*.de.txt` file is an unreviewed machine-translated adaptation of
the corresponding original report. This applies to both current variants,
`nmt.de.txt` and `tllm.de.txt`; neither includes human corrections. The
supplied original-report attribution and license metadata is retained verbatim
below. Generic `CC BY` and `CC-BY` values are not assigned an inferred version.

| Case ID | Supplied `docAuthor` | Supplied `docDOI` | Supplied `docUrl` | Supplied `docLicense` |
|---|---|---|---|---|
| `EN100075` | David Lagoro Kitara;  Amos Deogratius Mwaka;  Henry R Wabinga;  Paul Okot Bwangamoi | 10.11604/pamj.2013.16.65.2403 | https://www.panafrican-med-journal.com/content/article/16/65/full/ | `CC BY 4.0` |
| `EN100114` | Sonia Hammami;  Fethia Bdioui;  Afef Ouaz;  Hichem Loghmari;  Sylvia Mahjoub;  Hamouda Saffar | 10.11604/pamj.2014.18.165.2080 | https://www.panafrican-med-journal.com/content/article/18/165/full/ | `CC BY 4.0` |
| `EN100310` | Mouna Ayadi;  Azza Gabsi;  Khdija Meddeb;  Amina Mokrani;  Yosra Yahiaoui;  Feryel Letaief;  Nesrine Chraiet;  Henda Rais;  Amel Mezlini | 10.11604/pamj.2017.26.113.11472 | https://www.panafrican-med-journal.com/content/article/26/113/full/ | `CC BY 4.0` |
| `EN100593` | Bruce Shinga Wembulua;  Kalilou Diallo;  Mame Aïsse Thioubou;  Jean Didier Bosenge Nguma;  Noel Magloire Manga | 10.11604/pamj.2020.36.298.22658 | https://www.panafrican-med-journal.com/content/article/36/298/full/ | `CC BY 4.0` |
| `EN100600` | Soukayna Bahbah;  Karima El Harti ;  Wafaa El Wady | 10.11604/pamj.2020.36.342.21919 | https://www.panafrican-med-journal.com/content/article/36/342/full/ | `CC BY 4.0` |
| `EN100668` | Hasan Yüksel;  Tolga Atakul;  Emre Zafer;  Özgür Deniz Turan | 10.11604/pamj.2020.37.347.23100 | https://www.panafrican-med-journal.com/content/article/37/347/full/ | `CC BY 4.0` |
| `EN101318` | Margarita E Polyak; Elena V Zaklyazminskaya | 10.1186/s12881-020-01001-5 | https://pubmed.ncbi.nlm.nih.gov/32252658 | `CC BY` |
| `EN105832` | Gitte O Skajaa; Elisabeth R Mathiesen; Elisabeth Iyore; Henning Beck-Nielsen; Espen Jimenez-Solem; Peter Damm | 10.1186/1756-0500-7-804 | https://pubmed.ncbi.nlm.nih.gov/25404386 | `CC BY` |
| `EN107021` | Muhammad Zaman Khan Assir; Ali Jawa; Hafiz Ijaz Ahmed | 10.1186/1471-2334-12-240 | https://pubmed.ncbi.nlm.nih.gov/23033818 | `CC BY` |
| `EN107424` | Inga-Marie Schaefer; Harald Günnel; Stefan Schweyer; Michael Korenkov | 10.1186/1471-2407-11-352 | https://pubmed.ncbi.nlm.nih.gov/21838880 | `CC BY` |
| `ES100050` | Ander Intxaurrondo; Jose Antonio Lopez Martin; Heidy Rodriguez; Aitor Gonzalez-Agirre; Marta Villegas; Montserrat Marimon; Martin Krallinger | http://doi.org/10.5281/zenodo.2560316 | https://github.com/PlanTL-SANIDAD/SPACCC | `CC-BY` |
| `ES100163` | Ander Intxaurrondo; Jose Antonio Lopez Martin; Heidy Rodriguez; Aitor Gonzalez-Agirre; Marta Villegas; Montserrat Marimon; Martin Krallinger | http://doi.org/10.5281/zenodo.2560316 | https://github.com/PlanTL-SANIDAD/SPACCC | `CC-BY` |
| `ES100214` | Ander Intxaurrondo; Jose Antonio Lopez Martin; Heidy Rodriguez; Aitor Gonzalez-Agirre; Marta Villegas; Montserrat Marimon; Martin Krallinger | http://doi.org/10.5281/zenodo.2560316 | https://github.com/PlanTL-SANIDAD/SPACCC | `CC-BY` |
| `ES100417` | Ander Intxaurrondo; Jose Antonio Lopez Martin; Heidy Rodriguez; Aitor Gonzalez-Agirre; Marta Villegas; Montserrat Marimon; Martin Krallinger | http://doi.org/10.5281/zenodo.2560316 | https://github.com/PlanTL-SANIDAD/SPACCC | `CC-BY` |
| `ES100420` | Ander Intxaurrondo; Jose Antonio Lopez Martin; Heidy Rodriguez; Aitor Gonzalez-Agirre; Marta Villegas; Montserrat Marimon; Martin Krallinger | http://doi.org/10.5281/zenodo.2560316 | https://github.com/PlanTL-SANIDAD/SPACCC | `CC-BY` |
| `ES100521` | Ander Intxaurrondo; Jose Antonio Lopez Martin; Heidy Rodriguez; Aitor Gonzalez-Agirre; Marta Villegas; Montserrat Marimon; Martin Krallinger | http://doi.org/10.5281/zenodo.2560316 | https://github.com/PlanTL-SANIDAD/SPACCC | `CC-BY` |
| `ES100778` | Ander Intxaurrondo; Jose Antonio Lopez Martin; Heidy Rodriguez; Aitor Gonzalez-Agirre; Marta Villegas; Montserrat Marimon; Martin Krallinger | http://doi.org/10.5281/zenodo.2560316 | https://github.com/PlanTL-SANIDAD/SPACCC | `CC-BY` |
| `ES100791` | Ander Intxaurrondo; Jose Antonio Lopez Martin; Heidy Rodriguez; Aitor Gonzalez-Agirre; Marta Villegas; Montserrat Marimon; Martin Krallinger | http://doi.org/10.5281/zenodo.2560316 | https://github.com/PlanTL-SANIDAD/SPACCC | `CC-BY` |
| `ES100840` | Ander Intxaurrondo; Jose Antonio Lopez Martin; Heidy Rodriguez; Aitor Gonzalez-Agirre; Marta Villegas; Montserrat Marimon; Martin Krallinger | http://doi.org/10.5281/zenodo.2560316 | https://github.com/PlanTL-SANIDAD/SPACCC | `CC-BY` |
| `ES100937` | Ander Intxaurrondo; Jose Antonio Lopez Martin; Heidy Rodriguez; Aitor Gonzalez-Agirre; Marta Villegas; Montserrat Marimon; Martin Krallinger | http://doi.org/10.5281/zenodo.2560316 | https://github.com/PlanTL-SANIDAD/SPACCC | `CC-BY` |
| `FR100078` | Bouomrani Salem;  Kilani Ichrak;  Nouma Hanène;  Chebbi Safouane;  Béji Maher | 10.11604/pamj.2013.14.139.1785 | https://www.panafrican-med-journal.com/content/article/14/139/full/ | `CC BY 4.0` |
| `FR100185` | Mustapha Maâroufi;  Imane Kamaoui;  Meriem Boubbou;  Nadia Sqalli;  Siham Tizniti | 10.11604/pamj.2014.18.12.1008 | https://www.panafrican-med-journal.com/content/article/18/12/full/ | `CC BY 4.0` |
| `FR100275` | Zena Seka;  Pierre Mols;  Eric Gobin;  William Ngatchou | 10.11604/pamj.2014.19.46.4703 | https://www.panafrican-med-journal.com/content/article/19/46/full/ | `CC BY 4.0` |
| `FR100282` | Marcellin Bugeme;  Olivier Mukuku | 10.11604/pamj.2015.20.104.5958 | https://www.panafrican-med-journal.com/content/article/20/104/full/ | `CC BY 4.0` |
| `FR100344` | Christiane Tshabu Aguemon;  Justin Denakpo;  Benjamin Hounkpatin;  Lehila Bagnan Tossa;  Sosthène Adisso;  Jeanne Sacca;  José de Souza | 10.11604/pamj.2015.20.394.5419 | https://www.panafrican-med-journal.com/content/article/20/394/full/ | `CC BY 4.0` |
| `FR100510` | Abdessalam Achkoun;  Abdeljabbar Messoudi;  Salah Fnini;  Abdelhak Garch | 10.11604/pamj.2016.23.176.8616 | https://www.panafrican-med-journal.com/content/article/23/176/full/ | `CC BY 4.0` |
| `FR100849` | Saad Slaiki;  Mohamed Afdil;  Hicham El Bouhaddouti;  El Bachir Benjelloun;  Abdelmalek Ousadden;  Khalid Ait Taleb;  Ouadii Mouaqit | 10.11604/pamj.2020.36.149.21033 | https://www.panafrican-med-journal.com/content/article/36/149/full/ | `CC BY 4.0` |
| `FR100882` | Komi Ignéza Agbotsou;  Damelan Kombate;  Amégninou Mawuko Yao Adigo;  Kossivi Apétsè;  Albert Beschet;  Victor Chan | 10.11604/pamj.2020.37.218.24313 | https://www.panafrican-med-journal.com/content/article/37/218/full/ | `CC BY 4.0` |
| `FR100925` | Khaoula El Montacer; Wafaa Hliwa; Fz El Rhaoussi; Mohammed Tahiri; Fouad Haddad; Ahmed Bellabah; Wafaa Badre | 10.11604/pamj.2020.37.77.20817 | https://pubmed.ncbi.nlm.nih.gov/33244340 | `CC BY` |
| `FR100971` | Tahir Nebhani; Said Jidane; Hicham Bakkali; Lahcen Belyamani | 10.11604/pamj.2017.28.242.12970 | https://pubmed.ncbi.nlm.nih.gov/29881487 | `CC BY` |
<!-- END E3C REPORT ATTRIBUTION -->
