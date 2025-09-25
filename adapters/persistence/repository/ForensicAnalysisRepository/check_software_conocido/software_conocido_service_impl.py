"""
Implementación del servicio de análisis de software conocido.

Utiliza el helper SoftwareAnalyzer para realizar el análisis de software.
"""

import time
from typing import Dict, Any, List
from domain.ports.forensic_analysis.check_software_conocido_service import SoftwareConocidoServicePort
from domain.entities.forensic_analysis.check_software_conocido_result import SoftwareConocidoResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_software_conocido.software_analyzer import SoftwareAnalyzer
import config


class SoftwareConocidoServiceAdapter(SoftwareConocidoServicePort):
    """Adaptador para el servicio de análisis de software conocido"""
    
    def __init__(self):
        self.software_analyzer = SoftwareAnalyzer()
    
    def analyze_pdf_software(self, pdf_bytes: bytes) -> SoftwareConocidoResult:
        """
        Analiza el software usado para crear un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            SoftwareConocidoResult: Resultado del análisis de software
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de software
            analysis_result = self.software_analyzer.analyze_pdf_software(pdf_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return SoftwareConocidoResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            creator = analysis_result.get("creator")
            producer = analysis_result.get("producer")
            has_creator = analysis_result.get("has_creator", False)
            has_producer = analysis_result.get("has_producer", False)
            
            # Analizar combinación de software
            software_analysis = self.software_analyzer.analyze_software_combination(creator, producer)
            
            # Determinar si es software conocido y confiable
            is_known_software = software_analysis["general_category"] != "missing"
            is_trusted_software = software_analysis["general_category"] == "known_trusted"
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                software_analysis, has_creator, has_producer
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, software_analysis)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, software_analysis)
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return SoftwareConocidoResult(
                check_name="Análisis de software conocido",
                has_creator=has_creator,
                has_producer=has_producer,
                creator=creator,
                producer=producer,
                is_known_software=is_known_software,
                is_trusted_software=is_trusted_software,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="pdf",
                software_category=software_analysis["general_category"],
                software_confidence=software_analysis["general_confidence"],
                suspicious_indicators=software_analysis["all_suspicious_indicators"],
                analysis_notes=analysis_notes,
                file_size_bytes=len(pdf_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return SoftwareConocidoResult.create_error_result(
                f"Error en análisis de software PDF: {str(e)}"
            )
    
    def analyze_image_software(self, image_bytes: bytes) -> SoftwareConocidoResult:
        """
        Analiza el software usado para crear una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            SoftwareConocidoResult: Resultado del análisis de software
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de software de imagen
            analysis_result = self.software_analyzer.analyze_image_software(image_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return SoftwareConocidoResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            creator = analysis_result.get("creator")
            producer = analysis_result.get("producer")
            has_creator = analysis_result.get("has_creator", False)
            has_producer = analysis_result.get("has_producer", False)
            
            # Analizar combinación de software
            software_analysis = self.software_analyzer.analyze_software_combination(creator, producer)
            
            # Determinar si es software conocido y confiable
            is_known_software = software_analysis["general_category"] != "missing"
            is_trusted_software = software_analysis["general_category"] == "known_trusted"
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                software_analysis, has_creator, has_producer
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, software_analysis)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, software_analysis)
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return SoftwareConocidoResult(
                check_name="Análisis de software conocido",
                has_creator=has_creator,
                has_producer=has_producer,
                creator=creator,
                producer=producer,
                is_known_software=is_known_software,
                is_trusted_software=is_trusted_software,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="image",
                software_category=software_analysis["general_category"],
                software_confidence=software_analysis["general_confidence"],
                suspicious_indicators=software_analysis["all_suspicious_indicators"],
                analysis_notes=analysis_notes,
                file_size_bytes=len(image_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return SoftwareConocidoResult.create_error_result(
                f"Error en análisis de software de imagen: {str(e)}"
            )
    
    def _calculate_risk_and_confidence(self, software_analysis: Dict, has_creator: bool, has_producer: bool) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no hay metadatos de software, riesgo bajo
        if not has_creator and not has_producer:
            return "LOW", 0.0
        
        # Obtener categoría y confianza del análisis
        category = software_analysis["general_category"]
        confidence = software_analysis["general_confidence"]
        
        # Determinar nivel de riesgo basado en la categoría
        if category == "known_trusted":
            risk_level = "LOW"
        elif category == "known_suspicious":
            risk_level = "HIGH"
        elif category == "unknown":
            risk_level = "MEDIUM"
        else:  # missing
            risk_level = "LOW"
        
        # Ajustar confianza según indicadores sospechosos
        suspicious_indicators = software_analysis["all_suspicious_indicators"]
        if suspicious_indicators:
            # Reducir confianza si hay indicadores sospechosos
            confidence = min(confidence, 0.6)
            if len(suspicious_indicators) > 2:
                risk_level = "HIGH"
                confidence = 0.4
        
        # Ajustar según inconsistencias
        if software_analysis["inconsistencies"]:
            confidence = min(confidence, 0.5)
            if risk_level == "LOW":
                risk_level = "MEDIUM"
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, software_analysis: Dict) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("software_conocido", 12)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_analysis_notes(self, analysis_result: Dict, software_analysis: Dict) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre disponibilidad de metadatos
        if analysis_result.get("has_creator"):
            notes.append("Creator disponible en metadatos")
        else:
            notes.append("Creator no encontrado en metadatos")
        
        if analysis_result.get("has_producer"):
            notes.append("Producer disponible en metadatos")
        else:
            notes.append("Producer no encontrado en metadatos")
        
        # Notas sobre clasificación del software
        category = software_analysis["general_category"]
        if category == "known_trusted":
            notes.append("Software identificado como conocido y confiable")
        elif category == "known_suspicious":
            notes.append("Software identificado como conocido pero sospechoso")
        elif category == "unknown":
            notes.append("Software no identificado en base de datos de confianza")
        else:
            notes.append("Metadatos de software no disponibles")
        
        # Notas sobre inconsistencias (si las hay)
        if "inconsistencies" in analysis_result:
            for inconsistency in analysis_result["inconsistencies"]:
                notes.append(f"Inconsistencia detectada: {inconsistency}")
        
        # Notas sobre indicadores sospechosos
        suspicious_indicators = software_analysis["all_suspicious_indicators"]
        if suspicious_indicators:
            notes.append(f"Se detectaron {len(suspicious_indicators)} indicadores sospechosos")
        else:
            notes.append("No se detectaron indicadores sospechosos en el software")
        
        return notes
