"""
Entidad para el resultado del check de compresión estándar.

Analiza los métodos de compresión utilizados en documentos PDF e imágenes.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class CompresionEstandarResult:
    """Resultado del análisis de compresión estándar"""
    
    check_name: str
    metodos_compresion: List[str]
    compresion_estandar: bool
    compresion_sospechosa: bool
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "pdf" o "image"
    
    # Detalles específicos del análisis
    compresion_principal: str
    compresion_secundaria: Optional[str]
    metodos_detectados: List[str]
    metodos_sospechosos: List[str]
    indicadores_sospechosos: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.metodos_compresion is None:
            self.metodos_compresion = []
        if self.metodos_detectados is None:
            self.metodos_detectados = []
        if self.metodos_sospechosos is None:
            self.metodos_sospechosos = []
        if self.indicadores_sospechosos is None:
            self.indicadores_sospechosos = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'CompresionEstandarResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Análisis de compresión estándar",
            metodos_compresion=[],
            compresion_estandar=False,
            compresion_sospechosa=False,
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type="unknown",
            compresion_principal="",
            compresion_secundaria=None,
            metodos_detectados=[],
            metodos_sospechosos=[],
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
            "compresion_estandar": self.compresion_estandar,
            "compresion_sospechosa": self.compresion_sospechosa,
            "metodos_compresion": self.metodos_compresion,
            "compresion_principal": self.compresion_principal,
            "metodos_sospechosos": self.metodos_sospechosos,
            "indicadores_sospechosos": self.indicadores_sospechosos,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_compresion": {
                "metodos_detectados": self.metodos_detectados,
                "compresion_principal": self.compresion_principal,
                "compresion_secundaria": self.compresion_secundaria,
                "metodos_sospechosos": self.metodos_sospechosos
            },
            "indicadores_forenses": {
                "compresion_no_estandar": not self.compresion_estandar,
                "metodos_sospechosos": len(self.metodos_sospechosos) > 0,
                "compresion_mixta": len(self.metodos_detectados) > 1,
                "compresion_inusual": self.compresion_sospechosa,
                "posible_manipulacion": self.risk_level == "HIGH"
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
