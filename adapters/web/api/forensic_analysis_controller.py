"""
Controlador API para análisis forense
Endpoints para análisis forense de PDF e imágenes
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import base64

# Imports para análisis forense
from application.use_cases.ForensicAnalysisUseCases.check_capas_multiples.analyze_capas_multiples_use_case import AnalyzeCapasMultiplesUseCase
from adapters.persistence.repository.ForensicAnalysisRepository.check_capas_multiples.capas_multiples_service_impl import CapasMultiplesServiceAdapter
from application.use_cases.ForensicAnalysisUseCases.check_fecha_mod_vs_creacion.analyze_fecha_mod_vs_creacion_use_case import AnalyzeFechaModVsCreacionUseCase
from adapters.persistence.repository.ForensicAnalysisRepository.check_fecha_mod_vs_creacion.fecha_mod_vs_creacion_service_impl import FechaModVsCreacionServiceAdapter
from application.use_cases.ForensicAnalysisUseCases.check_software_conocido.analyze_software_conocido_use_case import AnalyzeSoftwareConocidoUseCase
from adapters.persistence.repository.ForensicAnalysisRepository.check_software_conocido.software_conocido_service_impl import SoftwareConocidoServiceAdapter
from application.use_cases.ForensicAnalysisUseCases.check_consistencia_fuentes.analyze_consistencia_fuentes_use_case import AnalyzeConsistenciaFuentesUseCase
from adapters.persistence.repository.ForensicAnalysisRepository.check_consistencia_fuentes.consistencia_fuentes_service_impl import ConsistenciaFuentesServiceAdapter
from application.use_cases.ForensicAnalysisUseCases.check_dpi_uniforme.analyze_dpi_uniforme_use_case import AnalyzeDpiUniformeUseCase
from adapters.persistence.repository.ForensicAnalysisRepository.check_dpi_uniforme.dpi_uniforme_service_impl import DpiUniformeServiceAdapter
from application.use_cases.ForensicAnalysisUseCases.check_compresion_estandar.analyze_compresion_estandar_use_case import AnalyzeCompresionEstandarUseCase
from adapters.persistence.repository.ForensicAnalysisRepository.check_compresion_estandar.compresion_estandar_service_impl import CompresionEstandarServiceAdapter
from application.use_cases.ForensicAnalysisUseCases.check_alineacion_texto.analyze_alineacion_texto_use_case import AnalyzeAlineacionTextoUseCase
from adapters.persistence.repository.ForensicAnalysisRepository.check_alineacion_texto.alineacion_texto_service_impl import AlineacionTextoServiceAdapter
from application.use_cases.ForensicAnalysisUseCases.check_javascript_embebido.analyze_javascript_embebido_use_case import AnalyzeJavascriptEmbebidoUseCase
from adapters.persistence.repository.ForensicAnalysisRepository.check_javascript_embebido.javascript_embebido_service_impl import JavascriptEmbebidoServiceAdapter
from application.use_cases.ForensicAnalysisUseCases.check_actualizaciones_incrementales.analyze_actualizaciones_incrementales_use_case import AnalyzeActualizacionesIncrementalesUseCase
from adapters.persistence.repository.ForensicAnalysisRepository.check_actualizaciones_incrementales.actualizaciones_incrementales_service_impl import ActualizacionesIncrementalesServiceAdapter
from application.use_cases.ForensicAnalysisUseCases.check_cifrado_permisos_extra.analyze_cifrado_permisos_extra_use_case import AnalyzeCifradoPermisosExtraUseCase
from adapters.persistence.repository.ForensicAnalysisRepository.check_cifrado_permisos_extra.cifrado_permisos_extra_service_impl import CifradoPermisosExtraServiceAdapter
from application.use_cases.ForensicAnalysisUseCases.check_extraccion_texto_ocr.analyze_extraccion_texto_ocr_use_case import AnalyzeExtraccionTextoOcrUseCase
from adapters.persistence.repository.ForensicAnalysisRepository.check_extraccion_texto_ocr.extraccion_texto_ocr_service_impl import ExtraccionTextoOcrServiceAdapter

# Modelos de request
class ForensicPDFRequest(BaseModel):
    pdf_base64: str
    tipo: str = "documento"  # documento, laboratorio, otros
    ocr_result: Optional[Dict[str, Any]] = None  # Resultado del OCR forense

class ForensicImageRequest(BaseModel):
    image_base64: str
    tipo: str = "imagen"  # imagen, laboratorio, otros
    ocr_result: Optional[Dict[str, Any]] = None  # Resultado del OCR forense

# Crear router
router = APIRouter(prefix="/forensic-analysis", tags=["Análisis Forense"])

@router.post("/analyze-pdf")
async def analyze_pdf_forensic(request: ForensicPDFRequest) -> JSONResponse:
    """
    Analiza detalles forenses de un PDF
    El parámetro 'tipo' puede ser: documento, laboratorio, otros
    """
    try:
        # Decodificar PDF desde base64
        pdf_bytes = base64.b64decode(request.pdf_base64)
        
        # Inicializar servicios de análisis
        capas_multiples_service = CapasMultiplesServiceAdapter()
        capas_multiples_use_case = AnalyzeCapasMultiplesUseCase(capas_multiples_service)
        
        fecha_service = FechaModVsCreacionServiceAdapter()
        fecha_use_case = AnalyzeFechaModVsCreacionUseCase(fecha_service)
        
        software_service = SoftwareConocidoServiceAdapter()
        software_use_case = AnalyzeSoftwareConocidoUseCase(software_service)
        
        font_consistency_service = ConsistenciaFuentesServiceAdapter()
        font_consistency_use_case = AnalyzeConsistenciaFuentesUseCase(font_consistency_service)
        
        dpi_uniforme_service = DpiUniformeServiceAdapter()
        dpi_uniforme_use_case = AnalyzeDpiUniformeUseCase(dpi_uniforme_service)
        
        compresion_estandar_service = CompresionEstandarServiceAdapter()
        compresion_estandar_use_case = AnalyzeCompresionEstandarUseCase(compresion_estandar_service)
        
        alineacion_texto_service = AlineacionTextoServiceAdapter()
        alineacion_texto_use_case = AnalyzeAlineacionTextoUseCase(alineacion_texto_service)
        
        javascript_embebido_service = JavascriptEmbebidoServiceAdapter()
        javascript_embebido_use_case = AnalyzeJavascriptEmbebidoUseCase(javascript_embebido_service)
        
        actualizaciones_incrementales_service = ActualizacionesIncrementalesServiceAdapter()
        actualizaciones_incrementales_use_case = AnalyzeActualizacionesIncrementalesUseCase(actualizaciones_incrementales_service)
        
        cifrado_permisos_extra_service = CifradoPermisosExtraServiceAdapter()
        cifrado_permisos_extra_use_case = AnalyzeCifradoPermisosExtraUseCase(cifrado_permisos_extra_service)
        
        # Ejecutar análisis de capas múltiples
        capas_result = capas_multiples_use_case.execute(pdf_bytes)
        
        # Ejecutar análisis de fechas
        fecha_result = fecha_use_case.execute_pdf(pdf_bytes)
        
        # Ejecutar análisis de software conocido
        software_result = software_use_case.execute_pdf(pdf_bytes)
        
        # Ejecutar análisis de uniformidad DPI
        dpi_uniforme_result = dpi_uniforme_use_case.execute_pdf(pdf_bytes)
        
        # Ejecutar análisis de compresión estándar
        compresion_estandar_result = compresion_estandar_use_case.execute_pdf(pdf_bytes)
        
        # Ejecutar análisis de JavaScript embebido
        javascript_embebido_result = javascript_embebido_use_case.execute_pdf(pdf_bytes)
        
        # Ejecutar análisis de actualizaciones incrementales
        actualizaciones_incrementales_result = actualizaciones_incrementales_use_case.execute_pdf(pdf_bytes)
        
        # Ejecutar análisis de cifrado y permisos especiales
        cifrado_permisos_extra_result = cifrado_permisos_extra_use_case.execute_pdf(pdf_bytes)
        
        # Ejecutar análisis de consistencia de fuentes (si hay resultado OCR)
        font_consistency_result = None
        if request.ocr_result:
            font_consistency_result = font_consistency_use_case.execute(request.ocr_result, "pdf")
        
        # Ejecutar análisis de alineación de texto (si hay resultado OCR)
        alineacion_texto_result = None
        if request.ocr_result:
            alineacion_texto_result = alineacion_texto_use_case.execute(request.ocr_result, "pdf")
        
        # Construir respuesta con estructura requerida
        adicionales = [software_result, dpi_uniforme_result, compresion_estandar_result]  # check-software_conocido, check-dpi_uniforme y check-compresion_estandar van en Adicionales
        
        # Agregar consistencia de fuentes si está disponible
        if font_consistency_result:
            adicionales.append(font_consistency_result)
        
        # Generar resumen general
        resumen_general = _generate_general_summary(
            capas_result, fecha_result, adicionales, font_consistency_result, alineacion_texto_result, javascript_embebido_result, actualizaciones_incrementales_result, cifrado_permisos_extra_result
        )
        
        result = {
            "success": True,
            "Prioridad": [
                capas_result  # check-capas_multiples va en Prioridad
            ],
            "Secundarios": [
                fecha_result  # check-fecha_mod_vs_creacion va en Secundarios
            ],
            "Adicionales": adicionales,
            "Resumen_General": resumen_general
        }
        
        return JSONResponse(
            status_code=200,
            content=result
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "Prioridad": [],
                "Secundarios": [],
                "Adicionales": [],
                "Resumen_General": []
            }
        )

@router.post("/analyze-image")
async def analyze_image_forensic(request: ForensicImageRequest) -> JSONResponse:
    """
    Analiza detalles forenses de una imagen
    El parámetro 'tipo' puede ser: imagen, laboratorio, otros
    """
    try:
        # Decodificar imagen desde base64
        image_bytes = base64.b64decode(request.image_base64)
        
        # Inicializar servicios de análisis
        fecha_service = FechaModVsCreacionServiceAdapter()
        fecha_use_case = AnalyzeFechaModVsCreacionUseCase(fecha_service)
        
        software_service = SoftwareConocidoServiceAdapter()
        software_use_case = AnalyzeSoftwareConocidoUseCase(software_service)
        
        font_consistency_service = ConsistenciaFuentesServiceAdapter()
        font_consistency_use_case = AnalyzeConsistenciaFuentesUseCase(font_consistency_service)
        
        dpi_uniforme_service = DpiUniformeServiceAdapter()
        dpi_uniforme_use_case = AnalyzeDpiUniformeUseCase(dpi_uniforme_service)
        
        compresion_estandar_service = CompresionEstandarServiceAdapter()
        compresion_estandar_use_case = AnalyzeCompresionEstandarUseCase(compresion_estandar_service)
        
        alineacion_texto_service = AlineacionTextoServiceAdapter()
        alineacion_texto_use_case = AnalyzeAlineacionTextoUseCase(alineacion_texto_service)
        
        javascript_embebido_service = JavascriptEmbebidoServiceAdapter()
        javascript_embebido_use_case = AnalyzeJavascriptEmbebidoUseCase(javascript_embebido_service)
        
        actualizaciones_incrementales_service = ActualizacionesIncrementalesServiceAdapter()
        actualizaciones_incrementales_use_case = AnalyzeActualizacionesIncrementalesUseCase(actualizaciones_incrementales_service)
        
        cifrado_permisos_extra_service = CifradoPermisosExtraServiceAdapter()
        cifrado_permisos_extra_use_case = AnalyzeCifradoPermisosExtraUseCase(cifrado_permisos_extra_service)
        
        extraccion_texto_ocr_service = ExtraccionTextoOcrServiceAdapter()
        extraccion_texto_ocr_use_case = AnalyzeExtraccionTextoOcrUseCase(extraccion_texto_ocr_service)
        
        # Ejecutar análisis de fechas
        fecha_result = fecha_use_case.execute_image(image_bytes)
        
        # Ejecutar análisis de software conocido
        software_result = software_use_case.execute_image(image_bytes)
        
        # Ejecutar análisis de uniformidad DPI
        dpi_uniforme_result = dpi_uniforme_use_case.execute_image(image_bytes)
        
        # Ejecutar análisis de compresión estándar
        compresion_estandar_result = compresion_estandar_use_case.execute_image(image_bytes)
        
        # Ejecutar análisis de JavaScript embebido
        javascript_embebido_result = javascript_embebido_use_case.execute_image(image_bytes)
        
        # Ejecutar análisis de actualizaciones incrementales
        actualizaciones_incrementales_result = actualizaciones_incrementales_use_case.execute_image(image_bytes)
        
        # Ejecutar análisis de cifrado y permisos especiales
        cifrado_permisos_extra_result = cifrado_permisos_extra_use_case.execute_image(image_bytes)
        
        # Ejecutar análisis de extracción de texto OCR (solo para imágenes)
        extraccion_texto_ocr_result = extraccion_texto_ocr_use_case.execute_image(image_bytes)
        
        # Ejecutar análisis de consistencia de fuentes (si hay resultado OCR)
        font_consistency_result = None
        if request.ocr_result:
            font_consistency_result = font_consistency_use_case.execute(request.ocr_result, "image")
        
        # Ejecutar análisis de alineación de texto (si hay resultado OCR)
        alineacion_texto_result = None
        if request.ocr_result:
            alineacion_texto_result = alineacion_texto_use_case.execute(request.ocr_result, "image")
        
        # Construir respuesta con estructura requerida
        adicionales = [software_result, dpi_uniforme_result, compresion_estandar_result]  # check-software_conocido, check-dpi_uniforme y check-compresion_estandar van en Adicionales
        
        # Agregar consistencia de fuentes si está disponible
        if font_consistency_result:
            adicionales.append(font_consistency_result)
        
        # Generar resumen general
        resumen_general = _generate_general_summary(
            None, fecha_result, adicionales, font_consistency_result, alineacion_texto_result, javascript_embebido_result, actualizaciones_incrementales_result, cifrado_permisos_extra_result, extraccion_texto_ocr_result
        )
        
        result = {
            "success": True,
            "Prioridad": [],
            "Secundarios": [
                fecha_result  # check-fecha_mod_vs_creacion va en Secundarios
            ],
            "Adicionales": adicionales,
            "Resumen_General": resumen_general
        }
        
        return JSONResponse(
            status_code=200,
            content=result
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "Prioridad": [],
                "Secundarios": [],
                "Adicionales": [],
                "Resumen_General": []
            }
        )

def _generate_general_summary(capas_result: Dict = None, fecha_result: Dict = None, 
                            adicionales: List[Dict] = None, font_consistency_result: Dict = None, 
                            alineacion_texto_result: Dict = None, javascript_embebido_result: Dict = None, 
                            actualizaciones_incrementales_result: Dict = None, cifrado_permisos_extra_result: Dict = None, 
                            extraccion_texto_ocr_result: Dict = None) -> List[str]:
    """Genera un resumen general basado en todos los análisis realizados"""
    summary = []
    
    # Resumen de análisis de prioridad
    if capas_result:
        capas_penalty = capas_result.get("penalizacion", 0)
        if capas_penalty > 0:
            summary.append(f"Análisis de capas múltiples: {capas_penalty} puntos de penalización")
        else:
            summary.append("Análisis de capas múltiples: Sin indicadores de manipulación")
    
    # Resumen de análisis secundarios
    if fecha_result:
        fecha_penalty = fecha_result.get("penalizacion", 0)
        if fecha_penalty > 0:
            summary.append(f"Análisis de fechas: {fecha_penalty} puntos de penalización")
        else:
            summary.append("Análisis de fechas: Sin indicadores temporales sospechosos")
    
    # Resumen de análisis adicionales
    if adicionales:
        total_penalty = 0
        checks_with_penalty = []
        
        for check in adicionales:
            penalty = check.get("penalizacion", 0)
            if penalty > 0:
                total_penalty += penalty
                check_name = check.get("check", "Check desconocido")
                checks_with_penalty.append(f"{check_name}: {penalty} puntos")
        
        if total_penalty > 0:
            summary.append(f"Análisis adicionales: {total_penalty} puntos totales de penalización")
            summary.extend(checks_with_penalty)
        else:
            summary.append("Análisis adicionales: Sin indicadores de manipulación")
    
    # Resumen de alineación de texto (si está disponible)
    if alineacion_texto_result:
        alignment_penalty = alineacion_texto_result.get("penalizacion", 0)
        if alignment_penalty > 0:
            summary.append(f"Análisis de alineación de texto: {alignment_penalty} puntos de penalización")
        else:
            summary.append("Análisis de alineación de texto: Alineación correcta")
    
    # Resumen de JavaScript embebido (si está disponible)
    if javascript_embebido_result:
        js_penalty = javascript_embebido_result.get("penalizacion", 0)
        if js_penalty > 0:
            summary.append(f"Análisis de JavaScript embebido: {js_penalty} puntos de penalización")
        else:
            summary.append("Análisis de JavaScript embebido: Sin JavaScript detectado")
    
    # Resumen de actualizaciones incrementales (si está disponible)
    if actualizaciones_incrementales_result:
        updates_penalty = actualizaciones_incrementales_result.get("penalizacion", 0)
        if updates_penalty > 0:
            summary.append(f"Análisis de actualizaciones incrementales: {updates_penalty} puntos de penalización")
        else:
            summary.append("Análisis de actualizaciones incrementales: Sin actualizaciones detectadas")
    
    # Resumen de cifrado y permisos especiales (si está disponible)
    if cifrado_permisos_extra_result:
        crypto_penalty = cifrado_permisos_extra_result.get("penalizacion", 0)
        if crypto_penalty > 0:
            summary.append(f"Análisis de cifrado y permisos especiales: {crypto_penalty} puntos de penalización")
        else:
            summary.append("Análisis de cifrado y permisos especiales: Sin restricciones detectadas")
    
    # Resumen de extracción de texto OCR (solo para imágenes)
    if extraccion_texto_ocr_result:
        ocr_penalty = extraccion_texto_ocr_result.get("penalizacion", 0)
        if ocr_penalty > 0:
            summary.append(f"Análisis de extracción de texto OCR: {ocr_penalty} puntos de penalización")
        else:
            summary.append("Análisis de extracción de texto OCR: Texto extraído correctamente")
    
    # Resumen general de riesgo
    total_penalty = 0
    if capas_result:
        total_penalty += capas_result.get("penalizacion", 0)
    if fecha_result:
        total_penalty += fecha_result.get("penalizacion", 0)
    if adicionales:
        for check in adicionales:
            total_penalty += check.get("penalizacion", 0)
    if alineacion_texto_result:
        total_penalty += alineacion_texto_result.get("penalizacion", 0)
    if javascript_embebido_result:
        total_penalty += javascript_embebido_result.get("penalizacion", 0)
    if actualizaciones_incrementales_result:
        total_penalty += actualizaciones_incrementales_result.get("penalizacion", 0)
    if cifrado_permisos_extra_result:
        total_penalty += cifrado_permisos_extra_result.get("penalizacion", 0)
    if extraccion_texto_ocr_result:
        total_penalty += extraccion_texto_ocr_result.get("penalizacion", 0)
    
    if total_penalty == 0:
        summary.append("RESUMEN: Documento sin indicadores de manipulación detectados")
    elif total_penalty <= 10:
        summary.append(f"RESUMEN: Riesgo bajo de manipulación ({total_penalty} puntos totales)")
    elif total_penalty <= 20:
        summary.append(f"RESUMEN: Riesgo medio de manipulación ({total_penalty} puntos totales)")
    else:
        summary.append(f"RESUMEN: Riesgo alto de manipulación ({total_penalty} puntos totales)")
    
    return summary

@router.get("/health")
async def health_check():
    """Verificación de salud del servicio de análisis forense"""
    return {"status": "healthy", "service": "forensic-analysis", "version": "1.0.0"}
