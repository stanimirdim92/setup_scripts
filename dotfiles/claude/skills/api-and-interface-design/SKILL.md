---
name: api-and-interface-design
description: Guides stable API and interface design. Use when designing APIs, module boundaries, or any public interface. Use when creating REST or GraphQL endpoints, defining type or tool-call contracts between modules or services, or establishing boundaries between components, languages, or a model and its tools.
---

# API and Interface Design

## Overview

Design stable, well-documented interfaces that are hard to misuse. Good interfaces make the right thing easy and the wrong thing hard. This applies to REST APIs, GraphQL schemas, module boundaries, function and type contracts between components, the tool/function schemas an LLM is given, and any surface where one piece of code — or one system — talks to another.

The principles here are language- and transport-independent. Examples appear in several languages (TypeScript, Python, Rust) and as LLM tool schemas; each illustrates a principle that holds regardless of the stack. When you apply the skill, follow the repository's own language and conventions — the principle is the rule, the example is only a picture of it.

## When to Use

- Designing new API endpoints or RPC/service methods
- Defining module boundaries or contracts between teams, services, or languages
- Defining the tool/function schemas exposed to an LLM
- Creating function signatures, component props, or type contracts
- Establishing database schema that informs an interface's shape
- Changing an existing public interface

## Core Principles

These nine principles are the substance of the skill. Everything below them is illustration.

### Hyrum's Law

> With a sufficient number of users of an API, all observable behaviors of your system will be depended on by somebody, regardless of what you promise in the contract.

Every public behavior — undocumented quirks, error-message text, field ordering, timing, default values, even the shape of a tool's output an LLM has learned to parse — becomes a de facto contract once something depends on it. Design implications:

- **Be intentional about what you expose.** Every observable behavior is a potential commitment.
- **Don't leak implementation details.** If a consumer can observe it, something will depend on it.
- **Plan for deprecation at design time.** See `deprecation-and-migration` for removing things consumers depend on.
- **Tests are not enough.** Even with perfect contract tests, "safe" changes can break real consumers who depend on behavior you never promised.

Hyrum's Law has a companion — the **Law of Leaky Abstractions**: every non-trivial abstraction leaks some of what it sits on top of. You cannot seal an interface perfectly; some implementation detail (an error, a timing, an ordering, a limit) will always show through. Hyrum's Law then says consumers *will* depend on whatever leaks. Together they set the design stance: since something always leaks and anything observable becomes a commitment, choose deliberately *what* you let leak, and treat those leaks as part of the contract rather than pretending they aren't there.

### The One-Version Rule

Avoid forcing consumers to choose between multiple live versions of the same dependency or interface. Diamond-dependency problems arise when different consumers need different versions of the same thing. Design for a world where one version exists at a time — extend rather than fork. This applies equally to a shared library's API, a service endpoint, and the tool schema a fleet of agents all call.

### 1. Contract First

Define the interface before implementing it. The contract is the spec; the implementation follows it. Write the signatures, types, errors, and semantics — then build to them.

The contract is the same idea in any stack: named operations, their inputs, their outputs, and what each promises. Below, the same task API expressed four ways.

```typescript
// TypeScript
interface TaskAPI {
  createTask(input: CreateTaskInput): Promise<Task>;      // returns created task incl. server fields
  listTasks(params: ListTasksParams): Promise<Page<Task>>; // paginated
  getTask(id: TaskId): Promise<Task>;                      // throws NotFound if absent
  updateTask(id: TaskId, input: UpdateTaskInput): Promise<Task>; // partial update
  deleteTask(id: TaskId): Promise<void>;                   // idempotent: ok if already gone
}
```

```python
# Python (Protocol = structural contract, no implementation)
from typing import Protocol

class TaskAPI(Protocol):
    def create_task(self, data: CreateTaskInput) -> Task: ...          # created task incl. server fields
    def list_tasks(self, params: ListTasksParams) -> Page[Task]: ...   # paginated
    def get_task(self, task_id: TaskId) -> Task: ...                   # raises NotFound if absent
    def update_task(self, task_id: TaskId, data: UpdateTaskInput) -> Task: ...  # partial update
    def delete_task(self, task_id: TaskId) -> None: ...                # idempotent: ok if already gone
```

