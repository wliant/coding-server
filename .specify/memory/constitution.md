<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0
Modified principles: None
Added sections:
  - Core Principles: VI. API-First with OpenAPI (new principle)
Removed sections: None
Templates requiring updates:
  - .specify/templates/plan-template.md  ✅ Constitution Check section is generic; compatible
  - .specify/templates/spec-template.md  ✅ No changes required
  - .specify/templates/tasks-template.md ✅ No changes required; OpenAPI/codegen tasks
      will be captured in feature-specific tasks.md files as part of setup phases
  - .specify/templates/agent-file-template.md ✅ No principle references to update
Follow-up TODOs:
  - None — all fields resolved.
-->

# Coding Machine Constitution

## Core Principles

### I. Simplicity-First

Every solution MUST begin at the simplest form that satisfies the current
requirement. Complexity MUST be introduced only when a simpler alternative is
demonstrably insufficient. YAGNI (You Aren't Gonna Need It) applies at all
levels: features, abstractions, configuration, and infrastructure.

Rationale: Unnecessary complexity increases maintenance burden, slows onboarding,
and hides defects. Complexity that cannot be justified in a Complexity Tracking
table (see plan template) MUST be removed.

### II. Test-Driven Development (NON-NEGOTIABLE)

Tests MUST be written before implementation code. The Red-Green-Refactor cycle
MUST be followed: write a failing test → confirm it fails → implement the minimum
code to make it pass → refactor while keeping tests green.

Tests MUST be independently runnable per user story. A feature is not complete
until all its acceptance scenarios pass and no previously passing tests regress.

Rationale: Tests written after implementation tend to confirm code, not behaviour.
Upfront tests enforce clear requirements and provide a safety net for refactoring.

### III. Modularity & Single Responsibility

Each module, package, or service MUST have a single, clearly stated purpose.
Inter-module dependencies MUST be explicit and minimal. Shared schemas and
contracts MUST be versioned and documented in `contracts/`.

No module MUST depend on implementation details of another module; it MUST depend
only on published interfaces or contracts.

Rationale: Tight coupling makes independent testing and incremental delivery
impossible. Loose coupling via contracts enables parallel development and safe
refactoring.

### IV. Observability

Every non-trivial operation MUST emit structured log entries at an appropriate
level (DEBUG, INFO, WARN, ERROR). Error paths MUST log actionable context
(what failed, why, and what the caller can do about it). Sensitive data (PII,
credentials) MUST NOT appear in logs.

Rationale: Systems that cannot be observed cannot be debugged in production.
Structured logs enable automated alerting and post-incident analysis.

### V. Incremental & Independent Delivery

Features MUST be broken into user stories that are each independently
implementable, testable, and deliverable as an MVP increment. No user story
SHOULD block delivery of another user story's core value. Work MUST be committed
in small, reviewable increments (one logical change per commit).

Rationale: Large, monolithic releases accumulate risk and delay feedback. Small
increments surface integration issues early and allow course-correction.

### VI. API-First with OpenAPI (NON-NEGOTIABLE)

Every REST API MUST be described by an OpenAPI specification document before any
implementation begins. The spec document MUST be the single source of truth for
request/response schemas, status codes, and authentication requirements.

Client and server stubs MUST be generated from the OpenAPI spec using a suitable
code generator (e.g., openapi-generator, oapi-codegen, FastAPI's schema export)
whenever one is available for the target language and framework. Hand-written
client or server implementations MUST only be used when code generation is
unavailable or produces demonstrably unusable output; this exception MUST be
documented in the feature's `plan.md` Complexity Tracking table.

The OpenAPI spec file MUST be committed alongside the feature code and updated
atomically with any breaking API change. Consumer-facing changes to the spec MUST
follow semantic versioning (the `info.version` field).

Rationale: An OpenAPI-first workflow ensures the contract is explicit and
machine-readable before code exists, prevents client/server drift, and enables
automated documentation, mocking, and testing. Generated stubs eliminate an entire
class of transcription bugs between spec and implementation.

## Quality Standards

All code entering the main branch MUST pass:

- **Linting / formatting**: Project-configured linter MUST report zero errors.
- **Unit tests**: All unit tests MUST pass; coverage MUST NOT regress below the
  project-established baseline.
- **Integration tests**: Contract and integration tests relevant to changed
  modules MUST pass.
- **Peer review**: At least one reviewer MUST approve before merge (self-merge
  only permitted for trivial doc fixes on solo projects).
- **OpenAPI validation**: Any PR that modifies an API MUST include an updated and
  schema-valid OpenAPI spec (validated via linter or CI check).

Security-sensitive changes (authentication, authorisation, cryptography, external
data handling) MUST receive explicit security review commentary in the PR.

## Development Workflow

1. **Spec first**: A feature MUST have an approved `spec.md` before coding begins.
2. **Plan before coding**: `plan.md` MUST be produced (via `/speckit.plan`) and
   reviewed before tasks are generated.
3. **Task list**: `tasks.md` MUST be generated (via `/speckit.tasks`) and
   dependency-ordered before implementation starts.
4. **Story-by-story delivery**: Implement, test, and validate each user story
   before starting the next.
5. **Constitution check**: Every `plan.md` MUST include a Constitution Check
   section confirming compliance with this document before Phase 0 research.
6. **API contract before code**: For any REST API feature, the OpenAPI spec MUST
   be authored and reviewed as the first implementation task; stubs MUST be
   generated before any business logic is written.

## Governance

This constitution supersedes all other informal practices and verbal agreements.
Amendments MUST be:

1. Proposed as a pull request modifying this file.
2. Accompanied by a rationale explaining the problem the amendment solves.
3. Reviewed and approved by at least one other project contributor (or the
   project owner on solo projects).
4. Applied with a version bump per the semantic versioning policy below.

**Versioning policy**:
- MAJOR bump — principle removed, renamed, or fundamentally redefined.
- MINOR bump — new principle or section added; material expansion of guidance.
- PATCH bump — clarification, wording refinement, or typo fix.

All PRs and code reviews MUST verify compliance with the Core Principles above.
Unjustified complexity MUST be flagged and resolved before merge. Runtime
development guidance lives in the agent file generated by `/speckit.plan`.

**Version**: 1.1.0 | **Ratified**: 2026-03-02 | **Last Amended**: 2026-03-02
