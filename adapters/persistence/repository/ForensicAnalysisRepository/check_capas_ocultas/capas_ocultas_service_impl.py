"""
Implementación del servicio de detección de capas ocultas.

Utiliza el helper CapasOcultasAnalyzer para realizar la detección usando la lógica existente.
"""

import time
from typing import Dict, Any, List
from domain.ports.forensic_analysis.check_capas_ocultas_service import CapasOcultasServicePort
from domain.entities.forensic_analysis.check_capas_ocultas_result import CapasOcultasResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_capas_ocultas.capas_ocultas_analyzer import CapasOcultasAnalyzer
import config


class CapasOcultasServiceAdapter(CapasOcultasServicePort):
    """Adaptador para el servicio de detección de capas ocultas"""
    
    def __init__(self):
        self.capas_ocultas_analyzer = CapasOcultasAnalyzer()
    
    def analyze_image_capas_ocultas(self, image_bytes: bytes) -> CapasOcultasResult:
        """
        Analiza capas ocultas en una imagen usando la lógica existente.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            CapasOcultasResult: Resultado del análisis de capas ocultas
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de capas ocultas
            analysis_result = self.capas_ocultas_analyzer.analyze_image_capas_ocultas(image_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return CapasOcultasResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            tiene_capas = analysis_result.get("tiene_capas", False)
            total_capas = analysis_result.get("total_capas", 0)
            capas_ocultas = analysis_result.get("capas_ocultas", 0)
            capas = analysis_result.get("capas", [])
            modos_mezcla = analysis_result.get("modos_mezcla", [])
            capas_sospechosas = analysis_result.get("sospechosas", [])
            tipo_archivo = analysis_result.get("tipo_archivo", "unknown")
            
            # Determinar si hay capas ocultas detectadas
            capas_ocultas_detectadas = capas_ocultas > 0
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                capas_ocultas_detectadas, total_capas, capas_ocultas, tipo_archivo
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar indicadores sospechosos
            indicadores_sospechosos = self._generate_suspicious_indicators(
                capas_ocultas_detectadas, total_capas, capas_ocultas, tipo_archivo, capas_sospechosas
            )
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result)
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return CapasOcultasResult(
                check_name="Detección de capas ocultas",
                capas_ocultas_detectadas=capas_ocultas_detectadas,
                total_capas=total_capas,
                capas_ocultas=capas_ocultas,
                tipo_archivo=tipo_archivo,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="image",
                capas=capas,
                modos_mezcla=modos_mezcla,
                capas_sospechosas=capas_sospechosas,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(image_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return CapasOcultasResult.create_error_result(
                f"Error en detección de capas ocultas: {str(e)}"
            )
    
    def _calculate_risk_and_confidence(self, capas_ocultas_detectadas: bool, 
                                     total_capas: int, capas_ocultas: int, 
                                     tipo_archivo: str) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no hay capas ocultas detectadas, riesgo bajo
        if not capas_ocultas_detectadas:
            return "LOW", 0.8
        
        # Determinar nivel de riesgo basado en métricas
        if capas_ocultas > 3 or (total_capas > 5 and capas_ocultas > 1):
            risk_level = "HIGH"
            confidence = 0.9
        elif capas_ocultas > 1 or (total_capas > 3 and capas_ocultas > 0):
            risk_level = "HIGH"
            confidence = 0.8
        elif capas_ocultas > 0:
            risk_level = "MEDIUM"
            confidence = 0.7
        else:
            risk_level = "LOW"
            confidence = 0.6
        
        # Ajustar confianza basado en tipo de archivo
        if tipo_archivo in ["PSD", "TIFF"]:
            confidence = min(confidence + 0.1, 1.0)  # Más confianza para formatos que soportan capas
        elif tipo_archivo in ["JPEG", "PNG"]:
            confidence = max(confidence - 0.1, 0.0)  # Menos confianza para formatos que no soportan capas
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, analysis_result: Dict) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("capas_ocultas", 20)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_suspicious_indicators(self, capas_ocultas_detectadas: bool, 
                                      total_capas: int, capas_ocultas: int, 
                                      tipo_archivo: str, capas_sospechosas: List[Dict]) -> List[str]:
        """Genera indicadores sospechosos basados en el análisis"""
        indicators = []
        
        if capas_ocultas_detectadas:
            indicators.append("Capas ocultas detectadas en la imagen")
        
        if total_capas > 1:
            indicators.append(f"Múltiples capas detectadas: {total_capas}")
        
        if capas_ocultas > 0:
            indicators.append(f"Capas ocultas encontradas: {capas_ocultas}")
        
        if tipo_archivo in ["PSD", "TIFF"]:
            indicators.append(f"Formato {tipo_archivo} soporta capas - análisis completo disponible")
        elif tipo_archivo in ["JPEG", "PNG"]:
            indicators.append(f"Formato {tipo_archivo} no soporta capas nativas")
        
        if capas_ocultas > 3:
            indicators.append("Múltiples capas ocultas - posible manipulación extensa")
        
        if total_capas > 5 and capas_ocultas > 1:
            indicators.append("Documento complejo con capas ocultas - posible edición profesional")
        
        if capas_sospechosas:
            indicators.append(f"{len(capas_sospechosas)} capas marcadas como sospechosas")
        
        return indicators
    
    def _generate_analysis_notes(self, analysis_result: Dict) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre detección de capas
        tiene_capas = analysis_result.get("tiene_capas", False)
        if tiene_capas:
            notes.append("Capas detectadas en la imagen")
        else:
            notes.append("No se detectaron capas en la imagen")
        
        # Notas sobre número de capas
        total_capas = analysis_result.get("total_capas", 0)
        if total_capas > 0:
            notes.append(f"Total de capas: {total_capas}")
        else:
            notes.append("No se detectaron capas")
        
        # Notas sobre capas ocultas
        capas_ocultas = analysis_result.get("capas_ocultas", 0)
        if capas_ocultas > 0:
            notes.append(f"Capas ocultas: {capas_ocultas}")
        else:
            notes.append("No se detectaron capas ocultas")
        
        # Notas sobre tipo de archivo
        tipo_archivo = analysis_result.get("tipo_archivo", "unknown")
        notes.append(f"Tipo de archivo: {tipo_archivo}")
        
        if tipo_archivo in ["PSD", "TIFF"]:
            notes.append("Formato soporta capas nativas")
        elif tipo_archivo in ["JPEG", "PNG"]:
            notes.append("Formato no soporta capas nativas")
        
        # Notas sobre capas específicas
        capas = analysis_result.get("capas", [])
        if capas:
            notes.append(f"Detalles de capas: {len(capas)} capas analizadas")
            
            # Analizar visibilidad de capas
            capas_visibles = sum(1 for capa in capas if capa.get("visible", True))
            capas_ocultas_count = len(capas) - capas_visibles
            if capas_ocultas_count > 0:
                notes.append(f"Capas visibles: {capas_visibles}, Capas ocultas: {capas_ocultas_count}")
        else:
            notes.append("No se detectaron capas para analizar")
        
        # Notas sobre modos de mezcla
        modos_mezcla = analysis_result.get("modos_mezcla", [])
        if modos_mezcla:
            notes.append(f"Modos de mezcla detectados: {', '.join(modos_mezcla)}")
        else:
            notes.append("No se detectaron modos de mezcla")
        
        # Notas sobre capas sospechosas
        capas_sospechosas = analysis_result.get("sospechosas", [])
        if capas_sospechosas:
            notes.append(f"Capas sospechosas: {len(capas_sospechosas)}")
        else:
            notes.append("No se detectaron capas sospechosas")
        
        # Notas específicas sobre análisis forense
        notes.append("Análisis de capas ocultas completado")
        notes.append("Las capas ocultas pueden contener información no visible que modifica el contenido aparente")
        
        return notes
