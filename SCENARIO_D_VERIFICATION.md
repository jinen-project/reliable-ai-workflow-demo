# Scenario D — AI Business Automation Recovery

Local verification record for the additional public demo scenario. This is a
synthetic, deterministic fixture; it does not identify or assume a client,
CRM vendor, WhatsApp provider, or predictive model.

## Flow exercised

```text
inbound customer event
→ validation
→ local classification/scoring
→ routing
→ mock CRM adapter
→ local notification adapter
→ response-loss failure
→ fresh process
→ bounded retry/readback
→ verified state
```

## Verification results

```ini
SCENARIO_D = VERIFIED
AI_CLASSIFICATION = TESTED_LOCALLY
REFERENCE_SCORING_ONLY = YES
CRM_ADAPTER = TESTED
NOTIFICATION_ADAPTER = TESTED
RETRY = TESTED
READBACK = YES
DUPLICATE_PREVENTION = YES
PROCESS_RESTART_RECOVERY = YES

MALFORMED_AI_RESULT = PRESERVED_AS_UNRESOLVED
CRM_TIMEOUT = RECOVERED_AFTER_RETRY
CRM_SUCCESS_RESPONSE_LOST = RECOVERED_BY_READBACK
NOTIFICATION_FAILURE = RECOVERED_AFTER_RETRY
RATE_LIMIT = RECOVERED_AFTER_BOUNDED_RETRY
DUPLICATE_INBOUND = REPLAY_RECOGNIZED
HUMAN_REVIEW_ROUTE = VERIFIED_FOR_HIGH_RISK_FIXTURE

CLIENT_PREDICTIVE_MODEL = UNRESOLVED
REAL_WHATSAPP = NOT_CONNECTED
REAL_CRM = NOT_CONNECTED
PRODUCTION_READY = NO
```

The executable checks are in `tests/test_demo.py` and run through `make verify`.
The existing Scenario C was retained unchanged; Scenario D is an additive
fixture and does not alter the C response-loss/restart path.

## Public-safe boundary

Only synthetic payloads and local adapters are used. No client name, project
identifier, credential, external API, WhatsApp account, or proposal content is
included.
