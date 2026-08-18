import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

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

        # System zaznaczania
        self.selected_slots = set()
        self.selected_slots_ordered = []
        self._drag_start = None
        self._is_dragging = False

        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # --- CANVAS ---
        self.canvas = tk.Canvas(self, bg="#2e2e2e", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # --- PANEL BOCZNY ---
        panel = ttk.Frame(self, width=200, padding=10)
        panel.grid(row=0, column=1, sticky="ns")
        panel.pack_propagate(False)

        ttk.Label(panel, text="PROJEKT", font=("Arial", 10, "bold")).pack(pady=5)
        ttk.Button(panel, text="Nowy projekt", command=self.nowy_projekt).pack(fill="x", pady=2)
        ttk.Button(panel, text="Otwórz projekt", command=self.otworz_projekt).pack(fill="x", pady=2)
        ttk.Button(panel, text="Generuj siatkę", command=self.generuj_siatke).pack(fill="x", pady=2)
        
        ttk.Separator(panel).pack(fill="x", pady=5)
        ttk.Button(panel, text="Przylosuj (Re-roll)", command=self.przelicz_ponownie).pack(fill="x", pady=2)
        ttk.Button(panel, text="Renderuj wszystkie (Batch)", command=self.batch_render).pack(fill="x", pady=2)
        ttk.Button(panel, text="Renderuj do druku (Wybierz)", command=self.renderuj_do_druku_click).pack(fill="x", pady=2)
        ttk.Button(panel, text="Otwórz folder...", command=self.otworz_folder_click).pack(fill="x", pady=2)
        ttk.Button(panel, text="Uruchom skrypt", command=self.uruchom_skrypt_click).pack(fill="x", pady=2)
        
        ttk.Separator(panel).pack(fill="x", pady=10)
        
        ttk.Label(panel, text="EDYCJA", font=("Arial", 10, "bold")).pack(pady=5)
        self.btn_edit = ttk.Button(panel, text="Edytuj slot", command=self.otworz_edytor, state="disabled")
        self.btn_edit.pack(fill="x", pady=2)
        self.btn_edit_selected = ttk.Button(panel, text="Edytuj zaznaczone", command=self.otworz_edytor_zaznaczonych, state="disabled")
        self.btn_edit_selected.pack(fill="x", pady=2)
        self.btn_edit_all = ttk.Button(panel, text="Edytuj wszystkie sloty", command=self.otworz_edytor_wszystkich, state="disabled")
        self.btn_edit_all.pack(fill="x", pady=2)
        ttk.Button(panel, text="Usuń slot", command=self.usun_slot).pack(fill="x", pady=2)

        ttk.Separator(panel).pack(fill="x", pady=10)
        
        ttk.Label(panel, text="ŁĄCZENIE (Operatory)", font=("Arial", 10, "bold")).pack(pady=5)
        ttk.Button(panel, text="Dodaj projekt (+)", command=self.polacz_poziomo).pack(fill="x", pady=2)
        ttk.Button(panel, text="Dziel projekt (/)", command=self.polacz_pionowo).pack(fill="x", pady=2)
        
        ttk.Separator(panel).pack(fill='x', pady=10)
        
        ttk.Button(panel, text="undo",
                   command=lambda: (self.sz.undo(), self.render())).pack(fill="x", pady=2)

        ttk.Button(panel, text="redo",
                   command=lambda: (self.sz.redo(), self.render())).pack(fill="x", pady=2)

        # --- DOLNY PANEL ---
        bottom_bar = ttk.Frame(self, padding=10)
        bottom_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

        ttk.Button(bottom_bar, text="ZAPISZ (JPG+JSON)", command=self._save_project).pack(side="left", expand=True, fill="x", padx=5)
        ttk.Button(bottom_bar, text="❌ ZAMKNIJ", command=self.quit).pack(side="left", expand=True, fill="x", padx=5)

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

    def otworz_folder_click(self):
        """Pokazuje okno z listą folderów do otwarcia."""
        from paths import PROJEKTY_DIR, OBRAZY_DIR, WYNIKI_DIR, TEKSTY_DIR, DO_DRUKU_DIR
        import os
        import subprocess
        import sys
        
        folders = [
            ("Projekty", PROJEKTY_DIR),
            ("Obrazy", OBRAZY_DIR),
            ("Wyniki", WYNIKI_DIR),
            ("Teksty", TEKSTY_DIR),
            ("Do Druku", DO_DRUKU_DIR)
        ]
        
        top = tk.Toplevel(self)
        top.title("Otwórz folder")
        top.geometry("300x300")
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
            btn.pack(fill="x", padx=20, pady=5)
            
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

    def _on_canvas_press(self, event):
        self._drag_start = (event.x, event.y)
        self._is_dragging = False

    def _on_canvas_drag(self, event):
        if not self._drag_start:
            return
        x0, y0 = self._drag_start
        x1, y1 = event.x, event.y
        if abs(x1 - x0) > 4 or abs(y1 - y0) > 4:
            self._is_dragging = True
            self.canvas.delete("selection_rect")
            self.canvas.create_rectangle(
                x0, y0, x1, y1,
                outline="#00aaff",
                width=1,
                dash=(4, 4),
                tags="selection_rect"
            )

    def _on_canvas_release(self, event):
        self.canvas.delete("selection_rect")
        ctrl_pressed = bool(event.state & 0x0004)

        if self._is_dragging and self._drag_start:
            x0, y0 = self._drag_start
            x1, y1 = event.x, event.y
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
            # Pojedyncze kliknięcie LPM
            x, y = event.x, event.y
            clicked_idx = None
            for i, slot in enumerate(self.sz.sloty):
                c = slot["coords"]
                if c[0] <= x <= c[2] and c[1] <= y <= c[3]:
                    clicked_idx = i
                    break

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
        self._is_dragging = False
        self._update_ui_state()
        self._draw_selection_highlights()

    def _draw_selection_highlights(self):
        self.canvas.delete("selection_outline")
        valid_slots = set(range(len(self.sz.sloty)))
        self.selected_slots = self.selected_slots.intersection(valid_slots)
        self.selected_slots_ordered = [i for i in self.selected_slots_ordered if i in valid_slots]

        for idx in self.selected_slots:
            c = self.sz.sloty[idx]["coords"]
            self.canvas.create_rectangle(
                c[0], c[1], c[2], c[3],
                outline="#0078d7",
                width=3,
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
        from PIL import ImageTk
        self._update_ui_state()
        self.sz.render_all()
        if self.sz.img:
            self.tk_img = ImageTk.PhotoImage(self.sz.img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self._draw_selection_highlights()
