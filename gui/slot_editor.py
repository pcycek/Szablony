import tkinter as tk
from tkinter import ttk
from tkinter import colorchooser

ROLE_OPTIONS = [
    ("", "Brak / Zwykły slot"),
    ("legend_symbol", "Symbol w legendzie (obrazek)"),
    ("legend_letter", "Litera w legendzie (tekst)"),
    ("task_symbol", "Symbol w zadaniu (zagadka)"),
    ("answer_slot", "Pole na odpowiedź (dla ucznia)")
]
ROLE_VAL_TO_LABEL = {val: label for val, label in ROLE_OPTIONS}
ROLE_LABEL_TO_VAL = {label: val for val, label in ROLE_OPTIONS}
ROLE_LABEL_TO_VAL.update({
    "legend_symbol": "legend_symbol",
    "legend_letter": "legend_letter",
    "task_symbol": "task_symbol",
    "answer_slot": "answer_slot",
    "symbol_legendy": "legend_symbol",
    "litera_legendy": "legend_letter",
    "symbol_zadania": "task_symbol",
    "pole_odpowiedzi": "answer_slot",
    "odpowiedz": "answer_slot"
})

class SlotEditorWindow(tk.Toplevel):
    def __init__(self, parent, szablony, indeks_slotu):
        super().__init__(parent)
        self.parent = parent
        self.sz = szablony
        self.indeks = indeks_slotu

        # Cache geometrii
        self.sz.zapisz_undo() # Zapisujemy stan przed edycja
        self.base_coords = self.sz.sloty[self.indeks]["coords"].copy()
        self.temp_coords = self.base_coords.copy()

        self.title(f"Edytor Slotu #{indeks_slotu}")
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._zatwierdz_i_zamknij)

        self._render_job = None
        self._build_ui()

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = 460
        h = min(580, max(420, sh - 100))
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(380, 360)
        self.resizable(True, True)
        
    def _build_ui(self):
        # 1. Pinned footer na dole okna (przyciski ZAWSZE widoczne)
        footer = ttk.Frame(self, padding=(10, 8))
        footer.pack(side="bottom", fill="x")
        
        ttk.Button(footer, text="ANULUJ", command=self._anuluj).pack(side="left", expand=True, padx=5)
        ttk.Button(footer, text="ZATWIERDŹ", command=self._zatwierdz_i_zamknij).pack(side="left", expand=True, padx=5)

        # 2. Przewijalny kontener główny (Canvas + Scrollbar)
        main_container = ttk.Frame(self)
        main_container.pack(side="top", fill="both", expand=True)

        canvas = tk.Canvas(main_container, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        container = ttk.Frame(canvas, padding=(12, 10))
        canvas_window = canvas.create_window((0, 0), window=container, anchor="nw")

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        container.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            if not canvas.winfo_exists():
                return
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        def _bind_mousewheel(e):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(e):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        self.bind("<Enter>", _bind_mousewheel)
        self.bind("<Leave>", _unbind_mousewheel)
        self.bind("<Destroy>", lambda e: _unbind_mousewheel(e) if e.widget == self else None)

        # --- SEKCJA: GEOMETRIA ---
        ttk.Label(container, text="POZYCJA I ROZMIAR", font=("Arial", 10, "bold")).pack(anchor="w")
        
        ttk.Label(container, text="Przesunięcie X (Poziomo):").pack(anchor="w", pady=(3,0))
        self.move_x = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
        self.move_x.pack(fill="x", pady=2)
        
        ttk.Label(container, text="Przesunięcie Y (Pionowo):").pack(anchor="w", pady=(3,0))
        self.move_y = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
        self.move_y.pack(fill="x", pady=2)
        
        ttk.Label(container, text="Skala szerokości (%):").pack(anchor="w", pady=(3,0))
        self.scale_w = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
        self.scale_w.pack(fill="x", pady=2)
        
        ttk.Label(container, text="Skala wysokości (%):").pack(anchor="w", pady=(3,0))
        self.scale_h = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
        self.scale_h.pack(fill="x", pady=2)

        ttk.Separator(container).pack(fill="x", pady=6)

        # --- SEKCJA: WYGLĄD ---
        ttk.Label(container, text="WYGLĄD", font=("Arial", 10, "bold")).pack(anchor="w", pady=(4,0))
        
        col_frame = ttk.Frame(container)
        col_frame.pack(fill="x", pady=4)
        
        ttk.Button(col_frame, text="Kolor Tła", command=self._zmien_tlo).pack(side="left", expand=True, padx=2)
        ttk.Button(col_frame, text="Kolor Ramki", command=self._zmien_ramke).pack(side="left", expand=True, padx=2)
        
        ttk.Label(container, text="Grubość ramki:").pack(anchor="w", pady=(3,0))
        self.out_width = ttk.Entry(container)
        self.out_width.insert(0, str(self.sz.sloty[self.indeks].get("outline_width", 2)))
        self.out_width.pack(fill="x", pady=2)
        
        ttk.Button(container, text="Ustaw grubość ramki", command=self._ustaw_grubosc).pack(fill="x", pady=2)

        ttk.Separator(container).pack(fill="x", pady=6)

        # --- SEKCJA: MEDIA I TEKST ---
        ttk.Label(container, text="ZAWARTOŚĆ", font=("Arial", 10, "bold")).pack(anchor="w", pady=(4,0))
        
        ttk.Button(container, text="📋 Wklej Obraz ze Schowka", command=self._wklej_ze_schowka).pack(fill="x", pady=2)
        ttk.Button(container, text="Wstaw Obraz", command=self._wstaw_obraz).pack(fill="x", pady=2)
        ttk.Button(container, text="Stwórz Kolaż", command=self._wstaw_kolaz).pack(fill="x", pady=2)
        ttk.Button(container, text="Zmień Tekst", command=self._zmien_tekst).pack(fill="x", pady=2)
        ttk.Button(container, text="🔲 Generuj Siatkę w tym Slocie...", command=self._generuj_siatke).pack(fill="x", pady=2)
        ttk.Button(container, text="💾 Zapisz zawartość slotu jako JPG...", command=self._zapisz_jako_jpg).pack(fill="x", pady=2)

        row_clear = ttk.Frame(container)
        row_clear.pack(fill="x", pady=3)
        ttk.Button(row_clear, text="🧹 Wyczyść Obraz", command=self._wyczysc_obraz).pack(side="left", expand=True, fill="x", padx=1)
        ttk.Button(row_clear, text="🧹 Wyczyść Tekst", command=self._wyczysc_tekst).pack(side="left", expand=True, fill="x", padx=1)
        ttk.Button(container, text="🧹 Wyczyść Cały Slot (Wszystko)", command=self._wyczysc_slot).pack(fill="x", pady=2)

        ttk.Separator(container).pack(fill="x", pady=6)

        # --- SEKCJA: SYMBOL I ROLA (ZADANIE SŁOWNE) ---
        ttk.Label(container, text="ZADANIE SŁOWNE (SYMBOL / ROLA)", font=("Arial", 10, "bold")).pack(anchor="w", pady=(4, 0))
        ttk.Label(container, text="💡 Sloty o tym samym symbolu wyświetlają ten sam obraz!", font=("Arial", 8, "italic"), foreground="#555555").pack(anchor="w", pady=(1, 3))

        sym_role_frame = ttk.Frame(container)
        sym_role_frame.pack(fill="x", pady=4)

        ttk.Label(sym_role_frame, text="Symbol:").grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self.entry_symbol = ttk.Entry(sym_role_frame, width=10)
        self.entry_symbol.insert(0, str(self.sz.sloty[self.indeks].get("symbol", "") or ""))
        self.entry_symbol.grid(row=0, column=1, sticky="w", padx=2, pady=2)

        ttk.Label(sym_role_frame, text="Rola:").grid(row=1, column=0, sticky="w", padx=2, pady=2)
        curr_role_raw = str(self.sz.sloty[self.indeks].get("role", "") or "")
        curr_label = ROLE_VAL_TO_LABEL.get(curr_role_raw, curr_role_raw if curr_role_raw else "Brak / Zwykły slot")

        self.combo_role = ttk.Combobox(
            sym_role_frame,
            values=[label for _, label in ROLE_OPTIONS],
            state="readonly",
            width=28
        )
        self.combo_role.set(curr_label)
        self.combo_role.grid(row=1, column=1, sticky="w", padx=2, pady=2)

        ttk.Button(sym_role_frame, text="🔄 Synchronizuj ten symbol teraz", command=self._sync_symbol).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 2))

        def on_symbol_role_change(_=None):
            sym_val = self.entry_symbol.get().strip().upper()
            selected_label = self.combo_role.get().strip()
            role_val = ROLE_LABEL_TO_VAL.get(selected_label, "")
            if sym_val:
                self.sz.sloty[self.indeks]["symbol"] = sym_val
            elif "symbol" in self.sz.sloty[self.indeks]:
                del self.sz.sloty[self.indeks]["symbol"]

            if role_val:
                self.sz.sloty[self.indeks]["role"] = role_val
            elif "role" in self.sz.sloty[self.indeks]:
                del self.sz.sloty[self.indeks]["role"]

            self.sz.synchronizuj_symbole()
            self._schedule_render()

        self.entry_symbol.bind("<KeyRelease>", on_symbol_role_change)
        self.combo_role.bind("<<ComboboxSelected>>", on_symbol_role_change)

    def _generuj_siatke(self):
        self.destroy()
        if hasattr(self.parent, "generuj_siatke_w_slocie_dialog"):
            self.parent.generuj_siatke_w_slocie_dialog(self.indeks)

    def _sync_symbol(self):
        c = self.sz.synchronizuj_symbole()
        self.sz.prepare_render_data(force=True)
        self.parent.render()
        from tkinter import messagebox
        messagebox.showinfo("Synchronizacja", f"Zsynchronizowano obraz w {c} slotach o tym samym symbolu.")

    def _zmien_tlo(self):
        from tkinter import colorchooser
        kolor = colorchooser.askcolor()[1]
        if kolor:
            self.sz.edytuj_slot(self.indeks, fill=kolor)
            self.parent.render()

    def _zmien_ramke(self):
        from tkinter import colorchooser
        kolor = colorchooser.askcolor()[1]
        if kolor:
            self.sz.edytuj_slot(self.indeks, outline=kolor)
            self.parent.render()

    def _ustaw_grubosc(self):
        try:
            w = int(self.out_width.get())
            self.sz.edytuj_slot(self.indeks, outline_width=w)
            self.parent.render()
        except: pass

    def _zmien_tekst(self):
        curr = self.sz.sloty[self.indeks].get("tekst")
        def save_cb(tekst_cfg):
            if isinstance(tekst_cfg, dict) and tekst_cfg.get("typ") == "file":
                self.sz.wstaw_tekst_z_pliku(
                    indeks=self.indeks,
                    plik=tekst_cfg["file"],
                    separator=tekst_cfg["separator"],
                    index=tekst_cfg["index"],
                    align=tekst_cfg["align"]
                )
            else:
                self.sz.edytuj_slot(self.indeks, tekst=tekst_cfg)
            self.parent.render()

        open_text_config_dialog(self, curr, save_cb)

