import tkinter as tk
from tkinter import ttk
from tkinter import colorchooser

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
        self.geometry("450x800")
        self.protocol("WM_DELETE_WINDOW", self._zatwierdz_i_zamknij)

        self._render_job = None
        self._build_ui()
        
    def _build_ui(self):
        # 1. TWORZYMY KONTENER (Musi być na samym początku!)
        container = ttk.Frame(self, padding=15)
        container.pack(fill="both", expand=True)

        # --- SEKCJA: GEOMETRIA ---
        ttk.Label(container, text="POZYCJA I ROZMIAR", font=("Arial", 10, "bold")).pack(anchor="w")
        
        ttk.Label(container, text="Przesunięcie X (Poziomo):").pack(anchor="w", pady=(4,0))
        self.move_x = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
        self.move_x.pack(fill="x", pady=2)
        
        ttk.Label(container, text="Przesunięcie Y (Pionowo):").pack(anchor="w", pady=(4,0))
        self.move_y = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
        self.move_y.pack(fill="x", pady=2)
        
        ttk.Label(container, text="Skala szerokości (%):").pack(anchor="w", pady=(4,0))
        self.scale_w = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
        self.scale_w.pack(fill="x", pady=2)
        
        ttk.Label(container, text="Skala wysokości (%):").pack(anchor="w", pady=(4,0))
        self.scale_h = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
        self.scale_h.pack(fill="x", pady=2)

        ttk.Separator(container).pack(fill="x", pady=10)

        # --- SEKCJA: WYGLĄD (Tu był błąd) ---
        ttk.Label(container, text="WYGLĄD", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10,0))
        
        col_frame = ttk.Frame(container)
        col_frame.pack(fill="x", pady=5)
        
        ttk.Button(col_frame, text="Kolor Tła", command=self._zmien_tlo).pack(side="left", expand=True, padx=2)
        ttk.Button(col_frame, text="Kolor Ramki", command=self._zmien_ramke).pack(side="left", expand=True, padx=2)
        
        ttk.Label(container, text="Grubość ramki:").pack(anchor="w")
        self.out_width = ttk.Entry(container)
        self.out_width.insert(0, str(self.sz.sloty[self.indeks].get("outline_width", 2)))
        self.out_width.pack(fill="x", pady=2)
        
        ttk.Button(container, text="Ustaw grubość ramki", command=self._ustaw_grubosc).pack(fill="x")

        ttk.Separator(container).pack(fill="x", pady=10)

        # --- SEKCJA: MEDIA I TEKST ---
        ttk.Label(container, text="ZAWARTOŚĆ", font=("Arial", 10, "bold")).pack(anchor="w")
        
        ttk.Button(container, text="Wstaw Obraz", command=self._wstaw_obraz).pack(fill="x", pady=2)
        ttk.Button(container, text="Stwórz Kolaż", command=self._wstaw_kolaz).pack(fill="x", pady=2)
        ttk.Button(container, text="Zmień Tekst", command=self._zmien_tekst).pack(fill="x", pady=2)

        # --- STOPKA ---
        footer = ttk.Frame(container)
        footer.pack(side="bottom", fill="x", pady=10)
        
        ttk.Button(footer, text="ANULUJ", command=self._anuluj).pack(side="left", expand=True, padx=5)
        ttk.Button(footer, text="ZATWIERDŹ", command=self._zatwierdz_i_zamknij).pack(side="left", expand=True, padx=5)

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
        from gui.dialogs import with_dialog
        @with_dialog(title="Obraz", fields=[("Nazwa pliku", "str")])
        def logic(pw, s):
            self.sz.wstaw_obrazek(self.indeks, s)
            self._schedule_render()
        logic(self)
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
    
#    def _wstaw_kolaz(self):
#        from gui.dialogs import with_dialog
#        @with_dialog(title="Kolaż", fields=[("Plik", "str"), ("Ilość", "int")])
#        def logic(pw, s, n):
#            self.sz.wklej_jeden_obraz_na_kolaz(self.indeks, s, n)
#            self._schedule_render()
#        logic(self)

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
        self.geometry("450x700")
        self.transient(parent)

        self.sz.zapisz_undo()
        self._build_ui()

    def _build_ui(self):
        container = ttk.Frame(self, padding=15)
        container.pack(fill="both", expand=True)

        # NAGŁÓWEK
        ttk.Label(
            container, 
            text=self.header_text, 
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(0, 10))

        # --- SEKCJA: WYGLĄD ---
        ttk.Label(container, text="WYGLĄD", font=("Arial", 10, "bold")).pack(anchor="w", pady=(5, 0))

        col_frame = ttk.Frame(container)
        col_frame.pack(fill="x", pady=5)

        ttk.Button(col_frame, text="Kolor Tła", command=self._zmien_tlo).pack(side="left", expand=True, padx=2)
        ttk.Button(col_frame, text="Kolor Ramki", command=self._zmien_ramke).pack(side="left", expand=True, padx=2)

        ttk.Label(container, text="Grubość ramki:").pack(anchor="w", pady=(5, 0))
        self.out_width = ttk.Entry(container)
        first_idx = self.slots[0] if self.slots else 0
        default_w = str(self.sz.sloty[first_idx].get("outline_width", 2)) if (0 <= first_idx < len(self.sz.sloty)) else "2"
        self.out_width.insert(0, default_w)
        self.out_width.pack(fill="x", pady=2)

        ttk.Button(container, text="Ustaw grubość ramki", command=self._ustaw_grubosc).pack(fill="x", pady=2)

        ttk.Separator(container).pack(fill="x", pady=15)

        # --- SEKCJA: MEDIA I TEKST ---
        ttk.Label(container, text="ZAWARTOŚĆ", font=("Arial", 10, "bold")).pack(anchor="w", pady=(5, 0))

        ttk.Button(container, text="Wstaw Obraz", command=self._wstaw_obraz).pack(fill="x", pady=3)
        ttk.Button(container, text="Stwórz Kolaż", command=self._wstaw_kolaz).pack(fill="x", pady=3)
        ttk.Button(container, text="Zmień Tekst", command=self._zmien_tekst).pack(fill="x", pady=3)
        ttk.Button(container, text="Losuj liczby bez powtórzeń", command=self._losuj_liczby).pack(fill="x", pady=3)

        ttk.Separator(container).pack(fill="x", pady=15)

        # --- STOPKA ---
        footer = ttk.Frame(container)
        footer.pack(side="bottom", fill="x", pady=10)

        ttk.Button(footer, text="ZAMKNIJ", command=self.destroy).pack(side="left", expand=True, padx=5)

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
        from gui.dialogs import with_dialog
        @with_dialog(title="Wstaw obraz", fields=[("Nazwa pliku", "str")])
        def logic(pw, s):
            self.sz.wstaw_obrazek(sciezka=s, slots=self.slots)
            self.parent.render()
        logic(self)

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


GroupSlotsEditorWindow = AllSlotsEditorWindow
