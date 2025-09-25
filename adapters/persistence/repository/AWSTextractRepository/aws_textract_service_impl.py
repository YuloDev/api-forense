import time
from typing import Dict, Any

from domain.ports.aws_textract_service import AWSTextractService
from domain.entities.aws_textract_document import TextractDocument, TextractAnalysisResult
from domain.entities.aws_textract_forms import FormAnalysisResult, FormExtractionRequest
from domain.entities.aws_textract_tables import TableAnalysisResult, TableExtractionRequest

from adapters.persistence.helpers.AWSTextractHelpers.textract_client_helper import TextractClientHelper
from adapters.persistence.helpers.AWSTextractHelpers.textract_response_processor import TextractResponseProcessor
from utils import log_step


class AWSTextractServiceAdapter(AWSTextractService):
    """Adaptador para servicio de AWS Textract"""

    def __init__(self):
        self.client_helper = TextractClientHelper()
        self.response_processor = TextractResponseProcessor()

    def validate_document(self, document_base64: str) -> bytes:
        """Valida y decodifica documento base64"""
        return self.client_helper.validate_base64_document(document_base64)

    def detect_document_type(self, document_bytes: bytes) -> str:
        """Detecta el tipo de documento"""
        return self.client_helper.detect_document_type(document_bytes)

    @TextractClientHelper.handle_textract_errors
    def analyze_document(self, document: TextractDocument) -> TextractAnalysisResult:
        """Analiza un documento usando AWS Textract"""
        t_start = time.perf_counter()
        log_step("Iniciando análisis con AWS Textract", t_start)
        
        client = self.client_helper.create_textract_client()
        
        parameters = {
            'Document': {
                'Bytes': document.content_bytes
            }
        }
        
        if document.analysis_type == "ANALYZE_DOCUMENT":
            if document.features:
                valid_features = ["TABLES", "FORMS", "SIGNATURES", "LAYOUT"]
                filtered_features = [f for f in document.features if f in valid_features]
                parameters['FeatureTypes'] = filtered_features if filtered_features else ["TABLES", "FORMS"]
            else:
                parameters['FeatureTypes'] = ["TABLES", "FORMS"]
        
        log_step("Enviando documento a AWS Textract", time.perf_counter())
        
        if document.analysis_type == "DETECT_DOCUMENT_TEXT":
            response = client.detect_document_text(**parameters)
        else:
            response = client.analyze_document(**parameters)
        
        log_step("Respuesta recibida de AWS Textract", time.perf_counter())
        
        result = self.response_processor.process_basic_response(response)
        
        if document.analysis_type == "ANALYZE_DOCUMENT":
            additional_info = self._extract_additional_info(response)
            result["metadata"].update(additional_info)
        
        result["metadata"]["document_type"] = document.document_type
        result["metadata"]["size_bytes"] = document.size_bytes
        result["metadata"]["analysis_type"] = document.analysis_type
        
        processing_time = (time.perf_counter() - t_start) * 1000
        
        log_step(f"Análisis completado - {len(result['extracted_text'])} caracteres extraídos", time.perf_counter())
        
        return TextractAnalysisResult(
            extracted_text=result["extracted_text"],
            average_confidence=result["average_confidence"],
            total_blocks=result["total_blocks"],
            metadata=result["metadata"],
            processing_time_ms=processing_time
        )

    @TextractClientHelper.handle_textract_errors
    def extract_forms(self, request: FormExtractionRequest) -> FormAnalysisResult:
        """Extrae formularios de un documento"""
        t_start = time.perf_counter()
        log_step("Iniciando extracción de formularios con AWS Textract", t_start)
        
        client = self.client_helper.create_textract_client()
        
        parameters = {
            'Document': {
                'Bytes': request.document_bytes
            },
            'FeatureTypes': ["FORMS"]
        }
        
        log_step("Enviando documento a AWS Textract (FORMS)", time.perf_counter())
        response = client.analyze_document(**parameters)
        
        key_value_pairs = self.response_processor.extract_key_value_pairs(response)
        
        key_confidences = [pair.key_confidence for pair in key_value_pairs if pair.key_confidence > 0]
        value_confidences = [pair.value_confidence for pair in key_value_pairs if pair.value_confidence > 0]
        
        average_key_confidence = sum(key_confidences) / len(key_confidences) if key_confidences else 0.0
        average_value_confidence = sum(value_confidences) / len(value_confidences) if value_confidences else 0.0
        
        processing_time = (time.perf_counter() - t_start) * 1000
        
        log_step(f"Extracción completada - {len(key_value_pairs)} pares clave-valor encontrados", time.perf_counter())
        
        return FormAnalysisResult(
            total_pairs=len(key_value_pairs),
            key_value_pairs=key_value_pairs,
            average_key_confidence=average_key_confidence,
            average_value_confidence=average_value_confidence,
            document_type=request.document_type,
            processing_time_ms=processing_time
        )

    @TextractClientHelper.handle_textract_errors
    def extract_tables(self, request: TableExtractionRequest) -> TableAnalysisResult:
        """Extrae tablas de un documento"""
        t_start = time.perf_counter()
        log_step("Iniciando análisis de tablas con AWS Textract", t_start)
        
        client = self.client_helper.create_textract_client()
        
        parameters = {
            'Document': {
                'Bytes': request.document_bytes
            },
            'FeatureTypes': ["TABLES"]
        }
        
        log_step("Enviando documento a AWS Textract (TABLES)", time.perf_counter())
        response = client.analyze_document(**parameters)
        log_step("Respuesta recibida de AWS Textract", time.perf_counter())
        
        detected_tables = self.response_processor.extract_tables(response)
        
        validations = []
        confidences = []
        
        for table in detected_tables:
            validation = self.response_processor.validate_table_structure(table)
            validations.append(validation)
            confidences.append(table.confidence)
        
        total_tables = len(detected_tables)
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        total_cells = sum(len(table.cells) for table in detected_tables)
        total_cells_with_text = sum(v.cells_with_text for v in validations)
        total_empty_cells = sum(v.empty_cells for v in validations)
        valid_tables = sum(1 for v in validations if v.is_valid)
        
        statistics = {
            "total_cells": total_cells,
            "cells_with_text": total_cells_with_text,
            "empty_cells": total_empty_cells,
            "valid_tables": valid_tables,
            "tables_with_problems": total_tables - valid_tables,
            "percentage_filled_cells": round((total_cells_with_text / total_cells * 100) if total_cells > 0 else 0, 2),
            "average_integrity_score": round(sum(v.integrity_score for v in validations) / len(validations) if validations else 0, 2),
            "table_types": {table.table_type: 1 for table in detected_tables},
            "has_titles": sum(1 for table in detected_tables if table.title),
            "has_footers": sum(1 for table in detected_tables if table.footer)
        }
        
        processing_time = (time.perf_counter() - t_start) * 1000
        
        log_step(f"Análisis completado - {total_tables} tablas detectadas", time.perf_counter())
        
        return TableAnalysisResult(
            total_tables=total_tables,
            detected_tables=detected_tables,
            validations=validations,
            average_confidence=average_confidence,
            document_type=request.document_type,
            statistics=statistics,
            processing_time_ms=processing_time
        )

    def _extract_additional_info(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae información adicional para análisis de documentos"""
        blocks = response.get('Blocks', [])
        
        tables = []
        forms = []
        
        for block in blocks:
            if block.get('BlockType') == 'TABLE':
                table_info = {
                    "id": block.get('Id'),
                    "confidence": block.get('Confidence', 0.0),
                    "rows": block.get('RowIndex', 0),
                    "columns": block.get('ColumnIndex', 0)
                }
                tables.append(table_info)
            elif block.get('BlockType') == 'KEY_VALUE_SET':
                if block.get('EntityTypes') and 'KEY' in block.get('EntityTypes'):
                    form_info = {
                        "id": block.get('Id'),
                        "text": block.get('Text', '').strip(),
                        "confidence": block.get('Confidence', 0.0)
                    }
                    forms.append(form_info)
        
        key_value_pairs = self.response_processor.extract_key_value_pairs(response)
        
        return {
            "tables": tables,
            "form_fields": forms,
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
                for pair in key_value_pairs
            ],
            "total_tables": len(tables),
            "total_fields": len(forms),
            "total_key_value_pairs": len(key_value_pairs)
        }
