from typing import Dict, Any, Optional, List

from domain.ports.aws_textract_service import AWSTextractService
from domain.entities.aws_textract_document import TextractDocument, TextractAnalysisResult


class AnalyzeDocumentUseCase:
    """Use case para análisis de documentos con AWS Textract"""

    def __init__(self, textract_service: AWSTextractService):
        self.textract_service = textract_service

    def execute(
        self, 
        document_base64: str, 
        analysis_type: str = "DETECT_DOCUMENT_TEXT",
        features: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el análisis de documento
        
        Args:
            document_base64: Documento en base64
            analysis_type: Tipo de análisis ("DETECT_DOCUMENT_TEXT" o "ANALYZE_DOCUMENT")
            features: Features para ANALYZE_DOCUMENT
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            # Validar documento
            document_bytes = self.textract_service.validate_document(document_base64)
            document_type = self.textract_service.detect_document_type(document_bytes)
            
            # Validar tipo de análisis
            valid_types = ["DETECT_DOCUMENT_TEXT", "ANALYZE_DOCUMENT"]
            if analysis_type not in valid_types:
                return {
                    "success": False,
                    "error": f"Tipo de análisis inválido. Debe ser uno de: {valid_types}"
                }
            
            # Crear entidad de documento
            document = TextractDocument(
                content_bytes=document_bytes,
                document_type=document_type,
                size_bytes=len(document_bytes),
                analysis_type=analysis_type,
                features=features
            )
            
            # Ejecutar análisis
            result = self.textract_service.analyze_document(document)
            
            # Formatear respuesta
            return {
                "success": True,
                "extracted_text": result.extracted_text,
                "average_confidence": result.average_confidence,
                "total_blocks": result.total_blocks,
                "metadata": result.metadata,
                "processing_time_ms": result.processing_time_ms,
                "message": f"OCR completado con AWS Textract. {len(result.extracted_text)} caracteres extraídos con confianza promedio de {result.average_confidence:.1f}%"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "extracted_text": "",
                "average_confidence": 0.0,
                "total_blocks": 0,
                "metadata": {},
                "processing_time_ms": 0.0
            }
