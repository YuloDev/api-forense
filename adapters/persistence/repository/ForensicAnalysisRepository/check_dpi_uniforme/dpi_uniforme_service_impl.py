"""
Implementación del servicio de análisis de uniformidad DPI.

Utiliza el helper DpiAnalyzer para realizar el análisis de uniformidad DPI.
"""

import time
from typing import Dict, Any, List
from domain.ports.forensic_analysis.check_dpi_uniforme_service import DpiUniformeServicePort
from domain.entities.forensic_analysis.check_dpi_uniforme_result import DpiUniformeResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_dpi_uniforme.dpi_analyzer import DpiAnalyzer
import config


class DpiUniformeServiceAdapter(DpiUniformeServicePort):
    """Adaptador para el servicio de análisis de uniformidad DPI"""
    
    def __init__(self):
        self.dpi_analyzer = DpiAnalyzer()
    
    def analyze_pdf_dpi(self, pdf_bytes: bytes) -> DpiUniformeResult:
        """
        Analiza la uniformidad DPI de un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            DpiUniformeResult: Resultado del análisis de uniformidad DPI
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de DPI
            analysis_result = self.dpi_analyzer.analyze_pdf_dpi(pdf_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return DpiUniformeResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            dpi_values = analysis_result.get("dpi_values", [])
            imagenes_analizadas = analysis_result.get("image_count", 0)
            dpi_promedio = analysis_result.get("dpi_promedio", 0.0)
            dpi_estandar = analysis_result.get("dpi_estandar", 0)
            variacion_dpi = analysis_result.get("variacion_dpi", 0.0)
            uniformidad_score = analysis_result.get("uniformidad_score", 0.0)
            dpi_sospechosos = analysis_result.get("dpi_sospechosos", [])
            indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                variacion_dpi, uniformidad_score, dpi_sospechosos, imagenes_analizadas
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, imagenes_analizadas)
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return DpiUniformeResult(
                check_name="Análisis de uniformidad DPI",
                imagenes_analizadas=imagenes_analizadas,
                dpi_promedio=dpi_promedio,
                dpi_estandar=dpi_estandar,
                variacion_dpi=variacion_dpi,
                uniformidad_score=uniformidad_score,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="pdf",
                dpi_detectados=dpi_values,
                dpi_mas_comun=analysis_result.get("dpi_mas_comun", 0.0),
                desviacion_estandar=analysis_result.get("desviacion_estandar", 0.0),
                rango_dpi=analysis_result.get("rango_dpi", []),
                dpi_sospechosos=dpi_sospechosos,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(pdf_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return DpiUniformeResult.create_error_result(
                f"Error en análisis de uniformidad DPI PDF: {str(e)}"
            )
    
    def analyze_image_dpi(self, image_bytes: bytes) -> DpiUniformeResult:
        """
        Analiza la uniformidad DPI de una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            DpiUniformeResult: Resultado del análisis de uniformidad DPI
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de DPI
            analysis_result = self.dpi_analyzer.analyze_image_dpi(image_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return DpiUniformeResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            dpi_values = analysis_result.get("dpi_values", [])
            imagenes_analizadas = analysis_result.get("image_count", 0)
            dpi_promedio = analysis_result.get("dpi_promedio", 0.0)
            dpi_estandar = analysis_result.get("dpi_estandar", 0)
            variacion_dpi = analysis_result.get("variacion_dpi", 0.0)
            uniformidad_score = analysis_result.get("uniformidad_score", 0.0)
            dpi_sospechosos = analysis_result.get("dpi_sospechosos", [])
            indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                variacion_dpi, uniformidad_score, dpi_sospechosos, imagenes_analizadas
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, imagenes_analizadas)
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return DpiUniformeResult(
                check_name="Análisis de uniformidad DPI",
                imagenes_analizadas=imagenes_analizadas,
                dpi_promedio=dpi_promedio,
                dpi_estandar=dpi_estandar,
                variacion_dpi=variacion_dpi,
                uniformidad_score=uniformidad_score,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="image",
                dpi_detectados=dpi_values,
                dpi_mas_comun=analysis_result.get("dpi_mas_comun", 0.0),
                desviacion_estandar=analysis_result.get("desviacion_estandar", 0.0),
                rango_dpi=analysis_result.get("rango_dpi", []),
                dpi_sospechosos=dpi_sospechosos,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(image_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return DpiUniformeResult.create_error_result(
                f"Error en análisis de uniformidad DPI de imagen: {str(e)}"
            )
    
    def _calculate_risk_and_confidence(self, variacion_dpi: float, uniformidad_score: float, 
                                     dpi_sospechosos: List[float], imagenes_analizadas: int) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no hay imágenes, riesgo bajo
        if imagenes_analizadas == 0:
            return "LOW", 0.0
        
        # Si solo hay una imagen, riesgo bajo
        if imagenes_analizadas == 1:
            return "LOW", 0.5
        
        # Determinar nivel de riesgo basado en variación y uniformidad
        if variacion_dpi > 0.3 or uniformidad_score < 0.3:
            risk_level = "HIGH"
            confidence = 0.9
        elif variacion_dpi > 0.2 or uniformidad_score < 0.6:
            risk_level = "MEDIUM"
            confidence = 0.7
        else:
            risk_level = "LOW"
            confidence = 0.8
        
        # Ajustar según DPI sospechosos
        if dpi_sospechosos:
            risk_level = "HIGH"
            confidence = 0.9
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, analysis_result: Dict) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("dpi_uniforme", 8)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_analysis_notes(self, analysis_result: Dict, imagenes_analizadas: int) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre métricas básicas
        notes.append(f"Imágenes analizadas: {imagenes_analizadas}")
        notes.append(f"DPI promedio: {analysis_result.get('dpi_promedio', 0.0):.1f}")
        notes.append(f"DPI estándar más cercano: {analysis_result.get('dpi_estandar', 0)}")
        notes.append(f"Variación DPI: {analysis_result.get('variacion_dpi', 0.0):.1%}")
        notes.append(f"Score de uniformidad: {analysis_result.get('uniformidad_score', 0.0):.2f}")
        
        # Notas sobre DPI detectados
        dpi_detectados = analysis_result.get("dpi_detectados", [])
        if dpi_detectados:
            notes.append(f"DPI detectados: {dpi_detectados}")
            if len(dpi_detectados) > 1:
                rango = analysis_result.get("rango_dpi", [])
                if rango:
                    notes.append(f"Rango DPI: {rango[0]:.1f} - {rango[1]:.1f}")
        
        # Notas sobre indicadores sospechosos
        indicadores = analysis_result.get("indicadores_sospechosos", [])
        if indicadores:
            notes.append(f"Se detectaron {len(indicadores)} indicadores sospechosos")
            for indicador in indicadores[:3]:  # Mostrar solo los primeros 3
                notes.append(f"- {indicador}")
        else:
            notes.append("No se detectaron indicadores sospechosos en el DPI")
        
        # Notas sobre uniformidad
        uniformidad_score = analysis_result.get("uniformidad_score", 0.0)
        if uniformidad_score >= 0.8:
            notes.append("Excelente uniformidad en el DPI")
        elif uniformidad_score >= 0.6:
            notes.append("Uniformidad moderada en el DPI")
        else:
            notes.append("Baja uniformidad en el DPI - posible inserción de imágenes")
        
        # Notas sobre variación
        variacion_dpi = analysis_result.get("variacion_dpi", 0.0)
        if variacion_dpi > 0.3:
            notes.append("Variación DPI muy alta - posible manipulación del documento")
        elif variacion_dpi > 0.2:
            notes.append("Variación DPI significativa - posible inserción de imágenes")
        elif variacion_dpi > 0.1:
            notes.append("Variación DPI moderada - revisar consistencia")
        else:
            notes.append("Variación DPI baja - buena consistencia")
        
        return notes
