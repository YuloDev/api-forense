import base64
import io
import time
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import fitz  # PyMuPDF

from config import MAX_PDF_BYTES
from utils import log_step

router = APIRouter()


class PeticionPdfImagenes(BaseModel):
    """Modelo de petición para convertir PDF a imágenes"""
    pdfbase64: str
    dpi: int = 150  # DPI por defecto


class RespuestaImagenes(BaseModel):
    """Modelo de respuesta para las imágenes del PDF"""
    total_paginas: int
    imagenes: List[str]  # Lista de imágenes en base64
    mensaje: str


def validate_pdf_file(file_content: bytes) -> bool:
    """Valida que el archivo sea un PDF válido"""
    try:
        # Verificar cabecera PDF
        if not file_content.startswith(b'%PDF-'):
            return False
        
        # Intentar abrir con PyMuPDF
        doc = fitz.open(stream=file_content, filetype="pdf")
        doc.close()
        return True
    except Exception:
        return False


def pdf_to_images(pdf_bytes: bytes, dpi: int = 150) -> List[str]:
    """
    Convierte un PDF a imágenes usando PyMuPDF
    Retorna una lista de imágenes en base64
    """
    images_b64 = []
    
    try:
        # Abrir el PDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Convertir cada página a imagen
        for page_num in range(len(doc)):
            # Obtener la página
            page = doc.load_page(page_num)
            
            # Crear matriz de transformación para el DPI deseado
            # fitz usa 72 DPI por defecto, así que calculamos el factor de escala
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            
            # Renderizar la página como imagen
            pix = page.get_pixmap(matrix=mat)
            
            # Convertir a bytes PNG
            img_data = pix.tobytes("png")
            
            # Convertir a base64
            img_b64 = base64.b64encode(img_data).decode('utf-8')
            images_b64.append(img_b64)
            
            # Limpiar memoria
            pix = None
        
        doc.close()
        return images_b64
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al convertir PDF a imágenes: {str(e)}"
        )


@router.post("/parse-pdf-to-images", response_model=RespuestaImagenes)
async def parse_pdf_to_images(req: PeticionPdfImagenes):
    """
    Endpoint que recibe un PDF en base64 y lo convierte en imágenes.
    
    Args:
        req: Petición con el PDF en base64 y opcionalmente el DPI
    
    Returns:
        RespuestaImagenes: Objeto con las imágenes en base64
    """
    t_inicio = time.perf_counter()
    log_step("Iniciando conversión PDF a imágenes", t_inicio)
    
    # 1) Decodificar base64
    try:
        pdf_bytes = base64.b64decode(req.pdfbase64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="El campo 'pdfbase64' no es base64 válido.")
    
    # 2) Validar tamaño del PDF
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=413, 
            detail=f"El PDF excede el tamaño máximo permitido ({MAX_PDF_BYTES} bytes)."
        )
    
    # 3) Validar que sea un PDF válido
    if not validate_pdf_file(pdf_bytes):
        raise HTTPException(
            status_code=400, 
            detail="Los datos no corresponden a un PDF válido."
        )
    
    # 4) Validar DPI
    if req.dpi < 72 or req.dpi > 600:
        raise HTTPException(
            status_code=400, 
            detail="El DPI debe estar entre 72 y 600."
        )
    
    log_step("Validaciones completadas", time.perf_counter())
    
    # 5) Convertir PDF a imágenes
    imagenes_b64 = pdf_to_images(pdf_bytes, req.dpi)
    
    log_step(f"Conversión completada - {len(imagenes_b64)} páginas", time.perf_counter())
    
    return RespuestaImagenes(
        total_paginas=len(imagenes_b64),
        imagenes=imagenes_b64,
        mensaje=f"PDF convertido exitosamente a {len(imagenes_b64)} imágenes con DPI {req.dpi}"
    )
