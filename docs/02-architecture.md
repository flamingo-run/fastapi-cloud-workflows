## Architecture (v0)

### Modules
- **`cloudflow.core`**: `Step` and `Workflow` types, decorators, registries, validation, `RetryPolicy`, `Context`, `Arg` expression builder.
- **`cloudflow.codegen`**: `workflows.py` (YAML emitter), `fastapi.py` (routers + endpoints generation), deterministic naming.
- **`cloudflow.runtime`**: FastAPI app factory, context middleware, error handlers, health endpoints.
- **`cloudflow.cli`**: `build`, `serve`, `validate`, `graph`.

### Key types (sketch)
```python
InT = TypeVar("InT", bound=BaseModel)
OutT = TypeVar("OutT", bound=BaseModel)

class Context(BaseModel):
    request_id: str
    timestamp: datetime
    env: Literal["dev", "stg", "prod"]

@dataclass
class RetryPolicy:
    max_retries: int
    initial_delay_s: float = 1.0
    max_delay_s: float = 30.0
    multiplier: float = 2.0
    predicate: Literal["http.default_retry_predicate", "always", "never"] = "http.default_retry_predicate"

class Step(Generic[InT, OutT]):
    name: str
    input_model: type[InT]
    output_model: type[OutT]
    fn: Callable[[Context, InT], Awaitable[OutT]] | None  # None for infra-native steps
    retry: RetryPolicy | None
    timeout: timedelta | None
    tags: set[str]

class Workflow:
    name: str
    nodes: list[Step[Any, Any]]
```

### Deterministic naming
- Default: `kebab-case(function_name)`.
- Stability: Append short hash of `signature + input_schema + output_schema + metadata`.
- Human override with `@step(name=...)` wins; collision detection errors out with guidance.

### Expression builder `Arg`
- `Arg.env("KEY")` → `${sys.get_env("KEY")}`
- `Arg.param("path.to")` → `${params.path.to}` (for future parameters support)
- `Arg.ctx("request_id")` → runtime propagation only unless explicitly mapped to headers/attributes.
- Safe concatenation (`/`) for URLs and `+` for strings.

### Code generation
- **YAML**: Each Python step → `http.post` call to generated FastAPI step endpoint; adapters → `assign`; infra-native steps → `http`/`googleapis`/`pubsub` connectors.
- **Routers**: One router per workflow with `POST /wf/{workflow}/run` and `POST /steps/{step}`. Request/response models from Pydantic v2 types.
- **Validation**: Build-time checks (type continuity, DAG connectivity, cycles, name collisions). Emit helpful errors with pointers to offending edges.

### Security and auth
- **Cloud Run**: Use Workflows `http` with OIDC. Audience configured per step or via defaults.
- **Third-party HTTP**: Raw `Authorization` header or OAuth2 depending on provider; secrets sourced from Secret Manager or environment.
- **Google APIs**: Use `googleapis` connector where possible.

### Observability
- Correlation id propagation: header `X-Request-Id` for HTTP; Pub/Sub attributes include `request_id`.
- Structured logs with step/workflow name, attempt, timings.
- Minimal metrics hooks; Prometheus later.

### ModelAdapter
- Typed mapping construct `ModelAdapter[In,Out]` for structural transforms.
- Backed by a safe mapping object (fields, constants, nested paths) → emits YAML `assign`.
- Supports raw `${...}` expressions for advanced cases.

### Adopted defaults
- Retries live in YAML by default using `http.default_retry_predicate` (5 tries, 1→30s, x2).
- Python-level retries disabled unless explicitly enabled (mutually exclusive with YAML retries).
- Default HTTP timeout 30s; explicit override per step.
- Headers propagated by default: `X-Request-Id`, `X-Env`.

### Build-time guardrails
- Validate graph shape (cycles, disconnections), type continuity, name stability/collisions.
- Validate against Workflows quotas where feasible; warn on large payload risks.
- Guidance to externalize large payloads to GCS and pass URIs.


