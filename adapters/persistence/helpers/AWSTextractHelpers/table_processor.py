from typing import Dict, Any, List, Tuple

from domain.entities.aws_textract_tables import TableCell, DetectedTable, TableValidation
from .table_validator import TableValidator


class TableProcessor:
    """Procesador especializado para tablas de Textract"""

    def __init__(self, blocks_map: Dict[str, Dict[str, Any]]):
        self.blocks_map = blocks_map

    def extract_tables(self, blocks: List[Dict[str, Any]]) -> List[DetectedTable]:
        """Extrae todas las tablas detectadas"""
        detected_tables = []
        table_number = 1
        
        for block in blocks:
            if block.get('BlockType') == 'TABLE':
                table = self._create_detected_table(block, table_number)
                detected_tables.append(table)
                table_number += 1
        
        return detected_tables

    def _create_detected_table(self, table_block: Dict[str, Any], table_number: int) -> DetectedTable:
        """Crea una tabla detectada desde un bloque TABLE"""
        table_id = table_block.get('Id')
        table_confidence = table_block.get('Confidence', 0.0)
        
        title = self._get_table_element(table_block, 'TABLE_TITLE')
        footer = self._get_table_element(table_block, 'TABLE_FOOTER')
        
        cells, max_row, max_column = self._extract_table_cells(table_block)
        table_type = self._determine_table_type(table_block)
        
        return DetectedTable(
            table_id=table_id,
            table_number=table_number,
            total_rows=max_row,
            total_columns=max_column,
            confidence=table_confidence,
            cells=cells,
            title=title if title else None,
            footer=footer if footer else None,
            table_type=table_type
        )

    def _get_table_element(self, table_block: Dict[str, Any], element_type: str) -> str:
        """Obtiene título o pie de tabla"""
        relationships = table_block.get('Relationships', [])
        
        for rel in relationships:
            if rel.get('Type') == element_type:
                for element_id in rel.get('Ids', []):
                    element = self.blocks_map.get(element_id)
                    if element:
                        return self._get_cell_text(element_id)
        return ""

    def _extract_table_cells(self, table_block: Dict[str, Any]) -> Tuple[List[TableCell], int, int]:
        """Extrae todas las celdas de una tabla"""
        cells = []
        max_row = 0
        max_column = 0
        
        relationships = table_block.get('Relationships', [])
        for rel in relationships:
            if rel.get('Type') == 'CHILD':
                for cell_id in rel.get('Ids', []):
                    cell_block = self.blocks_map.get(cell_id)
                    
                    if cell_block and cell_block.get('BlockType') == 'CELL':
                        cell, row, column = self._create_table_cell(cell_id, cell_block)
                        cells.append(cell)
                        max_row = max(max_row, row)
                        max_column = max(max_column, column)
        
        return cells, max_row, max_column

    def _create_table_cell(self, cell_id: str, cell_block: Dict[str, Any]) -> Tuple[TableCell, int, int]:
        """Crea una celda de tabla"""
        row = cell_block.get('RowIndex', 1)
        column = cell_block.get('ColumnIndex', 1)
        text = self._get_cell_text(cell_id)
        confidence = cell_block.get('Confidence', 0.0)
        entity_types = cell_block.get('EntityTypes', [])
        
        is_header, is_merged = self._detect_cell_type(entity_types)
        
        rowspan = cell_block.get('RowSpan', 1)
        colspan = cell_block.get('ColumnSpan', 1)
        
        cell = TableCell(
            row=row,
            column=column,
            text=text,
            confidence=confidence,
            cell_id=cell_id,
            is_header=is_header,
            is_merged=is_merged,
            rowspan=rowspan,
            colspan=colspan
        )
        
        return cell, row, column

    def _get_cell_text(self, cell_id: str) -> str:
        """Obtiene texto de una celda"""
        cell_block = self.blocks_map.get(cell_id)
        if not cell_block:
            return ""
        
        if cell_block.get('Text'):
            return cell_block.get('Text', '').strip()
        
        return self._extract_word_texts(cell_block)

    def _extract_word_texts(self, cell_block: Dict[str, Any]) -> str:
        """Extrae textos de palabras en una celda"""
        texts = []
        relationships = cell_block.get('Relationships', [])
        
        for rel in relationships:
            if rel.get('Type') == 'CHILD':
                self._collect_word_texts(rel.get('Ids', []), texts)
        
        return ' '.join(texts)

    def _collect_word_texts(self, child_ids: List[str], texts: List[str]):
        """Recolecta textos de palabras desde una lista de IDs hijo"""
        for child_id in child_ids:
            child_block = self.blocks_map.get(child_id)
            if child_block and child_block.get('BlockType') == 'WORD':
                text = child_block.get('Text', '').strip()
                if text:
                    texts.append(text)

    def _detect_cell_type(self, entity_types: List[str]) -> Tuple[bool, bool]:
        """Detecta tipo de celda"""
        is_header = 'COLUMN_HEADER' in entity_types
        is_merged = 'MERGED_CELL' in entity_types
        return is_header, is_merged

    def _determine_table_type(self, table_block: Dict[str, Any]) -> str:
        """Determina el tipo de tabla"""
        entity_types = table_block.get('EntityTypes', [])
        
        if 'SEMI_STRUCTURED_TABLE' in entity_types:
            return "SEMI_STRUCTURED"
        elif 'STRUCTURED_TABLE' in entity_types:
            return "STRUCTURED"
        
        return "STRUCTURED"

    def validate_table_structure(self, table: DetectedTable) -> TableValidation:
        """Valida la estructura de una tabla"""
        validator = TableValidator(table)
        return validator.validate()
