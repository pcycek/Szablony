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
