# Architecture

The demo is deliberately small and local.

```text
input receipt → SQLite durable state → scenario decision
                                      ↘ adapter action → readback
                                      ↘ operator/reviewer/audit projection
```

The implementation uses ordinary records and relationships; it does not add a new durable state primitive. The patterns shown are extracted from three independently implemented workflow challenges, not claimed as a universal model.

