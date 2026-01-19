import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


from paths import PROJEKTY_DIR

class ProjectPicker(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("Wybierz projekt")
        self.geometry("300x400")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text="Dostępne projekty:").pack(pady=5)

        self.listbox = tk.Listbox(self)
        self.listbox.pack(expand=True, fill="both", padx=10)

        for p in PROJEKTY_DIR.glob("*.json"):
            self.listbox.insert("end", p.name)

        ttk.Button(self, text="OK", command=self._ok).pack(pady=5)

    def _ok(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("Uwaga", "Wybierz projekt")
            return

        nazwa = self.listbox.get(sel[0])
        self.callback(nazwa)
        self.destroy()