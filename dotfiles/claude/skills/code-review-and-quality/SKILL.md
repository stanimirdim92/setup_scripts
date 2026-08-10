---
name: code-review-and-quality
description: Conducts multi-axis code review across correctness, readability, architecture, security, and performance. Use before merging any PR or change, after completing a feature or bug fix, or when evaluating code written by yourself, another agent, or a human. Trigger with a PR URL, diff, or file path, on phrases like "review this before I merge", "is this code safe?", or when checking for N+1 queries, injection risks, missing edge cases, error handling gaps, or structural/architectural problems.
argument-hint: "<PR URL, diff, or file path>"
---

# Code Review and Quality

## Overview

Multi-dimensional code review with quality gates. Every change gets reviewed before merge — no exceptions. Review covers five axes: correctness, readability, architecture, security, and performance.

**The approval standard:** Approve a change when it definitely improves overall code health, even if it isn't perfect. Perfect code doesn't exist — the goal is continuous improvement. Don't block a change because it isn't exactly how you would have written it. If it improves the codebase and follows the project's conventions, approve it.

## Usage

```
/code-review <PR URL, diff, or file path>
```

Review the provided code changes. If no file, URL, or diff is provided, ask what to review before proceeding.

## When to Use

- Before merging any PR or change
- After completing a feature implementation
- After any bug fix (review both the fix and the regression test)
- When another agent or model produced code you need to evaluate
- When refactoring existing code

## If Connectors Are Available

- **Source control connected:** pull the PR diff automatically from the URL; check CI status and test results before reviewing.
- **Project tracker connected:** verify the change addresses the linked ticket's stated requirements; link findings back to tickets.
- **Knowledge base connected:** check the change against team coding standards and style guides before applying generic conventions.

If none of these are connected, work standalone from whatever diff, PR URL, or file path was provided — all five axes below still apply.

## The Five-Axis Review

### 1. Correctness

- Does it match the spec or task requirements?
- Are edge cases handled (null, empty, boundary values, overflow)?
- Are error paths handled (not just the happy path)? Is error handling and propagation correct?
- Does it pass all tests? Are the tests actually testing behavior, not implementation details?
- Are there off-by-one errors, race conditions, or state inconsistencies?
- Is type safety maintained, or are gratuitous casts/`any` papering over a real issue?

### 2. Readability & Simplicity

