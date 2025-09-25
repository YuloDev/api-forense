"""
Caso de uso para análisis forense de PDF
"""
from typing import Dict, Any
from domain.ports.forensic_analysis import ForensicAnalysisServicePort

class AnalyzePDFForensicUseCase:
    """Caso de uso para análisis forense de PDF"""
    
    def __init__(self, forensic_analysis_service: ForensicAnalysisServicePort):
        self.forensic_analysis_service = forensic_analysis_service
    
    def execute(self, pdf_base64: str) -> Dict[str, Any]:
        """
        Ejecuta el análisis forense de un PDF
        
        Args:
            pdf_base64: PDF codificado en base64
            
        Returns:
            Dict con resultado del análisis forense
        """
        try:
            # Delegar al servicio de análisis forense
            result = self.forensic_analysis_service.analyze_pdf_forensic(pdf_base64)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analysis_type": "pdf",
                "risk_level": "unknown",
                "evidences": [],
                "summary": f"Error en análisis forense: {str(e)}"
            }
