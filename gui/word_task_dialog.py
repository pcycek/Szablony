import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from paths import TEKSTY_DIR, OBRAZY_DIR, OBRAZY_STALE_DIR, WYNIKI_DIR, napraw_sciezke
from word_task import WordTask
from gui.image_picker import ImagePickerDialog

class WordTaskDialog(tk.Toplevel):
    """
    Dialog konfiguracji i kreatora zadań słowno-obrazkowych:
    OBRAZEK/FIGURA → LITERA → SŁOWO → OBRAZKI DO ODGADNIĘCIA → MIEJSCE NA ODPOWIEDŹ
    """

    def __init__(self, parent, szablony, on_applied=None):
        super().__init__(parent)
        self.parent = parent
        self.sz = szablony
        self.on_applied = on_applied
        self.title("Kreator Zadania Słownego (Figura → Litera → Słowo)")
        self.geometry("750x680")
        self.transient(parent)
        self.grab_set()

        # Inicjalizacja stanu
        self.mapping_data = {}  # { "A": { "image_path": "trojkat.jpg", "image_source": "obrazy_stale" } }
        self.words = []
        self.unique_letters = []

        self._init_data_from_project()
        self._build_ui()
        self._on_txt_source_changed()

        # Wyśrodkowanie okna
        self.update_idletasks()
        self.resizable(True, True)
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"+{x}+{y}")

    def _init_data_from_project(self):
        wt = getattr(self.sz, "word_task", None)
        if wt:
            self.initial_file = wt.get("file", "slowa_demo.txt")
            self.initial_word = wt.get("word", "")
            self.mapping_data = WordTask.normalize_mapping(wt.get("mapping", {}))
        else:
            self.initial_file = "slowa_demo.txt"
            self.initial_word = ""
            self.mapping_data = {}

        # Domyślne mapowanie dla popularnych kształtów jeśli brak
        default_shapes = {
            "A": ("trojkat.jpg", "obrazy_stale"),
            "M": ("kolo.jpg", "obrazy_stale"),
            "K": ("kwadrat.jpg", "obrazy_stale"),
            "S": ("serce.jpg", "obrazy_stale"),
            "O": ("gwiazda.jpg", "obrazy_stale"),
            "T": ("przyklej prostokat.jpg", "obrazy")
        }
        for let, (img, src) in default_shapes.items():
            if let not in self.mapping_data:
                self.mapping_data[let] = {
                    "image_path": img,
                    "image_source": src,
                    "symbol": let
                }

    def _build_ui(self):
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        # 1. Wybór pliku TXT ze słowami
        sec1 = ttk.LabelFrame(container, text="1. Źródło słów (plik TXT)", padding=10)
        sec1.pack(fill="x", pady=(0, 10))

        row1 = ttk.Frame(sec1)
        row1.pack(fill="x")

        ttk.Label(row1, text="Plik TXT:").pack(side="left", padx=(0, 5))
        
        self.cb_file = ttk.Combobox(row1)
        self._populate_txt_files()
        self.cb_file.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.cb_file.bind("<<ComboboxSelected>>", lambda e: self._on_txt_source_changed())
        self.cb_file.bind("<Return>", lambda e: self._on_txt_source_changed())

        btn_browse_txt = ttk.Button(row1, text="Przeglądaj...", command=self._browse_txt)
        btn_browse_txt.pack(side="right")

        self.lbl_words_info = ttk.Label(sec1, text="", font=("Arial", 9))
        self.lbl_words_info.pack(anchor="w", pady=(6, 0))

        # 2. Tabela mapowania (Litera ↔ Obraz)
        sec2 = ttk.LabelFrame(container, text="2. Przypisanie obrazów/figur do liter (Wariant C - ręczny wybór)", padding=10)
        sec2.pack(fill="both", expand=True, pady=(0, 10))

        # Pasek narzędzi mapowania / mieszania liter
        sec2_tools = ttk.Frame(sec2)
        sec2_tools.pack(fill="x", pady=(0, 6))
        btn_shuffle = ttk.Button(sec2_tools, text="🔀 Pomieszaj kolejność liter", command=self._shuffle_letters)
        btn_shuffle.pack(side="left", padx=(0, 8))
        btn_auto_map = ttk.Button(sec2_tools, text="🎲 Losuj / Przypisz figury automatycznie", command=self._auto_assign_shapes)
        btn_auto_map.pack(side="left")

        # Scrollable area for mapping rows
        canvas_frame = ttk.Frame(sec2)
        canvas_frame.pack(fill="both", expand=True)

        self.map_canvas = tk.Canvas(canvas_frame, highlightthickness=0, bg="#fcfcfc")
        map_scroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.map_canvas.yview)
        self.map_scroll_frame = ttk.Frame(self.map_canvas)

        self.map_scroll_frame.bind(
            "<Configure>",
            lambda e: self.map_canvas.configure(scrollregion=self.map_canvas.bbox("all"))
        )
        self.map_canvas_window = self.map_canvas.create_window((0, 0), window=self.map_scroll_frame, anchor="nw")
        self.map_canvas.configure(yscrollcommand=map_scroll.set)

        self.map_canvas.pack(side="left", fill="both", expand=True)
        map_scroll.pack(side="right", fill="y")

        self.map_canvas.bind("<Configure>", self._on_canvas_configure)

        # 3. Układ i konfiguracja zadania dla wszystkich słów
        sec3 = ttk.LabelFrame(container, text="3. Układ arkusza zadania (wszystkie słowa z pliku TXT)", padding=10)
        sec3.pack(fill="x", pady=(0, 10))

        row3_1 = ttk.Frame(sec3)
        row3_1.pack(fill="x", pady=(0, 5))

        ttk.Label(row3_1, text="Słowa na arkuszu:").pack(side="left", padx=(0, 5))
        self.lbl_words_summary = ttk.Label(row3_1, text="", font=("Arial", 9, "bold"), foreground="#2980b9")
        self.lbl_words_summary.pack(side="left", fill="x", expand=True)

        row3_2 = ttk.Frame(sec3)
        row3_2.pack(fill="x")

        ttk.Label(row3_2, text="Układ słów:").pack(side="left", padx=(0, 5))
        self.cb_layout_mode = ttk.Combobox(row3_2, state="readonly", values=[
            "Automatyczny (1-2 słowa w linii z odstępem)",
            "1 słowo w linii",
            "2 słowa w linii"
        ], width=42)
        self.cb_layout_mode.set("Automatyczny (1-2 słowa w linii z odstępem)")
        self.cb_layout_mode.pack(side="left", padx=(0, 15))

        self.lbl_validation = ttk.Label(sec3, text="", foreground="green", font=("Arial", 9))
        self.lbl_validation.pack(anchor="w", pady=(6, 0))

        # 4. Akcje / Przyciski
        btn_box = ttk.Frame(container)
        btn_box.pack(fill="x")

        btn_batch = ttk.Button(btn_box, text="📦 Renderuj do folderu (Batch)", command=self._render_batch)
        btn_batch.pack(side="left", padx=(0, 10))

        btn_apply = ttk.Button(btn_box, text="💾 Zastosuj do projektu", command=self._apply_to_project)
        btn_apply.pack(side="right", padx=(5, 0))

        btn_create_layout = ttk.Button(btn_box, text="🎯 Utwórz układ dla wszystkich słów", command=self._create_new_layout)
        btn_create_layout.pack(side="right", padx=(5, 5))

    def _on_canvas_configure(self, event):
        self.map_canvas.itemconfig(self.map_canvas_window, width=event.width)

    def _populate_txt_files(self):
        txt_files = []
        if TEKSTY_DIR.is_dir():
            for p in sorted(TEKSTY_DIR.glob("*.txt")):
                txt_files.append(p.name)
        self.cb_file["values"] = txt_files
        if self.initial_file in txt_files:
            self.cb_file.set(self.initial_file)
        elif txt_files:
            self.cb_file.set(txt_files[0])
        else:
            self.cb_file.set("slowa_demo.txt")

    def _browse_txt(self):
        filename = filedialog.askopenfilename(
            initialdir=TEKSTY_DIR,
            title="Wybierz plik tekstowy ze słowami",
            filetypes=[("Pliki tekstowe", "*.txt"), ("Wszystkie pliki", "*.*")]
        )
        if filename:
            p = Path(filename)
            self.cb_file.set(p.name if p.parent == TEKSTY_DIR else str(p))
            self._on_txt_source_changed()

    def _shuffle_letters(self):
        import random
        if self.unique_letters:
            random.shuffle(self.unique_letters)
            self._refresh_mapping_ui()
            self._validate_and_update_status()

    def _auto_assign_shapes(self):
        if self.unique_letters:
            self.mapping_data = WordTask.generate_symbol_mapping(self.unique_letters, shuffle_images=True)
            self._refresh_mapping_ui()
            self._validate_and_update_status()

    def _on_txt_source_changed(self):
        source = self.cb_file.get().strip()
        self.words = WordTask.load_words(source)
        self.unique_letters = WordTask.extract_unique_letters(self.words, shuffle=True)

        if self.words:
            self.lbl_words_info.config(
                text=f"Wczytano {len(self.words)} słów: {', '.join(self.words[:8])}{'...' if len(self.words) > 8 else ''} | Unikalne litery ({len(self.unique_letters)}): {' '.join(self.unique_letters)}"
            )
            self.lbl_words_summary.config(
                text=f"{', '.join(self.words)} ({len(self.words)} słów)"
            )
        else:
            self.lbl_words_info.config(text="Brak słów w wybranym pliku TXT.")
            self.lbl_words_summary.config(text="Brak słów")

        self._refresh_mapping_ui()
        self._validate_and_update_status()

    def _refresh_mapping_ui(self):
        for child in self.map_scroll_frame.winfo_children():
            child.destroy()

        if not self.unique_letters:
            ttk.Label(self.map_scroll_frame, text="Wczytaj plik TXT, aby skonfigurować mapowanie liter.").pack(pady=20)
            return

        hdr = ttk.Frame(self.map_scroll_frame, padding=(5, 3))
        hdr.pack(fill="x")
        ttk.Label(hdr, text="Litera", width=8, font=("Arial", 9, "bold")).pack(side="left")
        ttk.Label(hdr, text="Przypisany Obraz / Figura", width=26, font=("Arial", 9, "bold")).pack(side="left", padx=5)
        ttk.Label(hdr, text="Źródło", width=22, font=("Arial", 9, "bold")).pack(side="left", padx=5)
        ttk.Label(hdr, text="Akcja", font=("Arial", 9, "bold")).pack(side="left")

        ttk.Separator(self.map_scroll_frame).pack(fill="x", pady=3)

        for letter in self.unique_letters:
            row = ttk.Frame(self.map_scroll_frame, padding=(5, 4))
            row.pack(fill="x")

            lbl_let = ttk.Label(row, text=f"  {letter}  ", width=6, font=("Arial", 11, "bold"), relief="groove", anchor="center")
            lbl_let.pack(side="left")

            curr = self.mapping_data.get(letter, {})
            curr_img = curr.get("image_path") or ""
            curr_src = curr.get("image_source", "obrazy_stale")

            lbl_img = ttk.Label(row, text=curr_img if curr_img else "(brak - WYMAGANE)", width=26, foreground="black" if curr_img else "red", font=("Arial", 9))
            lbl_img.pack(side="left", padx=5)

            src_desc = "Obrazy stałe (data/obrazy_stałe)" if curr_src in ("obrazy_stale", "stale", "obrazy_stałe") else "Obrazy zmienne (data/obrazy)"
            lbl_src = ttk.Label(row, text=src_desc if curr_img else "-", width=22, font=("Arial", 9))
            lbl_src.pack(side="left", padx=5)

            btn_pick = ttk.Button(row, text="Wybierz obraz...", command=lambda let=letter: self._pick_image_for_letter(let))
            btn_pick.pack(side="left", padx=5)

    def _pick_image_for_letter(self, letter):
        curr = self.mapping_data.get(letter, {})
        curr_img = curr.get("image_path", "")
        curr_src = curr.get("image_source", "obrazy_stale")

        def on_selected(filename, source):
            self.mapping_data[letter] = {
                "image_path": filename,
                "image_source": source,
                "symbol": letter
            }
            self._refresh_mapping_ui()
            self._validate_and_update_status()

        ImagePickerDialog(
            self,
            callback=on_selected,
            initial_source=curr_src,
            initial_file=curr_img,
            title=f"Wybierz obraz dla litery '{letter}'"
        )

    def _validate_and_update_status(self):
        if not self.unique_letters:
            self.lbl_validation.config(text="")
            return

        is_all_valid, err_all, missing_all = WordTask.validate_mapping(self.unique_letters, self.mapping_data)
        if not is_all_valid:
            self.lbl_validation.config(
                text=f"⚠️ {err_all}",
                foreground="red"
            )
        else:
            self.lbl_validation.config(
                text=f"✅ Wszystkie {len(self.unique_letters)} unikalnych liter posiada przypisane symbole. Gotowe!",
                foreground="green"
            )

    def _get_selected_layout_mode(self):
        val = self.cb_layout_mode.get()
        if "1 słowo" in val:
            return "single"
        elif "2 słowa" in val:
            return "double"
        return "auto"

    def _apply_to_project(self):
        if not self.words:
            messagebox.showwarning("Błąd", "Brak słów w wybranym pliku TXT.")
            return

        is_valid, err_msg, missing = WordTask.validate_mapping(self.unique_letters, self.mapping_data)
        if not is_valid:
            if not messagebox.askyesno("Brakujące symbole", f"{err_msg}\n\nCzy mimo to chcesz zastosować konfigurację?"):
                return

        txt_file = self.cb_file.get().strip()

        self.sz.zapisz_undo()
        self.sz.word_task = {
            "active": True,
            "file": txt_file,
            "words": self.words,
            "layout_mode": self._get_selected_layout_mode(),
            "mapping": WordTask.normalize_mapping(self.mapping_data)
        }

        if callable(self.on_applied):
            self.on_applied()
        else:
            self.sz.prepare_render_data(force=True)
            self.parent.render()
        messagebox.showinfo("Sukces", f"Zadanie słowne ({len(self.words)} słów) zostało zastosowane w projekcie.")
        self.destroy()

    def _create_new_layout(self):
        if not self.words:
            messagebox.showwarning("Błąd", "Brak słów do wygenerowania układu.")
            return

        is_valid, err_msg, missing = WordTask.validate_mapping(self.unique_letters, self.mapping_data)
        if not is_valid:
            if not messagebox.askyesno("Brakujące symbole", f"{err_msg}\n\nCzy mimo to chcesz wygenerować układ?"):
                return

        txt_file = self.cb_file.get().strip()
        w = self.sz.szerokosc if self.sz.szerokosc > 0 else 800
        h = self.sz.wysokosc if self.sz.wysokosc > 0 else 1000

        WordTask.create_word_task_layout(
            szablony=self.sz,
            words_file=txt_file,
            mapping=self.mapping_data,
            layout_mode=self._get_selected_layout_mode(),
            width=w,
            height=h
        )

        if callable(self.on_applied):
            self.on_applied()
        else:
            self.parent.render()
        messagebox.showinfo("Sukces", f"Utworzono nowy układ zadania dla wszystkich {len(self.words)} słów.")
        self.destroy()

    def _render_batch(self):
        txt_file = self.cb_file.get().strip()
        if not self.words:
            messagebox.showwarning("Błąd", "Brak słów do renderowania.")
            return

        is_all_valid, err_all, missing_all = WordTask.validate_mapping(self.unique_letters, self.mapping_data)
        if not is_all_valid:
            if not messagebox.askyesno("Ostrzeżenie", f"{err_all}\n\nCzy na pewno chcesz kontynuować?"):
                return

        out_dir = filedialog.askdirectory(
            initialdir=WYNIKI_DIR,
            title="Wybierz folder zapisu wygenerowanych zadań"
        )
        if not out_dir:
            return

        self.sz.word_task = {
            "active": True,
            "file": txt_file,
            "words": self.words,
            "layout_mode": self._get_selected_layout_mode(),
            "mapping": WordTask.normalize_mapping(self.mapping_data)
        }

        self.config(cursor="wait")
        self.update()
        try:
            cnt, files = WordTask.render_all_words_batch(self.sz, output_dir=out_dir)
            messagebox.showinfo("Gotowe", f"Wygenerowano pomyślnie {cnt} grafik w folderze:\n{out_dir}")
        except Exception as e:
            messagebox.showerror("Błąd", f"Wystąpił błąd podczas batch renderowania: {e}")
        finally:
            self.config(cursor="")
