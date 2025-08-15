## Roadmap

### v0 (MVP)
- Core: decorator, types, registries, validation, `Arg`.
- DSL: `workflow(name) >> step >> step`.
- Codegen: sequential YAML (`assign`, `http`, minimal `switch`, `try/retry/except`).
- Routers: per-step + per-workflow run; in-process execution.
- Infra steps: `HttpStep`, `GoogleApiStep`, `PubSubPublishStep`, `AssignStep`.
- CLI: `build`, `serve`, `validate`, `graph`.
- Docs and e2e sample with golden YAML tests.

### v0.1
- `.parallel`, `.foreach` with shared accumulators and concurrency limit.
- Retry presets and error taxonomy docs.
- JSON Schema emission for models.
- Optional unified `ActionStep(transport=...)` exploration.

### v0.2
- Sub-workflows.
- Secrets/KMS helpers and policy presets.
- Metrics endpoints and tracing headers.
- Workflows execution client and local parity improvements.


