# Public demo local review

Checked locally on 2026-09-29.

```ini
PUBLIC_DEMO = RUNNABLE
LOCAL_ONLY_MODE = YES
PAID_SERVICE_REQUIRED = NO
REAL_CREDENTIAL_REQUIRED = NO
SCENARIO_A = VERIFIED
SCENARIO_B = VERIFIED
SCENARIO_C = VERIFIED
FAILURE_INJECTION = YES
PROCESS_RESTART_DEMO = YES
READBACK_DEMO = YES
AUDIT_TIMELINE = YES
MULTIPLE_VIEWS = YES
ONE_COMMAND_VERIFY = YES
PUBLIC_SECRETS = 0
PRIVATE_CLIENT_DATA = 0
LOCAL_ABSOLUTE_PATHS = 0
GITHUB_READY = YES
PRODUCTION_READY = NO
```

`make verify` passes with the standard Python runtime and no pytest or network dependency. The local web viewer is provided by `make demo`; binding a listening socket is host-permission dependent, so the CLI is the authoritative verification path in restricted environments.

The repository contains only synthetic fixtures and generic public-demo language. No prior challenge repository or private application record is copied into it.

