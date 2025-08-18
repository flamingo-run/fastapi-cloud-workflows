from pathlib import Path
from typing import Any

import yaml

from ..core import AssignStep, HttpStep, Workflow


def _is_arg_expr(v: Any) -> bool:
    return hasattr(v, "expr") and isinstance(v.expr, str)


def _as_yaml_expr(v: Any) -> Any:
    if _is_arg_expr(v):
        return f"${{{v.expr}}}"
    return v


def _concat_expr(left_expr: str, right_literal: str) -> str:
    return f'${{{left_expr} + "{right_literal}"}}'


WORKFLOW_NAME_EXPR = 'sys.get_env("GOOGLE_CLOUD_WORKFLOW_ID")'


def workflow_to_yaml_dict(wf: Workflow, base_url_expr: str = 'sys.get_env("BASE_URL")') -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    payload_var = "payload"
    have_run_id = False

    def _with_required_headers(
        existing: dict[str, Any] | None, include_run_id: bool, include_content_type: bool
    ) -> dict[str, Any]:
        headers: dict[str, Any] = {}
        # Always include workflow name from env
        headers["X-Workflow-Name"] = f"${{{WORKFLOW_NAME_EXPR}}}"
        if include_run_id:
            headers["X-Workflow-Run-Id"] = "${run_id}"
        # Only set Content-Type when sending a body
        if include_content_type:
            headers["Content-Type"] = "application/json"
        if existing:
            headers.update({k: _as_yaml_expr(v) for k, v in existing.items()})
        return headers

    for idx, node in enumerate(wf.nodes):
        if isinstance(node, AssignStep):
            steps.append(
                {f"assign_{idx}": {"assign": [{payload_var: {k: _as_yaml_expr(v) for k, v in node.expr.items()}}]}}
            )
            continue

        if isinstance(node, HttpStep):
            method = node.method.lower()
            result_var = f"res_{idx}"
            args: dict[str, Any] = {"url": _as_yaml_expr(node.url)}
            # Only include body for non-GET methods; http.get does not accept a body argument
            if method != "get":
                args["body"] = f"${{{payload_var}}}"
            args["headers"] = _with_required_headers(
                node.headers or {}, have_run_id, include_content_type=(method != "get")
            )
            if node.auth:
                args["auth"] = {k: _as_yaml_expr(v) for k, v in node.auth.items()}
            if node.timeout:
                args["timeout"] = int(node.timeout.total_seconds())

            steps.append({f"call_{node.name}": {"call": f"http.{method}", "args": args, "result": result_var}})
            steps.append({f"set_payload_{idx}": {"assign": [{payload_var: f"${{{result_var}.body}}"}]}})
            continue

        # Python step via FastAPI endpoint
        result_var = f"res_{idx}"
        url_expr = _concat_expr(base_url_expr, f"/steps/{node.name}")
        args = {
            "url": url_expr,
            "body": f"${{{payload_var}}}",
            "headers": _with_required_headers({}, have_run_id, include_content_type=True),
            # Authenticate calls to Cloud Run using the workflow's service account
            "auth": {"type": "OIDC", "audience": f"${{{base_url_expr}}}"},
        }
        steps.append({f"call_{node.name}": {"call": "http.post", "args": args, "result": result_var}})
        steps.append({f"set_payload_{idx}": {"assign": [{payload_var: f"${{{result_var}.body}}"}]}})
        if not have_run_id:
            steps.append(
                {f"capture_run_id_{idx}": {"assign": [{"run_id": f'${{{result_var}.headers["X-Workflow-Run-Id"]}}'}]}}
            )
            have_run_id = True

    steps.append({"return_final": {"return": f"${{{payload_var}}}"}})
    return {"main": {"params": [payload_var], "steps": steps}}


def emit_workflow_yaml(wf: Workflow, out_dir: Path, base_url_expr: str | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = workflow_to_yaml_dict(wf, base_url_expr=base_url_expr or 'sys.get_env("BASE_URL")')
    path = out_dir / f"{wf.name}.yaml"
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False)
    return path
