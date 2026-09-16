import io
import os
from pathlib import Path
from typing import List, Union, Optional, Tuple, Dict, Any
from PIL import Image, ImageOps
try:
    import pymupdf as fitz
except ImportError:
    import fitz


class PDFManager:
    """
    Klasa do kompleksowego tworzenia, edycji i manipulacji plikami PDF.
    Umożliwia:
    - tworzenie PDF z listy obrazów (A4, dopasowane lub oryginalne wymiary),
    - otwieranie istniejących plików PDF,
    - manewrowanie stronami (przenoszenie strony X na pozycję Y, np. 1 na 5),
    - usuwanie, duplikowanie i obracanie stron (90, 180, 270 st.),
    - dołączanie kolejnych obrazów i scalanie innych plików PDF,
    - generowanie miniatur i podglądów stron jako obiekty PIL.Image,
    - zapisywanie zmodyfikowanego dokumentu.
    """

    # Standardowe wymiary A4 w punktach (72 punkty = 1 cal)
    A4_WIDTH = 595.276
    A4_HEIGHT = 841.890

    def __init__(self, pdf_path_or_doc: Optional[Union[str, Path, fitz.Document]] = None):
        self.doc: fitz.Document = fitz.open()
        self.source_path: Optional[Path] = None

        if pdf_path_or_doc is not None:
            if isinstance(pdf_path_or_doc, fitz.Document):
                self.doc = pdf_path_or_doc
            else:
                self.load_pdf(pdf_path_or_doc)

    def close(self):
        """Zamyka otwarty dokument fitz."""
        if self.doc and not self.doc.is_closed:
            self.doc.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # --- TWORZENIE I WCZYTYWANIE ---

    def load_pdf(self, pdf_path: Union[str, Path]):
        """Wczytuje istniejący plik PDF z dysku."""
        p = Path(pdf_path)
        if not p.exists():
            raise FileNotFoundError(f"Plik PDF nie istnieje: {p}")
        self.close()
        self.doc = fitz.open(str(p))
        self.source_path = p

    @classmethod
    def from_images(
        cls,
        image_paths: List[Union[str, Path, Image.Image]],
        page_size: str = "A4",
        orientation: str = "auto",
        margin_pt: float = 0.0
    ) -> "PDFManager":
        """
        Tworzy nową instancję PDFManager i dodaje do niej podaną listę obrazów jako kolejne strony.
        """
        manager = cls()
        manager.add_images(image_paths, page_size=page_size, orientation=orientation, margin_pt=margin_pt)
        return manager

    def add_image_page(
        self,
        img_or_path: Union[str, Path, Image.Image],
        target_index: Optional[int] = None,
        page_size: str = "A4",
        orientation: str = "auto",
        margin_pt: float = 0.0
    ) -> int:
        """
        Dodaje pojedynczy obraz jako nową stronę PDF.
        target_index: indeks docelowy (0-based). Jeśli None, dodaje na końcu.
        page_size: "A4" lub "fit_image" (wymiar strony = wymiar obrazu w pt).
        orientation: "auto" (zależnie od proporcji obrazu), "portrait" lub "landscape".
        margin_pt: margines w punktach (domyślnie 0).
        Zwraca indeks dodanej strony (0-based).
        """
        # Przygotowanie danych binarnych i wymiarów obrazu z uwzględnieniem obrotu EXIF
        if isinstance(img_or_path, Image.Image):
            pil_img = ImageOps.exif_transpose(img_or_path).convert("RGB")
        else:
            p = Path(img_or_path)
            if not p.exists():
                raise FileNotFoundError(f"Nie znaleziono obrazu: {p}")
            with Image.open(p) as tmp_img:
                pil_img = ImageOps.exif_transpose(tmp_img).convert("RGB")

        img_w, img_h = pil_img.size

        # Ustalanie wymiarów i orientacji strony (automatycznie: poziomo gdy szerokość > wysokość)
        is_landscape = (img_w > img_h) if orientation == "auto" else (orientation == "landscape")
        if page_size.upper() == "A4":
            pw = max(self.A4_WIDTH, self.A4_HEIGHT) if is_landscape else min(self.A4_WIDTH, self.A4_HEIGHT)
            ph = min(self.A4_WIDTH, self.A4_HEIGHT) if is_landscape else max(self.A4_WIDTH, self.A4_HEIGHT)
        else:
            # fit_image - rozmiar strony dokładnie taki jak obraz (zakładając 72 DPI)
            pw = float(img_w)
            ph = float(img_h)

        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=95)
        img_bytes = buf.getvalue()

        # Wstawienie pustej strony
        idx = target_index if (target_index is not None and 0 <= target_index <= len(self.doc)) else len(self.doc)
        page = self.doc.new_page(pno=idx, width=pw, height=ph)

        # Obliczenie prostokąta wstawienia obrazu z zachowaniem proporcji i marginesów
        avail_w = max(10.0, pw - 2 * margin_pt)
        avail_h = max(10.0, ph - 2 * margin_pt)

        scale = min(avail_w / img_w, avail_h / img_h)
        dest_w = img_w * scale
        dest_h = img_h * scale

        x0 = margin_pt + (avail_w - dest_w) / 2.0
        y0 = margin_pt + (avail_h - dest_h) / 2.0
        rect = fitz.Rect(x0, y0, x0 + dest_w, y0 + dest_h)

        # Wstawienie obrazu na stronę
        page.insert_image(rect, stream=img_bytes)
        return idx

    def add_images(
        self,
        image_paths: List[Union[str, Path, Image.Image]],
        target_index: Optional[int] = None,
        page_size: str = "A4",
        orientation: str = "auto",
        margin_pt: float = 0.0
    ):
        """Dodaje listę obrazów jako kolejne strony PDF."""
        current_target = target_index
        for img in image_paths:
            self.add_image_page(
                img,
                target_index=current_target,
                page_size=page_size,
                orientation=orientation,
                margin_pt=margin_pt
            )
            if current_target is not None:
                current_target += 1

    def merge_pdf(self, other_pdf_path: Union[str, Path], target_index: Optional[int] = None):
        """Dołącza wszystkie strony z innego pliku PDF na pozycji target_index (lub na końcu)."""
        p = Path(other_pdf_path)
        if not p.exists():
            raise FileNotFoundError(f"Nie znaleziono pliku PDF do scalenia: {p}")

        with fitz.open(str(p)) as other_doc:
            if target_index is None or target_index >= len(self.doc):
                self.doc.insert_pdf(other_doc)
            else:
                idx = max(0, target_index)
                self.doc.insert_pdf(other_doc, start_at=idx)

    # --- MANEWROWANIE STRONAMI (REORDERING, MOVING, ROTATING) ---

    def move_page(self, from_idx: int, to_idx: int, one_based: bool = False):
        """
        Przenosi stronę z pozycji from_idx na pozycję to_idx.
        np. ze strony 1 na stronę 5 (przy one_based=True).
        """
        total = len(self.doc)
        if total == 0:
            return

        f = (from_idx - 1) if one_based else from_idx
        t = (to_idx - 1) if one_based else to_idx

        f = max(0, min(total - 1, f))
        t = max(0, min(total - 1, t))

        if f == t:
            return

        # Utwórz listę aktualnych indeksów [0, 1, 2, 3, ...]
        order = list(range(total))
        # Usuń przenoszony element i wstaw go na nową pozycję
        item = order.pop(f)
        order.insert(t, item)

        # Zastosuj nową kolejność stron w dokumencie
        self.reorder_pages(order)

    def reorder_pages(self, new_order: List[int]):
        """
        Układa strony dokumentu według zadanej listy indeksów (0-based).
        np. [0, 2, 1, 3] zamienia miejscami stronę 2 i 3.
        """
        total = len(self.doc)
        if len(new_order) != total:
            raise ValueError(f"Długość nowej kolejności ({len(new_order)}) nie zgadza się z liczbą stron ({total}).")

        # PyMuPDF posiada natywną metodę select, która idealnie i bezstratnie przestawia strony
        self.doc.select(new_order)

    def move_page_up(self, idx: int, one_based: bool = False) -> int:
        """Przesuwa stronę o jedną pozycję wcześniej (w górę). Zwraca nową pozycję."""
        cur = (idx - 1) if one_based else idx
        if cur > 0:
            self.move_page(cur, cur - 1, one_based=False)
            return (cur) if one_based else (cur - 1)
        return idx

    def move_page_down(self, idx: int, one_based: bool = False) -> int:
        """Przesuwa stronę o jedną pozycję później (w dół). Zwraca nową pozycję."""
        cur = (idx - 1) if one_based else idx
        if cur < len(self.doc) - 1:
            self.move_page(cur, cur + 1, one_based=False)
            return (cur + 2) if one_based else (cur + 1)
        return idx

    def delete_page(self, idx: int, one_based: bool = False):
        """Usuwa stronę o podanym indeksie."""
        p = (idx - 1) if one_based else idx
        if 0 <= p < len(self.doc):
            self.doc.delete_page(p)

    def delete_pages(self, indices: List[int], one_based: bool = False):
        """Usuwa wiele stron o podanych indeksach."""
        sorted_indices = sorted(indices, reverse=True)
        for idx in sorted_indices:
            self.delete_page(idx, one_based=one_based)

    def rotate_page(self, idx: int, angle: int = 90, one_based: bool = False):
        """Obraca wskazaną stronę o podany kąt (np. 90, 180, 270, -90)."""
        p = (idx - 1) if one_based else idx
        if 0 <= p < len(self.doc):
            page = self.doc[p]
            page.set_rotation((page.rotation + angle) % 360)

    def toggle_page_orientation(self, idx: int, one_based: bool = False):
        """Przełącza orientację wskazanej strony (pionowa <-> pozioma)."""
        self.rotate_page(idx, angle=90, one_based=one_based)

    def auto_orient_pages(self, indices: Optional[List[int]] = None, one_based: bool = False) -> int:
        """
        Automatycznie dopasowuje orientację stron (pionowa / pozioma)
        w zależności od wymiarów znajdujących się na nich obrazów.
        - Jeśli obraz jest poziomy (szerokość > wysokość), strona staje się pozioma.
        - Jeśli obraz jest pionowy (wysokość >= szerokość), strona staje się pionowa.
        Zwraca liczbę obróconych stron.
        """
        total = len(self.doc)
        if total == 0:
            return 0

        if indices is not None:
            target_indices = [(i - 1 if one_based else i) for i in indices]
        else:
            target_indices = list(range(total))

        changed_count = 0
        for p in target_indices:
            if not (0 <= p < total):
                continue
            page = self.doc[p]
            imgs = page.get_images()
            if not imgs:
                continue

            try:
                # Wymiary głównego obrazu ze strony
                xref = imgs[0][0]
                img_dict = self.doc.extract_image(xref)
                img_w = img_dict.get("width", 0)
                img_h = img_dict.get("height", 0)
                if img_w <= 0 or img_h <= 0:
                    continue

                img_is_landscape = (img_w > img_h)
                # Aktualna widoczna orientacja strony (page.rect uwzględnia rotation)
                page_is_landscape = (page.rect.width > page.rect.height)

                if img_is_landscape != page_is_landscape:
                    page.set_rotation((page.rotation + 90) % 360)
                    changed_count += 1
            except Exception:
                continue

        return changed_count

    def duplicate_page(self, idx: int, one_based: bool = False) -> int:
        """Duplikuje stronę o wskazanym indeksie i wstawia ją bezpośrednio po niej."""
        p = (idx - 1) if one_based else idx
        if 0 <= p < len(self.doc):
            # Tworzymy tymczasowy dokument z wybraną stroną i wstawiamy go
            temp_doc = fitz.open()
            temp_doc.insert_pdf(self.doc, from_page=p, to_page=p)
            self.doc.insert_pdf(temp_doc, start_at=p + 1)
            temp_doc.close()
            return p + 1
        return -1

    # --- METADANE I PODGLĄDY ---

    def get_page_count(self) -> int:
        """Zwraca łączną liczbę stron dokumentu."""
        return len(self.doc)

    def get_pages_info(self) -> List[Dict[str, Any]]:
        """Zwraca listę słowników z informacjami o każdej stronie."""
        info = []
        for i, page in enumerate(self.doc):
            rect = page.rect
            info.append({
                "index": i,
                "page_number": i + 1,
                "width": round(rect.width, 1),
                "height": round(rect.height, 1),
                "rotation": page.rotation,
                "is_landscape": rect.width > rect.height
            })
        return info

    def get_page_thumbnail(self, idx: int, max_size: Tuple[int, int] = (160, 220), one_based: bool = False) -> Optional[Image.Image]:
        """
        Renderuje miniaturę wybranej strony jako obiekt PIL.Image.
        Dopasowuje wymiary miniatury do max_size z zachowaniem proporcji.
        """
        p = (idx - 1) if one_based else idx
        if not (0 <= p < len(self.doc)):
            return None

        page = self.doc[p]
        rect = page.rect
        if rect.width <= 0 or rect.height <= 0:
            return None

        # Obliczamy skalę matrycy dla miniatury
        scale = min(max_size[0] / rect.width, max_size[1] / rect.height)
        scale = max(0.1, min(3.0, scale))

        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img

    def get_page_preview(self, idx: int, dpi: int = 150, one_based: bool = False) -> Optional[Image.Image]:
        """Renderuje duży podgląd strony o zadanej rozdzielczości DPI (domyślnie 150)."""
        p = (idx - 1) if one_based else idx
        if not (0 <= p < len(self.doc)):
            return None

        page = self.doc[p]
        # Standardowa rozdzielczość PDF to 72 DPI
        scale = dpi / 72.0
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img

    # --- ZAPIS ---

    def save(self, output_path: Union[str, Path], garbage: int = 3, deflate: bool = True):
        """
        Zapisuje plik PDF do wskazanej ścieżki.
        garbage=3 usuwa nieużywane obiekty i optymalizuje rozmiar pliku.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(out_p), garbage=garbage, deflate=deflate)
