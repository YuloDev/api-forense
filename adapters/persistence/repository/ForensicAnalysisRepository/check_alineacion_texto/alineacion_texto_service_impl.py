"""
Implementación del servicio de análisis de alineación de texto.

Utiliza el helper AlignmentAnalyzer para realizar el análisis de alineación de texto.
"""

import time
from typing import Dict, Any, List
from domain.ports.forensic_analysis.check_alineacion_texto_service import AlineacionTextoServicePort
from domain.entities.forensic_analysis.check_alineacion_texto_result import AlineacionTextoResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_alineacion_texto.alignment_analyzer import AlignmentAnalyzer
import config


class AlineacionTextoServiceAdapter(AlineacionTextoServicePort):
    """Adaptador para el servicio de análisis de alineación de texto"""
    
    def __init__(self):
        self.alignment_analyzer = AlignmentAnalyzer()
    
    def analyze_text_alignment(self, ocr_result: Dict[str, Any], source_type: str) -> AlineacionTextoResult:
        """
        Analiza la alineación de texto basado en resultado OCR.
        
        Args:
            ocr_result: Resultado del análisis OCR
            source_type: Tipo de archivo ("pdf" o "image")
            
        Returns:
            AlineacionTextoResult: Resultado del análisis de alineación de texto
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de alineación
            analysis_result = self.alignment_analyzer.analyze_text_alignment(ocr_result, source_type)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return AlineacionTextoResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            elementos_analizados = analysis_result.get("elementos_analizados", 0)
            alineacion_correcta = analysis_result.get("alineacion_correcta", True)
            desviacion_promedio = analysis_result.get("desviacion_promedio", 0.0)
            alineaciones_detectadas = analysis_result.get("alineaciones_detectadas", [])
            desviaciones_por_elemento = analysis_result.get("desviaciones_por_elemento", [])
            elementos_mal_alineados = analysis_result.get("elementos_mal_alineados", [])
            indicadores_sospechosos = analysis_result.get("suspicious_indicators", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                alineacion_correcta, desviacion_promedio, elementos_mal_alineados, 
                indicadores_sospechosos, elementos_analizados
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, source_type)
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return AlineacionTextoResult(
                check_name="Análisis de alineación de texto",
                elementos_analizados=elementos_analizados,
                alineacion_correcta=alineacion_correcta,
                desviacion_promedio=desviacion_promedio,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type=source_type,
                alineaciones_detectadas=alineaciones_detectadas,
                desviaciones_por_elemento=desviaciones_por_elemento,
                elementos_mal_alineados=elementos_mal_alineados,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=None,  # No disponible en análisis OCR
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return AlineacionTextoResult.create_error_result(
                f"Error en análisis de alineación de texto: {str(e)}"
            )
    
    def _calculate_risk_and_confidence(self, alineacion_correcta: bool, desviacion_promedio: float, 
                                     elementos_mal_alineados: List[Dict], indicadores_sospechosos: List[str], 
                                     elementos_analizados: int) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no hay elementos analizados, riesgo bajo
        if elementos_analizados == 0:
            return "LOW", 0.0
        
        # Determinar nivel de riesgo basado en alineación y desviación
        if not alineacion_correcta or desviacion_promedio > 10.0:
            risk_level = "HIGH"
            confidence = 0.9
        elif desviacion_promedio > 5.0 or len(elementos_mal_alineados) > 0:
            risk_level = "MEDIUM"
            confidence = 0.7
        else:
            risk_level = "LOW"
            confidence = 0.8
        
        # Ajustar según indicadores sospechosos
        if indicadores_sospechosos:
            if len(indicadores_sospechosos) > 2:
                risk_level = "HIGH"
                confidence = 0.9
            elif len(indicadores_sospechosos) > 0:
                risk_level = "MEDIUM"
                confidence = 0.7
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, analysis_result: Dict) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("alineacion_texto", 6)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_analysis_notes(self, analysis_result: Dict, source_type: str) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre elementos analizados
        elementos_analizados = analysis_result.get("elementos_analizados", 0)
        notes.append(f"Elementos de texto analizados: {elementos_analizados}")
        
        # Notas sobre alineación
        alineacion_correcta = analysis_result.get("alineacion_correcta", True)
        if alineacion_correcta:
            notes.append("Alineación de texto correcta")
        else:
            notes.append("Problemas de alineación detectados")
        
        # Notas sobre desviación
        desviacion_promedio = analysis_result.get("desviacion_promedio", 0.0)
        if desviacion_promedio <= 1.0:
            notes.append("Excelente alineación de texto")
        elif desviacion_promedio <= 3.0:
            notes.append("Buena alineación de texto")
        elif desviacion_promedio <= 5.0:
            notes.append("Alineación de texto aceptable")
        elif desviacion_promedio <= 10.0:
            notes.append("Alineación de texto pobre")
        else:
            notes.append("Alineación de texto muy mala")
        
        # Notas sobre alineaciones detectadas
        alineaciones_detectadas = analysis_result.get("alineaciones_detectadas", [])
        if alineaciones_detectadas:
            notes.append(f"Tipos de alineación detectados: {alineaciones_detectadas}")
        
        # Notas sobre elementos mal alineados
        elementos_mal_alineados = analysis_result.get("elementos_mal_alineados", [])
        if elementos_mal_alineados:
            notes.append(f"{len(elementos_mal_alineados)} elementos mal alineados detectados")
            for elemento in elementos_mal_alineados[:3]:  # Mostrar solo los primeros 3
                notes.append(f"- {elemento['type']}: {elemento['text'][:30]}...")
        else:
            notes.append("No se detectaron elementos mal alineados")
        
        # Notas sobre indicadores sospechosos
        indicadores_sospechosos = analysis_result.get("suspicious_indicators", [])
        if indicadores_sospechosos:
            notes.append(f"Se detectaron {len(indicadores_sospechosos)} indicadores sospechosos")
            for indicador in indicadores_sospechosos[:3]:  # Mostrar solo los primeros 3
                notes.append(f"- {indicador}")
        else:
            notes.append("No se detectaron indicadores sospechosos en la alineación")
        
        # Notas específicas por tipo de archivo
        if source_type == "pdf":
            notes.append("Análisis de alineación de texto PDF completado")
        else:
            notes.append("Análisis de alineación de texto de imagen completado")
        
        # Notas sobre análisis detallado
        word_analysis = analysis_result.get("word_analysis", {})
        line_analysis = analysis_result.get("line_analysis", {})
        paragraph_analysis = analysis_result.get("paragraph_analysis", {})
        
        if word_analysis.get("elements", 0) > 0:
            notes.append(f"Análisis de palabras: {word_analysis['elements']} elementos")
        if line_analysis.get("elements", 0) > 0:
            notes.append(f"Análisis de líneas: {line_analysis['elements']} elementos")
        if paragraph_analysis.get("elements", 0) > 0:
            notes.append(f"Análisis de párrafos: {paragraph_analysis['elements']} elementos")
        
        return notes
