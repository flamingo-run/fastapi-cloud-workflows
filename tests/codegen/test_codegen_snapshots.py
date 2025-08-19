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


def run_cli_build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Use the module entry to avoid PATH issues
    cmd = [
        "fastapi-cloudflow",
        "build",
        "--app-spec",
        "main:app",
        "--flows-path",
        "examples/app/flows",
        "--out",
        str(out_dir),
    ]
    env = os.environ.copy()
    # Note: pytest's pythonpath config only affects the test interpreter. The CLI runs
    # in a separate subprocess, so we must set PYTHONPATH here to make `flows` (from
    # examples/app) and the installed package under src importable for the CLI process.
    env_pythonpath = ":".join(["src", "examples/app", ".", env.get("PYTHONPATH", "")]).strip(":")
    env["PYTHONPATH"] = env_pythonpath
    subprocess.run(cmd, check=True, cwd=str(_repo_root()), env=env)


def test_codegen_snapshots(tmp_path: Path) -> None:
    out = tmp_path / "yaml"
    run_cli_build(out)

    fixture_root = Path("tests/codegen/fixtures/yaml")
    fixture_root.mkdir(parents=True, exist_ok=True)

    # compare all generated files against fixtures
    generated = sorted(p.name for p in out.glob("*.yaml"))
    assert generated, "No YAMLs generated"

    missing_fixtures: list[str] = []
    mismatches: list[str] = []
    for name in generated:
        gen_path = out / name
        fix_path = fixture_root / name
        if not fix_path.exists():
            # create initial snapshot for review
            shutil.copy2(gen_path, fix_path)
            missing_fixtures.append(name)
        else:
            if not filecmp.cmp(gen_path, fix_path, shallow=False):
                mismatches.append(name)

    if missing_fixtures:
        raise AssertionError(f"Created initial snapshots for: {', '.join(missing_fixtures)}. Commit them and re-run.")
    if mismatches:
        diff_list = ", ".join(mismatches)
        raise AssertionError(f"Codegen snapshots differ for: {diff_list} (update fixtures if intended)")
