[![Code Coverage](https://qlty.sh/gh/flamingo-run/projects/fastapi-google-workflows/coverage.svg)](https://qlty.sh/gh/flamingo-run/projects/fastapi-google-workflows)
[![Maintainability](https://qlty.sh/gh/flamingo-run/projects/fastapi-google-workflows/maintainability.svg)](https://qlty.sh/gh/flamingo-run/projects/fastapi-google-workflows)
[![CI](https://github.com/flamingo-run/fastapi-cloud-workflows/actions/workflows/ci.yml/badge.svg)](https://github.com/flamingo-run/fastapi-cloud-workflows/actions/workflows/ci.yml)


# FastAPI Cloudflow

Typed, ergonomic Google Cloud Workflows backed by FastAPI apps.

Write typed steps as normal async functions, compose them with `>>`, and generate/deploy Cloud Workflows while the framework exposes first-class FastAPI step endpoints for you.

## Why it’s useful
- Define workflows in pure, typed Python (Pydantic IO models)
- Reuse your FastAPI app: framework attaches `/steps/<name>` endpoints automatically
- Generate stable Cloud Workflows YAML from your Python composition
- Works great with CI (codegen snapshots) and smoke tests against real GCP

## Tiny example
```python
from pydantic import BaseModel
from fastapi_cloudflow import Context, step, workflow

class CreateOrder(BaseModel):
    account_id: int
    sku: str
    qty: int

class OrderDraft(BaseModel):
    order_id: str
    status: str

class OrderPlaced(BaseModel):
    order_id: str
    status: str

@step(name="price-order")
async def price_order(ctx: Context, data: CreateOrder) -> OrderDraft:
    return OrderDraft(order_id="o-123", status="priced")

@step(name="confirm-order")
async def confirm_order(ctx: Context, data: OrderDraft) -> OrderPlaced:
    return OrderPlaced(order_id=data.order_id, status="approved")

ORDER_FLOW = (workflow("order-flow") >> price_order >> confirm_order).build()
```
- Run `fastapi-cloudflow build` and you’ll get `order-flow.yaml`
- Attach to your FastAPI app and the framework exposes `POST /steps/price-order` with typed IO

## How it works (high-level)
```mermaid
graph TD
  %% GCP runtime
  subgraph GCP
    subgraph CloudRun
      subgraph "FastAPI Server"
        subgraph "steps endpoints"
          StepCode["steps code"]
        end
        Other["other endpoints"]
      end
    end
    subgraph CloudWorkflows
      subgraph Workflow
        WFStep["Step"]
      end
    end
  end

  %% CD pipeline
  subgraph "Continuous Delivery"
    subgraph Codegen
      YAML["YAML"]
    end
    Deploy["Deployment"]
  end

  Codebase["Codebase"] --> Codegen
  Codebase --> Deploy
  Codegen --> YAML
  YAML --> Workflow
  WFStep -->|http.post| StepCode
  StepCode -->|JSON| WFStep
  Deploy --> CloudRun
```

- You write typed steps and compose with `workflow(...) >> step_a >> step_b`
- The CLI emits Cloud Workflows YAML that uses `http.post` to call the attached FastAPI step endpoints
- The framework injects a workflow context into each request (headers include name/run-id), and returns typed JSON bodies

## Try the examples
- See `examples/app/flows`: playful multi-step workflows
  - `echo_name.py` → echo-name-flow: echo → extract → shout
  - `post_story.py` → post-story-flow: build story → POST external → summarize
  - `jokes.py` → joke-flow: fetch → split → rate

## Supported features (Cloud Workflows)

| Feature | Status | Notes |
| --- | --- | --- |
| HTTP calls (http.get/post/…) | ✅ | `HttpStep`; custom headers, method |
| Auth to Cloud Run (OIDC audience) | ✅ | Python steps bake OIDC with `audience=BASE_URL` |
| Step timeouts | ✅ | `HttpStep(timeout=…)` emits seconds |
| Variables / assignment | ✅ | payload propagation + adapters/typed steps |
| Expressions (concat/env/params) | ✅ | `Arg.env/param/ctx`, string concat and path join |
| Sequential composition | ✅ | `workflow(...) >> step_a >> step_b` |
| Workflow input/output | ✅ | single `payload` param; final `return: ${payload}` |
| Error surfacing | ✅ | HTTP errors propagate; FastAPI returns typed 4xx/5xx |
| **Retries** | ✅ | `RetryPolicy` with backoff, predicates, max attempts |
| **Try/catch** | ✅ | `TryCatchStep` with exception handling and optional re-raise |

## Roadmap (Prioritized)

Priority order for upcoming features:

| Priority | Feature | Status | Notes |
| --- | --- | --- | --- |
| 1 | **Retries** | ✅ Completed | `RetryPolicy` with configurable backoff and predicates |
| 2 | **Try/catch** | ✅ Completed | `TryCatchStep` for exception handling with fallback flows |
| 3 | **Subworkflows** | 📋 Planned | Call other workflows, composition patterns |
| 4 | **GCP connectors** | 📋 Planned | Direct service calls, native Cloud Workflows connectors |
| 5 | **Deployment API** | 📋 Planned | Programmatic deployment of workflows & EventArc triggers via GCP APIs |
| 6 | **Loops** | 📋 Planned | For/while constructs, iteration over collections |
| 7 | **Conditionals / switch** | 📋 Planned | Branching logic, switch statements |
| 8 | **Parallel branches / join** | 📋 Planned | Concurrent execution, fork/join patterns |

### Deployment API (Planned)
Beyond YAML generation, the framework will provide APIs to:
- Deploy workflows programmatically to Google Cloud
- Create and manage EventArc triggers
- Configure IAM permissions and service accounts
- Orchestrate complete workflow deployment pipelines

## Next steps
- Open CONTRIBUTING.md for local setup, structure, and contribution checklist
- Use descriptive names for workflows/steps and prefer multi-step workflows that show transformations
