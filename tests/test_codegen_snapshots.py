from pathlib import Path

from app.flows.user import USER_SIGNUP
from fastapi_cloudflow.codegen.workflows import emit_workflow_yaml


def test_emit_yaml_creates_file(tmp_path: Path):
    out = tmp_path / "workflows"
    path = emit_workflow_yaml(USER_SIGNUP, out)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "X-Workflow-Name" in content
