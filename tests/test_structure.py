"""Static smoke checks; full integration tests require Discord and Supabase credentials."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_required_files():
    for name in ('README.md','build.txt','bot.py','Dockerfile','docker-compose.yml','database/schema.sql'):
        assert (ROOT / name).exists(), name

def test_commands_present():
    code = (ROOT / 'bot.py').read_text(encoding='utf-8')
    for command in ('建立角色','角色列表','切換角色','角色設定','刪除角色','角色狀態','聊天','聊天設定','背包','簽到','送禮','探索','任務','收藏','生成角色圖片'):
        assert f"name='{command}'" in code
