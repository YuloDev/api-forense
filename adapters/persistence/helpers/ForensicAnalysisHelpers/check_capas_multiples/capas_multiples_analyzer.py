"""
Helper para análisis de capas múltiples en PDFs
Usa directamente la función original de detección de texto superpuesto
"""

import time
import base64
from typing import Dict, Any
from domain.entities.forensic_analysis.check_capas_multiples_result import CapasMultiplesResult
import config
from adapters.persistence.shared import detectar_texto_superpuesto_detallado

class CapasMultiplesAnalyzer:
    """Analizador de capas múltiples en PDFs usando la función original"""
    
    def __init__(self):
        pass
    
    def analyze(self, pdf_bytes: bytes, extracted_text: str = "") -> CapasMultiplesResult:
        """
        Analiza la presencia de capas múltiples en el PDF usando la función original

        Args:
            pdf_bytes: Bytes del archivo PDF
            extracted_text: Texto extraído del PDF

        Returns:
            CapasMultiplesResult: Resultado del análisis
        """
        start_time = time.perf_counter()

        try:
            # Usar la función original de detección de texto superpuesto
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            analisis_completo = detectar_texto_superpuesto_detallado(pdf_base64)

            # Verificar si hay error en el análisis
            if "error" in analisis_completo:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return CapasMultiplesResult.create_error_result(f"Error en análisis: {analisis_completo['error']}")

            # Usar directamente el resumen_general del helper original
            resumen_general = analisis_completo.get("resumen_general", {})
            analisis_por_capas = analisis_completo.get("analisis_por_capas", {})
            
            # Extraer valores del resumen general
            probabilidad = resumen_general.get("probabilidad_manipulacion", 0.0)
            nivel_riesgo = resumen_general.get("nivel_riesgo", "LOW")

            # Calcular penalización basada en el nivel de riesgo
            peso_base = config.RISK_WEIGHTS.get("capas_multiples", 30)

            if nivel_riesgo == "HIGH":
                penalizacion = peso_base
            elif nivel_riesgo == "MEDIUM":
                penalizacion = peso_base // 2
            else:
                penalizacion = 0

            processing_time = int((time.perf_counter() - start_time) * 1000)

            # Crear resultado con la estructura correcta
            return CapasMultiplesResult(
                check_name="Presencia de capas múltiples (análisis integrado)",
                has_layers=probabilidad > 0.1,
                confidence=probabilidad,
                risk_level=nivel_riesgo,
                penalty_points=penalizacion,
                ocg_objects=analisis_por_capas.get("total_ocgs", 0),
                overlay_objects=analisis_por_capas.get("total_streams", 0),
                transparency_objects=0,
                suspicious_operators=0,
                content_streams=analisis_por_capas.get("total_streams", 0),
                layer_count_estimate=analisis_por_capas.get("total_streams", 0),
                indicators=[],
                blend_modes=[],
                alpha_values=[],
                score_breakdown={},
                weights_used={},
                detailed_analysis=analisis_completo,  # Estructura completa del análisis original
                processing_time_ms=processing_time
            )

        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return CapasMultiplesResult.create_error_result(f"Error en análisis de capas: {str(e)}")