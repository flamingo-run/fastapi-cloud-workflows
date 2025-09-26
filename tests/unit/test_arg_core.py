"""Tests for arg.py core module to improve coverage."""

from __future__ import annotations

from fastapi_cloudflow import Arg
from fastapi_cloudflow.core.arg import ArgExpr


def test_arg_expr_creation():
    """Test ArgExpr basic creation."""
    expr = ArgExpr("payload.value")
    assert expr.expr == "payload.value"
    assert str(expr) == "${payload.value}"


def test_arg_expr_coerce_with_arg_expr():
    """Test _coerce_expr with ArgExpr input (covers line 11)."""
    original_expr = ArgExpr("payload.data")

    # When coercing an ArgExpr, it should return the expr string
    result = ArgExpr._coerce_expr(original_expr)
    assert result == "payload.data"  # Returns the inner expr, not quoted


def test_arg_expr_coerce_with_string():
    """Test _coerce_expr with string input."""
    result = ArgExpr._coerce_expr("hello")
    assert result == '"hello"'


def test_arg_expr_div_with_arg_expr():
    """Test division operator with ArgExpr (path joining)."""
    base = ArgExpr('sys.get_env("BASE_URL")')
    path = ArgExpr("params.endpoint")

    result = base / path
    assert isinstance(result, ArgExpr)
    assert result.expr == 'sys.get_env("BASE_URL") + "/" + params.endpoint'


def test_arg_expr_div_with_string():
    """Test division operator with string."""
    base = ArgExpr('sys.get_env("BASE_URL")')

    result = base / "api/v1"
    assert isinstance(result, ArgExpr)
    assert result.expr == 'sys.get_env("BASE_URL") + "/api/v1"'


def test_arg_expr_add_with_arg_expr():
    """Test addition operator with ArgExpr."""
    left = ArgExpr("payload.first")
    right = ArgExpr("payload.last")

    result = left + right
    assert isinstance(result, ArgExpr)
    assert result.expr == "payload.first + payload.last"


def test_arg_expr_add_with_string():
    """Test addition operator with string."""
    expr = ArgExpr("payload.name")

    result = expr + " - processed"
    assert isinstance(result, ArgExpr)
    assert result.expr == 'payload.name + " - processed"'


def test_arg_env():
    """Test Arg.env() helper."""
    result = Arg.env("MY_ENV_VAR")
    assert isinstance(result, ArgExpr)
    assert result.expr == 'sys.get_env("MY_ENV_VAR")'
    assert str(result) == '${sys.get_env("MY_ENV_VAR")}'


def test_arg_param():
    """Test Arg.param() helper."""
    result = Arg.param("user.id")
    assert isinstance(result, ArgExpr)
    assert result.expr == "params.user.id"
    assert str(result) == "${params.user.id}"


def test_arg_ctx():
    """Test Arg.ctx() helper."""
    result = Arg.ctx("request_id")
    assert isinstance(result, ArgExpr)
    assert result.expr == "ctx.request_id"
    assert str(result) == "${ctx.request_id}"


def test_complex_expression_chaining():
    """Test complex chaining of ArgExpr operations."""
    # Build: ${sys.get_env("BASE_URL") + "/api/" + params.version + "/users"}
    base_url = Arg.env("BASE_URL")
    version = Arg.param("version")

    # Chain operations
    api_path = base_url / "api" / version / "users"

    assert isinstance(api_path, ArgExpr)
    # Should create nested path joining
    expected_parts = ['sys.get_env("BASE_URL")', '"/api"', "params.version", '"/users"']
    # Check that all parts are in the expression
    for part in expected_parts:
        assert part in api_path.expr or part.replace('"', "") in api_path.expr


def test_arg_expr_string_representation():
    """Test string representation of ArgExpr."""
    expr = ArgExpr("payload.total * 2")
    assert str(expr) == "${payload.total * 2}"

    # Test with environment variable
    env_expr = Arg.env("DATABASE_URL")
    assert str(env_expr) == '${sys.get_env("DATABASE_URL")}'


def test_mixed_operations():
    """Test mixing different operations."""
    # Create a complex expression mixing env, param, and literals
    host = Arg.env("HOST")
    port = Arg.param("port")

    # Build: ${sys.get_env("HOST") + ":" + params.port}
    url = host + ":" + port

    # Note: port is already an ArgExpr, so it won't be quoted
    # The _coerce_expr should handle this correctly
    assert ":" in url.expr
    assert "sys.get_env" in url.expr
    assert "params.port" in url.expr


def test_arg_expr_nested_coercion():
    """Test that nested ArgExpr coercion works correctly."""
    # This specifically tests the branch where _coerce_expr receives an ArgExpr
    expr1 = ArgExpr("payload.a")
    expr2 = ArgExpr("payload.b")

    # When adding two ArgExprs, the second one should be coerced properly
    result = expr1 + expr2

    # The second ArgExpr should have its .expr extracted (not quoted)
    assert result.expr == "payload.a + payload.b"

    # Test with mixed types
    result2 = expr1 + "literal"
    assert result2.expr == 'payload.a + "literal"'
