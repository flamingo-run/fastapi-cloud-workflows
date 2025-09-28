"""Contract test for try/catch workflows."""

from __future__ import annotations

from pathlib import Path

from examples.app.flows.try_catch_contract import TRY_CATCH_DEMO
from tests.codegen.utils import assert_workflow_contract


def test_try_catch_contract(tmp_path: Path) -> None:
    assert_workflow_contract(TRY_CATCH_DEMO, "try-catch-demo", tmp_path)
