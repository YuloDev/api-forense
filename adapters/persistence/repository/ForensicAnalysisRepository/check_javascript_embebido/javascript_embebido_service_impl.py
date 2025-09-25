"""
Implementación del servicio de análisis de JavaScript embebido.

Utiliza el helper JavascriptAnalyzer para realizar el análisis de JavaScript embebido.
"""

import time
from typing import Dict, Any, List
from domain.ports.forensic_analysis.check_javascript_embebido_service import JavascriptEmbebidoServicePort
from domain.entities.forensic_analysis.check_javascript_embebido_result import JavascriptEmbebidoResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_javascript_embebido.javascript_analyzer import JavascriptAnalyzer
import config


class JavascriptEmbebidoServiceAdapter(JavascriptEmbebidoServicePort):
    """Adaptador para el servicio de análisis de JavaScript embebido"""
    
    def __init__(self):
        self.javascript_analyzer = JavascriptAnalyzer()
    
    def analyze_pdf_javascript(self, pdf_bytes: bytes) -> JavascriptEmbebidoResult:
        """
        Analiza JavaScript embebido en un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            JavascriptEmbebidoResult: Resultado del análisis de JavaScript embebido
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de JavaScript
            analysis_result = self.javascript_analyzer.analyze_pdf_javascript(pdf_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return JavascriptEmbebidoResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            javascript_detectado = analysis_result.get("javascript_detectado", False)
            cantidad_scripts = analysis_result.get("cantidad_scripts", 0)
            scripts_sospechosos = analysis_result.get("scripts_sospechosos", 0)
            scripts_encontrados = analysis_result.get("scripts_encontrados", [])
            funciones_detectadas = analysis_result.get("funciones_detectadas", [])
            eventos_detectados = analysis_result.get("eventos_detectados", [])
            indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                javascript_detectado, cantidad_scripts, scripts_sospechosos, 
                funciones_detectadas, eventos_detectados
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, "pdf")
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return JavascriptEmbebidoResult(
                check_name="Análisis de JavaScript embebido",
                javascript_detectado=javascript_detectado,
                cantidad_scripts=cantidad_scripts,
                scripts_sospechosos=scripts_sospechosos,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="pdf",
                scripts_encontrados=scripts_encontrados,
                funciones_detectadas=funciones_detectadas,
                eventos_detectados=eventos_detectados,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(pdf_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return JavascriptEmbebidoResult.create_error_result(
                f"Error en análisis de JavaScript embebido PDF: {str(e)}"
            )
    
    def analyze_image_javascript(self, image_bytes: bytes) -> JavascriptEmbebidoResult:
        """
        Analiza JavaScript embebido en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            JavascriptEmbebidoResult: Resultado del análisis de JavaScript embebido
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de JavaScript
            analysis_result = self.javascript_analyzer.analyze_image_javascript(image_bytes)
            
            # Extraer información del análisis
            javascript_detectado = analysis_result.get("javascript_detectado", False)
            cantidad_scripts = analysis_result.get("cantidad_scripts", 0)
            scripts_sospechosos = analysis_result.get("scripts_sospechosos", 0)
            scripts_encontrados = analysis_result.get("scripts_encontrados", [])
            funciones_detectadas = analysis_result.get("funciones_detectadas", [])
            eventos_detectados = analysis_result.get("eventos_detectados", [])
            indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                javascript_detectado, cantidad_scripts, scripts_sospechosos, 
                funciones_detectadas, eventos_detectados
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, "image")
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return JavascriptEmbebidoResult(
                check_name="Análisis de JavaScript embebido",
                javascript_detectado=javascript_detectado,
                cantidad_scripts=cantidad_scripts,
                scripts_sospechosos=scripts_sospechosos,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="image",
                scripts_encontrados=scripts_encontrados,
                funciones_detectadas=funciones_detectadas,
                eventos_detectados=eventos_detectados,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(image_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return JavascriptEmbebidoResult.create_error_result(
                f"Error en análisis de JavaScript embebido de imagen: {str(e)}"
            )
    
    def _calculate_risk_and_confidence(self, javascript_detectado: bool, cantidad_scripts: int, 
                                     scripts_sospechosos: int, funciones_detectadas: List[str], 
                                     eventos_detectados: List[str]) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no hay JavaScript, riesgo bajo
        if not javascript_detectado:
            return "LOW", 0.8
        
        # Determinar nivel de riesgo basado en JavaScript detectado
        if scripts_sospechosos > 0 or cantidad_scripts > 3:
            risk_level = "HIGH"
            confidence = 0.9
        elif cantidad_scripts > 1 or len(funciones_detectadas) > 0 or len(eventos_detectados) > 0:
            risk_level = "MEDIUM"
            confidence = 0.7
        else:
            risk_level = "LOW"
            confidence = 0.6
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, analysis_result: Dict) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("javascript_embebido", 2)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_analysis_notes(self, analysis_result: Dict, source_type: str) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre JavaScript detectado
        javascript_detectado = analysis_result.get("javascript_detectado", False)
        if javascript_detectado:
            notes.append("JavaScript embebido detectado en el documento")
        else:
            notes.append("No se detectó JavaScript embebido en el documento")
        
        # Notas sobre cantidad de scripts
        cantidad_scripts = analysis_result.get("cantidad_scripts", 0)
        if cantidad_scripts > 0:
            notes.append(f"Total de scripts JavaScript encontrados: {cantidad_scripts}")
        else:
            notes.append("No se encontraron scripts JavaScript")
        
        # Notas sobre scripts sospechosos
        scripts_sospechosos = analysis_result.get("scripts_sospechosos", 0)
        if scripts_sospechosos > 0:
            notes.append(f"Scripts con patrones sospechosos: {scripts_sospechosos}")
        else:
            notes.append("No se detectaron scripts sospechosos")
        
        # Notas sobre funciones detectadas
        funciones_detectadas = analysis_result.get("funciones_detectadas", [])
        if funciones_detectadas:
            notes.append(f"Funciones JavaScript detectadas: {len(funciones_detectadas)}")
            for func in funciones_detectadas[:3]:  # Mostrar solo las primeras 3
                notes.append(f"- {func}")
        else:
            notes.append("No se detectaron funciones JavaScript")
        
        # Notas sobre eventos detectados
        eventos_detectados = analysis_result.get("eventos_detectados", [])
        if eventos_detectados:
            notes.append(f"Eventos JavaScript detectados: {len(eventos_detectados)}")
            for event in eventos_detectados[:3]:  # Mostrar solo los primeros 3
                notes.append(f"- {event}")
        else:
            notes.append("No se detectaron eventos JavaScript")
        
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
            notes.append("Análisis de JavaScript embebido PDF completado")
        else:
            notes.append("Análisis de JavaScript embebido de imagen completado")
            notes.append("Las imágenes no pueden contener JavaScript embebido")
        
        return notes
