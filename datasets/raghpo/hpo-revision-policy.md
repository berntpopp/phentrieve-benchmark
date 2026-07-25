# HPO revision policy

CSC and GSC identifiers are audited against the immutable official HPO release
`v2026-06-23` (`hp.obo`, SHA-256
`a5092cbdf605f568403cf7380d9173014015692433b2cc631bc5c1b053876b1b`).

- Active primary identifiers remain unchanged.
- Unambiguous alternate identifiers are canonicalized to their active primary
  identifier.
- Obsolete identifiers are never replaced automatically. `replaced_by` and
  `consider` values are proposals for manual review.
- Ambiguous, unresolved, unknown, and syntactically invalid identifiers enter
  the manual-review queue.
- If an identifier is both an obsolete primary stanza and an alternate ID on
  another term, the obsolete primary status takes precedence. This preserves
  the conservative review policy used by the official HPO file.

The audit is text-free and deterministic. It records ontology identity,
source annotation identity, status, canonical ID where automatic
canonicalization is permitted, proposed replacements, and reason codes. It
does not claim clinical or physician approval.

## Interpretation of annotation quality

CSC and GSC contain manually selected, case-level HPO terms and are therefore
more specific for HPO evaluation than an automatic conversion of E3C's UMLS
annotations. The revision audit confirms identifier validity, not whether an
annotation is supported by a particular phrase in its clinical note.

The source workbook supplies no text offsets. Consequently, an annotation
cannot be linked automatically to an exact evidence span or checked locally
for negation, uncertainty, or subject context. CSC/GSC are treated as
case-level HPO gold annotations, not as a complete span-based gold standard.
This limitation is complementary to E3C: E3C supplies source spans, but its
UMLS concepts can be substantially less specific than the accompanying text.
