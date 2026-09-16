import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, List, Union
from PIL import Image, ImageTk

from pdf_manager import PDFManager
from paths import WYNIKI_DIR, OBRAZY_DIR, DO_DRUKU_DIR


class PDFEditorDialog(tk.Toplevel):
    """
    Zaawansowane okno dialogowe do generowania, edycji, manewrowania stronami
    i zapisu dokumentów PDF.
    """

    def __init__(self, parent, initial_pdf: Optional[Union[str, Path]] = None, initial_images: Optional[List[Union[str, Path]]] = None):
        super().__init__(parent)
        self.title("📑 Generator i Edytor PDF")

        # Upewniamy się, że folder do druku istnieje
        DO_DRUKU_DIR.mkdir(parents=True, exist_ok=True)
        self._last_dir = DO_DRUKU_DIR

        # Dynamiczne wymiary okna dopasowane do rozdzielczości ekranu (zapobiega chowaniu dolnego paska)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        target_w = min(1140, int(screen_w * 0.88))
        target_h = min(680, int(screen_h * 0.80))
        x = max(0, (screen_w - target_w) // 2)
        y = max(0, (screen_h - target_h) // 2 - 25)
        self.geometry(f"{target_w}x{target_h}+{x}+{y}")
        self.minsize(750, 480)
        self.transient(parent)

        self.manager = PDFManager()
        self.current_page_idx = 0
        self._thumb_images_cache = {}
        self._big_preview_img = None

        self._build_ui()

        if initial_pdf and Path(initial_pdf).exists():
            try:
                self.manager.load_pdf(initial_pdf)
                self.manager.auto_orient_pages()
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się wczytać pliku PDF: {e}")
        elif initial_images:
            try:
                self.manager.add_images(initial_images, page_size="A4", orientation="auto")
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się dodać obrazów: {e}")

        self.refresh_pages_view()

    def _get_initial_dir(self) -> Path:
        """Zwraca domyślny folder do wyszukiwania plików (priorytet: 'do druku')."""
        DO_DRUKU_DIR.mkdir(parents=True, exist_ok=True)
        if hasattr(self, "_last_dir") and self._last_dir and Path(self._last_dir).exists():
            return Path(self._last_dir)
        return DO_DRUKU_DIR

    def _build_ui(self):
        # 1. Górny pasek narzędziowy (Toolbar)
        toolbar = ttk.Frame(self, padding=(10, 6))
        toolbar.pack(side="top", fill="x")

        ttk.Button(toolbar, text="🖼️ Nowy z obrazów...", command=self._action_new_from_images).pack(side="left", padx=3)
        ttk.Button(toolbar, text="📂 Otwórz PDF...", command=self._action_open_pdf).pack(side="left", padx=3)
        ttk.Button(toolbar, text="➕ Dodaj obrazy...", command=self._action_add_images).pack(side="left", padx=3)
        ttk.Button(toolbar, text="📑 Dołącz inny PDF...", command=self._action_merge_pdf).pack(side="left", padx=3)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(toolbar, text="📐 Auto-orientacja", command=self._action_auto_orient).pack(side="left", padx=3)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(toolbar, text="💾 Zapisz PDF jako...", command=self._action_save_pdf).pack(side="left", padx=3)

        self.lbl_status = ttk.Label(toolbar, text="Dokument: pusty", font=("Arial", 9, "italic"))
        self.lbl_status.pack(side="right", padx=10)

        # 2. Główny podział na 2 kolumny (PanedWindow)
        main_paned = ttk.PanedWindow(self, orient="horizontal")
        main_paned.pack(fill="both", expand=True, padx=8, pady=4)

        # Lewa kolumna: Lista / kafelki miniatur stron + panel akcji
        left_frame = ttk.Frame(main_paned, width=640)
        main_paned.add(left_frame, weight=3)

        # Nagłówek lewej kolumny (na górze lewej ramki)
        header_left = ttk.Frame(left_frame)
        header_left.pack(side="top", fill="x", padx=4, pady=2)
        self.lbl_pages_count = ttk.Label(header_left, text="Strony dokumentu (0 stron)", font=("Arial", 10, "bold"))
        self.lbl_pages_count.pack(side="left")

        # DOLNY PANEL AKCJI - pakowany z side="bottom" ZANIM dodamy thumbs_container z expand=True!
        # Dzięki temu dolne menu jest ZAWSZE w 100% widoczne bez względu na wysokość okna!
        action_box = ttk.LabelFrame(left_frame, text="Manewrowanie stronami", padding=(8, 4))
        action_box.pack(side="bottom", fill="x", padx=4, pady=4)

        # Rząd 1: Przenoszenie na konkretną stronę i orientacja
        row1 = ttk.Frame(action_box)
        row1.pack(fill="x", pady=2)

        ttk.Label(row1, text="Wybrana strona:", font=("Arial", 9, "bold")).pack(side="left", padx=2)
        self.lbl_selected_page = ttk.Label(row1, text="Brak", font=("Arial", 9, "bold"), foreground="#0078d7")
        self.lbl_selected_page.pack(side="left", padx=4)

        self.lbl_selected_orient = ttk.Label(row1, text="", font=("Arial", 9, "italic"), foreground="#444444")
        self.lbl_selected_orient.pack(side="left", padx=6)

        ttk.Label(row1, text="➡️ Przenieś na pozycję:").pack(side="left", padx=(10, 4))
        self.spin_target_page = ttk.Spinbox(row1, from_=1, to=9999, width=5)
        self.spin_target_page.pack(side="left", padx=2)
        ttk.Button(row1, text="Zastosuj", command=self._action_move_page_to).pack(side="left", padx=4)

        # Rząd 2: Szybkie przyciski nawigacji, obrotu i edycji
        row2 = ttk.Frame(action_box)
        row2.pack(fill="x", pady=3)

        ttk.Button(row2, text="▲ W górę", command=self._action_move_up).pack(side="left", padx=2)
        ttk.Button(row2, text="▼ W dół", command=self._action_move_down).pack(side="left", padx=2)
        ttk.Separator(row2, orient="vertical").pack(side="left", fill="y", padx=4)

        ttk.Button(row2, text="🔄 Pion / Poziom", command=self._action_toggle_orientation).pack(side="left", padx=2)
        ttk.Button(row2, text="⤾ -90°", command=lambda: self._action_rotate(-90)).pack(side="left", padx=2)
        ttk.Button(row2, text="⤿ +90°", command=lambda: self._action_rotate(90)).pack(side="left", padx=2)
        ttk.Separator(row2, orient="vertical").pack(side="left", fill="y", padx=4)

        ttk.Button(row2, text="📐 Auto-orientuj", command=self._action_auto_orient).pack(side="left", padx=2)
        ttk.Separator(row2, orient="vertical").pack(side="left", fill="y", padx=4)

        ttk.Button(row2, text="📄 Duplikuj", command=self._action_duplicate).pack(side="left", padx=2)
        ttk.Button(row2, text="🗑️ Usuń", command=self._action_delete).pack(side="left", padx=2)

        # KONTENER MINIATUR - wypełnia pozostałą przestrzeń w pionie
        thumbs_container = ttk.Frame(left_frame)
        thumbs_container.pack(side="top", fill="both", expand=True, padx=2, pady=2)
        thumbs_container.rowconfigure(0, weight=1)
        thumbs_container.columnconfigure(0, weight=1)

        self.canvas_thumbs = tk.Canvas(thumbs_container, bg="#f5f5f5", highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(thumbs_container, orient="vertical", command=self.canvas_thumbs.yview)
        self.canvas_thumbs.configure(yscrollcommand=self.v_scroll.set)

        self.canvas_thumbs.grid(row=0, column=0, sticky="nsew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")

        self.frame_thumbs_inner = ttk.Frame(self.canvas_thumbs)
        self.canvas_window = self.canvas_thumbs.create_window((0, 0), window=self.frame_thumbs_inner, anchor="nw")

        self.frame_thumbs_inner.bind("<Configure>", lambda e: self.canvas_thumbs.configure(scrollregion=self.canvas_thumbs.bbox("all")))
        self.canvas_thumbs.bind("<Configure>", lambda e: self.canvas_thumbs.itemconfig(self.canvas_window, width=e.width))

        # OBSŁUGA KÓŁKA MYSZY DLA MINIATUR
        self.canvas_thumbs.bind("<MouseWheel>", self._on_thumbs_mousewheel)
        self.canvas_thumbs.bind("<Button-4>", self._on_thumbs_mousewheel)
        self.canvas_thumbs.bind("<Button-5>", self._on_thumbs_mousewheel)
        self.frame_thumbs_inner.bind("<MouseWheel>", self._on_thumbs_mousewheel)
        self.frame_thumbs_inner.bind("<Button-4>", self._on_thumbs_mousewheel)
        self.frame_thumbs_inner.bind("<Button-5>", self._on_thumbs_mousewheel)

        # Globalne wiązanie kółka myszy po najechaniu na obszar lewego panelu miniatur
        thumbs_container.bind("<Enter>", lambda e: self._bind_global_thumbs_wheel(True))
        thumbs_container.bind("<Leave>", lambda e: self._bind_global_thumbs_wheel(False))

        # Prawa kolumna: Duży podgląd wybranej strony
        right_frame = ttk.Frame(main_paned, width=420)
        main_paned.add(right_frame, weight=2)

        header_right = ttk.Frame(right_frame)
        header_right.pack(fill="x", padx=4, pady=2)
        ttk.Label(header_right, text="Podgląd wybranej strony", font=("Arial", 10, "bold")).pack(side="left")

        self.lbl_page_details = ttk.Label(right_frame, text="", font=("Arial", 9))
        self.lbl_page_details.pack(fill="x", padx=4, pady=2)

        self.canvas_preview = tk.Canvas(right_frame, bg="#333333", highlightthickness=0)
        self.canvas_preview.pack(fill="both", expand=True, padx=4, pady=4)

        # Kółko myszy na prawym podglądzie przełącza strony (poprzednia / następna)
        self.canvas_preview.bind("<MouseWheel>", self._on_preview_mousewheel)
        self.canvas_preview.bind("<Button-4>", self._on_preview_mousewheel)
        self.canvas_preview.bind("<Button-5>", self._on_preview_mousewheel)

    # --- OBSŁUGA KÓŁKA MYSZY ---

    def _on_thumbs_mousewheel(self, e):
        """Obsługuje płynne przewijanie listy miniatur kółkiem myszy."""
        if hasattr(e, "delta") and e.delta:
            delta = int(-1 * (e.delta / 120))
            self.canvas_thumbs.yview_scroll(delta, "units")
        elif getattr(e, "num", None) == 4:
            self.canvas_thumbs.yview_scroll(-1, "units")
        elif getattr(e, "num", None) == 5:
            self.canvas_thumbs.yview_scroll(1, "units")

    def _bind_global_thumbs_wheel(self, active: bool):
        """Włącza lub wyłącza nasłuchiwanie kółka myszy w obszarze miniatur."""
        if active:
            self.bind_all("<MouseWheel>", self._on_thumbs_mousewheel)
            self.bind_all("<Button-4>", self._on_thumbs_mousewheel)
            self.bind_all("<Button-5>", self._on_thumbs_mousewheel)
        else:
            self.unbind_all("<MouseWheel>")
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")

    def _bind_mousewheel_recursive(self, widget):
        """Rekurencyjnie przypisuje obsługę kółka myszy do widżetu i wszystkich jego dzieci."""
        widget.bind("<MouseWheel>", self._on_thumbs_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_thumbs_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_thumbs_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child)

    def _on_preview_mousewheel(self, e):
        """Przewijanie kółkiem myszy na dużym podglądzie przełącza poprzednią/następną stronę."""
        if hasattr(e, "delta") and e.delta:
            if e.delta > 0:
                self._action_prev_page()
            else:
                self._action_next_page()
        elif getattr(e, "num", None) == 4:
            self._action_prev_page()
        elif getattr(e, "num", None) == 5:
            self._action_next_page()

    def _action_prev_page(self):
        """Przechodzi do poprzedniej strony dokumentu."""
        if self.current_page_idx > 0:
            self._select_page(self.current_page_idx - 1)

    def _action_next_page(self):
        """Przechodzi do następnej strony dokumentu."""
        if self.current_page_idx < self.manager.get_page_count() - 1:
            self._select_page(self.current_page_idx + 1)

    # --- ODŚWIEŻANIE WIDOKU STRON ---

    def refresh_pages_view(self):
        """Przebudowuje listę miniatur i aktualizuje podgląd wybranej strony."""
        for widget in self.frame_thumbs_inner.winfo_children():
            widget.destroy()
        self._thumb_images_cache.clear()

        total = self.manager.get_page_count()
        self.lbl_pages_count.config(text=f"Strony dokumentu ({total} stron)")

        src = self.manager.source_path.name if self.manager.source_path else "Nowy dokument"
        self.lbl_status.config(text=f"Plik: {src} ({total} stron)")

        if total == 0:
            self.current_page_idx = -1
            self.lbl_selected_page.config(text="Brak")
            self.lbl_selected_orient.config(text="")
            self.lbl_page_details.config(text="Brak stron w dokumencie. Użyj 'Nowy z obrazów...' lub 'Otwórz PDF...'.")
            self.canvas_preview.delete("all")
            return

        if self.current_page_idx < 0 or self.current_page_idx >= total:
            self.current_page_idx = 0

        self.spin_target_page.config(to=total)
        self.spin_target_page.set(self.current_page_idx + 1)
        self.lbl_selected_page.config(text=f"Strona {self.current_page_idx + 1}")

        pages_info = self.manager.get_pages_info()
        if 0 <= self.current_page_idx < len(pages_info):
            cur_land = pages_info[self.current_page_idx].get("is_landscape", False)
            self.lbl_selected_orient.config(text=f"({ 'Pozioma ↔' if cur_land else 'Pionowa ↕' })")

        # Układ kafelków miniatur w siatce (kolumny w zależności od szerokości)
        cols = 3
        for i in range(total):
            card = self._create_page_card(self.frame_thumbs_inner, i, pages_info)
            row = i // cols
            col = i % cols
            card.grid(row=row, column=col, padx=6, pady=6, sticky="n")

        self._update_big_preview()

    def _create_page_card(self, parent, page_idx: int, pages_info: Optional[List] = None) -> tk.Frame:
        """Tworzy pojedynczy kafelek z miniaturą strony, informacją o orientacji i wiąże scrolla."""
        is_selected = (page_idx == self.current_page_idx)
        card_bg = "#e1effe" if is_selected else "#ffffff"
        border_color = "#0078d7" if is_selected else "#cccccc"

        card = tk.Frame(parent, bg=card_bg, highlightbackground=border_color, highlightthickness=2, padx=4, pady=4, cursor="hand2")

        # Orientacja strony
        is_landscape = False
        if pages_info and page_idx < len(pages_info):
            is_landscape = pages_info[page_idx].get("is_landscape", False)
        orient_badge = "↔ Pozioma" if is_landscape else "↕ Pionowa"
        orient_color = "#005a9e" if is_landscape else "#107c10"

        # Render miniatury
        thumb_img = self.manager.get_page_thumbnail(page_idx, max_size=(130, 175))
        if thumb_img:
            tk_thumb = ImageTk.PhotoImage(thumb_img)
            self._thumb_images_cache[page_idx] = tk_thumb
            lbl_img = tk.Label(card, image=tk_thumb, bg=card_bg)
            lbl_img.pack()
            lbl_img.bind("<Button-1>", lambda e, idx=page_idx: self._select_page(idx))
        else:
            lbl_placeholder = tk.Label(card, text="[Błąd miniatury]", width=16, height=8, bg="#eeeeee")
            lbl_placeholder.pack()
            lbl_placeholder.bind("<Button-1>", lambda e, idx=page_idx: self._select_page(idx))

        # Etykieta numeru strony
        lbl_num = tk.Label(card, text=f"Strona {page_idx + 1}", font=("Arial", 9, "bold"), bg=card_bg)
        lbl_num.pack(pady=(2, 0))
        lbl_num.bind("<Button-1>", lambda e, idx=page_idx: self._select_page(idx))

        # Etykieta orientacji strony
        lbl_orient = tk.Label(card, text=orient_badge, font=("Arial", 8, "bold"), fg=orient_color, bg=card_bg)
        lbl_orient.pack(pady=(0, 2))
        lbl_orient.bind("<Button-1>", lambda e, idx=page_idx: self._select_page(idx))

        card.bind("<Button-1>", lambda e, idx=page_idx: self._select_page(idx))

        # Przypisanie obsługi kółka myszy do wszystkich elementów kafelka
        self._bind_mousewheel_recursive(card)
        return card

    def _select_page(self, idx: int):
        """Zaznacza stronę o podanym indeksie i odświeża widok."""
        if 0 <= idx < self.manager.get_page_count():
            self.current_page_idx = idx
            self.spin_target_page.set(idx + 1)
            self.lbl_selected_page.config(text=f"Strona {idx + 1}")
            self.refresh_pages_view()

    def _update_big_preview(self):
        """Aktualizuje duży podgląd wybranej strony w prawym panelu."""
        self.canvas_preview.delete("all")
        if not (0 <= self.current_page_idx < self.manager.get_page_count()):
            self.lbl_page_details.config(text="")
            return

        pages_info = self.manager.get_pages_info()
        p_info = pages_info[self.current_page_idx]
        pw, ph = p_info["width"], p_info["height"]
        rot = p_info["rotation"]
        orient = "Pozioma (Landscape)" if p_info["is_landscape"] else "Pionowa (Portrait)"
        self.lbl_page_details.config(
            text=f"Strona {self.current_page_idx + 1} / {len(pages_info)} | Rozmiar: {pw} x {ph} pt | Obrót: {rot}° | Orientacja: {orient}"
        )

        cw = max(50, self.canvas_preview.winfo_width())
        ch = max(50, self.canvas_preview.winfo_height())
        if cw <= 50 or ch <= 50:
            cw, ch = 380, 520

        preview_img = self.manager.get_page_preview(self.current_page_idx, dpi=120)
        if preview_img:
            scale = min((cw - 20) / preview_img.width, (ch - 20) / preview_img.height)
            scale = max(0.05, min(2.0, scale))
            disp_w = max(10, int(preview_img.width * scale))
            disp_h = max(10, int(preview_img.height * scale))

            disp_img = preview_img.resize((disp_w, disp_h), Image.Resampling.BILINEAR)
            self._big_preview_img = ImageTk.PhotoImage(disp_img)
            self.canvas_preview.create_image(cw // 2, ch // 2, anchor="center", image=self._big_preview_img)

    # --- AKCJE MANEWROWANIA STRONAMI ---

    def _action_move_page_to(self):
        """Przenosi aktualnie zaznaczoną stronę na wpisaną pozycję (np. z 1 na 5)."""
        if self.current_page_idx < 0 or self.manager.get_page_count() <= 1:
            return

        try:
            target_1based = int(self.spin_target_page.get())
            total = self.manager.get_page_count()
            if not (1 <= target_1based <= total):
                raise ValueError()
        except ValueError:
            messagebox.showerror("Błąd", f"Wpisz poprawny numer strony od 1 do {self.manager.get_page_count()}.")
            return

        from_1based = self.current_page_idx + 1
        self.manager.move_page(from_1based, target_1based, one_based=True)
        self.current_page_idx = target_1based - 1
        self.refresh_pages_view()

    def _action_move_up(self):
        """Przesuwa aktualną stronę w górę o 1 pozycję."""
        if self.current_page_idx > 0:
            self.manager.move_page_up(self.current_page_idx, one_based=False)
            self.current_page_idx -= 1
            self.refresh_pages_view()

    def _action_move_down(self):
        """Przesuwa aktualną stronę w dół o 1 pozycję."""
        if 0 <= self.current_page_idx < self.manager.get_page_count() - 1:
            self.manager.move_page_down(self.current_page_idx, one_based=False)
            self.current_page_idx += 1
            self.refresh_pages_view()

    def _action_toggle_orientation(self):
        """Przełącza orientację aktualnie wybranej strony (pion <-> poziom)."""
        if 0 <= self.current_page_idx < self.manager.get_page_count():
            self.manager.toggle_page_orientation(self.current_page_idx, one_based=False)
            self.refresh_pages_view()

    def _action_auto_orient(self):
        """Automatycznie dopasowuje orientację wszystkich stron do osadzonych obrazów."""
        total = self.manager.get_page_count()
        if total == 0:
            return
        changed = self.manager.auto_orient_pages()
        self.refresh_pages_view()
        if changed > 0:
            messagebox.showinfo("Auto-orientacja", f"Dopasowano orientację dla {changed} stron(y).")
        else:
            messagebox.showinfo("Auto-orientacja", "Wszystkie strony mają już prawidłową orientację dopasowaną do obrazów.")

    def _action_rotate(self, angle: int):
        """Obraca wybraną stronę o zadany kąt."""
        if 0 <= self.current_page_idx < self.manager.get_page_count():
            self.manager.rotate_page(self.current_page_idx, angle=angle, one_based=False)
            self.refresh_pages_view()

    def _action_duplicate(self):
        """Duplikuje wybraną stronę."""
        if 0 <= self.current_page_idx < self.manager.get_page_count():
            new_idx = self.manager.duplicate_page(self.current_page_idx, one_based=False)
            if new_idx >= 0:
                self.current_page_idx = new_idx
                self.refresh_pages_view()

    def _action_delete(self):
        """Usuwa wybraną stronę po potwierdzeniu."""
        if not (0 <= self.current_page_idx < self.manager.get_page_count()):
            return

        page_no = self.current_page_idx + 1
        ans = messagebox.askyesno("Potwierdzenie usunięcia", f"Czy na pewno chcesz usunąć stronę {page_no}?")
        if ans:
            self.manager.delete_page(self.current_page_idx, one_based=False)
            if self.current_page_idx >= self.manager.get_page_count():
                self.current_page_idx = max(0, self.manager.get_page_count() - 1)
            self.refresh_pages_view()

    # --- AKCJE GŁÓWNE TOOLBARA ---

    def _action_new_from_images(self):
        """Tworzy nowy dokument PDF z wybranych obrazów (automatyczna orientacja wg wymiarów obrazów)."""
        init_dir = self._get_initial_dir()
        files = filedialog.askopenfilenames(
            title="Wybierz obrazy do utworzenia PDF (domyślnie: do druku)",
            initialdir=init_dir,
            filetypes=[("Pliki graficzne", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Wszystkie pliki", "*.*")]
        )
        if files:
            self._last_dir = Path(files[0]).parent
            self.manager.close()
            self.manager = PDFManager()
            self.manager.add_images(list(files), page_size="A4", orientation="auto")
            self.current_page_idx = 0
            self.refresh_pages_view()

    def _action_open_pdf(self):
        """Otwiera istniejący plik PDF do edycji."""
        init_dir = self._get_initial_dir()
        filename = filedialog.askopenfilename(
            title="Wybierz plik PDF do edycji (domyślnie: do druku)",
            initialdir=init_dir,
            filetypes=[("Dokumenty PDF", "*.pdf"), ("Wszystkie pliki", "*.*")]
        )
        if filename:
            try:
                self._last_dir = Path(filename).parent
                self.manager.load_pdf(filename)
                # Automatycznie dopasowujemy orientację stron do wymiarów obrazków w pliku
                self.manager.auto_orient_pages()
                self.current_page_idx = 0
                self.refresh_pages_view()
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się otworzyć pliku PDF:\n{e}")

    def _action_add_images(self):
        """Dołącza kolejne obrazy jako strony do bieżącego dokumentu."""
        init_dir = self._get_initial_dir()
        files = filedialog.askopenfilenames(
            title="Wybierz obrazy do dołączenia (domyślnie: do druku)",
            initialdir=init_dir,
            filetypes=[("Pliki graficzne", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Wszystkie pliki", "*.*")]
        )
        if files:
            self._last_dir = Path(files[0]).parent
            self.manager.add_images(list(files), page_size="A4", orientation="auto")
            self.refresh_pages_view()

    def _action_merge_pdf(self):
        """Dołącza inny plik PDF do bieżącego dokumentu."""
        init_dir = self._get_initial_dir()
        filename = filedialog.askopenfilename(
            title="Wybierz plik PDF do scalenia (domyślnie: do druku)",
            initialdir=init_dir,
            filetypes=[("Dokumenty PDF", "*.pdf"), ("Wszystkie pliki", "*.*")]
        )
        if filename:
            try:
                self._last_dir = Path(filename).parent
                self.manager.merge_pdf(filename)
                self.manager.auto_orient_pages()
                self.refresh_pages_view()
            except Exception as e:
                messagebox.showerror("Błąd scalania", f"Wystąpił błąd: {e}")

    def _action_save_pdf(self):
        """Zapisuje edytowany plik PDF na dysku (domyślnie w folderze 'do druku')."""
        if self.manager.get_page_count() == 0:
            messagebox.showwarning("Pusty dokument", "Dokument nie zawiera żadnych stron do zapisania.")
            return

        initial_name = "dokument.pdf"
        if self.manager.source_path:
            initial_name = self.manager.source_path.stem + "_edytowany.pdf"

        init_dir = self._get_initial_dir()
        out_path = filedialog.asksaveasfilename(
            title="Zapisz plik PDF (domyślnie: do druku)",
            initialdir=init_dir,
            initialfile=initial_name,
            filetypes=[("Dokument PDF", "*.pdf")]
        )
        if out_path:
            self._last_dir = Path(out_path).parent
            if not out_path.lower().endswith(".pdf"):
                out_path += ".pdf"
            try:
                self.manager.save(out_path)
                messagebox.showinfo("Sukces", f"Zapisano plik PDF:\n{out_path}")
                self.manager.source_path = Path(out_path)
                self.refresh_pages_view()
            except Exception as e:
                messagebox.showerror("Błąd zapisu", f"Nie udało się zapisać pliku PDF:\n{e}")
