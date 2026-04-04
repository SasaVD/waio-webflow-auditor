-- Migration 006: Authentication system — users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),           -- NULL for Google OAuth-only users
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',      -- 'admin' or 'user'
    auth_provider VARCHAR(50) DEFAULT 'email',  -- 'email' or 'google'
    google_id VARCHAR(255) UNIQUE,
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL;
