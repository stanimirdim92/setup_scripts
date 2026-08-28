# Security Checklist

Quick reference for web application and AI/agent security. Use this as a practical review checklist; use [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) and the linked references when deeper verification is required.

> Keep this file principle-focused. Version-specific commands and fast-changing ecosystem details belong in `references/`.

## Table of Contents

- [Threat Modeling (Start Here)](#threat-modeling-start-here)
- [Pre-Commit & Secrets](#pre-commit--secrets)
- [Authentication](#authentication)
- [Authorization](#authorization)
- [API Security](#api-security)
- [Input Validation](#input-validation)
- [File Handling](#file-handling)
- [Browser Security](#browser-security)
- [Data Protection & Privacy](#data-protection--privacy)
- [Secrets & Key Management](#secrets--key-management)
- [Dependency & Supply-Chain Security](#dependency--supply-chain-security)
- [Infrastructure & Deployment](#infrastructure--deployment)
- [Logging & Monitoring](#logging--monitoring)
- [Security Testing](#security-testing)
- [Failure & Exceptional Conditions](#failure--exceptional-conditions)
- [AI / LLM Security](#ai--llm-security)
- [RAG / Retrieval Security](#rag--retrieval-security)
- [Agent & Tool Security](#agent--tool-security)
- [Agent Memory](#agent-memory)
- [Incident Readiness](#incident-readiness)
- [OWASP Top 10:2025 Quick Reference](#owasp-top-102025-quick-reference)
- [OWASP Top 10 for LLM Applications:2025](#owasp-top-10-for-llm-applications2025)

## Threat Modeling (Start Here)

Before reaching for controls, spend five minutes thinking like an attacker:

- [ ] Trust boundaries mapped (requests, uploads, webhooks, queues, third-party APIs, LLM output, tool calls)
- [ ] Assets named (credentials, PII, payment data, tenant data, admin actions, money movement)
- [ ] STRIDE run per boundary (Spoofing, Tampering, Repudiation, Information disclosure, DoS, Elevation of privilege)
- [ ] Abuse cases written next to use cases ("how would I misuse this?")
- [ ] High-impact actions identified (delete, publish, send, charge, transfer, deploy, change permissions)
- [ ] Failure behavior defined: which checks must fail closed?

## Pre-Commit & Secrets

- [ ] No secrets in staged changes; automated secret scanning used where possible (for example Gitleaks or TruffleHog) or (`git diff --cached | grep -i "password\|secret\|api_key\|token"`)
- [ ] `.gitignore` covers local secret/config files such as `.env`, `.env.local`, `*.pem`, `*.key`
- [ ] `.env.example` contains placeholders only
- [ ] Generated artifacts, fixtures, logs, and test snapshots contain no real credentials or sensitive production data
- [ ] Security-sensitive configuration changes receive explicit review

## Authentication

- [ ] Passwords hashed with Argon2id (preferred); scrypt acceptable; bcrypt retained only where required/legacy
- [ ] Session cookies use `httpOnly`, `secure`, and an appropriate `sameSite` policy
- [ ] Session lifetime and idle timeout are bounded
- [ ] Session ID rotated after authentication and privilege changes
- [ ] Sessions invalidated on logout and security-sensitive account changes
- [ ] Login/reset/recovery endpoints rate-limited
- [ ] Password-reset tokens are random, single-use, and time-limited
- [ ] Authentication responses do not enable username/email enumeration
- [ ] MFA required for privileged or high-impact access where appropriate
- [ ] JWTs validate allowed algorithm, signature, expiration, issuer, and audience
- [ ] JWT signing keys can be rotated and revoked

## Authorization

- [ ] Every protected endpoint checks authentication
- [ ] Every resource access checks ownership/tenant/role (prevents BOLA/IDOR)
- [ ] Authorization enforced server-side, never inferred from UI visibility
- [ ] Admin/privileged operations require explicit role/capability checks
- [ ] API keys and service identities use least-privilege scopes
- [ ] Cross-tenant access is denied by default
- [ ] Authorization is re-checked at execution time for queued/background/high-impact actions
- [ ] Database-level controls such as RLS are used as defense in depth where appropriate

## API Security

- [ ] Object-level authorization checked for every client-supplied resource identifier
- [ ] Property-level authorization enforced; prevent over-posting/mass assignment
- [ ] Function-level authorization enforced independently of routes/UI
- [ ] Request and response schemas explicitly defined and validated
- [ ] API responses expose only explicitly intended fields
- [ ] Pagination, filtering, and maximum result sizes bounded
- [ ] Request-body and upload-size limits enforced
- [ ] Expensive endpoints have rate, concurrency, timeout, and cost limits
- [ ] Idempotency used for retried state-changing operations where appropriate
- [ ] Third-party API responses treated as untrusted input
- [ ] API inventory/version ownership maintained; deprecated endpoints removed
- [ ] Sensitive business flows protected against automation/abuse, not only raw request volume

### Webhooks

- [ ] Webhook signature/MAC verified against the raw request body
- [ ] Timestamp/nonce or provider replay mechanism checked
- [ ] Duplicate events handled idempotently
- [ ] Webhook secrets independently rotatable
- [ ] Event authorization/business rules applied after authenticity verification
- [ ] Unknown event types rejected safely

## Input Validation

- [ ] All untrusted input validated at system boundaries
- [ ] Validation prefers allowlists and structured schemas over denylists
- [ ] String lengths and numeric ranges bounded
- [ ] Email, URL, date, UUID, enum, and identifier formats validated with appropriate libraries
- [ ] SQL uses parameters/bindings; no query construction by string concatenation
- [ ] HTML output encoded; framework auto-escaping kept enabled
- [ ] Redirect destinations validated to prevent open redirects
- [ ] Server-side URL fetches validate scheme/host and block private, loopback, link-local, metadata, and reserved ranges unless explicitly required
- [ ] Deserialized/decoded data treated as untrusted after parsing

## File Handling

- [ ] Extension, declared MIME type, and file signature/magic bytes validated
- [ ] Maximum file size enforced before expensive parsing
- [ ] Uploaded filename never used directly as a filesystem path
- [ ] Server-side filenames/IDs generated independently from user input
- [ ] Path traversal prevented
- [ ] Uploaded files stored outside the web root where practical
- [ ] Archive expansion, decompression ratio, recursion depth, and total extracted size bounded
- [ ] Parser CPU/memory/time limits enforced
- [ ] Dangerous active content rejected or sanitized where applicable
- [ ] Malware scanning used where the threat model requires it
- [ ] Downloads use safe `Content-Type` and `Content-Disposition`

## Browser Security

### Security Headers

Baseline — adapt CSP and permissions to the application:

```http
Content-Security-Policy: default-src 'self'; script-src 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

- [ ] CSP avoids unsafe inline/eval allowances unless there is a reviewed reason
- [ ] HSTS enabled only after HTTPS is correctly deployed across intended subdomains
- [ ] Sensitive responses use appropriate cache controls

### CORS

- [ ] Explicit trusted origins configured
- [ ] `Access-Control-Allow-Credentials` used only when required
- [ ] Allowed methods and headers minimized
- [ ] Origin reflection avoided unless strict validation is implemented
- [ ] Wildcard origin never combined with credentialed browser access

```typescript
// Restrictive (recommended)
cors({
  origin: ['https://yourdomain.com', 'https://app.yourdomain.com'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization'],
})

// NEVER use in production:
cors({ origin: '*' })  // Allows any origin
```

### CSRF

- [ ] Cookie-authenticated state-changing requests protected against CSRF
- [ ] `SameSite` is defense in depth, not the only control when the threat model requires anti-CSRF tokens/origin checks

## Data Protection & Privacy

- [ ] Sensitive fields excluded from API responses
- [ ] Sensitive data not logged (passwords, tokens, full payment data, unnecessary PII)
- [ ] TLS/HTTPS used for external communication
- [ ] Sensitive data encrypted at rest where required by policy/regulation/threat model
- [ ] Database backups encrypted
- [ ] Data classified (for example public/internal/confidential/restricted)
- [ ] Collect only data actually required
- [ ] Retention periods defined and enforced
- [ ] User/tenant deletion removes associated data where required
- [ ] Backup retention follows the same lifecycle policy
- [ ] Backup restoration periodically tested
- [ ] Encryption keys managed separately from encrypted data

## Secrets & Key Management

- [ ] Secrets stored in a secret manager or protected deployment environment
- [ ] Separate credentials per environment
- [ ] Separate service identities/credentials where blast-radius reduction matters
- [ ] Credentials scoped to minimum necessary permissions
- [ ] Secrets never committed, logged, returned, embedded in images/artifacts, or placed in LLM context
- [ ] Secrets/API keys can be rotated and revoked
- [ ] Compromised-credential response procedure documented
- [ ] Production secrets unavailable to development/test environments
- [ ] Signing/encryption keys have ownership and rotation policy

## Dependency & Supply-Chain Security

- [ ] Exactly one authoritative lockfile per project/workspace installation boundary
- [ ] CI uses frozen/immutable dependency installation and never silently rewrites the lockfile
- [ ] Dependency lifecycle/install scripts blocked or explicitly reviewed before first execution
- [ ] Known-vulnerability audit runs in CI
- [ ] Critical/high findings triaged for reachability; deferrals have owner/reason/review date
- [ ] Forced automatic remediation that changes dependency ranges is not applied blindly
- [ ] New dependencies reviewed for ownership, maintenance, release history, provenance, transitive graph, and typosquatting
- [ ] Registry signatures/provenance verified where supported
- [ ] Build/CI dependencies and third-party actions pinned appropriately
- [ ] Base container images pinned/scanned and updated deliberately
- [ ] SBOM generated for production artifacts where required/useful

See [`./supply-chain.md`](./supply-chain.md) for package-manager-specific install-script policy and commands.

## Infrastructure & Deployment

- [ ] Production debug/development modes disabled
- [ ] Services run as non-root where practical
- [ ] Containers drop unnecessary Linux capabilities
- [ ] Container/root filesystem read-only where practical
- [ ] Only required ports/services exposed
- [ ] Internal services not publicly reachable without a reason
- [ ] Inbound and outbound network access follows least privilege
- [ ] Application, migration, and administrative database roles separated where practical
- [ ] Production IAM/service accounts follow least privilege
- [ ] Base images and OS packages patched/scanned
- [ ] Images/artifacts immutable and preferably signed/provenanced
- [ ] Secrets never baked into container images/layers
- [ ] Production startup fails when mandatory secure configuration is missing
- [ ] Default credentials/demo endpoints/sample admin accounts removed

## Logging & Monitoring

- [ ] Authentication failures and important authentication events logged
- [ ] Authorization failures logged without leaking sensitive data
- [ ] Privileged/admin operations logged
- [ ] Credential/API-key creation, rotation, and revocation logged
- [ ] Destructive/high-impact operations logged
- [ ] Security-relevant configuration changes logged
- [ ] Logs contain request/correlation IDs where useful
- [ ] Logs never contain passwords, auth tokens, secrets, or unnecessary sensitive payloads
- [ ] Security events generate alerts where appropriate
- [ ] Logs protected from unauthorized modification/deletion
- [ ] Log retention and access policy defined
- [ ] Agent tool calls, approvals, and high-impact actions are auditable

## Security Testing

- [ ] Authorization tests include cross-user and cross-tenant negative cases
- [ ] Security-sensitive behavior has explicit "must not be able to" tests
- [ ] Secret scanning runs in CI
- [ ] Dependency vulnerability scanning runs in CI
- [ ] SAST runs on relevant code changes
- [ ] Container images scanned when containers are shipped
- [ ] IaC scanned when infrastructure-as-code is used
- [ ] DAST used for externally exposed applications where appropriate
- [ ] Complex parsers/input handlers fuzzed where risk justifies it
- [ ] High/critical findings block release unless explicitly risk-accepted
- [ ] Security regression tests added after security incidents/bugs

## Failure & Exceptional Conditions

- [ ] Security checks fail closed, not open
- [ ] Transactions roll back on partial failure where consistency/security requires it
- [ ] Locks, temporary credentials, files, connections, and leases released/expired safely
- [ ] Timeouts configured for network and external-service calls
- [ ] Retries bounded and use backoff/jitter where appropriate
- [ ] Retries do not duplicate irreversible operations
- [ ] Partial failures cannot bypass authorization, validation, or accounting
- [ ] Missing mandatory configuration causes startup failure rather than insecure fallback
- [ ] Unexpected exceptions return generic external errors and useful internal diagnostics
- [ ] Resource exhaustion/queue saturation has defined behavior

Example external error:

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Something went wrong"
  }
}
```

Never expose raw stack traces, SQL, internal paths, credentials, or provider internals to untrusted clients.

## AI / LLM Security

For any feature that calls an LLM (chatbots, summarizers, agents, RAG):

- [ ] Model output treated as untrusted data
- [ ] Prompt injection assumed; authorization and business rules enforced outside the model
- [ ] Indirect prompt injection assumed from documents, websites, emails, tool output, retrieved content, and other agents
- [ ] Secrets, cross-tenant data, and unnecessary system/developer instructions kept out of model context
- [ ] Structured model output validated against a strict schema before use
- [ ] Model-produced SQL, shell, URLs, HTML, code, paths, and identifiers validated/sandboxed before execution/use
- [ ] Safety/security controls remain effective if the model ignores instructions
- [ ] Token, request-rate, execution-time, tool-call, recursion, and monetary budgets enforced
- [ ] Model/provider fallback does not silently weaken required security or data-handling guarantees
- [ ] Sensitive prompts/completions have explicit retention/logging policy

## RAG / Retrieval Security

- [ ] Authorization applied before or during retrieval, not after generation
- [ ] Tenant/user/document scope enforced by application/database controls
- [ ] Vector stores/embedding namespaces cannot leak cross-tenant data
- [ ] Retrieved documents treated as untrusted data/instructions
- [ ] Document provenance/source metadata retained
- [ ] Documents validated before indexing
- [ ] Poisoned/malicious documents can be quarantined, deleted, and re-indexed
- [ ] Retrieval filters cannot be overridden by model-generated text alone
- [ ] Citations/provenance included where correctness or auditability matters
- [ ] Embedding/index deletion is included in tenant/user data-deletion workflows where required

## Agent & Tool Security

- [ ] Tool arguments validated independently of model output
- [ ] Tool authorization checked at execution time
- [ ] Tools expose minimum required capabilities and data
- [ ] High-impact/destructive/irreversible actions require deterministic policy checks and/or human approval
- [ ] Agent-generated shell/code runs only in an appropriately isolated sandbox
- [ ] Browser/network-enabled agents have restricted egress where practical
- [ ] Tool/API credentials are scoped per tool/service, not shared broadly
- [ ] Agent loops have hard termination conditions
- [ ] Tool-call count, wall-clock time, concurrency, and monetary spend bounded
- [ ] Untrusted tool output cannot automatically redefine agent policy/permissions
- [ ] Agent-to-agent messages treated as untrusted unless authenticated/authorized by the application
- [ ] High-impact actions produce an audit trail linking user/request, model decision, tool call, and result

See [`./ai-security.md`](./ai-security.md) for additional AI/agent guidance.

## Agent Memory

- [ ] Memory scoped per user/tenant/session
- [ ] Transient untrusted input cannot become trusted long-term memory without policy/validation
- [ ] Memory writes validated and auditable where important
- [ ] Sensitive information excluded from persistent memory unless explicitly required/protected
- [ ] Memory has retention/expiration/deletion behavior
- [ ] Retrieved memory is treated as untrusted context, not authorization or policy

## Incident Readiness

- [ ] Security owner/on-call escalation path defined
- [ ] Credential compromise procedure covers revoke/rotate/redeploy as needed
- [ ] Ability to disable affected API keys, integrations, tools, agents, or endpoints quickly
- [ ] Audit/log data sufficient to determine affected users/tenants/actions
- [ ] Backup/restore and critical recovery paths tested
- [ ] Vulnerability disclosure/contact path defined where appropriate
- [ ] Post-incident actions include regression tests and control updates

## OWASP Top 10:2025 Quick Reference

See [OWASP Top 10:2025](https://owasp.org/Top10/2025/).

| ID | Risk | Primary checks in this file |
|---|---|---|
| A01 | Broken Access Control | Authorization, API Security, CSRF, tenant isolation |
| A02 | Security Misconfiguration | Browser Security, Infrastructure & Deployment, fail-secure defaults |
| A03 | Software Supply Chain Failures | Dependency & Supply-Chain Security, CI security |
| A04 | Cryptographic Failures | Authentication, Data Protection, Secrets & Key Management |
| A05 | Injection | Input Validation, File Handling, AI output validation |
| A06 | Insecure Design | Threat Modeling, abuse cases, architecture/security boundaries |
| A07 | Authentication Failures | Authentication, session management, MFA, rate limits |
| A08 | Software or Data Integrity Failures | Supply chain, provenance/signing, webhook authenticity, untrusted data |
| A09 | Security Logging and Alerting Failures | Logging & Monitoring, audit trails, alerts |
| A10 | Mishandling of Exceptional Conditions | Failure & Exceptional Conditions, fail-closed behavior |

## OWASP Top 10 for LLM Applications:2025

See the [OWASP GenAI Security Project](https://genai.owasp.org/llm-top-10/).

| ID | Risk | Prevention focus |
|---|---|---|
| LLM01 | Prompt Injection | Treat instructions/content as untrusted; enforce permissions outside prompts |
| LLM02 | Sensitive Information Disclosure | Minimize context, protect secrets/PII, control logging/retention |
| LLM03 | Supply Chain | Vet models, datasets, plugins/tools, packages, and providers |
| LLM04 | Data and Model Poisoning | Validate provenance; control ingestion/fine-tuning/RAG data |
| LLM05 | Improper Output Handling | Validate, parameterize, encode, sandbox |
| LLM06 | Excessive Agency | Least-privilege tools, approvals, deterministic policy, bounded autonomy |
| LLM07 | System Prompt Leakage | Assume prompts can leak; never store secrets/security boundaries only in prompts |
| LLM08 | Vector and Embedding Weaknesses | Tenant isolation, document validation, scoped retrieval/deletion |
| LLM09 | Misinformation | Ground important claims, provenance/citations, verification/human review where needed |
| LLM10 | Unbounded Consumption | Cap tokens, rates, loops, tools, concurrency, time, and spend |

## References

- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)
- [OWASP Top 10:2025](https://owasp.org/Top10/2025/)
- [OWASP API Security Top 10](https://owasp.org/API-Security/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [OWASP GenAI Security Project](https://genai.owasp.org/)
- See [AI / Agent Security](./ai-security.md) for deeper guidance.
- See [Supply Chain Security](./supply-chain.md) for package-manager-specific guidance.
