import importlib
from pathlib import Path

import typer

from fastapi_cloudflow.codegen.workflows import emit_workflow_yaml
from fastapi_cloudflow.core import get_workflows

app = typer.Typer(help="FastAPI CloudFlow CLI")


def _import_app(app_spec: str | None) -> None:
    if not app_spec:
        return
    module_name, _, _attr = app_spec.partition(":")
    importlib.import_module(module_name)


def _discover_flow_modules(flows_path: Path) -> list[str]:
    modules: list[str] = []
    root = Path.cwd()
    if not flows_path.exists():
        return modules
    for py in flows_path.rglob("*.py"):
        if py.name == "__init__.py":
            continue
        try:
            rel = py.relative_to(root)
        except ValueError:
            rel = py
        mod = ".".join(rel.with_suffix("").parts)
        modules.append(mod)
    return modules


@app.command()
def build(
    module: list[str] | None = None,
    out: Path = Path("build/workflows"),
    base_url: str | None = None,
    app_spec: str | None = None,
    flows_path: Path = Path("app/flows"),
):
    module = module or []
    if module:
        for m in module:
            __import__(m)
    elif app_spec:
        # App is responsible for importing/registering flows; avoid double-imports
        _import_app(app_spec)
    else:
        # No app specified; import flows from the provided path
        for m in _discover_flow_modules(flows_path):
            __import__(m)
    workflows = get_workflows()
    out.mkdir(parents=True, exist_ok=True)
    for wf in workflows:
        emit_workflow_yaml(wf, out, base_url_expr=f'"{base_url}"' if base_url else None)
        print(f"wrote {out / (wf.name + '.yaml')}")


@app.command()
def validate(
    module: list[str] | None = None,
    app_spec: str | None = None,
    flows_path: Path = Path("app/flows"),
):
    module = module or []
    if module:
        for m in module:
            __import__(m)
    elif app_spec:
        _import_app(app_spec)
    else:
        for m in _discover_flow_modules(flows_path):
            __import__(m)
    workflows = get_workflows()
    for wf in workflows:
        if not wf.nodes:
            raise typer.Exit(code=1)
    print("Validation OK")


@app.command()
def graph(
    module: list[str] | None = None,
    out: Path | None = None,
    app_spec: str | None = None,
    flows_path: Path = Path("app/flows"),
    per_workflow: bool = False,
):
    module = module or []
    if module:
        for m in module:
            __import__(m)
    elif app_spec:
        _import_app(app_spec)
    else:
        for m in _discover_flow_modules(flows_path):
            __import__(m)
    workflows = get_workflows()

    if per_workflow:
        # Write one Mermaid file per workflow into the provided directory
        if out is None:
            out = Path("build/graphs")
        out.mkdir(parents=True, exist_ok=True)
        for wf in workflows:
            lines: list[str] = ["graph TD"]
            # Keep subgraph for consistency/labeling even when single workflow
            lines.append(f"  subgraph {wf.name}")
            for node in wf.nodes:
                lines.append(f"    {node.name}[{node.name}]")
            for a, b in zip(wf.nodes, wf.nodes[1:], strict=False):
                lines.append(f"    {a.name} --> {b.name}")
            lines.append("  end")
            content = "\n".join(lines) + "\n"
            target = out / f"{wf.name}.mmd"
            target.write_text(content, encoding="utf-8")
            print(f"wrote {target}")
    else:
        lines: list[str] = ["graph TD"]
        for wf in workflows:
            lines.append(f"  subgraph {wf.name}")
            for node in wf.nodes:
                lines.append(f"    {node.name}[{node.name}]")
            for a, b in zip(wf.nodes, wf.nodes[1:], strict=False):
                lines.append(f"    {a.name} --> {b.name}")
            lines.append("  end")

        content = "\n".join(lines) + "\n"
        if out is None:
            print(content)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(content, encoding="utf-8")
            print(f"wrote {out}")
