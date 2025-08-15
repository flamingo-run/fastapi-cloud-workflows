## Spec: Policy Presets (Retries, Timeouts, Idempotency)

### Defaults
- Retries happen in Workflows by default using:
  - `predicate: ${http.default_retry_predicate}`
  - `max_retries: 5`
  - `backoff: { initial_delay: 1, max_delay: 30, multiplier: 2.0 }`
- Default HTTP timeout: 30 seconds.
- Python-level retries: disabled by default. If enabled for a step, YAML retries are disabled for that step.

### Idempotency
- Steps that perform side effects SHOULD declare `idempotent: true/false`.
- Retry presets only auto-apply when `idempotent: true` or when using connectors that are known to be idempotent.

### Mapping to YAML
```yaml
- call_service:
    try:
      call: http.post
      args: { url: ${env.SVC_URL}, body: ${payload}, auth: { type: OIDC, audience: ${env.AUD} } }
      retry:
        predicate: ${http.default_retry_predicate}
        max_retries: 5
        backoff: { initial_delay: 1, max_delay: 30, multiplier: 2.0 }
      result: r
    except:
      as: e
      steps:
        - rethrow: { raise: ${e} }
```

### Overrides
- Per-step overrides for timeout and retry counts are supported and validated.
- Global defaults configurable via CLI flags and/or `cloudflow.toml` (future).


