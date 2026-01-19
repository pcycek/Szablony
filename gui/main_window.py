import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # 1. Inicjalizacja okna
        self.title("Szablony – GUI")
        self.geometry("1000x800") # Zwiększyłem nieco wysokość dla panelu

        # 2. Bezpieczny import silnika
        from Szablony_lib import Szablony
        self.sz = Szablony()
        self.tk_img = None
        self.aktualny_slot = None

        self._build_ui()
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # --- CANVAS ---
        self.canvas = tk.Canvas(self, bg="#2e2e2e", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # --- PANEL BOCZNY ---
        panel = ttk.Frame(self, width=200, padding=10)
        panel.grid(row=0, column=1, sticky="ns")
        panel.pack_propagate(False)

        ttk.Label(panel, text="PROJEKT", font=("Arial", 10, "bold")).pack(pady=5)
        ttk.Button(panel, text="Nowy projekt", command=self.nowy_projekt).pack(fill="x", pady=2)
        ttk.Button(panel, text="Otwórz projekt", command=self.otworz_projekt).pack(fill="x", pady=2)
        ttk.Button(panel, text="Generuj siatkę", command=self.generuj_siatke).pack(fill="x", pady=2)
        ttk.Button(panel, text="Renderuj wszystkie (Batch)", command=self.batch_render).pack(fill="x", pady=2)
        ttk.Button(panel, text="Renderuj do druku (Wybierz)", command=self.renderuj_do_druku_click).pack(fill="x", pady=2)
        ttk.Button(panel, text="Otwórz folder...", command=self.otworz_folder_click).pack(fill="x", pady=2)
        
        ttk.Separator(panel).pack(fill="x", pady=10)
        
        ttk.Label(panel, text="EDYCJA", font=("Arial", 10, "bold")).pack(pady=5)
        self.btn_edit = ttk.Button(panel, text="Edytuj slot", command=self.otworz_edytor, state="disabled")
        self.btn_edit.pack(fill="x", pady=2)
        ttk.Button(panel, text="Usuń slot", command=self.usun_slot).pack(fill="x", pady=2)

        ttk.Separator(panel).pack(fill="x", pady=10)
        
        ttk.Label(panel, text="ŁĄCZENIE (Operatory)", font=("Arial", 10, "bold")).pack(pady=5)
        ttk.Button(panel, text="Dodaj projekt (+)", command=self.polacz_poziomo).pack(fill="x", pady=2)
        ttk.Button(panel, text="Dziel projekt (/)", command=self.polacz_pionowo).pack(fill="x", pady=2)
        
        ttk.Separator(panel).pack(fill='x',pady=10)
        
        ttk.Button(panel, text="undo",
        command=lambda: (self.sz.undo(),                           self.render())).pack(fill="x", pady=2)

        ttk.Button(panel,text="redo",
        command=lambda: (self.sz.redo(),                           self.render())).pack(fill="x", pady=2)

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
                self.render()
            else:
                messagebox.showerror("Błąd", "Nie można otworzyć projektu")

        ProjectPicker(self, open_selected)
#    def otworz_projekt(self):
#        from gui.dialogs import with_dialog
#        @with_dialog(title="Otwórz", fields=[("Nazwa pliku .json", "str")])
#        def logic(s, nazwa):
#            if s.sz.otworz_projekt(nazwa):
#                s.render()
#            else:
#                messagebox.showerror("Błąd", "Nie znaleziono pliku projektu!")
#        logic(self)

    def usun_slot(self):
        if self.aktualny_slot is not None:
            self.sz.usun_slot(self.aktualny_slot)
            self.aktualny_slot = None
            self.btn_edit.config(state="disabled")
            self.render()

    def polacz_poziomo(self):
       
    
         from gui.project_picker import ProjectPicker

         def open_selected(nazwa2):
             from Szablony_lib import Szablony
             drugi = Szablony()
             if drugi.otworz_projekt(nazwa2):
            # Łączymy z aktualnym projektem poziomo
                 self.sz.zapisz_undo()
                 self.sz = self.sz + drugi
                 self.render()

         ProjectPicker(self, open_selected)

    def polacz_pionowo(self):

        from gui.project_picker import ProjectPicker

        def open_selected(nazwa2):
            from Szablony_lib import Szablony
            drugi = Szablony()
            if drugi.otworz_projekt(nazwa2):
            # Łączymy z aktualnym projektem pionowo
                self.sz.zapisz_undo()
                self.sz = self.sz / drugi
                self.render()

        ProjectPicker(self, open_selected)

    # --- METODA ZAPISU ---
    
    def _save_project(self):
        """Wywołuje zapis z silnika Szablony_lib i informuje użytkownika."""
        from tkinter import simpledialog
        
        # Opcja zmiany nazwy
        nowa_nazwa = simpledialog.askstring(
            "Zapisz projekt", 
            "Podaj nazwę projektu:", 
            initialvalue=self.sz.nazwa_projektu
        )
        
        if nowa_nazwa is None:
            return  # Anulowano
            
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
            s.render()
        logic(self)

    def generuj_siatke(self):
        from gui.dialogs import with_dialog
        
        @with_dialog(title="Siatka", fields=[("Kolumny", "int"), ("Wiersze", "int"), ("Margines (np. 5,5)", "str")])
        def logic(s, k, w, m_str):
            # Domyślny margines
            mx, my = 5, 5
            
            # Parsowanie wejścia
            if m_str:
                try:
                    parts = m_str.replace(" ", "").split(",")
                    if len(parts) >= 1:
                        mx = int(parts[0])
                    if len(parts) >= 2:
                        my = int(parts[1])
                    else:
                        my = mx # Jeśli podano jedną liczbę, użyj jej dla obu
                except:
                    pass # Zostaje 5,5 w razie błędu
            
            s.sz.generuj_siatke(k, w, margines=(mx, my))
            s.render()
        logic(self)

    def batch_render(self):
        answer = messagebox.askyesno("Renderowanie wsadowe", "Czy na pewno chcesz przenderować WSZYSTKIE projekty?\nTo może chwilę potrwać.")
        if not answer:
            return

        self.config(cursor="wait")
        self.update()
        
        # Zapytanie o skalowanie do druku
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

    # --- OBSŁUGA SLOTÓW ---


    def _on_canvas_click(self, event):
        x, y = event.x, event.y
        self.aktualny_slot = None
        
        for i, slot in enumerate(self.sz.sloty):
            c = slot["coords"]
            if c[0] <= x <= c[2] and c[1] <= y <= c[3]:
                self.aktualny_slot = i
                break
        
        if self.aktualny_slot is not None:
            self.btn_edit.config(state="normal")
            self._highlight_slot(self.aktualny_slot)
        else:
            self.btn_edit.config(state="disabled")
            self.render()

    def _highlight_slot(self, idx):
        self.render()
        c = self.sz.sloty[idx]["coords"]
        self.canvas.create_rectangle(c[0], c[1], c[2], c[3], outline="red", width=3)

    def otworz_edytor(self):
        if self.aktualny_slot is not None:
            from gui.slot_editor import SlotEditorWindow
            # Zapamiętujemy bazę przed edycją, aby Scale działało poprawnie
            self.sz.zapamietaj_baze_slotu(self.aktualny_slot)
            SlotEditorWindow(self, self.sz, self.aktualny_slot)

    def render(self):
        from PIL import ImageTk
        self.sz.render_all()
        if self.sz.img:
            self.tk_img = ImageTk.PhotoImage(self.sz.img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
