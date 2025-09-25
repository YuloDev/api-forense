"""
Entidad para el resultado del check de uniformidad DPI.

Analiza la uniformidad en la resolución (DPI) de las imágenes en documentos.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class DpiUniformeResult:
    """Resultado del análisis de uniformidad DPI"""
    
    check_name: str
    imagenes_analizadas: int
    dpi_promedio: float
    dpi_estandar: int
    variacion_dpi: float
    uniformidad_score: float
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "pdf" o "image"
    
    # Detalles específicos del análisis
    dpi_detectados: List[float]
    dpi_mas_comun: float
    desviacion_estandar: float
    rango_dpi: List[float]
    dpi_sospechosos: List[float]
    indicadores_sospechosos: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.dpi_detectados is None:
            self.dpi_detectados = []
        if self.dpi_sospechosos is None:
            self.dpi_sospechosos = []
        if self.indicadores_sospechosos is None:
            self.indicadores_sospechosos = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'DpiUniformeResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Análisis de uniformidad DPI",
            imagenes_analizadas=0,
            dpi_promedio=0.0,
            dpi_estandar=0,
            variacion_dpi=0.0,
            uniformidad_score=0.0,
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type="unknown",
            dpi_detectados=[],
            dpi_mas_comun=0.0,
            desviacion_estandar=0.0,
            rango_dpi=[],
            dpi_sospechosos=[],
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
            "dpi_promedio": self.dpi_promedio,
            "dpi_estandar": self.dpi_estandar,
            "variacion_dpi": self.variacion_dpi,
            "imagenes_analizadas": self.imagenes_analizadas,
            "dpi_sospechosos": self.dpi_sospechosos,
            "indicadores_sospechosos": self.indicadores_sospechosos,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_dpi": {
                "dpi_detectados": self.dpi_detectados,
                "dpi_mas_comun": self.dpi_mas_comun,
                "desviacion_estandar": self.desviacion_estandar,
                "rango_dpi": self.rango_dpi,
                "uniformidad_score": self.uniformidad_score
            },
            "indicadores_forenses": {
                "dpi_muy_diferentes": self.variacion_dpi > 0.3,
                "dpi_no_estandar": len(self.dpi_sospechosos) > 0,
                "insercion_imagenes": self.variacion_dpi > 0.2,
                "uniformidad_baja": self.uniformidad_score < 0.6,
                "resolucion_inconsistente": self.desviacion_estandar > 50.0
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
