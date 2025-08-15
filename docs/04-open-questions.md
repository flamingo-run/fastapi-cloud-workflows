## Open Questions

- **Local execution parity**: Should `serve` invoke Python steps in-process or always via HTTP even locally for parity? Proposal: support both, default to in-process; `--http-local` for parity.
- **Type compatibility**: Keep exact `Out == In` in v0, or allow structural compatibility with auto-generated adapters for trivial field copies/renames?
- **Retry layering**: How to prevent conflicting retries between Workflows and Python runtime? Proposal: retries in YAML by default; Python retries opt-in and mutually exclusive.
- **Secrets**: Standardize Secret Manager usage in YAML vs runtime; how do we thread secrets to HTTP steps safely?
- **OIDC audience defaults**: Global default vs per-step override? Source of truth and validation.
- **Quotas/limits enforcement**: Which limits do we validate at build time (payload size, steps, timeouts)? How to guide users to offload large payloads to GCS.
- **Error taxonomy**: Exact mapping of validation/runtime errors to HTTP status codes in FastAPI and to Workflows `raise` semantics.
- **Parameters**: When to introduce workflow parameters and how to surface them in the DSL.
- **Name hashing**: Hash inputs: function bytecode or signature + model schemas? How to balance stability and change detection.
- **Expression safety**: How far should `Arg` go before it becomes a DSL that hides Workflows? Keep explicit escape hatches to raw `${...}`.


