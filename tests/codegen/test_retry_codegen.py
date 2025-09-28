"""Contract tests for retry-related workflows."""

from __future__ import annotations

from pathlib import Path

from examples.app.flows.retry_contract import RETRY_DEMO_WORKFLOW
from tests.codegen.utils import assert_workflow_contract


def test_retry_workflow_contract(tmp_path: Path) -> None:
    assert_workflow_contract(RETRY_DEMO_WORKFLOW, "retry-demo", tmp_path)
