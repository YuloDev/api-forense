from typing import Dict, Any

from domain.ports.aws_textract_service import AWSTextractService
from domain.entities.aws_textract_tables import TableExtractionRequest, TableAnalysisResult


class ExtractTablesUseCase:
    """Use case para extracción de tablas con AWS Textract"""

    def __init__(self, textract_service: AWSTextractService):
        self.textract_service = textract_service

    def execute(self, document_base64: str) -> Dict[str, Any]:
        """
        Ejecuta la extracción de tablas
        
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
            request = TableExtractionRequest(
                document_bytes=document_bytes,
                document_type=document_type
            )
            
            # Ejecutar extracción
            result = self.textract_service.extract_tables(request)
            
            # Formatear respuesta
            return {
                "success": True,
                "total_tables": result.total_tables,
                "detected_tables": [
                    {
                        "table_id": table.table_id,
                        "table_number": table.table_number,
                        "total_rows": table.total_rows,
                        "total_columns": table.total_columns,
                        "confidence": table.confidence,
                        "cells": [
                            {
                                "row": cell.row,
                                "column": cell.column,
                                "text": cell.text,
                                "confidence": cell.confidence,
                                "cell_id": cell.cell_id,
                                "is_header": cell.is_header,
                                "is_merged": cell.is_merged,
                                "rowspan": cell.rowspan,
                                "colspan": cell.colspan
                            }
                            for cell in table.cells
                        ],
                        "title": table.title,
                        "footer": table.footer,
                        "table_type": table.table_type
                    }
                    for table in result.detected_tables
                ],
                "validations": [
                    {
                        "table_id": validation.table_id,
                        "is_valid": validation.is_valid,
                        "detected_problems": validation.detected_problems,
                        "empty_cells": validation.empty_cells,
                        "cells_with_text": validation.cells_with_text,
                        "complete_rows": validation.complete_rows,
                        "complete_columns": validation.complete_columns,
                        "integrity_score": validation.integrity_score
                    }
                    for validation in result.validations
                ],
                "average_confidence": result.average_confidence,
                "document_type": result.document_type,
                "statistics": result.statistics,
                "processing_time_ms": result.processing_time_ms,
                "message": f"Se detectaron {result.total_tables} tablas. {result.statistics.get('valid_tables', 0)} válidas, {result.statistics.get('total_cells', 0)} celdas totales con {result.statistics.get('percentage_filled_cells', 0)}% de ocupación."
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_tables": 0,
                "detected_tables": [],
                "validations": [],
                "average_confidence": 0.0,
                "document_type": "",
                "statistics": {},
                "processing_time_ms": 0.0
            }
