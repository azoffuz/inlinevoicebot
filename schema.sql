-- Supabase Database Schema for Inline Voice Bot

-- 1. Voices table (Ovozlar jadvali)
CREATE TABLE IF NOT EXISTS voices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    file_id TEXT NOT NULL,
    file_unique_id TEXT UNIQUE,
    channel_message_id BIGINT,
    duration INTEGER DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    created_by BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Bot Admins table (Adminlar jadvali)
CREATE TABLE IF NOT EXISTS bot_admins (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    role TEXT DEFAULT 'admin', -- 'superadmin' yoki 'admin'
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Bot Users table (Foydalanuvchilar va statistika)
CREATE TABLE IF NOT EXISTS bot_users (
    user_id BIGINT PRIMARY KEY,
    first_name TEXT,
    username TEXT,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tezkor qidiruv va tartiblash uchun indexlar
CREATE INDEX IF NOT EXISTS idx_voices_usage ON voices (usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_voices_created_at ON voices (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_voices_title ON voices USING gin(to_tsvector('simple', title));

-- RLS (Row Level Security) - Service role kaliti ishlatilganda hamma huquq bor
ALTER TABLE voices ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow service role full access to voices" ON voices
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow service role full access to bot_admins" ON bot_admins
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow service role full access to bot_users" ON bot_users
    FOR ALL USING (true) WITH CHECK (true);
