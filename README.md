# fastapi-cloudflow
Typed Python-to-Google Cloud Workflows for FastAPI apps. Define steps as typed functions, compose with `>>`, generate Workflows YAML and attach endpoints to your FastAPI app automatically.

## Quickstart (uv + Python 3.13)

```bash
uv run fastapi-cloudflow serve --module app.flows.order
```

Call your workflow locally:

```bash
curl -s localhost:8000/wf/order-flow/run \
  -H 'Content-Type: application/json' \
  -d '{"account_id":1,"sku":"abc","qty":2}'
```

Emit YAML:

```bash
uv run fastapi-cloudflow build --module app.flows.order
```

Attach to an existing FastAPI app:

```python
from fastapi import FastAPI
from fastapi_cloudflow import attach_to_fastapi
from app.flows.order import WORKFLOWS

app = FastAPI()
attach_to_fastapi(app, WORKFLOWS)
```

See `docs/` for architecture, decisions, and roadmap.
