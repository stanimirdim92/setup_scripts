# RFC 2119 keywords in requirements

**Context.** A spec requirement is one or two sentences under
`### Requirement: REQ-### — Title`. Its strength was implied by wording:
"must", "should", "can" and "will" appeared with no fixed meaning, so a reader
could not tell an absolute requirement from a preference, and `/ship`, which
blocks on any requirement without evidence, treated a soft "should" exactly as
a hard "must".

**Decision — uppercase RFC 2119 keywords.** Each requirement statement states
its obligation with an uppercase keyword, read as RFC 2119 with RFC 8174
(only uppercase carries the meaning):
- MUST / MUST NOT — absolute.
- SHOULD / SHOULD NOT — with the exception that allows otherwise, written in
  the requirement. A SHOULD with no named exception is a MUST.
- MAY — latitude the implementation is given.

The spec template and `spec-driven-development` carry the rule. Scenarios keep
GIVEN/WHEN/THEN.

**Decision — evidence follows the keyword.** `/ship` requires evidence for each
MUST and MUST NOT clause, and for each SHOULD or SHOULD NOT clause or its named
exception. A MAY clause needs no evidence of its own. A requirement with no
evidence is still NO-GO.

**Rejected.**
- *EARS ("When X, the system shall Y").* It overlaps the GIVEN/WHEN/THEN
  scenarios the spec already has, and every template would need rewriting.
- *Severity words of our own (hard/soft).* RFC 2119 is the form readers of
  specifications already know.
