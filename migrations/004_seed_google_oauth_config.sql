-- Migration: 004_seed_google_oauth_config
-- Description: Seed Google OAuth configuration for platform authentication
-- Created: 2025-11-28

-- Insert Google OAuth config for platform SSO
-- Note: client_id and client_secret should be updated via environment or direct DB update
INSERT INTO product_auth_config (
    product_id,
    provider_id,
    auth_type,
    client_id,
    client_secret,
    authorization_url,
    token_url,
    userinfo_url,
    revoke_url,
    scopes,
    redirect_uri,
    additional_params,
    is_active
) VALUES (
    NULL,
    (SELECT id FROM provider WHERE slug = 'google-workspace'),
    'oauth2',
    '',
    '',
    'https://accounts.google.com/o/oauth2/v2/auth',
    'https://oauth2.googleapis.com/token',
    'https://openidconnect.googleapis.com/v1/userinfo',
    'https://oauth2.googleapis.com/revoke',
    '["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]',
    NULL,
    '{}',
    TRUE
) ON CONFLICT DO NOTHING;

-- Record this migration
INSERT INTO schema_migrations (version, name) 
VALUES ('004', 'seed_google_oauth_config')
ON CONFLICT (version) DO NOTHING;
