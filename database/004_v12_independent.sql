-- Backup first. Apply AFTER 003_permissions.sql and upgrade_existing.sql.
-- Existing guild-level character experience is retained in characters for rollback,
-- but new player progress starts independently at level 1.
CREATE TABLE IF NOT EXISTS player_progress (
 character_id BIGINT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 user_id BIGINT NOT NULL, exp INTEGER NOT NULL DEFAULT 0, level INTEGER NOT NULL DEFAULT 1,
 mood INTEGER NOT NULL DEFAULT 70 CHECK(mood BETWEEN 0 AND 100),
 PRIMARY KEY(character_id,user_id)
);
CREATE TABLE IF NOT EXISTS player_memories (
 character_id BIGINT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 user_id BIGINT NOT NULL, summary TEXT NOT NULL DEFAULT '', updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(character_id,user_id)
);
CREATE TABLE IF NOT EXISTS character_favorites (
 character_id BIGINT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
 user_id BIGINT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(character_id,user_id)
);
ALTER TABLE important_memories ADD COLUMN IF NOT EXISTS user_id BIGINT;
-- Assign old shared memories to original character owner, preventing cross-player leakage.
UPDATE important_memories m SET user_id=c.owner_id FROM characters c
 WHERE m.character_id=c.id AND m.user_id IS NULL;
ALTER TABLE important_memories ALTER COLUMN user_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_important_player ON important_memories(character_id,user_id,id DESC);
-- Do not delete old shared memories or shares without a backup.
-- Existing inventory rows are consolidated into a single per-user DM inventory.
INSERT INTO inventories(scope_type,scope_id,user_id,item,quantity)
 SELECT 'dm',user_id,user_id,item,SUM(quantity)::integer FROM inventories
 WHERE NOT(scope_type='dm' AND scope_id=user_id)
 GROUP BY user_id,item
 ON CONFLICT(scope_type,scope_id,user_id,item) DO UPDATE SET quantity=inventories.quantity+EXCLUDED.quantity;
DELETE FROM inventories WHERE NOT(scope_type='dm' AND scope_id=user_id);
-- Old per-guild check-in/exploration counts are not merged; daily limits now use per-user rows.
