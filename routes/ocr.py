import base64
import io
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import MAX_PDF_BYTES
from utils import log_step
from pdf_extract import extract_clave_acceso_from_text, extract_invoice_fields_from_text
from riesgo import evaluar_riesgo_factura
from sri import sri_autorizacion_por_clave, parse_autorizacion_response, factura_xml_to_json
from ocr import easyocr_text_from_pdf, HAS_EASYOCR

router = APIRouter()


class OCRRequest(BaseModel):
    """Modelo para la solicitud de OCR de PDF."""
    pdf_base64: str
    lang: Optional[str] = "spa"
    oem: Optional[int] = 3
    psm: Optional[int] = 3
    dpi: Optional[int] = 300
    force_ocr: Optional[bool] = False
    min_embedded_chars: Optional[int] = 40


class OCRResponse(BaseModel):
    """Modelo para la respuesta del OCR."""
    success: bool
    text: str
    pages: int
    method_per_page: list
    total_chars: int
    processing_time: float
    error: Optional[str] = None


def has_extractable_text(page, min_chars=40):
    """Quick check: try to extract text with the PDF's embedded text layer."""
    txt = page.get_text("text") or ""
    return len(txt.strip()) >= min_chars, txt


def page_to_image(page, zoom=2.0, colorspace="rgb"):
    """Render a PDF page to a PIL Image with a given zoom factor."""
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB if colorspace == "rgb" else None, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def ocr_page(page, lang="spa", psm=3, oem=3, dpi_hint=300):
    """OCR a single page using pytesseract with basic config."""
    # Render page to a PIL image for OCR
    # A zoom of around 2.0 yields ~ 144 DPI * 2 = ~288 DPI effective.
    # We pass a dpi hint to tesseract via config (not guaranteed to be used).
    image = page_to_image(page, zoom=2.0, colorspace="rgb")
    config = f"--oem {oem} --psm {psm} -c user_defined_dpi={dpi_hint}"
    text = pytesseract.image_to_string(image, lang=lang, config=config)
    return text


def process_pdf_ocr(pdf_bytes: bytes, 
                   lang="spa", 
                   oem=3, 
                   psm=3, 
                   dpi_hint=300, 
                   force_ocr=False, 
                   min_embedded_chars=40):
    """
    Procesar un PDF para extraer texto usando OCR o texto embebido.
    
    Args:
        pdf_bytes: Bytes del PDF
        lang: Idioma para Tesseract (ej: "spa", "eng", "spa+eng")
        oem: Tesseract OEM mode (0-3)
        psm: Tesseract PSM mode (0-13)
        dpi_hint: DPI hint para Tesseract
        force_ocr: Forzar OCR incluso si hay texto embebido
        min_embedded_chars: Mínimo de caracteres para considerar texto embebido
    
    Returns:
        dict: Resultado del procesamiento
    """
    start_time = time.time()
    
    try:
        # Abrir PDF desde bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        all_text = []
        method_per_page = []
        
        for i in range(len(doc)):
            page = doc[i]
            
            # Verificar si hay texto embebido utilizable
            embedded_ok, embedded_txt = has_extractable_text(page, min_chars=min_embedded_chars)
            
            if embedded_ok and not force_ocr:
                page_text = embedded_txt
                method = "embedded"
            else:
                page_text = ocr_page(page, lang=lang, psm=psm, oem=oem, dpi_hint=dpi_hint)
                method = "ocr"
            
            method_per_page.append({
                "page": i + 1,
                "method": method,
                "chars": len(page_text.strip())
            })
            
            # Separator entre páginas
            sep = f"\n\n---- PÁGINA {i+1}/{len(doc)} ({method}) ----\n\n"
            all_text.append(sep + page_text.strip())
        
        doc.close()
        
        full_text = "\n".join(all_text).strip()
        processing_time = time.time() - start_time
        
        return {
            "success": True,
            "text": full_text,
            "pages": len(method_per_page),
            "method_per_page": method_per_page,
            "total_chars": len(full_text),
            "processing_time": processing_time,
            "error": None
        }
        
    except Exception as e:
        processing_time = time.time() - start_time
        return {
            "success": False,
            "text": "",
            "pages": 0,
            "method_per_page": [],
            "total_chars": 0,
            "processing_time": processing_time,
            "error": str(e)
        }


