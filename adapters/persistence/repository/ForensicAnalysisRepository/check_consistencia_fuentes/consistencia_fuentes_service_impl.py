"""
Implementación del servicio de análisis de consistencia de fuentes.

Utiliza el helper FontAnalyzer para realizar el análisis de consistencia de fuentes.
"""

import time
from typing import Dict, Any, List
from domain.ports.forensic_analysis.check_consistencia_fuentes_service import ConsistenciaFuentesServicePort
from domain.entities.forensic_analysis.check_consistencia_fuentes_result import ConsistenciaFuentesResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_consistencia_fuentes.font_analyzer import FontAnalyzer
from domain.entities.forensic_ocr_details import Palabra, BBox
import config


class ConsistenciaFuentesServiceAdapter(ConsistenciaFuentesServicePort):
    """Adaptador para el servicio de análisis de consistencia de fuentes"""
    
    def __init__(self):
        self.font_analyzer = FontAnalyzer()
    
    def analyze_font_consistency(self, ocr_result: Dict[str, Any], source_type: str) -> ConsistenciaFuentesResult:
        """
        Analiza la consistencia de fuentes usando el resultado del OCR.
        
        Args:
            ocr_result: Resultado del análisis OCR forense
            source_type: Tipo de fuente ("pdf" o "image")
            
        Returns:
            ConsistenciaFuentesResult: Resultado del análisis de consistencia de fuentes
        """
        start_time = time.perf_counter()
        
        try:
            # Verificar que el resultado del OCR sea válido
            if not ocr_result or not ocr_result.get("success", False):
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return ConsistenciaFuentesResult.create_error_result(
                    "Resultado de OCR inválido o no disponible"
                )
            
            # Extraer palabras del resultado del OCR
            palabras = self._extract_words_from_ocr_result(ocr_result)
            
            if not palabras:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return ConsistenciaFuentesResult.create_error_result(
                    "No se encontraron palabras en el resultado del OCR"
                )
            
            # Realizar análisis de consistencia de fuentes
            analisis_fuentes = self.font_analyzer.analyze_font_consistency(palabras)
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(analisis_fuentes)
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analisis_fuentes)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analisis_fuentes, ocr_result)
            
            # Crear lista de fuentes detectadas para el resultado
            fuentes_detectadas = [
                {
                    "font_family": f.font_family,
                    "font_size": f.font_size,
                    "font_style": f.font_style,
                    "font_weight": f.font_weight,
                    "count": f.count,
                    "percentage": f.percentage,
                    "confidence_avg": f.confidence_avg
                }
                for f in analisis_fuentes.fuentes_detectadas
            ]
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return ConsistenciaFuentesResult(
                check_name="Análisis de consistencia de fuentes",
                total_fuentes=analisis_fuentes.total_fuentes,
                fuentes_unicas=analisis_fuentes.fuentes_unicas,
                indice_diversidad=analisis_fuentes.indice_diversidad,
                consistencia_score=analisis_fuentes.consistencia_score,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type=source_type,
                fuentes_detectadas=fuentes_detectadas,
                fuentes_sospechosas=analisis_fuentes.fuentes_sospechosas,
                indicadores_sospechosos=analisis_fuentes.fuentes_sospechosas,
                analysis_notes=analysis_notes,
                file_size_bytes=ocr_result.get("source", {}).get("width_px", 0) * ocr_result.get("source", {}).get("height_px", 0),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return ConsistenciaFuentesResult.create_error_result(
                f"Error en análisis de consistencia de fuentes: {str(e)}"
            )
    
    def _extract_words_from_ocr_result(self, ocr_result: Dict[str, Any]) -> List[Palabra]:
        """Extrae palabras del resultado del OCR"""
        palabras = []
        
        try:
            # Navegar por la estructura del resultado OCR
            ocr_data = ocr_result.get("ocr", {})
            bloques = ocr_data.get("bloques", [])
            
            for bloque in bloques:
                lineas = bloque.get("lineas", [])
                for linea in lineas:
                    palabras_linea = linea.get("palabras", [])
                    for palabra_data in palabras_linea:
                        # Crear objeto Palabra
                        bbox_data = palabra_data.get("bbox", {})
                        bbox = BBox(
                            x=bbox_data.get("x", 0),
                            y=bbox_data.get("y", 0),
                            w=bbox_data.get("w", 0),
                            h=bbox_data.get("h", 0)
                        )
                        
                        palabra = Palabra(
                            bbox=bbox,
                            confidence=palabra_data.get("confidence", 0.0),
                            texto=palabra_data.get("texto", ""),
                            font_family=palabra_data.get("font_family"),
                            font_size=palabra_data.get("font_size"),
                            font_style=palabra_data.get("font_style"),
                            font_weight=palabra_data.get("font_weight")
                        )
                        
                        palabras.append(palabra)
        
        except Exception as e:
            # Si hay error extrayendo palabras, devolver lista vacía
            pass
        
        return palabras
    
    def _calculate_risk_and_confidence(self, analisis_fuentes) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Basado en el score de consistencia
        consistencia_score = analisis_fuentes.consistencia_score
        fuentes_unicas = analisis_fuentes.fuentes_unicas
        indice_diversidad = analisis_fuentes.indice_diversidad
        
        # Determinar nivel de riesgo
        if consistencia_score >= 0.8 and fuentes_unicas <= 2:
            risk_level = "LOW"
            confidence = 0.9
        elif consistencia_score >= 0.6 and fuentes_unicas <= 3:
            risk_level = "MEDIUM"
            confidence = 0.7
        else:
            risk_level = "HIGH"
            confidence = 0.8
        
        # Ajustar según indicadores específicos
        if analisis_fuentes.fuentes_sospechosas:
            risk_level = "HIGH"
            confidence = 0.9
        
        if indice_diversidad > 0.8:
            risk_level = "HIGH"
            confidence = 0.8
        
        if fuentes_unicas > 5:
            risk_level = "HIGH"
            confidence = 0.9
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, analisis_fuentes) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("consistencia_fuentes", 8)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_analysis_notes(self, analisis_fuentes, ocr_result: Dict[str, Any]) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre métricas básicas
        notes.append(f"Total de fuentes detectadas: {analisis_fuentes.total_fuentes}")
        notes.append(f"Fuentes únicas: {analisis_fuentes.fuentes_unicas}")
        notes.append(f"Índice de diversidad: {analisis_fuentes.indice_diversidad:.2f}")
        notes.append(f"Score de consistencia: {analisis_fuentes.consistencia_score:.2f}")
        
        # Notas sobre fuentes detectadas
        if analisis_fuentes.fuentes_detectadas:
            notes.append(f"Fuente más común: {analisis_fuentes.fuentes_detectadas[0].font_family}")
            if len(analisis_fuentes.fuentes_detectadas) > 1:
                notes.append(f"Segunda fuente más común: {analisis_fuentes.fuentes_detectadas[1].font_family}")
        
        # Notas sobre indicadores sospechosos
        if analisis_fuentes.fuentes_sospechosas:
            notes.append(f"Se detectaron {len(analisis_fuentes.fuentes_sospechosas)} fuentes sospechosas")
            for fuente_sospechosa in analisis_fuentes.fuentes_sospechosas[:3]:  # Mostrar solo las primeras 3
                notes.append(f"- {fuente_sospechosa}")
        else:
            notes.append("No se detectaron fuentes sospechosas")
        
        # Notas sobre consistencia
        if analisis_fuentes.consistencia_score >= 0.8:
            notes.append("Excelente consistencia en el uso de fuentes")
        elif analisis_fuentes.consistencia_score >= 0.6:
            notes.append("Consistencia moderada en el uso de fuentes")
        else:
            notes.append("Baja consistencia en el uso de fuentes - posible manipulación")
        
        # Notas sobre diversidad
        if analisis_fuentes.indice_diversidad > 0.7:
            notes.append("Alta diversidad de fuentes detectada - posible composición de múltiples fuentes")
        elif analisis_fuentes.indice_diversidad < 0.3:
            notes.append("Baja diversidad de fuentes - uso consistente")
        
        return notes
