# AI / Agent Security Reference

Companion to `security-checklist.md` for systems using LLMs, RAG, autonomous/semi-autonomous agents, tools, browsers, code execution, or persistent memory.

## Core Security Model

Treat the model as an **untrusted decision component**, not a security boundary.

The model may:

- follow malicious instructions;
- misunderstand trusted instructions;
- hallucinate identifiers, arguments, or permissions;
- expose context;
- repeat or amplify malicious retrieved content;
- call the wrong tool or call the right tool with unsafe arguments.

Therefore authentication, authorization, tenant isolation, validation, policy, budgets, and irreversible-action controls must live in deterministic application/tooling layers.

## Prompt Injection

Assume both direct and indirect prompt injection.

Untrusted instruction sources include:

- user messages;
- documents and RAG chunks;
- websites/browser content;
- email and chat messages;
- tool/API responses;
- code comments and repository files;
- agent-to-agent messages;
- persistent memory.

Controls:

- [ ] Never grant permissions because model text says an action is authorized
- [ ] Separate data from trusted policy/instructions structurally where possible
- [ ] Enforce authorization at tool execution time
- [ ] Restrict available tools/data before the model sees them
- [ ] Treat retrieved/tool content as data, not policy
- [ ] Require deterministic approval for high-impact actions

## Tool Use / Excessive Agency

- [ ] Give each tool the minimum operations and data needed
- [ ] Prefer narrow domain tools over generic shell/browser/admin tools
- [ ] Validate tool arguments with typed schemas and domain rules
- [ ] Re-check object/tenant authorization using application identity
- [ ] Use idempotency for retried side effects
- [ ] Require confirmation/approval for destructive, irreversible, financial, publishing, credential, or permission-changing actions
- [ ] Bound tool-call count, concurrency, wall-clock time, and spend
- [ ] Audit high-impact tool calls and results

## Code / Shell / Browser Agents

When an agent can execute code, shell commands, or browse arbitrary URLs:

- [ ] Run in an isolated sandbox/container/VM appropriate to the risk
- [ ] Use non-root identities
- [ ] Mount only required files/data
- [ ] Keep credentials out of the sandbox unless strictly needed
- [ ] Restrict network egress and metadata/private-network access where possible
- [ ] Bound CPU, memory, disk, process count, execution time, and output size
- [ ] Destroy/reset ephemeral environments between untrusted workloads where appropriate

## RAG

- [ ] Apply tenant/user ACL filters before/during retrieval
- [ ] Do not retrieve globally and filter after generation
- [ ] Namespace/partition vector data where it materially reduces cross-tenant risk
- [ ] Preserve document owner, tenant, ACL, provenance, version, and source metadata
- [ ] Validate uploads before parsing/indexing
- [ ] Treat chunk text as untrusted instructions
- [ ] Support quarantine/removal/re-index after poisoning or access changes
- [ ] Include embedding/index deletion in retention/deletion flows
- [ ] Keep citations/provenance for high-stakes or auditable answers

## Memory

Persistent memory can turn one malicious input into a long-lived compromise.

- [ ] Scope memory by tenant/user/session/purpose
- [ ] Validate and classify memory writes
- [ ] Do not store secrets unnecessarily
- [ ] Do not treat memory as authorization/policy
- [ ] Set retention/TTL where appropriate
- [ ] Support correction/deletion
- [ ] Audit important memory writes

## Model / Provider / Dataset Supply Chain

- [ ] Model/provider identity/version known
- [ ] Provider data-retention/training policy compatible with the data sent
- [ ] Fine-tuning/evaluation datasets have provenance and access controls
- [ ] Poisoning risks considered for user-contributed training/RAG data
- [ ] Provider/model fallback does not silently weaken data residency, retention, safety, or tool guarantees
- [ ] Model artifacts/checkpoints verified when self-hosted

## Output Handling

Model output must not flow directly into dangerous interpreters/sinks.

Validate or sandbox before using model-generated:

- SQL
- shell commands
- code
- file paths
- HTML/Markdown rendered with dangerous extensions
- URLs and redirects
- tool names and arguments
- object/tenant identifiers
- email recipients / external destinations
- infrastructure configuration

## Resource / Cost Abuse

Bound:

- input size;
- output tokens;
- model calls;
- tool calls;
- recursion/graph depth;
- concurrent runs;
- wall-clock time;
- upload/document size;
- retrieval breadth;
- browser pages/downloads;
- code execution resources;
- monetary spend per user/tenant/run/time window.

## Observability

For high-impact or agentic flows, retain enough structured telemetry to answer:

- who initiated the run;
- which tenant/data scope applied;
- which model/version handled it;
- which tools were available;
- which tools were called and with what validated arguments;
- which approvals occurred;
- what external side effects happened;
- why a run stopped (success, budget, policy, timeout, error).

Do not log secrets or unnecessary sensitive prompt/tool payloads merely for observability.

## Useful References

- OWASP GenAI Security Project: https://genai.owasp.org/
- OWASP Top 10 for LLM Applications: https://genai.owasp.org/llm-top-10/
- OWASP Top 10 for Agentic Applications: https://genai.owasp.org/
- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
