from fastapi_cloudflow.core import Arg


def test_arg_helpers_ctx_and_param():
    assert str(Arg.param("a.b")).startswith("${")
    assert str(Arg.ctx("request_id")).startswith("${")
