-- Backup your database before applying. This migration is additive and preserves existing rows.
ALTER TABLE IF EXISTS characters ADD COLUMN IF NOT EXISTS image_url TEXT NOT NULL DEFAULT '';
ALTER TABLE IF EXISTS chat_settings ADD COLUMN IF NOT EXISTS unanswered INTEGER NOT NULL DEFAULT 0;
CREATE TABLE IF NOT EXISTS explorations (
 scope_type TEXT NOT NULL, scope_id BIGINT NOT NULL, user_id BIGINT NOT NULL,
 day DATE NOT NULL, count INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(scope_type,scope_id,user_id,day)
);
CREATE TABLE IF NOT EXISTS important_memories (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 character_id BIGINT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 tag TEXT NOT NULL, content TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_important_memories ON important_memories(character_id,id DESC);
