"""
Implementación del servicio de análisis ELA sospechoso.

Utiliza el helper ElaAnalyzer para realizar el análisis de áreas ELA sospechosas.
"""

import time
from typing import Dict, Any, List
from domain.ports.forensic_analysis.check_analisis_ela_sospechoso_service import AnalisisElaSospechosoServicePort
from domain.entities.forensic_analysis.check_analisis_ela_sospechoso_result import AnalisisElaSospechosoResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_analisis_ela_sospechoso.ela_analyzer import ElaAnalyzer
import config


class AnalisisElaSospechosoServiceAdapter(AnalisisElaSospechosoServicePort):
    """Adaptador para el servicio de análisis ELA sospechoso"""
    
    def __init__(self):
        self.ela_analyzer = ElaAnalyzer()
    
    def analyze_image_ela(self, image_bytes: bytes) -> AnalisisElaSospechosoResult:
        """
        Analiza áreas ELA sospechosas en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            AnalisisElaSospechosoResult: Resultado del análisis ELA sospechoso
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis ELA
            analysis_result = self.ela_analyzer.analyze_image_ela(image_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return AnalisisElaSospechosoResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            areas_ela_detectadas = analysis_result.get("areas_ela_detectadas", False)
            nivel_sospecha = analysis_result.get("nivel_sospecha", "bajo")
            areas_sospechosas = analysis_result.get("areas_sospechosas", 0)
            nivel_compresion_inconsistente = analysis_result.get("nivel_compresion_inconsistente", 0)
            areas_recomprimidas = analysis_result.get("areas_recomprimidas", 0)
            areas_detectadas = analysis_result.get("areas_detectadas", [])
            niveles_ela = analysis_result.get("niveles_ela", [])
            patrones_compresion = analysis_result.get("patrones_compresion", [])
            indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                areas_ela_detectadas, nivel_sospecha, areas_sospechosas,
                nivel_compresion_inconsistente, areas_recomprimidas
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result)
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return AnalisisElaSospechosoResult(
                check_name="Análisis ELA sospechoso",
                areas_ela_detectadas=areas_ela_detectadas,
                nivel_sospecha=nivel_sospecha,
                areas_sospechosas=areas_sospechosas,
                nivel_compresion_inconsistente=nivel_compresion_inconsistente,
                areas_recomprimidas=areas_recomprimidas,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="image",
                areas_detectadas=areas_detectadas,
                niveles_ela=niveles_ela,
                patrones_compresion=patrones_compresion,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(image_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return AnalisisElaSospechosoResult.create_error_result(
                f"Error en análisis ELA sospechoso: {str(e)}"
            )
    
    def _calculate_risk_and_confidence(self, areas_ela_detectadas: bool, nivel_sospecha: str, 
                                     areas_sospechosas: int, nivel_compresion_inconsistente: int, 
                                     areas_recomprimidas: int) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no hay áreas ELA detectadas, riesgo bajo
        if not areas_ela_detectadas:
            return "LOW", 0.8
        
        # Determinar nivel de riesgo basado en métricas
        if nivel_sospecha == "muy_alto" or areas_sospechosas > 5:
            risk_level = "HIGH"
            confidence = 0.9
        elif nivel_sospecha == "alto" or areas_sospechosas > 2 or nivel_compresion_inconsistente > 3:
            risk_level = "HIGH"
            confidence = 0.8
        elif nivel_sospecha == "medio" or areas_sospechosas > 0 or nivel_compresion_inconsistente > 0:
            risk_level = "MEDIUM"
            confidence = 0.7
        else:
            risk_level = "LOW"
            confidence = 0.6
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, analysis_result: Dict) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("analisis_ela_sospechoso", 12)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_analysis_notes(self, analysis_result: Dict) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre áreas ELA detectadas
        areas_ela_detectadas = analysis_result.get("areas_ela_detectadas", False)
        if areas_ela_detectadas:
            notes.append("Áreas ELA sospechosas detectadas en la imagen")
        else:
            notes.append("No se detectaron áreas ELA sospechosas")
        
        # Notas sobre nivel de sospecha
        nivel_sospecha = analysis_result.get("nivel_sospecha", "bajo")
        notes.append(f"Nivel de sospecha ELA: {nivel_sospecha}")
        
        # Notas sobre áreas sospechosas
        areas_sospechosas = analysis_result.get("areas_sospechosas", 0)
        if areas_sospechosas > 0:
            notes.append(f"Áreas sospechosas detectadas: {areas_sospechosas}")
        else:
            notes.append("No se detectaron áreas sospechosas")
        
        # Notas sobre nivel de compresión inconsistente
        nivel_compresion_inconsistente = analysis_result.get("nivel_compresion_inconsistente", 0)
        if nivel_compresion_inconsistente > 0:
            notes.append(f"Patrones de compresión inconsistentes: {nivel_compresion_inconsistente}")
        else:
            notes.append("No se detectaron patrones de compresión inconsistentes")
        
        # Notas sobre áreas re-comprimidas
        areas_recomprimidas = analysis_result.get("areas_recomprimidas", 0)
        if areas_recomprimidas > 0:
            notes.append(f"Áreas re-comprimidas detectadas: {areas_recomprimidas}")
        else:
            notes.append("No se detectaron áreas re-comprimidas")
        
        # Notas sobre áreas detectadas
        areas_detectadas = analysis_result.get("areas_detectadas", [])
        if areas_detectadas:
            notes.append(f"Total de áreas analizadas: {len(areas_detectadas)}")
        else:
            notes.append("No se detectaron áreas para analizar")
        
        # Notas sobre niveles ELA
        niveles_ela = analysis_result.get("niveles_ela", [])
        if niveles_ela:
            notes.append(f"Total de niveles ELA analizados: {len(niveles_ela)}")
        else:
            notes.append("No se detectaron niveles ELA")
        
        # Notas sobre patrones de compresión
        patrones_compresion = analysis_result.get("patrones_compresion", [])
        if patrones_compresion:
            notes.append(f"Total de patrones de compresión analizados: {len(patrones_compresion)}")
        else:
            notes.append("No se detectaron patrones de compresión")
        
        # Notas sobre indicadores sospechosos
        indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
        if indicadores_sospechosos:
            notes.append(f"Se detectaron {len(indicadores_sospechosos)} indicadores sospechosos")
            for indicador in indicadores_sospechosos[:3]:  # Mostrar solo los primeros 3
                notes.append(f"- {indicador}")
        else:
            notes.append("No se detectaron indicadores sospechosos")
        
        # Notas específicas sobre análisis forense
        notes.append("Análisis ELA (Error Level Analysis) completado")
        notes.append("El ELA detecta áreas que han sido editadas o re-comprimidas")
        
        return notes
