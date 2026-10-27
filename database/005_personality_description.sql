-- Run once on existing databases before deploying this version.
ALTER TABLE characters ADD COLUMN IF NOT EXISTS personality_description TEXT NOT NULL DEFAULT '';
