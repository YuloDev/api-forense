"""
Caso de uso para análisis forense de imagen
"""
from typing import Dict, Any
from domain.ports.forensic_analysis import ForensicAnalysisServicePort

class AnalyzeImageForensicUseCase:
    """Caso de uso para análisis forense de imagen"""
    
    def __init__(self, forensic_analysis_service: ForensicAnalysisServicePort):
        self.forensic_analysis_service = forensic_analysis_service
    
    def execute(self, image_base64: str) -> Dict[str, Any]:
        """
        Ejecuta el análisis forense de una imagen
        
        Args:
            image_base64: Imagen codificada en base64
            
        Returns:
            Dict con resultado del análisis forense
        """
        try:
            # Delegar al servicio de análisis forense
            result = self.forensic_analysis_service.analyze_image_forensic(image_base64)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analysis_type": "image",
                "risk_level": "unknown",
                "evidences": [],
                "summary": f"Error en análisis forense: {str(e)}"
            }