### 2. Consistent Error Semantics

Pick one error strategy and use it everywhere. The failure path is part of the contract — a consumer must be able to predict how *every* operation reports failure, not discover it per call.

The mechanism differs by stack — a discriminated result, an exception hierarchy, a `Result` type, HTTP status codes, or a structured error block in a tool result — but the rule is the same: **one strategy, uniform shape, machine-readable code plus human-readable message.**

```typescript
// One error shape, everywhere. Discriminated so callers must handle both arms.
type Result<T> =
  | { ok: true; value: T }
  | { ok: false; error: { code: string; message: string; details?: unknown } };
```

```python
# One exception hierarchy, everywhere. Callers catch ApiError or a specific subclass.
class ApiError(Exception):
    def __init__(self, code: str, message: str, details: object | None = None):
        self.code, self.message, self.details = code, message, details

class ValidationError(ApiError): ...   # invalid input
class NotFoundError(ApiError): ...      # resource absent
class ConflictError(ApiError): ...      # duplicate / version clash
```

```rust
// One error enum, everywhere. The type system forces the caller to handle it.
enum ApiError {
    Validation { field: String, message: String },
    NotFound { resource: String },
    Conflict { message: String },
    Internal,  // never leak internal detail across the boundary
}
```

For HTTP transports, map that one strategy onto status codes consistently:

```
// Status code mapping
// 400 → Client sent invalid data
// 401 → Not authenticated
// 403 → Authenticated but not authorized
// 404 → Resource not found
// 409 → Conflict (duplicate, version mismatch)
// 422 → Validation failed (semantically invalid)
// 500 → Server error (never expose internal details)
```

For an LLM tool, the "error" is a result the model has to act on, so make it explicit and instructive rather than throwing something the harness swallows:

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "title is required", "retryable": false } }
```

**Don't mix patterns.** If some operations or endpoints throw, some return a null/none, and some return an error object, the consumer cannot write correct code against the interface.

### 3. Validate at Boundaries

Trust internal code; validate at the edges where external input enters. Inside the trust boundary, rely on the type contract — don't re-validate data your own code already guaranteed. At the boundary, treat everything as hostile until checked.

```python
# Validate once, at the boundary; internal code then trusts the parsed type.
def create_task_endpoint(raw: dict) -> Response:
    parsed = CreateTaskSchema.validate(raw)      # raises ValidationError on bad input
    if parsed.errors:
        return Response(422, {"error": {"code": "VALIDATION_ERROR", "details": parsed.errors}})
    task = task_service.create(parsed.value)     # service trusts the validated type
    return Response(201, task)
