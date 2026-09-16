import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROJEKTY_DIR = DATA_DIR / "projekty"
OBRAZY_DIR = DATA_DIR / "obrazy"
OBRAZY_STALE_DIR = DATA_DIR / "obrazy_stałe"
WYNIKI_DIR = DATA_DIR / "wyniki"
TEKSTY_DIR = DATA_DIR / "tekst"
DO_DRUKU_DIR = DATA_DIR / "do_druku"
SKRYPTY_DIR = DATA_DIR / "skrypty"

# Tworzenie folderów
for d in [PROJEKTY_DIR, OBRAZY_DIR, OBRAZY_STALE_DIR, WYNIKI_DIR, TEKSTY_DIR, DO_DRUKU_DIR, SKRYPTY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def napraw_sciezke(nazwa, typ="json", source="obrazy"):
    """
    Dodaje rozszerzenie i zwraca pełną ścieżkę Path.
    typ: "json" dla projektów, "img" dla obrazków, "txt" dla tekstów.
    source: "obrazy" (data/obrazy) lub "obrazy_stale" / "stale" (data/obrazy_stałe).
    """
    if not nazwa:
        return None
    
    if isinstance(nazwa, Path):
        return nazwa
    
    p = Path(nazwa)
    if p.is_file():
        return p
    
    nazwa_str = str(nazwa).replace("\\", "/")

    if typ == "json":
        rozszerzenie = ".json"
        katalog = PROJEKTY_DIR
    elif typ == "txt":
        rozszerzenie = ".txt"
        katalog = TEKSTY_DIR
    else:
        rozszerzenie = ".jpg"
        if source in ("obrazy_stale", "stale", "obrazy_stałe") or nazwa_str.startswith("obrazy_stale/") or nazwa_str.startswith("obrazy_stałe/"):
            katalog = OBRAZY_STALE_DIR
            if nazwa_str.startswith("obrazy_stale/"):
                nazwa_str = nazwa_str.split("/", 1)[1]
            elif nazwa_str.startswith("obrazy_stałe/"):
                nazwa_str = nazwa_str.split("/", 1)[1]
        else:
            katalog = OBRAZY_DIR
            if nazwa_str.startswith("obrazy/"):
                nazwa_str = nazwa_str.split("/", 1)[1]
    
    # Dodaj rozszerzenie jeśli brak kropki w nazwie pliku
    if "." not in Path(nazwa_str).name:
        nazwa_str = f"{nazwa_str}{rozszerzenie}"
    
    sciezka_wynikowa = katalog / nazwa_str

    # Bezpieczny fallback dla obrazów jeśli plik nie istnieje w domyślnym katalogu
    if typ == "img" and not sciezka_wynikowa.exists() and source in ("obrazy", None):
        alt = OBRAZY_STALE_DIR / nazwa_str
        if alt.exists():
            return alt

    return sciezka_wynikowa
