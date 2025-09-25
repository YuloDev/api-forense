"""
Implementación del servicio de análisis de actualizaciones incrementales.

Utiliza el helper ActualizacionesAnalyzer para realizar el análisis de actualizaciones incrementales.
"""

import time
from typing import Dict, Any, List
from domain.ports.forensic_analysis.check_actualizaciones_incrementales_service import ActualizacionesIncrementalesServicePort
from domain.entities.forensic_analysis.check_actualizaciones_incrementales_result import ActualizacionesIncrementalesResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_actualizaciones_incrementales.actualizaciones_analyzer import ActualizacionesAnalyzer
import config


class ActualizacionesIncrementalesServiceAdapter(ActualizacionesIncrementalesServicePort):
    """Adaptador para el servicio de análisis de actualizaciones incrementales"""
    
    def __init__(self):
        self.actualizaciones_analyzer = ActualizacionesAnalyzer()
    
    def analyze_pdf_actualizaciones(self, pdf_bytes: bytes) -> ActualizacionesIncrementalesResult:
        """
        Analiza actualizaciones incrementales en un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            ActualizacionesIncrementalesResult: Resultado del análisis de actualizaciones incrementales
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de actualizaciones
            analysis_result = self.actualizaciones_analyzer.analyze_pdf_actualizaciones(pdf_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return ActualizacionesIncrementalesResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            actualizaciones_detectadas = analysis_result.get("actualizaciones_detectadas", False)
            cantidad_actualizaciones = analysis_result.get("cantidad_actualizaciones", 0)
            actualizaciones_sospechosas = analysis_result.get("actualizaciones_sospechosas", 0)
            actualizaciones_encontradas = analysis_result.get("actualizaciones_encontradas", [])
            fechas_actualizacion = analysis_result.get("fechas_actualizacion", [])
            tipos_actualizacion = analysis_result.get("tipos_actualizacion", [])
            indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                actualizaciones_detectadas, cantidad_actualizaciones, actualizaciones_sospechosas, 
                fechas_actualizacion, tipos_actualizacion
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, "pdf")
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return ActualizacionesIncrementalesResult(
                check_name="Análisis de actualizaciones incrementales",
                actualizaciones_detectadas=actualizaciones_detectadas,
                cantidad_actualizaciones=cantidad_actualizaciones,
                actualizaciones_sospechosas=actualizaciones_sospechosas,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="pdf",
                actualizaciones_encontradas=actualizaciones_encontradas,
                fechas_actualizacion=fechas_actualizacion,
                tipos_actualizacion=tipos_actualizacion,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(pdf_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return ActualizacionesIncrementalesResult.create_error_result(
                f"Error en análisis de actualizaciones incrementales PDF: {str(e)}"
            )
    
    def analyze_image_actualizaciones(self, image_bytes: bytes) -> ActualizacionesIncrementalesResult:
        """
        Analiza actualizaciones incrementales en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            ActualizacionesIncrementalesResult: Resultado del análisis de actualizaciones incrementales
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de actualizaciones
            analysis_result = self.actualizaciones_analyzer.analyze_image_actualizaciones(image_bytes)
            
            # Extraer información del análisis
            actualizaciones_detectadas = analysis_result.get("actualizaciones_detectadas", False)
            cantidad_actualizaciones = analysis_result.get("cantidad_actualizaciones", 0)
            actualizaciones_sospechosas = analysis_result.get("actualizaciones_sospechosas", 0)
            actualizaciones_encontradas = analysis_result.get("actualizaciones_encontradas", [])
            fechas_actualizacion = analysis_result.get("fechas_actualizacion", [])
            tipos_actualizacion = analysis_result.get("tipos_actualizacion", [])
            indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                actualizaciones_detectadas, cantidad_actualizaciones, actualizaciones_sospechosas, 
                fechas_actualizacion, tipos_actualizacion
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, "image")
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return ActualizacionesIncrementalesResult(
                check_name="Análisis de actualizaciones incrementales",
                actualizaciones_detectadas=actualizaciones_detectadas,
                cantidad_actualizaciones=cantidad_actualizaciones,
                actualizaciones_sospechosas=actualizaciones_sospechosas,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="image",
                actualizaciones_encontradas=actualizaciones_encontradas,
                fechas_actualizacion=fechas_actualizacion,
                tipos_actualizacion=tipos_actualizacion,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(image_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return ActualizacionesIncrementalesResult.create_error_result(
                f"Error en análisis de actualizaciones incrementales de imagen: {str(e)}"
            )
    
    def _calculate_risk_and_confidence(self, actualizaciones_detectadas: bool, cantidad_actualizaciones: int, 
                                     actualizaciones_sospechosas: int, fechas_actualizacion: List[str], 
                                     tipos_actualizacion: List[str]) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no hay actualizaciones, riesgo bajo
        if not actualizaciones_detectadas:
            return "LOW", 0.8
        
        # Determinar nivel de riesgo basado en actualizaciones detectadas
        if actualizaciones_sospechosas > 0 or cantidad_actualizaciones > 5:
            risk_level = "HIGH"
            confidence = 0.9
        elif cantidad_actualizaciones > 2 or len(fechas_actualizacion) > 1 or len(tipos_actualizacion) > 1:
            risk_level = "MEDIUM"
            confidence = 0.7
        else:
            risk_level = "LOW"
            confidence = 0.6
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, analysis_result: Dict) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("actualizaciones_incrementales", 3)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_analysis_notes(self, analysis_result: Dict, source_type: str) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre actualizaciones detectadas
        actualizaciones_detectadas = analysis_result.get("actualizaciones_detectadas", False)
        if actualizaciones_detectadas:
            notes.append("Actualizaciones incrementales detectadas en el documento")
        else:
            notes.append("No se detectaron actualizaciones incrementales en el documento")
        
        # Notas sobre cantidad de actualizaciones
        cantidad_actualizaciones = analysis_result.get("cantidad_actualizaciones", 0)
        if cantidad_actualizaciones > 0:
            notes.append(f"Total de actualizaciones encontradas: {cantidad_actualizaciones}")
        else:
            notes.append("No se encontraron actualizaciones")
        
        # Notas sobre actualizaciones sospechosas
        actualizaciones_sospechosas = analysis_result.get("actualizaciones_sospechosas", 0)
        if actualizaciones_sospechosas > 0:
            notes.append(f"Actualizaciones con patrones sospechosos: {actualizaciones_sospechosas}")
        else:
            notes.append("No se detectaron actualizaciones sospechosas")
        
        # Notas sobre fechas de actualización
        fechas_actualizacion = analysis_result.get("fechas_actualizacion", [])
        if fechas_actualizacion:
            notes.append(f"Fechas de actualización detectadas: {len(fechas_actualizacion)}")
            for fecha in fechas_actualizacion[:3]:  # Mostrar solo las primeras 3
                notes.append(f"- {fecha}")
        else:
            notes.append("No se detectaron fechas de actualización")
        
        # Notas sobre tipos de actualización
        tipos_actualizacion = analysis_result.get("tipos_actualizacion", [])
        if tipos_actualizacion:
            notes.append(f"Tipos de actualización detectados: {len(tipos_actualizacion)}")
            for tipo in tipos_actualizacion[:3]:  # Mostrar solo los primeros 3
                notes.append(f"- {tipo}")
        else:
            notes.append("No se detectaron tipos de actualización")
        
        # Notas sobre indicadores sospechosos
        indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
        if indicadores_sospechosos:
            notes.append(f"Se detectaron {len(indicadores_sospechosos)} indicadores sospechosos")
            for indicador in indicadores_sospechosos[:3]:  # Mostrar solo los primeros 3
                notes.append(f"- {indicador}")
        else:
            notes.append("No se detectaron indicadores sospechosos")
        
        # Notas específicas por tipo de archivo
        if source_type == "pdf":
            notes.append("Análisis de actualizaciones incrementales PDF completado")
        else:
            notes.append("Análisis de actualizaciones incrementales de imagen completado")
            notes.append("Las imágenes no pueden contener actualizaciones incrementales")
        
        return notes
