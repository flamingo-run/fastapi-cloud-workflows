"""Contract tests for subworkflow composition."""

from __future__ import annotations

from pathlib import Path

from examples.app.flows.subworkflow_contract import SUBWORKFLOW_DEMO
from tests.codegen.utils import assert_workflow_contract


def test_subworkflow_contract(tmp_path: Path) -> None:
    assert_workflow_contract(SUBWORKFLOW_DEMO, "subworkflow-demo", tmp_path)
