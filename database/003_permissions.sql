-- Run once in Supabase SQL editor before deploying this version.
-- Back up the database first. Existing characters remain available to everyone.
ALTER TABLE characters ADD COLUMN IF NOT EXISTS access_mode TEXT NOT NULL DEFAULT 'everyone';
CREATE TABLE IF NOT EXISTS character_access (
 character_id BIGINT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 user_id BIGINT NOT NULL,
 PRIMARY KEY(character_id,user_id)
);
CREATE TABLE IF NOT EXISTS user_preferences (
 user_id BIGINT PRIMARY KEY,
 private_replies BOOLEAN NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS character_invites (
 character_id BIGINT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 invitee_id BIGINT NOT NULL,
 inviter_id BIGINT NOT NULL,
 PRIMARY KEY(character_id,invitee_id)
);
CREATE TABLE IF NOT EXISTS character_shares (
 character_id BIGINT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 user_id BIGINT NOT NULL,
 PRIMARY KEY(character_id,user_id)
);
