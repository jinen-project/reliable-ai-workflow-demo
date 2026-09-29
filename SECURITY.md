# Security boundary

- local-only synthetic fixtures
- no real credentials or customer data
- API key is read from `DEMO_API_KEY` only and is never returned by the tool
- read-only MCP-shaped adapter exposes no write method
- approval is explicit and role checked
- actions use stable idempotency keys
- local mail acceptance is not recipient engagement
- provider authentication, authorization scopes, retention, and threat-model review remain production work

