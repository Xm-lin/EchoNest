-- Run once in a NEW Supabase project. Re-running is safe.
CREATE TABLE IF NOT EXISTS characters (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 scope_type TEXT NOT NULL CHECK (scope_type IN ('dm','guild')),
 scope_id BIGINT NOT NULL,
 owner_id BIGINT NOT NULL,
 name TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 40),
 personality TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 mood INTEGER NOT NULL DEFAULT 70 CHECK (mood BETWEEN 0 AND 100),
 exp INTEGER NOT NULL DEFAULT 0 CHECK (exp >= 0),
 level INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
 status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','deleting')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_characters_scope ON characters(scope_type,scope_id,status);
CREATE TABLE IF NOT EXISTS selections (
 scope_type TEXT NOT NULL CHECK (scope_type IN ('dm','guild')),
 scope_id BIGINT NOT NULL,
 user_id BIGINT NOT NULL,
 character_id BIGINT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 PRIMARY KEY(scope_type,scope_id,user_id)
);
CREATE TABLE IF NOT EXISTS affection (
 character_id BIGINT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 user_id BIGINT NOT NULL,
 points INTEGER NOT NULL DEFAULT 0,
 last_reward_at TIMESTAMPTZ,
 reward_day DATE,
 reward_count INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(character_id,user_id)
);
CREATE TABLE IF NOT EXISTS chat_messages (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 character_id BIGINT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 user_id BIGINT,
 role TEXT NOT NULL CHECK (role IN ('user','assistant')),
 content TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chat_character ON chat_messages(character_id,id DESC);
CREATE TABLE IF NOT EXISTS chat_settings (
 user_id BIGINT PRIMARY KEY,
 proactive_enabled BOOLEAN NOT NULL DEFAULT false,
 frequency TEXT NOT NULL DEFAULT 'occasional' CHECK(frequency IN ('occasional','normal','active')),
 quiet_start SMALLINT NOT NULL DEFAULT 23 CHECK(quiet_start BETWEEN 0 AND 23),
 quiet_end SMALLINT NOT NULL DEFAULT 8 CHECK(quiet_end BETWEEN 0 AND 23),
 last_chat_at TIMESTAMPTZ,
 last_proactive_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS inventories (
 scope_type TEXT NOT NULL,
 scope_id BIGINT NOT NULL,
 user_id BIGINT NOT NULL,
 item TEXT NOT NULL,
 quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
 PRIMARY KEY(scope_type,scope_id,user_id,item)
);
CREATE TABLE IF NOT EXISTS checkins (
 scope_type TEXT NOT NULL,
 scope_id BIGINT NOT NULL,
 user_id BIGINT NOT NULL,
 day DATE NOT NULL,
 PRIMARY KEY(scope_type,scope_id,user_id,day)
);
CREATE TABLE IF NOT EXISTS quests (
 scope_type TEXT NOT NULL,
 scope_id BIGINT NOT NULL,
 user_id BIGINT NOT NULL,
 day DATE NOT NULL,
 claimed BOOLEAN NOT NULL DEFAULT false,
 PRIMARY KEY(scope_type,scope_id,user_id,day)
);
CREATE TABLE IF NOT EXISTS collections (
 scope_type TEXT NOT NULL,
 scope_id BIGINT NOT NULL,
 user_id BIGINT NOT NULL,
 key TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(scope_type,scope_id,user_id,key)
);
CREATE TABLE IF NOT EXISTS memories (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 character_id BIGINT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 summary TEXT NOT NULL DEFAULT '',
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(character_id)
);
