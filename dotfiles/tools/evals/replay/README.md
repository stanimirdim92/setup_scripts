# Replay a shipped ticket

Run today's harness on a ticket that already shipped, from the code as it was
before the ticket started, and compare each stage with what really happened.
It answers one question: would the current harness do this ticket better?

The worked example is LD-440, the parent of LD-441 (backend) and LD-442
(frontend). Paths are for this machine; adjust them for another one.

```bash
H=/var/www/html/personal/setup_scripts        # this repository
P=/var/www/html/leadbuster                    # the project
R=/var/www/html/replay-LD-440                 # the replay checkout (created below)
```

## 0. Bring the harness up to date

```bash
cd $H && git pull
./dotfiles/tools/setup/link_dotfiles.sh
./dotfiles/tools/setup/fetch-figma-skill.sh
claude mcp list            # figma and chrome-devtools must show Connected
```

In a Claude session, run `/sandbox` once and check that it reports the sandbox
as active.

## 1. Prepare the replay checkout

```bash
cd $P && git pull
$H/dotfiles/tools/evals/replay/prepare.sh $P 'LD-44[012]' $R
cd $R && bin/worktree-setup.sh      # the project's own dependency and database setup
```

`prepare.sh` finds the first commit whose message names LD-440, 441 or 442. It
clones the commit before it at depth 1, with no remote, and copies the
gitignored files that `.worktreeinclude` lists. The replay cannot see the
shipped specs, plans or code: they are not in its history.

Check the `base` line it prints. If the first matching commit is not really
where the work started, choose the base by hand and rerun with a narrower
pattern.

## 2. Run the pipeline in the replay

Start `claude` in `$R` and run the stages in order. Write down the start and
end time of each stage (UTC) for the metrics in step 3.

| Stage | Command | What you do |
| --- | --- | --- |
| Intake | `/jira-ticket LD-440` | Nothing. Jira now also holds comments written after the work shipped, so the replay knows a little more than the original run did. |
| Spec | `/spec LD-440` | Answer its questions the way you did originally. Your answers are the `DEC-###` entries in the deployed specs. Approve when it is ready. |
| Plan | `/plan LD-440` | Approve as you would have. |
| Build | `/build` | Answer questions as you did originally. Do not fix anything by hand. |
| Review | `/review` | Nothing. |
| Test | `/test` | Only if `/review` requires it. |
| Ship | `/ship` | Read the decision. Do not push. |

After each stage, print its observation-log row from `$R`:

```bash
$H/dotfiles/tools/run/run-metrics.sh --row LD-440 /spec --since 2026-10-04T08:00 --until 2026-10-04T08:40
```

## 3. Score each stage

**Spec.** Compare the replay spec with the two deployed specs. This needs the
spec-eval fixtures built once from the real project:

```bash
cd $H/dotfiles/tools/evals/spec-eval
python3 run.py --new LD-441 --repo $P --reference docs/specs/LD-441-SPEC.md   # once
python3 run.py --new LD-442 --repo $P --reference docs/specs/LD-442-SPEC.md   # once
python3 run.py --fixture LD-441 --spec $R/docs/specs/LD-440-SPEC.md
python3 run.py --fixture LD-442 --spec $R/docs/specs/LD-440-SPEC.md
```

Read the "not named" terms. A term from one of your own decisions (DEC-005,
DEC-009) is not a miss if the replay raised it as a question.

**Plan.** Score the replay plan against what really changed:

```bash
python3 $H/dotfiles/tools/evals/plan-recall/recall.py --repo $P \
    --ticket LD-441 --ticket LD-442 --subject-only --show-commits \
    --plan $R/docs/tasks/LD-440-plan.md --plan $R/docs/tasks/LD-440-todo.md \
    --range <base printed by prepare.sh>..<last LD-441/442 commit on main>
```

The original plans scored 100% (LD-441) and 67% (LD-442) on existing files.

**Build.** Run the shipped tests against the replay's implementation. A test
written for the real code that passes on the replay is strong evidence that
the behavior matches. Copy the test with any helper it uses; if the replay
already has a file at that path, rename the copy instead of overwriting it:

```bash
cd $R
git -C $P show main:tests/Feature/Socials/TickerFeedSeeder.php > tests/Feature/Socials/TickerFeedSeeder.php
git -C $P show main:tests/Feature/Socials/TickerMostRelevantFeedTest.php > tests/Feature/Socials/ShippedMostRelevantTest.php
composer test -- --filter=ShippedMostRelevant
```

A failure here can mean a real gap, or only a different internal shape. Read
it before you count it.

**Review.** Compare the replay's findings with what the real run found later:
the throw for an unmapped event type, the backfill not copying `score`, and
the DEC-005 reversal. Did the replay find any of them before `/ship`?

**Ship.** Compare the GO or NO-GO with how the real release went.

## 4. Record and clean up

Record in `$H/dotfiles/docs/observation-log.md`:
- a Run metrics row per stage;
- a Plan recall row for the replay plan;
- a Failures row for anything the replay got wrong that the original got
  right, or the reverse.

Then remove the replay:

```bash
rm -rf $R      # a standalone clone: nothing else references it
```

## Cost and limits

Every stage runs the real models, the same as a normal ticket. Spec, plan and
review run on Opus; build and test on Sonnet. Budget for a full ticket run.

The replay is not a perfect rerun. Jira has changed since, you know how the
work ended, and the models have changed. Treat a difference as something to
read, not as a score.
