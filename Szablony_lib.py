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

        # Odbudowa CACHE dla każdego slotu
        for i, s in enumerate(self.sloty):
            # 1. Reset starych obiektów Pillow (nie da się ich zapisać w JSON)
            s["_cached_img"] = None
            s["_cached_imgs"] = None

            # 2. Jeśli to był KOLAŻ - wywołaj odbudowę kolażu
            if "kolaz" in s:
                self._odbuduj_cache_slotu(i)
            
            # 3. Jeśli to był POJEDYNCZY OBRAZ (ważne!)
            elif s.get("image_path"):
                self.wstaw_obrazek(i, s["image_path"])

        self.render_all()
        return True

    # =====================================================
    # CACHE OBRAZÓW
    # =====================================================
    def _zaladuj_obraz_z_cache(self, sciezka):
        """Ładuje obraz z cache lub z dysku jeśli zmieniony."""
        from paths import napraw_sciezke

        pelna_sciezka = napraw_sciezke(sciezka, "img")
       # pelna_sciezka = OBRAZY_DIR / sciezka
        
        # Używamy os.path.getmtime - to najbezpieczniejsza metoda w Pythonie
        try:
            mtime = os.path.getmtime(pelna_sciezka)
        except Exception:
            mtime = 0 # Jeśli plik nie istnieje, ustawiamy czas na 0

        if sciezka in self.cache_obrazow:
            img, zapisany_mtime = self.cache_obrazow[sciezka]
            if zapisany_mtime == mtime:
                return img

        # Jeśli nie ma w cache lub mtime się nie zgadza:
        try:
            img = Image.open(pelna_sciezka).convert("RGB")
            self.cache_obrazow[sciezka] = (img, mtime)
            return img
        except Exception as e:
            print(f"Nie udało się załadować obrazu: {e}")
            # Zwróć pusty różowy obrazek, żeby było widać, że brakuje pliku
            return Image.new("RGB", (100, 100), "pink")


