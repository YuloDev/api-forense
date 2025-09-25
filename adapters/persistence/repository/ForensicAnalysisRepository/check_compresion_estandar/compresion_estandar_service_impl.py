"""
Implementación del servicio de análisis de compresión estándar.

Utiliza el helper CompressionAnalyzer para realizar el análisis de compresión estándar.
"""

import time
from typing import Dict, Any, List
from domain.ports.forensic_analysis.check_compresion_estandar_service import CompresionEstandarServicePort
from domain.entities.forensic_analysis.check_compresion_estandar_result import CompresionEstandarResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_compresion_estandar.compression_analyzer import CompressionAnalyzer
import config


class CompresionEstandarServiceAdapter(CompresionEstandarServicePort):
    """Adaptador para el servicio de análisis de compresión estándar"""
    
    def __init__(self):
        self.compression_analyzer = CompressionAnalyzer()
    
    def analyze_pdf_compression(self, pdf_bytes: bytes) -> CompresionEstandarResult:
        """
        Analiza la compresión estándar de un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            CompresionEstandarResult: Resultado del análisis de compresión estándar
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de compresión
            analysis_result = self.compression_analyzer.analyze_pdf_compression(pdf_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return CompresionEstandarResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            compression_methods = analysis_result.get("compression_methods", [])
            suspicious_methods = analysis_result.get("suspicious_methods", [])
            is_standard = analysis_result.get("is_standard", True)
            is_suspicious = analysis_result.get("is_suspicious", False)
            main_compression = analysis_result.get("main_compression", "None")
            secondary_compression = analysis_result.get("secondary_compression")
            suspicious_indicators = analysis_result.get("suspicious_indicators", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                is_standard, is_suspicious, suspicious_methods, compression_methods
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, "pdf")
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return CompresionEstandarResult(
                check_name="Análisis de compresión estándar",
                metodos_compresion=compression_methods,
                compresion_estandar=is_standard,
                compresion_sospechosa=is_suspicious,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="pdf",
                compresion_principal=main_compression,
                compresion_secundaria=secondary_compression,
                metodos_detectados=compression_methods,
                metodos_sospechosos=suspicious_methods,
                indicadores_sospechosos=suspicious_indicators,
                analysis_notes=analysis_notes,
                file_size_bytes=len(pdf_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return CompresionEstandarResult.create_error_result(
                f"Error en análisis de compresión estándar PDF: {str(e)}"
            )
    
    def analyze_image_compression(self, image_bytes: bytes) -> CompresionEstandarResult:
        """
        Analiza la compresión estándar de una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            CompresionEstandarResult: Resultado del análisis de compresión estándar
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de compresión
            analysis_result = self.compression_analyzer.analyze_image_compression(image_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return CompresionEstandarResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            compression_methods = analysis_result.get("compression_methods", [])
            suspicious_methods = analysis_result.get("suspicious_methods", [])
            is_standard = analysis_result.get("is_standard", True)
            is_suspicious = analysis_result.get("is_suspicious", False)
            main_compression = analysis_result.get("main_compression", "None")
            secondary_compression = analysis_result.get("secondary_compression")
            suspicious_indicators = analysis_result.get("suspicious_indicators", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                is_standard, is_suspicious, suspicious_methods, compression_methods
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, "image")
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return CompresionEstandarResult(
                check_name="Análisis de compresión estándar",
                metodos_compresion=compression_methods,
                compresion_estandar=is_standard,
                compresion_sospechosa=is_suspicious,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="image",
                compresion_principal=main_compression,
                compresion_secundaria=secondary_compression,
                metodos_detectados=compression_methods,
                metodos_sospechosos=suspicious_methods,
                indicadores_sospechosos=suspicious_indicators,
                analysis_notes=analysis_notes,
                file_size_bytes=len(image_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return CompresionEstandarResult.create_error_result(
                f"Error en análisis de compresión estándar de imagen: {str(e)}"
            )
    
    def _calculate_risk_and_confidence(self, is_standard: bool, is_suspicious: bool, 
                                     suspicious_methods: List[str], compression_methods: List[str]) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no hay métodos de compresión, riesgo bajo
        if not compression_methods:
            return "LOW", 0.5
        
        # Determinar nivel de riesgo basado en estándares y sospechas
        if not is_standard or is_suspicious:
            risk_level = "HIGH"
            confidence = 0.9
        elif len(compression_methods) > 2:
            risk_level = "MEDIUM"
            confidence = 0.7
        else:
            risk_level = "LOW"
            confidence = 0.8
        
        # Ajustar según métodos sospechosos específicos
        if suspicious_methods:
            risk_level = "HIGH"
            confidence = 0.9
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, analysis_result: Dict) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("compresion_estandar", 6)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_analysis_notes(self, analysis_result: Dict, source_type: str) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre métodos de compresión
        compression_methods = analysis_result.get("compression_methods", [])
        if compression_methods:
            notes.append(f"Métodos de compresión detectados: {compression_methods}")
        else:
            notes.append("No se detectaron métodos de compresión")
        
        # Notas sobre estándares
        is_standard = analysis_result.get("is_standard", True)
        if is_standard:
            notes.append("Uso de métodos de compresión estándar")
        else:
            notes.append("Uso de métodos de compresión no estándar")
        
        # Notas sobre compresión principal
        main_compression = analysis_result.get("main_compression", "None")
        if main_compression != "None":
            notes.append(f"Compresión principal: {main_compression}")
        
        # Notas sobre compresión secundaria
        secondary_compression = analysis_result.get("secondary_compression")
        if secondary_compression:
            notes.append(f"Compresión secundaria: {secondary_compression}")
        
        # Notas sobre métodos sospechosos
        suspicious_methods = analysis_result.get("suspicious_methods", [])
        if suspicious_methods:
            notes.append(f"Métodos sospechosos detectados: {suspicious_methods}")
        else:
            notes.append("No se detectaron métodos de compresión sospechosos")
        
        # Notas sobre indicadores sospechosos
        suspicious_indicators = analysis_result.get("suspicious_indicators", [])
        if suspicious_indicators:
            notes.append(f"Se detectaron {len(suspicious_indicators)} indicadores sospechosos")
            for indicator in suspicious_indicators[:3]:  # Mostrar solo los primeros 3
                notes.append(f"- {indicator}")
        else:
            notes.append("No se detectaron indicadores sospechosos en la compresión")
        
        # Notas específicas por tipo de archivo
        if source_type == "pdf":
            notes.append("Análisis de compresión PDF completado")
            if "FlateDecode" in compression_methods:
                notes.append("Uso de compresión ZIP/Deflate (estándar)")
            if "DCTDecode" in compression_methods:
                notes.append("Uso de compresión JPEG (estándar)")
        else:
            notes.append("Análisis de compresión de imagen completado")
            if "JPEG" in compression_methods:
                notes.append("Uso de compresión JPEG (estándar)")
            if "PNG" in compression_methods:
                notes.append("Uso de compresión PNG (estándar)")
        
        return notes
