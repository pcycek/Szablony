import os
import sys
import unittest
from pathlib import Path
import json
import shutil

# Dynamic setup of paths
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from Szablony_lib import Szablony
from word_task import WordTask
from paths import PROJEKTY_DIR, OBRAZY_STALE_DIR, OBRAZY_DIR, TEKSTY_DIR, DO_DRUKU_DIR, napraw_sciezke

class TestWordTaskComprehensive(unittest.TestCase):
    def setUp(self):
        # Sample word file
        self.sample_words_file = TEKSTY_DIR / "test_slowa_demo.txt"
        with open(self.sample_words_file, "w", encoding="utf-8") as f:
            f.write("MAMA\nKASA\nMAK\nSAM\nKOT\n")

    def tearDown(self):
        if self.sample_words_file.exists():
            self.sample_words_file.unlink()

    # -------------------------------------------------------------
    # TEST 1: Detekcja unikalnych liter z TXT w kolejności 1. wystąpienia
    # -------------------------------------------------------------
    def test_01_unique_letters_first_occurrence_order(self):
        words = WordTask.load_words(str(self.sample_words_file))
        self.assertEqual(words, ["MAMA", "KASA", "MAK", "SAM", "KOT"])

        letters = WordTask.extract_unique_letters(words)
        # MAMA -> M, A
        # KASA -> K, S
        # MAK -> (already M, A, K)
        # SAM -> (already S, A, M)
        # KOT -> O, T
        self.assertEqual(letters, ["M", "A", "K", "S", "O", "T"])

    # -------------------------------------------------------------
    # TEST 2: Mapowanie liter na symbole dla słowa (np. MAMA -> [koło, trójkąt, koło, trójkąt])
    # -------------------------------------------------------------
    def test_02_map_word_to_symbols(self):
        mapping = {
            "M": "kolo.jpg",
            "A": "trojkat.jpg",
            "K": "kwadrat.jpg",
            "S": "serce.jpg"
        }
        symbols_seq = WordTask.map_word_to_symbols("MAMA", mapping)
        self.assertEqual(len(symbols_seq), 4)
        self.assertEqual([s["letter"] for s in symbols_seq], ["M", "A", "M", "A"])
        self.assertEqual([s["image_path"] for s in symbols_seq], ["kolo.jpg", "trojkat.jpg", "kolo.jpg", "trojkat.jpg"])

    # -------------------------------------------------------------
    # TEST 3: Walidacja brakującego symbolu – zgłoszenie błędu i wskazanie braków
    # -------------------------------------------------------------
    def test_03_validate_mapping_missing_symbols(self):
        required_letters = ["M", "A", "K", "S"]
        partial_mapping = {
            "M": "kolo.jpg",
            "A": "trojkat.jpg"
        }
        is_valid, err_msg, missing = WordTask.validate_mapping(required_letters, partial_mapping)
        self.assertFalse(is_valid)
        self.assertIn("K", missing)
        self.assertIn("S", missing)
        self.assertIn("Brakujące litery", err_msg)

        complete_mapping = {
            "M": "kolo.jpg",
            "A": "trojkat.jpg",
            "K": "kwadrat.jpg",
            "S": "serce.jpg"
        }
        is_valid_c, err_msg_c, missing_c = WordTask.validate_mapping(required_letters, complete_mapping)
        self.assertTrue(is_valid_c)
        self.assertEqual(missing_c, [])

    # -------------------------------------------------------------
    # TEST 4: Zapis projektu do JSON, zamknięcie, ponowne otwarcie
    # -------------------------------------------------------------
    def test_04_save_and_reload_project(self):
        sz = Szablony()
        proj_name = "Test_Word_Task_Reload_04"
        sz.nowy_projekt(proj_name, 1000, 1000)

        task = WordTask(
            words_file=str(self.sample_words_file),
            max_len=6,
            auto_assign_symbols=True
        )
        words = task.load_words()
        letters = task.get_unique_letters(words)
        mapping = task.generate_symbol_mapping(letters)
        task.set_mapping(mapping)

        sz.sloty = task.build_template_slots(width=1000, height=1000, max_word_len=6)
        sz.word_task = task.to_dict()

        sz.zapisz()

        # Otwórz w nowej instancji
        sz2 = Szablony()
        loaded = sz2.otworz_projekt(proj_name)
        self.assertTrue(loaded)
        self.assertIsNotNone(sz2.word_task)
        self.assertEqual(sz2.word_task["max_len"], 6)
        self.assertEqual(len(sz2.sloty), len(sz.sloty))

        # Oczyszczenie pliku testowego
        p_json = PROJEKTY_DIR / f"{proj_name}.json"
        if p_json.exists():
            p_json.unlink()

    # -------------------------------------------------------------
    # TEST 5: Obraz ze stałego folderu data/obrazy_stałe jako symbol
    # -------------------------------------------------------------
    def test_05_obrazy_stale_loading_and_render(self):
        sz = Szablony()
        sz.nowy_projekt("Test_Obrazy_Stale_05", 800, 600)
        
        # Dodaj slot z obrazem ze stałego folderu
        sz.dodaj_slot(
            coords=[50, 50, 200, 200],
            image_path="trojkat.jpg",
            image_source="obrazy_stale",
            symbol="A",
            role="legend_symbol"
        )
        self.assertEqual(sz.sloty[0]["image_source"], "obrazy_stale")
        self.assertEqual(sz.sloty[0]["symbol"], "A")
        
        # Weryfikacja naprawy ścieżki
        resolved = napraw_sciezke("trojkat.jpg", typ="img", source="obrazy_stale")
        self.assertTrue(resolved.exists())
        self.assertEqual(resolved.parent.name, OBRAZY_STALE_DIR.name)

        # Renderowanie
        sz.prepare_render_data(force=True)
        sz.render_all()
        self.assertIsNotNone(sz.img)

    # -------------------------------------------------------------
    # TEST 6: Obraz z folderu data/obrazy jako element zmienny
    # -------------------------------------------------------------
    def test_06_obrazy_variable_loading_and_render(self):
        sz = Szablony()
        sz.nowy_projekt("Test_Obrazy_Zmienne_06", 800, 600)
        
        # Wstawienie obrazka z folderu data/obrazy
        sz.dodaj_slot(
            coords=[50, 50, 200, 200],
            image_path="0.jpg",
            image_source="obrazy"
        )
        resolved = napraw_sciezke("0.jpg", typ="img", source="obrazy")
        self.assertTrue(resolved.exists())
        self.assertEqual(resolved.parent.name, OBRAZY_DIR.name)

        sz.prepare_render_data(force=True)
        sz.render_all()
        self.assertIsNotNone(sz.img)

    # -------------------------------------------------------------
    # TEST 7: Determinizm renderowania (wielokrotne wywołania)
    # -------------------------------------------------------------
    def test_07_rendering_determinism(self):
        sz = Szablony()
        sz.nowy_projekt("Test_Determinism_07", 800, 600)
        task = WordTask(words_file=str(self.sample_words_file), max_len=4, auto_assign_symbols=True)
        sz.sloty = task.build_template_slots(width=800, height=600, max_word_len=4)
        sz.word_task = task.to_dict()

        sz.prepare_render_data(force=True)
        sz.render_all()
        cache_state_1 = json.dumps(sz._computed, sort_keys=True, default=str)

        # Kolejne wywołanie bez force=True nie powinno zmieniać stanu
        sz.prepare_render_data(force=False)
        sz.render_all()
        cache_state_2 = json.dumps(sz._computed, sort_keys=True, default=str)

        self.assertEqual(cache_state_1, cache_state_2)

    # -------------------------------------------------------------
    # TEST 8: Undo / Redo dla operacji zadania słownego i slotów
    # -------------------------------------------------------------
    def test_08_undo_redo_support(self):
        sz = Szablony()
        sz.nowy_projekt("Test_Undo_08", 800, 600)
        self.assertEqual(len(sz.sloty), 0)

        # Dodaj slot 1
        sz.dodaj_slot([10, 10, 100, 100], role="legend_symbol", symbol="M")
        self.assertEqual(len(sz.sloty), 1)

        # Dodaj slot 2
        sz.dodaj_slot([120, 10, 210, 100], role="legend_letter", symbol="M")
        self.assertEqual(len(sz.sloty), 2)

        # Undo
        sz.undo()
        self.assertEqual(len(sz.sloty), 1)

        # Redo
        sz.redo()
        self.assertEqual(len(sz.sloty), 2)

    # -------------------------------------------------------------
    # TEST 9: Dodanie pojedynczego slotu metodą dodaj_slot
    # -------------------------------------------------------------
    def test_09_dodaj_slot_integration(self):
        sz = Szablony()
        sz.nowy_projekt("Test_Dodaj_Slot_09", 1000, 800)

        sz.dodaj_slot(
            coords=[100, 150, 300, 350],
            fill="#ffffff",
            outline="#0078d7",
            outline_width=3,
            image_path="gwiazda.jpg",
            image_source="obrazy_stale",
            symbol="G",
            role="legend_symbol",
            task_index=0
        )

        self.assertEqual(len(sz.sloty), 1)
        slot = sz.sloty[0]
        self.assertEqual(slot["coords"], [100, 150, 300, 350])
        self.assertEqual(slot["outline"], "#0078d7")
        self.assertEqual(slot["symbol"], "G")
        self.assertEqual(slot["role"], "legend_symbol")
        self.assertEqual(slot["image_source"], "obrazy_stale")
        self.assertEqual(slot["task_index"], 0)

        # Render test
        sz.prepare_render_data(force=True)
        sz.render_all()
        self.assertIsNotNone(sz.img)

    # -------------------------------------------------------------
    # TEST 10: Automatyczne przypisanie obrazków z obrazy_stałe BEZ powtórzeń
    # -------------------------------------------------------------
    def test_10_auto_mapping_no_duplicates(self):
        letters = ["M", "A", "K", "S", "O", "T", "B", "R"]
        mapping = WordTask.generate_symbol_mapping(letters)
        self.assertEqual(len(mapping), len(letters))

        assigned_images = [v["image_path"] for v in mapping.values()]
        # Sprawdzamy czy każdy obrazek jest unikalny (brak duplikatów)
        self.assertEqual(len(assigned_images), len(set(assigned_images)))
        
        # Sprawdzamy czy źródło to obrazy_stałe
        for v in mapping.values():
            self.assertEqual(v["image_source"], "obrazy_stale")

    # -------------------------------------------------------------
    # TEST 11: Zgłoszenie błędu gdy unikalnych liter jest więcej niż obrazków
    # -------------------------------------------------------------
    def test_11_insufficient_images_error(self):
        # 16 unikalnych liter (a w folderze obrazy_stałe jest 14)
        too_many_letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P"]
        with self.assertRaises(ValueError) as ctx:
            WordTask.generate_symbol_mapping(too_many_letters, strict=True)
        self.assertIn("za mało obrazków", str(ctx.exception).lower())
        self.assertIn("obrazy_stałe", str(ctx.exception))

    # -------------------------------------------------------------
    # TEST 12: Automatyczna zmiana układu i slotów po modyfikacji pliku TXT
    # -------------------------------------------------------------
    def test_12_dynamic_txt_file_change_rebuilds_slots(self):
        sz = Szablony()
        proj_name = "Test_Dynamic_TXT_Change_12"
        sz.nowy_projekt(proj_name, 800, 1000)

        # 1. Zapisujemy początkowe 2 słowa do pliku TXT
        with open(self.sample_words_file, "w", encoding="utf-8") as f:
            f.write("KOT\nPIES\n")

        WordTask.create_word_task_layout(
            szablony=sz,
            words_file=str(self.sample_words_file),
            mapping=None,
            width=800,
            height=1000
        )
        sz.zapisz()

        # Sprawdzamy początkową liczbę slotów zadania (KOT: 3 + PIES: 4 = 7 symboli i 7 kratek odpowiedzi)
        task_slots = WordTask.get_slots_by_role(sz, WordTask.ROLE_TASK_SYMBOL)
        self.assertEqual(len(task_slots), 7)

        # 2. Użytkownik zamienia słowa w pliku TXT na inne 4 słowa
        with open(self.sample_words_file, "w", encoding="utf-8") as f:
            f.write("DOM\nLAS\nMAK\nKOS\n")

        # 3. Wywołanie prepare_render_data bez ręcznego układania slotów
        sz.prepare_render_data(force=True)
        sz.render_all()

        # Sprawdzamy nową liczbę slotów (DOM: 3 + LAS: 3 + MAK: 3 + KOS: 3 = 12 symboli)
        new_task_slots = WordTask.get_slots_by_role(sz, WordTask.ROLE_TASK_SYMBOL)
        self.assertEqual(len(new_task_slots), 12)
        self.assertIsNotNone(sz.img)

        # Czyszczenie
        p_json = PROJEKTY_DIR / f"{proj_name}.json"
        if p_json.exists():
            p_json.unlink()

    # -------------------------------------------------------------
    # TEST 13: Renderowanie pojedynczego projektu do folderu DO_DRUKU
    # -------------------------------------------------------------
    def test_13_render_to_do_druku(self):
        sz = Szablony()
        proj_name = "Test_Print_Render_13"
        sz.nowy_projekt(proj_name, 800, 1000)

        with open(self.sample_words_file, "w", encoding="utf-8") as f:
            f.write("MAMA\nKASA\nKOT\n")

        WordTask.create_word_task_layout(
            szablony=sz,
            words_file=str(self.sample_words_file),
            mapping=None,
            width=800,
            height=1000
        )
        sz.zapisz()

        # Renderujemy do folderu do_druku
        saved_file = sz.renderuj_pojedynczy_do_druku(proj_name)
        self.assertTrue(Path(saved_file).exists())
        self.assertEqual(Path(saved_file).parent.resolve(), DO_DRUKU_DIR.resolve())

        # Czyszczenie
        p_json = PROJEKTY_DIR / f"{proj_name}.json"
        if p_json.exists():
            p_json.unlink()
        if Path(saved_file).exists():
            Path(saved_file).unlink()

    # -------------------------------------------------------------
    # TEST 14: Zachowanie niestandardowych kolorów i grubości ramek po zmianie TXT
    # -------------------------------------------------------------
    def test_14_custom_slot_styles_preserved_on_txt_change(self):
        sz = Szablony()
        proj_name = "Test_Custom_Styles_14"
        sz.nowy_projekt(proj_name, 800, 1000)

        with open(self.sample_words_file, "w", encoding="utf-8") as f:
            f.write("KOT\n")

        WordTask.create_word_task_layout(
            szablony=sz,
            words_file=str(self.sample_words_file),
            mapping=None,
            width=800,
            height=1000
        )

        # Użytkownik zmienia styl ramki dla symboli zadania i kratek odpowiedzi
        for s in sz.sloty:
            if s.get("role") == WordTask.ROLE_TASK_SYMBOL:
                s["outline"] = "#ff0000"  # czerwona ramka
                s["outline_width"] = 4
            elif s.get("role") == WordTask.ROLE_ANSWER_SLOT:
                s["outline"] = "#0000ff"  # niebieska ramka
                s["outline_width"] = 5
                s["fill"] = "#ffffaa"

        # Zmieniamy słowa w pliku TXT na inne
        with open(self.sample_words_file, "w", encoding="utf-8") as f:
            f.write("DOM\nLAS\n")

        # Przeliczamy dane (wywołuje apply_to_szablony i rebuild)
        sz.prepare_render_data(force=True)
        sz.render_all()

        # Sprawdzamy czy nowe sloty przejęły niestandardowe kolory i grubości ustalone przez użytkownika
        for s in sz.sloty:
            if s.get("role") == WordTask.ROLE_TASK_SYMBOL:
                self.assertEqual(s["outline"], "#ff0000")
                self.assertEqual(s["outline_width"], 4)
            elif s.get("role") == WordTask.ROLE_ANSWER_SLOT:
                self.assertEqual(s["outline"], "#0000ff")
                self.assertEqual(s["outline_width"], 5)
                self.assertEqual(s["fill"], "#ffffaa")

        # Czyszczenie
        p_json = PROJEKTY_DIR / f"{proj_name}.json"
        if p_json.exists():
            p_json.unlink()

    # -------------------------------------------------------------
    # TEST 15: Losowe mieszanie liter (shuffled list) dla legendy zadania
    # -------------------------------------------------------------
    def test_15_shuffled_unique_letters(self):
        words = ["MAMA", "KASA", "MAK", "SAM", "KOT", "REKA", "WODA"]
        deterministic = WordTask.extract_unique_letters(words, shuffle=False)
        self.assertEqual(deterministic, ["M", "A", "K", "S", "O", "T", "R", "E", "W", "D"])

        shuffled = WordTask.extract_unique_letters(words, shuffle=True)
        # Zbiór liter musi być identyczny
        self.assertEqual(set(shuffled), set(deterministic))
        self.assertEqual(len(shuffled), len(deterministic))

        # Przy budowaniu slotów z shuffle_letters=True litery w legendzie są poprawnie umieszczone
        slots = WordTask.build_multi_word_slots(words, shuffle_letters=True)
        legend_let_slots = [s for s in slots if s.get("role") == WordTask.ROLE_LEGEND_LETTER]
        legend_symbols = [s.get("symbol") for s in legend_let_slots if s.get("symbol")]
        self.assertEqual(set(legend_symbols), set(deterministic))

    # -------------------------------------------------------------
    # TEST 16: Zachowanie zwykłych slotów (np. nagłówka) przy zmianie pliku TXT i przebudowie zadania
    # -------------------------------------------------------------
    def test_16_preserve_custom_slots_like_header_on_word_change(self):
        sz = Szablony()
        words_file = TEKSTY_DIR / "test_words_header.txt"
        with open(words_file, "w", encoding="utf-8") as f:
            f.write("KOT\nDOM\n")

        # 1. Tworzymy zadanie słowne
        WordTask.create_word_task_layout(
            szablony=sz,
            words_file=str(words_file),
            mapping={"K": "kolo.jpg", "O": "trojkat.jpg", "T": "kwadrat.jpg", "D": "serce.jpg", "M": "gwiazda.jpg"}
        )

        # 2. Dodajemy niestandardowy slot użytkownika (nagłówek)
        header_slot = {
            "coords": [50, 10, 750, 45],
            "fill": "#eef5ff",
            "outline": "#0055ff",
            "outline_width": 2,
            "tekst": {"typ": "manual", "value": "NAGŁÓWEK: ROZWIĄŻ ZADANIE", "align": "center"},
            "role": "",  # Zwykły slot
            "visible": True
        }
        sz.sloty.append(header_slot)
        sz.prepare_render_data(force=True)

        # 3. Zmieniamy zawartość pliku TXT (wymusza rebuild slotów zadania słownego)
        with open(words_file, "w", encoding="utf-8") as f:
            f.write("MAMA\nKASA\nLATO\n")

        sz.prepare_render_data(force=True)
        sz.render_all()

        # 4. Sprawdzamy czy nagłówek nadal istnieje w slotach i ma swoje właściwości
        headers = [s for s in sz.sloty if isinstance(s.get("tekst"), dict) and "NAGŁÓWEK" in s["tekst"].get("value", "")]
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0]["coords"], [50, 10, 750, 45])
        self.assertEqual(headers[0]["fill"], "#eef5ff")
        self.assertIsNotNone(sz.img)

        # Sprzątanie
        if words_file.exists():
            words_file.unlink()

    # -------------------------------------------------------------
    # TEST 17: Weryfikacja braku obrazków w slotach liter i odpowiedzi
    # -------------------------------------------------------------
    def test_17_letters_and_answers_have_no_images(self):
        sz = Szablony()
        proj_name = "Test_No_Images_Letters_Answers_17"
        sz.nowy_projekt(proj_name, 800, 1000)

        with open(self.sample_words_file, "w", encoding="utf-8") as f:
            f.write("KOT\nDOM\n")

        WordTask.create_word_task_layout(
            szablony=sz,
            words_file=str(self.sample_words_file),
            mapping={"K": "kolo.jpg", "O": "trojkat.jpg", "T": "kwadrat.jpg", "D": "serce.jpg", "M": "gwiazda.jpg"},
            width=800,
            height=1000
        )

        sz.prepare_render_data(force=True)
        sz.render_all()

        legend_sym_slots = [s for s in sz.sloty if s.get("role") == WordTask.ROLE_LEGEND_SYMBOL and s.get("visible", True)]
        legend_let_slots = [s for s in sz.sloty if s.get("role") == WordTask.ROLE_LEGEND_LETTER and s.get("visible", True)]
        task_sym_slots = [s for s in sz.sloty if s.get("role") == WordTask.ROLE_TASK_SYMBOL and s.get("visible", True)]
        answer_slots = [s for s in sz.sloty if s.get("role") == WordTask.ROLE_ANSWER_SLOT and s.get("visible", True)]

        # Sprawdzamy, że symbole w legendzie mają obrazki
        for s in legend_sym_slots:
            self.assertIsNotNone(s.get("image_path"), "Symbol legendy powinien mieć przypisany obrazek!")

        # Sprawdzamy, że litery w legendzie NIE MAJĄ obrazków
        for s in legend_let_slots:
            self.assertIsNone(s.get("image_path"), "Slot litery w legendzie NIE MOŻE mieć obrazka!")

        # Sprawdzamy, że symbole zadań mają obrazki
        for s in task_sym_slots:
            self.assertIsNotNone(s.get("image_path"), "Symbol zadania powinien mieć przypisany obrazek!")

        # Sprawdzamy, że pola na odpowiedź (dla dziecka) NIE MAJĄ obrazków
        for s in answer_slots:
            self.assertIsNone(s.get("image_path"), "Slot odpowiedzi dla ucznia NIE MOŻE mieć obrazka!")

        # Sprzątanie
        p_json = PROJEKTY_DIR / f"{proj_name}.json"
        if p_json.exists():
            p_json.unlink()


if __name__ == "__main__":
    unittest.main()
