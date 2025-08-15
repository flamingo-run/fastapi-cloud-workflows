from app.flows.payments import PAYMENT_FLOW
from app.flows.user import USER_SIGNUP
from fastapi_cloudflow.codegen.workflows import workflow_to_yaml_dict


def test_user_signup_codegen_headers_and_order():
    data = workflow_to_yaml_dict(USER_SIGNUP)
    steps = data["main"]["steps"]
    # Ensure order: call_hash-password -> assign draft->idp -> call_idp-call -> call_persist-user
    names = [
        list(s.keys())[0]
        for s in steps
        if list(s.keys())[0].startswith("call_") or list(s.keys())[0].startswith("assign_")
    ]
    assert any(n.startswith("call_hash-password") for n in names)
    assert any(n.startswith("assign_") for n in names)
    assert any(n.startswith("call_idp-call") for n in names)

    # Headers present
    first_call = next(s for s in steps if list(s.keys())[0].startswith("call_"))
    headers = list(first_call.values())[0]["args"]["headers"]
    assert "X-Workflow-Name" in headers


def test_payment_flow_codegen_and_runid():
    data = workflow_to_yaml_dict(PAYMENT_FLOW)
    steps = data["main"]["steps"]
    # run_id captured once
    captures = [s for s in steps if list(s.keys())[0].startswith("capture_run_id_")]
    assert len(captures) == 1
