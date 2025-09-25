from typing import Dict, Any, List, Tuple

from domain.entities.aws_textract_document import DocumentMetadata
from domain.entities.aws_textract_forms import KeyValuePair
from domain.entities.aws_textract_tables import TableCell, DetectedTable, TableValidation
from .key_value_processor import KeyValueProcessor
from .table_processor import TableProcessor


class TextractResponseProcessor:
    """Procesador de respuestas de AWS Textract"""

    @staticmethod
    def process_basic_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa la respuesta básica de AWS Textract"""
        blocks = response.get('Blocks', [])
        
        text_lines = []
        confidences = []
        
        for block in blocks:
            if block.get('BlockType') == 'LINE':
                text = block.get('Text', '')
                confidence = block.get('Confidence', 0.0)
                
                if text.strip():
                    text_lines.append(text)
                    confidences.append(confidence)
        
        full_text = '\n'.join(text_lines)
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        metadata = TextractResponseProcessor._create_metadata(blocks, confidences, text_lines)
        
        return {
            "extracted_text": full_text,
            "average_confidence": average_confidence,
            "total_blocks": len(blocks),
            "metadata": metadata
        }

    @staticmethod
    def _create_metadata(blocks: List[Dict], confidences: List[float], text_lines: List[str]) -> Dict[str, Any]:
        """Crea metadata del documento procesado"""
        blocks_by_type = {}
        for block in blocks:
            block_type = block.get('BlockType', 'UNKNOWN')
            blocks_by_type[block_type] = blocks_by_type.get(block_type, 0) + 1
        
        return {
            "total_blocks": len(blocks),
            "blocks_by_type": blocks_by_type,
            "detected_documents": len([b for b in blocks if b.get('BlockType') == 'PAGE']),
            "min_confidence": min(confidences) if confidences else 0.0,
            "max_confidence": max(confidences) if confidences else 0.0,
            "text_lines": len(text_lines)
        }

    @staticmethod
    def extract_key_value_pairs(response: Dict[str, Any]) -> List[KeyValuePair]:
        """Extrae pares clave-valor de la respuesta de Textract"""
        blocks = response.get('Blocks', [])
        blocks_map = {block.get('Id'): block for block in blocks}
        
        processor = KeyValueProcessor(blocks_map)
        return processor.extract_pairs(blocks)

    @staticmethod
    def extract_tables(response: Dict[str, Any]) -> List[DetectedTable]:
        """Extrae tablas de la respuesta de Textract"""
        blocks = response.get('Blocks', [])
        blocks_map = {block.get('Id'): block for block in blocks}
        
        processor = TableProcessor(blocks_map)
        return processor.extract_tables(blocks)

    @staticmethod
    def validate_table_structure(table: DetectedTable) -> TableValidation:
        """Valida la estructura de una tabla"""
        processor = TableProcessor({})
        return processor.validate_table_structure(table)
