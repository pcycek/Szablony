import tkinter as tk
from tkinter import ttk
import functools

class GenericDialog(tk.Toplevel):
    def __init__(self, parent, title, fields, callback):
        super().__init__(parent)
        self.callback = callback
        self.title(title)

        self.transient(parent)
        self.grab_set()

        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        self.widgets = [] # (Getter, Type) in order

        for item in fields:
            # Obsługa 2 lub 3 elementów w krotce (Label, Type, [Default])
            label = item[0]
            ftype = item[1]
            default = item[2] if len(item) > 2 else None

            if ftype == "bool":
                v = tk.BooleanVar(value=bool(default) if default is not None else False)
                ttk.Checkbutton(main, text=label, variable=v).pack(anchor="w", pady=4)
                self.widgets.append((v.get, "bool"))
            else:
                ttk.Label(main, text=label).pack(anchor="w", pady=(6, 2))
                v = tk.StringVar(value=str(default) if default is not None else "")
                ttk.Entry(main, textvariable=v).pack(fill="x")
                self.widgets.append((v.get, ftype))

        ttk.Separator(main).pack(fill="x", pady=8)
        ttk.Button(main, text="OK", command=self._ok).pack(fill="x")

        self.update_idletasks()
        self.resizable(False, False)
        # Center dialog
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"+{x}+{y}")

    def _ok(self):
        try:
            vals = []
            for getter, ftype in self.widgets:
                raw = getter()
                if ftype == "int":
                    if isinstance(raw, bool): # Powinno być stringiem, ale dla pewności
                         vals.append(int(raw))
                    else:
                         s = str(raw).strip()
                         if not s:
                             # Domyślne wartości dla pustych pól int
                             # Bezpieczniej dać 0, niż 1. 
                             # Ale logika biznesowa powinna dostarczać defaulty w __init__.
                             vals.append(0)
                         else:
                             vals.append(int(s))
                elif ftype == "bool":
                    vals.append(bool(raw))
                else:
                    vals.append(str(raw).strip())

            self.callback(self.master, *vals)
            self.destroy()
        except ValueError:
            from tkinter import messagebox
            messagebox.showerror("Błąd", "W polach liczbowych muszą znajdować się poprawne dane!")

def with_dialog(title, fields):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Tworzymy okno dopiero w momencie wywołania funkcji!
            dialog = GenericDialog(self, title, fields, func)
        return wrapper
    return decorator

class SaveSlotsDialog(tk.Toplevel):
    def __init__(self, parent, szablony, slots=None, callback=None):
        super().__init__(parent)
        self.sz = szablony
        self.callback = callback
        
        if slots is None:
            self.slots = list(range(len(self.sz.sloty)))
        elif isinstance(slots, (int, float)):
            self.slots = [int(slots)]
        else:
            self.slots = [int(i) for i in slots if 0 <= int(i) < len(self.sz.sloty)]

        self.is_single = (len(self.slots) == 1)
        self.title("Zapisz zawartość slotu jako JPG" if self.is_single else f"Zapisz sloty jako JPG ({len(self.slots)})")

        self.transient(parent)
        self.grab_set()

        main = ttk.Frame(self, padding=15)
        main.pack(fill="both", expand=True)

        # 1. Wybór folderu docelowego
        ttk.Label(main, text="FOLDER DOCELOWY:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 4))
        self.folder_var = tk.StringVar(value="obrazy")
        
        rb_frame = ttk.Frame(main)
        rb_frame.pack(fill="x", pady=(0, 10))
        ttk.Radiobutton(rb_frame, text="📁 data/obrazy (Zmienne)", variable=self.folder_var, value="obrazy").pack(anchor="w", pady=2)
        ttk.Radiobutton(rb_frame, text="📁 data/obrazy_stałe (Stałe)", variable=self.folder_var, value="obrazy_stale").pack(anchor="w", pady=2)

        # 2. Nazewnictwo
        ttk.Separator(main).pack(fill="x", pady=6)
        
        if self.is_single:
            idx = self.slots[0]
            default_name = f"slot_{idx}"
            s_dict = self.sz.sloty[idx] if 0 <= idx < len(self.sz.sloty) else {}
            if s_dict.get("symbol"):
                default_name = str(s_dict["symbol"])
            
            ttk.Label(main, text="NAZWA PLIKU (bez .jpg):", font=("Arial", 9, "bold")).pack(anchor="w", pady=(4, 2))
            self.name_var = tk.StringVar(value=default_name)
            entry = ttk.Entry(main, textvariable=self.name_var)
            entry.pack(fill="x", pady=(0, 6))
            entry.focus_set()
            entry.select_range(0, tk.END)
        else:
            ttk.Label(main, text=f"NAZEWNICTWO ({len(self.slots)} slotów):", font=("Arial", 9, "bold")).pack(anchor="w", pady=(4, 2))
            ttk.Label(main, text="Pliki zostaną zapisane jako: 0.jpg, 1.jpg, 2.jpg... itd.", foreground="#555").pack(anchor="w", pady=(0, 4))
            
            start_frame = ttk.Frame(main)
            start_frame.pack(fill="x", pady=(0, 6))
            ttk.Label(start_frame, text="Numer początkowy:").pack(side="left")
            self.start_idx_var = tk.IntVar(value=0)
            ttk.Spinbox(start_frame, from_=0, to=9999, textvariable=self.start_idx_var, width=6).pack(side="left", padx=5)

        # 3. Opcje
        self.clean_crop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main, text="Czysty wycinek (bez obramowania slotów)", variable=self.clean_crop_var).pack(anchor="w", pady=4)

        # 4. Przyciski
        ttk.Separator(main).pack(fill="x", pady=10)
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="💾 Zapisz JPG", command=self._on_save).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(btn_frame, text="Anuluj", command=self.destroy).pack(side="left", expand=True, fill="x", padx=(4, 0))

        self.update_idletasks()
        self.resizable(False, False)
        # Center dialog
        w = max(360, self.winfo_reqwidth())
        h = self.winfo_reqheight()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _on_save(self):
        folder = self.folder_var.get()
        bez_ramek = self.clean_crop_var.get()
        
        if self.is_single:
            nazwa = self.name_var.get().strip()
            if not nazwa:
                from tkinter import messagebox
                messagebox.showerror("Błąd", "Nazwa pliku nie może być pusta!")
                return
            saved = self.sz.zapisz_zawartosc_slotow(
                slots=self.slots,
                docelowy_folder=folder,
                nazwy=nazwa,
                bez_ramek=bez_ramek
            )
        else:
            start_idx = self.start_idx_var.get()
            saved = self.sz.zapisz_zawartosc_slotow(
                slots=self.slots,
                docelowy_folder=folder,
                start_index=start_idx,
                bez_ramek=bez_ramek
            )

        if saved:
            from tkinter import messagebox
            target_str = "data/obrazy_stałe" if folder in ("obrazy_stale", "obrazy_stałe") else "data/obrazy"
            pliki_str = ", ".join([p.name for p in saved[:5]])
            if len(saved) > 5:
                pliki_str += f" ... (łącznie {len(saved)})"
            messagebox.showinfo(
                "Zapisano pomyślnie",
                f"Zapisano {len(saved)} plik(ów) JPG do folderu:\n{target_str}\n\nPliki:\n{pliki_str}"
            )
            if self.callback:
                self.callback(saved)
            self.destroy()
        else:
            from tkinter import messagebox
            messagebox.showerror("Błąd", "Nie udało się zapisać zawartości slotów.")
