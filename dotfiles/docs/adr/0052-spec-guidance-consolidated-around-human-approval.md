# Spec guidance consolidated around human approval

**Decision.** Keep the spec skill's Overview and durable approval controls, but
remove duplicated drafting and verification prose.

1. File count alone does not require a spec. Bounded low-risk work with clear
   behavior may skip it even when production code and focused tests occupy a
   few files; ambiguity, risk, or independently planned behavior remains the
   trigger.
2. One **Draft the Spec** section chooses compact, full, or bugfix form and
   states the contracts shared by all three. Templates own their detailed
   shapes.
3. Requirement scenarios own acceptance criteria in every form. The full and
   bugfix templates no longer add a second Success Criteria section.
4. The skill's Verification section is a human gate. The agent runs the
   Approval Check before presentation, but only explicit human approval moves
   the document to `Status: Approved`.

The load-bearing `### Requirement: REQ-### — Title`, standalone `Source:`, and
`#### Scenario: Name` forms remain inline because downstream stages consume
them. Invariant and lifecycle quality gates remain unchanged and conditional.

**Validation.** The linked runtime skill resolved to this checkout. Plugin
validation passed, all 65 hook tests passed, relevant reference paths resolved,
and `git diff --check` passed. A fresh `/spec` canary under the configured
permission mode produced a compact 60-line Draft with the exact requirement,
source, and scenario forms; omitted Success Criteria; used the exact
repository-defined test command; spawned no recon agent; and stopped for human
approval without implementing.

**Rejected — keep both the agent checklist and human checklist.** The former
required `Status: Draft` while the latter required the same spec to be approved,
so the combined checklist could not be true at one point in time.

**Rejected — remove human approval with the duplicated prose.** Shortening the
skill does not change the approval boundary or permit self-approval.

**Deferred — broaden the requirement-quality rubric.** The canary suggested a
possible nearest-excluded-input check, but no new general rule is added without
a clearer contract. Existing scenario-quality gates remain in force.

**Revisit if** compact specs again lose the exact requirement/scenario heading
forms, duplicate acceptance criteria, or treat file count as the reason a spec
is mandatory.
