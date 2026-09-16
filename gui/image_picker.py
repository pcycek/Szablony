import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from paths import OBRAZY_DIR, OBRAZY_STALE_DIR, napraw_sciezke

class ImagePickerDialog(tk.Toplevel):
    """
    Uniwersalny dialog wyboru obrazu z możliwością wskazania folderu:
    - Obrazy zmienne (data/obrazy)
    - Obrazy stałe (data/obrazy_stałe)
    """

    def __init__(self, parent, callback, initial_source="obrazy", initial_file="", title="Wybierz obraz"):
        super().__init__(parent)
        self.callback = callback
        self.title(title)
        self.geometry("600x520")
        self.transient(parent)
        self.grab_set()

        self.source_var = tk.StringVar(value=initial_source if initial_source in ("obrazy_stale", "stale", "obrazy_stałe") else "obrazy")
        self.filter_var = tk.StringVar(value="")
        self.selected_file_var = tk.StringVar(value=initial_file if initial_file else "")
        self.preview_tk = None

        self._build_ui()
        self._refresh_file_list()

        # Wybierz initial_file jeśli podano
        if initial_file:
            self._select_file_in_list(initial_file)

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

    def _build_ui(self):
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        # 1. Wybór źródła (Folderu)
        source_frame = ttk.LabelFrame(container, text="1. Źródło obrazu (Folder)", padding=10)
        source_frame.pack(fill="x", pady=(0, 10))

        r1 = ttk.Radiobutton(
            source_frame,
            text="Obrazy zmienne (data/obrazy)",
            variable=self.source_var,
            value="obrazy",
            command=self._on_source_change
        )
        r1.pack(side="left", padx=(0, 20))

        r2 = ttk.Radiobutton(
            source_frame,
            text="Obrazy stałe (data/obrazy_stałe)",
            variable=self.source_var,
            value="obrazy_stale",
            command=self._on_source_change
        )
        r2.pack(side="left")

        # 2. Główny podział: Lista plików + Podgląd
        main_pane = ttk.PanedWindow(container, orient="horizontal")
        main_pane.pack(fill="both", expand=True, pady=(0, 10))

        # Lewa strona: Lista plików z filtrem
        left_frame = ttk.Frame(main_pane, padding=5)
        main_pane.add(left_frame, weight=3)

        # Filtr
        filter_box = ttk.Frame(left_frame)
        filter_box.pack(fill="x", pady=(0, 5))
        ttk.Label(filter_box, text="Szukaj:").pack(side="left", padx=(0, 5))
        self.entry_filter = ttk.Entry(filter_box, textvariable=self.filter_var)
        self.entry_filter.pack(side="left", fill="x", expand=True)
        self.entry_filter.bind("<KeyRelease>", lambda e: self._refresh_file_list())

        # Listbox ze scrollem
        list_scroll_frame = ttk.Frame(left_frame)
        list_scroll_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_scroll_frame, orient="vertical")
        self.listbox = tk.Listbox(list_scroll_frame, yscrollcommand=scrollbar.set, exportselection=False, font=("Arial", 10))
        scrollbar.config(command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)

        self.listbox.bind("<<ListboxSelect>>", self._on_listbox_select)
        self.listbox.bind("<Double-Button-1>", lambda e: self._on_confirm())

        # Prawa strona: Podgląd obrazu
        right_frame = ttk.LabelFrame(main_pane, text="Podgląd", padding=10)
        main_pane.add(right_frame, weight=2)

        self.lbl_preview = ttk.Label(right_frame, text="Brak podglądu", anchor="center")
        self.lbl_preview.pack(fill="both", expand=True)

        self.lbl_file_info = ttk.Label(right_frame, text="", anchor="center", font=("Arial", 9))
        self.lbl_file_info.pack(fill="x", pady=(5, 0))

        # 3. Dolny pasek wyboru i przycisków
        bottom_frame = ttk.Frame(container)
        bottom_frame.pack(fill="x")

        row_manual = ttk.Frame(bottom_frame)
        row_manual.pack(fill="x", pady=(0, 8))
        ttk.Label(row_manual, text="Wybrany plik:").pack(side="left", padx=(0, 5))
        self.entry_file = ttk.Entry(row_manual, textvariable=self.selected_file_var)
        self.entry_file.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_browse = ttk.Button(row_manual, text="Przeglądaj...", command=self._browse_custom_file)
        btn_browse.pack(side="right")

        row_buttons = ttk.Frame(bottom_frame)
        row_buttons.pack(fill="x")

        btn_cancel = ttk.Button(row_buttons, text="Anuluj", command=self.destroy)
        btn_cancel.pack(side="left", expand=True, fill="x", padx=(0, 5))

        btn_ok = ttk.Button(row_buttons, text="Wybierz obraz", command=self._on_confirm)
        btn_ok.pack(side="left", expand=True, fill="x", padx=(5, 0))

    def _get_current_dir(self):
        source = self.source_var.get()
        if source in ("obrazy_stale", "stale", "obrazy_stałe"):
            return OBRAZY_STALE_DIR
        return OBRAZY_DIR

    def _on_source_change(self):
        self._refresh_file_list()
        self._update_preview()

    def _refresh_file_list(self):
        folder = self._get_current_dir()
        query = self.filter_var.get().strip().lower()

        self.listbox.delete(0, "end")
        self._all_files = []

        if folder.is_dir():
            valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
            try:
                for p in sorted(folder.glob("*.*"), key=lambda x: x.name.lower()):
                    if p.suffix.lower() in valid_exts:
                        self._all_files.append(p.name)
                        if not query or query in p.name.lower():
                            self.listbox.insert("end", p.name)
            except Exception as e:
                print(f"[ImagePicker] Błąd odczytu folderu {folder}: {e}")

    def _select_file_in_list(self, filename):
        fname = Path(filename).name
        for idx, item in enumerate(self.listbox.get(0, "end")):
            if item.lower() == fname.lower() or Path(item).stem.lower() == Path(fname).stem.lower():
                self.listbox.selection_clear(0, "end")
                self.listbox.selection_set(idx)
                self.listbox.see(idx)
                self.selected_file_var.set(item)
                self._update_preview(item)
                break

    def _on_listbox_select(self, event):
        sel = self.listbox.curselection()
        if sel:
            filename = self.listbox.get(sel[0])
            self.selected_file_var.set(filename)
            self._update_preview(filename)

    def _update_preview(self, filename=None):
        if not filename:
            filename = self.selected_file_var.get().strip()

        if not filename:
            self.lbl_preview.config(image="", text="Brak wybranego pliku")
            self.lbl_file_info.config(text="")
            return

        folder = self._get_current_dir()
        path = napraw_sciezke(filename, "img", source=self.source_var.get())

        if not path or not path.is_file():
            self.lbl_preview.config(image="", text=f"Nie znaleziono pliku:\n{filename}")
            self.lbl_file_info.config(text="")
            return

        try:
            img = Image.open(path).convert("RGB")
            orig_w, orig_h = img.size
            # Skalowanie podglądu do max 180x180
            max_size = 180
            scale = min(max_size / max(1, orig_w), max_size / max(1, orig_h))
            pw = max(1, int(orig_w * scale))
            ph = max(1, int(orig_h * scale))
            img_thumb = img.resize((pw, ph), Image.LANCZOS)
            
            self.preview_tk = ImageTk.PhotoImage(img_thumb)
            self.lbl_preview.config(image=self.preview_tk, text="")
            self.lbl_file_info.config(text=f"{orig_w}x{orig_h} px ({path.name})")
        except Exception as e:
            self.lbl_preview.config(image="", text=f"Błąd podglądu:\n{e}")
            self.lbl_file_info.config(text="")

    def _browse_custom_file(self):
        curr_dir = self._get_current_dir()
        filename = filedialog.askopenfilename(
            initialdir=curr_dir,
            title="Wybierz plik graficzny",
            filetypes=[("Obrazy", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Wszystkie pliki", "*.*")]
        )
        if filename:
            p = Path(filename)
            # Jeśli plik znajduje się w jednym z naszych folderów, wykryj odpowiednie źródło
            if str(OBRAZY_STALE_DIR).lower() in str(p.parent).lower():
                self.source_var.set("obrazy_stale")
            elif str(OBRAZY_DIR).lower() in str(p.parent).lower():
                self.source_var.set("obrazy")

            self._refresh_file_list()
            self.selected_file_var.set(p.name)
            self._select_file_in_list(p.name)
            self._update_preview(p.name)

    def _on_confirm(self):
        chosen = self.selected_file_var.get().strip()
        if not chosen:
            messagebox.showwarning("Brak wyboru", "Proszę wybrać lub wpisać nazwę pliku obrazu.")
            return

        source = self.source_var.get()
        self.callback(chosen, source)
        self.destroy()
