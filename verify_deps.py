
import sys
import os
import random

# Add project root to path
sys.path.append(r"c:\Users\Piotr\PycharmProjects\Szablony\ProjektSzablony")

from Szablony_lib import Szablony

def test_dependencies():
    sz = Szablony()
    sz.nowy_projekt("TestDeps", 100, 100)
    
    # Slot 0: Random 50-100
    sz.sloty.append({
        "coords": [0,0,10,10],
        "tekst": {"typ": "random", "range": "50-100"}
    })
    
    # Slot 1: Dependent Smaller than 0 (Limit 10)
    sz.sloty.append({
        "coords": [0,0,10,10],
        "tekst": {"typ": "random_dependent", "source": 0, "relation": "smaller", "limit": 10}
    })
    
    # Slot 2: Dependent Larger than 0 (Limit 200)
    sz.sloty.append({
        "coords": [0,0,10,10],
        "tekst": {"typ": "random_dependent", "source": 0, "relation": "larger", "limit": 200}
    })
    
    # Slot 3: Collage dependent on Slot 1 (count)
    sz.sloty.append({
        "coords": [0,0,100,100],
        "kolaz": {"typ": "jeden_obraz", "sciezka": "test.jpg", "source_slot": 1}
    })

    print("--- Running Render All (calculates dependencies) ---")
    sz.render_all() # This should trigger calculation
    
    # Access internal cache
    # Structure: index -> { "value": int, "final_text": str, "collage_items": [...] }
    cache = sz._render_cache
    print(f"Calculated Cache Keys: {list(cache.keys())}")
    
    def get_val(idx):
        if idx in cache and "value" in cache[idx]:
            return cache[idx]["value"]
        return None
    
    v0 = get_val(0)
    v1 = get_val(1)
    v2 = get_val(2)
    
    # Verification
    if v0 is None:
        print("FAIL: Slot 0 not calculated")
        return
        
    print(f"Slot 0 (Random): {v0}")
    
    if v1 is not None:
        print(f"Slot 1 (Smaller than {v0}, limit 10): {v1}")
        if 10 <= v1 <= v0:
            print("  -> OK (Correct range)")
        else:
            print("  -> FAIL (Value out of range)")
    else:
        print("FAIL: Slot 1 not calculated")

    if v2 is not None:
        print(f"Slot 2 (Larger than {v0}, limit 200): {v2}")
        if v0 <= v2 <= 200:
            print("  -> OK (Correct range)")
        else:
            print("  -> FAIL (Value out of range)")
    else:
        print("FAIL: Slot 2 not calculated")
        
    # Check Collage count
    s3_cache = cache.get(3, {})
    items = s3_cache.get("collage_items", [])
    
    # Collage logic now calculates layout in prepare_render_data
    # and stores it in "collage_items". 
    # Logic: N = loop count.
    # Note: "test.jpg" likely doesn't exist, so _zaladuj_obraz_z_cache returns pink placeholder (100x100).
    # Logic will still generate N items.
    
    collage_count = n = 1
    if "collage_data" in s3_cache:
         collage_count = s3_cache["collage_data"]["n"]
    
    print(f"Slot 3 Collage Count Target: {collage_count} (Expected: {v1})")
    
    # Items list might be empty if slot size is too small for even 1 item?
    # 100x100 slot, 100x100 img. 1 item should fit.
    print(f"Slot 3 Generated Items: {len(items)}")
    
    if collage_count == v1:
        print("  -> OK (Count matches dependency)")
    else:
        print("  -> FAIL (Count mismatch)")

    print("\n--- Test Order Independence ---")
    # Slot 4 depends on Slot 5. Slot 5 is Random 100-200.
    sz.sloty.append({
        "coords": [0,0,10,10],
        "tekst": {"typ": "random_dependent", "source": 5, "relation": "smaller", "limit": 0}
    })
    sz.sloty.append({
        "coords": [0,0,10,10],
        "tekst": {"typ": "random", "range": "100-200"}
    })
    
    sz.render_all() # Should iterate enough times
    
    v4 = get_val(4)
    v5 = get_val(5)
    print(f"Slot 5 (Random): {v5}")
    print(f"Slot 4 (Dependent on 5): {v4}")
    
    if v4 is not None and v5 is not None and v4 <= v5:
        print("  -> OK (Order resolved correctly)")
    else:
        print("  -> FAIL (Dependencies failed)")

if __name__ == "__main__":
    test_dependencies()
