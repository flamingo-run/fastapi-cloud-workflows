## MVP Scope (v0)

### Deliverables
- **Core**: `@step` decorator, `workflow(name) >> a >> b` DSL, registries, validation.
- **Codegen**:
  - YAML for sequential workflows: `assign`, `http.(get|post)`, minimal `switch`, `try/retry/except`.
  - FastAPI routers: per-step `POST /steps/{step_name}`, per-workflow `POST /wf/{name}/run` with in-process execution.
- **Infra steps**: `HttpStep`, `GoogleApiStep`, `PubSubPublishStep`, `AssignStep`.
- **Adapters**: `ModelAdapter[In,Out]` with safe mapping → YAML `assign` (escape hatch for raw expressions).
- **CLI**: `build`, `serve`, `validate`, `graph` (Mermaid).
- **DX**: Deterministic names, helpful errors.
- **Docs**: Examples and guardrails.

### Non-goals (v0)
- Parallelism (`parallel`, `foreach`) beyond a placeholder API.
- Sub-workflows, compensation/sagas.
- Per-step custom auth policies beyond common presets.

### Opinionated defaults
- **Retries**: `idempotent_http()` preset using `http.default_retry_predicate`, backoff 1s→30s, 5 tries.
- **Timeouts**: 30s default for HTTP unless overridden.
- **Headers**: Propagate `X-Request-Id`, `X-Env` by default.
- **Local parity**: `--http-local` optional mode to call endpoints via HTTP even locally.

### Acceptance checks
- End-to-end example (`order-flow`) builds deterministic YAML and routers.
- Local `serve` executes flow and matches YAML behavior for success/validation errors.
- Golden-file tests for YAML; pydantic validation fires on every edge.


