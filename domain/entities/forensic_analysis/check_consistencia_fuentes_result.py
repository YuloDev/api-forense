"""
Entidad para el resultado del check de consistencia de fuentes.

Analiza la consistencia en el uso de fuentes tipográficas en documentos.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class ConsistenciaFuentesResult:
    """Resultado del análisis de consistencia de fuentes"""
    
    check_name: str
    total_fuentes: int
    fuentes_unicas: int
    indice_diversidad: float
    consistencia_score: float
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "pdf" o "image"
    
    # Detalles específicos del análisis
    fuentes_detectadas: List[Dict[str, Any]]
    fuentes_sospechosas: List[str]
    indicadores_sospechosos: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.fuentes_detectadas is None:
            self.fuentes_detectadas = []
        if self.fuentes_sospechosas is None:
            self.fuentes_sospechosas = []
        if self.indicadores_sospechosos is None:
            self.indicadores_sospechosos = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'ConsistenciaFuentesResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Análisis de consistencia de fuentes",
            total_fuentes=0,
            fuentes_unicas=0,
            indice_diversidad=0.0,
            consistencia_score=0.0,
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type="unknown",
            fuentes_detectadas=[],
            fuentes_sospechosas=[],
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
            "total_fuentes": self.total_fuentes,
            "fuentes_unicas": self.fuentes_unicas,
            "indice_diversidad": self.indice_diversidad,
            "consistencia_score": self.consistencia_score,
            "fuentes_sospechosas": self.fuentes_sospechosas,
            "indicadores_sospechosos": self.indicadores_sospechosos,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_fuentes": {
                "fuentes_detectadas": self.fuentes_detectadas,
                "total_fuentes": self.total_fuentes,
                "fuentes_unicas": self.fuentes_unicas,
                "indice_diversidad": self.indice_diversidad,
                "consistencia_score": self.consistencia_score
            },
            "indicadores_forenses": {
                "exceso_fuentes": self.fuentes_unicas > 5,
                "baja_consistencia": self.consistencia_score < 0.5,
                "alta_diversidad": self.indice_diversidad > 0.7,
                "fuentes_sospechosas": len(self.fuentes_sospechosas) > 0,
                "mezcla_excesiva": self.fuentes_unicas > 3 and self.consistencia_score < 0.6
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
