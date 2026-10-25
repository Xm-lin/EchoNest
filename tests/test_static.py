import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'bot.py').read_text()
module = ast.parse(source)
commands = [node for node in module.body if isinstance(node, ast.AsyncFunctionDef)
            and any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                    and d.func.attr == 'command' for d in node.decorator_list)]
assert len(commands) == 9, [n.name for n in commands]
for command in commands:
    assert any(isinstance(d, ast.Name) and d.id == 'command' for d in command.decorator_list), command.name
assert 'authorizing_integration_owners or {}' not in source
assert 'discord.Attachment' in source
assert 'system_message' in source
assert 'CREATE TABLE IF NOT EXISTS bot_characters' in (ROOT / 'database.py').read_text()
assert 'CREATE TABLE IF NOT EXISTS bot_memories' in (ROOT / 'database.py').read_text()
print('Static tests passed: 9 slash commands, attachment support, isolated schema')
