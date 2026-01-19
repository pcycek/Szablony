import os
import sys
import traceback

# 1. Dynamiczne ustawienie ścieżek
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

def main():
    print("--- Inicjalizacja aplikacji ---")
    try:
        # Importy Tkintera robimy lokalnie, aby mieć pewność, 
        # że nic nie zakłóca ich na starcie
        import tkinter as tk
        from gui.main_window import MainWindow

        print("Tworzenie okna głównego...")
        app = MainWindow()
        
        print("Uruchamianie pętli zdarzeń (mainloop)...")
        app.mainloop()
        
    except ImportError as e:
        print(f"\n[BŁĄD IMPORTU]: Brakuje pliku lub modułu: {e}")
        traceback.print_exc()
    except Exception as e:
        print(f"\n[BŁĄD KRYTYCZNY]: {e}")
        traceback.print_exc()
    finally:
        print("\n--- Program zakończony ---")

if __name__ == "__main__":
    # Małe opóźnienie pomaga Pydroidowi zainicjalizować bufor graficzny
    main()
