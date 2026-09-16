import os
import copy
import random
from pathlib import Path
from paths import TEKSTY_DIR, OBRAZY_DIR, OBRAZY_STALE_DIR, WYNIKI_DIR, DO_DRUKU_DIR, napraw_sciezke

class WordTask:
    """
    Klasa odpowiedzialna za logikę zadań słowno-obrazkowych typu:
    OBRAZEK/FIGURA → LITERA → SŁOWO → OBRAZKI DO ODGADNIĘCIA → MIEJSCE NA ODPOWIEDŹ
    
    Nie renderuje bezpośrednio Canvas/PIL - przygotowuje dane i stan dla silnika Szablony.
    """

    ROLE_LEGEND_SYMBOL = "legend_symbol"
    ROLE_LEGEND_LETTER = "legend_letter"
    ROLE_TASK_SYMBOL = "task_symbol"
    ROLE_ANSWER_SLOT = "answer_slot"

    # Polskie aliasy stałych ról
    ROLA_SYMBOL_LEGENDY = "legend_symbol"
    ROLA_LITERA_LEGENDY = "legend_letter"
    ROLA_SYMBOL_ZADANIA = "task_symbol"
    ROLA_POLE_ODPOWIEDZI = "answer_slot"

    def __init__(
        self,
        words_file=None,
        words=None,
        max_len=8,
        auto_assign_symbols=False,
        mapping=None,
        word=None,
        word_index=0
    ):
        self.words_file = words_file
        self.words = list(words) if words else []
        self.max_len = max_len
        self.auto_assign_symbols = auto_assign_symbols
        self.mapping = self.normalize_mapping(mapping) if mapping else {}
        self.word = word or ""
        self.word_index = word_index

        if self.words_file and not self.words:
            self.load_words()

        if self.auto_assign_symbols and not self.mapping:
            unique_letters = self.get_unique_letters()
            if unique_letters:
                self.mapping = self.normalize_mapping(self.generate_symbol_mapping(unique_letters))

    @staticmethod
    def _load_words_from_source(source):
        if not source:
            return []

        content = ""
        # Sprawdzamy czy to ścieżka do pliku
        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.is_file():
                # Sprawdzamy w katalogu TEKSTY_DIR
                candidate = napraw_sciezke(str(source), "txt")
                if candidate and candidate.is_file():
                    path = candidate
                elif (TEKSTY_DIR / str(source)).is_file():
                    path = TEKSTY_DIR / str(source)

            if path.is_file():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    print(f"[WordTask] Błąd odczytu pliku {path}: {e}")
                    content = ""
            else:
                content = str(source)
        elif isinstance(source, (list, tuple, set)):
            return [str(w).strip().upper() for w in source if str(w).strip()]
        else:
            content = str(source)

        if not content:
            return []

        # Rozdzielanie po liniach lub przecinkach
        lines = content.replace("\r", "").split("\n")
        words = []
        for line in lines:
            parts = line.split(",") if "," in line else line.split()
            for part in parts:
                cleaned = part.strip().upper()
                if cleaned:
                    words.append(cleaned)
        return words

    def load_words(self, source=None):
        """
        Wczytuje listę słów z pliku TXT lub bezpośredniego stringa.
        Może być wywołana jako metoda instancji (task.load_words())
        lub jako funkcja/metoda klasy (WordTask.load_words(source)).
        """
        if isinstance(self, type):
            # Wywołanie z metody klasy: cls.load_words(source)
            return WordTask._load_words_from_source(source)
        if not isinstance(self, WordTask):
            # Wywołanie statyczne WordTask.load_words(source)
            return WordTask._load_words_from_source(self)

        actual_source = source if source is not None else (self.words_file or self.words)
        words = WordTask._load_words_from_source(actual_source)
        if words:
            self.words = words
            if not self.word and self.words:
                self.word = self.words[0]
        return words

    @staticmethod
    def extract_unique_letters(words, shuffle=False):
        """
        Znajduje wszystkie unikalne litery ze zbioru słów.
        Domyślnie zachowuje deterministyczną kolejność pierwszego wystąpienia.
        Jeśli shuffle=True, zwraca listę z pomieszanymi (shuffled) literami.
        """
        if isinstance(words, str):
            words = WordTask._load_words_from_source(words)

        seen = set()
        unique = []
        for word in words:
            for char in str(word).upper():
                if char.isalpha() and char not in seen:
                    seen.add(char)
                    unique.append(char)
        if shuffle:
            shuffled = list(unique)
            random.shuffle(shuffled)
            return shuffled
        return unique

    def get_unique_letters(self, words=None, shuffle=False):
        """
        Zwraca unikalne litery dla instancji lub przekazanej listy słów.
        """
        if not isinstance(self, WordTask):
            return WordTask.extract_unique_letters(self, shuffle=shuffle)

        target_words = words if words is not None else self.words
        if not target_words and self.words_file:
            target_words = self.load_words()
        return WordTask.extract_unique_letters(target_words, shuffle=shuffle)

    @staticmethod
    def get_available_stale_images():
        """
        Zwraca posortowaną listę nazw plików obrazów z katalogu data/obrazy_stałe.
        """
        available = []
        if OBRAZY_STALE_DIR.is_dir():
            for p in sorted(OBRAZY_STALE_DIR.glob("*.*")):
                if p.suffix.lower() in [".jpg", ".png", ".jpeg"]:
                    available.append(p.name)
        return available

    @classmethod
    def generate_symbol_mapping(cls, letters=None, existing_mapping=None, strict=False, shuffle_images=False):
        """
        Generuje mapowanie unikalnych liter na obrazy ze stałego katalogu (data/obrazy_stałe).
        Gwarantuje brak powtórzeń (każda litera otrzymuje unikalny obrazek).
        Jeśli obrazków w folderze jest za mało, rzuca ValueError (gdy strict) lub zgłasza ostrzeżenie.
        """
        if not isinstance(cls, type):
            # Wywołanie jako metoda instancji
            task_inst = cls
            actual_cls = WordTask
            if letters is not None:
                unique_letters = actual_cls.extract_unique_letters(letters)
            else:
                unique_letters = task_inst.get_unique_letters()
            existing_mapping = existing_mapping or getattr(task_inst, "mapping", {})
        else:
            actual_cls = cls
            unique_letters = actual_cls.extract_unique_letters(letters or [])

        available_images = actual_cls.get_available_stale_images()
        norm_existing = actual_cls.normalize_mapping(existing_mapping) if existing_mapping else {}

        mapping = {}
        used_images = set()

        # 1. Zachowaj istniejące prawidłowe przypisania ze stałych obrazów
        for let in unique_letters:
            if let in norm_existing and norm_existing[let].get("image_path"):
                img = norm_existing[let]["image_path"]
                src = norm_existing[let].get("image_source", "obrazy_stale")
                if img in available_images and img not in used_images:
                    mapping[let] = {
                        "image_path": img,
                        "image_source": src,
                        "symbol": let
                    }
                    used_images.add(img)

        # 2. Dla pozostałych liter przydziel wolne obrazy z obrazy_stałe bez powtórzeń
        unused_images = [img for img in available_images if img not in used_images]
        if shuffle_images:
            random.shuffle(unused_images)
        missing_count = 0

        for let in unique_letters:
            if let not in mapping:
                if unused_images:
                    chosen_img = unused_images.pop(0)
                    mapping[let] = {
                        "image_path": chosen_img,
                        "image_source": "obrazy_stale",
                        "symbol": let
                    }
                    used_images.add(chosen_img)
                else:
                    missing_count += 1

        if missing_count > 0:
            err_msg = (
                f"W folderze 'obrazy_stałe' jest za mało obrazków! "
                f"Potrzeba {len(unique_letters)} unikalnych obrazków dla liter [{', '.join(unique_letters)}], "
                f"a w folderze znajduje się tylko {len(available_images)} ({', '.join(available_images)}). "
                f"Brakuje {missing_count} obrazków. Dodaj więcej plików graficznych do folderu data/obrazy_stałe."
            )
            if strict:
                raise ValueError(err_msg)
            else:
                print(f"[WordTask BŁĄD] {err_msg}")

        return mapping

    def set_mapping(self, mapping):
        """
        Ustawia mapowanie symboli w obiekcie zadania.
        """
        self.mapping = self.normalize_mapping(mapping)

    @staticmethod
    def plan_word_lines(words, mode="auto", max_letters_per_line=12):
        """
        Dzieli listę słów na linie dla układu zadania.
        Zwraca listę list słów: [["MAMA", "KASA"], ["MAK", "SAM"], ["KOT"]]
        """
        clean_words = [str(w).strip().upper() for w in words if str(w).strip()]
        if not clean_words:
            return []

        mode_str = str(mode).lower().strip()
        if mode_str in ("1", "single", "jeden", "1 słowo w wierszu", "1_word"):
            return [[w] for w in clean_words]
        elif mode_str in ("2", "double", "dwa", "2 słowa w wierszu", "2_words"):
            lines = []
            for i in range(0, len(clean_words), 2):
                lines.append(clean_words[i:i+2])
            return lines

        # Auto mode:
        if len(clean_words) <= 3:
            return [[w] for w in clean_words]

        # Jeśli więcej słów, pakujemy po 2 słowa na linię jeśli mieszczą się w max_letters_per_line
        lines = []
        i = 0
        while i < len(clean_words):
            w1 = clean_words[i]
            if i + 1 < len(clean_words):
                w2 = clean_words[i+1]
                if len(w1) + len(w2) <= max_letters_per_line:
                    lines.append([w1, w2])
                    i += 2
                    continue
            lines.append([w1])
            i += 1
        return lines

    @staticmethod
    def extract_slot_styles(sloty):
        """
        Pobiera style zdefiniowane przez użytkownika (outline, outline_width, fill itp.)
        dla każdej roli slotu, aby zachować je przy przebudowie/aktualizacji słów.
        """
        defaults = {
            WordTask.ROLE_LEGEND_SYMBOL: {"fill": "#ffffff", "outline": "black", "outline_width": 2},
            WordTask.ROLE_LEGEND_LETTER: {"fill": "#ffffff", "outline": "black", "outline_width": 2},
            WordTask.ROLE_TASK_SYMBOL: {"fill": "#ffffff", "outline": "black", "outline_width": 2},
            WordTask.ROLE_ANSWER_SLOT: {"fill": "#ffffff", "outline": "black", "outline_width": 2},
        }
        if not sloty:
            return defaults

        for s in sloty:
            role = s.get("role")
            if role in defaults:
                if "fill" in s and s["fill"] is not None:
                    defaults[role]["fill"] = s["fill"]
                if "outline" in s and s["outline"] is not None:
                    defaults[role]["outline"] = s["outline"]
                if "outline_width" in s and s["outline_width"] is not None:
                    defaults[role]["outline_width"] = s["outline_width"]

        return defaults

    @classmethod
    def build_multi_word_slots(
        cls,
        words,
        mapping=None,
        width=800,
        height=1000,
        layout_mode="auto",
        max_letters_per_line=12,
        role_styles=None,
        shuffle_letters=True
    ):
        """
        Generuje listę slotów dla arkusza zadania słownego ze WSZYSTKIMI słowami:
        - Legenda (symbole i litery) dla unikalnych liter ze wszystkich słów na górze (pomieszane losowo)
        - Zadania (symbole i puste kratki odpowiedzi) dla każdego słowa na dole
        Zachowuje niestandardowe kolory i grubości ramek (role_styles) ustawione przez użytkownika.
        """
        clean_words = [str(w).strip().upper() for w in words if str(w).strip()]
        if not clean_words:
            clean_words = ["SŁOWO"]

        unique_letters = cls.extract_unique_letters(clean_words, shuffle=shuffle_letters)
        num_legend = max(len(unique_letters), 4)
        
        # Jeśli nie ma mapowania lub jest niekompletne, generujemy automatycznie bez powtórzeń
        norm_map = cls.generate_symbol_mapping(unique_letters, existing_mapping=mapping)

        # Style ról slotów (domyślnie czarna ramka 2px, zachowuje edycje użytkownika)
        styles = role_styles or cls.extract_slot_styles(None)
        leg_sym_style = styles.get(cls.ROLE_LEGEND_SYMBOL, {"fill": "#ffffff", "outline": "black", "outline_width": 2})
        leg_let_style = styles.get(cls.ROLE_LEGEND_LETTER, {"fill": "#ffffff", "outline": "black", "outline_width": 2})
        task_sym_style = styles.get(cls.ROLE_TASK_SYMBOL, {"fill": "#ffffff", "outline": "black", "outline_width": 2})
        ans_slot_style = styles.get(cls.ROLE_ANSWER_SLOT, {"fill": "#ffffff", "outline": "black", "outline_width": 2})

        margin_x = 35
        margin_y_top = 30
        margin_y_bottom = 30

        # 1. LEGENDA (Rzędy 1 i 2)
        gap_x_legend = 8
        avail_legend_w = width - 2 * margin_x - (num_legend - 1) * gap_x_legend
        legend_slot_w = max(24, min(70, int(avail_legend_w / num_legend)))
        legend_total_w = num_legend * legend_slot_w + (num_legend - 1) * gap_x_legend
        legend_start_x = max(margin_x, int((width - legend_total_w) / 2))

        legend_y_sym = margin_y_top
        legend_sym_h = max(38, min(65, int(height * 0.075)))
        legend_y_let = legend_y_sym + legend_sym_h + 6
        legend_let_h = max(26, min(40, int(height * 0.045)))
        legend_bottom = legend_y_let + legend_let_h

        slots = []

        # Tworzenie slotów legendy
        for i in range(num_legend):
            x1 = legend_start_x + i * (legend_slot_w + gap_x_legend)
            x2 = x1 + legend_slot_w
            let = unique_letters[i] if i < len(unique_letters) else ""
            sym_info = norm_map.get(let, {}) if let else {}

            # Symbol legendy
            slots.append({
                "coords": [int(x1), int(legend_y_sym), int(x2), int(legend_y_sym + legend_sym_h)],
                "fill": leg_sym_style.get("fill", "#ffffff"),
                "outline": leg_sym_style.get("outline", "black"),
                "outline_width": leg_sym_style.get("outline_width", 2),
                "role": cls.ROLE_LEGEND_SYMBOL,
                "task_index": i,
                "symbol": let,
                "image_path": sym_info.get("image_path"),
                "image_source": sym_info.get("image_source", "obrazy_stale"),
                "visible": True if let else False
            })

            # Litera legendy
            slots.append({
                "coords": [int(x1), int(legend_y_let), int(x2), int(legend_y_let + legend_let_h)],
                "fill": leg_let_style.get("fill", "#ffffff"),
                "outline": leg_let_style.get("outline", "black"),
                "outline_width": leg_let_style.get("outline_width", 2),
                "role": cls.ROLE_LEGEND_LETTER,
                "task_index": i,
                "symbol": let,
                "image_path": None,
                "tekst": {"typ": "manual", "value": let, "align": "center"} if let else {"typ": "manual", "value": "", "align": "center"},
                "visible": True if let else False
            })

        # 2. ZADANIA SŁOWNE (Dla wszystkich słów w podziale na wiersze)
        lines = cls.plan_word_lines(clean_words, mode=layout_mode, max_letters_per_line=max_letters_per_line)
        num_lines = max(len(lines), 1)

        y_task_start = legend_bottom + max(20, min(40, int(height * 0.035)))
        avail_task_h = height - y_task_start - margin_y_bottom

        gap_between_lines = max(10, min(30, int(avail_task_h / (num_lines * 5))))
        line_h = (avail_task_h - (num_lines - 1) * gap_between_lines) / num_lines

        sym_h = max(32, min(85, int(line_h * 0.52)))
        ans_h = max(28, min(75, int(line_h * 0.40)))
        gap_sym_ans = max(4, int(line_h - sym_h - ans_h))

        task_running_idx = 0

        # Tworzenie slotów dla każdego wiersza słów
        for line_idx, line_words in enumerate(lines):
            y_sym_top = y_task_start + line_idx * (line_h + gap_between_lines)
            y_sym_bot = y_sym_top + sym_h
            y_ans_top = y_sym_bot + gap_sym_ans
            y_ans_bot = y_ans_top + ans_h

            gap_x_char = 8
            word_gap = max(28, min(65, int(sym_h * 0.7)))  # wyraźny pusty odstęp / separator między słowami w linii

            total_chars = sum(len(w) for w in line_words)
            num_word_gaps = len(line_words) - 1

            avail_w = width - 2 * margin_x - num_word_gaps * word_gap - (total_chars - len(line_words)) * gap_x_char
            slot_w = max(25, min(80, int(avail_w / max(total_chars, 1))))

            line_content_w = total_chars * slot_w + (total_chars - len(line_words)) * gap_x_char + num_word_gaps * word_gap
            cur_x = max(margin_x, int((width - line_content_w) / 2))

            for w_sub_idx, w_text in enumerate(line_words):
                w_global_idx = clean_words.index(w_text) if w_text in clean_words else 0
                if w_sub_idx > 0:
                    cur_x += word_gap

                for c_idx, char in enumerate(w_text):
                    x1 = cur_x
                    x2 = cur_x + slot_w
                    cur_x += slot_w + gap_x_char

                    sym_info = norm_map.get(char, {})

                    # Symbol zadania
                    slots.append({
                        "coords": [int(x1), int(y_sym_top), int(x2), int(y_sym_bot)],
                        "fill": task_sym_style.get("fill", "#ffffff"),
                        "outline": task_sym_style.get("outline", "black"),
                        "outline_width": task_sym_style.get("outline_width", 2),
                        "role": cls.ROLE_TASK_SYMBOL,
                        "word_index": w_global_idx,
                        "char_index": c_idx,
                        "word": w_text,
                        "symbol": char,
                        "task_index": task_running_idx,
                        "image_path": sym_info.get("image_path"),
                        "image_source": sym_info.get("image_source", "obrazy_stale"),
                        "visible": True
                    })

                    # Slot odpowiedzi
                    slots.append({
                        "coords": [int(x1), int(y_ans_top), int(x2), int(y_ans_bot)],
                        "fill": ans_slot_style.get("fill", "#ffffff"),
                        "outline": ans_slot_style.get("outline", "black"),
                        "outline_width": ans_slot_style.get("outline_width", 2),
                        "role": cls.ROLE_ANSWER_SLOT,
                        "word_index": w_global_idx,
                        "char_index": c_idx,
                        "word": w_text,
                        "symbol": char,
                        "task_index": task_running_idx,
                        "image_path": None,
                        "tekst": None,
                        "visible": True
                    })
                    task_running_idx += 1

                cur_x -= gap_x_char

        return slots

    def build_template_slots(self, width=800, height=600, max_word_len=None, layout_mode="auto", shuffle_letters=True):
        """
        Tworzy i zwraca listę slotów dla zadania słownego.
        Jeśli words zawiera wiele słów, tworzy pełny arkusz dla wszystkich słów.
        """
        if self.words and len(self.words) > 1:
            return self.build_multi_word_slots(
                words=self.words,
                mapping=self.mapping,
                width=width,
                height=height,
                layout_mode=layout_mode,
                shuffle_letters=shuffle_letters
            )

        unique_letters = self.get_unique_letters(shuffle=shuffle_letters)
        num_legend = len(unique_letters) if unique_letters else max(len(self.mapping), 4)
        num_task = max_word_len or self.max_len or 8

        margin_x = 40
        gap_x = 15

        # Rząd 1 i 2 (Legenda)
        legend_y_sym = 40
        legend_sym_h = 70
        legend_y_let = legend_y_sym + legend_sym_h + 10
        legend_let_h = 45

        legend_slot_w = (width - 2 * margin_x - (num_legend - 1) * gap_x) // max(num_legend, 1)

        slots = []

        for i in range(num_legend):
            x1 = margin_x + i * (legend_slot_w + gap_x)
            x2 = x1 + legend_slot_w

            # Symbol
            slots.append({
                "coords": [x1, legend_y_sym, x2, legend_y_sym + legend_sym_h],
                "fill": "#ffffff",
                "outline": "black",
                "outline_width": 2,
                "role": self.ROLE_LEGEND_SYMBOL,
                "task_index": i,
                "image_path": None,
                "image_source": "obrazy_stale",
                "visible": True
            })

            # Litera
            slots.append({
                "coords": [x1, legend_y_let, x2, legend_y_let + legend_let_h],
                "fill": "#ffffff",
                "outline": "black",
                "outline_width": 2,
                "role": self.ROLE_LEGEND_LETTER,
                "task_index": i,
                "tekst": {"typ": "manual", "value": "", "align": "center"},
                "visible": True
            })

        # Rząd 3 i 4 (Zadanie + Odpowiedź)
        task_slot_w = (width - 2 * margin_x - (num_task - 1) * gap_x) // max(num_task, 1)
        task_y_sym = 220
        task_sym_h = 100
        task_y_ans = task_y_sym + task_sym_h + 30
        task_ans_h = 90

        for i in range(num_task):
            x1 = margin_x + i * (task_slot_w + gap_x)
            x2 = x1 + task_slot_w

            # Symbol zadania
            slots.append({
                "coords": [x1, task_y_sym, x2, task_y_sym + task_sym_h],
                "fill": "#ffffff",
                "outline": "black",
                "outline_width": 2,
                "role": self.ROLE_TASK_SYMBOL,
                "task_index": i,
                "image_path": None,
                "image_source": "obrazy_stale",
                "visible": True
            })

            # Miejsce na odpowiedź
            slots.append({
                "coords": [x1, task_y_ans, x2, task_y_ans + task_ans_h],
                "fill": "#ffffff",
                "outline": "black",
                "outline_width": 2,
                "role": self.ROLE_ANSWER_SLOT,
                "task_index": i,
                "tekst": None,
                "visible": True
            })

        return slots

    def to_dict(self):
        """
        Zwraca słownik konfiguracyjny zadania słownego do zapisu w projekcie.
        """
        return {
            "active": True,
            "file": str(self.words_file) if self.words_file else "",
            "words": self.words,
            "max_len": self.max_len,
            "mapping": self.normalize_mapping(self.mapping),
            "word": self.word if self.word else (self.words[0] if self.words else ""),
            "word_index": self.word_index
        }

    @staticmethod
    def normalize_mapping(mapping):
        """
        Normalizuje strukturę mapowania do słownika:
        { "A": { "image_path": "trojkat.jpg", "image_source": "obrazy_stale", "symbol": "A" }, ... }
        """
        norm = {}
        if not mapping:
            return norm

        if isinstance(mapping, dict):
            for k, v in mapping.items():
                letter = str(k).strip().upper()
                if isinstance(v, dict):
                    norm[letter] = {
                        "image_path": v.get("image_path") or v.get("image") or v.get("sciezka"),
                        "image_source": v.get("image_source", "obrazy_stale"),
                        "symbol": v.get("symbol", letter)
                    }
                elif isinstance(v, str):
                    norm[letter] = {
                        "image_path": v,
                        "image_source": "obrazy_stale",
                        "symbol": letter
                    }
        elif isinstance(mapping, list):
            for item in mapping:
                if isinstance(item, dict):
                    letter = str(item.get("letter") or item.get("symbol") or "").strip().upper()
                    if letter:
                        norm[letter] = {
                            "image_path": item.get("image_path") or item.get("image") or item.get("sciezka"),
                            "image_source": item.get("image_source", "obrazy_stale"),
                            "symbol": item.get("symbol", letter)
                        }
        return norm

    @classmethod
    def validate_mapping(cls, required_letters, mapping):
        """
        Sprawdza, czy wszystkie wymagane litery mają przypisany obraz/symbol
        oraz czy w folderze obrazy_stałe jest wystarczająca liczba unikalnych obrazów.
        Zwraca: (is_valid: bool, error_message: str, missing_letters: list)
        """
        available_images = cls.get_available_stale_images()
        if len(required_letters) > len(available_images):
            diff = len(required_letters) - len(available_images)
            msg = (
                f"W folderze 'obrazy_stałe' jest za mało obrazków! "
                f"Potrzeba {len(required_letters)} unikalnych obrazków dla liter: [{', '.join(required_letters)}], "
                f"a w folderze znajduje się tylko {len(available_images)} ({', '.join(available_images)}). "
                f"Brakuje {diff} obrazków. Dodaj więcej plików do folderu data/obrazy_stałe."
            )
            return False, msg, required_letters[len(available_images):]

        norm_map = cls.normalize_mapping(mapping)
        missing = []
        mapped_count = 0

        for letter in required_letters:
            letter_up = str(letter).strip().upper()
            if letter_up in norm_map and norm_map[letter_up].get("image_path"):
                mapped_count += 1
            else:
                missing.append(letter_up)

        if missing:
            msg = (
                f"Do utworzenia zadania potrzebne jest {len(required_letters)} różnych symboli, "
                f"ale przypisano tylko {mapped_count}. Brakujące litery: {', '.join(missing)}."
            )
            return False, msg, missing
        return True, "", []

    @staticmethod
    def map_word_to_symbols(word, mapping):
        """
        Zamienia litery słowa na sekwencję symboli/obrazów według mapowania.
        Zwraca listę słowników: [{"letter": "M", "symbol": "M", "image_path": "kolo.jpg", "image_source": "obrazy_stale"}, ...]
        """
        norm_map = WordTask.normalize_mapping(mapping)
        result = []
        word_clean = str(word).strip().upper()

        for char in word_clean:
            if not char.isalpha():
                continue
            item = norm_map.get(char)
            if item and item.get("image_path"):
                result.append({
                    "letter": char,
                    "symbol": item.get("symbol", char),
                    "image_path": item.get("image_path"),
                    "image_source": item.get("image_source", "obrazy_stale")
                })
            else:
                result.append({
                    "letter": char,
                    "symbol": char,
                    "image_path": None,
                    "image_source": "obrazy_stale"
                })
        return result

    @staticmethod
    def get_slots_by_role(szablony, role_name):
        """
        Zwraca indeksy slotów o podanej roli lub grupie.
        """
        indices = []
        role_aliases = {
            WordTask.ROLE_LEGEND_SYMBOL: ["legend_symbol", "mapping_symbol", "legend_symbols", "mapping", "gora_symbol", "symbol_legendy", "Symbol w legendzie (obrazek)"],
            WordTask.ROLE_LEGEND_LETTER: ["legend_letter", "mapping_letter", "legend_letters", "letters", "gora_litera", "litera_legendy", "Litera w legendzie (tekst)"],
            WordTask.ROLE_TASK_SYMBOL: ["task_symbol", "task_symbols", "word_symbol", "task", "zadanie_symbol", "symbol_zadania", "Symbol w zadaniu (zagadka)"],
            WordTask.ROLE_ANSWER_SLOT: ["answer_slot", "answer_slots", "answer", "answers", "odpowiedz", "odpowiedzi", "pole_odpowiedzi", "Pole na odpowiedź (dla ucznia)"]
        }
        allowed = role_aliases.get(role_name, [role_name])

        for idx, s in enumerate(szablony.sloty):
            s_role = s.get("role") or s.get("task_role") or s.get("group")
            if s_role in allowed:
                indices.append(idx)
        return indices

    @classmethod
    def apply_to_szablony(cls, szablony, word=None, word_index=None):
        """
        Aplikuje konfigurację zadania słownego (word_task) do obiektu Szablony.
        Automatycznie wczytuje słowa z pliku TXT, przydziela unikalne obrazy ze stałego folderu
        bez powtórzeń oraz dynamicznie przebudowuje sloty arkusza jeśli słowa w pliku TXT uległy zmianie.
        Zachowuje kolory ramek, wypełnień i grubości ustalone przez użytkownika.
        """
        if not hasattr(szablony, "word_task") or not szablony.word_task:
            return True, ""

        wt_cfg = szablony.word_task
        if not wt_cfg.get("active", True):
            return True, ""

        # 1. Wczytanie słów z pliku TXT
        file_source = wt_cfg.get("file", "")
        if file_source:
            words = cls.load_words(file_source)
        else:
            raw_words = wt_cfg.get("words", [])
            words = [str(w).strip().upper() for w in raw_words if str(w).strip()]

        if not words and wt_cfg.get("word"):
            words = [str(wt_cfg.get("word")).strip().upper()]

        if not words:
            return False, "Brak słów w zadaniu słownym."

        prev_words = wt_cfg.get("words", [])
        words_changed = (prev_words != words)
        wt_cfg["words"] = words

        # 2. Wyznaczenie unikalnych liter i automatyczne przypisanie obrazów z obrazy_stałe bez powtórzeń
        unique_letters = cls.extract_unique_letters(words)
        available_images = cls.get_available_stale_images()

        if len(unique_letters) > len(available_images):
            diff = len(unique_letters) - len(available_images)
            err_msg = (
                f"Za mało obrazków w folderze 'obrazy_stałe'! "
                f"Wymagane {len(unique_letters)} dla liter [{', '.join(unique_letters)}], "
                f"a dostępnych jest tylko {len(available_images)} ({', '.join(available_images)}). "
                f"Dodaj {diff} obrazków do folderu data/obrazy_stałe."
            )
            print(f"[WordTask BŁĄD] {err_msg}")
            if getattr(szablony, "_in_print_render", False):
                raise ValueError(err_msg)

        # Generujemy automatyczne mapowanie bez powtórzeń ze stałego folderu
        norm_map = cls.generate_symbol_mapping(
            letters=unique_letters,
            existing_mapping=wt_cfg.get("mapping", {})
        )
        wt_cfg["mapping"] = norm_map

        # 3. Dynamiczne przebudowanie slotów jeśli słowa w pliku TXT zmieniły się
        task_sym_slots = cls.get_slots_by_role(szablony, cls.ROLE_TASK_SYMBOL)
        has_word_indexing = any("word_index" in szablony.sloty[idx] for idx in task_sym_slots) if task_sym_slots else False
        total_word_chars = sum(len(w) for w in words)

        need_rebuild = (
            words_changed or
            len(szablony.sloty) == 0 or
            len(task_sym_slots) != total_word_chars or
            (not has_word_indexing and len(words) > 1)
        )

        if need_rebuild:
            w = szablony.szerokosc if szablony.szerokosc > 0 else 800
            h = szablony.wysokosc if szablony.wysokosc > 0 else 1000
            existing_styles = cls.extract_slot_styles(szablony.sloty)

            # Zachowujemy niestandardowe sloty użytkownika (np. nagłówki, dodatkowe teksty/obrazy)
            word_task_roles = {
                cls.ROLE_LEGEND_SYMBOL,
                cls.ROLE_LEGEND_LETTER,
                cls.ROLE_TASK_SYMBOL,
                cls.ROLE_ANSWER_SLOT
            }
            custom_slots = [
                copy.deepcopy(s) for s in szablony.sloty
                if (s.get("role") or s.get("task_role") or s.get("group")) not in word_task_roles
            ]

            new_task_slots = cls.build_multi_word_slots(
                words=words,
                mapping=norm_map,
                width=w,
                height=h,
                layout_mode=wt_cfg.get("layout_mode", "auto"),
                role_styles=existing_styles
            )
            szablony.sloty = new_task_slots + custom_slots
            szablony._render_cache = {}
            szablony._computed = {}

        # 4. Wyszukanie slotów wg ról i uaktualnienie ich zawartości (bez nadpisywania styli użytkownika)
        legend_sym_slots = cls.get_slots_by_role(szablony, cls.ROLE_LEGEND_SYMBOL)
        legend_let_slots = cls.get_slots_by_role(szablony, cls.ROLE_LEGEND_LETTER)
        task_sym_slots = cls.get_slots_by_role(szablony, cls.ROLE_TASK_SYMBOL)
        answer_slots = cls.get_slots_by_role(szablony, cls.ROLE_ANSWER_SLOT)

        def sort_key(idx):
            s = szablony.sloty[idx]
            if "task_index" in s:
                return (0, s["task_index"])
            c = s.get("coords", [0, 0, 0, 0])
            return (1, c[1], c[0])

        legend_sym_slots.sort(key=sort_key)
        legend_let_slots.sort(key=sort_key)

        # Używamy kolejności liter z istniejących slotów legendy, aby zachować przemieszaną kolejność
        existing_let_order = [szablony.sloty[idx].get("symbol") for idx in legend_let_slots if szablony.sloty[idx].get("symbol")]
        if set(existing_let_order) == set(unique_letters) and len(existing_let_order) == len(unique_letters):
            active_legend_letters = existing_let_order
        else:
            active_legend_letters = unique_letters

        # Ustawienie legendy
        for i, let in enumerate(active_legend_letters):
            sym_info = norm_map.get(let, {})
            if i < len(legend_sym_slots):
                s_idx = legend_sym_slots[i]
                slot = szablony.sloty[s_idx]
                slot["visible"] = True
                slot["symbol"] = let
                if sym_info.get("image_path"):
                    slot["image_path"] = sym_info["image_path"]
                    slot["image_source"] = sym_info.get("image_source", "obrazy_stale")
                    if s_idx not in szablony._computed:
                        szablony._computed[s_idx] = {}
                    szablony._computed[s_idx]["image_path"] = sym_info["image_path"]
                    szablony._computed[s_idx]["image_source"] = sym_info.get("image_source", "obrazy_stale")
                if s_idx in szablony._render_cache:
                    del szablony._render_cache[s_idx]

            if i < len(legend_let_slots):
                l_idx = legend_let_slots[i]
                slot = szablony.sloty[l_idx]
                slot["visible"] = True
                slot["symbol"] = let
                slot["tekst"] = {"typ": "manual", "value": let, "align": "center"}
                slot["image_path"] = None
                slot.pop("image_source", None)
                if l_idx not in szablony._computed:
                    szablony._computed[l_idx] = {}
                szablony._computed[l_idx]["text"] = let
                szablony._computed[l_idx].pop("image_path", None)
                szablony._computed[l_idx].pop("image_source", None)
                if l_idx in szablony._render_cache:
                    del szablony._render_cache[l_idx]

        for i in range(len(unique_letters), len(legend_sym_slots)):
            szablony.sloty[legend_sym_slots[i]]["visible"] = False
        for i in range(len(unique_letters), len(legend_let_slots)):
            szablony.sloty[legend_let_slots[i]]["visible"] = False

        # Ustawienie symboli zadania i odpowiedzi
        for s_idx in task_sym_slots:
            slot = szablony.sloty[s_idx]
            w_idx = slot.get("word_index", 0)
            c_idx = slot.get("char_index", 0)
            if 0 <= w_idx < len(words) and 0 <= c_idx < len(words[w_idx]):
                let = words[w_idx][c_idx]
                sym_info = norm_map.get(let, {})
                slot["visible"] = True
                slot["symbol"] = let
                slot["word"] = words[w_idx]
                if sym_info.get("image_path"):
                    slot["image_path"] = sym_info["image_path"]
                    slot["image_source"] = sym_info.get("image_source", "obrazy_stale")
                    if s_idx not in szablony._computed:
                        szablony._computed[s_idx] = {}
                    szablony._computed[s_idx]["image_path"] = sym_info["image_path"]
                    szablony._computed[s_idx]["image_source"] = sym_info.get("image_source", "obrazy_stale")
                if s_idx in szablony._render_cache:
                    del szablony._render_cache[s_idx]
            else:
                slot["visible"] = False

        for a_idx in answer_slots:
            slot = szablony.sloty[a_idx]
            w_idx = slot.get("word_index", 0)
            c_idx = slot.get("char_index", 0)
            if 0 <= w_idx < len(words) and 0 <= c_idx < len(words[w_idx]):
                slot["visible"] = True
                slot["symbol"] = words[w_idx][c_idx]
                slot["word"] = words[w_idx]
                slot["image_path"] = None
                slot.pop("image_source", None)
                if not slot.get("outline"):
                    slot["outline"] = "black"
                if not slot.get("outline_width"):
                    slot["outline_width"] = 2
                if a_idx in szablony._computed:
                    szablony._computed[a_idx].pop("text", None)
                    szablony._computed[a_idx].pop("image_path", None)
                    szablony._computed[a_idx].pop("image_source", None)
                if a_idx in szablony._render_cache:
                    del szablony._render_cache[a_idx]
            else:
                slot["visible"] = False

        return True, ""

    @classmethod
    def create_word_task_layout(
        cls,
        szablony,
        words_file,
        mapping,
        active_word=None,
        layout_mode="auto",
        max_letters=8,
        width=None,
        height=None
    ):
        """
        Tworzy kompletny układ szablonu zadania słownego dla wszystkich słów z pliku TXT:
        - Legenda na górze (Symbole i litery dla wszystkich unikalnych liter)
        - Zadania dla każdego słowa (Symbole i puste kratki odpowiedzi)
        """
        w = width if width and width > 0 else (szablony.szerokosc if szablony.szerokosc > 0 else 800)
        h = height if height and height > 0 else (szablony.wysokosc if szablony.wysokosc > 0 else 1000)

        existing_styles = cls.extract_slot_styles(szablony.sloty) if szablony.sloty else None

        szablony.zapisz_undo()
        szablony.szerokosc = w
        szablony.wysokosc = h
        szablony._render_cache = {}
        szablony._computed = {}

        # Wczytanie słów
        words = cls.load_words(words_file)
        if not words and active_word:
            words = [active_word]

        # Zachowujemy niestandardowe sloty użytkownika (np. nagłówki)
        word_task_roles = {
            cls.ROLE_LEGEND_SYMBOL,
            cls.ROLE_LEGEND_LETTER,
            cls.ROLE_TASK_SYMBOL,
            cls.ROLE_ANSWER_SLOT
        }
        custom_slots = [
            copy.deepcopy(s) for s in szablony.sloty
            if (s.get("role") or s.get("task_role") or s.get("group")) not in word_task_roles
        ] if szablony.sloty else []

        new_task_slots = cls.build_multi_word_slots(
            words=words,
            mapping=mapping,
            width=w,
            height=h,
            layout_mode=layout_mode,
            role_styles=existing_styles
        )
        szablony.sloty = new_task_slots + custom_slots

        # Konfiguracja zadania słownego
        szablony.word_task = {
            "active": True,
            "file": str(words_file),
            "words": words,
            "layout_mode": layout_mode,
            "word": active_word if active_word else (words[0] if words else ""),
            "word_index": 0,
            "mapping": cls.normalize_mapping(mapping)
        }

        # Aplikacja i przygotowanie do renderu
        szablony.prepare_render_data(force=True)
        szablony.render_all()
        return True

    @classmethod
    def render_all_words_batch(cls, szablony, output_dir=None, scale=1.0):
        """
        Renderuje osobne grafiki dla każdego słowa z pliku TXT zadania słownego.
        Zwraca (liczba_sukcesow, lista_plikow).
        """
        if not hasattr(szablony, "word_task") or not szablony.word_task:
            return 0, []

        wt = szablony.word_task
        words = cls.load_words(wt.get("file", ""))
        if not words:
            return 0, []

        out_dir = Path(output_dir) if output_dir else WYNIKI_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []
        base_name = szablony.nazwa_projektu

        for idx, w in enumerate(words):
            wt["word_index"] = idx
            wt["word"] = w
            szablony.prepare_render_data(force=True)
            szablony.render_all(skala=scale)
            if szablony.img:
                out_path = out_dir / f"{base_name}_{idx+1}_{w}.jpg"
                szablony.img.convert("RGB").save(out_path, "JPEG", quality=95)
                saved_files.append(str(out_path))

        return len(saved_files), saved_files
