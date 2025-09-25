"""
Caso de uso para análisis de capas múltiples
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_capas_multiples_service import CheckCapasMultiplesServicePort
from domain.entities.forensic_analysis.check_capas_multiples_result import CapasMultiplesResult

class AnalyzeCapasMultiplesUseCase:
    """Caso de uso para análisis de capas múltiples"""
    
    def __init__(self, capas_multiples_service: CheckCapasMultiplesServicePort):
        self.capas_multiples_service = capas_multiples_service
    
    def execute(self, pdf_bytes: bytes, extracted_text: str = "") -> Dict[str, Any]:
        """
        Ejecuta el análisis de capas múltiples
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            extracted_text: Texto extraído del PDF (opcional)
            
        Returns:
            Dict: Resultado del análisis en formato JSON
        """
        try:
            # Ejecutar análisis de capas múltiples
            result = self.capas_multiples_service.analyze_capas_multiples(pdf_bytes, extracted_text)
            
            # Convertir a diccionario para serialización JSON
            return result.to_dict()
            
        except Exception as e:
            # Crear resultado de error
            error_result = CapasMultiplesResult.create_error_result(str(e))
            return error_result.to_dict()
