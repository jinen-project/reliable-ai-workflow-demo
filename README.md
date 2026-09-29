# Reliable AI Workflow Demo

A runnable demo for reliable AI-assisted workflows.

It shows how to:

- preserve source evidence
- separate AI claims from verified state
- require authorization where needed
- verify external actions with readback
- survive failures and process restarts
- reconstruct what happened afterwards

## 30-second architecture

```text
synthetic input → durable state → bounded decision → local adapter
                                      ↓
                              readback + timeline
```

## Run locally

Requirements: Python 3.11+ and pytest. No account, credential, network, or paid service is required.

```bash
make verify
make demo
```

The UI is intentionally small. The CLI is the source of truth:

```bash
PYTHONPATH=. python3 demo.py a   # human approval
PYTHONPATH=. python3 demo.py b   # read-only MCP-shaped tool
PYTHONPATH=. python3 demo.py c   # response-loss recovery after restart
PYTHONPATH=. python3 demo.py d   # AI business-automation recovery
```

## Try four scenarios

### A — Human approval

An AI recommendation is recorded as a claim. An unauthorized actor is blocked; an explicit reviewer approval permits a local external action, and a readback marks it verified.

### B — Read-only MCP tool

A user query calls a synthetic read-only tool and returns stable JSON. No write tool exists. A real Claude host is optional and not required for this local demo.

### C — Async recovery

The external action is committed, its response is lost, and the process is closed. A fresh process reads durable state back, verifies the prior action, and prevents duplicate execution.

### D — AI business-automation recovery

Added as a public-job-shaped fixture without assuming a particular CRM, WhatsApp provider, or predictive model. A synthetic inbound request is validated, classified/scored by a deterministic local fixture, routed, written to a mock CRM, sent to a local notification sink, and verified by readback. The scenario injects response loss and resumes after a fresh process; the same action identity prevents a duplicate CRM side effect.

```text
inbound → validation → reference scoring → routing → mock CRM
        → local notification → failure → bounded retry → readback → verified
```

`REFERENCE_SCORING_ONLY = YES`. The client's predictive model, CRM, WhatsApp provider, schemas, credentials, and production acceptance criteria remain unresolved.

## Break it on purpose

The scenario runner contains controlled response-loss, timeout, rate-limit, notification-failure, malformed-AI, and duplicate-inbound fixtures. Scenarios C and D demonstrate failure/restart recovery. The runtime also records duplicate-action blocking and unauthorized approval.

## What is verified vs simulated

Verified locally: authority boundary, read-only capability, durable state, action/readback separation, response-loss recovery, duplicate blocking, audit timeline, regenerated views, deterministic reference classification, mock CRM/notification adapters, bounded retry, ambiguous-result recovery, and process restart recovery.

Simulated: all people, payloads, providers, credentials, business rules, and external systems. This is a reference implementation, not production-ready software, compliance certification, or a universal workflow engine.

## Production integration points

Per-client changes are expected for API endpoints, schemas, credentials, business rules, approval policy, provider mappings, and acceptance criteria. Replace the local adapters without promoting fixture success into a customer outcome.

## Repository map

```text
core/       durable runtime and projections
patterns/   documented reusable patterns (no new primitive)
adapters/   local MCP-shaped, CRM, and mail boundaries
scenarios/  four synthetic demonstrations
ui/         small local viewer
tests/      executable verification
```
