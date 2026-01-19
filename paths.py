import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROJEKTY_DIR = DATA_DIR / "projekty"
OBRAZY_DIR = DATA_DIR / "obrazy"
WYNIKI_DIR = DATA_DIR / "wyniki"
TEKSTY_DIR = DATA_DIR / "tekst"
DO_DRUKU_DIR = DATA_DIR / "do_druku"

# Tworzenie folderów
for d in [PROJEKTY_DIR, OBRAZY_DIR, WYNIKI_DIR, TEKSTY_DIR, DO_DRUKU_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def napraw_sciezke(nazwa, typ="json"):
    """
    Dodaje rozszerzenie i zwraca pełną ścieżkę Path.
    typ: "json" dla projektów, "img" dla obrazków, "txt" dla tekstów.
    """
    if not nazwa:
        return None
    
    if typ == "json":
        rozszerzenie = ".json"
        katalog = PROJEKTY_DIR
    elif typ == "txt":
        rozszerzenie = ".txt"
        katalog = TEKSTY_DIR
    else:
        rozszerzenie = ".jpg"
        katalog = OBRAZY_DIR
    
    # Dodaj rozszerzenie jeśli brak kropki
    if "." not in str(nazwa):
        nazwa = f"{nazwa}{rozszerzenie}"
    
    return katalog / nazwa
