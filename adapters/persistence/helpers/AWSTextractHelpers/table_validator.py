from typing import Dict, List

from domain.entities.aws_textract_tables import DetectedTable, TableValidation


class TableValidator:
    """Validador de estructura de tablas"""

    def __init__(self, table: DetectedTable):
        self.table = table
        self.matrix = self._create_cell_matrix()

    def validate(self) -> TableValidation:
        """Valida la estructura completa de la tabla"""
        problems = []
        empty_cells, cells_with_text = self._count_cell_content()
        
        complete_rows = self._validate_rows(problems)
        complete_columns = self._validate_columns(problems)
        
        self._validate_empty_cells_ratio(problems, empty_cells, len(self.table.cells))
        
        integrity_score = self._calculate_integrity_score(
            complete_rows, complete_columns, cells_with_text, len(self.table.cells)
        )
        
        is_valid = self._determine_validity(problems, integrity_score, cells_with_text)
        
        return TableValidation(
            table_id=self.table.table_id,
            is_valid=is_valid,
            detected_problems=problems,
            empty_cells=empty_cells,
            cells_with_text=cells_with_text,
            complete_rows=complete_rows,
            complete_columns=complete_columns,
            integrity_score=round(integrity_score, 2)
        )

    def _create_cell_matrix(self) -> Dict:
        """Crea matriz de celdas para verificación"""
        matrix = {}
        for cell in self.table.cells:
            key = (cell.row, cell.column)
            matrix[key] = cell
        return matrix

    def _count_cell_content(self) -> tuple:
        """Cuenta celdas vacías y con texto"""
        empty_cells = 0
        cells_with_text = 0
        
        for cell in self.table.cells:
            if cell.text.strip():
                cells_with_text += 1
            else:
                empty_cells += 1
        
        return empty_cells, cells_with_text

    def _validate_rows(self, problems: List[str]) -> int:
        """Valida filas completas"""
        complete_rows = 0
        
        for row in range(1, self.table.total_rows + 1):
            if self._is_row_complete(row):
                complete_rows += 1
            else:
                problems.append(f"Fila {row} incompleta")
        
        return complete_rows

    def _validate_columns(self, problems: List[str]) -> int:
        """Valida columnas completas"""
        complete_columns = 0
        
        for column in range(1, self.table.total_columns + 1):
            if self._is_column_complete(column):
                complete_columns += 1
            else:
                problems.append(f"Columna {column} incompleta")
        
        return complete_columns

    def _is_row_complete(self, row: int) -> bool:
        """Verifica si una fila está completa"""
        for column in range(1, self.table.total_columns + 1):
            if (row, column) not in self.matrix:
                return False
        return True

    def _is_column_complete(self, column: int) -> bool:
        """Verifica si una columna está completa"""
        for row in range(1, self.table.total_rows + 1):
            if (row, column) not in self.matrix:
                return False
        return True

    def _validate_empty_cells_ratio(self, problems: List[str], empty_cells: int, total_cells: int):
        """Valida ratio de celdas vacías"""
        if total_cells > 0:
            empty_percentage = (empty_cells / total_cells) * 100
            if empty_percentage > 50:
                problems.append(f"Demasiadas celdas vacías ({empty_percentage:.1f}%)")

    def _calculate_integrity_score(self, complete_rows: int, complete_columns: int, 
                                 cells_with_text: int, total_cells: int) -> float:
        """Calcula score de integridad"""
        if self.table.total_rows > 0 and self.table.total_columns > 0:
            rows_completeness = (complete_rows / self.table.total_rows) * 100
            columns_completeness = (complete_columns / self.table.total_columns) * 100
            content_score = (cells_with_text / total_cells * 100) if total_cells > 0 else 0
            
            return (rows_completeness + columns_completeness + content_score) / 3
        else:
            return 0

    def _determine_validity(self, problems: List[str], integrity_score: float, 
                          cells_with_text: int) -> bool:
        """Determina si la tabla es válida"""
        return (
            len(problems) == 0 and 
            integrity_score >= 70 and 
            cells_with_text > 0
        )
