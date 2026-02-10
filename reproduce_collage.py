
import sys
sys.path.append(r"c:\Users\Piotr\PycharmProjects\Szablony\ProjektSzablony")
from Szablony_lib import Szablony
import os

def test_fixed_collage_quantity():
    print("--- Testing Fixed Collage Quantity ---")
    sz = Szablony()
    sz.nowy_projekt("CollageTest", 200, 200)
    
    # 1. Create a slot
    sz.generuj_siatke(1, 1) # Slot 0
    
    # 2. Set collage with quantity 5
    print("Setting collage with quantity 5...")
    sz.wklej_jeden_obraz_na_kolaz(0, "test.jpg", ilosc=5)
    
    # 3. Verify JSON data
    s = sz.sloty[0]
    k = s.get("kolaz", {})
    print(f"Collage Config in Slot: {k}")
    
    if k.get("ilosc") != 5:
        print(f"FAIL: 'ilosc' in config is {k.get('ilosc')}, expected 5")
        return False
        
    if k.get("typ") != "jeden_obraz":
        print("FAIL: Wrong collage type")
        return False

    # 4. Verify Render Cache
    cache = sz._render_cache.get(0, {})
    items = cache.get("collage_items", [])
    print(f"Generated items in cache: {len(items)}")
    
    if len(items) != 5:
        print(f"FAIL: Generated {len(items)} items, expected 5")
        return False
        
    print("OK: Fixed quantity collage logic works in library.")
    return True

if __name__ == "__main__":
    if test_fixed_collage_quantity():
        print("\nLibrary checks out. Issue is likely in GUI/Dialog.")
    else:
        print("\nLibrary logic FAILED.")
