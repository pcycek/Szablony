
from Szablony_lib import Szablony
import os

def test_text_fit():
    sz = Szablony()
    # Create a small project like a slot
    sz.nowy_projekt("Test", 200, 100)
    
    # Add a slot that covers most of the area
    sz.sloty.append({
        "coords": [0, 0, 200, 100],
        "fill": "white",
        "outline": "black",
        "tekst": {
            "value": "BardzoDlugiTekstKtoryNormalnieByWystawal",
            "align": "center"
        }
    })
    
    # Render
    sz.render_all()
    
    # Save
    if not os.path.exists("wyniki"):
        os.makedirs("wyniki")
    
    sz.img.save("wyniki/test_text_fit.jpg")
    print("Test image saved to wyniki/test_text_fit.jpg")

    # Test with left align and margin
    sz = Szablony()
    sz.nowy_projekt("TestLeft", 200, 100)
    sz.sloty.append({
        "coords": [0, 0, 200, 100],
        "fill": "white",
        "outline": "black",
        "tekst": {
            "value": "TekstZLewej",
            "align": "left"
        }
    })
    sz.render_all()
    sz.img.save("wyniki/test_text_left.jpg")
    print("Test image saved to wyniki/test_text_left.jpg")

    # Test tiny slot
    sz = Szablony()
    sz.nowy_projekt("TestTiny", 200, 20) # 20px height
    sz.sloty.append({
        "coords": [0, 0, 200, 20],
        "fill": "white",
        "outline": "black",
        "tekst": {
            "value": "MalyTekst",
            "align": "center"
        }
    })
    sz.render_all()
    sz.img.save("wyniki/test_text_tiny.jpg")
    print("Test image saved to wyniki/test_text_tiny.jpg")

if __name__ == "__main__":
    test_text_fit()
