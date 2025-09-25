"""
Entidad para el resultado del check de inconsistencias en ruido y bordes.

Analiza inconsistencias en patrones de ruido y bordes que pueden indicar edición local.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class InconsistenciasRuidoBordesResult:
    """Resultado del análisis de inconsistencias en ruido y bordes"""
    
    check_name: str
    inconsistencias_detectadas: bool
    nivel_inconsistencia: str  # "bajo", "medio", "alto", "muy_alto"
    areas_sospechosas: int
    patrones_ruido_inconsistentes: int
    bordes_irregulares: int
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "image" (solo para imágenes)
    
    # Detalles específicos del análisis
    areas_detectadas: List[Dict[str, Any]]
    patrones_ruido: List[Dict[str, Any]]
    bordes_analizados: List[Dict[str, Any]]
    indicadores_sospechosos: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.areas_detectadas is None:
            self.areas_detectadas = []
        if self.patrones_ruido is None:
            self.patrones_ruido = []
        if self.bordes_analizados is None:
            self.bordes_analizados = []
        if self.indicadores_sospechosos is None:
            self.indicadores_sospechosos = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'InconsistenciasRuidoBordesResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Análisis de inconsistencias en ruido y bordes",
            inconsistencias_detectadas=False,
            nivel_inconsistencia="bajo",
            areas_sospechosas=0,
            patrones_ruido_inconsistentes=0,
            bordes_irregulares=0,
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type="image",
            areas_detectadas=[],
            patrones_ruido=[],
            bordes_analizados=[],
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
            "inconsistencias_detectadas": self.inconsistencias_detectadas,
            "nivel_inconsistencia": self.nivel_inconsistencia,
            "areas_sospechosas": self.areas_sospechosas,
            "patrones_ruido_inconsistentes": self.patrones_ruido_inconsistentes,
            "bordes_irregulares": self.bordes_irregulares,
            "indicadores_sospechosos": self.indicadores_sospechosos,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_ruido_bordes": {
                "areas_detectadas": self.areas_detectadas,
                "patrones_ruido": self.patrones_ruido,
                "bordes_analizados": self.bordes_analizados,
                "estadisticas": {
                    "total_areas": len(self.areas_detectadas),
                    "areas_sospechosas": self.areas_sospechosas,
                    "patrones_inconsistentes": self.patrones_ruido_inconsistentes,
                    "bordes_irregulares": self.bordes_irregulares
                }
            },
            "indicadores_forenses": {
                "inconsistencias_presentes": self.inconsistencias_detectadas,
                "nivel_alto_inconsistencia": self.nivel_inconsistencia in ["alto", "muy_alto"],
                "areas_sospechosas": self.areas_sospechosas > 0,
                "patrones_ruido_inconsistentes": self.patrones_ruido_inconsistentes > 0,
                "bordes_irregulares": self.bordes_irregulares > 0,
                "posible_edicion_local": self.risk_level == "HIGH"
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
