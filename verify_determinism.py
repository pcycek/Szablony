
import sys
import time
sys.path.append(r"c:\Users\Piotr\PycharmProjects\Szablony\ProjektSzablony")
from Szablony_lib import Szablony

def verify_determinism():
    sz = Szablony()
    sz.nowy_projekt("DeterminismTest", 200, 200)
    
    # Add a random slot
    sz.sloty.append({
        "coords": [10,10,100,100],
        "tekst": {"typ": "random", "range": "1-100000"}
    })
    
    sz.render_all()
    
    val1 = sz._render_cache[0]["value"]
    print(f"Run 1 Value: {val1}")
    
    # Call render_all multiple times - should NOT change
    sz.render_all()
    val2 = sz._render_cache[0]["value"]
    print(f"Run 2 Value: {val2}")
    
    if val1 != val2:
        print("FAIL: Value changed on simple re-render!")
        return

    # Modify UNRELATED slot - should NOT change
    sz.sloty.append({
        "coords": [0,0,10,10],
        "tekst": "Static"
    })
    sz.render_all()
    val3 = sz._render_cache[0]["value"]
    print(f"Run 3 Value (after adding slot): {val3}")
    
    if val1 != val3:
        print("FAIL: Value changed after unrelated modification!")
        return
        
    # Force Refresh
    print("Forcing refresh...")
    sz.prepare_render_data(force=True)
    val4 = sz._render_cache[0]["value"]
    print(f"Run 4 Value (Forced): {val4}")
    
    if val1 == val4:
        print("WARNING: Value is same after force refresh (1 in 100000 chance or bug?)")
    else:
        print("OK: Value changed after force refresh.")
        
    print("Determinism test PASSED.")

if __name__ == "__main__":
    verify_determinism()
