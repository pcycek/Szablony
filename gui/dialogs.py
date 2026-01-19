import tkinter as tk
from tkinter import ttk
import functools

def with_dialog(title, fields):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Tworzymy okno dopiero w momencie wywołania funkcji!
            dialog = GenericDialog(self, title, fields, func)
        return wrapper
    return decorator
class GenericDialog(tk.Toplevel):
    def __init__(self, parent, title, fields, callback):
        super().__init__(parent)
        self.callback = callback
        self.title(title)

        self.transient(parent)
        self.grab_set()

        # 🔹 GŁÓWNA RAMKA (KLUCZ!)
        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        self.vars = []
        self.check_vars = {}

        # --- POLA ---
        for field in fields:
            if field[1] == "bool":
                v = tk.BooleanVar()
                ttk.Checkbutton(
                    main, text=field[0], variable=v
                ).pack(anchor="w", pady=4)
                self.check_vars[field[0]] = v
            else:
                label, ftype = field
                ttk.Label(main, text=label).pack(anchor="w", pady=(6, 2))
                v = tk.StringVar()
                ttk.Entry(main, textvariable=v).pack(fill="x")
                self.vars.append((v, ftype, label))

        # --- PRZYCISK OK ---
        ttk.Separator(main).pack(fill="x", pady=8)
        ttk.Button(main, text="OK", command=self._ok).pack(fill="x")

        # --- AUTOSIZE ---
        self.update_idletasks()
        self.resizable(False, False)
        self.geometry("")
    def _ok(self):
        try:
            vals = []
            for v, t, label in self.vars:
                val = v.get().strip()
                if t == "int":
                    vals.append(int(val) if val else 1)
                else:
                    vals.append(val)

            for k in self.check_vars.values():
                vals.insert(0, k.get())

            self.callback(self.master, *vals)
            self.destroy()
        except ValueError:
            from tkinter import messagebox
            messagebox.showerror("Błąd", "W polach liczbowych muszą znajdować się cyfry!")
