from pathlib import Path

from app.flows.order import ORDER_FLOW
from fastapi_cloudflow.codegen.workflows import workflow_to_yaml_dict


def test_yaml_includes_required_headers_and_sequence(tmp_path: Path):
    data = workflow_to_yaml_dict(ORDER_FLOW)
    steps = data["main"]["steps"]
    # Look at the first call step
    first_call = next(s for s in steps if list(s.keys())[0].startswith("call_"))
    args = list(first_call.values())[0]["args"]
    headers = args.get("headers", {})
    assert "X-Workflow-Name" in headers
    # Ensure run id capture step exists
    assert any("capture_run_id_" in list(s.keys())[0] for s in steps)
