from pathlib import Path
root = Path(__file__).resolve().parents[1]
bot = (root / 'bot.py').read_text(encoding='utf-8')
schema = (root / 'database/schema.sql').read_text(encoding='utf-8')
assert bot.count('@bot.tree.command(') == 15
for name in ('characters','chat_settings','selections','affection','inventories','checkins','quests','collections','memories'):
    assert f'CREATE TABLE IF NOT EXISTS {name}' in schema
print('Static project checks passed')
