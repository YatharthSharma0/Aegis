"""Auth endpoints (``05-API-Contracts`` §Auth). Public — no bearer required."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, get_account_service
from app.domain.accounts import AccountService, TokenPair

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_Accounts = Annotated[AccountService, Depends(get_account_service)]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    expires_in: int

    @classmethod
    def of(cls, pair: TokenPair) -> TokenResponse:
        return cls(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            role=pair.role.value,
            expires_in=pair.expires_in,
        )


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    unit: str | None


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, accounts: _Accounts) -> TokenResponse:
    account = accounts.authenticate(request.email, request.password)
    return TokenResponse.of(accounts.issue_tokens(account))


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: RefreshRequest, accounts: _Accounts) -> TokenResponse:
    return TokenResponse.of(accounts.refresh(request.refresh_token))


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser) -> MeResponse:
    return MeResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role.value, unit=user.unit,
    )
