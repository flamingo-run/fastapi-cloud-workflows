#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from typing import Any


def run_command(args: list[str]) -> str:
    # Avoid shell quoting issues by passing list args
    completed = subprocess.run(args, capture_output=True, text=True)
    if completed.returncode != 0:
        sys.stderr.write(f"Command failed ({completed.returncode}): {' '.join(shlex.quote(a) for a in args)}\n")
        sys.stderr.write(completed.stderr)
        raise SystemExit(1)
    return completed.stdout.strip()


def resolve_project() -> str:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT_ID")
    if project:
        return project
    try:
        return run_command(["gcloud", "config", "get-value", "project"]) or ""
    except SystemExit:
        return ""


def run_workflow(
    workflow_name: str, region: str, project: str, payload: dict[str, Any], timeout_sec: int = 180
) -> dict[str, Any]:
    data = json.dumps({"payload": payload})
    exec_name = run_command(
        [
            "gcloud",
            "workflows",
            "run",
            workflow_name,
            "--location",
            region,
            "--project",
            project,
            "--data",
            data,
            "--format=value(name)",
        ]
    )

    # Poll describe for state to avoid gcloud version mismatches
    deadline = time.time() + timeout_sec
    describe_args = [
        "gcloud",
        "workflows",
        "executions",
        "describe",
        exec_name,
        "--location",
        region,
        "--project",
        project,
        "--format=json",
    ]
    while True:
        out = run_command(describe_args)
        desc = json.loads(out)
        state = desc.get("state")
        if state == "SUCCEEDED":
            result_raw = desc.get("result", "")
            if not result_raw:
                sys.stderr.write("Execution SUCCEEDED but result is empty\n")
                sys.stderr.write(json.dumps(desc, indent=2) + "\n")
                raise SystemExit(1)
            try:
                return json.loads(result_raw)
            except json.JSONDecodeError as err:
                sys.stderr.write("Result is not valid JSON:\n" + result_raw + "\n")
                sys.stderr.write(json.dumps(desc, indent=2) + "\n")
                raise SystemExit(1) from err
        if state in {"FAILED", "ERROR", "CANCELLED"}:
            sys.stderr.write(f"Execution ended with state={state}\n")
            sys.stderr.write(json.dumps(desc, indent=2) + "\n")
            raise SystemExit(1)
        if time.time() > deadline:
            sys.stderr.write("Timed out waiting for execution to finish\n")
            sys.stderr.write(json.dumps(desc, indent=2) + "\n")
            raise SystemExit(1)
        time.sleep(2)


def assert_order_flow(result: dict[str, Any]) -> None:
    assert result.get("status") == "approved", result
    order_id = result.get("order_id", "")
    assert isinstance(order_id, str) and order_id.startswith("o-"), result


def assert_payment_flow(result: dict[str, Any]) -> None:
    assert result.get("ok") is True, result
    txn_id = result.get("txn_id")
    assert isinstance(txn_id, str) and len(txn_id) > 0, result


def assert_user_signup(result: dict[str, Any], email: str) -> None:
    assert result.get("user_id"), result
    assert result.get("email") == email, result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run smoke tests against deployed Workflows")
    parser.add_argument("--region", default="us-central1")
    parser.add_argument("--project", default=None)
    parser.add_argument(
        "--only",
        choices=[
            "order-flow",
            "payment-flow",
            "user-signup",
            "echo-name-flow",
            "post-story-flow",
            "joke-flow",
            "convert-flow",
        ],
        action="append",
    )
    args = parser.parse_args()

    project = args.project or resolve_project()
    if not project:
        print("Project not set. Set GOOGLE_CLOUD_PROJECT/PROJECT_ID or pass --project.", file=sys.stderr)
        sys.exit(1)

    include = set(
        args.only
        or [
            "order-flow",
            "payment-flow",
            "user-signup",
            "echo-name-flow",
            "post-story-flow",
            "joke-flow",
        ]
    )

    print(f"Running smoke tests in project={project} region={args.region}")

    if "order-flow" in include:
        print("- order-flow case 1")
        res1 = run_workflow("order-flow", args.region, project, {"account_id": 1, "sku": "abc", "qty": 1})
        assert_order_flow(res1)
        print("  OK", res1)
        print("- order-flow case 2")
        res2 = run_workflow("order-flow", args.region, project, {"account_id": 2, "sku": "xyz", "qty": 3})
        assert_order_flow(res2)
        print("  OK", res2)

    if "payment-flow" in include:
        print("- payment-flow")
        pres = run_workflow("payment-flow", args.region, project, {"total": 12.34, "currency": "USD"})
        assert_payment_flow(pres)
        print("  OK", pres)

    if "user-signup" in include:
        print("- user-signup")
        email = "user@example.com"
        ures = run_workflow("user-signup", args.region, project, {"email": email, "password": "hunter2asdf"})
        assert_user_signup(ures, email)
        print("  OK", ures)

    if "echo-name-flow" in include:
        print("- echo-name-flow")
        eres = run_workflow("echo-name-flow", args.region, project, {"name": "Developer"})
        # Final step returns a shout summary
        assert isinstance(eres.get("length"), int) and isinstance(eres.get("name_upper"), str), eres
        print("  OK", eres)

    if "post-story-flow" in include:
        print("- post-story-flow")
        jres = run_workflow(
            "post-story-flow",
            args.region,
            project,
            {"topic": "hello", "mood": "curious", "author_id": 1},
        )
        assert isinstance(jres.get("id"), int) and "slug" in jres and "short_title" in jres, jres
        print("  OK", jres)

    if "joke-flow" in include:
        print("- joke-flow")
        jf = run_workflow("joke-flow", args.region, project, {})
        # From rated joke, ensure shape
        assert "setup" in jf and "punch" in jf and isinstance(jf.get("rating"), int), jf
        print("  OK", jf)

    # convert-flow disabled until branch/merge is supported in core

    print("All smoke tests passed.")


if __name__ == "__main__":
    main()
