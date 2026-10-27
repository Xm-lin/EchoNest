CREATE TABLE IF NOT EXISTS characters (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), scope_type TEXT NOT NULL CHECK(scope_type IN ('dm','guild')),
 scope_id TEXT NOT NULL, owner_id TEXT NOT NULL, name VARCHAR(60) NOT NULL,
 personality TEXT NOT NULL, custom_personality TEXT, sensitivity TEXT NOT NULL DEFAULT 'medium',
 mood INTEGER NOT NULL DEFAULT 70 CHECK(mood BETWEEN 0 AND 100),
 exp BIGINT NOT NULL DEFAULT 0 CHECK(exp>=0), level INTEGER NOT NULL DEFAULT 1 CHECK(level>=1),
 image_path TEXT, status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','deleting')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(id,scope_type,scope_id)
);
CREATE INDEX IF NOT EXISTS idx_characters_scope ON characters(scope_type,scope_id,status);
CREATE TABLE IF NOT EXISTS selected_characters (
 scope_type TEXT NOT NULL, scope_id TEXT NOT NULL, user_id TEXT NOT NULL,
 character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 PRIMARY KEY(scope_type,scope_id,user_id)
);
CREATE TABLE IF NOT EXISTS affection (
 character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE, user_id TEXT NOT NULL,
 points INTEGER NOT NULL DEFAULT 0 CHECK(points>=0), last_reward_at TIMESTAMPTZ,
 reward_day DATE, reward_count INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(character_id,user_id)
);
CREATE TABLE IF NOT EXISTS chat_messages (
 id BIGSERIAL PRIMARY KEY, character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 user_id TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('user','assistant')),
 content TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_char ON chat_messages(character_id,id DESC);
CREATE TABLE IF NOT EXISTS memory_summaries (
 character_id UUID PRIMARY KEY REFERENCES characters(id) ON DELETE CASCADE,
 summary TEXT NOT NULL DEFAULT '', through_id BIGINT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS important_memories (
 id BIGSERIAL PRIMARY KEY, character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 user_id TEXT NOT NULL, content TEXT NOT NULL, tags TEXT[] NOT NULL DEFAULT '{}',
 importance INTEGER NOT NULL DEFAULT 1, updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_memories_char ON important_memories(character_id);
CREATE TABLE IF NOT EXISTS inventories (
 scope_type TEXT NOT NULL, scope_id TEXT NOT NULL, user_id TEXT NOT NULL,
 item_id TEXT NOT NULL, quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity>=0),
 PRIMARY KEY(scope_type,scope_id,user_id,item_id)
);
CREATE TABLE IF NOT EXISTS checkins (
 scope_type TEXT NOT NULL, scope_id TEXT NOT NULL, user_id TEXT NOT NULL,
 checkin_date DATE NOT NULL, PRIMARY KEY(scope_type,scope_id,user_id,checkin_date)
);
CREATE TABLE IF NOT EXISTS gifts (
 id BIGSERIAL PRIMARY KEY, character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 user_id TEXT NOT NULL, item_id TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS explorations (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 user_id TEXT NOT NULL, step INTEGER NOT NULL DEFAULT 0, choices JSONB NOT NULL DEFAULT '[]',
 status TEXT NOT NULL DEFAULT 'active', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_active_exploration ON explorations(character_id,user_id) WHERE status='active';
CREATE TABLE IF NOT EXISTS quest_claims (
 scope_type TEXT NOT NULL, scope_id TEXT NOT NULL, user_id TEXT NOT NULL,
 quest_id TEXT NOT NULL, character_id UUID REFERENCES characters(id) ON DELETE CASCADE,
 claimed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(scope_type,scope_id,user_id,quest_id)
);
CREATE TABLE IF NOT EXISTS collections (
 scope_type TEXT NOT NULL, scope_id TEXT NOT NULL, user_id TEXT NOT NULL,
 collectible_id TEXT NOT NULL, character_id UUID REFERENCES characters(id) ON DELETE CASCADE,
 acquired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(scope_type,scope_id,user_id,collectible_id)
);
CREATE TABLE IF NOT EXISTS chat_settings (
 user_id TEXT PRIMARY KEY, enabled BOOLEAN NOT NULL DEFAULT false,
 frequency TEXT NOT NULL DEFAULT 'rare' CHECK(frequency IN ('rare','normal','active')),
 quiet_start INTEGER NOT NULL DEFAULT 23 CHECK(quiet_start BETWEEN 0 AND 23),
 quiet_end INTEGER NOT NULL DEFAULT 8 CHECK(quiet_end BETWEEN 0 AND 23),
 last_chat_at TIMESTAMPTZ, unanswered INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS jobs (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), job_type TEXT NOT NULL, character_id UUID REFERENCES characters(id) ON DELETE CASCADE,
 payload JSONB NOT NULL DEFAULT '{}', state TEXT NOT NULL DEFAULT 'pending',
 attempts INTEGER NOT NULL DEFAULT 0, due_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 locked_until TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ai_usage (
 day DATE PRIMARY KEY, tokens BIGINT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS deletion_tombstones (
 character_id UUID PRIMARY KEY, deleted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS storage_cleanup(path TEXT PRIMARY KEY,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS proactive_sends(id BIGSERIAL PRIMARY KEY,user_id TEXT NOT NULL,day DATE NOT NULL,slot INTEGER NOT NULL,status TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(user_id,day,slot));
CREATE INDEX IF NOT EXISTS idx_proactive_user_day ON proactive_sends(user_id,day);

CREATE TABLE IF NOT EXISTS daily_chat_counts(
 scope_type TEXT NOT NULL,scope_id TEXT NOT NULL,user_id TEXT NOT NULL,day DATE NOT NULL,
 count INTEGER NOT NULL DEFAULT 0 CHECK(count>=0),
 PRIMARY KEY(scope_type,scope_id,user_id,day)
);
