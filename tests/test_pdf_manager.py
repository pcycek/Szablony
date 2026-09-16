import unittest
import os
import sys
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pdf_manager import PDFManager


class TestPDFManager(unittest.TestCase):
    def setUp(self):
        self.temp_files = []
        self.test_dir = BASE_DIR / "tests" / "temp_pdf_test"
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Tworzenie 5 testowych obrazów o różnych kolorach
        self.colors = ["red", "green", "blue", "yellow", "cyan"]
        self.img_paths = []
        for i, color in enumerate(self.colors):
            p = self.test_dir / f"test_img_{i}_{color}.png"
            img = Image.new("RGB", (300, 400), color)
            img.save(p)
            self.img_paths.append(p)
            self.temp_files.append(p)

    def tearDown(self):
        for p in self.temp_files:
            try:
                if Path(p).exists():
                    Path(p).unlink()
            except Exception:
                pass
        try:
            if self.test_dir.exists():
                self.test_dir.rmdir()
        except Exception:
            pass

    def test_01_create_from_images(self):
        manager = PDFManager.from_images(self.img_paths, page_size="A4")
        self.assertEqual(manager.get_page_count(), 5)
        pages_info = manager.get_pages_info()
        self.assertEqual(len(pages_info), 5)
        self.assertEqual(pages_info[0]["page_number"], 1)
        manager.close()

    def test_02_move_page_1_to_5(self):
        """
        Kluczowy test: weryfikacja manewrowania stronami.
        Przenosimy stronę 1 (czerwoną) na pozycję 5.
        Kolejność początkowa: [red, green, blue, yellow, cyan]
        Po przeniesieniu:     [green, blue, yellow, cyan, red]
        """
        manager = PDFManager.from_images(self.img_paths, page_size="fit_image")
        self.assertEqual(manager.get_page_count(), 5)

        # Pobieramy piksel ze środka strony 1 przed zmianą (czerwony)
        prev_1 = manager.get_page_preview(0, dpi=72)
        pix_1 = prev_1.getpixel((150, 200))
        self.assertTrue(pix_1[0] > 240 and pix_1[1] < 10 and pix_1[2] < 10)

        # Przenosimy stronę 1 na pozycję 5 (1-based)
        manager.move_page(from_idx=1, to_idx=5, one_based=True)

        # Po przesunięciu:
        # Nowa strona 1 to dawna strona 2 (green)
        new_page_1 = manager.get_page_preview(0, dpi=72)
        pix_new1 = new_page_1.getpixel((150, 200))
        self.assertTrue(pix_new1[1] > 100 and pix_new1[0] < 20 and pix_new1[2] < 20)

        # Nowa strona 5 to dawna strona 1 (red)
        new_page_5 = manager.get_page_preview(4, dpi=72)
        pix_new5 = new_page_5.getpixel((150, 200))
        self.assertTrue(pix_new5[0] > 240 and pix_new5[1] < 10 and pix_new5[2] < 10)

        manager.close()

    def test_03_move_page_up_and_down(self):
        manager = PDFManager.from_images(self.img_paths, page_size="fit_image")
        
        # Przesuń stronę 3 w górę -> staje się stroną 2
        manager.move_page_up(idx=3, one_based=True)
        # Przesuń stronę 1 w dół -> staje się stroną 2
        manager.move_page_down(idx=1, one_based=True)

        self.assertEqual(manager.get_page_count(), 5)
        manager.close()

    def test_04_rotate_page(self):
        manager = PDFManager.from_images(self.img_paths[:2], page_size="A4")
        self.assertEqual(manager.doc[0].rotation, 0)
        manager.rotate_page(0, angle=90, one_based=False)
        self.assertEqual(manager.doc[0].rotation, 90)
        manager.rotate_page(0, angle=90, one_based=False)
        self.assertEqual(manager.doc[0].rotation, 180)
        manager.close()

    def test_05_delete_page(self):
        manager = PDFManager.from_images(self.img_paths, page_size="A4")
        self.assertEqual(manager.get_page_count(), 5)
        # Usuwamy stronę 2
        manager.delete_page(2, one_based=True)
        self.assertEqual(manager.get_page_count(), 4)
        manager.close()

    def test_06_duplicate_page(self):
        manager = PDFManager.from_images(self.img_paths[:2], page_size="A4")
        self.assertEqual(manager.get_page_count(), 2)
        new_idx = manager.duplicate_page(0, one_based=False)
        self.assertEqual(new_idx, 1)
        self.assertEqual(manager.get_page_count(), 3)
        manager.close()

    def test_07_merge_pdf(self):
        p1 = self.test_dir / "doc1.pdf"
        p2 = self.test_dir / "doc2.pdf"
        self.temp_files.extend([p1, p2])

        m1 = PDFManager.from_images(self.img_paths[:2], page_size="A4")
        m1.save(p1)
        m1.close()

        m2 = PDFManager.from_images(self.img_paths[2:5], page_size="A4")
        m2.save(p2)
        m2.close()

        merged = PDFManager(p1)
        self.assertEqual(merged.get_page_count(), 2)
        merged.merge_pdf(p2)
        self.assertEqual(merged.get_page_count(), 5)
        merged.close()

    def test_08_save_and_reload(self):
        out_pdf = self.test_dir / "saved_test.pdf"
        self.temp_files.append(out_pdf)

        manager = PDFManager.from_images(self.img_paths, page_size="A4")
        manager.move_page(1, 5, one_based=True)
        manager.rotate_page(4, 90, one_based=False)
        manager.save(out_pdf)
        manager.close()

        self.assertTrue(out_pdf.exists())
        self.assertGreater(out_pdf.stat().st_size, 1000)

        # Wczytujemy z powrotem
        reloaded = PDFManager(out_pdf)
        self.assertEqual(reloaded.get_page_count(), 5)
        self.assertEqual(reloaded.doc[4].rotation, 90)
        reloaded.close()

    def test_09_thumbnails_and_preview(self):
        manager = PDFManager.from_images(self.img_paths[:1], page_size="A4")
        thumb = manager.get_page_thumbnail(0, max_size=(100, 150))
        self.assertIsInstance(thumb, Image.Image)
        self.assertLessEqual(thumb.width, 100)
        self.assertLessEqual(thumb.height, 150)

        prev = manager.get_page_preview(0, dpi=100)
        self.assertIsInstance(prev, Image.Image)
        self.assertGreater(prev.width, 500)
        manager.close()

    def test_10_auto_orientation_from_image_dimensions(self):
        """Sprawdza czy strona jest automatycznie pozioma gdy obraz jest poziomy i pionowa gdy obraz pionowy."""
        landscape_img = self.test_dir / "land.png"
        portrait_img = self.test_dir / "port.png"
        self.temp_files.extend([landscape_img, portrait_img])

        Image.new("RGB", (800, 400), "blue").save(landscape_img)
        Image.new("RGB", (400, 800), "red").save(portrait_img)

        manager = PDFManager.from_images([landscape_img, portrait_img], page_size="A4", orientation="auto")
        self.assertEqual(manager.get_page_count(), 2)

        info = manager.get_pages_info()
        # Strona 1: obraz 800x400 -> strona pozioma (landscape: width > height)
        self.assertTrue(info[0]["is_landscape"])
        self.assertGreater(info[0]["width"], info[0]["height"])

        # Strona 2: obraz 400x800 -> strona pionowa (portrait: height > width)
        self.assertFalse(info[1]["is_landscape"])
        self.assertGreater(info[1]["height"], info[1]["width"])

        manager.close()

    def test_11_auto_orient_pages_and_toggle(self):
        """Sprawdza działanie auto_orient_pages oraz toggle_page_orientation."""
        landscape_img = self.test_dir / "land2.png"
        self.temp_files.append(landscape_img)
        Image.new("RGB", (600, 300), "green").save(landscape_img)

        manager = PDFManager()
        # Celowo dodajemy jako portrait wymuszając orientation="portrait"
        manager.add_image_page(landscape_img, page_size="A4", orientation="portrait")
        info_before = manager.get_pages_info()
        self.assertFalse(info_before[0]["is_landscape"])

        # Uruchamiamy auto_orient_pages - powinno wykryć poziomy obraz i obrócić stronę
        changed = manager.auto_orient_pages()
        self.assertEqual(changed, 1)

        info_after = manager.get_pages_info()
        self.assertTrue(info_after[0]["is_landscape"])

        # Przełączenie orientacji toggle_page_orientation
        manager.toggle_page_orientation(0, one_based=False)
        info_toggled = manager.get_pages_info()
        self.assertFalse(info_toggled[0]["is_landscape"])

        manager.close()


if __name__ == "__main__":
    unittest.main()