```

```rust
// Parse, don't validate: convert unstructured input into a typed value at the edge,
// and the rest of the program cannot hold an invalid one.
fn create_task(raw: &str) -> Result<Task, ApiError> {
    let input: CreateTaskInput = serde_json::from_str(raw)   // shape-checked here
        .map_err(|e| ApiError::Validation { field: "body".into(), message: e.to_string() })?;
    task_service.create(input)                                // downstream trusts the type
}
```

Where validation **belongs**: request/RPC handlers, form or event handlers, external-service response parsing, environment/config loading, and — critically — **arguments arriving from an LLM tool call**.

Where validation does **not** belong: between internal functions sharing a type contract, in utilities called only by already-validated code, or on data that just came from your own database.

> **External and model-supplied inputs are untrusted.** Third-party API responses, and arguments an LLM passes to a tool, must have their shape *and* content validated before use in logic, rendering, storage, or a downstream call. A misbehaving service — or a model that has been prompt-injected — can supply unexpected types, out-of-range values, or instruction-like text. Validate at the boundary regardless of source.

### 4. Be Liberal in What You Accept — Within Strict Limits

Postel's Law (the Robustness Principle): *be conservative in what you send, liberal in what you accept.* Send output that rigidly follows your own contract, and tolerate reasonable variation in the *format* of what arrives — an optional field omitted, a date in a slightly different but unambiguous form, extra properties you can ignore.

But liberality has a hard boundary, and modern practice sharpens the original law: **liberal in format, strict in safety.** Being too accepting is how Hyrum's-Law dependencies and security holes form — a lenient parser that quietly accepts malformed input turns that malformation into a de-facto contract, and an interface that guesses at ambiguous input eventually guesses wrong. So:

- Accept format variation, then **normalize to one strict internal representation** immediately — don't let the variation propagate inward.
- Never relax *validation* in the name of liberality: shape, type, range, and content are still checked at the boundary (principle 3). Tolerating a missing optional field is liberal; tolerating an unvalidated one is a bug.
- Reject the genuinely ambiguous rather than guessing. A rejected request is recoverable; a wrong guess acted upon is not.

This is the reconciliation of "liberal in what you accept" with "external and model-supplied input is untrusted": be forgiving about form, unforgiving about safety.

### 5. Prefer Addition Over Modification

Extend an interface without breaking existing consumers: add optional inputs and new operations; don't change the type of an existing field, repurpose it, or remove it.

```python
# Good: new fields are optional with safe defaults — old callers keep working.
@dataclass
class CreateTaskInput:
    title: str
    description: str | None = None
    priority: Priority = Priority.MEDIUM     # added later, defaulted
    labels: list[str] = field(default_factory=list)  # added later, defaulted

# Bad: removing `description` or changing `priority` from str to int breaks existing callers.
```

### 6. Principle of Least Astonishment

An interface should behave the way its consumer expects it to. When a name, signature, or result forces the consumer to say "wait, it does *what*?", the design has failed regardless of how well it's documented — surprise is a defect. This principle is the *why* beneath the two rules that follow (consistent naming and consistent errors) and beneath consistent semantics generally: consumers build a mental model from the first few operations they touch and expect the rest to match it. An operation named `get*` that also writes, a `delete` that isn't idempotent when every neighbour is, a field that means one thing on create and another on read — each is astonishing, and each becomes a bug someone hits at the worst time.

The stakes are highest for LLM tools: a model has *only* the name and description to predict behavior from, so a tool that does anything beyond what its name and description imply is the most expensive surprise there is — the model cannot see the source to correct its expectation. Name and describe tools so the obvious reading is the correct one.

### 7. Predictable Naming

Consistency lets a consumer guess the next name correctly. Adopt the repository's existing convention; the table below is a common baseline for HTTP/JSON APIs — a Python or Rust library will use that language's idioms (`snake_case`, etc.) instead. What matters is that the surface is internally uniform.

| Element | Convention (HTTP/JSON baseline) | Example |
|---------|--------------------------------|---------|
| REST endpoints | plural nouns, no verbs | `GET /tasks`, `POST /tasks` |
| Query params | camelCase | `?sortBy=createdAt&pageSize=20` |
| Response fields | camelCase | `{ createdAt, updatedAt, taskId }` |
| Boolean fields | `is`/`has`/`can` prefix | `isComplete`, `hasAttachments` |
| Enum values | UPPER_SNAKE | `"IN_PROGRESS"`, `"COMPLETED"` |

The anti-pattern is language-independent: don't put verbs in REST URLs (`/createTask`), and don't mix `camelCase` and `snake_case` in one response body or one schema.

### 8. Make Illegal States Unrepresentable

Prefer a type that cannot express an invalid combination over a loose type plus runtime checks. If the interface makes a bad state impossible to construct, no consumer can reach it and no validation is needed for it.

```typescript
// Discriminated union: fields that only exist in one state live only in that arm.
type TaskStatus =
    | { type: 'pending' }
    | { type: 'in_progress'; assignee: string; startedAt: Date }
    | { type: 'completed'; completedAt: Date; completedBy: string }
    | { type: 'cancelled'; reason: string; cancelledAt: Date };
