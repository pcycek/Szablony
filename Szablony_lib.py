import json
import os
import copy
import gc
import random

from PIL import Image, ImageDraw, ImageFont, ImageOps
from paths import PROJEKTY_DIR, OBRAZY_DIR, WYNIKI_DIR, TEKSTY_DIR, DO_DRUKU_DIR

gc.disable()
# operacje

class Szablony:
    """
    Klasa do tworzenia i łączenia szablonów graficznych opartych o sloty.
    Wspiera obrazy, tekst, cache JPG oraz operatory + i /.
    """

    def __init__(self):
        # Obraz wynikowy
        self.img = None
        self.draw = None

        # Sloty projektu
        self.sloty = []

        # Wymiary projektu
        self.szerokosc = 0
        self.wysokosc = 0

        # Dane projektu
        self.nazwa_projektu = "Nowy"
        self.kolor_tla = "white"

        # Cache obrazów: sciezka -> (Image, mtime)
        self.cache_obrazow = {}
        
        # Cache renderowania (RAM only) - Tu trzymamy WSZYSTKO co potrzebne do rysowania
        # Klucz: index slotu (int)
        # Wartość: dict { "text": str, "collage": list, "value": int, ... }
        self._render_cache = {}
        
        # listy fo zspisu undo/redo
        self._undo_stack = []
        self._redo_stack = []
        self._max_undo = 5

    # =====================================================
    # PROJEKT
    # =====================================================

    def nowy_projekt(self, nazwa, szerokosc, wysokosc, kolor_tla="white"):
        """Tworzy nowy projekt."""
        
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.nazwa_projektu = nazwa
        self.szerokosc = szerokosc
        self.wysokosc = wysokosc
        self.kolor_tla = kolor_tla
        self.sloty = []
        
        self.prepare_render_data(force=True)
        self.render_all()

    def otworz_projekt(self, nazwa_pliku):
        from paths import napraw_sciezke
        path = napraw_sciezke(nazwa_pliku, "json")

        if not path or not path.is_file():
            return False

        with open(path, "r", encoding="utf-8") as f:
            dane = json.load(f)

        self.nazwa_projektu = dane["nazwa"]
        self.szerokosc = dane["szerokosc"]
        self.wysokosc = dane["wysokosc"]
        self.sloty = dane["sloty"]

        # Odbudowa CACHE obrazów (fizyczne pliki) - to zostaje w self (global cache)
        # Ale cache renderowania (_render_cache) budujemy od zera
        self.prepare_render_data(force=True)
        self.render_all()
        return True

    # =====================================================
    # CACHE OBRAZÓW
    # =====================================================
    def _zaladuj_obraz_z_cache(self, sciezka):
        """Ładuje obraz z cache lub z dysku jeśli zmieniony."""
        from paths import napraw_sciezke

        pelna_sciezka = napraw_sciezke(sciezka, "img")
        
        try:
            mtime = os.path.getmtime(pelna_sciezka)
        except Exception:
            mtime = 0 

        if sciezka in self.cache_obrazow:
            img, zapisany_mtime = self.cache_obrazow[sciezka]
            if zapisany_mtime == mtime:
                return img

        try:
            img = Image.open(pelna_sciezka).convert("RGB")
            self.cache_obrazow[sciezka] = (img, mtime)
            return img
        except Exception as e:
            print(f"Nie udało się załadować obrazu: {e}")
            return Image.new("RGB", (100, 100), "pink")

    # =====================================================
    # RENDER ENGINE
    # =====================================================
    
    def prepare_render_data(self, force=False):
        """
        Przygotowuje WSZYSTKIE dane do renderowania.
        1. Rozwiązuje zależności liczbowe (random/dependent).
        2. Przygotowuje teksty.
        3. Przygotowuje układy kolaży (liczy pozycje obrazków).
        """
        if force:
            self._render_cache = {}
            
        # 1. Rozwiązywanie zależności liczbowych (iteracyjnie)
        max_iter = len(self.sloty) + 2
        iteracja = 0
        zmieniono = True
        
        # Wewnętrzny helper do pobrania wartości z cache
        def get_val(idx):
            if idx in self._render_cache and "value" in self._render_cache[idx]:
                return self._render_cache[idx]["value"]
            return None

        while zmieniono and iteracja < max_iter:
            zmieniono = False
            iteracja += 1
            
            for i, s in enumerate(self.sloty):
                # Jeśli mamy już wartość w cache, to pomijamy
                if get_val(i) is not None:
                    continue
                    
                tekst_dane = s.get("tekst")
                if not tekst_dane:
                    continue
                
                typ = "manual"
                if isinstance(tekst_dane, dict):
                    typ = tekst_dane.get("typ", "manual")
                
                nowa_wartosc = None
                
                if typ == "manual":
                    val_str = tekst_dane.get("value", "") if isinstance(tekst_dane, dict) else tekst_dane
                    try:
                        nowa_wartosc = int(val_str)
                    except:
                        pass
                        
                elif typ == "random":
                    range_str = tekst_dane.get("range", "1-100")
                    try:
                        parts = range_str.split("-")
                        if len(parts) == 2:
                            min_v = int(parts[0].strip())
                            max_v = int(parts[1].strip())
                            if min_v > max_v: min_v, max_v = max_v, min_v
                            nowa_wartosc = random.randint(min_v, max_v)
                    except:
                        pass
                
                elif typ == "random_dependent":
                    src_idx = int(tekst_dane.get("source", -1))
                    src_val = get_val(src_idx)
                    
                    if src_val is not None:
                        rel = tekst_dane.get("relation", "smaller")
                        limit = int(tekst_dane.get("limit", 0))
                        try:
                            if rel == "smaller":
                                gorna = src_val
                                dolna = limit
                                if dolna > gorna: dolna = gorna 
                                nowa_wartosc = random.randint(dolna, gorna)
                            elif rel == "larger":
                                dolna = src_val
                                gorna = limit
                                if dolna > gorna: gorna = dolna
                                nowa_wartosc = random.randint(dolna, gorna)
                        except:
                            pass
                
                if nowa_wartosc is not None:
                    if i not in self._render_cache: self._render_cache[i] = {}
                    self._render_cache[i]["value"] = nowa_wartosc
                    zmieniono = True

        # 2. Generowanie danych dla KAŻDEGO slotu (Tekst, Kolaż)
        for i, s in enumerate(self.sloty):
            # Wykrywanie zmian geometrii
            should_recalc_layout = False
            current_coords = tuple(s["coords"])
            
            if i not in self._render_cache:
                self._render_cache[i] = {}
                should_recalc_layout = True
            else:
                # Sprawdź czy geometria się zmieniła (dla kolaży to ważne)
                last_coords = self._render_cache[i].get("last_coords")
                if last_coords != current_coords:
                    should_recalc_layout = True
            
            cache_slot = self._render_cache[i]
            cache_slot["last_coords"] = current_coords
            
            # --- TEKST ---
            if s.get("tekst"):
                val_text = ""
                # Czy to liczba z dependency?
                if "value" in cache_slot:
                    val_text = str(cache_slot["value"])
                else:
                    # Inne typy tekstów (file, manual string)
                    dane = s["tekst"]
                    if isinstance(dane, str):
                        val_text = dane
                    elif isinstance(dane, dict):
                        t = dane.get("typ", "manual")
                        if t == "random_dependent":
                            val_text = "[...]" 
                        elif t == "manual":
                             val_text = dane.get("value", "")
                        elif t == "file":
                            fpath = self._resolve_text_path(dane.get("file", ""))
                            try:
                                with open(fpath, "r", encoding="utf-8") as f:
                                    raw = f.read()
                                idx = int(dane.get("index", 0))
                                parts = raw.split(dane.get("separator", ","))
                                if idx < len(parts):
                                    val_text = parts[idx].strip()
                                else:
                                    val_text = ""
                            except Exception as e:
                                print(f"Błąd wczytywania pliku tekstowego {fpath}: {e}")
                                val_text = "[ERR]"
                
                cache_slot["final_text"] = val_text
            
            # --- KOLAŻ ---
            # Przeliczamy tylko gdy trzeba (nowy slot lub zmiana geometrii, lub brak danych)
            if s.get("kolaz") and (should_recalc_layout or "collage_items" not in cache_slot):
                k = s["kolaz"]
                # 1. Ilość
                n = 1
                if k.get("source_slot") is not None:
                    src = k["source_slot"]
                    if get_val(src) is not None:
                        n = get_val(src)
                elif k.get("random"):
                    if "collage_n" in cache_slot:
                         n = cache_slot["collage_n"]
                    else:
                         n = random.randint(k.get("min", 1), k.get("max", 1))
                         cache_slot["collage_n"] = n
                else:
                    n = k.get("ilosc", 1)
                
                # 2. Layout (Grid)
                layout_items = []
                if n > 0:
                    c = s["coords"]
                    slot_w = c[2] - c[0]
                    slot_h = c[3] - c[1]
                    
                    if slot_w > 0 and slot_h > 0:
                        ratio = slot_w / slot_h
                        cols = max(1, int((n * ratio) ** 0.5))
                        rows = (n + cols - 1) // cols
                        rows = max(1, rows)
                        
                        cell_w = max(1, slot_w // cols)
                        cell_h = max(1, slot_h // rows)
                        
                        margines_proc = k.get("margines_proc", 10)
                        margin_x = int(cell_w * margines_proc / 100)
                        margin_y = int(cell_h * margines_proc / 100)
                        
                        max_w = max(1, cell_w - margin_x)
                        max_h = max(1, cell_h - margin_y)
                        
                        base_path = k.get("sciezka")
                        
                        for idx in range(n):
                            r = idx // cols
                            c_idx = idx % cols
                            
                            # Obliczamy relatywne pozycje środka komórki w slocie
                            # Żeby potem przy renderze (i skalowaniu) to odtworzyć
                            # Ale uwaga: render potrzebuje Absolutnych pozycji dla danej skali.
                            # Najłatwiej zapisać pozycje znormalizowane (0.0-1.0) lub relatywne do slotu.
                            # Zapiszmy relatywne współrzędne w pikselach dla skali 1.0 (bazowej).
                            
                            cell_x = c_idx * cell_w
                            cell_y = r * cell_h
                            
                            # Wyliczamy offset wewnątrz komórki (centrowanie)
                            # Tutaj musimy znać proporcje obrazka, żeby go wycentrować.
                            # To wymaga załadowania obrazka w prepare? TAK.
                            img_obj = self._zaladuj_obraz_z_cache(base_path)
                            iw, ih = img_obj.size
                            
                            # Skalowanie "contain" wewnątrz max_w/max_h
                            scale_factor = min(max_w / iw, max_h / ih)
                            fw = int(iw * scale_factor)
                            fh = int(ih * scale_factor)
                            
                            final_x = cell_x + (cell_w - fw) // 2
                            final_y = cell_y + (cell_h - fh) // 2
                            
                            layout_items.append({
                                "path": base_path,
                                "rel_x": final_x, # Względem lewego górnego rogu slotu
                                "rel_y": final_y,
                                "w": fw,
                                "h": fh
                            })

                cache_slot["collage_items"] = layout_items

    def render_all(self, skala=1.0):
        """Renderuje (TYLKO rysuje) na podstawie _render_cache."""
        
        # Upewnij się, że mamy dane (uzupełnia braki, ale nie przelicza istniejących)
        self.prepare_render_data(force=False)
        
        w = int(self.szerokosc * skala)
        h = int(self.wysokosc * skala)

        self.img = Image.new("RGB", (w, h), self.kolor_tla)
        self.draw = ImageDraw.Draw(self.img)

        for i in range(len(self.sloty)):
            self._renderuj_pojedynczy_slot(i, skala)

    def _renderuj_pojedynczy_slot(self, i, skala=1.0):
        s = self.sloty[i]
        c_base = s["coords"]
        
        # Przeliczanie współrzędnych wg skali
        c = [int(val * skala) for val in c_base]
        
        slot_w = c[2] - c[0]
        slot_h = c[3] - c[1]

        # 0. Dane z cache
        cache = self._render_cache.get(i, {})

        # 1. Tło slotu
        if s.get("fill"):
            self.draw.rectangle(c, fill=s["fill"])

        # 2. Obraz / Kolaż
        if "collage_items" in cache and cache["collage_items"]:
            # Rysowanie kolażu z cache
            for item in cache["collage_items"]:
                # Pozycje są relatywne dla 1.0. Skalujemy je.
                ix = c[0] + int(item["rel_x"] * skala)
                iy = c[1] + int(item["rel_y"] * skala)
                iw = int(item["w"] * skala)
                ih = int(item["h"] * skala)
                
                if iw > 0 and ih > 0:
                    img = self._zaladuj_obraz_z_cache(item["path"])
                    # Resize na żywo (dla jakości pri druku można by ładować high-res, ale cache trzyma 'path' więc ok)
                    # Używamy Laczos
                    img_resized = img.resize((iw, ih), Image.LANCZOS)
                    self.img.paste(img_resized, (ix, iy))
                    
        elif s.get("image_path") and not s.get("kolaz"):
             # Pojedynczy obraz
             path = self._resolve_image_path(s["image_path"])
             if os.path.exists(path):
                 orig = Image.open(path).convert("RGB")
                 
                 # Centrowanie i skalowanie (contain)
                 # Możemy to obliczyć tu, bo to deterministyczne z natury (tylko geometria)
                 orig_w, orig_h = orig.size
                 scale_factor = min(slot_w / orig_w, slot_h / orig_h)
                 fw = int(orig_w * scale_factor)
                 fh = int(orig_h * scale_factor)
                 
                 ix = c[0] + (slot_w - fw) // 2
                 iy = c[1] + (slot_h - fh) // 2
                 
                 if fw > 0 and fh > 0:
                     orig_resized = orig.resize((fw, fh), Image.LANCZOS)
                     self.img.paste(orig_resized, (ix, iy))


        # 3. Obramowanie
        if s.get("outline"):
            width = int(s.get("outline_width", 1) * skala)
            self.draw.rectangle(c, outline=s["outline"], width=width)

        # 4. Tekst
        if "final_text" in cache and cache["final_text"]:
            self._renderuj_tekst_z_cache(i, cache["final_text"], skala)

    def _renderuj_tekst_z_cache(self, i, txt, skala=1.0):
        """To samo co wcześniej _renderuj_tekst_bezpieczny, ale bierze gotowy string."""
        s = self.sloty[i]
        c_base = s["coords"]
        c = [int(val * skala) for val in c_base]
        
        # Konfiguracja align
        align = "center"
        if isinstance(s["tekst"], dict):
            align = s["tekst"].get("align", "center")
            
        # ... Logika czcionek i rysowania ...
        w = c[2] - c[0]
        h = c[3] - c[1]
        
        base_margin = int(10 * skala)
        margin_x = min(base_margin, int(w * 0.15))
        margin_y = min(base_margin, int(h * 0.15))
        
        max_w = w - (2 * margin_x)
        max_h = h - (2 * margin_y)
        
        if max_w < 1 or max_h < 1:
            return

        font = ImageFont.load_default()
        start_size = int(100 * skala if skala >= 1 else 100)
        
        found_font = False
        smallest_font = None 
        
        try:
            for size in range(start_size, 4, -2):
                f = ImageFont.truetype("arial.ttf", size)
                smallest_font = f
                bb = self.draw.textbbox((0, 0), txt, font=f)
                bw = bb[2] - bb[0]
                bh = bb[3] - bb[1]
                if bw <= max_w and bh <= max_h:
                    font = f
                    found_font = True
                    break
            
            if not found_font and smallest_font:
                font = smallest_font
        except:
            pass
            
        cx = (c[0] + c[2]) / 2
        cy = (c[1] + c[3]) / 2
        
        text_x = cx
        text_y = cy
        pil_anchor = "mm"
        
        if align == "left":
            text_x = c[0] + margin_x
            pil_anchor = "lm"
        elif align == "right":
            text_x = c[2] - margin_x
            pil_anchor = "rm"
            
        self.draw.text((text_x, text_y), txt, fill="black", anchor=pil_anchor, font=font)


    def _resolve_image_path(self, sciezka):
        from paths import napraw_sciezke
        return napraw_sciezke(sciezka, "img")

    def _resolve_text_path(self, sciezka):
        from paths import napraw_sciezke
        return napraw_sciezke(sciezka, "txt")

    def _odbuduj_cache_slotu(self, indeks):
        # W nowej architekturze cache jest budowany w prepare_render_data
        # Ta metoda jest zachowana dla kompatybilności wstecznej (jeśli coś ją woła)
        pass

    def wklej_jeden_obraz_na_kolaz(
        self,
        indeks,
        sciezka,
        ilosc=None,
        random_cfg=None,
        source_slot=None,
        margines_proc=10
    ):
        if not (0 <= indeks < len(self.sloty)):
            return
    
        self.zapisz_undo()
        
        s = self.sloty[indeks]
        
        # Przygotowanie konfiguracji kolażu
        kolaz_cfg = {
            "typ": "jeden_obraz",
            "sciezka": sciezka,
            "margines_proc": margines_proc
        }
        
        if source_slot is not None:
            kolaz_cfg["source_slot"] = source_slot
            # Resetujemy inne flagi
            if "random" in kolaz_cfg: del kolaz_cfg["random"]
            if "ilosc" in kolaz_cfg: del kolaz_cfg["ilosc"]
            
        elif random_cfg:
            kolaz_cfg["random"] = True
            kolaz_cfg["min"] = random_cfg["min"]
            kolaz_cfg["max"] = random_cfg["max"]
            if "source_slot" in kolaz_cfg: del kolaz_cfg["source_slot"]
            if "ilosc" in kolaz_cfg: del kolaz_cfg["ilosc"]
            
        else:
            # Stała ilość
            kolaz_cfg["ilosc"] = ilosc if ilosc is not None else 1
            if "source_slot" in kolaz_cfg: del kolaz_cfg["source_slot"]
            if "random" in kolaz_cfg: del kolaz_cfg["random"]

        s["kolaz"] = kolaz_cfg
        
        # Czyścimy cache dla tego slotu, aby wymusić przeliczenie
        if indeks in self._render_cache:
            del self._render_cache[indeks]
            
        self.render_all()

    # =====================================================
    # UNDO REDO
    # =====================================================
    def _snapshot(self):
        return {
            "szerokosc": self.szerokosc,
            "wysokosc": self.wysokosc,
            "sloty": copy.deepcopy(self.sloty),
            "_render_cache": copy.deepcopy(self._render_cache) # Zapisujemy stan wizualny
        }
    def zapisz_undo(self):
        snapshot = self._snapshot()
        if self._undo_stack and snapshot == self._undo_stack[-1]:
            return
        
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        
    def undo(self):
        if not self._undo_stack:
            return

        self._redo_stack.append(self._snapshot())

        stan = self._undo_stack.pop()
        self.szerokosc = stan["szerokosc"]
        self.wysokosc = stan["wysokosc"]
        self.sloty = stan["sloty"]
        self._render_cache = stan.get("_render_cache", {})

        # self._odbuduj_cache() # Już niepotrzebne
        self.render_all()
        
    def redo(self):
        if not self._redo_stack:
            return

        self._undo_stack.append(self._snapshot())

        stan = self._redo_stack.pop()
        self.szerokosc = stan["szerokosc"]
        self.wysokosc = stan["wysokosc"]
        self.sloty = stan["sloty"]
        self._render_cache = stan.get("_render_cache", {})

        self.render_all()
        
    def _odbuduj_cache(self):
        # Wrapper dla kompatybilności
        self.prepare_render_data(force=False)
                
  # ========================================
    # TRANSFORMACJE SLOTÓW
    # =====================================================
    def zapamietaj_baze_slotu(self, indeks):
       if 0 <= indeks < len(self.sloty):
           self.sloty[indeks]["_base_coords"] = self.sloty[indeks]["coords"].copy()
           
    def przesun_procentowo_abs(self, indeks, proc_x, proc_y):
       if not (0 <= indeks < len(self.sloty)):
           return

       s = self.sloty[indeks]
       if "_base_coords" not in s:
           return

       bx1, by1, bx2, by2 = s["_base_coords"]
       w = bx2 - bx1
       h = by2 - by1

       dx = int((self.szerokosc - w) * proc_x / 200)
       dy = int((self.wysokosc - h) * proc_y / 200)

       x1 = bx1 + dx
       y1 = by1 + dy

       x1 = max(0, min(self.szerokosc - w, x1))
       y1 = max(0, min(self.wysokosc - h, y1))

       s["coords"] = [x1, y1, x1 + w, y1 + h]

    def skaluj_od_srodka_abs(self, indeks, proc_w, proc_h):
       if not (0 <= indeks < len(self.sloty)):
           return

       s = self.sloty[indeks]
       if "_base_coords" not in s:
           return

       bx1, by1, bx2, by2 = s["_base_coords"]
       bw = bx2 - bx1
       bh = by2 - by1

       cx = (bx1 + bx2) / 2
       cy = (by1 + by2) / 2

       nw = bw * (1 + proc_w / 100)
       nh = bh * (1 + proc_h / 100)

       x1 = int(cx - nw / 2)
       y1 = int(cy - nh / 2)
       x2 = int(cx + nw / 2)
       y2 = int(cy + nh / 2)

       s["coords"] = [x1, y1, x2, y2]
       
    def generuj_siatke(self, kolumny, wiersze, margines=(5, 5)):
        """Tworzy siatkę slotów."""
        self.zapisz_undo()
        self.sloty = []
        self._render_cache = {} # Reset cache przy nowej siatce

        sz_k = self.szerokosc / kolumny
        w_k = self.wysokosc / wiersze
        m_x = sz_k * margines[0] * 0.01
        m_y = w_k * margines[1] * 0.01

        for w in range(wiersze):
            for k in range(kolumny):
                coords = [
                    int(k * sz_k + m_x),
                    int(w * w_k + m_y),
                    int((k + 1) * sz_k - m_x),
                    int((w + 1) * w_k - m_y)
                ]
                self.sloty.append({
                    "coords": coords,
                    "fill": None,
                    "outline": "black",
                    "outline_width": 2,
                    "image_path": None,
                    "tekst": None
                })
        
        self.prepare_render_data(force=True)
        self.render_all()

    def edytuj_slot(self, indeks, **kwargs):
        """Edytuje właściwości slotu."""
        if 0 <= indeks < len(self.sloty):
            self.zapisz_undo()
            self.sloty[indeks].update(kwargs)
            
            # Reset cache tego slotu
            if indeks in self._render_cache:
                del self._render_cache[indeks]
            self.render_all()

    def usun_slot(self, indeks):
        """Usuwa slot."""
        if 0 <= indeks < len(self.sloty):
            self.zapisz_undo()
            self.sloty.pop(indeks)
            
            # Pełny reset, bo indeksy się zmieniają
            self._render_cache = {}
            self.prepare_render_data(force=True)
            self.render_all()

    def wstaw_tekst_z_pliku(self, indeks, plik, separator=",", index=0, align="center"):
        """Ustawia slot w tryb tekstu z pliku."""
        if 0 <= indeks < len(self.sloty):
            self.zapisz_undo()
            self.sloty[indeks]["tekst"] = {
                "typ": "file",
                "file": plik,
                "separator": separator,
                "index": index,
                "align": align
            }
            if indeks in self._render_cache:
                del self._render_cache[indeks]
            self.render_all()

    def renderuj_wszystkie_projekty(self, skaluj_300dpi=False):
        """
        Renderuje wszystkie projekty .json z folderu PROJEKTY_DIR.
        Zwraca (liczba_przetworzonych, lista_bledow).
        """
        import glob
        
        pliki = list(PROJEKTY_DIR.glob("*.json"))
        bledy = []
        sukcesy = 0
        
        scale = 3.0 if skaluj_300dpi else 1.0
        
        for p in pliki:
            try:
                temp_sz = Szablony() 
                if temp_sz.otworz_projekt(p.name):
                    # Wymuś nowe losowanie dla każdego projektu przy eksporcie
                    temp_sz.prepare_render_data(force=True)
                    temp_sz.render_all(skala=scale)
                    
                    if temp_sz.img:
                        if skaluj_300dpi:
                            out_path = DO_DRUKU_DIR / f"{p.stem}.jpg"
                            temp_sz.img.convert("RGB").save(out_path, "JPEG", quality=95, dpi=(300, 300))
                        else:
                            out_path = WYNIKI_DIR / f"{p.stem}.jpg"
                            temp_sz.img.convert("RGB").save(out_path, "JPEG", quality=95)
                            
                        sukcesy += 1
            except Exception as e:
                bledy.append(f"{p.name}: {e}")
                
        return sukcesy, bledy

    def renderuj_pojedynczy_do_druku(self, nazwa_projektu):
        """Renderuje wybrany projekt w wysokiej jakości do folderu DO_DRUKU."""
        temp = Szablony()
        if not temp.otworz_projekt(nazwa_projektu):
            raise Exception("Nie znaleziono projektu")
            
        temp.prepare_render_data(force=True)
        scale = 4.0 
        temp.render_all(skala=scale)
        
        if temp.img:
             sciezka = DO_DRUKU_DIR / f"{nazwa_projektu}_print.jpg"
             temp.img.convert("RGB").save(sciezka, quality=100, dpi=(300, 300))
             return str(sciezka)
        else:
             raise Exception("Błąd renderowania (pusty obraz)")

    # =====================================================
    # OBRAZY
    # =====================================================
    def wstaw_obrazek(self, indeks, sciezka):
        """Wstawia obraz do slotu bez przycinania (tryb contain)."""
        if not (0 <= indeks < len(self.sloty)):
            return
    
        self.zapisz_undo()
    
        s = self.sloty[indeks]
        
        # W nowej architekturze tylko zapisujemy ścieżkę do JSON
        # Obliczenia i ładowanie nastąpi w render_all (a ten używa cache)
        # Ale musimy wyczyścić cache tego slotu
        
        s["image_path"] = sciezka
        
        # --- czyścimy ewentualny kolaż ---
        if "kolaz" in s:
            del s["kolaz"]
            
        # Reset cache
        if indeks in self._render_cache:
            del self._render_cache[indeks]
    
        self.render_all()

    def wstaw_wiele_obrazkow(self, lista_sciezek, lista_indeksow):
        """Wstawia wiele obrazów i renderuje raz."""
        for sciezka, indeks in zip(lista_sciezek, lista_indeksow):
            self.wstaw_obrazek(indeks, sciezka)
        self.render_all()

    # =====================================================
    # OPERATORY
    # =====================================================

    def __add__(self, other):
        """Łączy projekty poziomo."""
        s1, h1, sl1 = self.szerokosc, self.wysokosc, copy.deepcopy(self.sloty)
        s2, h2, sl2 = other.szerokosc, other.wysokosc, copy.deepcopy(other.sloty)

        skala = h1 / h2

        for s in sl2:
            c = s["coords"]
            s["coords"] = [
                int(c[0] * skala + s1),
                int(c[1] * skala),
                int(c[2] * skala + s1),
                int(c[3] * skala)
            ]
            s["_cached_img"] = None
            sl1.append(s)

        wynik = Szablony()
        wynik.nowy_projekt("Suma", s1 + int(s2 * skala), h1)
        wynik.sloty = sl1
        
        # ODBUDOWA CACHE OBRAZÓW
        for i, s in enumerate(wynik.sloty):
            s["_cached_img"] = None
            s["_cached_imgs"] = None

            if "kolaz" in s:
                wynik._odbuduj_cache_slotu(i)
            elif s.get("image_path"):
                # wstaw_obrazek ładuje obraz i robi render (trochę wolne, ale bezpieczne)
                wynik.wstaw_obrazek(i, s["image_path"])

        wynik.render_all()
        return wynik

    def __truediv__(self, other):
        """Łączy projekty pionowo."""
        s1, h1, sl1 = self.szerokosc, self.wysokosc, copy.deepcopy(self.sloty)
        s2, h2, sl2 = other.szerokosc, other.wysokosc, copy.deepcopy(other.sloty)

        skala = s1 / s2

        for s in sl2:
            c = s["coords"]
            s["coords"] = [
                int(c[0] * skala),
                int(c[1] * skala + h1),
                int(c[2] * skala),
                int(c[3] * skala + h1)
            ]
            s["_cached_img"] = None
            sl1.append(s)

        wynik = Szablony()
        wynik.nowy_projekt("Dzielenie", s1, h1 + int(h2 * skala))
        wynik.sloty = sl1
        
        # ODBUDOWA CACHE OBRAZÓW
        for i, s in enumerate(wynik.sloty):
            s["_cached_img"] = None
            s["_cached_imgs"] = None

            if "kolaz" in s:
                wynik._odbuduj_cache_slotu(i)
            elif s.get("image_path"):
                wynik.wstaw_obrazek(i, s["image_path"])
        
        wynik.render_all()
        return wynik

    # =====================================================
    # ZAPIS
    # =====================================================

    def zapisz(self):
        sloty_json = []

        for s in self.sloty:
            czysty = {}
            for k, v in s.items():
                if k.startswith("_"):
                    continue  # NIE zapisujemy cache
                czysty[k] = v
            sloty_json.append(czysty)

        img_path = WYNIKI_DIR / f"{self.nazwa_projektu}.jpg"
        json_path = PROJEKTY_DIR / f"{self.nazwa_projektu}.json"

        if self.img:
            self.img.convert("RGB").save(img_path, "JPEG", quality=95)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "nazwa": self.nazwa_projektu,
                    "szerokosc": self.szerokosc,
                    "wysokosc": self.wysokosc,
                    "sloty": sloty_json
                },
                f,
                indent=4,
                ensure_ascii=False
            )

gc.enable()
