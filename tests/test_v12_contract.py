from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BOT=(ROOT/'bot.py').read_text()
SQL=(ROOT/'database/004_v12_independent.sql').read_text()

def test_no_sharing_commands():
    for command in ['邀請角色','接受邀請','轉移所有權']:
        assert f"@bot.tree.command(name='{command}'" not in BOT

def test_private_role_only_owner():
    assert "return c['owner_id'] == i.user.id and i.guild_id is None" in BOT

def test_player_chat_history():
    assert 'WHERE character_id=$1 AND user_id=$2 ORDER BY id DESC LIMIT 20' in BOT

def test_player_memories():
    assert 'CREATE TABLE IF NOT EXISTS player_memories' in SQL
    assert 'user_id=$2' in BOT

def test_player_progress():
    assert 'CREATE TABLE IF NOT EXISTS player_progress' in SQL
    assert 'mood INTEGER' in SQL

def test_gift_ui():
    assert 'class GiftView' in BOT and 'class GiftSelect' in BOT
    assert 'quantity=quantity-1' in BOT

def test_explore_limit():
    assert 'explorations.count<5' in BOT
    assert 'if random.random()<0.85 else None' in BOT

def test_favorites():
    assert 'CREATE TABLE IF NOT EXISTS character_favorites' in SQL
    assert "@bot.tree.command(name='收藏角色'" in BOT
