import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from Szablony_lib import Szablony

class TestSlotImageInsertion(unittest.TestCase):
    def setUp(self):
        self.sz = Szablony()
        self.sz.generuj_siatke(kolumny=2, wiersze=2)

    def test_single_slot_image_insertion_image_source(self):
        self.sz.wstaw_obrazek(0, "kolo.jpg", image_source="obrazy_stale")
        slot = self.sz.sloty[0]
        self.assertEqual(slot["image_path"], "kolo.jpg")
        self.assertEqual(slot["image_source"], "obrazy_stale")
        self.assertNotIn("kolaz", slot)

    def test_single_slot_image_insertion_source_alias(self):
        # Should accept source= as alias without throwing TypeError
        self.sz.wstaw_obrazek(1, "trojkat.jpg", source="obrazy_stale")
        slot = self.sz.sloty[1]
        self.assertEqual(slot["image_path"], "trojkat.jpg")
        self.assertEqual(slot["image_source"], "obrazy_stale")

    def test_overwrite_collage_with_single_image(self):
        # Create collage first
        self.sz.wklej_jeden_obraz_na_kolaz(0, "kolo.jpg", ilosc=4)
        self.assertIn("kolaz", self.sz.sloty[0])

        # Overwrite with single image
        self.sz.wstaw_obrazek(0, "kwadrat.jpg", image_source="obrazy")
        slot = self.sz.sloty[0]
        self.assertEqual(slot["image_path"], "kwadrat.jpg")
        self.assertEqual(slot["image_source"], "obrazy")
        self.assertNotIn("kolaz", slot)

    def test_image_clears_existing_text(self):
        # Set text / random number first
        self.sz.losuj_liczby_bez_powtorzen(1, 10, slots=[0])
        self.assertIn("tekst", self.sz.sloty[0])

        # Insert image
        self.sz.wstaw_obrazek(0, "kolo.jpg", image_source="obrazy_stale")
        self.assertNotIn("tekst", self.sz.sloty[0])
        self.assertNotIn("text", self.sz._computed.get(0, {}))
        self.assertEqual(self.sz.sloty[0]["image_path"], "kolo.jpg")

    def test_text_clears_existing_image(self):
        # Insert image first
        self.sz.wstaw_obrazek(0, "kolo.jpg", image_source="obrazy_stale")
        self.assertEqual(self.sz.sloty[0]["image_path"], "kolo.jpg")

        # Set text
        self.sz.ustaw_tekst_wszystkim({"typ": "manual", "value": "TEST"}, slots=[0])
        self.assertNotIn("image_path", self.sz.sloty[0])
        self.assertNotIn("image_path", self.sz._computed.get(0, {}))
        self.assertEqual(self.sz.sloty[0]["tekst"]["value"], "TEST")

    def test_wyczysc_obraz(self):
        self.sz.wstaw_obrazek(0, "kolo.jpg", image_source="obrazy_stale")
        self.assertEqual(self.sz.sloty[0]["image_path"], "kolo.jpg")

        self.sz.wyczysc_obraz(0)
        self.assertNotIn("image_path", self.sz.sloty[0])
        self.assertNotIn("image_source", self.sz.sloty[0])
        self.assertNotIn("image_path", self.sz._computed.get(0, {}))

    def test_wyczysc_tekst(self):
        self.sz.ustaw_tekst_wszystkim({"typ": "manual", "value": "ABC"}, slots=[1])
        self.assertEqual(self.sz.sloty[1]["tekst"]["value"], "ABC")

        self.sz.wyczysc_tekst(1)
        self.assertNotIn("tekst", self.sz.sloty[1])
        self.assertNotIn("text", self.sz._computed.get(1, {}))

    def test_wyczysc_slot_wszystko(self):
        self.sz.wstaw_obrazek(0, "kolo.jpg", image_source="obrazy_stale")
        self.sz.sloty[0]["fill"] = "#ff0000"
        self.sz.sloty[0]["symbol"] = "X"

        self.sz.wyczysc_slot(0, co="wszystko")
        self.assertNotIn("image_path", self.sz.sloty[0])
        self.assertNotIn("symbol", self.sz.sloty[0])
        self.assertIsNone(self.sz.sloty[0]["fill"])

    def test_multi_slot_image_insertion(self):
        self.sz.wstaw_obrazek(slots=[2, 3], sciezka="serce.jpg", image_source="obrazy_stale")
        self.assertEqual(self.sz.sloty[2]["image_path"], "serce.jpg")
        self.assertEqual(self.sz.sloty[2]["image_source"], "obrazy_stale")
        self.assertEqual(self.sz.sloty[3]["image_path"], "serce.jpg")
        self.assertEqual(self.sz.sloty[3]["image_source"], "obrazy_stale")

    def test_render_with_inserted_images(self):
        self.sz.wstaw_obrazek(0, "kolo.jpg", image_source="obrazy_stale")
        self.sz.render_all()
        self.assertIsNotNone(self.sz.img)

if __name__ == "__main__":
    unittest.main()