#    def wyczysc_cache(self):
#        """Czyści cache obrazów."""
#        self.cache_obrazow.clear()

    # =====================================================
    # RENDER
    # =====================================================

    def render_all(self, skala=1.0):
        """Renderuje cały obraz projektu. Skala > 1.0 służy do druku."""
        
        w = int(self.szerokosc * skala)
        h = int(self.wysokosc * skala)

        self.img = Image.new("RGB", (w, h), self.kolor_tla)
        self.draw = ImageDraw.Draw(self.img)

        for i in range(len(self.sloty)):
            self._renderuj_pojedynczy_slot(i, skala)

    def _renderuj_pojedynczy_slot(self, i, skala=1.0):
        s = self.sloty[i]
        base_c = s["coords"]
        
        # Przeliczanie współrzędnych wg skali
        c = [int(val * skala) for val in base_c]
        
        slot_w = c[2] - c[0]
        slot_h = c[3] - c[1]

        # 1. Tło slotu
        if s.get("fill"):
            self.draw.rectangle(c, fill=s["fill"])

        # 2. Obraz
        # Jeśli skala == 1.0, używamy cache (szybko).
        # Jeśli skala > 1.0 (druk), ładujemy oryginał i skalujemy ładnie (wolno).
        
        if skala == 1.0:
            if s.get("_cached_imgs"):
                 for img, x, y in s["_cached_imgs"]:
                     self.img.paste(img, (x, y))
            elif s.get("_cached_img"):
                 img = s["_cached_img"]
                 # Centrowanie w slocie
                 ix = c[0] + (slot_w - img.width) // 2
                 iy = c[1] + (slot_h - img.height) // 2
                 self.img.paste(img, (ix, iy))
        
        else:
            # TRYB HI-RES / DRUK
            # Wersja uproszczona: Skalujemy tylko pojedyncze obrazy. 
            # Kolaże/sytemu cache - tutaj, dla bezpieczeństwa, przeskalujemy bitmapę z cache (mniej ostre, ale działa pewnie).
            # Rozbudowa kolaży na 300DPI wymagałaby przebudowy cache.
            
            if s.get("image_path") and not s.get("kolaz"):
                 # Pojedynczy obraz - ładujemy oryginał dla jakości!
                 path = self._resolve_image_path(s["image_path"])
                 if os.path.exists(path):
                     orig = Image.open(path).convert("RGB")
                     orig.thumbnail((slot_w, slot_h), Image.LANCZOS)
                     
                     ix = c[0] + (slot_w - orig.width) // 2
                     iy = c[1] + (slot_h - orig.height) // 2
                     self.img.paste(orig, (ix, iy))
            
            elif s.get("_cached_imgs") or s.get("_cached_img"):
                 # Fallback dla kolażu lub braku pliku: skalujemy to co mamy w RAM
                 # To nie da jakości 300DPI, ale zachowa układ.
                 pass 
                 # TODO: W przyszłości dodać rebuilding kolażu dla scale > 1
                 # Na razie pomijamy fallback renderowania starego cache na dużym canvasie,
                 # bo byłoby to skomplikowane pozycyjnie. 
                 # Jeśli użytkownik chce 300DPI kolażu, to na razie dostanie puste lub trzeba by przeskalować każdy element.
                 
                 # PROSTE PODEJŚCIE: Skalujemy cache i wklejamy
                 if s.get("_cached_img"):
                     im = s["_cached_img"].copy()
                     im = im.resize((int(im.width*skala), int(im.height*skala)), Image.NEAREST) # Nearest dla szybkości lub Bicubic
                     ix = c[0] + (slot_w - im.width) // 2
                     iy = c[1] + (slot_h - im.height) // 2
                     self.img.paste(im, (ix, iy))
                     
                 if s.get("_cached_imgs"):
                     for sm_img, ox, oy in s["_cached_imgs"]:
                        nm_img = sm_img.resize((int(sm_img.width*skala), int(sm_img.height*skala)))
                        nx = int(ox * skala)
                        ny = int(oy * skala)
                        self.img.paste(nm_img, (nx, ny))


        # 3. Obramowanie
        if s.get("outline"):
            width = int(s.get("outline_width", 1) * skala)
            self.draw.rectangle(c, outline=s["outline"], width=width)

        # 4. Tekst
        if s.get("tekst"):
            self._renderuj_tekst_bezpieczny(i, skala)

    def _pobierz_tekst_ze_zrodla(self, dane_tekstu):
        """
        Parsuje słownik konfiguracji tekstu lub string.
        Zwraca: (treść_stringa, align_string)
        """
        # Domyślne wartości
        text_content = ""
        align = "center"
        
        if isinstance(dane_tekstu, str):
            # Kompatybilność wsteczna - po prostu napis
            return dane_tekstu, "center"
            
        if isinstance(dane_tekstu, dict):
            typ = dane_tekstu.get("typ", "manual")
            align = dane_tekstu.get("align", "center")
            
            if typ == "manual":
                text_content = dane_tekstu.get("value", "")
            
            elif typ == "file":
                filename = dane_tekstu.get("file", "")
                separator = dane_tekstu.get("separator", ",")
                try:
                    idx = int(dane_tekstu.get("index", 0))
                except:
                    idx = 0
                
                # Odczyt z pliku
                from paths import napraw_sciezke
                fpath = napraw_sciezke(filename, "txt")
                
                if fpath and fpath.exists():
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            raw = f.read()
                        # Podział
                        parts = raw.split(separator)
                        if idx < len(parts):
                            text_content = parts[idx].strip()
                        else:
                            text_content = f"[BRAK INDEXU {idx}]"
                    except Exception as e:
                        text_content = f"[BŁĄD PLIKU]"
                else:
                    text_content = "[BRAK PLIKU]"
        
        return text_content, align

    def _renderuj_tekst_bezpieczny(self, i, skala=1.0):
        """
        Renderuje tekst z uwzględnieniem konfiguracji (plik, align) i skali.
        """
        s = self.sloty[i]
        base_c = s["coords"]
        
        # Przeliczanie współrzędnych
        c = [int(val * skala) for val in base_c]
        
        # Pobranie treści i ustawień
        txt, align = self._pobierz_tekst_ze_zrodla(s["tekst"])
        
        if not txt:
            return

        # Obliczanie max boxa
        w = c[2] - c[0]
        h = c[3] - c[1]
        
        max_w = w * 0.95
        max_h = h * 0.95

        font = ImageFont.load_default()
        
        # Zakres szukania czcionki zależny od skali (dla 300DPI > 1.0 potrzebujemy większych fontów)
        start_size = int(100 * skala if skala >= 1 else 100)
        # Przy dużym druku (skala 4) start_size = 400
        
        try:
            for size in range(start_size, 5, -2):
                f = ImageFont.truetype("arial.ttf", size)
                bb = self.draw.textbbox((0, 0), txt, font=f)
                bw = bb[2] - bb[0]
                bh = bb[3] - bb[1]
                
                if bw <= max_w and bh <= max_h:
                    font = f
                    break
        except:
            pass
            
        # Ustalanie pozycji (Anchor)
        # c[0] = lewa, c[1] = góra, c[2] = prawa, c[3] = dół
        cx = (c[0] + c[2]) / 2
        cy = (c[1] + c[3]) / 2
        
        text_x = cx
        text_y = cy
        pil_anchor = "mm" # middle-middle domyślnie
        
        margin_px = int(10 * skala)
        
        if align == "left":
            text_x = c[0] + margin_px
            pil_anchor = "lm" # left-middle
        elif align == "right":
            text_x = c[2] - margin_px
            pil_anchor = "rm" # right-middle
            
        self.draw.text(
            (text_x, text_y),
            txt,
            fill="black",
            anchor=pil_anchor,
            font=font
        )

    def _resolve_image_path(self, sciezka):
        """Pomocnik do pełnej ścieżki obrazu."""
        from paths import napraw_sciezke
        return napraw_sciezke(sciezka, "img")
    def _odbuduj_cache_slotu(self, indeks):
        s = self.sloty[indeks]
    
        if "kolaz" not in s:
            return
    
        k = s["kolaz"]
    
        if k.get("typ") == "jeden_obraz":
            # --- RANDOM ---
            if k.get("random"):
                self.wklej_jeden_obraz_na_kolaz(
                    indeks=indeks,
                    sciezka=k["sciezka"],
                    random_cfg={
                        "min": k.get("min", 1),
                        "max": k.get("max", 1)
                    },
                    margines_proc=k.get("margines_proc", 10)
                )
            # --- STAŁA ILOŚĆ ---
            else:
                self.wklej_jeden_obraz_na_kolaz(
                    indeks=indeks,
                    sciezka=k["sciezka"],
                    ilosc=k.get("ilosc", 1),
                    margines_proc=k.get("margines_proc", 10)
                )

    # =====================================================
    # UNDO REDO
    # =====================================================
    # snspshot projektu
    def _snapshot(self):
        return {
            "szerokosc": self.szerokosc,
            "wysokosc": self.wysokosc,
            "sloty": copy.deepcopy(self.sloty)
        }
    # zapis undo
    def zapisz_undo(self):
        snapshot = self._snapshot()
        if self._undo_stack and snapshot == self._undo_stack[-1]:
            return
        
        
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        
    # undo
    def undo(self):
        if not self._undo_stack:
            return

        self._redo_stack.append(self._snapshot())

        stan = self._undo_stack.pop()
        self.szerokosc = stan["szerokosc"]
        self.wysokosc = stan["wysokosc"]
        self.sloty = stan["sloty"]

        self._odbuduj_cache()
        self.render_all()
        
    # redo
    def redo(self):
        if not self._redo_stack:
            return

        self._undo_stack.append(self._snapshot())

        stan = self._redo_stack.pop()
        self.szerokosc = stan["szerokosc"]
        self.wysokosc = stan["wysokosc"]
        self.sloty = stan["sloty"]

        self._odbuduj_cache()
        self.render_all()
        
    # odbudowa pamieci (obrazki)
    def _odbuduj_cache(self):
        for i, s in enumerate(self.sloty):
            s["_cached_img"] = None
            s["_cached_imgs"] = None

            if "kolaz" in s:
                self._odbuduj_cache_slotu(i)
            elif s.get("image_path"):
                self.wstaw_obrazek(i, s["image_path"])
                
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
                    "_cached_img": None,
                    "tekst": None
                })

        self.render_all()

    def edytuj_slot(self, indeks, **kwargs):
        """Edytuje właściwości slotu."""
        if 0 <= indeks < len(self.sloty):
            self.zapisz_undo()
            self.sloty[indeks].update(kwargs)
            self.render_all()

    def usun_slot(self, indeks):
        """Usuwa slot."""
        if 0 <= indeks < len(self.sloty):
            self.zapisz_undo()
            self.sloty.pop(indeks)
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
        
        # Jeśli druk, to np. skala=4 (dla małych projektów ~800px zrobi się ~3200px)
        scale = 3.0 if skaluj_300dpi else 1.0
        
        for p in pliki:
            try:
                temp_sz = Szablony() # Nowa instancja by nie psuć obecnej
                if temp_sz.otworz_projekt(p.name):
                    # Render
                    temp_sz.render_all(skala=scale)
                    
                    if temp_sz.img:
                        if skaluj_300dpi:
                            out_path = DO_DRUKU_DIR / f"{p.stem}.jpg"
                            # Dla druku 300 DPI warto ustawić DPI w metadanych pliku
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
            
        # Skalujemy x4 dla ~300 DPI (zakładając base ~72-96 DPI)
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
    
        # --- UNDO ---
        self.zapisz_undo()
    
        s = self.sloty[indeks]
        c = s["coords"]
    
        max_w = c[2] - c[0]
        max_h = c[3] - c[1]
    
        # --- ładowanie z cache ---
        img = self._zaladuj_obraz_z_cache(sciezka).copy()
    
        # --- skalowanie (contain) ---
        img.thumbnail((max_w, max_h), Image.LANCZOS)
    
        # --- zapis do slotu ---
        s["_cached_img"] = img
        s["_cached_imgs"] = None
        s["image_path"] = sciezka
    
        # --- czyścimy ewentualny kolaż ---
        if "kolaz" in s:
            del s["kolaz"]
    
        self.render_all()
    import random
    
    def wklej_jeden_obraz_na_kolaz(
        self,
        indeks,
        sciezka,
        ilosc=None,
        random_cfg=None,
        margines_proc=10
    ):
        if not (0 <= indeks < len(self.sloty)):
            return
    
        self.zapisz_undo()
    
        # --- ustalenie ilości ---
        if random_cfg:
            n = random.randint(random_cfg["min"], random_cfg["max"])
        else:
            n = ilosc
    
        if not n or n <= 0:
            return
    
        s = self.sloty[indeks]
        c = s["coords"]
    
        slot_w = c[2] - c[0]
        slot_h = c[3] - c[1]
    
        # --- siatka ---
        ratio = slot_w / slot_h
        cols = max(1, int((n * ratio) ** 0.5))
        rows = (n + cols - 1) // cols
    
        cell_w = slot_w // cols
        cell_h = slot_h // rows
    
        margin_x = int(cell_w * margines_proc / 100)
        margin_y = int(cell_h * margines_proc / 100)
    
        max_w = cell_w - margin_x
        max_h = cell_h - margin_y
    
        base_img = self._zaladuj_obraz_z_cache(sciezka).copy()
        base_img.thumbnail((max_w, max_h), Image.LANCZOS)
    
        cached = []
    
        for idx in range(n):
            r = idx // cols
            c_idx = idx % cols
    
            x = c[0] + c_idx * cell_w + (cell_w - base_img.width) // 2
            y = c[1] + r * cell_h + (cell_h - base_img.height) // 2
    
            cached.append((base_img, x, y))
    
        s["_cached_imgs"] = cached
    
        # --- zapis opisu do JSON ---
        if random_cfg:
            s["kolaz"] = {
                "typ": "jeden_obraz",
                "sciezka": sciezka,
                "random": True,
                "min": random_cfg["min"],
                "max": random_cfg["max"],
                "margines_proc": margines_proc
            }
        else:
            s["kolaz"] = {
                "typ": "jeden_obraz",
                "sciezka": sciezka,
                "random": False,
                "ilosc": n,
                "margines_proc": margines_proc
            }      
       
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

        # Tutaj definiujesz ścieżki (to jest OK)
        img_path = WYNIKI_DIR / f"{self.nazwa_projektu}.jpg"
        json_path = PROJEKTY_DIR / f"{self.nazwa_projektu}.json"

        # --- POPRAWKA 1: Zapis obrazu ---
        if self.img:
            self.img.convert("RGB").save(img_path, "JPEG", quality=95)

        # --- POPRAWKA 2: Użycie json_path zamiast f"{self.nazwa_projektu}.json" ---
        with open(json_path, "w", encoding="utf-8") as f: # <--- TUTAJ była zmiana
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
