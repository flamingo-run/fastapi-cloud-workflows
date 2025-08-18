## Contributing

Thanks for helping improve fastapi-cloudflow! This guide explains how to develop locally, run tests, and the project structure expectations so contributions stay consistent.

### Prerequisites
- Python 3.13
- [uv](https://github.com/astral-sh/uv) for env/install

### Setup
```
uv sync
```

### Commands (local)
- Lint: `uv run ruff check --fix .`
- Types: `uv run ty check`
- Unit tests: `uv run pytest -q tests/unit`
- Codegen tests (snapshots): `uv run pytest -q tests/codegen`
  - First run creates snapshots under `tests/codegen/fixtures/yaml` if missing; commit them
- Full test suite: `uv run pytest -q`

### Smoke tests
Run end-to-end against deployed Workflows (requires Google Cloud project and a deployed example app):
```
export GOOGLE_CLOUD_PROJECT=<your-project>
uv run -q python tests/smoke/run_smoke.py --region us-central1
```

### Project structure
- `src/fastapi_cloudflow/`
  - The reusable library (FastAPI-first) and CLI. Includes a FastAPI runtime (`attach_to_fastapi`) plus codegen/CLI. Keep it typed and well-tested

- `examples/app/`
  - A realistic FastAPI app showcasing multi-step, playful workflows
  - Naming: files should reflect the workflow domain (e.g., `echo_name.py`, `post_story.py`, `jokes.py`)
  - Every workflow is multi-step and demonstrates transformations; avoid duplicates covering the exact same feature

- `tests/`
  - `unit/`: FastAPI TestClient calls each step endpoint (`/steps/<name>`). Scope: step contracts (Pydantic I/O), route registration, and runtime error paths (422s for malformed/missing body, wrapper support)
  - `codegen/`: Runs the CLI to generate YAML and compares full-file snapshots under `tests/codegen/fixtures/yaml`. Scope: codegen stability and header/auth/timeout/ArgExpr emission
  - `smoke/`: Python runner that deploys Workflows and invokes them via gcloud, asserting final outputs. Scope: end-to-end validation of the example app + generated Workflows
