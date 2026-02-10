
import sys
import os

# Add project root to path
sys.path.append(r"c:\Users\Piotr\PycharmProjects\Szablony\ProjektSzablony")

from Szablony_lib import Szablony

def test_random_slot():
    sz = Szablony()
    sz.nowy_projekt("Test", 100, 100)
    
    # Add a slot
    sz.sloty.append({
        "coords": [0, 0, 100, 100],
        "tekst": {
            "typ": "random",
            "range": "10-20",
            "align": "center"
        }
    })
    
    print("Testing random generation (10-20):")
    values = []
    for i in range(5):
        # We need to access the private logic or just inspect the rendered result logic
        # render_all calls _pobierz_tekst_ze_zrodla internally.
        # Let's call _pobierz_tekst_ze_zrodla directly to verify logic
        txt, align = sz._pobierz_tekst_ze_zrodla(sz.sloty[0]["tekst"])
        print(f"Attempt {i+1}: {txt}")
        values.append(int(txt))
        
    if all(10 <= v <= 20 for v in values):
        print("SUCCESS: All values in range.")
    else:
        print("FAILURE: Values out of range.")
        
    if len(set(values)) > 1:
        print("SUCCESS: Values vary (randomness works).")
    else:
        print("WARNING: Values are identical (might be bad luck or seed issue, but unlikely for 5 tries 10-20).")

if __name__ == "__main__":
    test_random_slot()
