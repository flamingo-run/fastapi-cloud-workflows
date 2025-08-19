from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from fastapi_cloudflow import Arg, AssignStep, Context, HttpStep, step, workflow


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserDraft(BaseModel):
    email: EmailStr
    hashed_password: str


class IdentityReq(BaseModel):
    email: EmailStr
    secret: str


class IdentityRes(BaseModel):
    external_id: str
    ok: bool


class UserCreated(BaseModel):
    user_id: str
    email: EmailStr


@step(name="hash-password")
async def hash_password(ctx: Context, data: SignupRequest) -> UserDraft:
    return UserDraft(email=data.email, hashed_password=f"hashed:{data.password}")


adapt_to_idp = AssignStep(
    "draft->idp",
    UserDraft,
    IdentityReq,
    expr={
        "email": "${payload.email}",
        "secret": "${payload.hashed_password}",
    },
)


idp_call = HttpStep(
    name="idp-call",
    input_model=IdentityReq,
    output_model=IdentityRes,
    method="POST",
    url=Arg.env("IDP_URL") / "signup",
    auth={"type": "OIDC", "audience": Arg.env("IDP_URL")},
)


@step(name="persist-user")
async def persist_user(ctx: Context, data: IdentityRes) -> UserCreated:
    return UserCreated(user_id=data.external_id, email="user@example.com")


USER_SIGNUP = (workflow("user-signup") >> hash_password >> adapt_to_idp >> idp_call >> persist_user).build()
