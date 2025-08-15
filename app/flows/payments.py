from __future__ import annotations

from pydantic import BaseModel

from fastapi_cloudflow import Arg, AssignStep, Context, HttpStep, step, workflow


class Cart(BaseModel):
    total: float
    currency: str


class PSPReq(BaseModel):
    amount: float
    currency: str


class PSPRes(BaseModel):
    status: str
    psp_id: str


@step(name="validate-cart")
async def validate_cart(ctx: Context, data: Cart) -> Cart:
    assert data.total >= 0
    return data


to_psp = AssignStep("cart->psp", Cart, PSPReq, expr={"amount": "${payload.total}", "currency": "${payload.currency}"})

psp = HttpStep("psp-charge", PSPReq, PSPRes, method="POST", url=Arg.env("PSP_URL") / "charge")


class ChargeResult(BaseModel):
    ok: bool
    txn_id: str | None


@step(name="summarize-charge")
async def summarize_charge(ctx: Context, data: PSPRes) -> ChargeResult:
    return ChargeResult(ok=(data.status == "approved"), txn_id=data.psp_id)


PAYMENT_FLOW = (workflow("payment-flow") >> validate_cart >> to_psp >> psp >> summarize_charge).build()
