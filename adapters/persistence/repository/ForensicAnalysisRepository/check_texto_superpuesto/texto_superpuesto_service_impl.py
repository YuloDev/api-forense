"""
Implementación del servicio de detección de texto superpuesto.

Utiliza el helper TextoSuperpuestoAnalyzer para realizar la detección usando la lógica existente.
"""

import time
from typing import Dict, Any, List, Optional
from domain.ports.forensic_analysis.check_texto_superpuesto_service import TextoSuperpuestoServicePort
from domain.entities.forensic_analysis.check_texto_superpuesto_result import TextoSuperpuestoResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_texto_superpuesto.texto_superpuesto_analyzer import TextoSuperpuestoAnalyzer
import config


class TextoSuperpuestoServiceAdapter(TextoSuperpuestoServicePort):
    """Adaptador para el servicio de detección de texto superpuesto"""
    
    def __init__(self):
        self.texto_superpuesto_analyzer = TextoSuperpuestoAnalyzer()
    
    def analyze_image_texto_superpuesto(self, image_bytes: bytes, ocr_tokens: Optional[List[Dict[str, Any]]] = None) -> TextoSuperpuestoResult:
        """
        Analiza texto superpuesto en una imagen usando la lógica existente.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            ocr_tokens: Lista opcional de tokens OCR
            
        Returns:
            TextoSuperpuestoResult: Resultado del análisis de texto superpuesto
        """
        start_time = time.perf_counter()
        
        try:
            # Realizar análisis de texto superpuesto
            analysis_result = self.texto_superpuesto_analyzer.analyze_image_texto_superpuesto(image_bytes, ocr_tokens)
            
            if "error" in analysis_result:
                processing_time = int((time.perf_counter() - start_time) * 1000)
                return TextoSuperpuestoResult.create_error_result(analysis_result["error"])
            
            # Extraer información del análisis
            texto_superpuesto_detectado = analysis_result.get("match", False)
            num_sospechosos = analysis_result.get("num_sospechosos", 0)
            localized = analysis_result.get("localized", False)
            sospechosos = analysis_result.get("sospechosos", [])
            
            # Calcular nivel de riesgo y confianza
            risk_level, confidence = self._calculate_risk_and_confidence(
                texto_superpuesto_detectado, num_sospechosos, localized
            )
            
            # Calcular penalización
            penalty_points = self._calculate_penalty_points(risk_level, analysis_result)
            
            # Generar indicadores sospechosos
            indicadores_sospechosos = self._generate_suspicious_indicators(
                texto_superpuesto_detectado, num_sospechosos, localized, sospechosos
            )
            
            # Generar notas de análisis
            analysis_notes = self._generate_analysis_notes(analysis_result)
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return TextoSuperpuestoResult(
                check_name="Detección de texto superpuesto",
                texto_superpuesto_detectado=texto_superpuesto_detectado,
                num_sospechosos=num_sospechosos,
                localized=localized,
                confidence=confidence,
                risk_level=risk_level,
                penalty_points=penalty_points,
                source_type="image",
                sospechosos=sospechosos,
                indicadores_sospechosos=indicadores_sospechosos,
                analysis_notes=analysis_notes,
                file_size_bytes=len(image_bytes),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return TextoSuperpuestoResult.create_error_result(
                f"Error en detección de texto superpuesto: {str(e)}"
            )
    
    def _calculate_risk_and_confidence(self, texto_superpuesto_detectado: bool, 
                                     num_sospechosos: int, localized: bool) -> tuple:
        """Calcula el nivel de riesgo y confianza del análisis"""
        
        # Si no hay texto superpuesto detectado, riesgo bajo
        if not texto_superpuesto_detectado:
            return "LOW", 0.8
        
        # Determinar nivel de riesgo basado en métricas
        if num_sospechosos > 5 or (num_sospechosos > 2 and localized):
            risk_level = "HIGH"
            confidence = 0.9
        elif num_sospechosos > 2 or localized:
            risk_level = "HIGH"
            confidence = 0.8
        elif num_sospechosos > 0:
            risk_level = "MEDIUM"
            confidence = 0.7
        else:
            risk_level = "LOW"
            confidence = 0.6
        
        return risk_level, confidence
    
    def _calculate_penalty_points(self, risk_level: str, analysis_result: Dict) -> int:
        """Calcula los puntos de penalización basados en el nivel de riesgo"""
        
        # Obtener peso base de configuración
        base_weight = config.RISK_WEIGHTS.get("texto_superpuesto", 25)
        
        if risk_level == "HIGH":
            return base_weight
        elif risk_level == "MEDIUM":
            return base_weight // 2
        else:
            return 0
    
    def _generate_suspicious_indicators(self, texto_superpuesto_detectado: bool, 
                                      num_sospechosos: int, localized: bool, 
                                      sospechosos: List[Dict]) -> List[str]:
        """Genera indicadores sospechosos basados en el análisis"""
        indicators = []
        
        if texto_superpuesto_detectado:
            indicators.append("Texto superpuesto detectado en la imagen")
        
        if num_sospechosos > 0:
            indicators.append(f"{num_sospechosos} elementos sospechosos detectados")
        
        if localized:
            indicators.append("Elementos sospechosos localizados en grupo")
        
        if num_sospechosos > 5:
            indicators.append("Múltiples elementos sospechosos - posible manipulación extensa")
        
        if localized and num_sospechosos > 2:
            indicators.append("Grupo de elementos sospechosos - posible edición localizada")
        
        # Analizar tipos de elementos sospechosos
        tipos_detectados = set()
        for sospechoso in sospechosos:
            tipo = sospechoso.get("tipo", "desconocido")
            tipos_detectados.add(tipo)
        
        if "texto_neutro" in tipos_detectados:
            indicators.append("Texto neutro superpuesto detectado")
        
        if "overlay_color" in tipos_detectados:
            indicators.append("Overlay de color detectado")
        
        if "mixto" in tipos_detectados:
            indicators.append("Elementos mixtos superpuestos detectados")
        
        # Analizar elementos numéricos
        elementos_numericos = sum(1 for s in sospechosos if s.get("metricas", {}).get("is_numeric", False))
        if elementos_numericos > 0:
            indicators.append(f"{elementos_numericos} elementos numéricos sospechosos (posibles montos/fechas)")
        
        return indicators
    
    def _generate_analysis_notes(self, analysis_result: Dict) -> List[str]:
        """Genera notas de análisis basadas en los resultados"""
        notes = []
        
        # Notas sobre detección
        texto_superpuesto_detectado = analysis_result.get("match", False)
        if texto_superpuesto_detectado:
            notes.append("Texto superpuesto detectado en la imagen")
        else:
            notes.append("No se detectó texto superpuesto en la imagen")
        
        # Notas sobre número de sospechosos
        num_sospechosos = analysis_result.get("num_sospechosos", 0)
        if num_sospechosos > 0:
            notes.append(f"Elementos sospechosos detectados: {num_sospechosos}")
        else:
            notes.append("No se detectaron elementos sospechosos")
        
        # Notas sobre localización
        localized = analysis_result.get("localized", False)
        if localized:
            notes.append("Elementos sospechosos localizados en grupo")
        else:
            notes.append("Elementos sospechosos dispersos")
        
        # Notas sobre sospechosos específicos
        sospechosos = analysis_result.get("sospechosos", [])
        if sospechosos:
            notes.append(f"Total de elementos analizados: {len(sospechosos)}")
            
            # Analizar tipos
            tipos = {}
            for sospechoso in sospechosos:
                tipo = sospechoso.get("tipo", "desconocido")
                tipos[tipo] = tipos.get(tipo, 0) + 1
            
            for tipo, count in tipos.items():
                notes.append(f"Elementos de tipo '{tipo}': {count}")
            
            # Analizar scores
            scores = [s.get("score", 0) for s in sospechosos]
            if scores:
                notes.append(f"Score promedio: {sum(scores) / len(scores):.1f}")
                notes.append(f"Score máximo: {max(scores)}")
                notes.append(f"Score mínimo: {min(scores)}")
        else:
            notes.append("No se detectaron elementos para analizar")
        
        # Notas específicas sobre análisis forense
        notes.append("Análisis de texto superpuesto completado")
        notes.append("El texto superpuesto puede indicar que se agregó información sobre el documento original")
        
        return notes
