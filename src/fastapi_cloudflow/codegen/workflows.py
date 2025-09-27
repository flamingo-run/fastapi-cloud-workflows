from pathlib import Path
from typing import Any

import yaml

from ..core import AssignStep, HttpStep, TryCatchStep, Workflow


def _is_arg_expr(v: Any) -> bool:
    return hasattr(v, "expr") and isinstance(v.expr, str)


def _as_yaml_expr(v: Any) -> Any:
    if _is_arg_expr(v):
        return f"${{{v.expr}}}"
    return v


def _concat_expr(left_expr: str, right_literal: str) -> str:
    return f'${{{left_expr} + "{right_literal}"}}'


WORKFLOW_NAME_EXPR = 'sys.get_env("GOOGLE_CLOUD_WORKFLOW_ID")'


def _emit_retry_config(retry: Any) -> dict[str, Any] | None:
    """Emit retry configuration for Cloud Workflows YAML."""
    if not retry:
        return None

    from ..core import RetryPolicy

    if not isinstance(retry, RetryPolicy):
        return None

    config: dict[str, Any] = {
        "predicate": f"${{{retry.predicate}}}",
        "max_retries": retry.max_retries,
    }

    if retry.initial_delay_s or retry.max_delay_s or retry.multiplier:
        config["backoff"] = {
            "initial_delay": retry.initial_delay_s,
            "max_delay": retry.max_delay_s,
            "multiplier": retry.multiplier,
        }

    return config


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


def _process_single_step(
    node: Any,
    idx: int,
    base_url_expr: str,
    payload_var: str,
    have_run_id: bool,
) -> tuple[list[dict[str, Any]], bool]:
    """Process a single step and return the YAML steps and whether run_id was captured."""
    steps: list[dict[str, Any]] = []

    if isinstance(node, AssignStep):
        steps.append(
            {f"assign_{idx}": {"assign": [{payload_var: {k: _as_yaml_expr(v) for k, v in node.expr.items()}}]}}
        )
        return steps, have_run_id

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

        step_def: dict[str, Any] = {"call": f"http.{method}", "args": args, "result": result_var}
        retry_config = _emit_retry_config(node.retry)
        if retry_config:
            step_def["retry"] = retry_config
        steps.append({f"call_{node.name}": step_def})
        steps.append({f"set_payload_{idx}": {"assign": [{payload_var: f"${{{result_var}.body}}"}]}})
        return steps, have_run_id

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
    if node.timeout:
        args["timeout"] = int(node.timeout.total_seconds())

    step_def: dict[str, Any] = {"call": "http.post", "args": args, "result": result_var}
    retry_config = _emit_retry_config(node.retry)
    if retry_config:
        step_def["retry"] = retry_config
    steps.append({f"call_{node.name}": step_def})
    steps.append({f"set_payload_{idx}": {"assign": [{payload_var: f"${{{result_var}.body}}"}]}})

    if not have_run_id:
        steps.append(
            {f"capture_run_id_{idx}": {"assign": [{"run_id": f'${{{result_var}.headers["X-Workflow-Run-Id"]}}'}]}}
        )
        have_run_id = True

    return steps, have_run_id


def _process_steps(
    nodes: list[Any],
    base_url_expr: str,
    payload_var: str = "payload",
    have_run_id: bool = False,
    step_offset: int = 0,
) -> tuple[list[dict[str, Any]], bool]:
    """Process a list of steps and return YAML steps and whether run_id was captured."""
    steps: list[dict[str, Any]] = []

    for idx, node in enumerate(nodes):
        actual_idx = step_offset + idx

        if isinstance(node, TryCatchStep):
            # Generate try/catch block
            try_steps, have_run_id = _process_steps(
                node.try_steps, base_url_expr, payload_var, have_run_id, step_offset=actual_idx * 100
            )

            try_catch_def: dict[str, Any] = {"try": {"steps": try_steps}}

            if node.except_steps:
                except_steps, have_run_id = _process_steps(
                    node.except_steps, base_url_expr, payload_var, have_run_id, step_offset=actual_idx * 100 + 50
                )
                try_catch_def["except"] = {"as": node.error_var, "steps": except_steps}
                if node.raise_on_error:
                    # Add a uniquely named step to re-raise the error after handling
                    reraise_name = f"reraise_{node.name}"
                    except_steps.append({reraise_name: {"raise": f"${{{node.error_var}}}"}})
                    try_catch_def["except"]["steps"] = except_steps
            else:
                # Just catch without handling - useful for ignoring errors
                try_catch_def["except"] = {"as": node.error_var, "steps": []}

            steps.append({f"try_catch_{node.name}": try_catch_def})
            continue

        step_list, have_run_id = _process_single_step(node, actual_idx, base_url_expr, payload_var, have_run_id)
        steps.extend(step_list)

    return steps, have_run_id


def workflow_to_yaml_dict(wf: Workflow, base_url_expr: str = 'sys.get_env("BASE_URL")') -> dict[str, Any]:
    payload_var = "payload"

    # Process all steps (including try/catch blocks)
    steps, _ = _process_steps(wf.nodes, base_url_expr, payload_var, have_run_id=False)

    steps.append({"return_final": {"return": f"${{{payload_var}}}"}})
    return {"main": {"params": [payload_var], "steps": steps}}


def emit_workflow_yaml(wf: Workflow, out_dir: Path, base_url_expr: str | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = workflow_to_yaml_dict(wf, base_url_expr=base_url_expr or 'sys.get_env("BASE_URL")')
    path = out_dir / f"{wf.name}.yaml"
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False)
    return path
