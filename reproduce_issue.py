
import sys
sys.path.append(r"c:\Users\Piotr\PycharmProjects\Szablony\ProjektSzablony")
from Szablony_lib import Szablony
import os

def check_grid_gen():
    print("--- Testing Grid Generation ---")
    sz = Szablony()
    sz.nowy_projekt("GridTest", 200, 200)
    
    initial_slots = len(sz.sloty)
    print(f"Initial slots: {initial_slots}")
    
    sz.generuj_siatke(2, 2)
    new_slots = len(sz.sloty)
    print(f"Slots after 2x2 grid: {new_slots}")
    
    if new_slots != 4:
        print("FAIL: Grid generation didn't create 4 slots.")
        return False
        
    if len(sz._render_cache) != 4:
         print(f"FAIL: Render cache has {len(sz._render_cache)} items, expected 4.")
         return False
         
    print("OK: Grid generation looks correct in logic.")
    return True

def check_edit_slot():
    print("\n--- Testing Edit Slot ---")
    sz = Szablony()
    sz.nowy_projekt("EditTest", 200, 200)
    sz.generuj_siatke(1, 1) # 1 slot
    
    # Init text
    sz.edytuj_slot(0, tekst={"typ": "manual", "value": "Old"})
    cache_val = sz._render_cache.get(0, {}).get("final_text")
    print(f"Text before edit: {cache_val}")
    
    if cache_val != "Old":
        print("FAIL: Initial text not set correctly.")
        return False

    # Edit text
    print("Editing slot 0 text to 'New'...")
    sz.edytuj_slot(0, tekst={"typ": "manual", "value": "New"})
    
    cache_val_new = sz._render_cache.get(0, {}).get("final_text")
    print(f"Text after edit: {cache_val_new}")
    
    if cache_val_new != "New":
        print(f"FAIL: Text did not update! (Got: {cache_val_new})")
        return False
        
    print("OK: Edit slot updated cache.")
    return True

if __name__ == "__main__":
    r1 = check_grid_gen()
    r2 = check_edit_slot()
    
    if r1 and r2:
        print("\nLIBRARY LOGIC SEEMS FINE. Issue might be in GUI integration.")
    else:
        print("\nLIBRARY LOGIC FAILED.")
