## Spec: Deterministic Naming

### Goals
- Stable, reproducible step and node identifiers across builds.
- Human-readable base with collision-resistant suffix.

### Algorithm
1. Base id: `kebab-case(function_name)` or explicit `name=`.
2. Canonical payload for hashing:
   - Function signature (param/return annotations, qualified name).
   - Input/Output JSON Schemas (Pydantic v2 `model_json_schema()` canonicalized: sorted keys, no descriptions/examples).
   - Step metadata: retry policy, timeout, tags, transport config, adapter mapping.
3. Serialize payload to JSON with sorted keys and normalized whitespace.
4. Hash: SHA-256 → hex; take first 8 chars.
5. Final id: `{base}-{hash8}`.

### Rules
- Explicit `name=` bypasses base generation but still receives a hash suffix.
- Collisions (same base and hash) across different steps are allowed only if payloads are identical; else build fails with a clear error.
- Provide `--no-hash` dev flag for readability in local-only builds; disabled in CI.


