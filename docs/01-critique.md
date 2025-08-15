## CloudFlow v0 Contract — Critique

### Strengths
- **Typed-first I/O (Pydantic v2)**: Keeps boundaries explicit; great DX with FastAPI integration and OpenAPI derivation.
- **Code as the contract**: Python remains the single source; YAML and routers are derived → fewer drift issues.
- **Simple DSL (`>>`)**: Sequential composition is easy to read; lean surface area for v0.
- **Adapters via `AssignStep`**: Avoids extra HTTP hops for pure data mapping and compiles to native Workflows `assign`.
- **Infra-native steps**: `HttpStep`, `GoogleApiStep`, `PubSubPublishStep` align with Workflows primitives; leverages OIDC and connectors.
- **Deterministic builds**: Intent to produce stable names enables repeatability and cacheability.

### Risks and Gaps
- **Type continuity strictness**: Exact model match between steps is too rigid. Real flows often need structural compatibility (subset/superset, field transforms). Relying only on manual `AssignStep`s can be noisy. Consider schema-compat checks and safe auto-adapters for trivial renames/copies.
- **Context vs YAML expressions**: Clear separation is needed: what belongs to runtime `Context` vs compile-time YAML expressions (`Arg`). Ensure we don’t promise `Arg.ctx()` compilation unless explicitly mapped.
- **Retry semantics parity**: Workflows retries support `retry` with predicates (e.g., `http.default_retry_predicate`) and backoff. Framework-level retries must not double-conflict. Provide defaults per transport and forbid nested retries unless opted-in.
- **Branching UX**: Conditions as raw expression strings are error-prone. Prefer a tiny expression builder (`Arg`) or typed predicates to reduce `${...}` stringly-typed mistakes.
- **Parallel/fan-in semantics**: v0.1 proposes `.parallel`/`.foreach`. Need clear variable scoping, shared accumulators, and join semantics that map 1:1 to Workflows `parallel` without surprises.
- **Deterministic naming**: Define stable step ids: kebab-case of function name + short content hash of signature and metadata. Document collision rules and human-overrides.
- **Local execution parity**: In-process execution can diverge from Workflows (retries, timeouts, auth). Consider the alternative: always call via HTTP locally for parity (slower dev loop, simpler semantics), behind a `--http-local` flag.
- **Security defaults**: Must provide first-class OIDC for Cloud Run targets, principled handling of third-party auth, and Secret Manager usage patterns. Avoid bespoke header injection in user code; provide ergonomic, explicit config.
- **Observability**: Minimal plan mentions request id; we should add structured logging fields, timing, and a consistent header/attr propagation contract across Python and YAML edges.
- **Limits/quotas awareness**: Enforce guardrails for payload sizes, timeouts, number of steps, and variable sizes. Provide guidance to offload large payloads to GCS and pass pointers.

### Suggestions
- **Schema adapters**: Add a declarative `ModelAdapter[In,Out]` that compiles to `assign`, generated from typed field mapping objects (safer than expression strings). Keep an escape hatch to raw expressions.
- **Default policies**: `RetryPolicy.idempotent_http()` with `http.default_retry_predicate`; sane timeouts per transport; per-step `idempotent: bool` to gate retries.
- **Validation layers**: Build-time: type/graph validation + name stability checks; Runtime: Pydantic input/output validation; YAML lint; snapshot tests for generated YAML.
- **Config**: CLI flags plus a small `cloudflow.toml` to set `env` mappings, base URL, service account audiences, and global retry defaults.
- **Testing**: Golden-file tests for YAML; contract tests for generated FastAPI routers; e2e “hello world” using Workflows execution client in CI (optionally mocked).

### Competitive calibration
- **Temporal**: Strong typed workflows but code-exec model; CloudFlow’s value is compiling to managed Workflows + typed Python steps for business logic.
- **AWS Step Functions**: Comparable YAML-first; our edge is Python typing + codegen + adapters.
- **Airflow/Prefect/Dagster**: General orchestration; our narrow focus on GCP Workflows primitives + FastAPI keeps it simpler.

### Verdict
Great foundation: small, typed, and pragmatic. The main risks are mismatch between Python local mode and Workflows semantics, plus ergonomics around mapping and retries. Address with adapters, policy presets, strict codegen validation, and opinionated defaults.


