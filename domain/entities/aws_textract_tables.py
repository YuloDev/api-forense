from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class TableCell:
    """Entidad de dominio para celda de tabla"""
    row: int
    column: int
    text: str
    confidence: float
    cell_id: str
    is_header: bool = False
    is_merged: bool = False
    rowspan: int = 1
    colspan: int = 1


@dataclass
class DetectedTable:
    """Entidad de dominio para tabla detectada"""
    table_id: str
    table_number: int
    total_rows: int
    total_columns: int
    confidence: float
    cells: List[TableCell]
    title: Optional[str] = None
    footer: Optional[str] = None
    table_type: str = "STRUCTURED"


@dataclass
class TableValidation:
    """Validación de estructura de tabla"""
    table_id: str
    is_valid: bool
    detected_problems: List[str]
    empty_cells: int
    cells_with_text: int
    complete_rows: int
    complete_columns: int
    integrity_score: float


@dataclass
class TableAnalysisResult:
    """Resultado del análisis de tablas"""
    total_tables: int
    detected_tables: List[DetectedTable]
    validations: List[TableValidation]
    average_confidence: float
    document_type: str
    statistics: Dict[str, Any]
    processing_time_ms: float


@dataclass
class TableExtractionRequest:
    """Petición para extracción de tablas"""
    document_bytes: bytes
    document_type: str
