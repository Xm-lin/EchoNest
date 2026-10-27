import io
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from character_card import render_card
from images import validate_image, ImageProviderError

class CardTests(unittest.TestCase):
    def test_card_is_png(self):
        card=render_card('測試角色','溫柔','123456',70,12,2,135)
        self.assertTrue(card.read(8).startswith(b'\x89PNG'))
    def test_bad_image_rejected(self):
        with self.assertRaises(ImageProviderError):validate_image(b'not an image')

if __name__=='__main__':unittest.main()
