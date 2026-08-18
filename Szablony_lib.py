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
        self._computed = {}
        
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
    # COMPUTE ENGINE
    # =====================================================
    def compute(self):
        self._computed = {}
        for i in range(len(self.sloty)):
            self._compute_slot(i)
        self._compute_unique_numbers()
        self._compute_auto_images()
        self._compute_letters()

    def _compute_unique_numbers(self):
        groups = {}
        for i, s in enumerate(self.sloty):
            tekst_dane = s.get("tekst") or s.get("text")
            if isinstance(tekst_dane, dict) and tekst_dane.get("typ") in ("random_unique", "random_no_repeat"):
                gid = tekst_dane.get("group_id", f"grp_{tekst_dane.get('min', 1)}_{tekst_dane.get('max', 100)}")
                groups.setdefault(gid, []).append(i)

        for gid, indices in groups.items():
            if not indices:
                continue
            first_cfg = self.sloty[indices[0]].get("tekst") or self.sloty[indices[0]].get("text")
            min_v = int(first_cfg.get("min", 1))
            max_v = int(first_cfg.get("max", 100))
            if min_v > max_v:
                min_v, max_v = max_v, min_v

            dostepne = list(range(min_v, max_v + 1))
            k = min(len(indices), len(dostepne))
            wylosowane = random.sample(dostepne, k)

            for idx, val in zip(indices[:k], wylosowane):
                if idx not in self._computed:
                    self._computed[idx] = {}
                self._computed[idx]["value"] = val
                self._computed[idx]["text"] = str(val)

    def _compute_slot(self, i):
        s = self.sloty[i]
        self._computed[i] = {}
        s["visible"] = True

        # LICZBY
        if s.get("liczba"):
            cfg = s["liczba"]
            if cfg.get("random"):
                val = random.randint(cfg.get("min", 0), cfg.get("max", 100))
            elif cfg.get("ref") is not None:
                base = self._computed.get(cfg["ref"], {}).get("value", 0)
                val = base + cfg.get("offset", 0)
            else:
                val = cfg.get("value", 0)
            self._computed[i]["value"] = val

        # KOLAŻ
        elif "kolaz" in s:
            k = s["kolaz"]
            if k.get("ref_slot") is not None:
                val = self._computed.get(k["ref_slot"], {}).get("value", 1)
            elif k.get("source_slot") is not None:
                val = self._computed.get(k["source_slot"], {}).get("value", 1)
            elif k.get("random"):
                val = random.randint(k.get("min", 1), k.get("max", 1))
            else:
                val = k.get("ilosc_obrazkow", k.get("ilosc", 1))
            self._computed[i]["kolaz_count"] = val

        # TEKST
        tekst_dane = None
        if s.get("tekst"):
            tekst_dane = s["tekst"]
        elif s.get("text"):
            tekst_dane = s["text"]

        if tekst_dane:
            if isinstance(tekst_dane, dict):
                typ = tekst_dane.get("typ", "manual")
                if typ == "file":
                    try:
                        fpath = self._resolve_text_path(tekst_dane.get("file", ""))
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read()
                        parts = content.split(tekst_dane.get("separator", ","))
                        idx = int(tekst_dane.get("index", 0))
                        txt = parts[idx].strip() if idx < len(parts) else ""
                    except Exception:
                        txt = "ERR"
                    self._computed[i]["text"] = txt
                elif typ == "manual":
                    self._computed[i]["text"] = str(tekst_dane.get("value", ""))
                elif typ == "random":
                    range_str = str(tekst_dane.get("range", "1-100"))
                    try:
                        parts = range_str.split("-")
                        min_v, max_v = int(parts[0].strip()), int(parts[1].strip())
                        if min_v > max_v: min_v, max_v = max_v, min_v
                        val = random.randint(min_v, max_v)
                        self._computed[i]["value"] = val
                        self._computed[i]["text"] = str(val)
                    except:
                        pass
                elif typ in ("random_unique", "random_no_repeat"):
                    if i in self._computed and "value" in self._computed[i]:
                        val = self._computed[i]["value"]
                    else:
                        min_v = int(tekst_dane.get("min", 1))
                        max_v = int(tekst_dane.get("max", 100))
                        val = random.randint(min_v, max_v)
                    self._computed[i]["value"] = val
                    self._computed[i]["text"] = str(val)
                elif typ == "random_dependent":
                    src_idx = int(tekst_dane.get("source", -1))
                    src_val = self._computed.get(src_idx, {}).get("value", 0)
                    rel = tekst_dane.get("relation", "smaller")
                    limit = int(tekst_dane.get("limit", 0))
                    try:
                        if rel == "smaller":
                            gorna, dolna = src_val, limit
                            if dolna > gorna: dolna = gorna
                            val = random.randint(dolna, gorna)
                        else:
                            dolna, gorna = src_val, limit
                            if dolna > gorna: gorna = dolna
                            val = random.randint(dolna, gorna)
                        self._computed[i]["value"] = val
                        self._computed[i]["text"] = str(val)
                    except:
                        pass
            else:
                self._computed[i]["text"] = str(tekst_dane)

    def _compute_auto_images(self):
        from paths import OBRAZY_DIR
        folders_to_slots = {}
        for i, s in enumerate(self.sloty):
            if "auto_images" in s:
                folder = s["auto_images"].get("folder")
                if folder:
                    folders_to_slots.setdefault(folder, []).append(i)
                    
        for folder, indices in folders_to_slots.items():
            folder_path = OBRAZY_DIR / folder
            if not folder_path.is_dir():
                continue
                
            pliki = [p.name for p in folder_path.glob("*.*") if p.suffix.lower() in [".jpg", ".png", ".jpeg"]]
            if not pliki:
                continue
                
            repeat = self.sloty[indices[0]]["auto_images"].get("repeat", 1)
            pula = pliki * repeat
            random.shuffle(pula)
            
            no_same_row = self.sloty[indices[0]]["auto_images"].get("no_same_row", False)
            
            for idx in indices:
                if not pula: break
                
                if no_same_row:
                    my_y = self.sloty[idx]["coords"][1]
                    used_in_row = set()
                    for other_idx in indices:
                        if other_idx == idx: continue
                        if other_idx in self._computed and "image_path" in self._computed[other_idx]:
                            other_y = self.sloty[other_idx]["coords"][1]
                            if abs(my_y - other_y) < 10:
                                used_img = self._computed[other_idx]["image_path"].split("/")[-1]
                                used_in_row.add(used_img)
                                
                    chosen_img = next((img for img in pula if img not in used_in_row), None)
                    if chosen_img:
                        pula.remove(chosen_img)
                    else:
                        chosen_img = pula.pop(0)
                else:
                    chosen_img = pula.pop(0)
                    
                self._computed[idx]["image_path"] = f"{folder}/{chosen_img}"

    def _compute_letters(self):
        from paths import TEKSTY_DIR
        for s in self.sloty:
            if "letters" in s:
                cfg = s["letters"]
                file_name = cfg.get("file", "")
                separator = cfg.get("separator", "")
                try:
                    with open(TEKSTY_DIR / file_name, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    litery = content.split(separator) if separator else list(content)
                except Exception:
                    litery = []
                    
                gorne = [i for i, slot in enumerate(self.sloty) if slot.get("group") == "gora"]
                dolne = [i for i, slot in enumerate(self.sloty) if slot.get("group") == "dol"]
                
                for idx_in_gora, slot_idx in enumerate(gorne):
                    if idx_in_gora < len(litery):
                        self._computed[slot_idx]["letter"] = litery[idx_in_gora]
                        self._computed[slot_idx]["text"] = litery[idx_in_gora]
                    else:
                        self.sloty[slot_idx]["visible"] = False
                        if idx_in_gora < len(dolne):
                            self.sloty[dolne[idx_in_gora]]["visible"] = False
                break

    def _apply_auto_images(self):
        from paths import OBRAZY_DIR
        import random
        
        folders_to_slots = {}
        for i, s in enumerate(self.sloty):
            if "auto_images" in s:
                folder = s["auto_images"].get("folder")
                if folder:
                    folders_to_slots.setdefault(folder, []).append(i)
                    
        for folder, indices in folders_to_slots.items():
            folder_path = OBRAZY_DIR / folder
            if not folder_path.is_dir():
                continue
                
            pliki = [p.name for p in folder_path.glob("*.*") if p.suffix.lower() in [".jpg", ".png", ".jpeg"]]
            if not pliki:
                continue
                
            cfg = self.sloty[indices[0]]["auto_images"]
            repeat = cfg.get("repeat", 1)
            seed_val = cfg.get("seed", 123)
            no_repeat_in_row = cfg.get("no_repeat_in_row", False)
            
            pula = pliki * repeat
            rng = random.Random(seed_val)
            rng.shuffle(pula)
            
            for idx in indices:
                if not pula: break
                
                if no_repeat_in_row:
                    my_y = self.sloty[idx]["coords"][1]
                    used_in_row = set()
                    for other_idx in indices:
                        if other_idx == idx: continue
                        if other_idx in self._computed and "image_path" in self._computed[other_idx]:
                            other_y = self.sloty[other_idx]["coords"][1]
                            if abs(my_y - other_y) < 10:
                                used_img = self._computed[other_idx]["image_path"].split("/")[-1]
                                used_in_row.add(used_img)
                                
                    chosen_img = next((img for img in pula if img not in used_in_row), None)
                    if chosen_img:
                        pula.remove(chosen_img)
                    else:
                        chosen_img = pula.pop(0)
                else:
                    chosen_img = pula.pop(0)
                    
                self._computed[idx]["image_path"] = f"{folder}/{chosen_img}"

    def _apply_letters_layout(self):
        from paths import TEKSTY_DIR
        for s in self.sloty:
            if "letters_layout" in s:
                cfg = s["letters_layout"]
                source_file = cfg.get("source_file", "")
                separator = cfg.get("separator", "")
                group_name = cfg.get("group", "top")
                
                try:
                    with open(TEKSTY_DIR / source_file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    litery = content.split(separator) if separator else list(content)
                except Exception:
                    litery = []
                    
                gorne = [i for i, slot in enumerate(self.sloty) if slot.get("group") == group_name]
                dolne = [i for i, slot in enumerate(self.sloty) if slot.get("group") == ("bottom" if group_name == "top" else "top")]
                
                for idx_in_gora, slot_idx in enumerate(gorne):
                    if idx_in_gora < len(litery):
                        self._computed[slot_idx]["letter"] = litery[idx_in_gora]
                        self._computed[slot_idx]["text"] = litery[idx_in_gora]
                    else:
                        self.sloty[slot_idx]["visible"] = False
                        if idx_in_gora < len(dolne):
                            self.sloty[dolne[idx_in_gora]]["visible"] = False
                break

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
            self.compute()
            self._apply_auto_images()
            self._apply_letters_layout()
            
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
                    
                tekst_dane = None
                if s.get("tekst"):
                    tekst_dane = s["tekst"]
                elif s.get("text"):
                    tekst_dane = s["text"]

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
                
                elif typ in ("random_unique", "random_no_repeat"):
                    if i in self._computed and "value" in self._computed[i]:
                        nowa_wartosc = self._computed[i]["value"]
                    else:
                        min_v = int(tekst_dane.get("min", 1))
                        max_v = int(tekst_dane.get("max", 100))
                        nowa_wartosc = random.randint(min_v, max_v)
                
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
            tekst_dane = None
            if s.get("tekst"):
                tekst_dane = s["tekst"]
            elif s.get("text"):
                tekst_dane = s["text"]

            if tekst_dane:
                val_text = ""
                # Czy to liczba z dependency?
                if "value" in cache_slot:
                    val_text = str(cache_slot["value"])
                else:
                    # Inne typy tekstów (file, manual string)
                    dane = tekst_dane
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
                if k.get("ref_slot") is not None:
                    src = k["ref_slot"]
                    if get_val(src) is not None:
                        n = get_val(src)
                elif k.get("source_slot") is not None:
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

    def _render_lines_v2(self, draw, skala=1.0):
        gorne = [i for i, s in enumerate(self.sloty) if s.get("group") == "top" and s.get("visible", True)]
        dolne = [i for i, s in enumerate(self.sloty) if s.get("group") == "bottom" and s.get("visible", True)]
        
        for idx in range(min(len(gorne), len(dolne))):
            i_gora = gorne[idx]
            i_dol = dolne[idx]
            
            g_base = self.sloty[i_gora]["coords"]
            d_base = self.sloty[i_dol]["coords"]
            
            g = [int(val * skala) for val in g_base]
            d = [int(val * skala) for val in d_base]
            
            x1 = (g[0] + g[2]) // 2
            y1 = g[3]
            
            x2 = (d[0] + d[2]) // 2
            y2 = d[1]
            
            draw.line((x1, y1, x2, y2), fill="black", width=max(1, int(2 * skala)))

    def render_all(self, skala=1.0):
        self.prepare_render_data(force=False)
        
        w = int(self.szerokosc * skala)
        h = int(self.wysokosc * skala)

        self.img = Image.new("RGB", (w, h), self.kolor_tla)
        self.draw = ImageDraw.Draw(self.img)

        for i in range(len(self.sloty)):
            self._renderuj_pojedynczy_slot(i, skala)
            
        draw_lines = any(s.get("letters_layout", {}).get("draw_lines", False) for s in self.sloty)
        if draw_lines:
            self._render_lines_v2(self.draw, skala)

    def _render_lines(self, skala=1.0):
        gorne = [i for i, s in enumerate(self.sloty) if s.get("group") == "gora" and s.get("visible", True)]
        dolne = [i for i, s in enumerate(self.sloty) if s.get("group") == "dol" and s.get("visible", True)]
        
        for idx in range(min(len(gorne), len(dolne))):
            i_gora = gorne[idx]
            i_dol = dolne[idx]
            
            g_base = self.sloty[i_gora]["coords"]
            d_base = self.sloty[i_dol]["coords"]
            
            g = [int(val * skala) for val in g_base]
            d = [int(val * skala) for val in d_base]
            
            x1 = (g[0] + g[2]) // 2
            y1 = g[3]
            
            x2 = (d[0] + d[2]) // 2
            y2 = d[1]
            
            self.draw.line((x1, y1, x2, y2), fill="black", width=max(1, int(2 * skala)))

    def _renderuj_pojedynczy_slot(self, i, skala=1.0):
        s = self.sloty[i]
        
        if not s.get("visible", True):
            return
            
        c_base = s["coords"]
        
        # Przeliczanie współrzędnych wg skali
        c = [int(val * skala) for val in c_base]
        
        slot_w = c[2] - c[0]
        slot_h = c[3] - c[1]

        # 0. Dane z cache
        cache = self._render_cache.get(i, {})
        computed = self._computed.get(i, {})

        # 1. Tło slotu
        if s.get("fill"):
            self.draw.rectangle(c, fill=s["fill"])

        # 2. Obraz / Kolaż
        if "kolaz" in s:
            n = computed.get("kolaz_count", 0)
            if n > 0:
                k = s["kolaz"]
                ratio = slot_w / slot_h if slot_h > 0 else 1
                cols = max(1, int((n * ratio) ** 0.5))
                rows = max(1, (n + cols - 1) // cols)
                cell_w = max(1, slot_w // cols)
                cell_h = max(1, slot_h // rows)
                margines_proc = k.get("margines_proc", 10)
                margin_x = int(cell_w * margines_proc / 100)
                margin_y = int(cell_h * margines_proc / 100)
                max_w = max(1, cell_w - margin_x)
                max_h = max(1, cell_h - margin_y)
                base_path = k.get("sciezka", "")
                
                try:
                    img_obj = self._zaladuj_obraz_z_cache(base_path)
                    iw, ih = img_obj.size
                    
                    scale_factor = min(max_w / max(1, iw), max_h / max(1, ih))
                    fw = int(iw * scale_factor)
                    fh = int(ih * scale_factor)
                    
                    if fw > 0 and fh > 0:
                        img_resized = img_obj.resize((fw, fh), Image.LANCZOS)
                        
                        for idx in range(n):
                            r = idx // cols
                            c_idx = idx % cols
                            cell_x = c[0] + c_idx * cell_w
                            cell_y = c[1] + r * cell_h
                            ix = cell_x + (cell_w - fw) // 2
                            iy = cell_y + (cell_h - fh) // 2
                            self.img.paste(img_resized, (ix, iy))
                except:
                    pass
                    
        elif computed.get("image_path"):
             path = self._resolve_image_path(computed["image_path"])
             if os.path.exists(path):
                 orig = Image.open(path).convert("RGB")
                 orig_w, orig_h = orig.size
                 scale_factor = min(slot_w / max(1, orig_w), slot_h / max(1, orig_h))
                 fw = int(orig_w * scale_factor)
                 fh = int(orig_h * scale_factor)
                 ix = c[0] + (slot_w - fw) // 2
                 iy = c[1] + (slot_h - fh) // 2
                 if fw > 0 and fh > 0:
                     orig_resized = orig.resize((fw, fh), Image.LANCZOS)
                     self.img.paste(orig_resized, (ix, iy))
                     
        elif s.get("image_path") and not s.get("kolaz"):
             # Pojedynczy obraz stary kod
             path = self._resolve_image_path(s["image_path"])
             if os.path.exists(path):
                 orig = Image.open(path).convert("RGB")
                 
                 orig_w, orig_h = orig.size
                 scale_factor = min(slot_w / max(1, orig_w), slot_h / max(1, orig_h))
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
        txt = computed.get("text")
        if txt is None and "value" in computed:
            txt = str(computed["value"])
            
        if txt is not None:
            self._renderuj_tekst_z_cache(i, str(txt), skala)
        elif "final_text" in cache and cache["final_text"]:
            self._renderuj_tekst_z_cache(i, cache["final_text"], skala)

    def _renderuj_tekst_z_cache(self, i, txt, skala=1.0):
        """To samo co wcześniej _renderuj_tekst_bezpieczny, ale bierze gotowy string."""
        s = self.sloty[i]
        c_base = s["coords"]
        c = [int(val * skala) for val in c_base]
        
        # Konfiguracja align
        align = "center"
        tekst_dane = None
        if s.get("tekst"):
            tekst_dane = s["tekst"]
        elif s.get("text"):
            tekst_dane = s["text"]

        if isinstance(tekst_dane, dict):
            align = tekst_dane.get("align", "center")
            
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
        indeks=None,
        sciezka=None,
        ilosc=None,
        random_cfg=None,
        source_slot=None,
        margines_proc=10,
        slots=None
    ):
        if slots is not None:
            target_slots = [i for i in slots if 0 <= i < len(self.sloty)]
        elif indeks is not None:
            target_slots = [indeks] if 0 <= indeks < len(self.sloty) else []
        else:
            target_slots = []

        if not target_slots:
            return

        self.zapisz_undo()

        # Przygotowanie konfiguracji kolażu
        kolaz_cfg = {
            "typ": "jeden_obraz",
            "sciezka": sciezka,
            "margines_proc": margines_proc
        }

        if source_slot is not None and source_slot >= 0:
            kolaz_cfg["source_slot"] = source_slot
        elif random_cfg:
            kolaz_cfg["random"] = True
            kolaz_cfg["min"] = random_cfg["min"]
            kolaz_cfg["max"] = random_cfg["max"]
        else:
            kolaz_cfg["ilosc"] = ilosc if ilosc is not None else 1

        for i in target_slots:
            s = self.sloty[i]
            s["kolaz"] = copy.deepcopy(kolaz_cfg)
            if i in self._render_cache:
                del self._render_cache[i]
            self._compute_slot(i)

    # =====================================================
    # UNDO REDO
    # =====================================================
    def _snapshot(self):
        return {
            "szerokosc": self.szerokosc,
            "wysokosc": self.wysokosc,
            "sloty": copy.deepcopy(self.sloty),
            "_render_cache": copy.deepcopy(self._render_cache), # Zapisujemy stan wizualny
            "_computed": copy.deepcopy(self._computed) if hasattr(self, '_computed') else {}
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
        self._computed = stan.get("_computed", {})
        
    def redo(self):
        if not self._redo_stack:
            return

        self._undo_stack.append(self._snapshot())

        stan = self._redo_stack.pop()
        self.szerokosc = stan["szerokosc"]
        self.wysokosc = stan["wysokosc"]
        self.sloty = stan["sloty"]
        self._render_cache = stan.get("_render_cache", {})
        self._computed = stan.get("_computed", {})
        
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

    def edytuj_slot(self, indeks=None, slots=None, **kwargs):
        """Edytuje właściwości jednego lub wielu slotów."""
        if slots is not None:
            target_slots = [i for i in slots if 0 <= i < len(self.sloty)]
        elif indeks is not None:
            target_slots = [indeks] if 0 <= indeks < len(self.sloty) else []
        else:
            target_slots = []

        if not target_slots:
            return

        self.zapisz_undo()
        for i in target_slots:
            self.sloty[i].update(copy.deepcopy(kwargs))
            if i in self._render_cache:
                del self._render_cache[i]
            self._compute_slot(i)

    def edytuj_wszystkie_sloty(self, slots=None, **kwargs):
        """Edytuje właściwości wszystkich (lub wskazanych) slotów naraz."""
        if slots is None:
            slots = range(len(self.sloty))
        self.edytuj_slot(slots=slots, **kwargs)

    def usun_slot(self, indeks):
        """Usuwa slot."""
        if 0 <= indeks < len(self.sloty):
            self.zapisz_undo()
            self.sloty.pop(indeks)
            
            # Pełny reset, bo indeksy się zmieniają
            self._render_cache = {}
            self.prepare_render_data(force=True)

    def wstaw_tekst_z_pliku(self, indeks=None, plik="", separator=",", index=0, align="center", slots=None):
        """Ustawia slot(y) w tryb tekstu z pliku."""
        if slots is not None:
            target_slots = [i for i in slots if 0 <= i < len(self.sloty)]
        elif indeks is not None:
            target_slots = [indeks] if 0 <= indeks < len(self.sloty) else []
        else:
            target_slots = []

        if not target_slots:
            return

        self.zapisz_undo()
        for i in target_slots:
            self.sloty[i]["tekst"] = {
                "typ": "file",
                "file": plik,
                "separator": separator,
                "index": index,
                "align": align
            }
            if i in self._render_cache:
                del self._render_cache[i]
            self._compute_slot(i)

    def ustaw_tekst_wszystkim(self, tekst_dane, slots=None):
        """Ustawia konfigurację tekstu dla wszystkich (lub wybranych) slotów naraz."""
        if slots is None:
            slots = range(len(self.sloty))
        target_slots = [i for i in slots if 0 <= i < len(self.sloty)]
        if not target_slots:
            return

        self.zapisz_undo()
        for i in target_slots:
            self.sloty[i]["tekst"] = copy.deepcopy(tekst_dane)
            if i in self._render_cache:
                del self._render_cache[i]
            self._compute_slot(i)

    def losuj_liczby_bez_powtorzen(self, min_val, max_val, slots=None):
        """Przypisuje dynamiczną konfigurację losowych liczb bez powtórzeń (random.sample) do podanych slotów."""
        import time
        if slots is None:
            target_slots = list(range(len(self.sloty)))
        else:
            target_slots = [i for i in slots if 0 <= i < len(self.sloty)]

        if not target_slots:
            return

        dostepne = list(range(min_val, max_val + 1))
        if len(target_slots) > len(dostepne):
            target_slots = target_slots[:len(dostepne)]

        group_id = f"unique_grp_{min_val}_{max_val}_{int(time.time() * 1000)}"

        self.zapisz_undo()
        for idx in target_slots:
            s = self.sloty[idx]
            current_align = "center"
            if isinstance(s.get("tekst"), dict):
                current_align = s["tekst"].get("align", "center")
            s["tekst"] = {
                "typ": "random_unique",
                "group_id": group_id,
                "min": min_val,
                "max": max_val,
                "range": f"{min_val}-{max_val}",
                "align": current_align
            }
            if idx in self._render_cache:
                del self._render_cache[idx]

        self.compute()

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
    def wstaw_obrazek(self, indeks=None, sciezka=None, slots=None):
        """Wstawia obraz do slotu lub grupy slotów bez przycinania (tryb contain)."""
        if slots is not None:
            target_slots = [i for i in slots if 0 <= i < len(self.sloty)]
        elif indeks is not None:
            target_slots = [indeks] if 0 <= indeks < len(self.sloty) else []
        else:
            target_slots = []

        if not target_slots:
            return

        self.zapisz_undo()
        for i in target_slots:
            s = self.sloty[i]
            s["image_path"] = sciezka
            if "kolaz" in s:
                del s["kolaz"]
            if i in self._render_cache:
                del self._render_cache[i]
            self._compute_slot(i)

    def wstaw_obrazek_wszystkim(self, sciezka, slots=None):
        """Wstawia ten sam obraz do wszystkich (lub wybranych) slotów."""
        if slots is None:
            slots = range(len(self.sloty))
        self.wstaw_obrazek(sciezka=sciezka, slots=slots)

    def wklej_kolaz_wszystkim(
        self,
        sciezka,
        ilosc=None,
        random_cfg=None,
        source_slot=None,
        margines_proc=10,
        slots=None
    ):
        """Ustawia kolaż dla wszystkich (lub wybranych) slotów naraz."""
        if slots is None:
            slots = range(len(self.sloty))
        self.wklej_jeden_obraz_na_kolaz(
            sciezka=sciezka,
            ilosc=ilosc,
            random_cfg=random_cfg,
            source_slot=source_slot,
            margines_proc=margines_proc,
            slots=slots
        )

    def wstaw_wiele_obrazkow(self, lista_sciezek, lista_indeksow):
        """Wstawia wiele obrazów i renderuje raz."""
        for sciezka, indeks in zip(lista_sciezek, lista_indeksow):
            self.wstaw_obrazek(indeks, sciezka)

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