#    def _build_ui(self):
#        container = ttk.Frame(self, padding=15)
#        container.pack(fill="both", expand=True)

#        # --- SEKCJA: GEOMETRIA ---
#        ttk.Label(container, text="POZYCJA I ROZMIAR", font=("Arial", 10, "bold")).pack(anchor="w")
#        self.move_x = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
#        self.move_x.pack(fill="x", pady=2)
#        self.move_y = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
#        self.move_y.pack(fill="x", pady=2)
#        
#        self.scale_w = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
#        self.scale_w.pack(fill="x", pady=2)
#        self.scale_h = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
#        self.scale_h.pack(fill="x", pady=2)

#        ttk.Separator(container).pack(fill="x", pady=10)

#        # --- SEKCJA: OBRAZY I KOLORY ---
#        ttk.Label(container, text="WYGLĄD I MEDIA", font=("Arial", 10, "bold")).pack(anchor="w")
#        
#        btn_f = ttk.Frame(container)
#        btn_f.pack(fill="x", pady=5)
#        ttk.Button(btn_f, text="Kolor Tła", command=self._set_fill).pack(side="left", expand=True, fill="x")
#        ttk.Button(btn_f, text="Kolor Ramki", command=self._set_outline).pack(side="left", expand=True, fill="x")

#        ttk.Button(container, text="Wstaw Obraz", command=self._wstaw_obraz).pack(fill="x", pady=2)
#        ttk.Button(container, text="Kolaż (Siatka)", command=self._wstaw_kolaz).pack(fill="x", pady=2)
#        
#        ttk.Separator(container).pack(fill="x", pady=10)

