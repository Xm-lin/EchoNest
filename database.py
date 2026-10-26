"""PostgreSQL access; v1 tables intentionally separate from legacy tables."""
import os
from contextlib import contextmanager
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

SCHEMA = '''
CREATE TABLE IF NOT EXISTS bot_reply_settings (
 user_id TEXT NOT NULL, command_name TEXT NOT NULL, private BOOLEAN NOT NULL DEFAULT TRUE,
 PRIMARY KEY(user_id,command_name)
);
CREATE TABLE IF NOT EXISTS bot_characters (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 scope TEXT NOT NULL, name TEXT NOT NULL, personality TEXT NOT NULL,
 background TEXT NOT NULL, speaking_style TEXT NOT NULL,
 system_message TEXT NOT NULL, image_path TEXT NOT NULL DEFAULT '',
 mood TEXT NOT NULL DEFAULT '普通', created_by TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS bot_characters_scope_idx ON bot_characters(scope,id);
CREATE TABLE IF NOT EXISTS bot_proactive_settings (
 scope TEXT NOT NULL, user_id TEXT NOT NULL,
 character_id BIGINT NOT NULL REFERENCES bot_characters(id) ON DELETE CASCADE,
 enabled BOOLEAN NOT NULL DEFAULT FALSE,
 frequency TEXT NOT NULL DEFAULT '普通',
 start_hour SMALLINT NOT NULL DEFAULT 9,
 end_hour SMALLINT NOT NULL DEFAULT 22,
 destination TEXT NOT NULL DEFAULT 'dm',
 channel_id BIGINT,
 next_send_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 PRIMARY KEY(scope,user_id,character_id)
);
CREATE TABLE IF NOT EXISTS bot_active (
 scope TEXT NOT NULL, user_id TEXT NOT NULL, character_id BIGINT NOT NULL REFERENCES bot_characters(id) ON DELETE CASCADE,
 PRIMARY KEY(scope,user_id)
);
CREATE TABLE IF NOT EXISTS bot_profiles (
 scope TEXT NOT NULL, user_id TEXT NOT NULL,
 character_id BIGINT NOT NULL REFERENCES bot_characters(id) ON DELETE CASCADE,
 exp INTEGER NOT NULL DEFAULT 0, affection INTEGER NOT NULL DEFAULT 0,
 last_reward_at TIMESTAMPTZ,
 PRIMARY KEY(scope,user_id,character_id)
);
CREATE TABLE IF NOT EXISTS bot_inventory (
 scope TEXT NOT NULL, user_id TEXT NOT NULL, item TEXT NOT NULL,
 quantity INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(scope,user_id,item)
);
CREATE TABLE IF NOT EXISTS bot_checkins (
 scope TEXT NOT NULL, user_id TEXT NOT NULL, day TEXT NOT NULL,
 PRIMARY KEY(scope,user_id)
);
CREATE TABLE IF NOT EXISTS bot_messages (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 scope TEXT NOT NULL, user_id TEXT NOT NULL,
 character_id BIGINT NOT NULL REFERENCES bot_characters(id) ON DELETE CASCADE,
 role TEXT NOT NULL, content TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS bot_messages_owner_idx ON bot_messages(scope,user_id,character_id,id DESC);
CREATE TABLE IF NOT EXISTS bot_memories (
 scope TEXT NOT NULL, user_id TEXT NOT NULL,
 character_id BIGINT NOT NULL REFERENCES bot_characters(id) ON DELETE CASCADE,
 summary TEXT NOT NULL DEFAULT '', last_id BIGINT NOT NULL DEFAULT 0,
 PRIMARY KEY(scope,user_id,character_id)
);
CREATE TABLE IF NOT EXISTS bot_collectibles (
 scope TEXT NOT NULL, user_id TEXT NOT NULL, character_id BIGINT NOT NULL REFERENCES bot_characters(id) ON DELETE CASCADE,
 item TEXT NOT NULL, obtained_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 PRIMARY KEY(scope,user_id,character_id,item)
);
CREATE TABLE IF NOT EXISTS bot_story_pending (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 scope TEXT NOT NULL, user_id TEXT NOT NULL, character_id BIGINT NOT NULL REFERENCES bot_characters(id) ON DELETE CASCADE,
 event_index INTEGER NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
 UNIQUE(scope,user_id,character_id)
);
CREATE TABLE IF NOT EXISTS bot_story_history (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 scope TEXT NOT NULL, user_id TEXT NOT NULL, character_id BIGINT NOT NULL REFERENCES bot_characters(id) ON DELETE CASCADE,
 day TEXT NOT NULL, event_title TEXT NOT NULL, choice TEXT NOT NULL, ending TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS bot_story_daily_idx ON bot_story_history(scope,user_id,character_id,day);
CREATE TABLE IF NOT EXISTS bot_quest_progress (
 scope TEXT NOT NULL, user_id TEXT NOT NULL, character_id BIGINT NOT NULL REFERENCES bot_characters(id) ON DELETE CASCADE,
 week TEXT NOT NULL, action TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(scope,user_id,character_id,week,action)
);
CREATE TABLE IF NOT EXISTS bot_quest_rewards (
 scope TEXT NOT NULL, user_id TEXT NOT NULL, character_id BIGINT NOT NULL REFERENCES bot_characters(id) ON DELETE CASCADE,
 week TEXT NOT NULL, action TEXT NOT NULL,
 PRIMARY KEY(scope,user_id,character_id,week,action)
);
'''

class Database:
    def __init__(self, dsn):
        self.pool = ConnectionPool(dsn, min_size=1, max_size=5, open=False,
                                   kwargs={'row_factory': dict_row, 'autocommit': True})

    def open(self):
        self.pool.open(wait=True, timeout=30)
        with self.pool.connection() as conn:
            with conn.transaction():
                for sql in SCHEMA.split(';'):
                    if sql.strip():
                        conn.execute(sql)

    def one(self, sql, args=()):
        with self.pool.connection() as conn:
            return conn.execute(sql, args).fetchone()

    def all(self, sql, args=()):
        with self.pool.connection() as conn:
            return conn.execute(sql, args).fetchall()

    def run(self, sql, args=()):
        with self.pool.connection() as conn:
            cur = conn.execute(sql, args)
            return cur.rowcount

    @contextmanager
    def transaction(self):
        with self.pool.connection() as conn:
            with conn.transaction():
                yield conn


def connect():
    dsn = os.environ['DATABASE_URL']
    if 'sslmode=' not in dsn:
        dsn += ('&' if '?' in dsn else '?') + 'sslmode=require'
    db = Database(dsn)
    db.open()
    return db