// No way to have a `completedAt` on a pending task.
```

```python
# Python: a tagged union of dataclasses; match makes handling exhaustive.
@dataclass
class Pending: pass
@dataclass
class InProgress: assignee: UserId; started_at: datetime
@dataclass
class Completed: completed_at: datetime; completed_by: UserId
TaskStatus = Pending | InProgress | Completed
```

Two supporting habits in the same spirit:

- **Separate input from output types.** What the caller provides (no server-generated fields) is a different type from what the system returns (ids, timestamps, computed fields). Don't force one type to do both with a scatter of optional fields.
- **Give identifiers distinct types where the language allows.** A `TaskId` and a `UserId` that are both bare strings will eventually be swapped by accident. Branded types (TS), newtypes (Rust `struct UserId(String)`), or `NewType` (Python) make that a compile-time or checker error.

### 9. Idempotency for State-Changing Operations

Any operation that can be retried — and across a network, all of them can — needs a defined answer to "what if this runs twice?" Accepting an idempotency key is the *contract*; honouring it is the *implementation*, and it is where money is lost. A key the server accepts but handles carelessly is worse than no key, because the client now believes retrying is safe.

**Derive the key from the intent, not the attempt** — stable across retries of one intent, distinct across different intents:

```
random-uuid-per-call        ✗ new key each attempt → every retry is a fresh effect
"{userId}:{amount}"         ✗ two legitimate $50 charges collapse into one
"{orderId}:{timestamp}"     ✗ a timestamp is a per-attempt value in disguise
client-supplied key         ✓ generated once by the initiator, reused on retry
"charge:v1:{orderId}"       ✓ derived from an immutable identifier
```

The key comes from the client or the initiating event — never from the layer doing the retrying.

**Claim it atomically — a check-then-act is a race:**

```python
# ✗ TOCTOU: two concurrent retries both read "not seen", both perform the effect
if not db.exists(key):
    charge_card(amount)
    db.insert(key)

# ✓ let a unique constraint pick the single winner
try:
    db.insert(key=key, state="in_progress", request_hash=h)
except UniqueViolation:
    return replay_or_reject(key)
result = charge_card(amount)
db.update(key=key, state="succeeded", response=result)
```

The unique constraint *is* the mechanism; a store that can't enforce uniqueness in one operation can't back this.

**Guard the payload.** The same key with a different body is a client bug — fail loudly rather than serving the first response to a different request:

```python
if existing.request_hash != hash(body):
    return error(422, "idempotency key reused with a different payload")
```

**Decide what an in-flight duplicate gets** — the first request is still running when the second arrives, the common case under a retry storm:

| Strategy | Response | Use when |
|---|---|---|
| Reject | conflict (`409`) | client can retry later; simplest and safest |
| Wait | block for the result, bounded | caller needs it synchronously |
| Return pending | accepted (`202`) + status handle | long-running effects |

Never let the second caller through because the first "seems stuck" — a stalled attempt of unknown fate is exactly when duplicating costs most.

**Every call has three outcomes, not two: success, failure, and _unknown_.** A timeout tells you nothing about whether the effect applied. Record the intent *before* calling out, so a crash between the call and its response leaves evidence something must be resolved later, rather than a silently retried effect.

**Set retention from the longest retry chain**, not from storage cost. Keys must outlive every path that can re-deliver the same intent — a dead-letter queue replayed a week later, a provider dispute window. A 24-hour key behind a 7-day DLQ is a duplicate waiting to happen.

### 10. Pagination, Filtering, and Partial Update

Three list/mutation habits that are cheap at design time and expensive to retrofit:

- **Paginate every list from the start.** An endpoint or method that returns "all" items becomes a problem the moment a consumer has hundreds. Return a page plus metadata (page/size/total, or a cursor).
- **Filter and sort via explicit parameters**, not by returning everything and letting the caller filter.
- **Support partial update** where it fits: accept only the fields that change rather than requiring the caller to resubmit the whole object.

```typescript
type TaskId = string & { readonly __brand: 'TaskId' };
type UserId = string & { readonly __brand: 'UserId' };

