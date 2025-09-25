"""
Implementación del servicio de análisis de extracción de texto OCR.

Utiliza el helper OcrExtractionAnalyzer para realizar el análisis de extracción de texto OCR.
"""

import time
from typing import Dict, Any, List
from domain.ports.forensic_analysis.check_extraccion_texto_ocr_service import ExtraccionTextoOcrServicePort
from domain.entities.forensic_analysis.check_extraccion_texto_ocr_result import ExtraccionTextoOcrResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_extraccion_texto_ocr.ocr_extraction_analyzer import OcrExtractionAnalyzer
import config


class ExtraccionTextoOcrServiceAdapter(ExtraccionTextoOcrServicePort):
    """Adaptador para el servicio de análisis de extracción de texto OCR"""
    
    def __init__(self):
        self.ocr_extraction_analyzer = OcrExtractionAnalyzer()
    
    def analyze_image_ocr_extraction(self, image_bytes: bytes) -> ExtraccionTextoOcrResult:
        """
        Analiza la extracción de texto OCR en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            ExtraccionTextoOcrResult: Resultado del análisis de extracción de texto OCR
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de extracción OCR
            analysis_result = self.ocr_extraction_analyzer.analyze_image_ocr_extraction(image_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return ExtraccionTextoOcrResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            texto_extraido = analysis_result.get("texto_extraido", False)
            calidad_extraccion = analysis_result.get("calidad_extraccion", "muy_mala")
            confianza_promedio = analysis_result.get("confianza_promedio", 0.0)
            cantidad_palabras = analysis_result.get("cantidad_palabras", 0)
            cantidad_caracteres = analysis_result.get("cantidad_caracteres", 0)
            palabras_detectadas = analysis_result.get("palabras_detectadas", [])
            caracteres_legibles = analysis_result.get("caracteres_legibles", 0)
            caracteres_no_legibles = analysis_result.get("caracteres_no_legibles", 0)
            indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                texto_extraido, calidad_extraccion, confianza_promedio, 
                cantidad_palabras, caracteres_legibles, caracteres_no_legibles
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result)
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return ExtraccionTextoOcrResult(
                check_name="Análisis de extracción de texto OCR",
                texto_extraido=texto_extraido,
                calidad_extraccion=calidad_extraccion,
                confianza_promedio=confianza_promedio,
                cantidad_palabras=cantidad_palabras,
                cantidad_caracteres=cantidad_caracteres,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="image",
                palabras_detectadas=palabras_detectadas,
                caracteres_legibles=caracteres_legibles,
                caracteres_no_legibles=caracteres_no_legibles,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(image_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return ExtraccionTextoOcrResult.create_error_result(
                f"Error en análisis de extracción de texto OCR: {str(e)}"
            )
    
    def _calculate_risk_and_confidence(self, texto_extraido: bool, calidad_extraccion: str, 
                                     confianza_promedio: float, cantidad_palabras: int, 
                                     caracteres_legibles: int, caracteres_no_legibles: int) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no se extrajo texto, riesgo alto
        if not texto_extraido:
            return "HIGH", 0.9
        
        # Determinar nivel de riesgo basado en calidad de extracción
        if calidad_extraccion == "muy_mala" or confianza_promedio < 0.2:
            risk_level = "HIGH"
            confidence = 0.9
        elif calidad_extraccion == "mala" or confianza_promedio < 0.4:
            risk_level = "HIGH"
            confidence = 0.8
        elif calidad_extraccion == "regular" or confianza_promedio < 0.6:
            risk_level = "MEDIUM"
            confidence = 0.7
        elif calidad_extraccion == "buena" or confianza_promedio < 0.8:
            risk_level = "LOW"
            confidence = 0.6
        else:
            risk_level = "LOW"
            confidence = 0.5
        
        # Ajustar riesgo basado en cantidad de texto
        if cantidad_palabras < 3:
            risk_level = "HIGH"
            confidence = 0.9
        elif cantidad_palabras < 10 and risk_level != "HIGH":
            risk_level = "MEDIUM"
            confidence = 0.8
        
        # Ajustar riesgo basado en ratio de caracteres legibles
        total_caracteres = caracteres_legibles + caracteres_no_legibles
        if total_caracteres > 0:
            ratio_legibles = caracteres_legibles / total_caracteres
            if ratio_legibles < 0.3:
                risk_level = "HIGH"
                confidence = 0.9
            elif ratio_legibles < 0.5 and risk_level != "HIGH":
                risk_level = "MEDIUM"
                confidence = 0.8
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, analysis_result: Dict) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("extraccion_texto_ocr", 30)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_analysis_notes(self, analysis_result: Dict) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre extracción de texto
        texto_extraido = analysis_result.get("texto_extraido", False)
        if texto_extraido:
            notes.append("Texto extraído exitosamente de la imagen")
        else:
            notes.append("No se pudo extraer texto de la imagen")
            notes.append("Posible manipulación o formato no estándar")
        
        # Notas sobre calidad de extracción
        calidad_extraccion = analysis_result.get("calidad_extraccion", "muy_mala")
        notes.append(f"Calidad de extracción: {calidad_extraccion}")
        
        # Notas sobre confianza promedio
        confianza_promedio = analysis_result.get("confianza_promedio", 0.0)
        notes.append(f"Confianza promedio de OCR: {confianza_promedio:.2f}")
        
        # Notas sobre cantidad de palabras
        cantidad_palabras = analysis_result.get("cantidad_palabras", 0)
        if cantidad_palabras > 0:
            notes.append(f"Palabras detectadas: {cantidad_palabras}")
        else:
            notes.append("No se detectaron palabras")
        
        # Notas sobre caracteres
        caracteres_legibles = analysis_result.get("caracteres_legibles", 0)
        caracteres_no_legibles = analysis_result.get("caracteres_no_legibles", 0)
        total_caracteres = caracteres_legibles + caracteres_no_legibles
        
        if total_caracteres > 0:
            notes.append(f"Caracteres totales: {total_caracteres}")
            notes.append(f"Caracteres legibles: {caracteres_legibles}")
            notes.append(f"Caracteres no legibles: {caracteres_no_legibles}")
            
            ratio_legibles = caracteres_legibles / total_caracteres
            notes.append(f"Ratio de legibilidad: {ratio_legibles:.2f}")
        else:
            notes.append("No se detectaron caracteres")
        
        # Notas sobre indicadores sospechosos
        indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
        if indicadores_sospechosos:
            notes.append(f"Se detectaron {len(indicadores_sospechosos)} indicadores sospechosos")
            for indicador in indicadores_sospechosos[:3]:  # Mostrar solo los primeros 3
                notes.append(f"- {indicador}")
        else:
            notes.append("No se detectaron indicadores sospechosos")
        
        # Notas específicas sobre OCR
        notes.append("Análisis de extracción de texto OCR completado")
        notes.append("La incapacidad de extraer texto puede indicar manipulación")
        
        return notes
