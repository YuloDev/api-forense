from fastapi import APIRouter
from importlib.metadata import version as pkg_version
from config import MAX_PDF_BYTES, SRI_TIMEOUT

router = APIRouter()

@router.get("/health")
def health():
    def safe_ver(pkg):
        try:
            return pkg_version(pkg)
        except Exception:
            return None
    return {
        "ok": True,
        "mode": "json + easyocr + compare-products + risk",
        "pdfminer": safe_ver("pdfminer.six"),
        "pymupdf": safe_ver("pymupdf"),
        "easyocr": safe_ver("easyocr"),
        "torch": safe_ver("torch"),
        "Pillow": safe_ver("Pillow"),
        "zeep": safe_ver("zeep"),
        "max_pdf_bytes": MAX_PDF_BYTES,
        "sri_timeout_sec": SRI_TIMEOUT,
        "app_version": "1.50.0-risk",
    }
