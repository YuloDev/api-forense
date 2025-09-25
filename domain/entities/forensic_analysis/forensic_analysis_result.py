"""
Entidades para análisis forense de documentos
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class AnalysisType(Enum):
    """Tipos de análisis forense"""
    PDF = "pdf"
    IMAGE = "image"

class RiskLevel(Enum):
    """Niveles de riesgo"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class EvidenceType(Enum):
    """Tipos de evidencia forense"""
    METADATA_ANOMALY = "metadata_anomaly"
    COMPRESSION_ARTIFACT = "compression_artifact"
    EDITING_SIGNATURE = "editing_signature"
    TEXT_OVERLAY = "text_overlay"
    SIGNATURE_MISMATCH = "signature_mismatch"
    TIMESTAMP_INCONSISTENCY = "timestamp_inconsistency"
    FORMAT_ANOMALY = "format_anomaly"

@dataclass
class BBox:
    """Bounding box para coordenadas"""
    x: float
    y: float
    w: float
    h: float

@dataclass
class ForensicEvidence:
    """Evidencia forense individual"""
    evidence_type: EvidenceType
    confidence: float
    description: str
    bbox: Optional[BBox] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    severity: RiskLevel = RiskLevel.MEDIUM

@dataclass
class MetadataAnalysis:
    """Análisis de metadatos"""
    has_exif: bool
    has_xmp: bool
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    software_used: List[str] = field(default_factory=list)
    camera_info: Dict[str, Any] = field(default_factory=dict)
    anomalies: List[str] = field(default_factory=list)

@dataclass
class CompressionAnalysis:
    """Análisis de compresión"""
    is_double_compressed: bool
    compression_quality: Optional[float] = None
    artifacts_detected: List[str] = field(default_factory=list)
    compression_history: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class TextAnalysis:
    """Análisis de texto"""
    has_text_overlay: bool
    suspicious_text_areas: List[BBox] = field(default_factory=list)
    font_inconsistencies: List[Dict[str, Any]] = field(default_factory=list)
    text_confidence_scores: List[float] = field(default_factory=list)

@dataclass
class ImageIntegrityAnalysis:
    """Análisis de integridad de imagen"""
    ela_anomalies: List[BBox] = field(default_factory=list)
    noise_inconsistencies: List[BBox] = field(default_factory=list)
    edge_anomalies: List[BBox] = field(default_factory=list)
    color_anomalies: List[BBox] = field(default_factory=list)

@dataclass
class ForensicAnalysisResult:
    """Resultado completo del análisis forense"""
    analysis_id: str
    analysis_type: AnalysisType
    document_hash: str
    timestamp: datetime
    risk_level: RiskLevel
    overall_confidence: float
    
    # Análisis específicos
    metadata_analysis: MetadataAnalysis
    compression_analysis: CompressionAnalysis
    text_analysis: TextAnalysis
    image_integrity_analysis: ImageIntegrityAnalysis
    
    # Evidencias encontradas
    evidences: List[ForensicEvidence] = field(default_factory=list)
    
    # Resumen
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    # Metadatos técnicos
    processing_time_ms: int = 0
    analysis_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entidad a diccionario para serialización JSON"""
        return {
            "analysis_id": self.analysis_id,
            "analysis_type": self.analysis_type.value,
            "document_hash": self.document_hash,
            "timestamp": self.timestamp.isoformat(),
            "risk_level": self.risk_level.value,
            "overall_confidence": self.overall_confidence,
            "metadata_analysis": {
                "has_exif": self.metadata_analysis.has_exif,
                "has_xmp": self.metadata_analysis.has_xmp,
                "creation_date": self.metadata_analysis.creation_date.isoformat() if self.metadata_analysis.creation_date else None,
                "modification_date": self.metadata_analysis.modification_date.isoformat() if self.metadata_analysis.modification_date else None,
                "software_used": self.metadata_analysis.software_used,
                "camera_info": self.metadata_analysis.camera_info,
                "anomalies": self.metadata_analysis.anomalies
            },
            "compression_analysis": {
                "is_double_compressed": self.compression_analysis.is_double_compressed,
                "compression_quality": self.compression_analysis.compression_quality,
                "artifacts_detected": self.compression_analysis.artifacts_detected,
                "compression_history": self.compression_analysis.compression_history
            },
            "text_analysis": {
                "has_text_overlay": self.text_analysis.has_text_overlay,
                "suspicious_text_areas": [
                    {"x": bbox.x, "y": bbox.y, "w": bbox.w, "h": bbox.h}
                    for bbox in self.text_analysis.suspicious_text_areas
                ],
                "font_inconsistencies": self.text_analysis.font_inconsistencies,
                "text_confidence_scores": self.text_analysis.text_confidence_scores
            },
            "image_integrity_analysis": {
                "ela_anomalies": [
                    {"x": bbox.x, "y": bbox.y, "w": bbox.w, "h": bbox.h}
                    for bbox in self.image_integrity_analysis.ela_anomalies
                ],
                "noise_inconsistencies": [
                    {"x": bbox.x, "y": bbox.y, "w": bbox.w, "h": bbox.h}
                    for bbox in self.image_integrity_analysis.noise_inconsistencies
                ],
                "edge_anomalies": [
                    {"x": bbox.x, "y": bbox.y, "w": bbox.w, "h": bbox.h}
                    for bbox in self.image_integrity_analysis.edge_anomalies
                ],
                "color_anomalies": [
                    {"x": bbox.x, "y": bbox.y, "w": bbox.w, "h": bbox.h}
                    for bbox in self.image_integrity_analysis.color_anomalies
                ]
            },
            "evidences": [
                {
                    "evidence_type": evidence.evidence_type.value,
                    "confidence": evidence.confidence,
                    "description": evidence.description,
                    "bbox": {"x": evidence.bbox.x, "y": evidence.bbox.y, "w": evidence.bbox.w, "h": evidence.bbox.h} if evidence.bbox else None,
                    "metadata": evidence.metadata,
                    "severity": evidence.severity.value
                }
                for evidence in self.evidences
            ],
            "summary": self.summary,
            "recommendations": self.recommendations,
            "processing_time_ms": self.processing_time_ms,
            "analysis_version": self.analysis_version
        }
