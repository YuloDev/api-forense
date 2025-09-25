"""
Entidad para el resultado del check de capas ocultas.

Analiza la presencia de capas ocultas en formatos que las soportan.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class CapasOcultasResult:
    """Resultado del análisis de capas ocultas"""
    
    check_name: str
    capas_ocultas_detectadas: bool
    total_capas: int
    capas_ocultas: int
    tipo_archivo: str
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "image" (solo para imágenes)
    
    # Detalles específicos del análisis
    capas: List[Dict[str, Any]]
    modos_mezcla: List[str]
    capas_sospechosas: List[Dict[str, Any]]
    indicadores_sospechosos: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.capas is None:
            self.capas = []
        if self.modos_mezcla is None:
            self.modos_mezcla = []
        if self.capas_sospechosas is None:
            self.capas_sospechosas = []
        if self.indicadores_sospechosos is None:
            self.indicadores_sospechosos = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'CapasOcultasResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Detección de capas ocultas",
            capas_ocultas_detectadas=False,
            total_capas=0,
            capas_ocultas=0,
            tipo_archivo="unknown",
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type="image",
            capas=[],
            modos_mezcla=[],
            capas_sospechosas=[],
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
            "capas_ocultas_detectadas": self.capas_ocultas_detectadas,
            "total_capas": self.total_capas,
            "capas_ocultas": self.capas_ocultas,
            "tipo_archivo": self.tipo_archivo,
            "indicadores_sospechosos": self.indicadores_sospechosos,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_capas_ocultas": {
                "capas": self.capas,
                "modos_mezcla": self.modos_mezcla,
                "capas_sospechosas": self.capas_sospechosas,
                "estadisticas": {
                    "total_capas": self.total_capas,
                    "capas_ocultas": self.capas_ocultas,
                    "capas_visibles": self.total_capas - self.capas_ocultas,
                    "porcentaje_ocultas": (self.capas_ocultas / max(1, self.total_capas)) * 100
                }
            },
            "indicadores_forenses": {
                "capas_ocultas_presentes": self.capas_ocultas_detectadas,
                "múltiples_capas": self.total_capas > 1,
                "capas_ocultas": self.capas_ocultas > 0,
                "modos_mezcla_sospechosos": len(self.modos_mezcla) > 0,
                "posible_manipulacion": self.risk_level == "HIGH"
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
