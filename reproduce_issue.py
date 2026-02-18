import os
from Szablony_lib import Szablony
from paths import TEKSTY_DIR

# 1. Create a test text file in the correct directory (TEKSTY_DIR)
test_file_name = "repro_test.txt"
test_content = "Hello,World,Test"
test_path = TEKSTY_DIR / test_file_name

with open(test_path, "w", encoding="utf-8") as f:
    f.write(test_content)

print(f"Created test file at: {test_path}")

# 2. Initialize Szablony and attempt to load text
sz = Szablony()
sz.nowy_projekt("TestProject", 100, 100)
sz.generuj_siatke(1, 1)

# Try to load the text.
# The issue is suspected to be that it looks in OBRAZY_DIR instead of TEKSTY_DIR
print("Attempting to load text from file...")
sz.wstaw_tekst_z_pliku(0, test_file_name, separator=",", index=0)

# 3. Check the result
# Access the render cache to see what happened
sz.prepare_render_data()
cache = sz._render_cache.get(0, {})
loaded_text = cache.get("final_text", "N/A")

print(f"Loaded text: '{loaded_text}'")

if loaded_text == "[ERR]":
    print("FAILURE: Text loaded as [ERR]. Issue reproduced.")
elif loaded_text == "Hello":
    print("SUCCESS: Text loaded correctly.")
else:
    print(f"UNEXPECTED: Loaded '{loaded_text}'")

# Cleanup
if os.path.exists(test_path):
    os.remove(test_path)
