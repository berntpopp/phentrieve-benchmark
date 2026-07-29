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
require bilingual or fachsprachliche review. These texts
must not be used for clinical decisions.

The source is the E3C Corpus at commit
`f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc`. Its upstream README declares
CC BY-NC without identifying a license version. This review snapshot follows
the project's documented working assumption that attributed, non-commercial
scientific review is permitted. Preserve the E3C attribution when sharing or
discussing these materials.

The files preserve the original machine outputs. Corrections, preferences, and
accepted benchmark texts will be recorded separately rather than overwriting
this snapshot.
