import ast
import base64
import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import images

class FeatureTests(unittest.TestCase):
    def test_image_validation(self):
        from PIL import Image
        pic = Image.new('RGB', (40, 40), '#00ff00')
        out = io.BytesIO(); pic.save(out, format='PNG')
        result = images.validate_image(out.getvalue())
        self.assertTrue(result.startswith(b'\x89PNG'))

    def test_reject_bad_image(self):
        with self.assertRaises(images.ImageProviderError):
            images.validate_image(b'not a picture')

    def test_62_gifts(self):
        t = ast.parse((ROOT / 'bot.py').read_text())
        gifts = next(n.value for n in t.body if isinstance(n, ast.Assign) and any(isinstance(k, ast.Name) and k.id == 'GIFTS' for k in n.targets))
        self.assertGreaterEqual(len(ast.literal_eval(gifts)), 60)

    def test_required_commands(self):
        t = ast.parse((ROOT / 'bot.py').read_text())
        cmds = set()
        for node in ast.walk(t):
            if isinstance(node, ast.AsyncFunctionDef):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == 'command':
                        cmds.add(next(k.value.value for k in dec.keywords if k.arg == 'name'))
        for command in ['生成角色圖片','角色狀態','聊天','簽到','送禮','探索','任務','收藏','記住','記憶列表','刪除記憶']:
            self.assertIn(command, cmds)

if __name__ == '__main__':
    unittest.main()
