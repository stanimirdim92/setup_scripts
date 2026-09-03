# Spec pin made durable; hook bypasses closed and put under test

**Decision.** A second external scan found two high-severity defects in work
this repo shipped over the previous three entries. Both are cases of a check
that was verified working rather than verified *correct*, which is the failure
[0048](0048-repository-precedent-placement-corrected.md) named and did not
cure.

## 1. The spec pin was not durable

[0046](0046-plan-technical-approach-spec-pinning-and-plan-gates.md) had `/plan`
pin the spec with `git hash-object -w` and `/build` retrieve it with
`git cat-file blob`. That entry claims "verified both ends before adopting."
What was verified is that the two commands work in sequence, immediately, on
one machine. What was never verified is that the object survives:

```
$ git hash-object -w spec.md   # 7c1ab2f…
$ git cat-file blob 7c1ab2f…   # retrievable
$ git prune --expire=now
$ git cat-file blob 7c1ab2f…   # gone
```

The blob has no ref pointing at it. `git gc` and `git prune` delete it, and it
is never transferred by push or clone — so the pin was unverifiable on any
second machine and could become unverifiable on the first. A gate that silently
stops working is worse than no gate, because the plan still carries a line that
looks like a guarantee.

**Now:** the spec must be committed with no uncommitted edits, and the plan
records `Spec revision: git-commit:<sha>:<path>` from
`git log -1 --format=%H -- <path>`. `/build` retrieves it with `git show`.
Requiring the commit adds no obligation the harness didn't already have —
`spec-driven-development` has always said the spec belongs in version control.
Where a sha no longer resolves, because the commit was rebased or squashed
away, the plan is `Needs replan` rather than assumed current.

## 2. Both git-safety hooks were still bypassable

[0044](0044-config-security-hardening-pass.md) made the hooks alias-aware and
stopped there. Aliases were one normalisation gap of several. Every one of these
reached the tool untouched:

| Command | Why it slipped through |
|---|---|
| `rm -rf "$HOME"` | quoted target; the matcher required a bare `$HOME` |
| `rm -rf ${HOME}` | brace form |
| `rm -rf ~/` | trailing slash |
| `git -C /tmp reset --hard` | global option between `git` and the subcommand |
| `git --no-pager push --force origin main` | same, for the push hook |
| `git push origin +HEAD:main` | force expressed as a refspec, never as `--force` |
| `git push --mirror origin` | can delete every remote ref absent locally |
| `git push --delete origin main` / `origin :main` | remote branch deletion |
| `git checkout -f` / `git switch -f` / `--discard-changes` | discards the tree without naming a path |

**The fix that matters is not the regexes — it is `tools/test-hooks.sh`**, 65
fixtures asserting `deny` / `ask` / `allow`, including the allow cases
(`rm -rf ./build`, `git switch main`, `git checkout -b`) so a future
over-broad matcher fails too. The hooks are the only primitive in this harness
that is enforcement rather than instruction, and until now nothing tested them.
Two rounds of hand-reasoned regexes each looked complete and each shipped a
bypass; the fixture file is what makes the third round checkable. **Add a
fixture before adding a matcher.**

The Codex `["git", "switch"]` allow rule is also removed: prefix rules cannot
express "but not `-f`", exactly as with `sed` in
[0044](0044-config-security-hardening-pass.md), so it goes rather than narrows.

## 3. `/build` did not re-check the spec's status

It verified the plan's status and the spec's content, but never the spec's own
`Status`. A change from `Approved` to `Needs reapproval` or `Superseded` is a
one-line edit that the editorial/behavioral triage would happily classify as
editorial, re-pin, and dispatch against. `/build` now requires the spec header
to still read `Approved`, and **a `Status` line change is never editorial** —
it is the spec saying the plan's foundation moved.

## 4. Requirement traceability contradicted itself

[0045](0045-spec-approval-state-change-impact-and-requirement-traceability.md)
and [0046](0046-plan-technical-approach-spec-pinning-and-plan-gates.md) shipped
three incompatible versions of one rule: `/plan` demanded a `REQ-###` on every
task, the plan gates allowed `TD-###`-only spikes and named delivery concerns,
and the traceability contract said `/build` carries the ids while its executor
packet omitted them entirely. Unified:

- a **delivery task** names at least one `REQ-###`;
- a **spike** names the `TD-###` it resolves *and* the requirements it unblocks
  — a spike with no downstream requirement is investigation for its own sake;
- a **withdrawn requirement** stays in the coverage table marked withdrawn,
  because deleting the row makes a dropped requirement look like one that was
  never specified;
- every **executor packet** carries `requirements: [REQ-###, ...]`, so the
  contract has a producer at the stage that was supposed to honour it.

## Minor corrections

- `claude mcp remove <name>` gains `--scope user` in both places it is
  suggested; the script only ever installs at user scope.
- `README.md` overstated the Context7 placeholder: with `CONTEXT7_API_KEY`
  unset the server is added with no auth header, and a later rerun skips it as
  already configured. Now stated.
- `spec-quality-gates.md` said "four consumers" and listed five.
- One blank line at EOF removed. The remaining `git diff --check` hits are
  pre-existing `.idea/`, php config and vendored caveman files, deliberately
  left alone.

**Honest note on the pattern.** Three consecutive entries have now had to
correct the entry before them: 0048 corrected 0047's measurement, and this
corrects 0046's durability claim and 0045/0046's traceability rule. The common
cause is not carelessness about testing — each was tested. It is testing the
happy path of the mechanism instead of the property being claimed. "The
commands work in sequence" is not "the pin survives". "The bytes left the file"
is not "the run costs less". "Every task has a REQ id" is not "the id reaches
the executor". The generalisation, now written where it will be read: **state
the property, then test the property's failure mode, not its success case.**

**Rejected — pinning both a commit sha and a blob sha.** Belt and braces, and
the blob half is the half that rots, so it would reintroduce a stale
verification path that looks authoritative.

**Rejected — dropping the pin and trusting `Status: Approved`.** That is the
original gap 0046 existed to close: an approved status proves a human approved
something, not that the file still says it.

**Rejected — hand-narrowing the Codex `git switch` rule.** Prefix matching
cannot exclude a flag. Same shape as `sed`, same outcome.

**Revisit if** the commit-pin requirement proves obstructive for genuinely
throwaway work — the honest alternative there is not a weaker pin but skipping
`/plan`, which `spec-driven-development`'s "When NOT to use" already sanctions.
