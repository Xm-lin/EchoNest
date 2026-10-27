import ast
import unittest
from pathlib import Path

class PortraitPromptTests(unittest.TestCase):
    def test_slash_command_has_three_fields(self):
        source = (Path(__file__).resolve().parents[1] / 'bot.py').read_text()
        tree = ast.parse(source)
        command = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'character_image')
        self.assertEqual([a.arg for a in command.args.args], ['i', '人物形容', '風格', '動作'])

    def test_prompt_contains_head_only_constraints(self):
        source = (Path(__file__).resolve().parents[1] / 'bot.py').read_text()
        self.assertIn('Extreme close-up head-and-neck portrait', source)
        self.assertIn('POSE AND ACTION:', source)
        self.assertIn('no full-body, no half-body', source)

if __name__ == '__main__':
    unittest.main()
