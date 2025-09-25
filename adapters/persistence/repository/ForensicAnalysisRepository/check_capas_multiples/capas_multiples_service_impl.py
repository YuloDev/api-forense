"""
Implementación del servicio de análisis de capas múltiples
"""

from domain.ports.forensic_analysis.check_capas_multiples_service import CheckCapasMultiplesServicePort
from domain.entities.forensic_analysis.check_capas_multiples_result import CapasMultiplesResult
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_capas_multiples.capas_multiples_analyzer import CapasMultiplesAnalyzer

class CapasMultiplesServiceAdapter(CheckCapasMultiplesServicePort):
    """Implementación del servicio de análisis de capas múltiples"""
    
    def __init__(self):
        self.analyzer = CapasMultiplesAnalyzer()
    
    def analyze_capas_multiples(self, pdf_bytes: bytes, extracted_text: str = "") -> CapasMultiplesResult:
        """
        Analiza la presencia de capas múltiples en un PDF
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            extracted_text: Texto extraído del PDF (opcional)
            
        Returns:
            CapasMultiplesResult: Resultado del análisis
        """
        try:
            # Validar entrada
            if not pdf_bytes:
                return CapasMultiplesResult.create_error_result("PDF bytes vacío")
            
            # Ejecutar análisis
            result = self.analyzer.analyze(pdf_bytes, extracted_text)
            
            return result
            
        except Exception as e:
            return CapasMultiplesResult.create_error_result(f"Error en servicio de capas múltiples: {str(e)}")