// Prevents accidentally passing a UserId where a TaskId is expected
function getTask(id: TaskId): Promise<Task> { ... }
```

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "We'll document the interface later" | The types/signatures ARE the documentation. Define them first. |
| "We don't need pagination for now" | You will the moment a consumer has 100+ items. Add it from the start. |
| "Full-object update is simpler than partial" | It forces every caller to resend everything and clobbers concurrent edits. Support partial update. |
| "We'll version it when we need to" | Breaking changes without a version break consumers silently. Design for extension from the start. |
| "Nobody uses that undocumented behavior" | Hyrum's Law: if it's observable, something depends on it. Treat every public behavior as a commitment. |
| "We can just maintain two versions" | Multiple live versions multiply maintenance and create diamond-dependency problems. Prefer the One-Version Rule. |
| "Internal interfaces don't need contracts" | Internal consumers are still consumers. Contracts prevent coupling and enable parallel work. |
| "The model will figure out the arguments" | The model has only your schema and descriptions. Vague descriptions produce malformed calls; be explicit. |
| "Be liberal — just accept whatever comes in" | Liberal in *format*, strict in *safety*. Accepting unvalidated or ambiguous input turns malformation into a contract and opens holes. Normalize to one strict internal form. |
| "Accepting the idempotency key is enough" | The key is the contract; claiming it atomically against the result is the implementation. A key you accept but don't honour tells the client retrying is safe when it isn't. |
| "Our queue guarantees exactly-once delivery" | None does across a consumer crash — the broker's ack and your side effect aren't in one transaction. Design for at-least-once with idempotent processing. |
| "Duplicate requests are rare" | They're *correlated*. Retries spike exactly when a dependency is degraded — when duplicates are most likely and most costly. |

## Red Flags

- An operation that returns different shapes depending on conditions
- Inconsistent error format/strategy across operations in the same interface
- Validation scattered through internal code instead of at the boundary
- External or model-supplied input used without validation
- Breaking changes to existing fields (type change, removal, repurposing)
- List endpoints or methods with no pagination
- Verbs in REST URLs (`/createTask`, `/getUsers`), or mixed casing in one surface
- Bare-string identifiers that are easily swapped (no branded/newtype distinction)
- A read-then-write for an idempotency key — that's a race, not a guard
- An idempotency key derived from a UUID, timestamp, or anything regenerated per attempt
- The same key accepted with a different body, silently replaying the first response
- Key retention shorter than the longest path that can re-deliver the request
- An LLM tool whose field descriptions don't state required/optional, defaults, or format
- A parser that silently accepts malformed or ambiguous input instead of rejecting or normalizing it
- An operation whose behavior contradicts its name (a `get*` that writes, a non-idempotent `delete` among idempotent siblings)

## Verification

After designing an interface:

- [ ] Every operation has typed (or fully described) input and output
- [ ] Errors follow a single consistent strategy and shape across the whole interface
- [ ] Validation happens at boundaries only; external and model-supplied input is validated for shape and content
- [ ] List operations support pagination; filtering/sorting use explicit parameters
- [ ] New fields/parameters are additive and optional with safe defaults (backward compatible)
- [ ] Naming is internally consistent and follows the repository's language conventions
- [ ] Illegal states are unrepresentable where the type system allows; input and output types are separate
- [ ] Documentation or types are committed alongside the implementation
- [ ] State-changing operations either honour an idempotency key or are documented as unsafe to retry
- [ ] The key is claimed in one atomic operation, guarded by a unique constraint
- [ ] A reused key with a different payload fails loudly rather than replaying the wrong response
- [ ] The in-flight-duplicate response is a deliberate choice (reject / wait / pending), not whatever falls out
- [ ] Key retention outlives the longest retry path, including dead-letter replay
- [ ] For LLM tools: descriptions state required/optional, defaults, units, and format; results are structured for the model to act on
