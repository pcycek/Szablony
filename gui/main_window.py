import copy
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, simpledialog
from PIL import Image, ImageTk, ImageGrab

def pobierz_obraz_ze_schowka():
    """Zwraca obiekt PIL.Image ze schowka systemowego (zrzut ekranu lub skopiowany plik graficzny) lub None."""
    try:
        data = ImageGrab.grabclipboard()
        if isinstance(data, Image.Image):
            return data.convert("RGB")
        elif isinstance(data, (list, tuple)) and len(data) > 0:
            for item in data:
                p = Path(item)
                if p.exists() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
                    return Image.open(p).convert("RGB")
    except Exception as e:
        print(f"[Schowek] Błąd odczytu: {e}")
    return None

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # 1. Inicjalizacja okna
        self.title("Szablony – GUI")
        self.geometry("1000x800")

        # 2. Bezpieczny import silnika
        from Szablony_lib import Szablony
        self.sz = Szablony()
        self.tk_img = None
        self.aktualny_slot = None
        self.zoom = 1.0

        # System zaznaczania
        self.selected_slots = set()
        self.selected_slots_ordered = []
        self._drag_start = None
        self._drag_start_canvas = None
        self._is_dragging = False

        self._build_ui()
        if self.sz.szerokosc == 0 or self.sz.wysokosc == 0:
            self.sz.nowy_projekt("Nowy", 800, 600)
        self.render()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # --- KONTENER PŁÓTNA Z SUWAKAMI ---
        canvas_container = ttk.Frame(self)
        canvas_container.grid(row=0, column=0, sticky="nsew")
        canvas_container.rowconfigure(0, weight=1)
        canvas_container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_container, bg="#2e2e2e", highlightthickness=0)
        self.v_scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=self.canvas.yview)
        self.h_scrollbar = ttk.Scrollbar(canvas_container, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.canvas.bind("<Button-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.canvas.bind("<Button-2>", self._on_canvas_right_click)

        # Obsługa kółka myszy (Ctrl+kółko = zoom jak w Paint, kółko = pionowy scroll, Shift+kółko = poziomy scroll)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Control-MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)
        self.canvas.bind("<Control-Button-4>", self._on_mouse_wheel)
        self.canvas.bind("<Control-Button-5>", self._on_mouse_wheel)
        self.canvas.bind("<Shift-Button-4>", self._on_mouse_wheel)
        self.canvas.bind("<Shift-Button-5>", self._on_mouse_wheel)
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())

        # --- PANEL BOCZNY ---
        panel = ttk.Frame(self, width=200, padding=10)
        panel.grid(row=0, column=1, sticky="ns")
        panel.pack_propagate(False)

        ttk.Label(panel, text="PROJEKT", font=("Arial", 10, "bold")).pack(pady=5)
        ttk.Button(panel, text="Nowy projekt", command=self.nowy_projekt).pack(fill="x", pady=2)
        ttk.Button(panel, text="Otwórz projekt", command=self.otworz_projekt).pack(fill="x", pady=2)
        ttk.Button(panel, text="📋 Wklej obraz na płótno", command=self.wklej_obraz_na_plotno_click).pack(fill="x", pady=2)
        ttk.Button(panel, text="Generuj siatkę", command=self.generuj_siatke).pack(fill="x", pady=2)
        ttk.Button(panel, text="🔲 Siatka w slocie...", command=self.generuj_siatke_w_slocie_dialog).pack(fill="x", pady=2)
        ttk.Button(panel, text="🎲 Losuj obrazy stałe", command=lambda: self.wstaw_losowe_obrazy_stale()).pack(fill="x", pady=2)
        ttk.Button(panel, text="🔄 Synchronizuj symbole", command=self.synchronizuj_wg_symboli).pack(fill="x", pady=2)
        self.btn_add_slot = ttk.Button(panel, text="➕ Dodaj slot (myszką)", command=self.wlacz_tryb_dodawania_slotu)
        self.btn_add_slot.pack(fill="x", pady=2)
        ttk.Button(panel, text="Zadanie Słowo-Symbol", command=self.konfiguruj_zadanie_slowo).pack(fill="x", pady=2)
        
        ttk.Separator(panel).pack(fill="x", pady=5)
        ttk.Button(panel, text="Przylosuj (Re-roll)", command=self.przelicz_ponownie).pack(fill="x", pady=2)
        ttk.Button(panel, text="Renderuj wszystkie (Batch)", command=self.batch_render).pack(fill="x", pady=2)
        ttk.Button(panel, text="Renderuj do druku (Wybierz)", command=self.renderuj_do_druku_click).pack(fill="x", pady=2)
        ttk.Button(panel, text="📑 Generator / Edytor PDF...", command=self.otworz_edytor_pdf).pack(fill="x", pady=2)
        ttk.Button(panel, text="Otwórz folder...", command=self.otworz_folder_click).pack(fill="x", pady=2)
        ttk.Button(panel, text="Uruchom skrypt", command=self.uruchom_skrypt_click).pack(fill="x", pady=2)
        
        ttk.Separator(panel).pack(fill="x", pady=10)
        
        ttk.Label(panel, text="ŁĄCZENIE (Operatory)", font=("Arial", 10, "bold")).pack(pady=5)
        ttk.Button(panel, text="Dodaj projekt (+)", command=self.polacz_poziomo).pack(fill="x", pady=2)
        ttk.Button(panel, text="Dziel projekt (/)", command=self.polacz_pionowo).pack(fill="x", pady=2)
        
        ttk.Separator(panel).pack(fill='x', pady=10)
        
        ttk.Button(panel, text="undo",
                   command=lambda: (self.sz.undo(), self.render())).pack(fill="x", pady=2)

        ttk.Button(panel, text="redo",
                   command=lambda: (self.sz.redo(), self.render())).pack(fill="x", pady=2)

        # Skróty klawiszowe
        self.bind("<Control-v>", lambda e: self.wklej_ze_schowka_shortcut())
        self.bind("<Control-V>", lambda e: self.wklej_ze_schowka_shortcut())

        # Skróty klawiszowe powiększania
        self.bind("<Control-plus>", lambda e: self.zoom_in())
        self.bind("<Control-equal>", lambda e: self.zoom_in())
        self.bind("<Control-minus>", lambda e: self.zoom_out())
        self.bind("<Control-0>", lambda e: self.zoom_reset())

        # --- DOLNY PANEL ---
        bottom_bar = ttk.Frame(self, padding=(10, 6))
        bottom_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

        ttk.Button(bottom_bar, text="💾 ZAPISZ (JPG+JSON)", command=self._save_project).pack(side="left", padx=5)
        ttk.Button(bottom_bar, text="❌ ZAMKNIJ", command=self.quit).pack(side="left", padx=5)

        # Kontrolki Zoom (jak w MS Paint)
        zoom_frame = ttk.Frame(bottom_bar)
        zoom_frame.pack(side="right", padx=5)

        ttk.Button(zoom_frame, text="➖", width=3, command=self.zoom_out).pack(side="left", padx=1)
        self.lbl_zoom = ttk.Label(zoom_frame, text="🔍 100%", width=8, anchor="center", font=("Arial", 9, "bold"))
        self.lbl_zoom.pack(side="left", padx=2)
        ttk.Button(zoom_frame, text="➕", width=3, command=self.zoom_in).pack(side="left", padx=1)
        ttk.Button(zoom_frame, text="100%", width=5, command=self.zoom_reset).pack(side="left", padx=2)
        ttk.Button(zoom_frame, text="Dopasuj", command=self.zoom_fit).pack(side="left", padx=2)

    # --- NOWE METODY OBSŁUGI SILNIKA ---
    def otworz_projekt(self):
        from gui.project_picker import ProjectPicker

        def open_selected(nazwa):
            if self.sz.otworz_projekt(nazwa):
                self.selected_slots.clear()
                self.selected_slots_ordered.clear()
                self.aktualny_slot = None
                self.render()
            else:
                messagebox.showerror("Błąd", "Nie można otworzyć projektu")

        ProjectPicker(self, open_selected)

    def usun_slot(self):
        if self.aktualny_slot is not None:
            self.sz.usun_slot(self.aktualny_slot)
            self.selected_slots.discard(self.aktualny_slot)
            if self.aktualny_slot in self.selected_slots_ordered:
                self.selected_slots_ordered.remove(self.aktualny_slot)
            self.aktualny_slot = self.selected_slots_ordered[-1] if self.selected_slots_ordered else None
            self.render()

    def polacz_poziomo(self):
        from gui.project_picker import ProjectPicker

        def open_selected(nazwa2):
            from Szablony_lib import Szablony
            drugi = Szablony()
            if drugi.otworz_projekt(nazwa2):
                self.sz.zapisz_undo()
                self.sz = self.sz + drugi
                self.selected_slots.clear()
                self.selected_slots_ordered.clear()
                self.aktualny_slot = None
                self.render()

        ProjectPicker(self, open_selected)

    def polacz_pionowo(self):
        from gui.project_picker import ProjectPicker

        def open_selected(nazwa2):
            from Szablony_lib import Szablony
            drugi = Szablony()
            if drugi.otworz_projekt(nazwa2):
                self.sz.zapisz_undo()
                self.sz = self.sz / drugi
                self.selected_slots.clear()
                self.selected_slots_ordered.clear()
                self.aktualny_slot = None
                self.render()

        ProjectPicker(self, open_selected)

    # --- METODA ZAPISU ---
    def _save_project(self):
        """Wywołuje zapis z silnika Szablony_lib i informuje użytkownika."""
        from tkinter import simpledialog
        
        nowa_nazwa = simpledialog.askstring(
            "Zapisz projekt", 
            "Podaj nazwę projektu:", 
            initialvalue=self.sz.nazwa_projektu
        )
        
        if nowa_nazwa is None:
            return
            
        if nowa_nazwa.strip():
            self.sz.nazwa_projektu = nowa_nazwa.strip()

        try:
            self.sz.zapisz()
            messagebox.showinfo("Sukces", f"Projekt '{self.sz.nazwa_projektu}' został zapisany w folderach projekty i wyniki.")
        except Exception as e:
            messagebox.showerror("Błąd zapisu", f"Wystąpił problem: {e}")

    # --- DIALOGI Z DEKORATORAMI ---
    def nowy_projekt(self):
        from gui.dialogs import with_dialog
        @with_dialog(title="Nowy", fields=[("Nazwa", "str"), ("Szer", "int"), ("Wys", "int")])
        def logic(s, nazwa, w, h):
            s.sz.nowy_projekt(nazwa, w, h)
            s.selected_slots.clear()
            s.selected_slots_ordered.clear()
            s.aktualny_slot = None
            s.render()
        logic(self)

    def konfiguruj_zadanie_slowo(self):
        from gui.word_task_dialog import WordTaskDialog
        def on_applied():
            self.sz.prepare_render_data(force=True)
            self.render()
        WordTaskDialog(self, self.sz, on_applied=on_applied)

    def przelicz_ponownie(self):
        """Wymusza przeliczenie losowych wartości w aktualnym projekcie."""
        self.sz.prepare_render_data(force=True)
        self.render()

    def generuj_siatke(self):
        from gui.dialogs import with_dialog
        
        @with_dialog(title="Siatka", fields=[("Kolumny", "int"), ("Wiersze", "int"), ("Margines (np. 5,5)", "str")])
        def logic(s, k, w, m_str):
            mx, my = 5, 5
            if m_str:
                try:
                    parts = m_str.replace(" ", "").split(",")
                    if len(parts) >= 1:
                        mx = int(parts[0])
                    if len(parts) >= 2:
                        my = int(parts[1])
                    else:
                        my = mx
                except:
                    pass
            
            s.sz.generuj_siatke(k, w, margines=(mx, my))
            s.selected_slots.clear()
            s.selected_slots_ordered.clear()
            s.aktualny_slot = None
            s.render()
        logic(self)

    def generuj_siatke_w_slocie_dialog(self, slot_idx=None):
        """Otwiera dialog generowania podsiatki slotów wewnątrz wybranego slotu."""
        if slot_idx is None:
            slot_idx = self.aktualny_slot
        if slot_idx is None or not (0 <= slot_idx < len(self.sz.sloty)):
            messagebox.showwarning("Brak wyboru", "Zaznacz najpierw slot, wewnątrz którego chcesz utworzyć siatkę.")
            return

        top = tk.Toplevel(self)
        top.title(f"Generuj siatkę w slocie #{slot_idx}")
        top.geometry("400x390")
        top.transient(self)
        top.grab_set()

        container = ttk.Frame(top, padding=15)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text=f"Podział slotu #{slot_idx} na siatkę", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 10))

        # Kolumny i Wiersze
        grid_f = ttk.Frame(container)
        grid_f.pack(fill="x", pady=4)
        ttk.Label(grid_f, text="Kolumny:").grid(row=0, column=0, sticky="w", padx=2, pady=4)
        e_kol = ttk.Spinbox(grid_f, from_=1, to=20, width=6)
        e_kol.set(2)
        e_kol.grid(row=0, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(grid_f, text="Wiersze:").grid(row=0, column=2, sticky="w", padx=(10, 2), pady=4)
        e_wier = ttk.Spinbox(grid_f, from_=1, to=20, width=6)
        e_wier.set(2)
        e_wier.grid(row=0, column=3, sticky="w", padx=4, pady=4)

        # Margines
        ttk.Label(container, text="Margines / odstępy w % (np. 5 lub 5,5):").pack(anchor="w", pady=(6, 2))
        e_marg = ttk.Entry(container)
        e_marg.insert(0, "5, 5")
        e_marg.pack(fill="x", pady=2)

        # Opcje
        var_zachowaj = tk.BooleanVar(value=True)
        ttk.Checkbutton(container, text="Zachowaj slot nadrzędny (jako ramkę/tło)", variable=var_zachowaj).pack(anchor="w", pady=(8, 4))

        # Symbole
        ttk.Label(container, text="Automatyczne symbole:").pack(anchor="w", pady=(6, 2))
        combo_symbole = ttk.Combobox(container, values=["Brak symboli", "Litery (A, B, C...)", "Liczby (1, 2, 3...)"], state="readonly")
        combo_symbole.set("Brak symboli")
        combo_symbole.pack(fill="x", pady=2)

        # Prefiks
        pref_frame = ttk.Frame(container)
        pref_frame.pack(fill="x", pady=4)
        ttk.Label(pref_frame, text="Prefiks symbolu (opcjonalny):").pack(side="left", padx=(0, 5))
        e_prefix = ttk.Entry(pref_frame, width=8)
        e_prefix.pack(side="left")

        def zatwierdz():
            try:
                k = int(e_kol.get())
                w = int(e_wier.get())
                if k < 1 or w < 1:
                    raise ValueError("Wartości muszą być >= 1")
            except Exception:
                messagebox.showerror("Błąd", "Wprowadź poprawne liczby kolumn i wierszy.")
                return

            m_str = e_marg.get().strip()
            mx, my = 5, 5
            if m_str:
                try:
                    parts = m_str.replace(" ", "").split(",")
                    mx = int(parts[0])
                    my = int(parts[1]) if len(parts) > 1 else mx
                except Exception:
                    pass

            sym_choice = combo_symbole.get()
            auto_sym = False
            if "Litery" in sym_choice:
                auto_sym = "letters"
            elif "Liczby" in sym_choice:
                auto_sym = "numbers"

            prefix = e_prefix.get().strip()
            keep_parent = var_zachowaj.get()

            try:
                new_indices = self.sz.generuj_siatke_w_slocie(
                    indeks_slotu=slot_idx,
                    kolumny=k,
                    wiersze=w,
                    margines=(mx, my),
                    zachowaj_nadrzedny=keep_parent,
                    auto_symbole=auto_sym,
                    symbol_prefix=prefix
                )
                self.selected_slots.clear()
                self.selected_slots_ordered.clear()
                for ni in new_indices:
                    self.selected_slots.add(ni)
                    self.selected_slots_ordered.append(ni)
                if new_indices:
                    self.aktualny_slot = new_indices[0]
                self.render()
                top.destroy()
            except Exception as ex:
                messagebox.showerror("Błąd generowania", str(ex))

        footer = ttk.Frame(container)
        footer.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Button(footer, text="Anuluj", command=top.destroy).pack(side="left", expand=True, padx=2)
        ttk.Button(footer, text="Generuj siatkę", command=zatwierdz).pack(side="left", expand=True, padx=2)

    def wstaw_losowe_obrazy_stale(self, slots=None):
        """Wstawia losowe unikalne obrazy ze stałych do wybranych slotów i synchronizuje pasujące symbole."""
        target_slots = list(slots) if slots is not None else list(self.selected_slots_ordered)
        if not target_slots:
            if self.aktualny_slot is not None:
                target_slots = [self.aktualny_slot]
            else:
                messagebox.showwarning("Brak zaznaczenia", "Zaznacz najpierw slot(y), do których chcesz wylosować obrazy.")
                return

        try:
            assigned = self.sz.losuj_obrazy_stale(slots=target_slots, unikalne=True)
            self.render()
            messagebox.showinfo("Wylosowano obrazy", f"Przypisano unikalne obrazy ze stałych do {len(assigned)} slotów.\nPowiązane sloty o tych samych symbolach zostały automatycznie zaktualizowane.")
        except Exception as e:
            messagebox.showerror("Błąd losowania", str(e))

    def synchronizuj_wg_symboli(self):
        """Synchronizuje zawartość obrazkową pomiędzy slotami o pasujących symbolach."""
        updated = self.sz.synchronizuj_symbole()
        self.sz.prepare_render_data(force=True)
        self.render()
        if updated > 0:
            messagebox.showinfo("Synchronizacja", f"Zsynchronizowano obraz w {updated} powiązanych slotach.")
        else:
            messagebox.showinfo("Synchronizacja", "Wszystkie sloty o tych samych symbolach są już zsynchronizowane lub brak powiązań z obrazkami.")

    def batch_render(self):
        answer = messagebox.askyesno("Renderowanie wsadowe", "Czy na pewno chcesz przenderować WSZYSTKIE projekty?\nTo może chwilę potrwać.")
        if not answer:
            return

        self.config(cursor="wait")
        self.update()
        
        skaluj = messagebox.askyesno("Opcja druku", "Czy przeskalować grafiki do druku (300 DPI)?\n\nTAK = powiększenie wymiarów (~4x)\nNIE = oryginalne wymiary ekranowe")
        
        try:
            cnt, err = self.sz.renderuj_wszystkie_projekty(skaluj_300dpi=skaluj)
            messagebox.showinfo("Gotowe", f"Zakończono renderowanie wsadowe.\nPrzetworzono: {cnt}\nBłędy: {err}\n\nPliki zapisano w folderze 'wyniki'.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Wystąpił błąd podczas renderowania: {e}")
        finally:
            self.config(cursor="")

    def renderuj_do_druku_click(self):
        """Obsługa przycisku 'Renderuj do druku'."""
        from gui.project_picker import ProjectPicker

        def do_render(nazwa):
            self.config(cursor="wait")
            self.update()
            try:
                sciezka = self.sz.renderuj_pojedynczy_do_druku(nazwa)
                messagebox.showinfo("Gotowe", f"Zapisano plik do druku:\n{sciezka}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się wygenerować pliku do druku:\n{e}")
            finally:
                self.config(cursor="")

        ProjectPicker(self, do_render)

    def wlacz_tryb_dodawania_slotu(self, parent_constraint=None):
        """Włącza lub wyłącza tryb dodawania nowego slotu myszką na Canvasie (opcjonalnie wewnątrz slotu)."""
        current = getattr(self, "_adding_slot_mode", False)
        if parent_constraint is not None:
            self._adding_slot_mode = True
            self._parent_slot_constraint = parent_constraint
        else:
            self._adding_slot_mode = not current
            self._parent_slot_constraint = None

        if self._adding_slot_mode:
            self.canvas.config(cursor="crosshair")
            if hasattr(self, "btn_add_slot"):
                self.btn_add_slot.config(text="🎯 Kliknij/przeciągnij...")
            if getattr(self, "_parent_slot_constraint", None) is not None:
                pid = self._parent_slot_constraint
                if 0 <= pid < len(self.sz.sloty):
                    p_c = self.sz.sloty[pid]["coords"]
                    zoom = getattr(self, "zoom", 1.0)
                    self.canvas.delete("parent_constraint_rect")
                    self.canvas.create_rectangle(
                        p_c[0] * zoom, p_c[1] * zoom, p_c[2] * zoom, p_c[3] * zoom,
                        outline="#ff9900",
                        width=2,
                        dash=(3, 3),
                        tags="parent_constraint_rect"
                    )
        else:
            self.canvas.config(cursor="")
            self.canvas.delete("parent_constraint_rect")
            self._parent_slot_constraint = None
            if hasattr(self, "btn_add_slot"):
                self.btn_add_slot.config(text="➕ Dodaj slot (myszką)")

    def otworz_folder_click(self):
        """Pokazuje okno z listą folderów do otwarcia."""
        from paths import PROJEKTY_DIR, OBRAZY_DIR, OBRAZY_STALE_DIR, WYNIKI_DIR, TEKSTY_DIR, DO_DRUKU_DIR
        import os
        import subprocess
        import sys
        
        folders = [
            ("Projekty", PROJEKTY_DIR),
            ("Obrazy (Zmienne)", OBRAZY_DIR),
            ("Obrazy Stałe", OBRAZY_STALE_DIR),
            ("Wyniki", WYNIKI_DIR),
            ("Teksty", TEKSTY_DIR),
            ("Do Druku", DO_DRUKU_DIR)
        ]
        
        top = tk.Toplevel(self)
        top.title("Otwórz folder")
        top.geometry("300x320")
        top.transient(self)
        
        ttk.Label(top, text="Wybierz folder do otwarcia:", font=("Arial", 10, "bold")).pack(pady=10)
        
        def open_dir(path):
            try:
                if sys.platform == 'win32':
                    os.startfile(path)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', str(path)])
                else:
                    subprocess.Popen(['xdg-open', str(path)])
                top.destroy()
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się otworzyć folderu:\n{e}")

        for name, path in folders:
            btn = ttk.Button(top, text=name, command=lambda p=path: open_dir(p))
            btn.pack(fill="x", padx=20, pady=4)
            
        ttk.Button(top, text="Anuluj", command=top.destroy).pack(pady=10)

    def uruchom_skrypt_click(self):
        """Uruchamia wybrany skrypt Pythona w nowym procesie."""
        from tkinter import filedialog
        from paths import SKRYPTY_DIR
        import subprocess
        import sys

        filename = filedialog.askopenfilename(
            initialdir=SKRYPTY_DIR,
            title="Wybierz skrypt do uruchomienia",
            filetypes=[("Pliki Python", "*.py"), ("Wszystkie pliki", "*.*")]
        )

        if filename:
            try:
                subprocess.Popen([sys.executable, filename])
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się uruchomić skryptu:\n{e}")

    # --- OBSŁUGA SLOTÓW I ZAZNACZENIA ---

    # --- ZOOM I NAWIGACJA PŁÓTNA ---

    def zoom_in(self):
        self.zoom_by(1.2)

    def zoom_out(self):
        self.zoom_by(1.0 / 1.2)

    def zoom_reset(self):
        self.zoom = 1.0
        self._update_canvas_view()

    def zoom_fit(self):
        vw = self.canvas.winfo_width()
        vh = self.canvas.winfo_height()
        if vw > 20 and vh > 20 and self.sz.szerokosc > 0 and self.sz.wysokosc > 0:
            scale = min((vw - 10) / self.sz.szerokosc, (vh - 10) / self.sz.wysokosc)
            self.zoom = max(0.05, min(10.0, round(scale, 2)))
            self._update_canvas_view()
            self.canvas.xview_moveto(0)
            self.canvas.yview_moveto(0)

    def zoom_by(self, factor, center_viewport=None):
        old_zoom = getattr(self, "zoom", 1.0)
        new_zoom = max(0.05, min(10.0, round(old_zoom * factor, 3)))
        if new_zoom == old_zoom:
            return

        if center_viewport is None:
            vw = self.canvas.winfo_width()
            vh = self.canvas.winfo_height()
            center_viewport = (vw / 2, vh / 2)

        vx, vy = center_viewport
        old_cx = self.canvas.canvasx(vx)
        old_cy = self.canvas.canvasy(vy)

        px = old_cx / old_zoom
        py = old_cy / old_zoom

        self.zoom = new_zoom
        self._update_canvas_view()

        new_cx = px * new_zoom
        new_cy = py * new_zoom

        pw = max(1, self.sz.szerokosc)
        ph = max(1, self.sz.wysokosc)
        dw = max(1, int(round(pw * new_zoom)))
        dh = max(1, int(round(ph * new_zoom)))

        target_left = new_cx - vx
        target_top = new_cy - vy

        frac_x = max(0.0, min(1.0, target_left / dw))
        frac_y = max(0.0, min(1.0, target_top / dh))

        self.canvas.xview_moveto(frac_x)
        self.canvas.yview_moveto(frac_y)

    def _on_mouse_wheel(self, event):
        ctrl = bool(event.state & 0x0004)
        shift = bool(event.state & 0x0001)

        delta = 0
        if hasattr(event, 'delta') and event.delta != 0:
            delta = event.delta
        elif getattr(event, 'num', None) == 4:
            delta = 120
        elif getattr(event, 'num', None) == 5:
            delta = -120

        if delta == 0:
            return "break"

        if ctrl:
            factor = 1.15 if delta > 0 else (1.0 / 1.15)
            self.zoom_by(factor, (event.x, event.y))
        elif shift:
            units = -1 if delta > 0 else 1
            self.canvas.xview_scroll(units, "units")
        else:
            units = -1 if delta > 0 else 1
            self.canvas.yview_scroll(units, "units")
        return "break"

    # --- OBSŁUGA SLOTÓW I ZAZNACZENIA ---

    def _on_canvas_press(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        zoom = getattr(self, "zoom", 1.0)
        self._drag_start = (cx / zoom, cy / zoom)
        self._drag_start_canvas = (cx, cy)
        self._is_dragging = False

    def _on_canvas_drag(self, event):
        if not self._drag_start or not hasattr(self, "_drag_start_canvas") or self._drag_start_canvas is None:
            return
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        x0_vis, y0_vis = self._drag_start_canvas
        x1_vis, y1_vis = cx, cy

        zoom = getattr(self, "zoom", 1.0)
        if getattr(self, "_adding_slot_mode", False) and getattr(self, "_parent_slot_constraint", None) is not None:
            pid = self._parent_slot_constraint
            if 0 <= pid < len(self.sz.sloty):
                pc = self.sz.sloty[pid]["coords"]
                x1_vis = max(pc[0] * zoom, min(pc[2] * zoom, x1_vis))
                y1_vis = max(pc[1] * zoom, min(pc[3] * zoom, y1_vis))

        if abs(x1_vis - x0_vis) > 4 or abs(y1_vis - y0_vis) > 4:
            self._is_dragging = True
            self.canvas.delete("selection_rect")
            self.canvas.create_rectangle(
                x0_vis, y0_vis, x1_vis, y1_vis,
                outline="#00aaff" if not getattr(self, "_adding_slot_mode", False) else "#28a745",
                width=2 if getattr(self, "_adding_slot_mode", False) else 1,
                dash=(4, 4),
                tags="selection_rect"
            )

    def _on_canvas_release(self, event):
        self.canvas.delete("selection_rect")
        self.canvas.delete("parent_constraint_rect")

        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        zoom = getattr(self, "zoom", 1.0)
        px = cx / zoom
        py = cy / zoom

        # Obsługa trybu dodawania slotu myszką
        if getattr(self, "_adding_slot_mode", False):
            if self._drag_start:
                x0, y0 = self._drag_start
                x1, y1 = px, py
                parent_idx = getattr(self, "_parent_slot_constraint", None)
                if parent_idx is not None and not (0 <= parent_idx < len(self.sz.sloty)):
                    parent_idx = None

                if self._is_dragging and (abs(x1 - x0) > 10 or abs(y1 - y0) > 10):
                    rx1, rx2 = min(x0, x1), max(x0, x1)
                    ry1, ry2 = min(y0, y1), max(y0, y1)
                else:
                    # Pojedyncze kliknięcie
                    if parent_idx is not None:
                        pc = self.sz.sloty[parent_idx]["coords"]
                        dw = max(30, int((pc[2] - pc[0]) * 0.5))
                        dh = max(30, int((pc[3] - pc[1]) * 0.5))
                        rx1, ry1 = px, py
                        rx2, ry2 = min(rx1 + dw, pc[2]), min(ry1 + dh, pc[3])
                    else:
                        rx1, ry1 = px, py
                        rx2, ry2 = min(px + 120, self.sz.szerokosc), min(py + 80, self.sz.wysokosc)

                if parent_idx is not None:
                    pc = self.sz.sloty[parent_idx]["coords"]
                    rx1 = max(pc[0], min(pc[2] - 5, rx1))
                    ry1 = max(pc[1], min(pc[3] - 5, ry1))
                    rx2 = min(pc[2], max(pc[0] + 5, rx2))
                    ry2 = min(pc[3], max(pc[1] + 5, ry2))

                coords = [int(round(rx1)), int(round(ry1)), int(round(rx2)), int(round(ry2))]
                self.sz.dodaj_slot(coords, parent_slot=parent_idx)
                new_idx = len(self.sz.sloty) - 1
                self.selected_slots.clear()
                self.selected_slots_ordered.clear()
                self.selected_slots.add(new_idx)
                self.selected_slots_ordered.append(new_idx)
                self.aktualny_slot = new_idx
                self.wlacz_tryb_dodawania_slotu() # Wyłącz tryb dodawania
                self.render()

            self._drag_start = None
            self._drag_start_canvas = None
            self._is_dragging = False
            self._parent_slot_constraint = None
            return

        ctrl_pressed = bool(event.state & 0x0004)

        if self._is_dragging and self._drag_start:
            x0, y0 = self._drag_start
            x1, y1 = px, py
            rx1, rx2 = min(x0, x1), max(x0, x1)
            ry1, ry2 = min(y0, y1), max(y0, y1)

            if not ctrl_pressed:
                self.selected_slots.clear()
                self.selected_slots_ordered.clear()

            for i, slot in enumerate(self.sz.sloty):
                sx1, sy1, sx2, sy2 = slot["coords"]
                # Sprawdzenie przecięcia prostokątów (AABB)
                if not (sx2 < rx1 or sx1 > rx2 or sy2 < ry1 or sy1 > ry2):
                    if i not in self.selected_slots:
                        self.selected_slots.add(i)
                        self.selected_slots_ordered.append(i)

            if self.selected_slots_ordered:
                self.aktualny_slot = self.selected_slots_ordered[-1]
            else:
                self.aktualny_slot = None

        else:
            # Pojedyncze kliknięcie LPM - wybieramy najbardziej wewnętrzny slot (najmniejszy obszar)
            x, y = px, py
            matching = []
            for i, slot in enumerate(self.sz.sloty):
                c = slot["coords"]
                if c[0] <= x <= c[2] and c[1] <= y <= c[3]:
                    area = max(0, c[2] - c[0]) * max(0, c[3] - c[1])
                    matching.append((area, i))

            clicked_idx = None
            if matching:
                matching.sort(key=lambda it: (it[0], -it[1]))
                clicked_idx = matching[0][1]

            if not ctrl_pressed:
                self.selected_slots.clear()
                self.selected_slots_ordered.clear()
                if clicked_idx is not None:
                    self.selected_slots.add(clicked_idx)
                    self.selected_slots_ordered.append(clicked_idx)
                    self.aktualny_slot = clicked_idx
                else:
                    self.aktualny_slot = None
            else:
                if clicked_idx is not None:
                    if clicked_idx in self.selected_slots:
                        self.selected_slots.remove(clicked_idx)
                        self.selected_slots_ordered.remove(clicked_idx)
                        if self.aktualny_slot == clicked_idx:
                            self.aktualny_slot = self.selected_slots_ordered[-1] if self.selected_slots_ordered else None
                    else:
                        self.selected_slots.add(clicked_idx)
                        self.selected_slots_ordered.append(clicked_idx)
                        self.aktualny_slot = clicked_idx

        self._drag_start = None
        self._drag_start_canvas = None
        self._is_dragging = False
        self._update_ui_state()
        self._draw_selection_highlights()

    def _draw_selection_highlights(self):
        self.canvas.delete("selection_outline")
        valid_slots = set(range(len(self.sz.sloty)))
        self.selected_slots = self.selected_slots.intersection(valid_slots)
        self.selected_slots_ordered = [i for i in self.selected_slots_ordered if i in valid_slots]

        zoom = getattr(self, "zoom", 1.0)
        for idx in self.selected_slots:
            c = self.sz.sloty[idx]["coords"]
            self.canvas.create_rectangle(
                c[0] * zoom, c[1] * zoom, c[2] * zoom, c[3] * zoom,
                outline="#0078d7",
                width=max(1, int(3 * min(zoom, 1.5))),
                tags="selection_outline"
            )

    def _update_ui_state(self):
        if hasattr(self, 'btn_edit'):
            if self.aktualny_slot is not None and 0 <= self.aktualny_slot < len(self.sz.sloty):
                self.btn_edit.config(state="normal")
            else:
                self.btn_edit.config(state="disabled")

        if hasattr(self, 'btn_edit_selected'):
            if len(self.selected_slots) >= 1:
                self.btn_edit_selected.config(state="normal")
            else:
                self.btn_edit_selected.config(state="disabled")

        if hasattr(self, 'btn_edit_all'):
            if self.sz.sloty:
                self.btn_edit_all.config(state="normal")
            else:
                self.btn_edit_all.config(state="disabled")

    def otworz_edytor(self):
        if self.aktualny_slot is not None:
            from gui.slot_editor import SlotEditorWindow
            self.sz.zapamietaj_baze_slotu(self.aktualny_slot)
            SlotEditorWindow(self, self.sz, self.aktualny_slot)

    def otworz_edytor_zaznaczonych(self):
        if not self.selected_slots_ordered:
            messagebox.showwarning("Brak zaznaczenia", "Nie zaznaczono żadnych slotów do edycji.")
            return
        from gui.slot_editor import AllSlotsEditorWindow
        AllSlotsEditorWindow(
            self, 
            self.sz, 
            slots=self.selected_slots_ordered, 
            title=f"Edycja zaznaczonych slotów ({len(self.selected_slots_ordered)})"
        )

    def otworz_edytor_wszystkich(self):
        if not self.sz.sloty:
            messagebox.showwarning("Brak slotów", "Projekt nie posiada żadnych slotów do edycji.")
            return
        from gui.slot_editor import AllSlotsEditorWindow
        AllSlotsEditorWindow(
            self, 
            self.sz, 
            slots=list(range(len(self.sz.sloty))), 
            title=f"Edycja wszystkich slotów ({len(self.sz.sloty)})"
        )

    def render(self):
        self._update_ui_state()
        self.sz.render_all()
        self._update_canvas_view()

    def _update_canvas_view(self):
        from PIL import ImageTk, Image
        if not hasattr(self, 'zoom'):
            self.zoom = 1.0

        pw = max(1, self.sz.szerokosc)
        ph = max(1, self.sz.wysokosc)
        dw = max(1, int(round(pw * self.zoom)))
        dh = max(1, int(round(ph * self.zoom)))

        self.canvas.configure(scrollregion=(0, 0, dw, dh))

        if self.sz.img:
            if self.zoom == 1.0 or (self.sz.img.width == dw and self.sz.img.height == dh):
                display_img = self.sz.img
            else:
                display_img = self.sz.img.resize((dw, dh), Image.Resampling.BILINEAR)

            self.tk_img = ImageTk.PhotoImage(display_img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img, tags="bg_image")

        if hasattr(self, 'lbl_zoom'):
            pct = int(round(self.zoom * 100))
            self.lbl_zoom.config(text=f"🔍 {pct}%")

        self._draw_selection_highlights()

        if getattr(self, "_adding_slot_mode", False) and getattr(self, "_parent_slot_constraint", None) is not None:
            pid = self._parent_slot_constraint
            if 0 <= pid < len(self.sz.sloty):
                pc = self.sz.sloty[pid]["coords"]
                zoom = getattr(self, "zoom", 1.0)
                self.canvas.delete("parent_constraint_rect")
                self.canvas.create_rectangle(
                    pc[0] * zoom, pc[1] * zoom, pc[2] * zoom, pc[3] * zoom,
                    outline="#ff9900",
                    width=2,
                    dash=(3, 3),
                    tags="parent_constraint_rect"
                )

    # --- MENU KONTEKSTOWE (PRAWY PRZYCISK MYSZY) ---

    def _on_canvas_right_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        zoom = getattr(self, "zoom", 1.0)
        x = cx / zoom
        y = cy / zoom
        matching = []
        for i, slot in enumerate(self.sz.sloty):
            c = slot["coords"]
            if c[0] <= x <= c[2] and c[1] <= y <= c[3]:
                area = max(0, c[2] - c[0]) * max(0, c[3] - c[1])
                matching.append((area, i))

        clicked_idx = None
        if matching:
            matching.sort(key=lambda it: (it[0], -it[1]))
            clicked_idx = matching[0][1]

        if clicked_idx is not None:
            if clicked_idx not in self.selected_slots:
                self.selected_slots.clear()
                self.selected_slots_ordered.clear()
                self.selected_slots.add(clicked_idx)
                self.selected_slots_ordered.append(clicked_idx)
                self.aktualny_slot = clicked_idx
            else:
                self.aktualny_slot = clicked_idx
            self._update_ui_state()
            self._draw_selection_highlights()
            self._show_slot_context_menu(event, list(self.selected_slots_ordered))
        else:
            self._show_empty_context_menu(event, int(round(x)), int(round(y)))

    def _show_slot_context_menu(self, event, slots):
        if not slots:
            return
        menu = tk.Menu(self, tearoff=0)

        is_multi = len(slots) > 1
        title_text = f"Zaznaczone sloty ({len(slots)})" if is_multi else f"Slot #{slots[0]}"
        menu.add_command(label=f"📌 {title_text}", state="disabled")
        menu.add_separator()

        if is_multi:
            menu.add_command(label="✏️ Edytuj zaznaczone...", command=self.otworz_edytor_zaznaczonych)
        else:
            menu.add_command(label="✏️ Edytuj slot...", command=self.otworz_edytor)

        menu.add_separator()
        if not is_multi:
            menu.add_command(label="🔲 Generuj siatkę w tym slocie...", command=lambda: self.generuj_siatke_w_slocie_dialog(slots[0]))
            menu.add_command(label="🎯 Rysuj slot wewnątrz tego slotu...", command=lambda: self.wlacz_tryb_dodawania_slotu(parent_constraint=slots[0]))
        else:
            menu.add_command(label="🔲 Generuj siatkę w pierwszym zaznaczonym...", command=lambda: self.generuj_siatke_w_slocie_dialog(slots[0]))

        menu.add_separator()
        menu.add_command(label="📋 Wklej obraz ze schowka (do slotu)", command=lambda: self.wklej_obraz_do_slotu_click(slots))
        menu.add_command(label="🖼️ Wstaw obraz...", command=lambda: self._wstaw_obraz_dialog(slots))
        menu.add_command(label="🧩 Stwórz kolaż...", command=lambda: self._wstaw_kolaz_dialog(slots))
        menu.add_command(label="🔤 Zmień tekst...", command=lambda: self._zmien_tekst_dialog(slots))
        menu.add_command(label="🎲 Losuj liczby bez powtórzeń...", command=lambda: self._losuj_liczby_dialog(slots))
        menu.add_command(label="🎲 Wstaw losowe obrazy (z 'obrazy stałe')...", command=lambda: self.wstaw_losowe_obrazy_stale(slots))
        menu.add_command(label="🔄 Synchronizuj zawartość wg symboli", command=self.synchronizuj_wg_symboli)

        menu.add_separator()

        # Eksport do JPG
        if is_multi:
            menu.add_command(label="💾 Zapisz zaznaczone jako JPG (0.jpg, 1.jpg...)...", command=lambda: self.zapisz_sloty_do_jpg_click(slots))
        else:
            menu.add_command(label="💾 Zapisz zawartość slotu jako JPG...", command=lambda: self.zapisz_sloty_do_jpg_click(slots))

        menu.add_separator()

        # Podmenu Wygląd
        appearance_menu = tk.Menu(menu, tearoff=0)
        appearance_menu.add_command(label="🎨 Kolor tła...", command=lambda: self._zmien_tlo_dialog(slots))
        appearance_menu.add_command(label="🔲 Kolor ramki...", command=lambda: self._zmien_ramke_dialog(slots))
        appearance_menu.add_command(label="📏 Grubość ramki...", command=lambda: self._zmien_grubosc_dialog(slots))
        menu.add_cascade(label="🎨 Wygląd (Kolory / Ramka)", menu=appearance_menu)

        # Podmenu Wyczyść
        clear_menu = tk.Menu(menu, tearoff=0)
        clear_menu.add_command(label="🧹 Wyczyść cały slot (Wszystko)", command=lambda: self._wyczysc_sloty_action(slots, "wszystko"))
        clear_menu.add_command(label="🖼️ Wyczyść tylko obraz / kolaż", command=lambda: self._wyczysc_sloty_action(slots, "obraz"))
        clear_menu.add_command(label="🔤 Wyczyść tylko tekst / liczby", command=lambda: self._wyczysc_sloty_action(slots, "tekst"))
        clear_menu.add_command(label="🎨 Wyczyść tło (Przezroczyste)", command=lambda: self._wyczysc_sloty_action(slots, "tlo"))
        clear_menu.add_command(label="🔲 Usuń ramkę", command=lambda: self._wyczysc_sloty_action(slots, "ramka"))
        menu.add_cascade(label="🧹 Wyczyść zawartość...", menu=clear_menu)

        menu.add_separator()
        menu.add_command(label="📋 Duplikuj slot(y)", command=lambda: self.duplikuj_sloty(slots))
        menu.add_command(label="🗑️ Usuń slot(y)", command=lambda: self.usun_zaznaczone_sloty(slots))

        menu.add_separator()
        menu.add_command(label="☑️ Zaznacz wszystkie", command=self.zaznacz_wszystkie_sloty)
        menu.add_command(label="⬜ Odznacz wszystko", command=self.odznacz_wszystkie_sloty)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _show_empty_context_menu(self, event, x, y):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="➕ Dodaj slot tutaj", command=lambda: self._dodaj_slot_w_punkcie(x, y))
        mode_text = "🎯 Anuluj tryb rysowania slotu" if getattr(self, "_adding_slot_mode", False) else "🎯 Rysuj nowy slot myszką (przeciągnij)"
        menu.add_command(label=mode_text, command=self.wlacz_tryb_dodawania_slotu)

        menu.add_separator()
        menu.add_command(label="📋 Wklej obraz ze schowka (na płótno)", command=self.wklej_obraz_na_plotno_click)
        menu.add_command(label="🖼️ Wczytaj obraz na płótno z dysku...", command=self.wczytaj_obraz_na_plotno_click)
        if getattr(self.sz, "obraz_tla", None) is not None:
            menu.add_command(label="🧹 Usuń obraz z płótna (tło)", command=self.wyczysc_obraz_plotna_click)

        menu.add_separator()
        menu.add_command(label="🔲 Generuj siatkę...", command=self.generuj_siatke)
        menu.add_command(label="📝 Zadanie Słowo-Symbol...", command=self.konfiguruj_zadanie_slowo)

        menu.add_separator()
        if self.sz.sloty:
            menu.add_command(label="✏️ Edytuj wszystkie sloty...", command=self.otworz_edytor_wszystkich)
            menu.add_command(label="💾 Zapisz wszystkie sloty jako JPG (0.jpg, 1.jpg...)...", command=lambda: self.zapisz_sloty_do_jpg_click(list(range(len(self.sz.sloty)))))
            menu.add_command(label="☑️ Zaznacz wszystkie sloty", command=self.zaznacz_wszystkie_sloty)
            if self.selected_slots:
                menu.add_command(label="⬜ Odznacz wszystko", command=self.odznacz_wszystkie_sloty)
            menu.add_separator()
            menu.add_command(label="🎲 Przylosuj (Re-roll)", command=self.przelicz_ponownie)

        menu.add_command(label="🖨️ Renderuj do druku...", command=self.renderuj_do_druku_click)
        menu.add_command(label="📑 Generator / Edytor PDF...", command=self.otworz_edytor_pdf)
        menu.add_separator()
        menu.add_command(label="📂 Otwórz projekt...", command=self.otworz_projekt)
        menu.add_command(label="📄 Nowy projekt...", command=self.nowy_projekt)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def otworz_edytor_pdf(self, initial_images=None, initial_pdf=None):
        """Otwiera okno generatora i edytora PDF."""
        try:
            from gui.pdf_editor_dialog import PDFEditorDialog
            PDFEditorDialog(self, initial_pdf=initial_pdf, initial_images=initial_images)
        except ImportError as e:
            messagebox.showerror(
                "Brak biblioteki",
                f"Wymagana biblioteka do obsługi PDF nie została znaleziona:\n{e}\n\n"
                "Uruchom w terminalu:\npip install pymupdf pypdf"
            )

    # --- METODY SCHOWKA I ZAPISU JPG ---

    def wklej_ze_schowka_shortcut(self):
        """Globalna obsługa Ctrl+V: wkleja obraz ze schowka na płótno (lub do slotu jeśli zaznaczono)."""
        if self.selected_slots_ordered and len(self.selected_slots_ordered) == 1:
            # Pytanie czy do slotu czy na płótno, albo wklejenie na płótno
            self.wklej_obraz_na_plotno_click()
        else:
            self.wklej_obraz_na_plotno_click()

    def wklej_obraz_na_plotno_click(self):
        """Wkleja obraz ze schowka na kanwę jako tło w pełnej rozdzielczości."""
        img = pobierz_obraz_ze_schowka()
        if not img:
            messagebox.showinfo(
                "Schowek pusty",
                "W schowku nie znaleziono obrazu ani pliku graficznego.\nSkopiuj grafikę (np. Win+Shift+S lub Ctrl+C) i spróbuj ponownie."
            )
            return

        self.sz.ustaw_obraz_tla(img, dopasuj_rozmiar=True)
        self.zoom = 1.0
        self.render()
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        messagebox.showinfo(
            "Wklejono obraz",
            f"Wklejono obraz na płótno w pełnej rozdzielczości ({img.width}x{img.height} px).\n"
            "Możesz przesuwać płótno suwakami lub zmieniać podgląd za pomocą Ctrl + kółko myszy."
        )

    def wczytaj_obraz_na_plotno_click(self):
        """Wczytuje obraz z dysku jako tło kanwy w pełnej rozdzielczości."""
        from tkinter import filedialog
        from paths import OBRAZY_DIR
        filename = filedialog.askopenfilename(
            initialdir=OBRAZY_DIR,
            title="Wybierz obraz na płótno",
            filetypes=[("Pliki graficzne", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Wszystkie pliki", "*.*")]
        )
        if filename:
            self.sz.ustaw_obraz_tla(filename, dopasuj_rozmiar=True)
            self.zoom = 1.0
            self.render()
            self.canvas.xview_moveto(0)
            self.canvas.yview_moveto(0)

    def wyczysc_obraz_plotna_click(self):
        """Usuwa obraz tła z kanwy."""
        self.sz.wyczysc_obraz_tla()
        self.render()

    def wklej_obraz_do_slotu_click(self, slots):
        """Wkleja obraz ze schowka do wskazanego slotu lub grupy slotów."""
        img = pobierz_obraz_ze_schowka()
        if not img:
            messagebox.showinfo(
                "Schowek pusty",
                "W schowku nie znaleziono obrazu ani pliku graficznego."
            )
            return

        from paths import OBRAZY_DIR
        import time
        target_slots = [i for i in slots if 0 <= i < len(self.sz.sloty)]
        if not target_slots:
            return

        # Zapisujemy obraz do data/obrazy
        ts = int(time.time() * 1000) % 1000000
        if len(target_slots) == 1:
            idx = target_slots[0]
            filename = f"wklejony_slot_{idx}_{ts}.jpg"
        else:
            filename = f"wklejony_{ts}.jpg"

        filepath = OBRAZY_DIR / filename
        img.save(filepath, "JPEG", quality=95)

        self.sz.wstaw_obrazek(slots=target_slots, sciezka=filename, image_source="obrazy")
        self.render()
        messagebox.showinfo(
            "Wklejono",
            f"Wklejono obraz ze schowka do {len(target_slots)} slotu/slotów (zapisano jako {filename})."
        )

    def zapisz_sloty_do_jpg_click(self, slots=None):
        """Otwiera okno eksportu wskazanych slotów do formatu JPG."""
        from gui.dialogs import SaveSlotsDialog
        if slots is None:
            slots = self.selected_slots_ordered if self.selected_slots_ordered else list(range(len(self.sz.sloty)))
        if not slots:
            messagebox.showwarning("Brak slotów", "Brak slotów do zapisania.")
            return
        SaveSlotsDialog(self, self.sz, slots=slots)

    # --- METODY POMOCNICZE MENU KONTEKSTOWEGO ---

    def _wstaw_obraz_dialog(self, slots):
        from gui.image_picker import ImagePickerDialog
        first_idx = slots[0] if slots else 0
        curr_img = (self.sz.sloty[first_idx].get("image_path") or self.sz.sloty[first_idx].get("image")) if (0 <= first_idx < len(self.sz.sloty)) else ""
        curr_src = self.sz.sloty[first_idx].get("image_source", "obrazy") if (0 <= first_idx < len(self.sz.sloty)) else "obrazy"

        def on_picked(filename, source):
            self.sz.wstaw_obrazek(slots=slots, sciezka=filename, image_source=source)
            self.render()

        title = f"Wybierz obraz dla slotu #{slots[0]}" if len(slots) == 1 else f"Wybierz obraz ({len(slots)} slotów)"
        ImagePickerDialog(
            self,
            callback=on_picked,
            initial_source=curr_src,
            initial_file=curr_img if isinstance(curr_img, str) else "",
            title=title
        )

    def _wstaw_kolaz_dialog(self, slots):
        from gui.dialogs import with_dialog
        @with_dialog(
            title="Kolaż",
            fields=[
                ("Plik", "str"),
                ("Ilość (0 = random/slot)", "int", 1),
                ("Min (dla random)", "int", 1),
                ("Max (dla random)", "int", 1),
                ("Slot źródłowy (Index lub -1)", "int", -1)
            ]
        )
        def logic(pw, sciezka, ilosc, min_n, max_n, src_slot):
            if src_slot >= 0:
                self.sz.wklej_jeden_obraz_na_kolaz(
                    sciezka=sciezka,
                    source_slot=src_slot,
                    slots=slots
                )
            elif ilosc == 0:
                if min_n <= 0 or max_n <= 0 or min_n > max_n:
                    messagebox.showerror(
                        "Błąd",
                        "Dla random: min i max muszą być > 0 oraz min ≤ max"
                    )
                    return
                self.sz.wklej_jeden_obraz_na_kolaz(
                    sciezka=sciezka,
                    random_cfg={"min": min_n, "max": max_n},
                    slots=slots
                )
            else:
                self.sz.wklej_jeden_obraz_na_kolaz(
                    sciezka=sciezka,
                    ilosc=ilosc,
                    slots=slots
                )
            self.render()
        logic(self)

    def _zmien_tekst_dialog(self, slots):
        from gui.slot_editor import open_text_config_dialog
        first_idx = slots[0] if slots else 0
        first_txt = self.sz.sloty[first_idx].get("tekst") if (0 <= first_idx < len(self.sz.sloty)) else None

        def save_cb(tekst_cfg):
            if isinstance(tekst_cfg, dict) and tekst_cfg.get("typ") == "file":
                self.sz.wstaw_tekst_z_pliku(
                    plik=tekst_cfg["file"],
                    separator=tekst_cfg["separator"],
                    index=tekst_cfg["index"],
                    align=tekst_cfg["align"],
                    slots=slots
                )
            else:
                self.sz.ustaw_tekst_wszystkim(tekst_cfg, slots=slots)
            self.render()

        open_text_config_dialog(self, first_txt, save_cb)

    def _losuj_liczby_dialog(self, slots):
        from gui.slot_editor import open_random_numbers_dialog
        open_random_numbers_dialog(self, self.sz, slots=slots)

    def _zmien_tlo_dialog(self, slots):
        kolor = colorchooser.askcolor(title="Wybierz kolor tła")[1]
        if kolor:
            self.sz.edytuj_slot(slots=slots, fill=kolor)
            self.render()

    def _zmien_ramke_dialog(self, slots):
        kolor = colorchooser.askcolor(title="Wybierz kolor ramki")[1]
        if kolor:
            self.sz.edytuj_slot(slots=slots, outline=kolor)
            self.render()

    def _zmien_grubosc_dialog(self, slots):
        first_idx = slots[0] if slots else 0
        cur_w = self.sz.sloty[first_idx].get("outline_width", 2) if (0 <= first_idx < len(self.sz.sloty)) else 2
        w = simpledialog.askinteger("Grubość ramki", "Podaj grubość ramki (w px):", initialvalue=cur_w, minvalue=0, maxvalue=50)
        if w is not None:
            self.sz.edytuj_slot(slots=slots, outline_width=w)
            self.render()

    def _wyczysc_sloty_action(self, slots, co="wszystko"):
        self.sz.wyczysc_slot(slots=slots, co=co)
        self.render()

    def usun_zaznaczone_sloty(self, slots=None):
        if slots is None:
            slots = self.selected_slots_ordered
        if not slots:
            return
        self.sz.zapisz_undo()
        for idx in sorted(list(slots), reverse=True):
            if 0 <= idx < len(self.sz.sloty):
                self.sz.usun_slot(idx)
        self.selected_slots.clear()
        self.selected_slots_ordered.clear()
        self.aktualny_slot = None
        self.render()

    def duplikuj_sloty(self, slots=None):
        if slots is None:
            slots = self.selected_slots_ordered
        if not slots:
            return
        self.sz.zapisz_undo()
        new_indices = []
        for idx in sorted(list(slots)):
            if 0 <= idx < len(self.sz.sloty):
                s = copy.deepcopy(self.sz.sloty[idx])
                c = s.get("coords", [0, 0, 100, 100])
                w = c[2] - c[0]
                h = c[3] - c[1]
                offset_x = 20
                offset_y = 20
                nx1 = min(c[0] + offset_x, max(0, self.sz.szerokosc - w))
                ny1 = min(c[1] + offset_y, max(0, self.sz.wysokosc - h))
                s["coords"] = [int(nx1), int(ny1), int(nx1 + w), int(ny1 + h)]
                self.sz.sloty.append(s)
                new_indices.append(len(self.sz.sloty) - 1)
        self.sz.prepare_render_data(force=True)
        self.selected_slots = set(new_indices)
        self.selected_slots_ordered = list(new_indices)
        self.aktualny_slot = new_indices[-1] if new_indices else None
        self.render()

    def zaznacz_wszystkie_sloty(self):
        self.selected_slots = set(range(len(self.sz.sloty)))
        self.selected_slots_ordered = list(range(len(self.sz.sloty)))
        self.aktualny_slot = self.selected_slots_ordered[-1] if self.selected_slots_ordered else None
        self._update_ui_state()
        self._draw_selection_highlights()

    def odznacz_wszystkie_sloty(self):
        self.selected_slots.clear()
        self.selected_slots_ordered.clear()
        self.aktualny_slot = None
        self._update_ui_state()
        self._draw_selection_highlights()

    def _dodaj_slot_w_punkcie(self, x, y):
        w = 120
        h = 80
        x2 = min(x + w, self.sz.szerokosc)
        y2 = min(y + h, self.sz.wysokosc)
        coords = [int(x), int(y), int(x2), int(y2)]
        self.sz.dodaj_slot(coords)
        new_idx = len(self.sz.sloty) - 1
        self.selected_slots.clear()
        self.selected_slots_ordered.clear()
        self.selected_slots.add(new_idx)
        self.selected_slots_ordered.append(new_idx)
        self.aktualny_slot = new_idx
        self.render()
