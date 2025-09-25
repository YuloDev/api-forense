"""
Entidades de análisis forense
"""
from .forensic_analysis_result import (
    ForensicAnalysisResult,
    ForensicEvidence,
    MetadataAnalysis,
    CompressionAnalysis,
    TextAnalysis,
    ImageIntegrityAnalysis,
    BBox,
    AnalysisType,
    RiskLevel,
    EvidenceType
)

__all__ = [
    'ForensicAnalysisResult',
    'ForensicEvidence',
    'MetadataAnalysis',
    'CompressionAnalysis',
    'TextAnalysis',
    'ImageIntegrityAnalysis',
    'BBox',
    'AnalysisType',
    'RiskLevel',
    'EvidenceType'
]
