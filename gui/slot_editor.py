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
        
        self.move_x = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
        self.move_x.pack(fill="x", pady=2)
        
        self.move_y = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
        self.move_y.pack(fill="x", pady=2)
        
        self.scale_w = ttk.Scale(container, from_=-100, to=100, command=self._aktualizuj_geo)
        self.scale_w.pack(fill="x", pady=2)
        
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
        # Tworzymy dedykowane okno dialogowe
        top = tk.Toplevel(self)
        top.title("Konfiguracja tekstu")
        top.geometry("400x350")
        
        container = ttk.Frame(top, padding=10)
        container.pack(fill="both", expand=True)

        mode_var = tk.StringVar(value="manual")

        # --- Frames ---
        f_manual = ttk.LabelFrame(container, text="Tekst Ręczny", padding=10)
        f_file = ttk.LabelFrame(container, text="Tekst z Pliku", padding=10)

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
            if mode == "manual":
                f_manual.pack(fill="x", pady=5)
                f_file.pack_forget()
            else:
                f_manual.pack_forget()
                f_file.pack(fill="x", pady=5)

        ttk.Radiobutton(container, text="Wpisz ręcznie", variable=mode_var, value="manual", command=update_visibility).pack(anchor="w")
        ttk.Radiobutton(container, text="Wczytaj z pliku", variable=mode_var, value="file", command=update_visibility).pack(anchor="w")

        # --- ŁADOWANIE DANYCH ---
        curr = self.sz.sloty[self.indeks].get("tekst")
        
        # Load align
        initial_align = "center"
        if isinstance(curr, dict):
            initial_align = curr.get("align", "center")
        align_var.set(initial_align)
        
        if isinstance(curr, dict) and curr.get("typ") == "file":
            mode_var.set("file")
            e_file.insert(0, curr.get("file", ""))
            e_sep.delete(0, "end"); e_sep.insert(0, curr.get("separator", ","))
            e_idx.delete(0, "end"); e_idx.insert(0, str(curr.get("index", 0)))
        else:
            mode_var.set("manual")
            val = ""
            if isinstance(curr, str):
                val = curr
            elif isinstance(curr, dict) and curr.get("typ") == "manual":
                val = curr.get("value", "")
            e_manual.insert(0, val)
            
        update_visibility()

        # --- ZATWIERDZANIE ---
        def on_save():
            chosen_align = align_var.get()
            
            if mode_var.get() == "manual":
                # Zapisujemy w formacie JSON (zgodnie z życzeniem)
                self.sz.edytuj_slot(self.indeks, tekst={
                    "typ": "manual",
                    "value": e_manual.get(),
                    "align": chosen_align
                })
            else:
                try:
                    idx = int(e_idx.get())
                except:
                    idx = 0
                self.sz.wstaw_tekst_z_pliku(
                    indeks=self.indeks,
                    plik=e_file.get(),
                    separator=e_sep.get(),
                    index=idx,
                    align=chosen_align
                )
            self.parent.render()
            top.destroy()

        ttk.Button(container, text="Zatwierdź", command=on_save).pack(pady=10)

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
                ("Ilość (0 = random)", "int"),
                ("Min (dla random)", "int"),
                ("Max (dla random)", "int"),
            ]
        )
        def logic(pw, sciezka, ilosc, min_n, max_n):
    
            if ilosc == 0:
                # --- RANDOM ---
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
            else:
                # --- STAŁA ILOŚĆ ---
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
