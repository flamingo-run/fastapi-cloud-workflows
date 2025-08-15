from pathlib import Path

import typer

from .codegen.workflows import emit_workflow_yaml
from .core import get_workflows

app = typer.Typer(help="FastAPI CloudFlow CLI")


@app.command()
def build(
    module: str = typer.Option(None, help="Python module to import for side effects (register steps/workflows)"),
    out: Path = Path("build/workflows"),
):
    if module is None:
        raise typer.Exit(code=2)
    __import__(module)
    workflows = get_workflows()
    out.mkdir(parents=True, exist_ok=True)
    for wf in workflows:
        path = emit_workflow_yaml(wf, out)
        print(f"wrote {path}")


@app.command()
def validate(
    module: str = typer.Option(None, help="Python module to import for side effects (register steps/workflows)"),
):
    if module is None:
        raise typer.Exit(code=2)
    __import__(module)
    workflows = get_workflows()
    for wf in workflows:
        if not wf.nodes:
            raise typer.Exit(code=1)
    print("Validation OK")


@app.command()
def graph(
    module: str = typer.Option(None, help="Python module to import for side effects (register steps/workflows)"),
    out: Path | None = None,
):
    if module is None:
        raise typer.Exit(code=2)
    __import__(module)
    workflows = get_workflows()

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
