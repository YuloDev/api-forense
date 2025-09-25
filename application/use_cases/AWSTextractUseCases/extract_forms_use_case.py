from typing import Dict, Any

from domain.ports.aws_textract_service import AWSTextractService
from domain.entities.aws_textract_forms import FormExtractionRequest, FormAnalysisResult


class ExtractFormsUseCase:
    """Use case para extracción de formularios con AWS Textract"""

    def __init__(self, textract_service: AWSTextractService):
        self.textract_service = textract_service

    def execute(self, document_base64: str) -> Dict[str, Any]:
        """
        Ejecuta la extracción de formularios
        
        Args:
            document_base64: Documento en base64
            
        Returns:
            Dict con el resultado de la extracción
        """
        try:
            # Validar documento
            document_bytes = self.textract_service.validate_document(document_base64)
            document_type = self.textract_service.detect_document_type(document_bytes)
            
            # Crear petición de extracción
            request = FormExtractionRequest(
                document_bytes=document_bytes,
                document_type=document_type
            )
            
            # Ejecutar extracción
            result = self.textract_service.extract_forms(request)
            
            # Formatear respuesta
            return {
                "success": True,
                "total_pairs": result.total_pairs,
                "key_value_pairs": [
                    {
                        "page": pair.page,
                        "key": pair.key,
                        "value": pair.value,
                        "key_confidence": pair.key_confidence,
                        "value_confidence": pair.value_confidence,
                        "key_id": pair.key_id,
                        "value_id": pair.value_id,
                        "selection_status": pair.selection_status
                    }
                    for pair in result.key_value_pairs
                ],
                "average_key_confidence": result.average_key_confidence,
                "average_value_confidence": result.average_value_confidence,
                "document_type": result.document_type,
                "processing_time_ms": result.processing_time_ms,
                "message": f"Se extrajeron {result.total_pairs} pares clave-valor del formulario. Confianza promedio: claves {result.average_key_confidence:.1f}%, valores {result.average_value_confidence:.1f}%"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_pairs": 0,
                "key_value_pairs": [],
                "average_key_confidence": 0.0,
                "average_value_confidence": 0.0,
                "document_type": "",
                "processing_time_ms": 0.0
            }
