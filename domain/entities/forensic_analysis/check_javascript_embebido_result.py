"""
Entidad para el resultado del check de JavaScript embebido.

Analiza la presencia de código JavaScript embebido en documentos PDF.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class JavascriptEmbebidoResult:
    """Resultado del análisis de JavaScript embebido"""
    
    check_name: str
    javascript_detectado: bool
    cantidad_scripts: int
    scripts_sospechosos: int
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "pdf" o "image"
    
    # Detalles específicos del análisis
    scripts_encontrados: List[Dict[str, Any]]
    funciones_detectadas: List[str]
    eventos_detectados: List[str]
    indicadores_sospechosos: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.scripts_encontrados is None:
            self.scripts_encontrados = []
        if self.funciones_detectadas is None:
            self.funciones_detectadas = []
        if self.eventos_detectados is None:
            self.eventos_detectados = []
        if self.indicadores_sospechosos is None:
            self.indicadores_sospechosos = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'JavascriptEmbebidoResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Análisis de JavaScript embebido",
            javascript_detectado=False,
            cantidad_scripts=0,
            scripts_sospechosos=0,
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type="unknown",
            scripts_encontrados=[],
            funciones_detectadas=[],
            eventos_detectados=[],
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
            "javascript_detectado": self.javascript_detectado,
            "cantidad_scripts": self.cantidad_scripts,
            "scripts_sospechosos": self.scripts_sospechosos,
            "funciones_detectadas": self.funciones_detectadas,
            "eventos_detectados": self.eventos_detectados,
            "indicadores_sospechosos": self.indicadores_sospechosos,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_javascript": {
                "scripts_encontrados": self.scripts_encontrados,
                "funciones_detectadas": self.funciones_detectadas,
                "eventos_detectados": self.eventos_detectados,
                "scripts_sospechosos": self.scripts_sospechosos
            },
            "indicadores_forenses": {
                "javascript_presente": self.javascript_detectado,
                "scripts_multiples": self.cantidad_scripts > 1,
                "scripts_sospechosos": self.scripts_sospechosos > 0,
                "funciones_avanzadas": len(self.funciones_detectadas) > 0,
                "eventos_interactivos": len(self.eventos_detectados) > 0,
                "posible_ocultamiento": self.risk_level == "HIGH"
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
