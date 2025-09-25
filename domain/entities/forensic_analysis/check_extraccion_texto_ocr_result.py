"""
Entidad para el resultado del check de extracción de texto OCR.

Analiza la incapacidad de extraer texto legible mediante OCR que puede indicar manipulación.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class ExtraccionTextoOcrResult:
    """Resultado del análisis de extracción de texto OCR"""
    
    check_name: str
    texto_extraido: bool
    calidad_extraccion: str  # "excelente", "buena", "regular", "mala", "muy_mala"
    confianza_promedio: float
    cantidad_palabras: int
    cantidad_caracteres: int
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "image" (solo para imágenes)
    
    # Detalles específicos del análisis
    palabras_detectadas: List[Dict[str, Any]]
    caracteres_legibles: int
    caracteres_no_legibles: int
    indicadores_sospechosos: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.palabras_detectadas is None:
            self.palabras_detectadas = []
        if self.indicadores_sospechosos is None:
            self.indicadores_sospechosos = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'ExtraccionTextoOcrResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Análisis de extracción de texto OCR",
            texto_extraido=False,
            calidad_extraccion="muy_mala",
            confianza_promedio=0.0,
            cantidad_palabras=0,
            cantidad_caracteres=0,
            confidence=0.0,
            risk_level="HIGH",
            penalty_points=30,
            source_type="image",
            palabras_detectadas=[],
            caracteres_legibles=0,
            caracteres_no_legibles=0,
            indicadores_sospechosos=[],
            analysis_notes=[f"Error: {error_message}"],
            file_size_bytes=None,
            processing_time_ms=0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entidad a diccionario para serialización JSON"""
        
        # Generar resumen del análisis
        resumen = {
            "probabilidad_manipulacion": self.confidence,
            "nivel_riesgo": self.risk_level,
            "texto_extraido": self.texto_extraido,
            "calidad_extraccion": self.calidad_extraccion,
            "confianza_promedio": self.confianza_promedio,
            "cantidad_palabras": self.cantidad_palabras,
            "cantidad_caracteres": self.cantidad_caracteres,
            "caracteres_legibles": self.caracteres_legibles,
            "caracteres_no_legibles": self.caracteres_no_legibles,
            "indicadores_sospechosos": self.indicadores_sospechosos,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_ocr": {
                "palabras_detectadas": self.palabras_detectadas,
                "confianza_promedio": self.confianza_promedio,
                "calidad_extraccion": self.calidad_extraccion,
                "estadisticas_texto": {
                    "total_palabras": self.cantidad_palabras,
                    "total_caracteres": self.cantidad_caracteres,
                    "caracteres_legibles": self.caracteres_legibles,
                    "caracteres_no_legibles": self.caracteres_no_legibles
                }
            },
            "indicadores_forenses": {
                "texto_extraible": self.texto_extraido,
                "calidad_ocr_baja": self.calidad_extraccion in ["mala", "muy_mala"],
                "confianza_baja": self.confianza_promedio < 0.5,
                "pocas_palabras": self.cantidad_palabras < 5,
                "caracteres_ilegibles": self.caracteres_no_legibles > self.caracteres_legibles,
                "posible_manipulacion": self.risk_level == "HIGH"
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
