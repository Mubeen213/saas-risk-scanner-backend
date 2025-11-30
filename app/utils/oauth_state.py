import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from app.core.settings import settings

STATE_EXPIRY_SECONDS = 600  # 10 minutes


def _get_signing_key() -> bytes:
    return settings.jwt_secret_key.encode()


def _sign_data(data: str) -> str:
    signature = hmac.new(_get_signing_key(), data.encode(), hashlib.sha256).hexdigest()
    return signature


def create_signed_state(
    provider_slug: str,
    frontend_redirect_uri: str,
) -> str:
    nonce = secrets.token_urlsafe(16)
    payload = {
        "nonce": nonce,
        "provider_slug": provider_slug,
        "frontend_redirect_uri": frontend_redirect_uri,
        "exp": int(time.time()) + STATE_EXPIRY_SECONDS,
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    signature = _sign_data(payload_b64)
    return f"{payload_b64}.{signature}"


def verify_signed_state(state: str) -> dict[str, Any] | None:
    try:
        parts = state.split(".")
        if len(parts) != 2:
            return None

        payload_b64, signature = parts

        expected_signature = _sign_data(payload_b64)
        if not hmac.compare_digest(signature, expected_signature):
            return None

        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_json)

        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload
    except Exception:
        return None
