"""
Entidad para el resultado del check de evidencias forenses.

Analiza indicadores técnicos que sugieren que la imagen ha sido modificada o manipulada digitalmente.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class EvidenciasForensesResult:
    """Resultado del análisis de evidencias forenses"""
    
    check_name: str
    evidencias_forenses_detectadas: bool
    grado_confianza: str  # BAJO, MEDIO, ALTO, ERROR
    porcentaje_confianza: float
    puntuacion: int
    max_puntuacion: int
    es_screenshot: bool
    tipo_imagen: str
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH
    penalty_points: int
    source_type: str  # "image" (solo para imágenes)
    
    # Detalles específicos del análisis
    evidencias: List[str]
    metadatos: Dict[str, Any]
    compresion: Dict[str, Any]
    cuadricula_jpeg: Dict[str, Any]
    texto_sintetico: Dict[str, Any]
    ela: Dict[str, Any]
    ruido_bordes: Dict[str, Any]
    hashes: Dict[str, Any]
    overlays: Dict[str, Any]
    indicadores_sospechosos: List[str]
    analysis_notes: List[str]
    
    # Metadatos adicionales
    file_size_bytes: Optional[int]
    processing_time_ms: int
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.evidencias is None:
            self.evidencias = []
        if self.metadatos is None:
            self.metadatos = {}
        if self.compresion is None:
            self.compresion = {}
        if self.cuadricula_jpeg is None:
            self.cuadricula_jpeg = {}
        if self.texto_sintetico is None:
            self.texto_sintetico = {}
        if self.ela is None:
            self.ela = {}
        if self.ruido_bordes is None:
            self.ruido_bordes = {}
        if self.hashes is None:
            self.hashes = {}
        if self.overlays is None:
            self.overlays = {}
        if self.indicadores_sospechosos is None:
            self.indicadores_sospechosos = []
        if self.analysis_notes is None:
            self.analysis_notes = []
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'EvidenciasForensesResult':
        """Crea un resultado de error"""
        return cls(
            check_name="Análisis de evidencias forenses",
            evidencias_forenses_detectadas=False,
            grado_confianza="ERROR",
            porcentaje_confianza=0.0,
            puntuacion=0,
            max_puntuacion=0,
            es_screenshot=False,
            tipo_imagen="unknown",
            confidence=0.0,
            risk_level="LOW",
            penalty_points=0,
            source_type="image",
            evidencias=[],
            metadatos={},
            compresion={},
            cuadricula_jpeg={},
            texto_sintetico={},
            ela={},
            ruido_bordes={},
            hashes={},
            overlays={},
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
            "evidencias_forenses_detectadas": self.evidencias_forenses_detectadas,
            "grado_confianza": self.grado_confianza,
            "porcentaje_confianza": self.porcentaje_confianza,
            "puntuacion": self.puntuacion,
            "max_puntuacion": self.max_puntuacion,
            "es_screenshot": self.es_screenshot,
            "tipo_imagen": self.tipo_imagen,
            "indicadores_sospechosos": self.indicadores_sospechosos,
            "notas_analisis": self.analysis_notes
        }
        
        # Generar detalle del análisis
        detalle = {
            "tipo_archivo": self.source_type,
            "tamaño_archivo_bytes": self.file_size_bytes,
            "tiempo_procesamiento_ms": self.processing_time_ms,
            "analisis_evidencias_forenses": {
                "evidencias": self.evidencias,
                "metadatos": self.metadatos,
                "compresion": self.compresion,
                "cuadricula_jpeg": self.cuadricula_jpeg,
                "texto_sintetico": self.texto_sintetico,
                "ela": self.ela,
                "ruido_bordes": self.ruido_bordes,
                "hashes": self.hashes,
                "overlays": self.overlays,
                "estadisticas": {
                    "total_evidencias": len(self.evidencias),
                    "evidencias_forenses_detectadas": self.evidencias_forenses_detectadas,
                    "grado_confianza": self.grado_confianza,
                    "porcentaje_confianza": self.porcentaje_confianza,
                    "puntuacion": self.puntuacion,
                    "max_puntuacion": self.max_puntuacion,
                    "es_screenshot": self.es_screenshot,
                    "tipo_imagen": self.tipo_imagen
                }
            },
            "indicadores_forenses": {
                "evidencias_forenses_presentes": self.evidencias_forenses_detectadas,
                "alto_grado_confianza": self.grado_confianza == "ALTO",
                "es_screenshot": self.es_screenshot,
                "múltiples_evidencias": len(self.evidencias) > 3,
                "posible_manipulacion": self.risk_level == "HIGH"
            }
        }
        
        return {
            "check": self.check_name,
            "resumen": resumen,
            "detalle": detalle,
            "penalizacion": self.penalty_points
        }