- Are names descriptive and consistent with project conventions? (No `temp`, `data`, `result` without context)
- Is the control flow straightforward (avoid nested ternaries, deep callbacks)?
- Is the code organized logically (related code grouped, clear module/single-responsibility boundaries)?
- Are there any "clever" tricks that should be simplified?
- **Could this be done in fewer lines?** (1000 lines where 100 suffice is a failure)
- **Are abstractions earning their complexity?** (Don't generalize until the third use case)
- Would comments help clarify non-obvious intent? (But don't comment obvious code, and check for missing documentation on genuinely non-obvious logic.)
- Are there dead code artifacts: no-op variables (`_unused`), backwards-compat shims, or `// removed` comments?
- **Is a new conditional bolted onto an unrelated flow?** That's a design smell — push it into its own helper, state, or policy.
- **Do repeated conditionals on the same shape appear?** They signal a missing model or dispatcher. A "temporary" branch is usually permanent debt.

### 3. Architecture

- Does it follow existing patterns or introduce a new one? If new, is it justified?
- Does it maintain clean module boundaries? Are dependencies flowing in the right direction (no circular deps)?
- Is there code duplication that should be shared?
- Is the abstraction level appropriate (not over-engineered, not too coupled)?
- **Does this refactor reduce complexity or just relocate it?** Count the concepts a reader must hold to follow the change. Prefer the restructuring that makes whole branches, modes, or layers disappear over one that re-centralizes the same logic. Prefer deleting an abstraction to polishing it.
- **Is feature-specific logic leaking into a shared or general-purpose module?** Keep logic in its owning layer; reuse the canonical helper instead of a near-duplicate.
- **Are type boundaries explicit?** Question gratuitous `any`/`unknown`/optional/casts and silent fallbacks that paper over an unclear invariant.

### 4. Security

- SQL injection, XSS, CSRF — are queries parameterized, outputs encoded?
- Authentication and authorization flaws — are checks present where needed?
- Secrets or credentials in code, logs, or version control?
- Insecure deserialization, path traversal, SSRF?
- Is user input validated and sanitized at every entry point?
- Is data from external sources (APIs, logs, user content, config files) treated as untrusted and validated at system boundaries before use in logic or rendering?
- Are dependencies from trusted sources with no known vulnerabilities? (`npm audit` or equivalent)

For deeper triage of supply-chain risk and vuln severity, see the `security-and-hardening` skill if available — this skill covers structural review, that one covers security verdicts.

### 5. Performance

- N+1 query patterns?
- Unnecessary memory allocations or large objects created in hot paths?
- Algorithmic complexity (O(n²) or worse in hot paths)?
- Missing database indexes, missing pagination on list endpoints?
- Unbounded loops, unconstrained data fetching, or resource leaks?
- Any synchronous operations that should be async? Unnecessary re-renders in UI components?

For deeper profiling and optimization technique, see the `performance-optimization` skill if available.

## Structural Remedies

When you flag a structural problem, propose the move — not just the problem. Reach for a named restructuring:

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

```
~100 lines changed   → Good. Reviewable in one sitting.
~300 lines changed   → Acceptable if it's a single logical change.
~1000 lines changed  → Too large. Split it.
```

**Watch file size, not just diff size.** Around 1000 *total* lines in a single file is a common inspection signal — a small diff can still push a file past it. When a change materially grows an already-large file, ask whether to extract helpers, subcomponents, or modules *first*.

**Splitting strategies:**

| Strategy | How | When |
|----------|-----|------|
| **Stack** | Submit a small change, start the next based on it | Sequential dependencies |
| **By file group** | Separate changes for groups needing different reviewers | Cross-cutting concerns |
| **Horizontal** | Create shared code/stubs first, then consumers | Layered architecture |
| **Vertical** | Break into smaller full-stack slices of the feature | Feature work |

**Separate refactoring from feature work** — submit them as two changes. Small cleanups (renaming) can ride along at reviewer discretion.

**When large changes are acceptable:** complete file deletions and automated refactoring where the reviewer only needs to verify intent, not every line.

## Change Descriptions

**First line:** short, imperative, standalone ("Delete the FizzBuzz RPC," not "Deleting the FizzBuzz RPC").
**Body:** what's changing and why — context, decisions, tradeoffs not visible in the diff. Link bugs/benchmarks/design docs. Acknowledge shortcomings.
**Anti-patterns:** "Fix bug," "Fix build," "Add patch," "Moving code from A to B," "Phase 1."

## Review Process

1. **Understand the context** — what is this trying to accomplish, what spec/ticket does it implement, what's the expected behavior change? (Pull this from the connected tracker if available.)
2. **Review the tests first** — do they exist, test behavior not implementation, cover edge cases, have descriptive names, and would they catch a regression?
3. **Review the implementation** against all five axes above.
4. **Categorize every finding** by severity (table below).
5. **Verify the verification** — what tests were run, did the build pass, was it tested manually, are there before/after screenshots for UI changes?

### Severity Labels

| Prefix | Meaning | Author Action |
|--------|---------|----------------|
| **Critical:** | Blocks merge | Security vulnerability, data loss, broken functionality |
| *(no prefix)* | Required change | Must address before merge |
| **Consider:** / **Optional:** | Suggestion | Worth considering but not required |
| **Nit:** | Minor, optional | Formatting, style preferences — author may ignore |
| **FYI** | Informational | No action needed — context for future reference |

**Lead with what matters.** Order findings by leverage: correctness and security first, then structural regressions and missed simplifications, then everything else. A few high-conviction comments beat a long list of nits. If there's one structural problem and ten nits, the structural problem *is* the review.

## Output Format

```markdown
## Code Review: [PR/change title or file]

### Summary
[1-2 sentence overview of the change and overall quality]

### Critical Issues
| # | File | Line | Issue | Severity |
|---|------|------|-------|----------|
| 1 | [file] | [line] | [description] | Critical |

### Required Changes
| # | File | Line | Issue |
|---|------|------|-------|
| 1 | [file] | [line] | [description] |

### Suggestions
| # | File | Line | Suggestion | Category | Severity |
|---|------|------|------------|----------|----------|
| 1 | [file] | [line] | [description] | Architecture | Consider |

### What Looks Good
- [Positive observations — don't skip this, it's signal that review happened]

### Dead Code Identified
- [file/symbol — why it's now unused] → confirm before removing

### Verification Story
- Tests run: [...]
- Build: [pass/fail]
- Manual verification: [...]

### Verdict
**Approve** / **Request Changes** / **Needs Discussion**
```

## Dead Code Hygiene

After any refactoring or implementation change, check for orphaned code. List it explicitly, then **ask before deleting** — don't silently remove things you're not sure about.

```
DEAD CODE IDENTIFIED:
- formatLegacyDate() in src/utils/date.ts — replaced by formatDate()
- OldTaskCard component in src/components/ — replaced by TaskCard
→ Safe to remove these?
```

## Dependency Discipline

**Before adding any dependency:**
1. Does the existing stack solve this? (Often it does.)
2. How large is the dependency? (Bundle impact.)
3. Is it actively maintained? (Last commit, open issues.)
4. Known vulnerabilities? (`npm audit` or equivalent)
5. Is the license compatible with the project?

**Rule:** prefer standard library and existing utilities. Every dependency is a liability.

**Upgrading an existing dependency** is a code change like any other — review with the same discipline, especially bulk "bump deps" PRs:

1. **Read the changelog, not just the version number.** A "patch" can carry a behavioral change; for a major bump, read the migration notes.
2. **One dependency per change.** A bulk bump that breaks the build hides which package did it.
3. **Let the tests decide.** Verified by a green suite before *and* after — if coverage is thin, that gap is the real finding.
4. **Mind the transitive graph.** Review the lockfile diff, not just `package.json`.
5. **Keep the lockfile honest.** Commit it, review its diff, never hand-edit it.

For triaging `npm audit` findings and supply-chain risk, see the `security-and-hardening` skill if available.

## Review Speed

- **Respond within one business day** — maximum, not target.
- Prioritize fast individual responses over quick final approval; multiple quick rounds beat one slow one.
- Large changes: ask the author to split them rather than reviewing one massive changeset.

## Handling Disagreements

1. **Technical facts and data** override opinions and preferences.
2. **Style guides** are the absolute authority on style matters.
3. **Software design** is evaluated on engineering principles, not personal preference.
4. **Codebase consistency** is an acceptable reason to keep something, if it doesn't degrade overall health.

**Don't accept "I'll clean it up later."** Require cleanup before submission unless it's a genuine emergency; otherwise require a self-assigned bug filed against it.

## Honesty in Review

- **Don't rubber-stamp.** "LGTM" without evidence of review helps no one.
- **Don't soften real issues.** Say "this is a bug that will hit production," not "this might be a minor concern."
- **Quantify problems when possible.** "This N+1 will add ~50ms per item" beats "this could be slow."
- **Push back on approaches with clear problems.** Sycophancy is a review failure mode.
- **Accept override gracefully.** If the author has full context and disagrees, defer to their judgment — but comment on the code, not the person.

## Tips for Better Reviews

1. **Provide context up front** — "this is a hot path" or "this handles PII" focuses the review.
2. **Specify concerns** — "focus on security" narrows scope.
3. **Include tests** in what's reviewed — coverage and quality get checked too.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It works, that's good enough" | Unreadable, insecure, or architecturally wrong code creates debt that compounds. |
| "I wrote it, so I know it's correct" | Authors are blind to their own assumptions. |
| "We'll clean it up later" | Later never comes. Require cleanup before merge. |
| "AI-generated code is probably fine" | AI code needs more scrutiny, not less — confident and plausible even when wrong. |
| "The tests pass, so it's good" | Tests don't catch architecture, security, or readability problems. |
| "The refactor makes it cleaner" | Relocating complexity isn't reducing it — look for the version where branches disappear. |
| "It's only a small addition to this file" | Small diffs still push files past a healthy size and bolt branches onto unrelated flows. |
| "It's just a version bump" | A bump is a behavior change you didn't write. Semver doesn't guarantee no breakage. |
| "I'll upgrade everything in one PR to save time" | A bulk bump that breaks the build hides which package did it. |

## Red Flags

- PRs merged without any review, or review that only checks if tests pass
- "LGTM" without evidence of actual review
- Security-sensitive changes without security-focused review
- Large PRs that are "too big to review properly" (split them)
- No regression tests with bug fix PRs
- Review comments without severity labels
- Accepting "I'll fix it later"
- A refactor that moves code around without reducing the number of concepts a reader must hold
- A change that grows an already-large file instead of decomposing it
- New conditionals scattered into unrelated code paths
- A bespoke helper duplicating an existing canonical one, or feature logic placed in a shared module
- A bulk "bump dependencies" PR with no changelog review and no per-package isolation
- A lockfile change that's hand-edited, uncommitted, or merged without reviewing its diff

## Verification

- [ ] All Critical issues resolved
- [ ] All Required changes resolved or explicitly deferred with justification
- [ ] Tests pass, build succeeds
- [ ] Verification story documented (what changed, how it was verified)
- [ ] Dependency upgrades reviewed against changelog, isolated per package, verified by a green suite, lockfile diff reviewed

**Presumptive blockers** — surface and propose the simpler design; escalate to Required only when the change actively makes structure worse:
- A refactor that relocates complexity instead of reducing it
- A change that pushes a file past the size boundary with no decomposition
- Feature logic added to a shared module
- A near-duplicate of an existing canonical helper
- A silent fallback that hides an unclear invariant

## Multi-Model Review Pattern

```
Model A writes the code → Model B reviews for correctness/architecture →
Model A addresses feedback → Human makes the final call
```

Different models have different blind spots — this catches what a single model misses.

## See Also

- `security-and-hardening` skill (if available) — vulnerability triage, supply-chain risk
- `performance-optimization` skill (if available) — profiling and optimization technique
