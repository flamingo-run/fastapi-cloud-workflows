from __future__ import annotations

from fastapi_cloudflow.core.arg import Arg, ArgExpr


def test_arg_env_and_str() -> None:
    e = Arg.env("FOO")
    assert isinstance(e, ArgExpr)
    assert str(e) == '${sys.get_env("FOO")}'  # wrapped as ${...}


def test_arg_concat_and_div() -> None:
    base = Arg.env("BASE")
    p = base / "steps" / Arg.env("NAME")
    s = base + "/hello"
    # Validate expression strings
    assert isinstance(p, ArgExpr)
    assert "/steps" in p.expr and 'sys.get_env("NAME")' in p.expr
    assert isinstance(s, ArgExpr)
    assert "/hello" in s.expr


def test_arg_param_and_ctx() -> None:
    assert str(Arg.param("foo")) == "${params.foo}"
    assert str(Arg.ctx("run_id")) == "${ctx.run_id}"
