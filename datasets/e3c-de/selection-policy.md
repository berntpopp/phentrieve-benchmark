# E3C feasibility selection policy

Document length is measured locally as `len(canonical_text.split())`.
Strata are short (<200 tokens), medium (200–400), and long (>400). Each
language contributes 3 short, 4 medium, and 3 long reports, for 30 total.

Features comprise token length, total annotation density, densities for the
six semantic entity types, entity-type diversity, and factuality, negation,
and Bodypart markers. Bodypart is only a proxy; it is not true HPO
organ-system coverage. Counts and densities use exact rational arithmetic.
Within each language/stratum, features are min-max scaled, the first case is
farthest from the centroid, and subsequent cases maximize their minimum
squared distance to the selected set.

The algorithm is `e3c-diversity-maximin/v1`; the deterministic tie seed is
`phentrieve-e3c-de-feasibility-30-v1`. Ties use the SHA-256-derived case order.
The current override list is empty. Future include/exclude overrides must be
explicit, hashed, documented, and must not silently mutate this manifest.

