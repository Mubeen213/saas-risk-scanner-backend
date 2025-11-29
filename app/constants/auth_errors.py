from enum import Enum


class AuthErrorCode(str, Enum):
    INVALID_EMAIL_DOMAIN = "INVALID_EMAIL_DOMAIN"
    USER_SUSPENDED = "USER_SUSPENDED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_INACTIVE = "USER_INACTIVE"
    USER_CREATION_FAILED = "USER_CREATION_FAILED"
    INVALID_USER_STATE = "INVALID_USER_STATE"
    UPDATE_FAILED = "UPDATE_FAILED"

    ORGANIZATION_NOT_FOUND = "ORGANIZATION_NOT_FOUND"
    ORGANIZATION_SUSPENDED = "ORGANIZATION_SUSPENDED"
    ORGANIZATION_EXISTS = "ORGANIZATION_EXISTS"
    DOMAIN_MISMATCH = "DOMAIN_MISMATCH"

    PLAN_NOT_FOUND = "PLAN_NOT_FOUND"
    ROLE_NOT_FOUND = "ROLE_NOT_FOUND"

    INVALID_OAUTH_STATE = "INVALID_OAUTH_STATE"
    OAUTH_ERROR = "OAUTH_ERROR"
    OAUTH_TOKEN_EXCHANGE_FAILED = "OAUTH_TOKEN_EXCHANGE_FAILED"
    OAUTH_USER_INFO_FAILED = "OAUTH_USER_INFO_FAILED"

    PROVIDER_NOT_FOUND = "PROVIDER_NOT_FOUND"
    AUTH_CONFIG_NOT_FOUND = "AUTH_CONFIG_NOT_FOUND"

    INVALID_REDIRECT_URI = "INVALID_REDIRECT_URI"
    INVALID_ACCESS_TOKEN = "INVALID_ACCESS_TOKEN"
    INVALID_REFRESH_TOKEN = "INVALID_REFRESH_TOKEN"


AUTH_ERROR_MESSAGES: dict[AuthErrorCode, str] = {
    AuthErrorCode.INVALID_EMAIL_DOMAIN: "Personal email addresses are not allowed. Please use your company email.",
    AuthErrorCode.USER_SUSPENDED: "Your account has been suspended. Please contact your administrator.",
    AuthErrorCode.USER_DEACTIVATED: "Your account has been deactivated.",
    AuthErrorCode.USER_NOT_FOUND: "User not found.",
    AuthErrorCode.USER_INACTIVE: "User account is not active.",
    AuthErrorCode.USER_CREATION_FAILED: "Failed to create user.",
    AuthErrorCode.INVALID_USER_STATE: "User is not in a valid state for this operation.",
    AuthErrorCode.UPDATE_FAILED: "Failed to update user.",
    AuthErrorCode.ORGANIZATION_NOT_FOUND: "Organization not found.",
    AuthErrorCode.ORGANIZATION_SUSPENDED: "Your organization has been suspended.",
    AuthErrorCode.ORGANIZATION_EXISTS: "An organization already exists for this domain. Please contact your administrator for an invitation.",
    AuthErrorCode.DOMAIN_MISMATCH: "Email domain does not match organization domain.",
    AuthErrorCode.PLAN_NOT_FOUND: "Subscription plan not found.",
    AuthErrorCode.ROLE_NOT_FOUND: "User role not found.",
    AuthErrorCode.INVALID_OAUTH_STATE: "Invalid OAuth state. Please try again.",
    AuthErrorCode.OAUTH_ERROR: "OAuth authentication failed. Please try again.",
    AuthErrorCode.OAUTH_TOKEN_EXCHANGE_FAILED: "Failed to exchange authorization code for tokens.",
    AuthErrorCode.OAUTH_USER_INFO_FAILED: "Failed to fetch user information from provider.",
    AuthErrorCode.PROVIDER_NOT_FOUND: "OAuth provider not found or not configured.",
    AuthErrorCode.AUTH_CONFIG_NOT_FOUND: "OAuth configuration not found for this provider.",
    AuthErrorCode.INVALID_REDIRECT_URI: "Invalid redirect URI.",
    AuthErrorCode.INVALID_ACCESS_TOKEN: "Access token is invalid or expired.",
    AuthErrorCode.INVALID_REFRESH_TOKEN: "Refresh token is invalid or expired.",
}
