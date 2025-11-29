from datetime import datetime

from pydantic import BaseModel


class AccessTokenPayload(BaseModel):
    sub: str
    type: str
    user_id: int
    org_id: int
    role: str
    email: str
    iat: datetime
    exp: datetime


class RefreshTokenPayload(BaseModel):
    sub: str
    type: str
    user_id: int
    jti: str
    iat: datetime
    exp: datetime