@router.post("/ocr-pdf", response_model=OCRResponse)
async def ocr_pdf_endpoint(request: OCRRequest):
    """
    Endpoint para realizar OCR en un PDF.
    
    Puede usar texto embebido del PDF o OCR con Tesseract según la configuración.
    Soporta múltiples idiomas y configuraciones de Tesseract.
    """
    t_start = time.time()
    
    try:
        # Validar y decodificar el PDF
        if not request.pdf_base64:
            raise HTTPException(status_code=400, detail="pdf_base64 es requerido")
        
        try:
            pdf_bytes = base64.b64decode(request.pdf_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error decodificando base64: {str(e)}")
        
        # Validar tamaño del PDF
        if len(pdf_bytes) > MAX_PDF_BYTES:
            raise HTTPException(
                status_code=413, 
                detail=f"PDF demasiado grande. Máximo: {MAX_PDF_BYTES / (1024*1024):.1f} MB"
            )
        
        log_step("1) Validación inicial", t_start)
        
        # Verificar que Tesseract esté disponible
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Tesseract OCR no está instalado o no está disponible en el PATH. "
                       f"Instala Tesseract desde: https://github.com/UB-Mannheim/tesseract/wiki "
                       f"Error: {str(e)}"
            )
        
        log_step("2) Verificación Tesseract", t_start)
        
        # Procesar el PDF
        result = process_pdf_ocr(
            pdf_bytes=pdf_bytes,
            lang=request.lang,
            oem=request.oem,
            psm=request.psm,
            dpi_hint=request.dpi,
            force_ocr=request.force_ocr,
            min_embedded_chars=request.min_embedded_chars
        )
        
        log_step("3) Procesamiento OCR completo", t_start)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=f"Error procesando PDF: {result['error']}")
        
        return OCRResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/ocr-pdf-upload")
async def ocr_pdf_upload_endpoint(
    file: UploadFile = File(...),
    lang: str = "spa",
    oem: int = 3,
    psm: int = 3,
    dpi: int = 300,
    force_ocr: bool = False,
    min_embedded_chars: int = 40
):
    """
    Endpoint alternativo para OCR que acepta upload directo de archivo PDF.
    """
    t_start = time.time()
    
    try:
        # Validar tipo de archivo
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
        
        # Leer el contenido del archivo
        content = await file.read()
        
        # Validar tamaño
        if len(content) > MAX_PDF_BYTES:
            raise HTTPException(
                status_code=413, 
                detail=f"PDF demasiado grande. Máximo: {MAX_PDF_BYTES / (1024*1024):.1f} MB"
            )
        
        log_step("1) Upload y validación", t_start)
        
        # Verificar Tesseract
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Tesseract OCR no está instalado o no está disponible en el PATH. "
                       f"Instala Tesseract desde: https://github.com/UB-Mannheim/tesseract/wiki "
                       f"Error: {str(e)}"
            )
        
        # Procesar el PDF
        result = process_pdf_ocr(
            pdf_bytes=content,
            lang=lang,
            oem=oem,
            psm=psm,
            dpi_hint=dpi,
            force_ocr=force_ocr,
            min_embedded_chars=min_embedded_chars
        )
        
        log_step("2) Procesamiento OCR completo", t_start)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=f"Error procesando PDF: {result['error']}")
        
        # Agregar información del archivo
        result["filename"] = file.filename
        result["file_size"] = len(content)
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/ocr-info")
async def ocr_info():
    """
    Información sobre las capacidades de OCR del sistema.
    """
    try:
        # Verificar Tesseract
        tesseract_version = pytesseract.get_tesseract_version()
        tesseract_available = True
        
        # Intentar obtener idiomas disponibles
        try:
            available_langs = pytesseract.get_languages(config='')
        except:
            available_langs = ["Información no disponible"]
        
    except Exception as e:
        tesseract_version = None
        tesseract_available = False
        available_langs = []
    
    return {
        "tesseract_available": tesseract_available,
        "tesseract_version": str(tesseract_version) if tesseract_version else None,
        "available_languages": available_langs,
        "supported_formats": ["PDF"],
        "max_file_size_mb": MAX_PDF_BYTES / (1024*1024),
        "default_config": {
            "lang": "spa",
            "oem": 3,
            "psm": 3,
            "dpi": 300,
            "force_ocr": False,
            "min_embedded_chars": 40
        },
        "psm_modes": {
            "0": "Orientation and script detection (OSD) only",
            "1": "Automatic page segmentation with OSD",
            "2": "Automatic page segmentation, but no OSD, or OCR",
            "3": "Fully automatic page segmentation, but no OSD (Default)",
            "4": "Assume a single column of text of variable sizes",
            "5": "Assume a single uniform block of vertically aligned text",
            "6": "Assume a single uniform block of text",
            "7": "Treat the image as a single text line",
            "8": "Treat the image as a single word",
            "9": "Treat the image as a single word in a circle",
            "10": "Treat the image as a single character",
            "11": "Sparse text. Find as much text as possible in no particular order",
            "12": "Sparse text with OSD",
            "13": "Raw line. Treat the image as a single text line, bypassing hacks"
        },
        "oem_modes": {
            "0": "Legacy engine only",
            "1": "Neural nets LSTM engine only",
            "2": "Legacy + LSTM engines",
            "3": "Default, based on what is available (Default)"
        }
    }
