Testing layout

- smoke/
  - Cloud Build pipeline and Python runner that deploys the example app and Workflows, then invokes workflows end-to-end and asserts final results.

- unit/
  - FastAPI TestClient tests that call each step endpoint under /steps and validate Pydantic contracts and route registration.

- codegen/
  - CLI-driven codegen tests that generate YAML and compare full-file snapshots under tests/fixtures/yaml.

Notes
- Set GOOGLE_CLOUD_PROJECT (or configure gcloud) to run smoke tests locally.
- On first snapshot run, snapshot files will be created under tests/fixtures/yaml; commit them and re-run.

