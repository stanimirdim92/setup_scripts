# Risk tier and review depth

Single source of truth for the risk tier `/review` records and the depth it
reviews at (ADR 0106). The change sets the tier, not the author, the ticket's
priority, or how small the diff looks.

## Tier

Take the highest tier that matches.

**High**, when the change:

- touches a path in the project's "Always a person" list (`always-person.py`);
- can corrupt, delete, migrate, or reinterpret persistent data;
- alters authentication, authorization, permissions, secrets, cryptography,
  tenant isolation, or another security boundary;
- alters concurrency, retries, idempotency, ordering, delivery, queue
  processing, or job recovery;
- changes a public or shared contract consumed outside this change (an API,
  an event, a file format, a package export);
- touches money, billing, or a flow whose failure has legal or financial
  impact.

**Low**, when every changed file is exempt from `/test`
(`verification-triggers.md`), or the change is user-visible copy, or it is
purely additive behind a feature flag that is off by default.

**Medium**: everything else, which is most product work.

When unsure between two tiers, take the higher.

## Depth

The tier picks the depth. A project can raise the floor with a
`## Review depth` heading in its `REVIEW.md` (`Quick`, `Standard` or `Deep`);
the base branch's value wins over a lower tier, never the reverse. The user can
ask for a deeper review; nobody can ask for a shallower one than the tier.

| | Quick (Low) | Standard (Medium) | Deep (High) |
|---|---|---|---|
| Reviewers | the three always-on reviewers, plus specialists by trigger | the same | the same, and a specialist whose trigger might match is dispatched |
| Independent check (ADR 0092) | BLOCKER findings | BLOCKER findings | BLOCKER and REQUIRED findings |
| ADVISORY findings | at most 3 per reviewer | the REVIEW.md nit cap | the REVIEW.md nit cap |
| `/test` | per `verification-triggers.md` | per `verification-triggers.md` | required, with a mutation probe on every changed condition and the full suite |
| `/ship` asks the owner to | read the summary | read the diff | read every changed file, and get a second person where the team has one |

Security review runs at every depth (ADR 0102). Depth never removes a
reviewer that `reviewer-triggers.md` requires.

Do not duplicate this file in `/review`, `/test`, `/ship`, or agent
definitions; point to it.
