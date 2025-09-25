"""
Entidad de dominio para el resultado del check de capas múltiples
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class CapasMultiplesResult:
    """Resultado del análisis de capas múltiples en PDF"""
    
    # Información básica
    check_name: str = "capas_multiples"
    has_layers: bool = False
    confidence: float = 0.0
    risk_level: str = "VERY_LOW"
    penalty_points: int = 0
    
    # Detalles técnicos
    ocg_objects: int = 0
    overlay_objects: int = 0
    transparency_objects: int = 0
    suspicious_operators: int = 0
    content_streams: int = 0
    layer_count_estimate: int = 0
    
    # Análisis detallado
    indicators: List[str] = None
    blend_modes: List[str] = None
    alpha_values: List[float] = None
    score_breakdown: Dict[str, Any] = None
    weights_used: Dict[str, float] = None
    detailed_analysis: Dict[str, Any] = None
    
    # Metadatos
    processing_time_ms: int = 0
    error: Optional[str] = None
    
    def __post_init__(self):
        """Inicializar listas vacías si son None"""
        if self.indicators is None:
            self.indicators = []
        if self.blend_modes is None:
            self.blend_modes = []
        if self.alpha_values is None:
            self.alpha_values = []
        if self.score_breakdown is None:
            self.score_breakdown = {}
        if self.weights_used is None:
            self.weights_used = {}
        if self.detailed_analysis is None:
            self.detailed_analysis = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entidad a diccionario para serialización JSON"""
        
        # Usar directamente el resumen_general del helper original
        resumen_general = self.detailed_analysis.get("resumen_general", {})
        
        return {
            "check": self.check_name,
            "resumen": resumen_general,  # Usar el resumen_general completo del helper original
            "detalle": self.detailed_analysis,
            "penalizacion": self.penalty_points
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        recommendations = []
        
        if self.risk_level == "HIGH":
            recommendations.append("Alto riesgo de manipulación detectado")
        elif self.risk_level == "MEDIUM":
            recommendations.append("Riesgo medio de texto superpuesto")
        else:
            recommendations.append("Riesgo bajo de manipulación")
        
        return recommendations
    
    @classmethod
    def create_error_result(cls, error_message: str) -> 'CapasMultiplesResult':
        """Crea un resultado de error"""
        return cls(
            error=error_message,
            has_layers=False,
            confidence=0.0,
            risk_level="VERY_LOW",
            penalty_points=0
        )