#        # --- SEKCJA: TEKST ---
#        ttk.Label(container, text="TEKST", font=("Arial", 10, "bold")).pack(anchor="w")
#        ttk.Button(container, text="Ustaw Tekst", command=self._set_text).pack(fill="x", pady=2)

#        # --- SEKCJA: AKCJE KRYTYCZNE ---
#        ttk.Separator(container).pack(fill="x", pady=10)
#        ttk.Button(container, text="USUŃ SLOT", command=self._usun_slot, style="Danger.TButton").pack(fill="x", pady=5)

#        # STOPKA
#        footer = ttk.Frame(container)
#        footer.pack(side="bottom", fill="x", pady=10)
#        ttk.Button(footer, text="ANULUJ", command=self._anuluj).pack(side="left", expand=True, fill="x", padx=2)
#        ttk.Button(footer, text="OK", command=self._zatwierdz_i_zamknij).pack(side="left", expand=True, fill="x", padx=2)

    # --- LOGIKA ---
    def _aktualizuj_geo(self, _=None):
        bx1, by1, bx2, by2 = self.base_coords
        bw, bh = bx2-bx1, by2-by1
        cx, cy = (bx1+bx2)/2, (by1+by2)/2
        tx, ty, sw, sh = self.move_x.get(), self.move_y.get(), self.scale_w.get(), self.scale_h.get()
        
        nw, nh = bw * (1+sw/100), bh * (1+sh/100)
        dx, dy = (tx/100)*bw, (ty/100)*bh
        
        self.temp_coords = [int(cx-nw/2+dx), int(cy-nh/2+dy), int(cx+nw/2+dx), int(cy+nh/2+dy)]
        self.sz.sloty[self.indeks]["coords"] = self.temp_coords
        self._schedule_render()

    def _set_fill(self):
        c = colorchooser.askcolor()[1]
        if c: self.sz.sloty[self.indeks]["fill"] = c; self._schedule_render()

    def _set_outline(self):
        c = colorchooser.askcolor()[1]
        if c: self.sz.sloty[self.indeks]["outline"] = c; self._schedule_render()

    def _set_text(self):
        from gui.dialogs import with_dialog
        @with_dialog(title="Tekst", fields=[("Tekst", "str")])
        def logic(pw, txt):
            self.sz.sloty[self.indeks]["tekst"] = txt
            self._schedule_render()
        logic(self)
        #==========

    def _wstaw_obraz(self):
        from gui.image_picker import ImagePickerDialog
        curr_img = self.sz.sloty[self.indeks].get("image_path") or self.sz.sloty[self.indeks].get("image")
        curr_source = self.sz.sloty[self.indeks].get("image_source", "obrazy")

        def on_image_picked(filename, source):
            self.sz.wstaw_obrazek(self.indeks, filename, image_source=source)
            self._schedule_render()

        ImagePickerDialog(
            self,
            callback=on_image_picked,
            initial_source=curr_source,
            initial_file=curr_img if isinstance(curr_img, str) else "",
            title=f"Wybierz obraz dla slotu #{self.indeks}"
        )
    def _wstaw_kolaz(self):
        from gui.dialogs import with_dialog
        import random
    
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
            
            # 1. Priorytet: Slot źródłowy
            if src_slot >= 0:
                self.sz.wklej_jeden_obraz_na_kolaz(
                    indeks=self.indeks,
                    sciezka=sciezka,
                    source_slot=src_slot
                )
            # 2. Random
            elif ilosc == 0:
                if min_n <= 0 or max_n <= 0 or min_n > max_n:
                    from tkinter import messagebox
                    messagebox.showerror(
                        "Błąd",
                        "Dla random: min i max muszą być > 0 oraz min ≤ max"
                    )
                    return
    
                self.sz.wklej_jeden_obraz_na_kolaz(
                    indeks=self.indeks,
                    sciezka=sciezka,
                    random_cfg={
                        "min": min_n,
                        "max": max_n
                    }
                )
            # 3. Stała ilość
            else:
                self.sz.wklej_jeden_obraz_na_kolaz(
                    indeks=self.indeks,
                    sciezka=sciezka,
                    ilosc=ilosc
                )
    
            self._schedule_render()
    
        logic(self)

    def _wyczysc_obraz(self):
        self.sz.wyczysc_obraz(self.indeks)
        self._schedule_render()

    def _wyczysc_tekst(self):
        self.sz.wyczysc_tekst(self.indeks)
        self._schedule_render()

    def _wyczysc_slot(self):
        self.sz.wyczysc_slot(self.indeks, co="wszystko")
        self._schedule_render()

    def _usun_slot(self):
        self.sz.usun_slot(self.indeks)
        self.parent.render()
        self.destroy()

    def _schedule_render(self):
        if self._render_job: self.after_cancel(self._render_job)
        self._render_job = self.after(80, self._do_render)

    def _do_render(self):
        self.parent.render()
        self._render_job = None

    def _zatwierdz_i_zamknij(self):
        self.sz.sloty[self.indeks]["coords"] = self.temp_coords
        self.parent.render()
        self.destroy()

    def _wklej_ze_schowka(self):
        from gui.main_window import pobierz_obraz_ze_schowka
        img = pobierz_obraz_ze_schowka()
        if not img:
            from tkinter import messagebox
            messagebox.showinfo("Schowek pusty", "W schowku nie znaleziono obrazu ani pliku graficznego.")
            return
        from paths import OBRAZY_DIR
        import time
        ts = int(time.time() * 1000) % 1000000
        filename = f"wklejony_slot_{self.indeks}_{ts}.jpg"
        img.save(OBRAZY_DIR / filename, "JPEG", quality=95)
        self.sz.wstaw_obrazek(self.indeks, filename, image_source="obrazy")
        self.parent.render()
        from tkinter import messagebox
        messagebox.showinfo("Wklejono", f"Wklejono obraz ze schowka do slotu #{self.indeks}.")

    def _zapisz_jako_jpg(self):
        from gui.dialogs import SaveSlotsDialog
        SaveSlotsDialog(self, self.sz, slots=[self.indeks])

    def _anuluj(self):
        self.sz.sloty[self.indeks]["coords"] = self.base_coords
        self.parent.render()
        self.destroy()


