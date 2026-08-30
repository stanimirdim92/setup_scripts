---
name: code-review-and-quality
description: Conducts multi-axis code review across correctness, readability, architecture, security, and performance. Use before merging any PR or change, after completing a feature or bug fix, or when evaluating code written by yourself, another agent, or a human. Trigger with a PR URL, diff, or file path, on phrases like "review this before I merge", "is this code safe?", or when checking for N+1 queries, injection risks, missing edge cases, error handling gaps, or structural/architectural problems.
argument-hint: "<PR URL, diff, or file path>"
---

# Code Review and Quality

## Overview

Multi-dimensional code review with quality gates. Every change gets reviewed before merge — no exceptions. Review covers five axes: correctness, readability, architecture, security, and performance.

**The approval standard:** Approve a change when it definitely improves overall code health, even if it isn't perfect. Perfect code doesn't exist — the goal is continuous improvement. Don't block a change because it isn't exactly how you would have written it. If it improves the codebase and follows the project's conventions, approve it.

**The finding standard:** Finding and filtering are separate steps. At the finding stage, record every issue you discover, including ones you are uncertain about or consider low-severity — do not pre-filter for importance or confidence. It is better to surface a finding that gets labeled Suggestion (or declined by the author) than to silently drop a real bug. The only things you may omit entirely are pure style or naming preferences already enforced by a formatter or explicitly covered by the style guide. Severity labels, confidence, and ordering — not omission — are how the review stays readable.

## Usage

Invoke `code-review-and-quality` with a PR URL, diff, or file path. If none is
provided, ask what to review before proceeding.

## When to Use

- Before merging any PR or change
- After completing a feature implementation
- When another agent or model produced code you need to evaluate
- When refactoring existing code
- After any bug fix (review both the fix and the regression test)

## If Connectors Are Available

- **Source control connected:** pull the PR diff automatically from the URL; check CI status and test results before reviewing.
- **Project tracker connected:** verify the change addresses the linked ticket's stated requirements; link findings back to tickets.
- **Knowledge base connected:** check the change against team coding standards and style guides before applying generic conventions.

If none of these are connected, work standalone from whatever diff, PR URL, or file path was provided — all five axes below still apply.

## The Five-Axis Review

Every review evaluates code across these dimensions:

### 1. Correctness

Does the code do what it claims to do?

- Does it match the spec or task requirements?
- Are edge cases handled (null, empty, boundary values, overflow)?
- Are error paths handled (not just the happy path)? Is error handling and propagation correct?
- Does it pass all tests? Are the tests actually testing behavior, not implementation details?
- Are there off-by-one errors, race conditions, or state inconsistencies?
- Is type safety maintained, or are gratuitous casts/`any` papering over a real issue?

### 2. Readability & Simplicity

Can another engineer (or agent) understand this code without the author explaining it?

