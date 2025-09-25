from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class BBox:
    x: int
    y: int
    w: int
    h: int

@dataclass
class SourceInfo:
    filename: str
    mime: str
    width_px: int
    height_px: int
    dpi_estimado: float
    rotation_deg: float

@dataclass
class Palabra:
    bbox: BBox
    confidence: float
    texto: str
    font_family: Optional[str] = None
    font_size: Optional[float] = None
    font_style: Optional[str] = None  # normal, bold, italic
    font_weight: Optional[str] = None

@dataclass
class Linea:
    bbox: BBox
    confidence: float
    texto: str
    palabras: List[Palabra]

@dataclass
class Bloque:
    bbox: BBox
    confidence: float
    lang: str
    lineas: List[Linea]

@dataclass
class ZonaBajaConfianza:
    bbox: BBox
    confidence_avg: float

@dataclass
class MetricasOCR:
    skew_deg: float
    densidad_lineas_por_1000px: float
    porcentaje_area_texto: float
    zonas_baja_confianza: List[ZonaBajaConfianza]

@dataclass
class OCRInfo:
    engine: str
    lang_detected: List[str]
    confidence_avg: float
    confidence_std: float
    texto_full: str
    bloques: List[Bloque]
    metricas: MetricasOCR

@dataclass
class FechaNormalizada:
    texto_raw: str
    iso8601: str
    bbox: BBox

@dataclass
class MonedaNormalizada:
    texto_raw: str
    valor: float
    moneda: str
    bbox: BBox

@dataclass
class Identificador:
    tipo: str  # RUC|CI|FACTURA|OTRO
    texto_raw: str
    valor: str
    bbox: BBox
    regex: str

@dataclass
class CampoClave:
    label_detectada: str
    bbox_label: BBox
    valor_raw: str
    valor_normalizado: float
    bbox_valor: BBox

@dataclass
class ItemDetectado:
    descripcion_raw: str
    descripcion_normalizada: str
    cantidad: int
    precio_unitario: float
    importe: float
    bboxes: Dict[str, BBox]

@dataclass
class Normalizaciones:
    fechas: List[FechaNormalizada]
    monedas: List[MonedaNormalizada]
    identificadores: List[Identificador]
    campos_clave: List[CampoClave]
    items_detectados: List[ItemDetectado]

@dataclass
class AlertaForense:
    tipo: str  # sobreposicion_sospechosa|formato_inconsistente|baja_confianza_local|alineacion_anomala|moneda_incongruente|aritmetica_inconsistente
    severidad: str  # low|medium|high
    detalle: str
    bbox: BBox

@dataclass
class ResumenForense:
    score_calidad_ocr: float
    score_integridad_textual: float
    tiene_inconsistencias_monetarias: bool
    tiene_sobreposiciones_sospechosas: bool

@dataclass
class ForenseInfo:
    alertas: List[AlertaForense]
    resumen: ResumenForense

@dataclass
class TiemposMS:
    preprocesado: int
    ocr: int
    postprocesado: int

@dataclass
class FuenteDetectada:
    font_family: str
    font_size: float
    font_style: str
    font_weight: str
    count: int
    percentage: float
    confidence_avg: float

@dataclass
class AnalisisFuentes:
    fuentes_detectadas: List[FuenteDetectada]
    total_fuentes: int
    fuentes_unicas: int
    indice_diversidad: float  # 0-1, donde 1 es máxima diversidad
    fuentes_sospechosas: List[str]
    consistencia_score: float  # 0-1, donde 1 es máxima consistencia

