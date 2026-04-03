-- Sprint 3B: Google OAuth token storage for GSC/GA4

CREATE TABLE IF NOT EXISTS google_tokens (
    id SERIAL PRIMARY KEY,
    property_url TEXT NOT NULL,                -- GSC property URL (e.g. "https://example.com/")
    ga4_property_id TEXT,                      -- GA4 property (e.g. "properties/123456789")
    encrypted_tokens TEXT NOT NULL,            -- Fernet-encrypted JSON blob
    email TEXT,                                -- Google account email (for display)
    scopes TEXT,                               -- comma-separated granted scopes
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(property_url)
);

CREATE INDEX IF NOT EXISTS idx_google_tokens_property ON google_tokens(property_url);
