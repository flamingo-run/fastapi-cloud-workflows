from fastapi_cloudflow.core import Arg


def test_argexpr_concat_and_join():
    base = Arg.env("BASE")
    expr1 = str(base / "v1")
    assert expr1.startswith("${") and "/v1" in expr1

    expr2 = str(base + "suffix")
    assert expr2.startswith("${") and "suffix" in expr2
