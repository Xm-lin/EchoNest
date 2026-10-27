import ast
import unittest
from pathlib import Path

source = (Path(__file__).resolve().parents[1] / 'bot.py').read_text(encoding='utf-8')
module = ast.parse(source)
styles_node = next(n for n in module.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'IMAGE_STYLES' for t in n.targets))
styles = ast.literal_eval(styles_node.value)

class StyleTests(unittest.TestCase):
    def test_all_eight_styles(self):
        self.assertEqual(set(styles), {'anime','realistic','illustration','watercolor','pixel','chibi','fantasy','comic'})
    def test_style_details(self):
        for name, prompt in styles.items():
            with self.subTest(name=name):
                self.assertGreater(len(prompt), 150)
    def test_universal_framing(self):
        self.assertIn('UNIVERSAL FRAMING FOR EVERY STYLE', source)
        self.assertIn('This close camera framing MUST remain identical across', source)
        self.assertIn('distant camera', source)

if __name__ == '__main__': unittest.main()
