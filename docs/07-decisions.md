## Adopted Decisions (v0)

- **Adapters: `ModelAdapter[In,Out]`**
  - Provide a typed field-mapping adapter that compiles to Workflows `assign`.
  - Keep an escape hatch for raw `${...}` expressions where needed.

- **Retry/timeout policy presets**
  - Default: retries occur in Workflows YAML, not in Python runtime.
  - Provide `RetryPolicy.idempotent_http()` using `http.default_retry_predicate`, 5 attempts, backoff 1→30s, multiplier 2.0.
  - Default HTTP timeout 30s; explicit override per step allowed.
  - Python-level retries are off by default; enabling them disables YAML retries for that step.

- **Deterministic naming**
  - Default step id: `kebab-case(function_name)`.
  - Stability: append short hash derived from signature + input/output schemas + metadata.
  - Human `name=` overrides are respected; collisions raise a validation error with guidance.

- **Context vs YAML expressions**
  - `Arg.env()` and `Arg.param()` compile to Workflows `${...}`.
  - `Arg.ctx()` is runtime-only; only compiles to YAML when explicitly mapped in step config (e.g., headers/attributes).

- **Local execution modes**
  - Default local mode runs Python steps in-process for speed.
  - `--http-local` flag forces local HTTP calls to generated endpoints for higher parity.
  - CI integration tests favor HTTP-local mode.

- **Observability defaults**
  - Propagate `X-Request-Id` header and include `env` header by default.
  - Structured logs: include workflow/step name, attempt number, duration.

- **Build-time guardrails**
  - Validate against key Workflows quotas (e.g., step count, payload hints, timeouts) and emit guidance.
  - Recommend storing large payloads in GCS and passing references.

- **Security defaults**
  - OIDC for Cloud Run/Functions by default; per-step audience override.
  - Third-party HTTP supports raw `Authorization` or OAuth2.
  - Secrets sourced via Secret Manager or environment; no inline secrets in YAML.

- **Branching ergonomics**
  - Prefer `Arg` or typed predicate helpers over raw condition strings.

- **Parallel semantics (v0.1)**
  - `.parallel`/`.foreach` compile 1:1 to Workflows with explicit shared state, concurrency limit, and deterministic join semantics.


