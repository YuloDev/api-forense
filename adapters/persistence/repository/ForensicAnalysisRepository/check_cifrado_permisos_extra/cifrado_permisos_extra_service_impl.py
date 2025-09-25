"""
Implementación del servicio de análisis de cifrado y permisos especiales.

Utiliza el helper CifradoPermisosAnalyzer para realizar el análisis de cifrado y permisos especiales.
"""

import time
from typing import Dict, Any, List
from domain.ports.forensic_analysis.check_cifrado_permisos_extra_service import CifradoPermisosExtraServicePort
from domain.entities.forensic_analysis.check_cifrado_permisos_extra_result import CifradoPermisosExtraResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_cifrado_permisos_extra.cifrado_permisos_analyzer import CifradoPermisosAnalyzer
import config


class CifradoPermisosExtraServiceAdapter(CifradoPermisosExtraServicePort):
    """Adaptador para el servicio de análisis de cifrado y permisos especiales"""
    
    def __init__(self):
        self.cifrado_permisos_analyzer = CifradoPermisosAnalyzer()
    
    def analyze_pdf_cifrado_permisos(self, pdf_bytes: bytes) -> CifradoPermisosExtraResult:
        """
        Analiza cifrado y permisos especiales en un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            CifradoPermisosExtraResult: Resultado del análisis de cifrado y permisos especiales
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de cifrado y permisos
            analysis_result = self.cifrado_permisos_analyzer.analyze_pdf_cifrado_permisos(pdf_bytes)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return CifradoPermisosExtraResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            cifrado_detectado = analysis_result.get("cifrado_detectado", False)
            permisos_especiales = analysis_result.get("permisos_especiales", False)
            nivel_cifrado = analysis_result.get("nivel_cifrado", "none")
            tipos_permisos = analysis_result.get("tipos_permisos", [])
            metodos_cifrado = analysis_result.get("metodos_cifrado", [])
            restricciones_detectadas = analysis_result.get("restricciones_detectadas", [])
            permisos_restrictivos = analysis_result.get("permisos_restrictivos", [])
            indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                cifrado_detectado, permisos_especiales, nivel_cifrado, 
                metodos_cifrado, permisos_restrictivos, restricciones_detectadas
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, "pdf")
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return CifradoPermisosExtraResult(
                check_name="Análisis de cifrado y permisos especiales",
                cifrado_detectado=cifrado_detectado,
                permisos_especiales=permisos_especiales,
                nivel_cifrado=nivel_cifrado,
                tipos_permisos=tipos_permisos,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="pdf",
                metodos_cifrado=metodos_cifrado,
                restricciones_detectadas=restricciones_detectadas,
                permisos_restrictivos=permisos_restrictivos,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(pdf_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return CifradoPermisosExtraResult.create_error_result(
                f"Error en análisis de cifrado y permisos especiales PDF: {str(e)}"
            )
    
    def analyze_image_cifrado_permisos(self, image_bytes: bytes) -> CifradoPermisosExtraResult:
        """
        Analiza cifrado y permisos especiales en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            CifradoPermisosExtraResult: Resultado del análisis de cifrado y permisos especiales
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de cifrado y permisos
            analysis_result = self.cifrado_permisos_analyzer.analyze_image_cifrado_permisos(image_bytes)
            
            # Extraer información del análisis
            cifrado_detectado = analysis_result.get("cifrado_detectado", False)
            permisos_especiales = analysis_result.get("permisos_especiales", False)
            nivel_cifrado = analysis_result.get("nivel_cifrado", "none")
            tipos_permisos = analysis_result.get("tipos_permisos", [])
            metodos_cifrado = analysis_result.get("metodos_cifrado", [])
            restricciones_detectadas = analysis_result.get("restricciones_detectadas", [])
            permisos_restrictivos = analysis_result.get("permisos_restrictivos", [])
            indicadores_sospechosos = analysis_result.get("indicadores_sospechosos", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                cifrado_detectado, permisos_especiales, nivel_cifrado, 
                metodos_cifrado, permisos_restrictivos, restricciones_detectadas
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result, "image")
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return CifradoPermisosExtraResult(
                check_name="Análisis de cifrado y permisos especiales",
                cifrado_detectado=cifrado_detectado,
                permisos_especiales=permisos_especiales,
                nivel_cifrado=nivel_cifrado,
                tipos_permisos=tipos_permisos,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="image",
                metodos_cifrado=metodos_cifrado,
                restricciones_detectadas=restricciones_detectadas,
                permisos_restrictivos=permisos_restrictivos,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(image_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return CifradoPermisosExtraResult.create_error_result(
                f"Error en análisis de cifrado y permisos especiales de imagen: {str(e)}"
            )
    
    def _calculate_risk_and_confidence(self, cifrado_detectado: bool, permisos_especiales: bool, 
                                     nivel_cifrado: str, metodos_cifrado: List[str], 
                                     permisos_restrictivos: List[str], restricciones_detectadas: List[Dict[str, Any]]) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no hay cifrado ni permisos especiales, riesgo bajo
        if not cifrado_detectado and not permisos_especiales:
            return "LOW", 0.8
        
        # Determinar nivel de riesgo basado en cifrado y permisos
        if nivel_cifrado == "high" or len(metodos_cifrado) > 2 or len(permisos_restrictivos) > 3:
            risk_level = "HIGH"
            confidence = 0.9
        elif nivel_cifrado == "medium" or len(metodos_cifrado) > 1 or len(permisos_restrictivos) > 1:
            risk_level = "MEDIUM"
            confidence = 0.7
        else:
            risk_level = "LOW"
            confidence = 0.6
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, analysis_result: Dict) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("cifrado_permisos_extra", 2)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_analysis_notes(self, analysis_result: Dict, source_type: str) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre cifrado detectado
        cifrado_detectado = analysis_result.get("cifrado_detectado", False)
        if cifrado_detectado:
            notes.append("Cifrado detectado en el documento")
        else:
            notes.append("No se detectó cifrado en el documento")
        
        # Notas sobre permisos especiales
        permisos_especiales = analysis_result.get("permisos_especiales", False)
        if permisos_especiales:
            notes.append("Permisos especiales aplicados al documento")
        else:
            notes.append("No se detectaron permisos especiales")
        
        # Notas sobre nivel de cifrado
        nivel_cifrado = analysis_result.get("nivel_cifrado", "none")
        if nivel_cifrado != "none":
            notes.append(f"Nivel de cifrado detectado: {nivel_cifrado}")
        else:
            notes.append("Sin cifrado detectado")
        
        # Notas sobre métodos de cifrado
        metodos_cifrado = analysis_result.get("metodos_cifrado", [])
        if metodos_cifrado:
            notes.append(f"Métodos de cifrado detectados: {len(metodos_cifrado)}")
            for metodo in metodos_cifrado[:3]:  # Mostrar solo los primeros 3
                notes.append(f"- {metodo}")
        else:
            notes.append("No se detectaron métodos de cifrado")
        
        # Notas sobre permisos restrictivos
        permisos_restrictivos = analysis_result.get("permisos_restrictivos", [])
        if permisos_restrictivos:
            notes.append(f"Permisos restrictivos detectados: {len(permisos_restrictivos)}")
            for permiso in permisos_restrictivos[:3]:  # Mostrar solo los primeros 3
                notes.append(f"- {permiso}")
        else:
            notes.append("No se detectaron permisos restrictivos")
        
        # Notas sobre restricciones detectadas
        restricciones_detectadas = analysis_result.get("restricciones_detectadas", [])
        if restricciones_detectadas:
            notes.append(f"Restricciones detectadas: {len(restricciones_detectadas)}")
            for restriccion in restricciones_detectadas[:3]:  # Mostrar solo las primeras 3
                notes.append(f"- {restriccion}")
        else:
            notes.append("No se detectaron restricciones")
        
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
            notes.append("Análisis de cifrado y permisos especiales PDF completado")
        else:
            notes.append("Análisis de cifrado y permisos especiales de imagen completado")
            notes.append("Las imágenes pueden tener restricciones en metadatos EXIF")
        
        return notes