@dataclass
class ForensicOCRDetails:
    source: SourceInfo
    ocr: OCRInfo
    normalizaciones: Normalizaciones
    forense: ForenseInfo
    version: str
    tiempos_ms: TiemposMS
    success: bool
    analisis_fuentes: Optional[AnalisisFuentes] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entidad a diccionario para serialización JSON"""
        return {
            "source": {
                "filename": self.source.filename,
                "mime": self.source.mime,
                "width_px": self.source.width_px,
                "height_px": self.source.height_px,
                "dpi_estimado": self.source.dpi_estimado,
                "rotation_deg": self.source.rotation_deg
            },
            "ocr": {
                "engine": self.ocr.engine,
                "lang_detected": self.ocr.lang_detected,
                "confidence_avg": self.ocr.confidence_avg,
                "confidence_std": self.ocr.confidence_std,
                "texto_full": self.ocr.texto_full,
                "bloques": [
                    {
                        "bbox": {"x": b.bbox.x, "y": b.bbox.y, "w": b.bbox.w, "h": b.bbox.h},
                        "confidence": b.confidence,
                        "lang": b.lang,
                        "lineas": [
                            {
                                "bbox": {"x": l.bbox.x, "y": l.bbox.y, "w": l.bbox.w, "h": l.bbox.h},
                                "confidence": l.confidence,
                                "texto": l.texto,
                                "palabras": [
                                    {
                                        "bbox": {"x": p.bbox.x, "y": p.bbox.y, "w": p.bbox.w, "h": p.bbox.h},
                                        "confidence": p.confidence,
                                        "texto": p.texto,
                                        "font_family": p.font_family,
                                        "font_size": p.font_size,
                                        "font_style": p.font_style,
                                        "font_weight": p.font_weight
                                    } for p in l.palabras
                                ]
                            } for l in b.lineas
                        ]
                    } for b in self.ocr.bloques
                ],
                "metricas": {
                    "skew_deg": self.ocr.metricas.skew_deg,
                    "densidad_lineas_por_1000px": self.ocr.metricas.densidad_lineas_por_1000px,
                    "porcentaje_area_texto": self.ocr.metricas.porcentaje_area_texto,
                    "zonas_baja_confianza": [
                        {
                            "bbox": {"x": z.bbox.x, "y": z.bbox.y, "w": z.bbox.w, "h": z.bbox.h},
                            "confidence_avg": z.confidence_avg
                        } for z in self.ocr.metricas.zonas_baja_confianza
                    ]
                }
            },
            "normalizaciones": {
                "fechas": [
                    {
                        "texto_raw": f.texto_raw,
                        "iso8601": f.iso8601,
                        "bbox": {"x": f.bbox.x, "y": f.bbox.y, "w": f.bbox.w, "h": f.bbox.h}
                    } for f in self.normalizaciones.fechas
                ],
                "monedas": [
                    {
                        "texto_raw": m.texto_raw,
                        "valor": m.valor,
                        "moneda": m.moneda,
                        "bbox": {"x": m.bbox.x, "y": m.bbox.y, "w": m.bbox.w, "h": m.bbox.h}
                    } for m in self.normalizaciones.monedas
                ],
                "identificadores": [
                    {
                        "tipo": i.tipo,
                        "texto_raw": i.texto_raw,
                        "valor": i.valor,
                        "bbox": {"x": i.bbox.x, "y": i.bbox.y, "w": i.bbox.w, "h": i.bbox.h},
                        "regex": i.regex
                    } for i in self.normalizaciones.identificadores
                ],
                "campos_clave": [
                    {
                        "label_detectada": c.label_detectada,
                        "bbox_label": {"x": c.bbox_label.x, "y": c.bbox_label.y, "w": c.bbox_label.w, "h": c.bbox_label.h},
                        "valor_raw": c.valor_raw,
                        "valor_normalizado": c.valor_normalizado,
                        "bbox_valor": {"x": c.bbox_valor.x, "y": c.bbox_valor.y, "w": c.bbox_valor.w, "h": c.bbox_valor.h}
                    } for c in self.normalizaciones.campos_clave
                ],
                "items_detectados": [
                    {
                        "descripcion_raw": item.descripcion_raw,
                        "descripcion_normalizada": item.descripcion_normalizada,
                        "cantidad": item.cantidad,
                        "precio_unitario": item.precio_unitario,
                        "importe": item.importe,
                        "bboxes": {
                            key: {"x": bbox.x, "y": bbox.y, "w": bbox.w, "h": bbox.h}
                            for key, bbox in item.bboxes.items()
                        }
                    } for item in self.normalizaciones.items_detectados
                ]
            },
            "forense": {
                "alertas": [
                    {
                        "tipo": a.tipo,
                        "severidad": a.severidad,
                        "detalle": a.detalle,
                        "bbox": {"x": a.bbox.x, "y": a.bbox.y, "w": a.bbox.w, "h": a.bbox.h}
                    } for a in self.forense.alertas
                ],
                "resumen": {
                    "score_calidad_ocr": self.forense.resumen.score_calidad_ocr,
                    "score_integridad_textual": self.forense.resumen.score_integridad_textual,
                    "tiene_inconsistencias_monetarias": self.forense.resumen.tiene_inconsistencias_monetarias,
                    "tiene_sobreposiciones_sospechosas": self.forense.resumen.tiene_sobreposiciones_sospechosas
                }
            },
            "analisis_fuentes": {
                "fuentes_detectadas": [
                    {
                        "font_family": f.font_family,
                        "font_size": f.font_size,
                        "font_style": f.font_style,
                        "font_weight": f.font_weight,
                        "count": f.count,
                        "percentage": f.percentage,
                        "confidence_avg": f.confidence_avg
                    } for f in self.analisis_fuentes.fuentes_detectadas
                ] if self.analisis_fuentes else [],
                "total_fuentes": self.analisis_fuentes.total_fuentes if self.analisis_fuentes else 0,
                "fuentes_unicas": self.analisis_fuentes.fuentes_unicas if self.analisis_fuentes else 0,
                "indice_diversidad": self.analisis_fuentes.indice_diversidad if self.analisis_fuentes else 0.0,
                "fuentes_sospechosas": self.analisis_fuentes.fuentes_sospechosas if self.analisis_fuentes else [],
                "consistencia_score": self.analisis_fuentes.consistencia_score if self.analisis_fuentes else 0.0
            },
            "version": self.version,
            "tiempos_ms": {
                "preprocesado": self.tiempos_ms.preprocesado,
                "ocr": self.tiempos_ms.ocr,
                "postprocesado": self.tiempos_ms.postprocesado
            },
            "success": self.success,
            "error": self.error
        }