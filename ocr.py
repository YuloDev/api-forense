import fitz  # PyMuPDF
from PIL import Image
from typing import Optional, Any, List
import numpy as np

from config import EASYOCR_LANGS, EASYOCR_GPU, RENDER_DPI

try:
    import easyocr
    HAS_EASYOCR = True
except Exception:
    HAS_EASYOCR = False

_reader_cache: Optional[Any] = None

def _easyocr_reader():
    """Crea/recupera una instancia de EasyOCR Reader (singleton)."""
    global _reader_cache
    if _reader_cache is None:
        _reader_cache = easyocr.Reader(EASYOCR_LANGS, gpu=EASYOCR_GPU, verbose=False)
    return _reader_cache

def easyocr_text_from_pdf(pdf_bytes: bytes, dpi: int = RENDER_DPI) -> str:
    """Extrae texto de un PDF escaneado usando EasyOCR."""
    if not HAS_EASYOCR:
        return ""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    reader = _easyocr_reader()
    chunks: List[str] = []

    for page in doc:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        np_img = np.array(img)
        try:
            results = reader.readtext(np_img, detail=0, paragraph=True)
            if results:
                chunks.append("\n".join(results))
        except Exception:
            continue
    return "\n".join(chunks).strip()
