"""
Entidad para el resultado del check de análisis ELA sospechoso.

Analiza áreas de la imagen que han sido editadas o re-comprimidas mediante Error Level Analysis.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class AnalisisElaSospechosoResult:
    """Resultado del análisis ELA sospechoso"""
    
    check_name: str
    areas_ela_detectadas: bool
    nivel_sospecha: str  # "bajo", "medio", "alto", "muy_alto"
    areas_sospechosas: int
    nivel_compresion_inconsistente: int
    areas_recomprimidas: int
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "image" (solo para imágenes)
    
    # Detalles específicos del análisis
    areas_detectadas: List[Dict[str, Any]]
    niveles_ela: List[Dict[str, Any]]
    patrones_compresion: List[Dict[str, Any]]
    indicadores_sospechosos: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.areas_detectadas is None:
            self.areas_detectadas = []
        if self.niveles_ela is None:
            self.niveles_ela = []
        if self.patrones_compresion is None:
            self.patrones_compresion = []
        if self.indicadores_sospechosos is None:
            self.indicadores_sospechosos = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'AnalisisElaSospechosoResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Análisis ELA sospechoso",
            areas_ela_detectadas=False,
            nivel_sospecha="bajo",
            areas_sospechosas=0,
            nivel_compresion_inconsistente=0,
            areas_recomprimidas=0,
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type="image",
            areas_detectadas=[],
            niveles_ela=[],
            patrones_compresion=[],
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
            "areas_ela_detectadas": self.areas_ela_detectadas,
            "nivel_sospecha": self.nivel_sospecha,
            "areas_sospechosas": self.areas_sospechosas,
            "nivel_compresion_inconsistente": self.nivel_compresion_inconsistente,
            "areas_recomprimidas": self.areas_recomprimidas,
            "indicadores_sospechosos": self.indicadores_sospechosos,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_ela": {
                "areas_detectadas": self.areas_detectadas,
                "niveles_ela": self.niveles_ela,
                "patrones_compresion": self.patrones_compresion,
                "estadisticas": {
                    "total_areas": len(self.areas_detectadas),
                    "areas_sospechosas": self.areas_sospechosas,
                    "niveles_inconsistentes": self.nivel_compresion_inconsistente,
                    "areas_recomprimidas": self.areas_recomprimidas
                }
            },
            "indicadores_forenses": {
                "areas_ela_presentes": self.areas_ela_detectadas,
                "nivel_alto_sospecha": self.nivel_sospecha in ["alto", "muy_alto"],
                "areas_sospechosas": self.areas_sospechosas > 0,
                "compresion_inconsistente": self.nivel_compresion_inconsistente > 0,
                "areas_recomprimidas": self.areas_recomprimidas > 0,
                "posible_manipulacion": self.risk_level == "HIGH"
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
