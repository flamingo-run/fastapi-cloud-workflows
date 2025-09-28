from __future__ import annotations

from pydantic import BaseModel

from fastapi_cloudflow import Context, step, try_catch, workflow


class TryCatchInput(BaseModel):
    value: int


class TryCatchResult(BaseModel):
    result: int


@step(name="tc-risky")
async def tc_risky(ctx: Context, data: TryCatchInput) -> TryCatchResult:
    return TryCatchResult(result=data.value * 2)


@step(name="tc-handler")
async def tc_handler(ctx: Context, data: TryCatchInput) -> TryCatchResult:
    return TryCatchResult(result=0)


TRY_BLOCK = workflow("tc-try") >> tc_risky
EXCEPT_BLOCK = workflow("tc-except") >> tc_handler
TRY_CATCH_STEP = try_catch("tc-safe").try_block(TRY_BLOCK).except_block(EXCEPT_BLOCK).raise_error(True).build()


TRY_CATCH_DEMO = (workflow("try-catch-demo") >> TRY_CATCH_STEP).build()
