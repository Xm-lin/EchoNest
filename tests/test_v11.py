from pathlib import Path
import ast
root = Path(__file__).resolve().parents[1]
s = (root/'bot.py').read_text()
d = (root/'database.py').read_text()
ast.parse(s)
assert 'bot_proactive_settings' in s and 'bot_proactive_settings' in d
assert 'async def proactive_worker' in s
assert 'async def deliver_proactive' in s
assert 'async def proactive_button' in s
assert "'傲嬌': '雌小鬼傲嬌，嘴硬愛捉弄，帶色氣調戲，否認卻會幫忙。'" in s
assert 'c = await asyncio.to_thread(db.one' in s
print('v11 static checks passed')
