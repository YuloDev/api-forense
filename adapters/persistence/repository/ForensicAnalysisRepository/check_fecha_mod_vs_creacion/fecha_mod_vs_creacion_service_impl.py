"""
Implementación del servicio de análisis de fecha modificación vs creación.

Utiliza el helper FechaAnalyzer para realizar el análisis temporal.
"""

import time
from typing import Dict, Any
from domain.ports.forensic_analysis.check_fecha_mod_vs_creacion_service import FechaModVsCreacionServicePort
from domain.entities.forensic_analysis.check_fecha_mod_vs_creacion_result import FechaModVsCreacionResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_fecha_mod_vs_creacion.fecha_analyzer import FechaAnalyzer
import config


class FechaModVsCreacionServiceAdapter(FechaModVsCreacionServicePort):
    """Adaptador para el servicio de análisis de fecha modificación vs creación"""
    
    def __init__(self):
        self.fecha_analyzer = FechaAnalyzer()
    
    def analyze_pdf_dates(self, pdf_bytes: bytes) -> FechaModVsCreacionResult:
        """
        Analiza las fechas de creación y modificación de un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            FechaModVsCreacionResult: Resultado del análisis temporal
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de fechas
            analysis_result = self.fecha_analyzer.analyze_pdf_dates(pdf_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return FechaModVsCreacionResult.create_error_result(
                    analysis_result["error"], 
                    "pdf"
                )
            
            # Extraer información del análisis
            creation_date = analysis_result.get("creation_date")
            modification_date = analysis_result.get("modification_date")
            has_creation_date = analysis_result.get("has_creation_date", False)
            has_modification_date = analysis_result.get("has_modification_date", False)
            
            # Calcular diferencias temporales
            time_diff_hours, time_diff_days = self.fecha_analyzer.calculate_time_difference(
                creation_date, modification_date
            )
            
            # Detectar patrones sospechosos
            suspicious_indicators = self.fecha_analyzer.detect_suspicious_patterns(
                creation_date, modification_date
            )
            
            # Determinar si es sospechoso
            is_suspicious = len(suspicious_indicators) > 0
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                suspicious_indicators, time_diff_days, has_creation_date, has_modification_date
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, suspicious_indicators)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, suspicious_indicators)
            
            # Formatear fechas para display
            creation_date_str = creation_date.strftime("%Y-%m-%d %H:%M:%S") if creation_date else None
            modification_date_str = modification_date.strftime("%Y-%m-%d %H:%M:%S") if modification_date else None
            
            # Formatear diferencia temporal
            time_diff_formatted = self._format_time_difference(time_diff_hours, time_diff_days)
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return FechaModVsCreacionResult(
                check_name="Análisis de fecha modificación vs creación",
                has_creation_date=has_creation_date,
                has_modification_date=has_modification_date,
                creation_date=creation_date,
                modification_date=modification_date,
                time_difference_hours=time_diff_hours,
                time_difference_days=time_diff_days,
                is_suspicious=is_suspicious,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="pdf",
                creation_date_str=creation_date_str,
                modification_date_str=modification_date_str,
                time_difference_formatted=time_diff_formatted,
                suspicious_indicators=suspicious_indicators,
                analysis_notes=analysis_notes,
                file_size_bytes=len(pdf_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return FechaModVsCreacionResult.create_error_result(
                f"Error en análisis de fechas PDF: {str(e)}", 
                "pdf"
            )
    
    def analyze_image_dates(self, image_bytes: bytes) -> FechaModVsCreacionResult:
        """
        Analiza las fechas de creación y modificación de una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            FechaModVsCreacionResult: Resultado del análisis temporal
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de fechas
            analysis_result = self.fecha_analyzer.analyze_image_dates(image_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return FechaModVsCreacionResult.create_error_result(
                    analysis_result["error"], 
                    "image"
                )
            
            # Extraer información del análisis
            creation_date = analysis_result.get("creation_date")
            modification_date = analysis_result.get("modification_date")
            has_creation_date = analysis_result.get("has_creation_date", False)
            has_modification_date = analysis_result.get("has_modification_date", False)
            
            # Calcular diferencias temporales
            time_diff_hours, time_diff_days = self.fecha_analyzer.calculate_time_difference(
                creation_date, modification_date
            )
            
            # Detectar patrones sospechosos
            suspicious_indicators = self.fecha_analyzer.detect_suspicious_patterns(
                creation_date, modification_date
            )
            
            # Determinar si es sospechoso
            is_suspicious = len(suspicious_indicators) > 0
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                suspicious_indicators, time_diff_days, has_creation_date, has_modification_date
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, suspicious_indicators)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, suspicious_indicators)
            
            # Formatear fechas para display
            creation_date_str = creation_date.strftime("%Y-%m-%d %H:%M:%S") if creation_date else None
            modification_date_str = modification_date.strftime("%Y-%m-%d %H:%M:%S") if modification_date else None
            
            # Formatear diferencia temporal
            time_diff_formatted = self._format_time_difference(time_diff_hours, time_diff_days)
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return FechaModVsCreacionResult(
                check_name="Análisis de fecha modificación vs creación",
                has_creation_date=has_creation_date,
                has_modification_date=has_modification_date,
                creation_date=creation_date,
                modification_date=modification_date,
                time_difference_hours=time_diff_hours,
                time_difference_days=time_diff_days,
                is_suspicious=is_suspicious,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="image",
                creation_date_str=creation_date_str,
                modification_date_str=modification_date_str,
                time_difference_formatted=time_diff_formatted,
                suspicious_indicators=suspicious_indicators,
                analysis_notes=analysis_notes,
                file_size_bytes=len(image_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return FechaModVsCreacionResult.create_error_result(
                f"Error en análisis de fechas imagen: {str(e)}", 
                "image"
            )
    
    def _calculate_risk_and_confidence(self, suspicious_indicators: list, time_diff_days: float, 
                                     has_creation_date: bool, has_modification_date: bool) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no hay fechas, riesgo bajo
        if not has_creation_date and not has_modification_date:
            return "LOW", 0.0
        
        # Si no hay fecha de modificación, NO se penaliza (riesgo bajo)
        if not has_modification_date:
            return "LOW", 0.0
        
        # Si no hay fecha de creación pero sí de modificación, riesgo medio
        if not has_creation_date:
            return "MEDIUM", 0.5
        
        # Solo se penaliza si hay AMBAS fechas y hay diferencia
        # Si no hay diferencia temporal (time_diff_days es None), no se penaliza
        if time_diff_days is None:
            return "LOW", 0.0
        
        # Calcular confianza basada en indicadores sospechosos
        confidence = 1.0
        risk_level = "LOW"
        
        # SIEMPRE penalizar si hay diferencia temporal (cualquier diferencia)
        # Según la descripción: "Modificaciones posteriores a la creación pueden sugerir alteraciones del documento original"
        if time_diff_days != 0:  # Cualquier diferencia temporal
            confidence = 0.8
            risk_level = "HIGH"  # Cambiado a HIGH para aplicar penalización completa
        
        # Ajustar confianza según indicadores específicos
        for indicator in suspicious_indicators:
            if "anterior" in indicator.lower():
                confidence = 0.9
                risk_level = "HIGH"
            elif "idénticas" in indicator.lower():
                confidence = 0.8
                risk_level = "HIGH"
            elif "muy grande" in indicator.lower():
                confidence = 0.7
                risk_level = "HIGH"  # Cambiado a HIGH para diferencias muy grandes
            elif "muy pequeña" in indicator.lower():
                confidence = 0.6
                risk_level = "MEDIUM"
            elif "futuro" in indicator.lower():
                confidence = 0.9
                risk_level = "HIGH"
        
        # Ajustar según diferencia temporal específica
        if time_diff_days < 0:  # Modificación anterior a creación
            confidence = 0.9
            risk_level = "HIGH"
        elif time_diff_days == 0:  # Fechas iguales
            confidence = 0.8
            risk_level = "HIGH"
        elif time_diff_days > 365:  # Diferencia muy grande
            confidence = 0.7
            risk_level = "HIGH"  # Cambiado a HIGH para diferencias muy grandes
        elif time_diff_days < 1:  # Diferencia muy pequeña
            confidence = 0.6
            risk_level = "MEDIUM"
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, suspicious_indicators: list) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("fecha_mod_vs_creacion", 12)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_analysis_notes(self, analysis_result: dict, suspicious_indicators: list) -> list:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre disponibilidad de fechas
        if analysis_result.get("has_creation_date"):
            notes.append("Fecha de creación disponible en metadatos")
        else:
            notes.append("Fecha de creación no encontrada en metadatos")
        
        if analysis_result.get("has_modification_date"):
            notes.append("Fecha de modificación disponible en metadatos")
        else:
            notes.append("Fecha de modificación no encontrada en metadatos - NO se penaliza")
        
        # Notas sobre inconsistencias (si las hay)
        if "inconsistencies" in analysis_result:
            for inconsistency in analysis_result["inconsistencies"]:
                notes.append(f"Inconsistencia detectada: {inconsistency}")
        
        # Notas sobre indicadores sospechosos
        if suspicious_indicators:
            notes.append(f"Se detectaron {len(suspicious_indicators)} indicadores sospechosos")
        else:
            if analysis_result.get("has_modification_date"):
                notes.append("No se detectaron indicadores sospechosos en las fechas")
            else:
                notes.append("Sin fecha de modificación - análisis temporal no aplicable")
        
        return notes
    
    def _format_time_difference(self, hours: float, days: float) -> str:
        """Formatea la diferencia temporal para display"""
        if hours is None or days is None:
            return "No disponible"
        
        if days >= 1:
            return f"{days:.1f} días ({hours:.1f} horas)"
        else:
            return f"{hours:.1f} horas"
