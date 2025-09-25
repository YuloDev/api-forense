"""
Entidad para el resultado del check de texto superpuesto.

Analiza detección de texto superpuesto en imágenes usando la lógica existente del proyecto.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class TextoSuperpuestoResult:
    """Resultado del análisis de texto superpuesto"""
    
    check_name: str
    texto_superpuesto_detectado: bool
    num_sospechosos: int
    localized: bool
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "image" (solo para imágenes)
    
    # Detalles específicos del análisis
    sospechosos: List[Dict[str, Any]]
    indicadores_sospechosos: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.sospechosos is None:
            self.sospechosos = []
        if self.indicadores_sospechosos is None:
            self.indicadores_sospechosos = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'TextoSuperpuestoResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Detección de texto superpuesto",
            texto_superpuesto_detectado=False,
            num_sospechosos=0,
            localized=False,
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type="image",
            sospechosos=[],
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
            "texto_superpuesto_detectado": self.texto_superpuesto_detectado,
            "num_sospechosos": self.num_sospechosos,
            "localized": self.localized,
            "indicadores_sospechosos": self.indicadores_sospechosos,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_texto_superpuesto": {
                "sospechosos": self.sospechosos,
                "estadisticas": {
                    "total_sospechosos": len(self.sospechosos),
                    "texto_superpuesto_detectado": self.texto_superpuesto_detectado,
                    "localized": self.localized,
                    "num_sospechosos": self.num_sospechosos
                }
            },
            "indicadores_forenses": {
                "texto_superpuesto_presente": self.texto_superpuesto_detectado,
                "múltiples_sospechosos": self.num_sospechosos > 1,
                "localized": self.localized,
                "posible_manipulacion": self.risk_level == "HIGH"
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
