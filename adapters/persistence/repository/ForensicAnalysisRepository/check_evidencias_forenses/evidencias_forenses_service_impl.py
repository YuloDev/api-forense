"""
Implementación del servicio de análisis de evidencias forenses.

Utiliza el helper EvidenciasForensesAnalyzer para realizar el análisis usando la lógica existente.
"""

import time
from typing import Dict, Any, List
from domain.ports.forensic_analysis.check_evidencias_forenses_service import EvidenciasForensesServicePort
from domain.entities.forensic_analysis.check_evidencias_forenses_result import EvidenciasForensesResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_evidencias_forenses.evidencias_forenses_analyzer import EvidenciasForensesAnalyzer
import config


class EvidenciasForensesServiceAdapter(EvidenciasForensesServicePort):
    """Adaptador para el servicio de análisis de evidencias forenses"""
    
    def __init__(self):
        self.evidencias_forenses_analyzer = EvidenciasForensesAnalyzer()
    
    def analyze_image_evidencias_forenses(self, image_bytes: bytes) -> EvidenciasForensesResult:
        """
        Analiza evidencias forenses en una imagen usando la lógica existente.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            EvidenciasForensesResult: Resultado del análisis de evidencias forenses
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de evidencias forenses
            analysis_result = self.evidencias_forenses_analyzer.analyze_image_evidencias_forenses(image_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return EvidenciasForensesResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            evidencias_forenses_detectadas = len(analysis_result.get("evidencias", [])) > 0
            grado_confianza = analysis_result.get("grado_confianza", "BAJO")
            porcentaje_confianza = analysis_result.get("porcentaje_confianza", 0.0)
            puntuacion = analysis_result.get("puntuacion", 0)
            max_puntuacion = analysis_result.get("max_puntuacion", 0)
            es_screenshot = analysis_result.get("es_screenshot", False)
            tipo_imagen = analysis_result.get("tipo_imagen", "unknown")
            evidencias = analysis_result.get("evidencias", [])
            metadatos = analysis_result.get("metadatos", {})
            compresion = analysis_result.get("compresion", {})
            cuadricula_jpeg = analysis_result.get("cuadricula_jpeg", {})
            texto_sintetico = analysis_result.get("texto_sintetico", {})
            ela = analysis_result.get("ela", {})
            ruido_bordes = analysis_result.get("ruido_bordes", {})
            hashes = analysis_result.get("hashes", {})
            overlays = analysis_result.get("overlays", {})
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                grado_confianza, porcentaje_confianza, evidencias_forenses_detectadas
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar indicadores sospechosos
            indicadores_sospechosos = self._generate_suspicious_indicators(
                evidencias_forenses_detectadas, grado_confianza, evidencias, es_screenshot
            )
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result)
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return EvidenciasForensesResult(
                check_name="Análisis de evidencias forenses",
                evidencias_forenses_detectadas=evidencias_forenses_detectadas,
                grado_confianza=grado_confianza,
                porcentaje_confianza=porcentaje_confianza,
                puntuacion=puntuacion,
                max_puntuacion=max_puntuacion,
                es_screenshot=es_screenshot,
                tipo_imagen=tipo_imagen,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="image",
                evidencias=evidencias,
                metadatos=metadatos,
                compresion=compresion,
                cuadricula_jpeg=cuadricula_jpeg,
                texto_sintetico=texto_sintetico,
                ela=ela,
                ruido_bordes=ruido_bordes,
                hashes=hashes,
                overlays=overlays,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(image_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return EvidenciasForensesResult.create_error_result(
                f"Error en análisis de evidencias forenses: {str(e)}"
            )
    
    def _calculate_risk_and_confidence(self, grado_confianza: str, 
                                     porcentaje_confianza: float, 
                                     evidencias_forenses_detectadas: bool) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no hay evidencias forenses detectadas, riesgo bajo
        if not evidencias_forenses_detectadas:
            return "LOW", 0.8
        
        # Determinar nivel de riesgo basado en grado de confianza
        if grado_confianza == "ALTO":
            risk_level = "HIGH"
            confidence = min(porcentaje_confianza / 100.0, 1.0)
        elif grado_confianza == "MEDIO":
            risk_level = "HIGH"
            confidence = min(porcentaje_confianza / 100.0, 0.8)
        elif grado_confianza == "BAJO":
            risk_level = "MEDIUM"
            confidence = min(porcentaje_confianza / 100.0, 0.6)
        else:  # ERROR
            risk_level = "LOW"
            confidence = 0.0
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, analysis_result: Dict) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("evidencias_forenses", 15)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_suspicious_indicators(self, evidencias_forenses_detectadas: bool, 
                                      grado_confianza: str, evidencias: List[str], 
                                      es_screenshot: bool) -> List[str]:
        """Genera indicadores sospechosos basados en el análisis"""
        indicators = []
        
        if evidencias_forenses_detectadas:
            indicators.append("Evidencias forenses detectadas en la imagen")
        
        if grado_confianza == "ALTO":
            indicators.append("Alto grado de confianza en la detección de manipulación")
        elif grado_confianza == "MEDIO":
            indicators.append("Grado medio de confianza en la detección de manipulación")
        elif grado_confianza == "BAJO":
            indicators.append("Bajo grado de confianza en la detección de manipulación")
        
        if es_screenshot:
            indicators.append("Imagen identificada como screenshot/web")
        
        if len(evidencias) > 5:
            indicators.append("Múltiples evidencias forenses detectadas")
        
        if len(evidencias) > 10:
            indicators.append("Numerosas evidencias forenses - posible manipulación extensa")
        
        # Analizar tipos de evidencias específicas
        evidencias_altas = [e for e in evidencias if "🚨" in e]
        if evidencias_altas:
            indicators.append(f"{len(evidencias_altas)} evidencias de alta prioridad detectadas")
        
        evidencias_medias = [e for e in evidencias if "⚠️" in e]
        if evidencias_medias:
            indicators.append(f"{len(evidencias_medias)} evidencias de prioridad media detectadas")
        
        return indicators
    
    def _generate_analysis_notes(self, analysis_result: Dict) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre detección general
        evidencias_forenses_detectadas = len(analysis_result.get("evidencias", [])) > 0
        if evidencias_forenses_detectadas:
            notes.append("Evidencias forenses detectadas en la imagen")
        else:
            notes.append("No se detectaron evidencias forenses en la imagen")
        
        # Notas sobre grado de confianza
        grado_confianza = analysis_result.get("grado_confianza", "BAJO")
        porcentaje_confianza = analysis_result.get("porcentaje_confianza", 0.0)
        notes.append(f"Grado de confianza: {grado_confianza} ({porcentaje_confianza:.1f}%)")
        
        # Notas sobre puntuación
        puntuacion = analysis_result.get("puntuacion", 0)
        max_puntuacion = analysis_result.get("max_puntuacion", 0)
        if max_puntuacion > 0:
            notes.append(f"Puntuación: {puntuacion}/{max_puntuacion}")
        else:
            notes.append("Puntuación: No calculada")
        
        # Notas sobre tipo de imagen
        es_screenshot = analysis_result.get("es_screenshot", False)
        tipo_imagen = analysis_result.get("tipo_imagen", "unknown")
        if es_screenshot:
            notes.append(f"Tipo de imagen: {tipo_imagen} (screenshot/web)")
        else:
            notes.append(f"Tipo de imagen: {tipo_imagen}")
        
        # Notas sobre evidencias específicas
        evidencias = analysis_result.get("evidencias", [])
        if evidencias:
            notes.append(f"Total de evidencias: {len(evidencias)}")
            
            # Contar por tipo de evidencia
            evidencias_altas = [e for e in evidencias if "🚨" in e]
            evidencias_medias = [e for e in evidencias if "⚠️" in e]
            evidencias_info = [e for e in evidencias if "ℹ️" in e]
            
            if evidencias_altas:
                notes.append(f"Evidencias de alta prioridad: {len(evidencias_altas)}")
            if evidencias_medias:
                notes.append(f"Evidencias de prioridad media: {len(evidencias_medias)}")
            if evidencias_info:
                notes.append(f"Evidencias informativas: {len(evidencias_info)}")
        else:
            notes.append("No se detectaron evidencias específicas")
        
        # Notas sobre análisis específicos
        metadatos = analysis_result.get("metadatos", {})
        if metadatos.get("software_edicion"):
            notes.append("Análisis de metadatos: Software de edición detectado")
        
        texto_sintetico = analysis_result.get("texto_sintetico", {})
        if texto_sintetico.get("tiene_texto_sintetico"):
            notes.append("Análisis de texto sintético: Texto sintético detectado")
        
        ela = analysis_result.get("ela", {})
        if ela.get("tiene_ediciones"):
            notes.append("Análisis ELA: Ediciones detectadas")
        
        ruido_bordes = analysis_result.get("ruido_bordes", {})
        if ruido_bordes.get("ruido_analisis", {}).get("inconsistencias_ruido"):
            notes.append("Análisis de ruido: Inconsistencias detectadas")
        
        overlays = analysis_result.get("overlays", {})
        n_over = overlays.get("resumen", {}).get("n_overlays", 0)
        if n_over > 0:
            notes.append(f"Análisis de overlays: {n_over} overlays detectados")
        
        # Notas específicas sobre análisis forense
        notes.append("Análisis de evidencias forenses completado")
        notes.append("Los indicadores técnicos sugieren si la imagen ha sido modificada o manipulada digitalmente")
        
        return notes
