import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_fifteen_commands_and_autocomplete():
    tree=ast.parse((ROOT/'bot.py').read_text())
    commands=[]
    for node in ast.walk(tree):
        if isinstance(node,(ast.AsyncFunctionDef,ast.FunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec,ast.Call) and isinstance(dec.func,ast.Attribute) and dec.func.attr=='command':
                    if dec.args: continue
                    for kw in dec.keywords:
                        if kw.arg=='name' and isinstance(kw.value,ast.Constant):commands.append(kw.value.value)
    assert len(commands)==15,commands
    assert len(set(commands))==15
    assert '生成角色圖片' in commands
    assert '送禮' in commands


def test_docs_and_schema():
    readme=(ROOT/'README.md').read_text()
    build=(ROOT/'build.txt').read_text()
    assert '[指令列表](#指令列表)' in readme
    assert 'DATABASE_URL' not in readme
    assert 'DATABASE_URL' in build
    assert 'Render' in build
    assert 'v12' not in readme and 'v12' not in build
    schema=(ROOT/'database/schema.sql').read_text()
    for name in ('characters','daily_chat_counts','storage_cleanup','proactive_sends','important_memories'):
        assert f'CREATE TABLE IF NOT EXISTS {name}' in schema


def test_gifts():
    text=(ROOT/'src/core.py').read_text()
    tree=ast.parse(text)
    assign=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='GIFT_CATEGORIES' for t in n.targets))
    categories=ast.literal_eval(assign.value)
    assert len(categories)==10
    assert sum(len(v) for v in categories.values())>=60
