from datetime import datetime, timedelta, timezone

import jwt
from pydantic import ValidationError

from app.constants.enums import TokenType
from app.core.settings import settings
from app.dtos.token_dtos import AccessTokenPayload, RefreshTokenPayload


class TokenService:

    def create_access_token(
        self, user_id: int, org_id: int, role: str, email: str
    ) -> str:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=settings.access_token_expire_seconds)
        payload = {
            "sub": str(user_id),
            "type": TokenType.ACCESS.value,
            "user_id": user_id,
            "org_id": org_id,
            "role": role,
            "email": email,
            "iat": now,
            "exp": expires,
        }
        return jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    def create_refresh_token(self, user_id: int, jti: str) -> str:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=settings.refresh_token_expire_seconds)
        payload = {
            "sub": str(user_id),
            "type": TokenType.REFRESH.value,
            "user_id": user_id,
            "jti": jti,
            "iat": now,
            "exp": expires,
        }
        return jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    def verify_access_token(self, token: str) -> AccessTokenPayload | None:
        try:
            payload = jwt.decode(
                token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
            )
            if payload.get("type") != TokenType.ACCESS.value:
                return None
            return AccessTokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except ValidationError:
            return None

    def verify_refresh_token(self, token: str) -> RefreshTokenPayload | None:
        try:
            payload = jwt.decode(
                token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
            )
            if payload.get("type") != TokenType.REFRESH.value:
                return None
            return RefreshTokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except ValidationError:
            return None


token_service = TokenService()
