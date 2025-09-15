import base64
import io
import re
import time
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pdfminer.high_level import extract_text

from config import MAX_PDF_BYTES
from utils import log_step
from pdf_extract import extract_clave_acceso_from_text, extract_invoice_fields_from_text
from ocr import easyocr_text_from_pdf, HAS_EASYOCR
from riesgo import evaluar_riesgo

router = APIRouter()


class PeticionDoc(BaseModel):
    pdfbase64: str


def is_scanned_image_pdf(pdf_bytes: bytes, extracted_text: str) -> bool:
    text_len = len((extracted_text or "").strip())
    little_text = text_len < 50
    try:
        sample = pdf_bytes[: min(len(pdf_bytes), 2_000_000)]
        img_hits = len(re.findall(rb"/Subtype\s*/Image", sample)) or len(re.findall(rb"/Image\b", sample))
        has_image_objs = img_hits > 0
    except Exception:
        has_image_objs = False
    return little_text and has_image_objs


@router.post("/validar-documento")
async def validar_documento(req: PeticionDoc):
    t_all = time.perf_counter()

    # 1) decode base64
    t0 = time.perf_counter()
    try:
        pdf_bytes = base64.b64decode(req.pdfbase64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="El campo 'pdfbase64' no es base64 válido.")
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail=f"El PDF excede el tamaño máximo permitido ({MAX_PDF_BYTES} bytes).")
    log_step("1) decode base64", t0)

    # 2) texto directo con pdfminer
    try:
        text = extract_text(io.BytesIO(pdf_bytes))
    except Exception:
        text = ""

    # 3) clave de acceso (opcional)
    clave, _ = extract_clave_acceso_from_text(text or "")
    ocr_text = ""
    if is_scanned_image_pdf(pdf_bytes, text or "") and HAS_EASYOCR:
        ocr_text = easyocr_text_from_pdf(pdf_bytes)

    fuente_texto = text if text and not is_scanned_image_pdf(pdf_bytes, text) else (ocr_text or text)

    # 4) extraer campos del PDF
    pdf_fields = extract_invoice_fields_from_text(fuente_texto or "", clave)
    pdf_fields_b64 = base64.b64encode(json.dumps(pdf_fields, ensure_ascii=False).encode("utf-8")).decode("utf-8")

    # 5) análisis de riesgo (sin SRI)
    riesgo = evaluar_riesgo(pdf_bytes, fuente_texto or "", pdf_fields)

    return JSONResponse(
        status_code=200,
        content={
            "sri_verificado": False,
            "mensaje": "Análisis local del documento (sin consulta al SRI).",
            "riesgo": riesgo,
            "claveAccesoDetectada": clave,
            "textoAnalizado": fuente_texto
        }
    )
