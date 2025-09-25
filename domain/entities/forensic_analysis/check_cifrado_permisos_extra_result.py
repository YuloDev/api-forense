"""
Entidad para el resultado del check de cifrado y permisos especiales.

Analiza cifrado o permisos especiales aplicados que pueden usarse para ocultar el método de creación.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class CifradoPermisosExtraResult:
    """Resultado del análisis de cifrado y permisos especiales"""
    
    check_name: str
    cifrado_detectado: bool
    permisos_especiales: bool
    nivel_cifrado: str  # "none", "low", "medium", "high"
    tipos_permisos: List[str]
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "pdf" o "image"
    
    # Detalles específicos del análisis
    metodos_cifrado: List[str]
    restricciones_detectadas: List[Dict[str, Any]]
    permisos_restrictivos: List[str]
    indicadores_sospechosos: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.tipos_permisos is None:
            self.tipos_permisos = []
        if self.metodos_cifrado is None:
            self.metodos_cifrado = []
        if self.restricciones_detectadas is None:
            self.restricciones_detectadas = []
        if self.permisos_restrictivos is None:
            self.permisos_restrictivos = []
        if self.indicadores_sospechosos is None:
            self.indicadores_sospechosos = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'CifradoPermisosExtraResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Análisis de cifrado y permisos especiales",
            cifrado_detectado=False,
            permisos_especiales=False,
            nivel_cifrado="none",
            tipos_permisos=[],
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type="unknown",
            metodos_cifrado=[],
            restricciones_detectadas=[],
            permisos_restrictivos=[],
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
            "cifrado_detectado": self.cifrado_detectado,
            "permisos_especiales": self.permisos_especiales,
            "nivel_cifrado": self.nivel_cifrado,
            "tipos_permisos": self.tipos_permisos,
            "metodos_cifrado": self.metodos_cifrado,
            "permisos_restrictivos": self.permisos_restrictivos,
            "indicadores_sospechosos": self.indicadores_sospechosos,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_cifrado_permisos": {
                "metodos_cifrado": self.metodos_cifrado,
                "restricciones_detectadas": self.restricciones_detectadas,
                "permisos_restrictivos": self.permisos_restrictivos,
                "tipos_permisos": self.tipos_permisos
            },
            "indicadores_forenses": {
                "cifrado_presente": self.cifrado_detectado,
                "permisos_especiales": self.permisos_especiales,
                "cifrado_avanzado": self.nivel_cifrado in ["medium", "high"],
                "restricciones_multiples": len(self.restricciones_detectadas) > 1,
                "permisos_restrictivos": len(self.permisos_restrictivos) > 0,
                "posible_ocultamiento": self.risk_level == "HIGH"
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
