from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any

from application.use_cases.OCRUseCases.extract_forensic_details import ExtractForensicDetailsUseCase
from adapters.persistence.repository.OCRRepository.forensic_ocr_service_impl import ForensicOCRServiceAdapter


# Modelos de datos para la API forense
class ForensicImageRequest(BaseModel):
    """Modelo para peticiones forenses de imágenes"""
    image_base64: str
    tipo: str = "imagen"  # Puede ser: imagen, laboratorio, otros


class ForensicTextRequest(BaseModel):
    """Modelo para peticiones forenses de texto"""
    text_base64: str
    tipo: str = "pdf"  # Puede ser: pdf, laboratorio, otros


# Inicializar router y dependencias
router = APIRouter(prefix="/forensic-ocr", tags=["Forensic OCR Analysis"])

# Inyección de dependencias
forensic_ocr_service = ForensicOCRServiceAdapter()
extract_forensic_use_case = ExtractForensicDetailsUseCase(forensic_ocr_service)


@router.post("/analyze-image")
async def analyze_image_forensic(request: ForensicImageRequest) -> JSONResponse:
    """
    Analiza detalles forenses de una imagen usando OCR
    El parámetro 'tipo' puede ser: imagen, laboratorio, otros
    """
    try:
        result = extract_forensic_use_case.execute_image(request.image_base64, request.tipo)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Devolver el esquema JSON completo según especificación
        return JSONResponse(
            status_code=200,
            content=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "source": {"filename": "", "mime": "", "width_px": 0, "height_px": 0, "dpi_estimado": 0, "rotation_deg": 0},
                "ocr": {"engine": "", "lang_detected": [], "confidence_avg": 0, "confidence_std": 0, "texto_full": "", "bloques": [], "metricas": {"skew_deg": 0, "densidad_lineas_por_1000px": 0, "porcentaje_area_texto": 0, "zonas_baja_confianza": []}},
                "normalizaciones": {"fechas": [], "monedas": [], "identificadores": [], "campos_clave": [], "items_detectados": []},
                "forense": {"alertas": [], "resumen": {"score_calidad_ocr": 0, "score_integridad_textual": 0, "tiene_inconsistencias_monetarias": False, "tiene_sobreposiciones_sospechosas": False}},
                "version": "ocr-forense-1.0.0",
                "tiempos_ms": {"preprocesado": 0, "ocr": 0, "postprocesado": 0}
            }
        )


@router.post("/analyze-text")
async def analyze_text_forensic(request: ForensicTextRequest) -> JSONResponse:
    """
    Analiza detalles forenses de un documento PDF (nativo o escaneado) usando OCR
    El parámetro 'tipo' puede ser: pdf, laboratorio, otros
    """
    try:
        result = extract_forensic_use_case.execute_pdf(request.text_base64, request.tipo)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Devolver el esquema JSON completo según especificación
        return JSONResponse(
            status_code=200,
            content=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "source": {"filename": "", "mime": "", "width_px": 0, "height_px": 0, "dpi_estimado": 0, "rotation_deg": 0},
                "ocr": {"engine": "", "lang_detected": [], "confidence_avg": 0, "confidence_std": 0, "texto_full": "", "bloques": [], "metricas": {"skew_deg": 0, "densidad_lineas_por_1000px": 0, "porcentaje_area_texto": 0, "zonas_baja_confianza": []}},
                "normalizaciones": {"fechas": [], "monedas": [], "identificadores": [], "campos_clave": [], "items_detectados": []},
                "forense": {"alertas": [], "resumen": {"score_calidad_ocr": 0, "score_integridad_textual": 0, "tiene_inconsistencias_monetarias": False, "tiene_sobreposiciones_sospechosas": False}},
                "version": "ocr-forense-1.0.0",
                "tiempos_ms": {"preprocesado": 0, "ocr": 0, "postprocesado": 0}
            }
        )


@router.get("/health")
async def forensic_health_check() -> JSONResponse:
    """
    Endpoint de salud para verificar que el servicio forense OCR está funcionando
    """
    try:
        # Verificar que Tesseract está disponible
        import pytesseract
        version = pytesseract.get_tesseract_version()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Servicio forense OCR funcionando correctamente",
                "tesseract_version": str(version),
                "language": forensic_ocr_service.language,
                "min_confidence": forensic_ocr_service.min_confidence,
                "available_analyses": [
                    "identificacion_reproducibilidad",
                    "ocr_result_detailed",
                    "visual_artifacts",
                    "entities_extraction",
                    "financial_analysis",
                    "consistency_hints"
                ]
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Error en el servicio forense OCR",
                "error": str(e)
            }
        )