def open_text_config_dialog(parent, current_data, on_save_callback):
    top = tk.Toplevel(parent)
    top.title("Konfiguracja tekstu")
    top.geometry("450x550")
    top.transient(parent)
    top.grab_set()

    container = ttk.Frame(top, padding=10)
    container.pack(fill="both", expand=True)

    mode_var = tk.StringVar(value="manual")

    # --- Frames ---
    f_manual = ttk.LabelFrame(container, text="Tekst Ręczny", padding=10)
    f_file = ttk.LabelFrame(container, text="Tekst z Pliku", padding=10)
    f_random = ttk.LabelFrame(container, text="Losowa Liczba (Zakres)", padding=10)
    f_dep = ttk.LabelFrame(container, text="Zależna Liczba", padding=10)

    # --- MANUAL UI ---
    ttk.Label(f_manual, text="Treść:").pack(anchor="w")
    e_manual = ttk.Entry(f_manual)
    e_manual.pack(fill="x", pady=5)

    # --- FILE UI ---
    ttk.Label(f_file, text="Ścieżka do pliku (.txt):").pack(anchor="w")
    e_file = ttk.Entry(f_file)
    e_file.pack(fill="x", pady=2)
    
    row_opts = ttk.Frame(f_file)
    row_opts.pack(fill="x", pady=5)
    
    ttk.Label(row_opts, text="Separator:").pack(side="left")
    e_sep = ttk.Entry(row_opts, width=5)
    e_sep.pack(side="left", padx=5)
    e_sep.insert(0, ",")
    
    ttk.Label(row_opts, text="Index:").pack(side="left", padx=(10,0))
    e_idx = ttk.Entry(row_opts, width=5)
    e_idx.pack(side="left", padx=5)
    e_idx.insert(0, "0")
    
    # --- RANDOM UI ---
    ttk.Label(f_random, text="Zakres (min-max):").pack(anchor="w")
    e_range = ttk.Entry(f_random)
    e_range.pack(fill="x", pady=5)
    e_range.insert(0, "1-100")
    
    # --- DEPENDENT UI ---
    ttk.Label(f_dep, text="Slot źródłowy (Index):").pack(anchor="w")
    e_src_idx = ttk.Entry(f_dep)
    e_src_idx.pack(fill="x", pady=2)
    e_src_idx.insert(0, "0")
    
    ttk.Label(f_dep, text="Relacja:").pack(anchor="w", pady=(5,0))
    rel_var = tk.StringVar(value="smaller")
    
    def update_limit_label():
        if rel_var.get() == "smaller":
            l_limit.config(text="Dolna granica (domyślnie 0):")
        else:
            l_limit.config(text="Górna granica (wymagana):")
            
    ttk.Radiobutton(f_dep, text="Mniejsza od źródła", variable=rel_var, value="smaller", command=update_limit_label).pack(anchor="w")
    ttk.Radiobutton(f_dep, text="Większa od źródła", variable=rel_var, value="larger", command=update_limit_label).pack(anchor="w")
    
    l_limit = ttk.Label(f_dep, text="Limit:")
    l_limit.pack(anchor="w", pady=(5,0))
    e_limit = ttk.Entry(f_dep)
    e_limit.pack(fill="x", pady=2)
    e_limit.insert(0, "0")

    update_limit_label()

    # --- ALIGNMENT ---
    f_align = ttk.LabelFrame(container, text="Wyrównanie", padding=10)
    f_align.pack(fill="x", pady=5)
    
    align_var = tk.StringVar(value="center")
    
    ttk.Radiobutton(f_align, text="Do lewej", variable=align_var, value="left").pack(side="left", padx=5)
    ttk.Radiobutton(f_align, text="Środek", variable=align_var, value="center").pack(side="left", padx=5)
    ttk.Radiobutton(f_align, text="Do prawej", variable=align_var, value="right").pack(side="left", padx=5)

    # --- LOGIKA PRZEŁĄCZANIA ---
    def update_visibility():
        mode = mode_var.get()
        f_manual.pack_forget()
        f_file.pack_forget()
        f_random.pack_forget()
        f_dep.pack_forget()
        
        if mode == "manual":
            f_manual.pack(fill="x", pady=5)
        elif mode == "file":
            f_file.pack(fill="x", pady=5)
        elif mode == "random":
            f_random.pack(fill="x", pady=5)
        elif mode == "random_dependent":
            f_dep.pack(fill="x", pady=5)

    ttk.Radiobutton(container, text="Wpisz ręcznie", variable=mode_var, value="manual", command=update_visibility).pack(anchor="w")
    ttk.Radiobutton(container, text="Wczytaj z pliku", variable=mode_var, value="file", command=update_visibility).pack(anchor="w")
    ttk.Radiobutton(container, text="Losowa liczba", variable=mode_var, value="random", command=update_visibility).pack(anchor="w")
    ttk.Radiobutton(container, text="Zależna liczba", variable=mode_var, value="random_dependent", command=update_visibility).pack(anchor="w")

    # --- ŁADOWANIE DANYCH ---
    curr = current_data
    initial_align = "center"
    if isinstance(curr, dict):
        initial_align = curr.get("align", "center")
    align_var.set(initial_align)
    
    if isinstance(curr, dict):
        typ = curr.get("typ", "manual")
        if typ == "file":
            mode_var.set("file")
            e_file.insert(0, curr.get("file", ""))
            e_sep.delete(0, "end"); e_sep.insert(0, curr.get("separator", ","))
            e_idx.delete(0, "end"); e_idx.insert(0, str(curr.get("index", 0)))
        elif typ == "random":
            mode_var.set("random")
            e_range.delete(0, "end")
            e_range.insert(0, curr.get("range", "1-100"))
        elif typ == "random_dependent":
            mode_var.set("random_dependent")
            e_src_idx.delete(0, "end"); e_src_idx.insert(0, str(curr.get("source", 0)))
            rel_var.set(curr.get("relation", "smaller"))
            e_limit.delete(0, "end"); e_limit.insert(0, str(curr.get("limit", 0)))
            update_limit_label()
        else:
            mode_var.set("manual")
            e_manual.delete(0, "end")
            e_manual.insert(0, curr.get("value", ""))
    else:
        mode_var.set("manual")
        val = curr if isinstance(curr, str) else ""
        e_manual.delete(0, "end")
        e_manual.insert(0, val)
        
    update_visibility()

    # --- ZATWIERDZANIE ---
    def on_save():
        chosen_align = align_var.get()
        mode = mode_var.get()
        
        if mode == "manual":
            tekst_cfg = {
                "typ": "manual",
                "value": e_manual.get(),
                "align": chosen_align
            }
        elif mode == "file":
            try:
                idx = int(e_idx.get())
            except:
                idx = 0
            tekst_cfg = {
                "typ": "file",
                "file": e_file.get(),
                "separator": e_sep.get(),
                "index": idx,
                "align": chosen_align
            }
        elif mode == "random":
            tekst_cfg = {
                "typ": "random",
                "range": e_range.get(),
                "align": chosen_align
            }
        elif mode == "random_dependent":
            try:
                src = int(e_src_idx.get())
            except:
                src = 0
            try:
                lim = int(e_limit.get())
            except:
                lim = 0
            tekst_cfg = {
                "typ": "random_dependent",
                "source": src,
                "relation": rel_var.get(),
                "limit": lim,
                "align": chosen_align
            }
            
        on_save_callback(tekst_cfg)
        top.destroy()

    ttk.Button(container, text="Zatwierdź", command=on_save).pack(pady=10)


