"""
Entidad para el resultado del check de actualizaciones incrementales.

Analiza múltiples actualizaciones incrementales del PDF que pueden indicar alteraciones sucesivas.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class ActualizacionesIncrementalesResult:
    """Resultado del análisis de actualizaciones incrementales"""
    
    check_name: str
    actualizaciones_detectadas: bool
    cantidad_actualizaciones: int
    actualizaciones_sospechosas: int
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "pdf" o "image"
    
    # Detalles específicos del análisis
    actualizaciones_encontradas: List[Dict[str, Any]]
    fechas_actualizacion: List[str]
    tipos_actualizacion: List[str]
    indicadores_sospechosos: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.actualizaciones_encontradas is None:
            self.actualizaciones_encontradas = []
        if self.fechas_actualizacion is None:
            self.fechas_actualizacion = []
        if self.tipos_actualizacion is None:
            self.tipos_actualizacion = []
        if self.indicadores_sospechosos is None:
            self.indicadores_sospechosos = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'ActualizacionesIncrementalesResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Análisis de actualizaciones incrementales",
            actualizaciones_detectadas=False,
            cantidad_actualizaciones=0,
            actualizaciones_sospechosas=0,
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type="unknown",
            actualizaciones_encontradas=[],
            fechas_actualizacion=[],
            tipos_actualizacion=[],
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
            "actualizaciones_detectadas": self.actualizaciones_detectadas,
            "cantidad_actualizaciones": self.cantidad_actualizaciones,
            "actualizaciones_sospechosas": self.actualizaciones_sospechosas,
            "fechas_actualizacion": self.fechas_actualizacion,
            "tipos_actualizacion": self.tipos_actualizacion,
            "indicadores_sospechosos": self.indicadores_sospechosos,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_actualizaciones": {
                "actualizaciones_encontradas": self.actualizaciones_encontradas,
                "fechas_actualizacion": self.fechas_actualizacion,
                "tipos_actualizacion": self.tipos_actualizacion,
                "actualizaciones_sospechosas": self.actualizaciones_sospechosas
            },
            "indicadores_forenses": {
                "actualizaciones_presentes": self.actualizaciones_detectadas,
                "actualizaciones_multiples": self.cantidad_actualizaciones > 1,
                "actualizaciones_sospechosas": self.actualizaciones_sospechosas > 0,
                "fechas_diferentes": len(set(self.fechas_actualizacion)) > 1,
                "tipos_variados": len(set(self.tipos_actualizacion)) > 1,
                "posible_manipulacion": self.risk_level == "HIGH"
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
