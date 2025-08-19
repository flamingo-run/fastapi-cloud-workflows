from __future__ import annotations

import filecmp
import os
import shutil
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "pyproject.toml").exists():
            return p
    return Path.cwd()


def run_cli_graph_dir(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "fastapi-cloudflow",
        "graph",
        "--app-spec",
        "main:app",
        "--flows-path",
        "examples/app/flows",
        "--per-workflow",
        "--out",
        str(out_dir),
    ]
    env = os.environ.copy()
    # Ensure CLI subprocess resolves the project modules
    env_pythonpath = ":".join(["src", "examples/app", ".", env.get("PYTHONPATH", "")]).strip(":")
    env["PYTHONPATH"] = env_pythonpath
    subprocess.run(cmd, check=True, cwd=str(_repo_root()), env=env, capture_output=True, text=True)
    return sorted(out_dir.glob("*.mmd"))


def test_graph_mermaid_snapshots(tmp_path: Path) -> None:
    out_dir = tmp_path / "graphs"
    files = run_cli_graph_dir(out_dir)

    fixture_dir = Path("tests/codegen/fixtures/mermaid")
    fixture_dir.mkdir(parents=True, exist_ok=True)

    missing: list[str] = []
    mismatches: list[str] = []
    for f in files:
        fix = fixture_dir / f.name
        if not fix.exists():
            shutil.copy2(f, fix)
            missing.append(f.name)
        else:
            if not filecmp.cmp(f, fix, shallow=False):
                mismatches.append(f.name)

    if missing:
        raise AssertionError(f"Created initial graph snapshots for: {', '.join(missing)}. Commit them and re-run.")
    if mismatches:
        raise AssertionError(
            f"Mermaid graph snapshots differ for: {', '.join(mismatches)} (update fixtures if intended)"
        )
