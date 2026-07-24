def synthetic_hpo_obo() -> bytes:
    return b"""format-version: 1.4
ontology: hp

[Term]
id: HP:0000001
name: Active root
xref: UMLS:C0000001

[Term]
id: HP:0000002
name: Active with alternate
xref: UMLS:C0000002
xref: UMLS:C0000001
xref: SNOMEDCT_US:123
alt_id: HP:1000002
alt_id: HP:0000006

[Term]
id: HP:0000003
name: Obsolete single
xref: UMLS:C0000003
is_obsolete: true
replaced_by: HP:0000002

[Term]
id: HP:0000004
name: Obsolete multiple
is_obsolete: true
replaced_by: HP:0000001
replaced_by: HP:0000002

[Term]
id: HP:0000005
name: Obsolete consider
is_obsolete: true
consider: HP:0000001

[Term]
id: HP:0000006
name: Obsolete unresolved
is_obsolete: true

[Term]
id: HP:0000007
name: Obsolete chain
is_obsolete: true
replaced_by: HP:0000003
"""
