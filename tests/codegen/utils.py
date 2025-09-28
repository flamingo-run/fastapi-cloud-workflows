"""Helper utilities for codegen contract tests."""

from __future__ import annotations

from pathlib import Path

import yaml

from fastapi_cloudflow.codegen.workflows import emit_workflow_yaml
from fastapi_cloudflow.core.workflow import Workflow

FIXTURE_YAML_DIR = Path("tests/codegen/fixtures/yaml")


def _ensure_fixture(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")
        raise AssertionError(f"Created missing fixture {path}. Review and rerun the tests.")
    existing = path.read_text(encoding="utf-8")
    if existing != content:
        path.write_text(content, encoding="utf-8")
        raise AssertionError(f"Updated fixture {path}. Review and rerun the tests.")


def assert_workflow_contract(workflow: Workflow, fixture_name: str, tmp_path: Path) -> dict:
    generated_yaml_dir = tmp_path / "yaml"
    generated_yaml_dir.mkdir(parents=True, exist_ok=True)
    generated_yaml_path = emit_workflow_yaml(workflow, generated_yaml_dir)
    yaml_content = generated_yaml_path.read_text(encoding="utf-8")
    yaml_fixture = FIXTURE_YAML_DIR / f"{fixture_name}.yaml"
    _ensure_fixture(yaml_fixture, yaml_content)
    return yaml.safe_load(yaml_content)
