from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any

from application.use_cases.OCRUseCases.validate_ocr_text import ValidateOCRTextUseCase
from adapters.persistence.repository.OCRRepository.ocr_service_impl import OCRServiceAdapter


# Modelos de datos para la API
class ImageOCRRequest(BaseModel):
    """Modelo para peticiones de OCR de imágenes"""
    image_base64: str
    tipo: str = "imagen"  # Puede ser: imagen, laboratorio, otros


class TextOCRRequest(BaseModel):
    """Modelo para peticiones de OCR de texto"""
    text_base64: str
    tipo: str = "pdf"  # Puede ser: pdf, laboratorio, otros


# Inicializar router y dependencias
router = APIRouter(prefix="/ocr", tags=["OCR Validation"])

# Inyección de dependencias (en un caso real usarías un contenedor DI)
ocr_service = OCRServiceAdapter()
validate_ocr_use_case = ValidateOCRTextUseCase(ocr_service)


@router.post("/extract-image")
async def extract_image_text(request: ImageOCRRequest) -> JSONResponse:
    """
    Extrae texto de una imagen usando OCR
    El parámetro 'tipo' puede ser: imagen, laboratorio, otros
    """
    try:
        result = validate_ocr_use_case.execute_image(request.image_base64)
        
        # Agregar el tipo a la respuesta
        if result["success"]:
            result["tipo"] = request.tipo
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "text_raw": result["text_raw"],
                "text_normalized": result["text_normalized"],
                "tipo": result.get("tipo", "imagen")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "text_raw": "",
                "text_normalized": ""
            }
        )


@router.post("/extract-text")
async def extract_text(request: TextOCRRequest) -> JSONResponse:
    """
    Extrae texto de un documento PDF (nativo o escaneado) usando OCR
    El parámetro 'tipo' puede ser: pdf, laboratorio, otros
    """
    try:
        result = validate_ocr_use_case.execute_pdf(request.text_base64)
        
        # Agregar el tipo a la respuesta
        if result["success"]:
            result["tipo"] = request.tipo
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "text_raw": result["text_raw"],
                "text_normalized": result["text_normalized"],
                "tipo": result.get("tipo", "pdf")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "text_raw": "",
                "text_normalized": ""
            }
        )


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Endpoint de salud para verificar que el servicio OCR está funcionando
    """
    try:
        # Verificar que Tesseract está disponible
        import pytesseract
        version = pytesseract.get_tesseract_version()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Servicio OCR funcionando correctamente",
                "tesseract_version": str(version),
                "language": ocr_service.language,
                "min_confidence": ocr_service.min_confidence
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Error en el servicio OCR",
                "error": str(e)
            }
        )