- Are names descriptive and consistent with project conventions? (No `temp`, `data`, `result` without context)
- Is the control flow straightforward (avoid nested ternaries, deep callbacks)?
- Is the code organized logically (related code grouped, clear module/single-responsibility boundaries)?
- Are there any "clever" tricks that should be simplified?
- **Could this be done in fewer lines?** (1000 lines where 100 suffice is a failure)
- **Are abstractions earning their complexity?** (Don't generalize until the third use case)
- Would comments help clarify non-obvious intent? (But don't comment obvious code, and check for missing documentation on genuinely non-obvious logic.)
- Are there dead code artifacts: no-op variables (`_unused`), backwards-compat shims, or `// removed` comments?
- **Is a new conditional bolted onto an unrelated flow?** That's a design smell, not a nit — push the logic into its own helper, state, or policy instead of tangling an existing path.
- **Do repeated conditionals on the same shape appear?** They signal a missing model or dispatcher. A "temporary" branch is usually permanent debt.

### 3. Architecture

Does the change fit the system's design?

- Does it follow existing patterns or introduce a new one? If new, is it justified?
- Does it maintain clean module boundaries? Are dependencies flowing in the right direction (no circular dependencies)?
- Is there code duplication that should be shared?
- Is the abstraction level appropriate (not over-engineered, not too coupled)?
- **Does this refactor reduce complexity or just relocate it?** Count the concepts a reader must hold to follow the change. If a "cleaner" version leaves that count unchanged, it isn't cleaner — prefer the restructuring that makes whole branches, modes, or layers disappear over one that re-centralizes the same logic. Prefer deleting an abstraction to polishing it.
- **Is feature-specific logic leaking into a shared or general-purpose module?** Keep logic in its owning layer, reuse the existing canonical helper instead of a near-duplicate, and don't normalize architectural drift.
- **Are type boundaries explicit?** Question gratuitous `any`/`unknown`/optional/casts and silent fallbacks that paper over an unclear invariant — making the boundary explicit often makes the surrounding control flow simpler.

### 4. Security

- Injection: are SQL queries parameterized (no string concatenation)? Are outputs encoded to prevent XSS? CSRF protections in place?
- Authentication and authorization: are checks present where needed?
- Secrets: kept out of code, logs, and version control?
- Insecure deserialization, path traversal, SSRF?
- Is user input validated and sanitized?
- Is data from external sources (APIs, logs, user content, config files) treated as untrusted and validated at system boundaries before use in logic or rendering?
- Are dependencies from trusted sources with no known vulnerabilities? (`npm audit` or equivalent)

### 5. Performance

Does the change introduce performance problems?

- Any N+1 query patterns?
- Unnecessary memory allocations or large objects created in hot paths?
- Algorithmic complexity (O(n²) or worse in hot paths)?
- Missing database indexes, missing pagination on list endpoints?
- Unbounded loops, unconstrained data fetching, or resource leaks?
- Any synchronous operations that should be async? Unnecessary re-renders in UI components?

## Structural Remedies

When you flag a structural problem, propose the move — not just the problem. A review that only says "this is complex" leaves the author guessing. Reach for a named restructuring:

- **Replace a chain of conditionals** with a typed model or an explicit dispatcher.
- **Collapse duplicate branches** into a single clearer flow.
- **Separate orchestration from business logic** so each reads on its own.
- **Move feature-specific logic** out of a shared module into the package that owns the concept.
- **Reuse the canonical helper** instead of a bespoke near-duplicate.
- **Make a type boundary explicit** so downstream branching disappears.
- **Delete a pass-through wrapper** that adds indirection without clarifying the API.
- **Extract a helper, or split a large file** into focused modules.

Prefer the remedy that removes moving pieces over one that spreads the same complexity around.

## Change Sizing

Small, focused changes are easier to review, faster to merge, and safer to deploy. Target these sizes:

```
~100 lines changed   → Good. Reviewable in one sitting.
~300 lines changed   → Acceptable if it's a single logical change.
~1000 lines changed  → Too large. Split it.
```

**Watch file size, not just diff size.** A small diff can still push a file past a healthy boundary — around 1000 *total* lines in a single file (distinct from the ~1000 *changed*-lines threshold above) is a common inspection signal, not a hard cap. When a change materially grows an already-large file, ask whether to extract helpers, subcomponents, or modules *first*, before piling more on. Decompose, then add.

**What counts as "one change":** A single self-contained modification that addresses one thing, includes related tests, and keeps the system functional after submission. One part of a feature — not the whole feature.

**Splitting strategies when a change is too large:**

| Strategy | How | When |
|----------|-----|------|
| **Stack** | Submit a small change, start the next one based on it | Sequential dependencies |
| **By file group** | Separate changes for groups needing different reviewers | Cross-cutting concerns |
| **Horizontal** | Create shared code/stubs first, then consumers | Layered architecture |
| **Vertical** | Break into smaller full-stack slices of the feature | Feature work |

(Horizontal here means splitting an oversized *change* for reviewability — it does not override the planning skill's rule against horizontal task slicing.)

**When large changes are acceptable:** Complete file deletions and automated refactoring where the reviewer only needs to verify intent, not every line.

**Separate refactoring from feature work.** A change that refactors existing code and adds new behavior is two changes — submit them separately. Small cleanups (variable renaming) can be included at reviewer discretion.

## Change Descriptions

Every change needs a description that stands alone in version control history.

**First line:** Short, imperative, standalone. "Delete the FizzBuzz RPC" not "Deleting the FizzBuzz RPC." Must be informative enough that someone searching history can understand the change without reading the diff.

**Body:** What is changing and why. Include context, decisions, and reasoning not visible in the code itself. Link to bug numbers, benchmark results, or design docs where relevant. Acknowledge approach shortcomings when they exist.

**Anti-patterns:** "Fix bug," "Fix build," "Add patch," "Moving code from A to B," "Phase 1," "Add convenience functions."

## Review Process

### Step 1: Understand the Context

Before looking at code, understand the intent:

```
- What is this change trying to accomplish?
- What spec or task does it implement?
- What is the expected behavior change?
```

### Step 2: Review the Tests First

Tests reveal intent and coverage:

```
- Do tests exist for the change?
- Do they test behavior (not implementation details)?
- Are edge cases covered?
- Do tests have descriptive names?
- Would the tests catch a regression if the code changed?
```

### Step 3: Review the Implementation

Walk through the code with the five axes in mind, recording every finding as
you go (per the finding standard in the Overview — no pre-filtering):

```
For each file changed:
1. Correctness: Does this code do what the test says it should?
2. Readability: Can I understand this without help?
3. Architecture: Does this fit the system?
4. Security: Any vulnerabilities?
5. Performance: Any bottlenecks?
```

### Step 4: Label Every Finding

Labeling ranks findings; it never deletes them. Every finding recorded in
Step 3 appears in the output with a severity label and a confidence level
(high/medium/low). Label every comment so the author knows what's required vs
optional:

| Label | Meaning | Author Action |
|-------|---------|---------------|
| **Critical** | Blocks merge | Security vulnerability, data loss risk, broken functionality — must fix |
| **Important** | Should fix before merge | Missing test, wrong abstraction, poor error handling |
| **Suggestion** | Optional improvement | Naming, style, optional optimization — author may decline |

Concrete labeling bar: label Critical or Important any finding that could
cause incorrect behavior, a test failure, a security exposure, data loss, or
a misleading result for a future reader; everything else that survives the
finding standard is a Suggestion. Low confidence lowers certainty, not
severity — a low-confidence possible race condition is still Critical, marked
low-confidence, not a Suggestion.

A low-confidence Critical or Important finding is a **suspected** defect, not a
confirmed one: state what evidence would confirm or refute it (the input, the
interleaving, the state) so the resolution step can settle it by investigation.
Downstream, such a finding is resolved either by a fix or by recorded evidence
refuting its failure scenario — never by changing code that investigation shows
to be correct, and never by dropping it.

**Presumptive blockers** — for each of these, always record the finding and
propose the simpler design; label it Suggestion by default, escalating to
Important when the change actively makes structure worse than before:

- a refactor that relocates complexity instead of reducing it;
- a change that pushes a file past the size boundary with no decomposition;
- feature logic added to a shared module;
- a near-duplicate of an existing canonical helper;
- a silent fallback that hides an unclear invariant.

This prevents authors from treating all feedback as mandatory and wasting time on optional suggestions.

Use exactly these three native labels. When the review participates in the SDLC
pipeline, their canonical dispositions are:

| Native label | Pipeline disposition |
|--------------|----------------------|
| Critical | BLOCKER |
| Important | REQUIRED |
| Suggestion | ADVISORY |

A fourth tier has nowhere to land in that mapping, and splitting optional work
across several labels makes the blocking set ambiguous.

### Output Contract

Every finding includes a stable id (`CODE-1`, `CODE-2`, ...), native label,
confidence (high/medium/low), file/location, evidence, and concrete
recommendation. Critical and Important findings must explain the required
correction rather than merely naming a problem.

Report:

- review scope and one-line goal;
- **Recommendation: APPROVE | REQUEST CHANGES**;
- Critical issues;
- Important issues;
- Suggestions;
- specific strengths worth preserving;
- verification story: tests inspected or run, build evidence, manual/runtime
  checks, and anything not verified.

Use **REQUEST CHANGES** while any Critical or Important finding is unresolved;
otherwise use **APPROVE**. This is a code-review recommendation, not a release
verdict.

This skill is the full standalone review method. The `/review` pipeline uses the
compact `code-reviewer` persona instead and maps its findings before `/ship`;
do not automatically invoke both for the same review.

**Lead with what matters — by ordering, never by omission.** Within each
severity section, order findings by leverage: correctness and security first,
then structural regressions and missed simplifications, then everything else.
The severity sections already keep a real issue from being buried under
Suggestions; a structural problem leads its section, and the ten nits still
appear — as Suggestions, after it.

### Step 5: Verify the Verification

Check the author's verification story:

```
- What tests were run?
- Did the build pass?
- Was the change tested manually?
- Are there screenshots for UI changes?
- Is there a before/after comparison?
```

## Multi-Model Review Pattern

Use different models for different review perspectives:

```
Model A writes the code
    │
    ▼
Model B reviews for correctness and architecture
    │
    ▼
Model A addresses the feedback
    │
    ▼
Human makes the final call
```

This catches issues that a single model might miss — different models have different blind spots.

**Example prompt for a review agent:**
```
Review this code change for correctness, security, and adherence to our
project conventions. The spec says [X]. The change should [Y]. Report every
issue you find, including ones you are uncertain about or consider
low-severity — do not filter for importance or confidence; a downstream step
does that. For each finding, include a severity label (Critical, Important,
Suggestion) and a confidence level.
```

## Dead Code Hygiene

After any refactoring or implementation change, check for orphaned code:

1. Identify code that is now unreachable or unused
2. List it explicitly
3. **Ask before deleting:** "Should I remove these now-unused elements: [list]?"

Don't leave dead code lying around — it confuses future readers and agents. But don't silently delete things you're not sure about. When in doubt, ask.

```
DEAD CODE IDENTIFIED:
- formatLegacyDate() in src/utils/date.ts — replaced by formatDate()
- OldTaskCard component in src/components/ — replaced by TaskCard
- LEGACY_API_URL constant in src/config.ts — no remaining references
→ Safe to remove these?
```

## Review Speed

(For human teams; an agent reviewer responds immediately.)

- Slow reviews block entire teams: respond within one business day maximum; ideally shortly after the request unless deep in focused work.
- Prioritize fast individual responses over quick final approval — a typical change should complete multiple rounds in a day.
- Large changes: ask the author to split them rather than reviewing one massive changeset.

## Handling Disagreements

When resolving review disputes, apply this hierarchy:

1. **Technical facts and data** override opinions and preferences
2. **Style guides** are the absolute authority on style matters
3. **Software design** must be evaluated on engineering principles, not personal preference
4. **Codebase consistency** is acceptable if it doesn't degrade overall health

**Don't accept a bare "I'll clean it up later."** Experience shows deferred cleanup rarely happens. Require cleanup before submission unless it's a genuine emergency. The only valid deferral is a filed ticket, self-assigned by the author, linked from the review — that is what "explicitly deferred with justification" means in the Verification checklist.

## Honesty in Review

When reviewing code — whether written by you, another agent, or a human:

- **Don't rubber-stamp.** "LGTM" without evidence of review helps no one.
- **Don't soften real issues.** "This might be a minor concern" when it's a bug that will hit production is dishonest.
- **Quantify problems when possible.** "This N+1 query will add ~50ms per item in the list" is better than "this could be slow."
- **Push back on approaches with clear problems.** Sycophancy is a failure mode in reviews. If the implementation has issues, say so directly and propose alternatives.
- **Accept override gracefully.** If the author has full context and disagrees, defer to their judgment. Comment on code, not people — reframe personal critiques to focus on the code itself.

## Dependency Discipline

Part of code review is dependency review:

**Before adding any dependency:**
1. Does the existing stack solve this? (Often it does.)
2. How large is the dependency? (Check bundle impact.)
3. Is it actively maintained? (Check last commit, open issues.)
4. Does it have known vulnerabilities? (`npm audit`)
5. What's the license? (Must be compatible with the project.)

**Rule:** Prefer standard library and existing utilities over new dependencies. Every dependency is a liability.

**Upgrading an existing dependency** is a code change like any other, and the riskiest upgrades are the ones merged in bulk with a message like "bump deps." Review them with the same discipline:

1. **Read the changelog, not just the version number.** Semver is a promise the maintainer may not have kept — a "patch" can carry a behavioral change. For a major bump, read the migration notes and find what breaks.
2. **One dependency per change.** Upgrade and merge them individually (or in small related groups). When a bulk bump breaks the build, you've lost which package did it; a single-package change makes the cause obvious and the revert clean.
3. **Let the tests decide.** The upgrade is verified by a green suite before *and* after, not by "it installed." If coverage around the dependency's behavior is thin, that gap is the real finding — add a test first.
4. **Mind the transitive graph.** Most installed packages are ones nobody chose directly. Review the lockfile diff, not just `package.json`; a single direct bump can pull in dozens of indirect changes.
5. **Keep the lockfile honest.** Commit it, review its diff, and never hand-edit it. The lockfile is the thing that actually pins what ships.

For triaging `npm|yarn audit` findings and supply-chain risk (typosquatting, compromised maintainers), follow the `security-and-hardening` skill — this section covers the upgrade *workflow*, that one covers the security verdict.

## The Review Checklist

```markdown
## Review: [PR/Change title]

### Context
- [ ] I understand what this change does and why

### Correctness
- [ ] Change matches spec/task requirements
- [ ] Edge cases handled
- [ ] Error paths handled
- [ ] Tests cover the change adequately

### Readability
- [ ] Names are clear and consistent
- [ ] Logic is straightforward
- [ ] No unnecessary complexity

### Architecture
- [ ] Follows existing patterns
- [ ] No unnecessary coupling or dependencies
- [ ] Appropriate abstraction level
- [ ] Refactors reduce complexity rather than relocate it
- [ ] No feature logic in shared modules; file stays within a healthy size

### Security
- [ ] No secrets in code
- [ ] Input validated at boundaries
- [ ] No injection vulnerabilities
- [ ] Auth checks in place
- [ ] External data sources treated as untrusted

### Performance
- [ ] No N+1 patterns
- [ ] No unbounded operations
- [ ] Pagination on list endpoints

### Verification
- [ ] Tests pass
- [ ] Build succeeds
- [ ] Manual verification done (if applicable)

```

When invoked standalone, pair this checklist with the Output Contract's review
recommendation. In the pipeline, `/review` reports review findings and `/ship`
owns the separate GO/NO-GO release verdict.

## See Also

- For detailed security review guidance, see `../../references/security-checklist.md`

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It works, that's good enough" | Working code that's unreadable, insecure, or architecturally wrong creates debt that compounds. |
| "I wrote it, so I know it's correct" | Authors are blind to their own assumptions. Every change benefits from another set of eyes. |
| "We'll clean it up later" | Later never comes. The review is the quality gate — use it. Require a filed, self-assigned ticket or cleanup before merge. |
| "AI-generated code is probably fine" | AI code needs more scrutiny, not less. It's confident and plausible, even when wrong. |
| "The tests pass, so it's good" | Tests are necessary but not sufficient. They don't catch architecture problems, security issues, or readability concerns. |
| "I'm not sure it's a bug, so I won't mention it" | Uncertainty is metadata, not a filter. Report it with low confidence — the label and downstream step decide, not silence. |
| "The refactor makes it cleaner" | Relocating complexity isn't reducing it. If the reader still holds the same number of concepts, the structure didn't improve — look for the version where branches disappear. |
| "It's only a small addition to this file" | Small diffs still push files past a healthy size and bolt branches onto unrelated flows. Judge the resulting structure, not the diff size. |
| "It's just a version bump" | A bump is a behavior change you didn't write. Read the changelog; semver doesn't guarantee no breakage. |
| "I'll upgrade everything in one PR to save time" | A bulk bump that breaks the build hides which package did it. One dependency per change keeps the cause and the revert clean. |

## Red Flags

- PRs merged without any review
- Review that only checks if tests pass (ignoring other axes)
- "LGTM" without evidence of actual review
- Security-sensitive changes without security-focused review
- Large PRs that are "too big to review properly" (split them)
- No regression tests with bug fix PRs
- Review comments without severity labels — makes it unclear what's required vs optional
- Findings silently dropped instead of reported with low confidence
- Accepting "I'll fix it later" with no filed ticket — it never happens
- A refactor that moves code around without reducing the number of concepts a reader must hold
- A change that grows an already-large file instead of decomposing it
- New conditionals scattered into unrelated code paths (a missing abstraction)
- A bespoke helper that duplicates an existing canonical one, or feature logic placed in a shared module
- A bulk "bump dependencies" PR with no changelog review and no per-package isolation
- A lockfile change that's hand-edited, uncommitted, or merged without reviewing its diff

## Verification

After review is complete:

- [ ] Every finding from Step 3 appears in the output with an id, label, and confidence — none were silently dropped
- [ ] All Critical issues are resolved
- [ ] All Important issues are resolved or deferred via a filed, self-assigned, linked ticket
- [ ] Tests pass
- [ ] Build succeeds
- [ ] The verification story is documented (what changed, how it was verified)
- [ ] Dependency upgrades were reviewed against their changelog, isolated per package, and verified by a green suite with the lockfile diff reviewed
