import time
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from application.use_cases.PDFParsingUseCases.convert_pdf_to_images_use_case import ConvertPDFToImagesUseCase
from adapters.persistence.repository.PDFParsingRepository.pdf_parsing_service_impl import PDFParsingServiceAdapter
from utils import log_step

router = APIRouter(prefix="/pdf-parsing", tags=["PDF Parsing"])


class PDFToImagesRequest(BaseModel):
    """Modelo de petición para convertir PDF a imágenes"""
    pdfbase64: str
    dpi: int = 150  # DPI por defecto
    filename: str = ""
    include_metadata: bool = True


class PDFToImagesResponse(BaseModel):
    """Modelo de respuesta para las imágenes del PDF"""
    success: bool
    total_paginas: int
    imagenes: List[str]  # Lista de imágenes en base64
    mensaje: str
    source_info: dict = {}
    metrics: dict = {}
    errors: List[dict] = []


# Inicializar dependencias
pdf_parsing_service = PDFParsingServiceAdapter()
convert_pdf_use_case = ConvertPDFToImagesUseCase(pdf_parsing_service)


@router.post("/convert-to-images")
async def convert_pdf_to_images(request: PDFToImagesRequest) -> JSONResponse:
    """
    Convierte un PDF a imágenes usando la arquitectura hexagonal
    
    Args:
        request: Petición con el PDF en base64 y configuración
    
    Returns:
        JSONResponse: Respuesta con las imágenes convertidas y metadatos
    """
    t_inicio = time.perf_counter()
    log_step("Iniciando conversión PDF a imágenes", t_inicio)
    
    try:
        # Ejecutar caso de uso
        result = convert_pdf_use_case.execute(
            pdf_base64=request.pdfbase64,
            dpi=request.dpi,
            filename=request.filename,
            include_metadata=request.include_metadata
        )
        
        log_step(f"Conversión completada - Status: {result.get('success')}", time.perf_counter())
        
        # Determinar código de respuesta
        status_code = 200 if result.get("success") else 400
        
        return JSONResponse(
            status_code=status_code,
            content=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_step(f"Error inesperado: {str(e)}", time.perf_counter())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "total_paginas": 0,
                "imagenes": [],
                "mensaje": f"Error interno del servidor: {str(e)}",
                "source_info": {},
                "metrics": {},
                "errors": [{
                    "page_number": None,
                    "error_type": "internal_error",
                    "error_message": str(e)
                }]
            }
        )