class RangeOverflowDialog(tk.Toplevel):
    def __init__(self, parent, num_slots, num_available):
        super().__init__(parent)
        self.title("Zakres za mały")
        self.result = "reduce"  # Domyślna opcja: "Zmniejsz zaznaczenie"
        self.transient(parent)
        self.grab_set()

        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)

        msg = (
            f"Wybrano więcej slotów ({num_slots}) niż dostępnych unikalnych liczb ({num_available}).\n"
            "Co chcesz zrobić?"
        )
        ttk.Label(container, text=msg, justify="center", font=("Arial", 10)).pack(pady=(0, 15))

        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill="x", pady=5)

        # 1. Zmniejsz zaznaczenie (Domyślna)
        b1 = ttk.Button(btn_frame, text="Zmniejsz zaznaczenie", command=lambda: self._set_choice("reduce"))
        b1.pack(fill="x", pady=3)
        b1.focus_set()

        # 2. Zwiększ zakres
        b2 = ttk.Button(btn_frame, text="Zwiększ zakres", command=lambda: self._set_choice("expand"))
        b2.pack(fill="x", pady=3)

        # 3. Anuluj
        b3 = ttk.Button(btn_frame, text="Anuluj", command=lambda: self._set_choice("cancel"))
        b3.pack(fill="x", pady=3)

        self.protocol("WM_DELETE_WINDOW", lambda: self._set_choice("cancel"))
        self.bind("<Return>", lambda e: self._set_choice("reduce"))
        self.bind("<Escape>", lambda e: self._set_choice("cancel"))

        self.update_idletasks()
        self.resizable(False, False)
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"+{x}+{y}")

        self.wait_window()

    def _set_choice(self, choice):
        self.result = choice
        self.destroy()


