"""
Entidad para el resultado del check de fecha de modificación vs creación.

Analiza la diferencia entre la fecha de modificación y creación de un documento
para detectar posibles manipulaciones temporales.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class FechaModVsCreacionResult:
    """Resultado del análisis de fecha de modificación vs creación"""
    
    check_name: str
    has_creation_date: bool
    has_modification_date: bool
    creation_date: Optional[datetime]
    modification_date: Optional[datetime]
    time_difference_hours: Optional[float]
    time_difference_days: Optional[float]
    is_suspicious: bool
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "pdf" o "image"
    
    # Detalles específicos del análisis
    creation_date_str: Optional[str]
    modification_date_str: Optional[str]
    time_difference_formatted: Optional[str]
    suspicious_indicators: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.suspicious_indicators is None:
            self.suspicious_indicators = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str, source_type: str = "unknown") -> 'FechaModVsCreacionResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Análisis de fecha modificación vs creación",
            has_creation_date=False,
            has_modification_date=False,
            creation_date=None,
            modification_date=None,
            time_difference_hours=None,
            time_difference_days=None,
            is_suspicious=False,
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type=source_type,
            creation_date_str=None,
            modification_date_str=None,
            time_difference_formatted=None,
            suspicious_indicators=[],
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
            "tiene_fecha_creacion": self.has_creation_date,
            "tiene_fecha_modificacion": self.has_modification_date,
            "diferencia_tiempo_horas": self.time_difference_hours,
            "diferencia_tiempo_dias": self.time_difference_days,
            "es_sospechoso": self.is_suspicious,
            "indicadores_sospechosos": self.suspicious_indicators,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "fecha_creacion": self.creation_date_str,
            "fecha_modificacion": self.modification_date_str,
            "diferencia_formateada": self.time_difference_formatted,
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_temporal": {
                "fecha_creacion_original": self.creation_date.isoformat() if self.creation_date else None,
                "fecha_modificacion_original": self.modification_date.isoformat() if self.modification_date else None,
                "diferencia_segundos": (self.modification_date - self.creation_date).total_seconds() if self.creation_date and self.modification_date else None,
                "diferencia_horas": self.time_difference_hours,
                "diferencia_dias": self.time_difference_days
            },
            "indicadores_forenses": {
                "fechas_iguales": self.creation_date == self.modification_date if self.creation_date and self.modification_date else False,
                "modificacion_anterior_creacion": self.modification_date < self.creation_date if self.creation_date and self.modification_date else False,
                "diferencia_muy_grande": self.time_difference_days > 365 if self.time_difference_days else False,
                "diferencia_muy_pequena": self.time_difference_hours < 1 if self.time_difference_hours else False,
                "fecha_creacion_futura": self.creation_date > datetime.now() if self.creation_date else False,
                "fecha_modificacion_futura": self.modification_date > datetime.now() if self.modification_date else False
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
