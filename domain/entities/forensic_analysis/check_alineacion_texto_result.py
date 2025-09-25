"""
Entidad para el resultado del check de alineación de texto.

Analiza la alineación correcta de elementos de texto en documentos.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class AlineacionTextoResult:
    """Resultado del análisis de alineación de texto"""
    
    check_name: str
    elementos_analizados: int
    alineacion_correcta: bool
    desviacion_promedio: float
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "pdf" o "image"
    
    # Detalles específicos del análisis
    alineaciones_detectadas: List[str]
    desviaciones_por_elemento: List[float]
    elementos_mal_alineados: List[Dict[str, Any]]
    indicadores_sospechosos: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.alineaciones_detectadas is None:
            self.alineaciones_detectadas = []
        if self.desviaciones_por_elemento is None:
            self.desviaciones_por_elemento = []
        if self.elementos_mal_alineados is None:
            self.elementos_mal_alineados = []
        if self.indicadores_sospechosos is None:
            self.indicadores_sospechosos = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'AlineacionTextoResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Análisis de alineación de texto",
            elementos_analizados=0,
            alineacion_correcta=False,
            desviacion_promedio=0.0,
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type="unknown",
            alineaciones_detectadas=[],
            desviaciones_por_elemento=[],
            elementos_mal_alineados=[],
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
            "alineacion_correcta": self.alineacion_correcta,
            "elementos_analizados": self.elementos_analizados,
            "desviacion_promedio": self.desviacion_promedio,
            "alineaciones_detectadas": self.alineaciones_detectadas,
            "elementos_mal_alineados": len(self.elementos_mal_alineados),
            "indicadores_sospechosos": self.indicadores_sospechosos,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_alineacion": {
                "alineaciones_detectadas": self.alineaciones_detectadas,
                "desviaciones_por_elemento": self.desviaciones_por_elemento,
                "elementos_mal_alineados": self.elementos_mal_alineados,
                "desviacion_promedio": self.desviacion_promedio
            },
            "indicadores_forenses": {
                "alineacion_incorrecta": not self.alineacion_correcta,
                "desviacion_alta": self.desviacion_promedio > 5.0,
                "elementos_rotados": len([e for e in self.elementos_mal_alineados if e.get("rotacion", 0) != 0]) > 0,
                "alineacion_inconsistente": len(set(self.alineaciones_detectadas)) > 3,
                "posible_manipulacion": self.risk_level == "HIGH"
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