def open_random_numbers_dialog(parent, sz, slots=None, initial_min=1, initial_max=20):
    if slots is None:
        target_slots = list(range(len(sz.sloty)))
    else:
        target_slots = list(slots)

    if not target_slots:
        from tkinter import messagebox
        messagebox.showwarning("Brak slotów", "Brak slotów do przypisania liczb.")
        return

    top = tk.Toplevel(parent)
    top.title("Losuj liczby bez powtórzeń")
    top.geometry("320x220")
    top.transient(parent)
    top.grab_set()

    container = ttk.Frame(top, padding=15)
    container.pack(fill="both", expand=True)

    ttk.Label(container, text=f"Losowanie dla {len(target_slots)} slotów", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 10))

    ttk.Label(container, text="Minimum:").pack(anchor="w", pady=(4, 2))
    e_min = ttk.Entry(container)
    e_min.insert(0, str(initial_min))
    e_min.pack(fill="x")

    ttk.Label(container, text="Maksimum:").pack(anchor="w", pady=(6, 2))
    e_max = ttk.Entry(container)
    e_max.insert(0, str(initial_max))
    e_max.pack(fill="x")

    def on_ok():
        try:
            min_val = int(e_min.get().strip())
            max_val = int(e_max.get().strip())
        except ValueError:
            from tkinter import messagebox
            messagebox.showerror("Błąd", "Wprowadź poprawne liczby całkowite!")
            return

        if min_val > max_val:
            min_val, max_val = max_val, min_val

        top.destroy()
        _process_random_numbers(parent, sz, target_slots, min_val, max_val)

    ttk.Separator(container).pack(fill="x", pady=12)
    ttk.Button(container, text="Losuj", command=on_ok).pack(fill="x")

    top.update_idletasks()
    top.resizable(False, False)
    w = top.winfo_reqwidth()
    h = top.winfo_reqheight()
    sw = top.winfo_screenwidth()
    sh = top.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    top.geometry(f"+{x}+{y}")


def _process_random_numbers(parent, sz, target_slots, min_val, max_val):
    num_slots = len(target_slots)
    avail_count = max_val - min_val + 1

    if num_slots > avail_count:
        dlg = RangeOverflowDialog(parent, num_slots, avail_count)
        choice = dlg.result

        if choice == "reduce":
            final_slots = target_slots[:avail_count]
            # Zaktualizuj zaznaczenie w oknie głównym, jeśli to dotyczy zaznaczenia
            mw = parent if hasattr(parent, "selected_slots_ordered") else getattr(parent, "parent", None)
            if mw and hasattr(mw, "selected_slots_ordered"):
                mw.selected_slots_ordered = list(final_slots)
                mw.selected_slots = set(final_slots)
                if hasattr(mw, "_draw_selection_highlights"):
                    mw._draw_selection_highlights()
                if hasattr(mw, "_update_ui_state"):
                    mw._update_ui_state()

            sz.losuj_liczby_bez_powtorzen(min_val, max_val, slots=final_slots)
            if hasattr(parent, "parent") and hasattr(parent.parent, "render"):
                parent.parent.render()
            elif hasattr(parent, "render"):
                parent.render()

        elif choice == "expand":
            open_random_numbers_dialog(parent, sz, slots=target_slots, initial_min=min_val, initial_max=max_val)
        else:
            # cancel
            return
    else:
        sz.losuj_liczby_bez_powtorzen(min_val, max_val, slots=target_slots)
        if hasattr(parent, "parent") and hasattr(parent.parent, "render"):
            parent.parent.render()
        elif hasattr(parent, "render"):
            parent.render()


