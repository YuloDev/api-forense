"""
Implementación del servicio de análisis de inconsistencias en ruido y bordes.

Utiliza el helper RuidoBordesAnalyzer para realizar el análisis de inconsistencias en ruido y bordes.
"""

import time
from typing import Dict, Any, List
from domain.ports.forensic_analysis.check_inconsistencias_ruido_bordes_service import InconsistenciasRuidoBordesServicePort
from domain.entities.forensic_analysis.check_inconsistencias_ruido_bordes_result import InconsistenciasRuidoBordesResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_inconsistencias_ruido_bordes.ruido_bordes_analyzer import RuidoBordesAnalyzer
import config


class InconsistenciasRuidoBordesServiceAdapter(InconsistenciasRuidoBordesServicePort):
    """Adaptador para el servicio de análisis de inconsistencias en ruido y bordes"""
    
    def __init__(self):
        self.ruido_bordes_analyzer = RuidoBordesAnalyzer()
    
    def analyze_image_ruido_bordes(self, image_bytes: bytes) -> InconsistenciasRuidoBordesResult:
        """
        Analiza inconsistencias en ruido y bordes en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            InconsistenciasRuidoBordesResult: Resultado del análisis de inconsistencias en ruido y bordes
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de inconsistencias en ruido y bordes
            analysis_result = self.ruido_bordes_analyzer.analyze_image_ruido_bordes(image_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return InconsistenciasRuidoBordesResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            inconsistencias_detectadas = analysis_result.get("inconsistencias_detectadas", False)
            nivel_inconsistencia = analysis_result.get("nivel_inconsistencia", "bajo")
            areas_sospechosas = analysis_result.get("areas_sospechosas", 0)
            patrones_ruido_inconsistentes = analysis_result.get("patrones_ruido_inconsistentes", 0)
            bordes_irregulares = analysis_result.get("bordes_irregulares", 0)
            areas_detectadas = analysis_result.get("areas_detectadas", [])
            patrones_ruido = analysis_result.get("patrones_ruido", [])
            bordes_analizados = analysis_result.get("bordes_analizados", [])
            indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                inconsistencias_detectadas, nivel_inconsistencia, areas_sospechosas,
                patrones_ruido_inconsistentes, bordes_irregulares
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result)
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return InconsistenciasRuidoBordesResult(
                check_name="Análisis de inconsistencias en ruido y bordes",
                inconsistencias_detectadas=inconsistencias_detectadas,
                nivel_inconsistencia=nivel_inconsistencia,
                areas_sospechosas=areas_sospechosas,
                patrones_ruido_inconsistentes=patrones_ruido_inconsistentes,
                bordes_irregulares=bordes_irregulares,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="image",
                areas_detectadas=areas_detectadas,
                patrones_ruido=patrones_ruido,
                bordes_analizados=bordes_analizados,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(image_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return InconsistenciasRuidoBordesResult.create_error_result(
                f"Error en análisis de inconsistencias en ruido y bordes: {str(e)}"
            )
    
    def _calculate_risk_and_confidence(self, inconsistencias_detectadas: bool, 
                                     nivel_inconsistencia: str, areas_sospechosas: int,
                                     patrones_ruido_inconsistentes: int, 
                                     bordes_irregulares: int) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no hay inconsistencias, riesgo bajo
        if not inconsistencias_detectadas:
            return "LOW", 0.8
        
        # Determinar nivel de riesgo basado en métricas
        if nivel_inconsistencia == "muy_alto" or areas_sospechosas > 5:
            risk_level = "HIGH"
            confidence = 0.9
        elif nivel_inconsistencia == "alto" or areas_sospechosas > 2 or patrones_ruido_inconsistentes > 3:
            risk_level = "HIGH"
            confidence = 0.8
        elif nivel_inconsistencia == "medio" or areas_sospechosas > 0 or patrones_ruido_inconsistentes > 0:
            risk_level = "MEDIUM"
            confidence = 0.7
        else:
            risk_level = "LOW"
            confidence = 0.6
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, analysis_result: Dict) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("inconsistencias_ruido_bordes", 18)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_analysis_notes(self, analysis_result: Dict) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre inconsistencias detectadas
        inconsistencias_detectadas = analysis_result.get("inconsistencias_detectadas", False)
        if inconsistencias_detectadas:
            notes.append("Inconsistencias detectadas en patrones de ruido y bordes")
        else:
            notes.append("No se detectaron inconsistencias en patrones de ruido y bordes")
        
        # Notas sobre nivel de inconsistencia
        nivel_inconsistencia = analysis_result.get("nivel_inconsistencia", "bajo")
        notes.append(f"Nivel de inconsistencia: {nivel_inconsistencia}")
        
        # Notas sobre áreas sospechosas
        areas_sospechosas = analysis_result.get("areas_sospechosas", 0)
        if areas_sospechosas > 0:
            notes.append(f"Áreas sospechosas detectadas: {areas_sospechosas}")
        else:
            notes.append("No se detectaron áreas sospechosas")
        
        # Notas sobre patrones de ruido inconsistentes
        patrones_ruido_inconsistentes = analysis_result.get("patrones_ruido_inconsistentes", 0)
        if patrones_ruido_inconsistentes > 0:
            notes.append(f"Patrones de ruido inconsistentes: {patrones_ruido_inconsistentes}")
        else:
            notes.append("No se detectaron patrones de ruido inconsistentes")
        
        # Notas sobre bordes irregulares
        bordes_irregulares = analysis_result.get("bordes_irregulares", 0)
        if bordes_irregulares > 0:
            notes.append(f"Bordes irregulares detectados: {bordes_irregulares}")
        else:
            notes.append("No se detectaron bordes irregulares")
        
        # Notas sobre áreas detectadas
        areas_detectadas = analysis_result.get("areas_detectadas", [])
        if areas_detectadas:
            notes.append(f"Total de áreas analizadas: {len(areas_detectadas)}")
        else:
            notes.append("No se detectaron áreas para analizar")
        
        # Notas sobre patrones de ruido
        patrones_ruido = analysis_result.get("patrones_ruido", [])
        if patrones_ruido:
            notes.append(f"Total de patrones de ruido analizados: {len(patrones_ruido)}")
        else:
            notes.append("No se detectaron patrones de ruido")
        
        # Notas sobre bordes analizados
        bordes_analizados = analysis_result.get("bordes_analizados", [])
        if bordes_analizados:
            notes.append(f"Total de bordes analizados: {len(bordes_analizados)}")
        else:
            notes.append("No se detectaron bordes")
        
        # Notas sobre indicadores sospechosos
        indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
        if indicadores_sospechosos:
            notes.append(f"Se detectaron {len(indicadores_sospechosos)} indicadores sospechosos")
            for indicador in indicadores_sospechosos[:3]:  # Mostrar solo los primeros 3
                notes.append(f"- {indicador}")
        else:
            notes.append("No se detectaron indicadores sospechosos")
        
        # Notas específicas sobre análisis forense
        notes.append("Análisis de inconsistencias en ruido y bordes completado")
        notes.append("Las inconsistencias pueden indicar edición local, clonado o pegado de elementos")
        
        return notes
