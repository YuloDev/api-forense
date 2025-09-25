"""
Entidad para el resultado del check de software conocido.

Analiza el software usado para crear el PDF y determina si es confiable o sospechoso.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class SoftwareConocidoResult:
    """Resultado del análisis de software conocido"""
    
    check_name: str
    has_creator: bool
    has_producer: bool
    creator: Optional[str]
    producer: Optional[str]
    is_known_software: bool
    is_trusted_software: bool
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "pdf"
    
    # Detalles específicos del análisis
    software_category: str  # "known_trusted", "known_suspicious", "unknown", "missing"
    software_confidence: float
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
    def create_error_result(cls, error_message: str) -> 'SoftwareConocidoResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Análisis de software conocido",
            has_creator=False,
            has_producer=False,
            creator=None,
            producer=None,
            is_known_software=False,
            is_trusted_software=False,
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type="pdf",
            software_category="error",
            software_confidence=0.0,
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
            "tiene_creator": self.has_creator,
            "tiene_producer": self.has_producer,
            "es_software_conocido": self.is_known_software,
            "es_software_confiable": self.is_trusted_software,
            "categoria_software": self.software_category,
            "confianza_software": self.software_confidence,
            "indicadores_sospechosos": self.suspicious_indicators,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "creator": self.creator,
            "producer": self.producer,
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_software": {
                "creator_original": self.creator,
                "producer_original": self.producer,
                "categoria_detectada": self.software_category,
                "confianza_deteccion": self.software_confidence,
                "es_conocido": self.is_known_software,
                "es_confiable": self.is_trusted_software
            },
            "indicadores_forenses": {
                "software_faltante": not self.has_creator and not self.has_producer,
                "software_desconocido": not self.is_known_software,
                "software_no_confiable": not self.is_trusted_software,
                "metadatos_inconsistentes": self.has_creator != self.has_producer,
                "software_sospechoso": len(self.suspicious_indicators) > 0
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