class AllSlotsEditorWindow(tk.Toplevel):
    def __init__(self, parent, szablony, slots=None, title=None):
        super().__init__(parent)
        self.parent = parent
        self.sz = szablony

        # Jeśli slots nie podano, edytujemy wszystkie sloty
        if slots is not None:
            self.slots = list(slots)
            default_title = f"Edycja zaznaczonych slotów ({len(self.slots)})"
            self.header_text = f"EDYCJA ZAZNACZONYCH ({len(self.slots)} slotów)"
        else:
            self.slots = list(range(len(self.sz.sloty)))
            default_title = "Edytor wszystkich slotów"
            self.header_text = f"EDYCJA HURTOWA ({len(self.sz.sloty)} slotów)"

        self.title(title if title else default_title)
        self.transient(parent)

        self.sz.zapisz_undo()
        self._build_ui()

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = 460
        h = min(580, max(420, sh - 100))
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(380, 360)
        self.resizable(True, True)

    def _build_ui(self):
        # 1. Pinned footer na dole okna (przycisk ZAMKNIJ ZAWSZE widoczny)
        footer = ttk.Frame(self, padding=(10, 8))
        footer.pack(side="bottom", fill="x")
        ttk.Button(footer, text="ZAMKNIJ", command=self.destroy).pack(side="left", expand=True, padx=5)

        # 2. Główny kontener na całe okno (zawiera Canvas i Scrollbar)
        main_container = ttk.Frame(self)
        main_container.pack(side="top", fill="both", expand=True)

        canvas = tk.Canvas(main_container, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)

        container = ttk.Frame(canvas, padding=(12, 10))

        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        canvas_window = canvas.create_window((0, 0), window=container, anchor="nw")

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        container.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            if not canvas.winfo_exists():
                return
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        def _bind_mousewheel(e):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(e):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        self.bind("<Enter>", _bind_mousewheel)
        self.bind("<Leave>", _unbind_mousewheel)
        self.bind("<Destroy>", lambda e: _unbind_mousewheel(e) if e.widget == self else None)

        # NAGŁÓWEK
        ttk.Label(
            container,
            text=self.header_text,
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(0, 8))

        # --- SEKCJA: WYGLĄD ---
        ttk.Label(container, text="WYGLĄD", font=("Arial", 10, "bold")).pack(anchor="w", pady=(4, 0))

        col_frame = ttk.Frame(container)
        col_frame.pack(fill="x", pady=4)

        ttk.Button(col_frame, text="Kolor Tła", command=self._zmien_tlo).pack(side="left", expand=True, padx=2)
        ttk.Button(col_frame, text="Kolor Ramki", command=self._zmien_ramke).pack(side="left", expand=True, padx=2)

        ttk.Label(container, text="Grubość ramki:").pack(anchor="w", pady=(3, 0))
        self.out_width = ttk.Entry(container)
        first_idx = self.slots[0] if self.slots else 0
        default_w = str(self.sz.sloty[first_idx].get("outline_width", 2)) if (
                    0 <= first_idx < len(self.sz.sloty)) else "2"
        self.out_width.insert(0, default_w)
        self.out_width.pack(fill="x", pady=2)

        ttk.Button(container, text="Ustaw grubość ramki", command=self._ustaw_grubosc).pack(fill="x", pady=2)

        ttk.Separator(container).pack(fill="x", pady=6)

        # --- SEKCJA: MEDIA I TEKST ---
        ttk.Label(container, text="ZAWARTOŚĆ", font=("Arial", 10, "bold")).pack(anchor="w", pady=(4, 0))

        ttk.Button(container, text="📋 Wklej Obraz ze Schowka do Zaznaczonych", command=self._wklej_ze_schowka).pack(
            fill="x", pady=2)
        ttk.Button(container, text="Wstaw Obraz", command=self._wstaw_obraz).pack(fill="x", pady=2)
        ttk.Button(container, text="Stwórz Kolaż", command=self._wstaw_kolaz).pack(fill="x", pady=2)
        ttk.Button(container, text="Zmień Tekst", command=self._zmien_tekst).pack(fill="x", pady=2)
        ttk.Button(container, text="Losuj liczby bez powtórzeń", command=self._losuj_liczby).pack(fill="x", pady=2)
        ttk.Button(container, text="🎲 Losuj unikalne obrazy (obrazy stałe)", command=self._losuj_obrazy_stale).pack(fill="x", pady=2)
        ttk.Button(container, text="🔄 Synchronizuj zawartość wg symboli", command=self._synchronizuj_symbole).pack(fill="x", pady=2)
        ttk.Button(container, text="💾 Zapisz zawartość slotów jako JPG...", command=self._zapisz_jako_jpg).pack(
            fill="x", pady=2)

        row_clear = ttk.Frame(container)
        row_clear.pack(fill="x", pady=3)
        ttk.Button(row_clear, text="🧹 Wyczyść Obraz", command=self._wyczysc_obraz).pack(side="left", expand=True,
                                                                                        fill="x", padx=1)
        ttk.Button(row_clear, text="🧹 Wyczyść Tekst", command=self._wyczysc_tekst).pack(side="left", expand=True,
                                                                                        fill="x", padx=1)
        ttk.Button(container, text="🧹 Wyczyść Zawartość Slotów", command=self._wyczysc_slot).pack(fill="x", pady=2)

        # --- SEKCJA: ROLA (DLA ZAZNACZONYCH) ---
        ttk.Separator(container).pack(fill="x", pady=6)
        ttk.Label(container, text="ZADANIE SŁOWNE (ROLA DLA ZAZNACZONYCH)", font=("Arial", 10, "bold")).pack(anchor="w",
                                                                                                             pady=(4,
                                                                                                                   0))

        role_frame = ttk.Frame(container)
        role_frame.pack(fill="x", pady=4)
        ttk.Label(role_frame, text="Rola:").pack(side="left", padx=(0, 5))

        self.combo_role_all = ttk.Combobox(
            role_frame,
            values=[label for _, label in ROLE_OPTIONS],
            state="readonly",
            width=28
        )
        first_role = str(self.sz.sloty[self.slots[0]].get("role", "") or "") if self.slots else ""
        self.combo_role_all.set(ROLE_VAL_TO_LABEL.get(first_role, "Brak / Zwykły slot"))
        self.combo_role_all.pack(side="left", fill="x", expand=True)

        def on_all_role_change(_=None):
            selected_label = self.combo_role_all.get().strip()
            role_val = ROLE_LABEL_TO_VAL.get(selected_label, "")
            self.sz.zapisz_undo()
            for idx in self.slots:
                if 0 <= idx < len(self.sz.sloty):
                    if role_val:
                        self.sz.sloty[idx]["role"] = role_val
                    elif "role" in self.sz.sloty[idx]:
                        del self.sz.sloty[idx]["role"]
            self.parent.render()

        self.combo_role_all.bind("<<ComboboxSelected>>", on_all_role_change)

    def _zmien_tlo(self):
        kolor = colorchooser.askcolor()[1]
        if kolor:
            self.sz.edytuj_slot(slots=self.slots, fill=kolor)
            self.parent.render()

    def _zmien_ramke(self):
        kolor = colorchooser.askcolor()[1]
        if kolor:
            self.sz.edytuj_slot(slots=self.slots, outline=kolor)
            self.parent.render()

    def _ustaw_grubosc(self):
        try:
            w = int(self.out_width.get())
            self.sz.edytuj_slot(slots=self.slots, outline_width=w)
            self.parent.render()
        except:
            pass

    def _wstaw_obraz(self):
        from gui.image_picker import ImagePickerDialog
        first_idx = self.slots[0] if self.slots else 0
        curr_img = (self.sz.sloty[first_idx].get("image_path") or self.sz.sloty[first_idx].get("image")) if (0 <= first_idx < len(self.sz.sloty)) else ""
        curr_source = self.sz.sloty[first_idx].get("image_source", "obrazy") if (0 <= first_idx < len(self.sz.sloty)) else "obrazy"

        def on_image_picked(filename, source):
            self.sz.wstaw_obrazek(slots=self.slots, sciezka=filename, image_source=source)
            self.parent.render()

        ImagePickerDialog(
            self,
            callback=on_image_picked,
            initial_source=curr_source,
            initial_file=curr_img if isinstance(curr_img, str) else "",
            title=f"Wybierz obraz ({len(self.slots)} slotów)"
        )

    def _wstaw_kolaz(self):
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
                    slots=self.slots
                )
            elif ilosc == 0:
                if min_n <= 0 or max_n <= 0 or min_n > max_n:
                    from tkinter import messagebox
                    messagebox.showerror(
                        "Błąd",
                        "Dla random: min i max muszą być > 0 oraz min ≤ max"
                    )
                    return

                self.sz.wklej_jeden_obraz_na_kolaz(
                    sciezka=sciezka,
                    random_cfg={"min": min_n, "max": max_n},
                    slots=self.slots
                )
            else:
                self.sz.wklej_jeden_obraz_na_kolaz(
                    sciezka=sciezka,
                    ilosc=ilosc,
                    slots=self.slots
                )

            self.parent.render()

        logic(self)

    def _zmien_tekst(self):
        first_idx = self.slots[0] if self.slots else 0
        first_txt = self.sz.sloty[first_idx].get("tekst") if (0 <= first_idx < len(self.sz.sloty)) else None
        def save_cb(tekst_cfg):
            if isinstance(tekst_cfg, dict) and tekst_cfg.get("typ") == "file":
                self.sz.wstaw_tekst_z_pliku(
                    plik=tekst_cfg["file"],
                    separator=tekst_cfg["separator"],
                    index=tekst_cfg["index"],
                    align=tekst_cfg["align"],
                    slots=self.slots
                )
            else:
                self.sz.ustaw_tekst_wszystkim(tekst_cfg, slots=self.slots)
            self.parent.render()

        open_text_config_dialog(self, first_txt, save_cb)

    def _losuj_liczby(self):
        open_random_numbers_dialog(self, self.sz, slots=self.slots)

    def _wyczysc_obraz(self):
        self.sz.wyczysc_obraz(slots=self.slots)
        self.parent.render()

    def _wyczysc_tekst(self):
        self.sz.wyczysc_tekst(slots=self.slots)
        self.parent.render()

    def _wyczysc_slot(self):
        self.sz.wyczysc_slot(slots=self.slots, co="wszystko")
        self.parent.render()

    def _wklej_ze_schowka(self):
        from gui.main_window import pobierz_obraz_ze_schowka
        img = pobierz_obraz_ze_schowka()
        if not img:
            from tkinter import messagebox
            messagebox.showinfo("Schowek pusty", "W schowku nie znaleziono obrazu ani pliku graficznego.")
            return
        from paths import OBRAZY_DIR
        import time
        ts = int(time.time() * 1000) % 1000000
        filename = f"wklejony_{ts}.jpg"
        img.save(OBRAZY_DIR / filename, "JPEG", quality=95)
        self.sz.wstaw_obrazek(slots=self.slots, sciezka=filename, image_source="obrazy")
        self.parent.render()
        from tkinter import messagebox
        messagebox.showinfo("Wklejono", f"Wklejono obraz ze schowka do {len(self.slots)} slotów.")

    def _zapisz_jako_jpg(self):
        from gui.dialogs import SaveSlotsDialog
        SaveSlotsDialog(self, self.sz, slots=self.slots)

    def _losuj_obrazy_stale(self):
        try:
            assigned = self.sz.losuj_obrazy_stale(slots=self.slots, unikalne=True)
            self.parent.render()
            from tkinter import messagebox
            messagebox.showinfo("Wylosowano obrazy", f"Przypisano unikalne obrazy ze stałych do {len(assigned)} slotów.\nPowiązane sloty o tych samych symbolach zostały zaktualizowane.")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Błąd", str(e))

    def _synchronizuj_symbole(self):
        c = self.sz.synchronizuj_symbole()
        self.sz.prepare_render_data(force=True)
        self.parent.render()
        from tkinter import messagebox
        messagebox.showinfo("Synchronizacja", f"Zsynchronizowano obrazy w {c} slotach o pasujących symbolach.")


GroupSlotsEditorWindow = AllSlotsEditorWindow
