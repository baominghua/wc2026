from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from services.auth import (
    auth_cookie_name,
    cookie_secure,
    create_session_token,
    is_auth_enabled,
    session_max_age_seconds,
    verify_admin_password,
    verify_session_token,
)


router = APIRouter()


class LoginRequest(BaseModel):
    password: str


@router.get("/status")
async def get_auth_status(request: Request):
    enabled = is_auth_enabled()
    if not enabled:
        return {"enabled": False, "authenticated": True}
    token = request.cookies.get(auth_cookie_name())
    return {"enabled": True, "authenticated": verify_session_token(token)}


@router.post("/login")
async def login(payload: LoginRequest, response: Response):
    if not is_auth_enabled():
        return {"enabled": False, "authenticated": True}
    if not verify_admin_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    response.set_cookie(
        key=auth_cookie_name(),
        value=create_session_token(),
        max_age=session_max_age_seconds(),
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
        path="/",
    )
    return {"enabled": True, "authenticated": True}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=auth_cookie_name(), path="/")
    return {"authenticated": False}
