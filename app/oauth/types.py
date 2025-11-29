from typing import Any

from pydantic import BaseModel, EmailStr, Field


class OAuthTokens(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int | None = None
    scope: str | None = None
    id_token: str | None = None


class OAuthUserInfo(BaseModel):
    provider_user_id: str
    email: EmailStr
    full_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    avatar_url: str | None = None
    email_verified: bool = False
    hosted_domain: str | None = None


class OAuthConfig(BaseModel):
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    userinfo_url: str
    revoke_url: str | None = None
    scopes: list[str] = Field(default_factory=list)
    redirect_uri: str
    additional_params: dict[str, Any] = Field(default_factory=dict)
