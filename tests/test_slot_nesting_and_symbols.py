import unittest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from Szablony_lib import Szablony
from paths import OBRAZY_STALE_DIR


class TestSlotNestingAndSymbols(unittest.TestCase):
    def setUp(self):
        self.sz = Szablony()
        self.sz.nowy_projekt("TestNestingSymbols", 1000, 1000)

    def test_01_generuj_siatke_w_slocie_keep_parent(self):
        # Tworzymy slot rodzica [100, 100, 500, 500] (szer 400, wys 400)
        p_idx = self.sz.dodaj_slot([100, 100, 500, 500])
        self.assertEqual(len(self.sz.sloty), 1)

        # Generujemy siatkę 2x2 wewnątrz slotu z zachowaniem nadrzędnego
        new_indices = self.sz.generuj_siatke_w_slocie(
            indeks_slotu=p_idx,
            kolumny=2,
            wiersze=2,
            margines=(5, 5),
            zachowaj_nadrzedny=True,
            auto_symbole="numbers",
            symbol_prefix="SUB_"
        )
        self.assertEqual(len(new_indices), 4)
        self.assertEqual(len(self.sz.sloty), 5)
        self.assertEqual(self.sz.sloty[0]["coords"], [100, 100, 500, 500])

        # Sprawdzamy współrzędne pierwszego pod-slotu:
        # parent w=400, h=400, kolumny=2 -> k_w=200, k_h=200
        # margines 5% z 200 = 10
        # slot 0: [100+10, 100+10, 100+200-10, 100+200-10] = [110, 110, 290, 290]
        s1 = self.sz.sloty[new_indices[0]]
        self.assertEqual(s1["coords"], [110, 110, 290, 290])
        self.assertEqual(s1["parent_slot"], 0)
        self.assertEqual(s1["symbol"], "SUB_1")

        s4 = self.sz.sloty[new_indices[3]]
        # slot 3: [100+200+10, 100+200+10, 500-10, 500-10] = [310, 310, 490, 490]
        self.assertEqual(s4["coords"], [310, 310, 490, 490])
        self.assertEqual(s4["symbol"], "SUB_4")

    def test_02_generuj_siatke_w_slocie_replace_parent(self):
        p_idx = self.sz.dodaj_slot([0, 0, 400, 400])
        self.assertEqual(len(self.sz.sloty), 1)

        new_indices = self.sz.generuj_siatke_w_slocie(
            indeks_slotu=p_idx,
            kolumny=2,
            wiersze=1,
            margines=(0, 0),
            zachowaj_nadrzedny=False,
            auto_symbole="letters"
        )
        self.assertEqual(len(new_indices), 2)
        self.assertEqual(len(self.sz.sloty), 2)
        self.assertEqual(self.sz.sloty[0]["symbol"], "A")
        self.assertEqual(self.sz.sloty[1]["symbol"], "B")
        self.assertEqual(self.sz.sloty[0]["coords"], [0, 0, 200, 400])
        self.assertEqual(self.sz.sloty[1]["coords"], [200, 0, 400, 400])

    def test_03_symbol_image_synchronization_manual(self):
        # Slot 0 z symbolem A i obrazkiem
        s0 = self.sz.dodaj_slot([0, 0, 100, 100], symbol="A", image_path="kolo.jpg", image_source="obrazy_stale")
        # Slot 1 z symbolem A bez obrazka
        s1 = self.sz.dodaj_slot([100, 0, 200, 100], symbol="A")

        self.assertIsNone(self.sz.sloty[s1].get("image_path"))

        # Synchronizacja
        updated = self.sz.synchronizuj_symbole()
        self.assertEqual(updated, 1)
        self.assertEqual(self.sz.sloty[s1]["image_path"], "kolo.jpg")
        self.assertEqual(self.sz.sloty[s1]["image_source"], "obrazy_stale")

    def test_04_four_random_images_and_four_matching_slots(self):
        """
        Scenariusz użytkownika:
        4 sloty z losowymi obrazkami z 'obrazy stałe' i kolejne 4 sloty,
        w których te same obrazki wyświetlają się automatycznie.
        """
        # Tworzymy 4 sloty źródłowe (np. wiersz 1) z symbolami S1..S4
        source_slots = []
        for i in range(4):
            idx = self.sz.dodaj_slot([i * 150, 0, (i + 1) * 150 - 10, 140], symbol=f"S{i+1}", role="legend_symbol")
            source_slots.append(idx)

        # Tworzymy 4 sloty docelowe (np. wiersz 2) z takimi samymi symbolami S1..S4
        target_slots = []
        for i in range(4):
            idx = self.sz.dodaj_slot([i * 150, 200, (i + 1) * 150 - 10, 340], symbol=f"S{i+1}", role="task_symbol")
            target_slots.append(idx)

        # Losujemy unikalne obrazy ze stałych dla 4 slotów źródłowych
        assigned = self.sz.losuj_obrazy_stale(slots=source_slots, unikalne=True)
        self.assertEqual(len(assigned), 4)

        # Sprawdzamy czy każdy ze slotów docelowych otrzymał identyczny obrazek jak odpowiadający mu slot źródłowy
        for i in range(4):
            src_idx = source_slots[i]
            tgt_idx = target_slots[i]
            self.assertIsNotNone(self.sz.sloty[src_idx]["image_path"])
            self.assertEqual(self.sz.sloty[src_idx]["image_path"], self.sz.sloty[tgt_idx]["image_path"])
            self.assertEqual(self.sz.sloty[src_idx]["image_source"], "obrazy_stale")
            self.assertEqual(self.sz.sloty[tgt_idx]["image_source"], "obrazy_stale")

    def test_05_hit_testing_priority_innermost_slot(self):
        # Slot duży (rodzic): [100, 100, 500, 500] (powierzchnia 160000)
        p_idx = self.sz.dodaj_slot([100, 100, 500, 500])
        # Slot mały (dziecko): [150, 150, 250, 250] (powierzchnia 10000)
        c_idx = self.sz.dodaj_slot([150, 150, 250, 250])

        # Symulacja algorytmu hit-testingu przy kliknięciu w punkt (200, 200)
        x, y = 200, 200
        matching = []
        for i, slot in enumerate(self.sz.sloty):
            c = slot["coords"]
            if c[0] <= x <= c[2] and c[1] <= y <= c[3]:
                area = max(0, c[2] - c[0]) * max(0, c[3] - c[1])
                matching.append((area, i))

        matching.sort(key=lambda it: (it[0], -it[1]))
        clicked_idx = matching[0][1]
        self.assertEqual(clicked_idx, c_idx, "Kliknięcie wewnątrz dziecka powinno wybrać dziecko, a nie rodzica!")

        # Kliknięcie w punkt (400, 400) - wewnątrz rodzica, ale poza dzieckiem
        x2, y2 = 400, 400
        matching2 = []
        for i, slot in enumerate(self.sz.sloty):
            c = slot["coords"]
            if c[0] <= x2 <= c[2] and c[1] <= y2 <= c[3]:
                area = max(0, c[2] - c[0]) * max(0, c[3] - c[1])
                matching2.append((area, i))

        matching2.sort(key=lambda it: (it[0], -it[1]))
        clicked_idx2 = matching2[0][1]
        self.assertEqual(clicked_idx2, p_idx, "Kliknięcie poza dzieckiem powinno wybrać rodzica!")

    def test_06_symbol_sync_does_not_copy_images_to_letters_or_answers(self):
        """
        Weryfikuje, że w zadaniu słowo-symbol oraz przy synchronizacji symboli:
        - Sloty o rolach legend_letter oraz answer_slot NIE otrzymują obrazków
        - Zwykłe pojedyncze sloty oraz task_symbol o tym samym symbolu otrzymują obrazek
        """
        # Slot 0: symbol w legendzie z obrazkiem
        s0 = self.sz.dodaj_slot([0, 0, 100, 100], symbol="A", role="legend_symbol", image_path="kolo.jpg", image_source="obrazy_stale")
        # Slot 1: litera w legendzie z tym samym symbolem "A"
        s1 = self.sz.dodaj_slot([0, 110, 100, 160], symbol="A", role="legend_letter")
        # Slot 2: symbol zadania z symbolem "A"
        s2 = self.sz.dodaj_slot([0, 200, 100, 300], symbol="A", role="task_symbol")
        # Slot 3: pole na odpowiedź z symbolem "A"
        s3 = self.sz.dodaj_slot([0, 310, 100, 400], symbol="A", role="answer_slot")
        # Slot 4: zwykły pojedynczy slot użytkownika z symbolem "A" (bez roli)
        s4 = self.sz.dodaj_slot([0, 410, 100, 500], symbol="A")

        updated = self.sz.synchronizuj_symbole()
        # Zaktualizowane powinny być tylko slot 2 (task_symbol) i slot 4 (zwykły slot)
        self.assertEqual(updated, 2)
        self.assertEqual(self.sz.sloty[s0]["image_path"], "kolo.jpg")
        self.assertIsNone(self.sz.sloty[s1].get("image_path"), "Slot litery w legendzie nie może mieć obrazka!")
        self.assertEqual(self.sz.sloty[s2]["image_path"], "kolo.jpg", "Slot symbolu zadania musi mieć zsynchronizowany obraz!")
        self.assertIsNone(self.sz.sloty[s3].get("image_path"), "Slot odpowiedzi ucznia nie może mieć obrazka!")
        self.assertEqual(self.sz.sloty[s4]["image_path"], "kolo.jpg", "Zwykły slot użytkownika musi mieć zsynchronizowany obraz!")


if __name__ == "__main__":
    unittest.main()
