# Project Context Introduction

*Reusable AI code generation evaluated through a local messaging system*

This document initializes the project context for an AI coding agent. The project is to build a reusable, reproducible generator that produces working client applications from a written specification. A small local messaging system provides the concrete example used to demonstrate and evaluate that generator.

## Source of truth

The authoritative presentation brief is [`docs/brief/aware-test-brief.md`](brief/aware-test-brief.md) (transcribed from the original `Aware test.rtf`). It defines the evaluation focus, required messaging behavior, constraints, deliverables, and regeneration expectations.

Behavior questions are resolved by the written specification in [`spec/`](../spec/), not by inferring behavior from implementation code.

This context introduction organizes the brief and adds the requester's preferred implementation direction. If a later architecture choice conflicts with an explicit evaluation constraint in the brief, preserve the brief's constraint and document the decision in [`docs/decisions/`](decisions/).

## Project objective

Create an agentic code-generation harness that can take a written, evolving specification and reliably generate client code. The generator is the central deliverable; the messaging application is its evaluation example. The result should be reproducible: deleting the marked generated client code and running the documented generator should recreate clients that satisfy the specification.

## Example system

A minimal local messaging system with a small server and two clients implemented in different languages. The clients communicate through the server and exhibit identical behavior for scenarios defined by the specification.

- **Identity:** on first launch, a user identifies themselves by name.
- **Send:** a user sends a text message addressed to another named user.
- **Offline queue:** outgoing messages are retained locally while the client is offline and sent after reconnection.
- **Receive:** clients display messages received from the server, including messages queued for a recipient while that recipient was offline.
- **Interoperability:** both client implementations follow the same protocol and observable behavior.

The specification must define enough detail to make ordering, delivery, reconnection, and message visibility unambiguous. It must cover the Alice and Bob offline/reconnect sequence in the brief (see [`spec/scenarios/alice-bob-offline.md`](../spec/scenarios/alice-bob-offline.md)).

## Preferred implementation direction

### Android client (Kotlin)
Complete Android application in Kotlin and Jetpack Compose, following current Google Android guidance. Coroutines for async work, Hilt for dependency injection, Retrofit for server communication. Scalable multi-module project with clear feature and shared-data boundaries, including at minimum login, chat, and a networking/data API module (or equivalent).

### Web client
Widely adopted, maintainable community stack. Modular, feature-oriented structure with clear boundaries between UI, domain behavior, and server/data access. Specific tools are selected based on project needs and the choice is documented (see `docs/decisions/`).

### Local server (Python)
Concise local server supporting communication between the Android emulator and the web client. Small responsibilities, clear separation. In-memory, single-process is sufficient; cloud services, durable persistence, authentication/security hardening, and production-scale abuse prevention are out of scope.

## Architecture and quality expectations

- Apply SOLID principles and clean architecture consistently, scaled to the size of each component.
- Keep protocol and behavior rules in an explicit, platform-neutral specification; no client implementation becomes the source of truth.
- Mark generated code and hand-written code clearly, and explain the regeneration boundary in the README.
- Include tests that demonstrate protocol behavior, offline queueing and flushing, and client/server interoperability.
- Keep the generator reusable as specifications evolve to include additional capabilities such as attachments, reactions, or group conversations.

## Generator and delivery expectations

- Use Claude Code or Codex as the agentic coding tool so the generation process can be evaluated reproducibly.
- No turnkey messaging SDKs. General-purpose HTTP, WebSocket, JSON, and local-storage libraries are acceptable; the messaging protocol and offline behavior must be specified and implemented by the project.
- Entire demonstration is local and reproducible in a sandbox, without cloud or third-party services.
- Deliver repository or repositories with a README that identifies the agentic harness, authoritative specification, generator command and tool, generated client code, and regeneration boundary.
- Meaningful commit history showing the development process, not a single final-output commit. A design document and agent setup files (such as `AGENTS.md`) make the design and agent workflow understandable.
- A future-work note (`FUTURE.md`) is optional.

## AI workflow and orchestration

A main orchestrator acts as technical manager and the user's direct point of contact. It maintains the plan, tracks adherence, and launches specialized agents with scoped context, requirements, and boundaries. It integrates and reviews their results against the shared specification and plan. Detailed agent prompts, handoffs, and pipeline mechanics will be defined in a later workflow design (placeholder: [`generator/WORKFLOW.md`](../generator/WORKFLOW.md)).

## Working principles

1. Read the source brief and the current specification before changing behavior or architecture.
2. Treat the specification as authoritative; update it when requirements change, then regenerate and verify affected clients.
3. Prefer explicit, testable contracts and repeatable commands over assumptions embedded in prompts or code.
4. Keep implementation choices proportionate: the server is intentionally small, while protocol clarity and reliable generation receive the most attention.

## Changes from the original context document

- Brief now lives at `docs/brief/aware-test-brief.md` instead of a root-level `Aware test.rtf` (converted to Markdown so agents and diffs can read it).
- Added links to the concrete folders in this repo.
- Brief's `FUTURE.md` deliverable name used consistently.
