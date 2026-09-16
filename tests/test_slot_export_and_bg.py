import unittest
import sys
import os
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from Szablony_lib import Szablony
from paths import OBRAZY_DIR, OBRAZY_STALE_DIR, PROJEKTY_DIR

class TestSlotExportAndBackground(unittest.TestCase):
    def setUp(self):
        self.sz = Szablony()
        self.sz.nowy_projekt("TestExport", 400, 300)
        self.sz.dodaj_slot([10, 10, 110, 110], fill="red")
        self.sz.dodaj_slot([120, 10, 220, 110], fill="green")
        self.sz.dodaj_slot([230, 10, 330, 110], fill="blue")
        self.created_files = []

    def tearDown(self):
        for p in self.created_files:
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass

    def test_background_image_setting_and_render(self):
        bg = Image.new("RGB", (400, 300), "yellow")
        self.sz.ustaw_obraz_tla(bg, dopasuj_rozmiar=True)
        self.assertEqual(self.sz.szerokosc, 400)
        self.assertEqual(self.sz.wysokosc, 300)
        self.assertIsNotNone(self.sz.obraz_tla)
        self.sz.render_all()
        # Pixel at (0, 0) should be yellow (background)
        pixel_bg = self.sz.img.getpixel((0, 0))
        self.assertEqual(pixel_bg, (255, 255, 0))
        # Pixel inside slot 0 (50, 50) should be red
        pixel_slot0 = self.sz.img.getpixel((50, 50))
        self.assertEqual(pixel_slot0, (255, 0, 0))

    def test_background_image_clear(self):
        bg = Image.new("RGB", (400, 300), "yellow")
        self.sz.ustaw_obraz_tla(bg)
        self.assertIsNotNone(self.sz.obraz_tla)
        self.sz.wyczysc_obraz_tla()
        self.assertIsNone(self.sz.obraz_tla)

    def test_background_image_undo_redo(self):
        bg = Image.new("RGB", (400, 300), "yellow")
        self.sz.ustaw_obraz_tla(bg)
        self.assertIsNotNone(self.sz.obraz_tla)
        self.sz.undo()
        self.assertIsNone(self.sz.obraz_tla)
        self.sz.redo()
        self.assertIsNotNone(self.sz.obraz_tla)

    def test_large_background_image_retains_full_resolution(self):
        # Sprawdzamy czy duży obraz (np. 2560x1440) nie zostaje zmniejszony do 1000x750
        large_bg = Image.new("RGB", (2560, 1440), "cyan")
        self.sz.ustaw_obraz_tla(large_bg, dopasuj_rozmiar=True)
        self.assertEqual(self.sz.szerokosc, 2560)
        self.assertEqual(self.sz.wysokosc, 1440)
        self.sz.render_all()
        self.assertEqual(self.sz.img.size, (2560, 1440))
        self.assertEqual(self.sz.img.getpixel((0, 0)), (0, 255, 255))

    def test_export_single_slot_with_custom_name(self):
        saved = self.sz.zapisz_zawartosc_slotow(
            slots=[0],
            docelowy_folder="obrazy",
            nazwy="moj_czerwony_kwadrat",
            bez_ramek=True
        )
        self.created_files.extend(saved)
        self.assertEqual(len(saved), 1)
        expected_path = OBRAZY_DIR / "moj_czerwony_kwadrat.jpg"
        self.assertEqual(saved[0], expected_path)
        self.assertTrue(expected_path.exists())

        # Verify image dimensions (100x100)
        with Image.open(expected_path) as im:
            self.assertEqual(im.size, (100, 100))
            self.assertEqual(im.format, "JPEG")

    def test_export_single_slot_to_obrazy_stale(self):
        saved = self.sz.zapisz_zawartosc_slotow(
            slots=[1],
            docelowy_folder="obrazy_stale",
            nazwy="zielony",
            bez_ramek=True
        )
        self.created_files.extend(saved)
        self.assertEqual(len(saved), 1)
        expected_path = OBRAZY_STALE_DIR / "zielony.jpg"
        self.assertEqual(saved[0], expected_path)
        self.assertTrue(expected_path.exists())

    def test_export_multiple_selected_slots_numbering(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            saved = self.sz.zapisz_zawartosc_slotow(
                slots=[1, 2],
                docelowy_folder=tmppath,
                start_index=0,
                bez_ramek=True
            )
            self.assertEqual(len(saved), 2)
            self.assertEqual(saved[0], tmppath / "0.jpg")
            self.assertEqual(saved[1], tmppath / "1.jpg")
            self.assertTrue(saved[0].exists())
            self.assertTrue(saved[1].exists())

    def test_export_all_slots(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            saved = self.sz.zapisz_zawartosc_slotow(
                slots=None,
                docelowy_folder=tmppath,
                start_index=0,
                bez_ramek=True
            )
            self.assertEqual(len(saved), 3)
            self.assertEqual(saved[0], tmppath / "0.jpg")
            self.assertEqual(saved[1], tmppath / "1.jpg")
            self.assertEqual(saved[2], tmppath / "2.jpg")
            for p in saved:
                self.assertTrue(p.exists())

    def test_export_from_background_crop(self):
        # Test drawing slots over a background and exporting crops
        bg = Image.new("RGB", (400, 300), "white")
        # Draw some specific colored pixels on bg
        for x in range(10, 110):
            for y in range(10, 110):
                bg.putpixel((x, y), (123, 45, 67))
        
        # New project with background and transparent slots (fill=None)
        self.sz.nowy_projekt("BgCropTest", 400, 300)
        self.sz.ustaw_obraz_tla(bg)
        self.sz.dodaj_slot([10, 10, 110, 110], fill=None, outline="black")

        saved = self.sz.zapisz_zawartosc_slotow(
            slots=[0],
            docelowy_folder="obrazy",
            nazwy="crop_test",
            bez_ramek=True
        )
        self.created_files.extend(saved)
        self.assertEqual(len(saved), 1)
        with Image.open(saved[0]) as im:
            self.assertEqual(im.size, (100, 100))
            # Center pixel should match the background
            px = im.getpixel((50, 50))
            self.assertEqual(px, (123, 45, 67))

if __name__ == "__main__":
    unittest.main()
