"""
Helper para detección avanzada de capas múltiples en PDFs.

Este módulo proporciona un sistema modular y escalable para detectar 
capas múltiples (OCG) y técnicas de manipulación visual en documentos PDF.

Componentes principales:
1. LayerDetector - Clase principal para análisis
2. OCGAnalyzer - Análisis de Optional Content Groups
3. OverlayAnalyzer - Análisis de objetos superpuestos
4. TextOverlapAnalyzer - Análisis de superposición de texto
5. StructureAnalyzer - Análisis de estructura PDF
6. RiskCalculator - Cálculo de pesos y riesgos dinámicos
"""

import re
import statistics
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import fitz

# Configuración de patrones y constantes
class LayerPatterns:
    """Patrones para detección de diferentes tipos de capas y manipulaciones."""
    
    OCG_PATTERNS = [
        rb"/OCGs",
        rb"/OCProperties", 
        rb"/OC\s",
        rb"/ON\s+\[",
        rb"/OFF\s+\[",
        rb"/Order\s+\[",
        rb"/RBGroups",
        rb"/Locked\s+\[",
        rb"/AS\s+<<",
        rb"/Category\s+\["
    ]
    
    OVERLAY_PATTERNS = [
        rb"/Type\s*/XObject",
        rb"/Subtype\s*/Form",
        rb"/Group\s*<<",
        rb"/S\s*/Transparency",
        rb"/BM\s*/\w+",  # Blend modes
        rb"/CA\s+[\d\.]+",  # Constant alpha
        rb"/ca\s+[\d\.]+",  # Non-stroking alpha
    ]
    
    SUSPICIOUS_OPERATORS = [
        rb"q\s+[\d\.\-\s]+cm",  # Transformaciones de matriz
        rb"Do\s",  # XObject references
        rb"gs\s",  # Graphics state
        rb"/G\d+\s+gs",  # Graphics state references
    ]
    
    TRANSPARENCY_PATTERNS = [
        rb"/S\s*/Transparency",
        rb"/BM\s*/\w+",
        rb"/CA\s+[\d\.]+",
        rb"/ca\s+[\d\.]+",
        rb"/SMask",
        rb"/Group\s*<<"
    ]


class RiskWeights:
    """Configuración de pesos para cálculo de riesgo dinámico."""
    
    # Pesos para componentes de análisis (deben sumar 1.0)
    COMPONENT_WEIGHTS = {
        "ocg_confidence": 0.35,      # OCG detection (más importante)
        "overlay_presence": 0.25,    # Objetos superpuestos
        "text_overlapping": 0.25,    # Superposición de texto 
        "structure_suspicious": 0.15 # Análisis estructural
    }
    
    # Configuración de peso base y escalas
    BASE_WEIGHT = 15  # Peso base recomendado
    
    # Umbrales para clasificación de riesgo
    RISK_THRESHOLDS = {
        "VERY_HIGH": 0.8,   # 80%+
        "HIGH": 0.6,        # 60-79%
        "MEDIUM": 0.4,      # 40-59%
        "LOW": 0.2,         # 20-39%
        "VERY_LOW": 0.0     # 0-19%
    }
    
    # Multiplicadores de peso por nivel de riesgo
    RISK_MULTIPLIERS = {
        "VERY_HIGH": 1.0,   # Peso completo
        "HIGH": 0.8,        # 80% del peso
        "MEDIUM": 0.6,      # 60% del peso
        "LOW": 0.4,         # 40% del peso
        "VERY_LOW": 0.2     # 20% del peso
    }


import re, math
from typing import Any, Dict, List, Tuple, Optional

try:
    import fitz  # PyMuPDF (opcional pero recomendado)
except Exception:
    fitz = None


class OCGAnalyzer:
    """Analizador especializado para Optional Content Groups (OCG)."""

    def __init__(self, pdf_bytes: bytes):
        self.pdf_bytes = pdf_bytes
        self.sample_size = min(8_000_000, len(pdf_bytes))
        self.sample = pdf_bytes[:self.sample_size]

    # ------------------------ helpers internos ------------------------

    @staticmethod
    def _pattern_bytes(p) -> bytes:
        if hasattr(p, "pattern"):
            pat = p.pattern
            return pat if isinstance(pat, (bytes, bytearray)) else pat.encode("latin1", "ignore")
        return p if isinstance(p, (bytes, bytearray)) else bytes(p)

    @staticmethod
    def _find_unique(pattern, data: bytes) -> List[Tuple[int, int, bytes]]:
        pat = pattern if hasattr(pattern, "finditer") else re.compile(pattern)
        out = []
        for m in pat.finditer(data):
            # start, end y un pequeño sample del match
            out.append((m.start(), m.end(), data[m.start():m.start()+64]))
        # dedupe por offsets
        key = {}
        for s, e, snip in out:
            key[(s, e)] = snip
        return [(s, e, snip) for (s, e), snip in key.items()]

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    @staticmethod
    def _bytes_per_mb(n: int) -> float:
        return max(1.0, n / 1_000_000.0)

    # ------------------------ núcleo de análisis ------------------------

    def analyze(self) -> Dict[str, Any]:
        """
        Analiza la presencia y configuración de Optional Content Groups.
        Returns: Dict con análisis detallado de OCG
        """
        result = {
            "has_ocg": False,
            "confidence": 0.0,
            "ocg_count": 0,                 # hits totales (señales OCG)
            "patterns_found": [],
            "details": {}
        }

        # 1) Escaneo por patrones (compatibilidad con tu pipeline)
        patterns = getattr(LayerPatterns, "OCG_PATTERNS", [
            re.compile(rb"/OCProperties\b"),
            re.compile(rb"/OCGs\b"),
            re.compile(rb"/OC\b"),
            re.compile(rb"/OCMD\b"),
            re.compile(rb"/D\s*<<.*?/OFF\s*\[.*?\].*?>>", re.DOTALL),  # config de estado OFF en diccionario
        ])

        ocg_count = 0
        patterns_found = []
        for pattern in patterns:
            hits = self._find_unique(pattern, self.sample)
            count = len(hits)
            if count > 0:
                ocg_count += count
                pat_name = self._pattern_bytes(pattern).decode("latin1", "ignore")
                patterns_found.append({
                    "pattern": pat_name,
                    "count": count,
                    "samples": [snip.decode("latin1", "ignore", errors="ignore") for _, _, snip in hits[:3]]
                })

        # 2) (Opcional) Análisis estructural con PyMuPDF: catalog y streams por página
        ocg_pages = 0
        total_pages = 0
        pages_with_hits: List[int] = []
        per_page_hits: List[Dict[str, Any]] = []
        catalog_flags = {"has_OCProperties": False, "catalog_hits": 0}

        if fitz is not None:
            try:
                doc = fitz.open(stream=self.pdf_bytes, filetype="pdf")
                total_pages = len(doc)

                # 2.a Catalog: /OCProperties, /OCGs, etc.
                try:
                    cat_str = doc.xref_object(doc.pdf_catalog_xref) if hasattr(doc, "pdf_catalog_xref") else doc.pdf_catalog()
                    cat_txt = str(cat_str)
                    cat_hits = len(re.findall(r"/OC(?:Properties|Gs|MD)\b", cat_txt))
                    catalog_flags["catalog_hits"] = cat_hits
                    catalog_flags["has_OCProperties"] = "/OCProperties" in cat_txt
                    ocg_count += cat_hits  # señal adicional
                except Exception:
                    pass

                # 2.b Streams por página: buscar OC/OCMD en cada stream
                token_re = re.compile(rb"/OC(?:MD)?\b", re.I)
                for pno in range(total_pages):
                    page = doc.load_page(pno)
                    # Contents puede ser array de referencias o un stream; extrae los bytes de cada stream
                    page_hits = 0
                    try:
                        t, v = doc.xref_get_key(page.xref, "Contents")
                        streams = []
                        if t == "array":
                            for ref in re.findall(r"(\d+)\s+0\s+R", v or ""):
                                ref_i = int(ref)
                                bs = doc.xref_stream(ref_i) or b""
                                streams.append(bs)
                        elif t == "stream":
                            bs = doc.xref_stream(page.xref) or b""
                            streams.append(bs)
                        else:
                            streams = []
                        # cuenta hits únicos por stream
                        for bs in streams:
                            hits = self._find_unique(token_re, bs)
                            page_hits += len(hits)
                    except Exception:
                        pass

                    if page_hits > 0:
                        ocg_pages += 1
                        pages_with_hits.append(pno + 1)
                    if page_hits > 0:
                        per_page_hits.append({"page": pno + 1, "hits": page_hits})
                    else:
                        per_page_hits.append({"page": pno + 1, "hits": 0})

            except Exception:
                # si falla, seguimos solo con el escaneo por bytes
                total_pages = 0

        # 3) Métricas derivadas (densidad y cobertura)
        ocg_density = ocg_count / self._bytes_per_mb(self.sample_size)   # señales por MB
        coverage = (ocg_pages / total_pages) if total_pages else 0.0     # 0..1

        # 4) Confianza con suavizado y contexto (mejor que escalones)
        confidence = self._ocg_confidence_smooth(ocg_count, coverage, ocg_density)

        result.update({
            "has_ocg": (ocg_count > 0),
            "confidence": confidence,
            "ocg_count": ocg_count,
            "patterns_found": patterns_found,
            "details": {
                "total_patterns": len(patterns),
                "patterns_detected": len(patterns_found),
                "ocg_density_per_mb": round(ocg_density, 3),
                "pages_with_ocg": pages_with_hits,
                "ocg_pages": ocg_pages,
                "total_pages": total_pages,
                "per_page_hits": per_page_hits,
                "catalog": catalog_flags,
                "sampled_bytes": self.sample_size
            }
        })
        return result

    # ------------------------ scoring mejorado ------------------------

    def _ocg_confidence_smooth(self, ocg_count: int, coverage: float, density: float) -> float:
        """
        Confianza 0..1 basada en:
          - ocg_count (cap 12)
          - coverage (páginas con OCG / total)
          - density (señales OCG por MB)
        Curva logística (suave) + tope 0.95. Evita “saltos”.
        """
        ocg_count = max(0, ocg_count)
        coverage = max(0.0, min(1.0, coverage))
        # normaliza densidad (cap 20 señales/MB -> 1.0)
        dens_norm = max(0.0, min(1.0, density / 20.0))
        capped = min(ocg_count, 12)

        # mezcla de señales
        raw = 0.7 * (capped / 12.0) + 0.2 * coverage + 0.1 * dens_norm
        # logística centrada en ~0.35 con pendiente marcada
        p = self._sigmoid(8.0 * (raw - 0.35))
        base = 0.0 if ocg_count == 0 else 0.05  # piso si hay al menos una señal
        return min(0.95, base + 0.85 * p)


import re, math
from typing import Any, Dict, List, Tuple

class OverlayAnalyzer:
    """Analizador especializado para objetos superpuestos y transparencias."""

    def __init__(self, pdf_bytes: bytes):
        self.pdf_bytes = pdf_bytes
        self.sample_size = min(8_000_000, len(pdf_bytes))
        self.sample = pdf_bytes[:self.sample_size]

    # ───────────── helpers internos (anti FP/FN) ─────────────

    @staticmethod
    def _pattern_bytes(p) -> bytes:
        if hasattr(p, "pattern"):
            pat = p.pattern
            return pat if isinstance(pat, (bytes, bytearray)) else pat.encode("latin1", "ignore")
        return p if isinstance(p, (bytes, bytearray)) else bytes(p)

    @staticmethod
    def _find_unique(pattern, data: bytes) -> List[Tuple[int, int]]:
        """Rangos únicos (start, end) para no contar dos veces el mismo match."""
        pat = pattern if hasattr(pattern, "finditer") else re.compile(pattern)
        hits = [(m.start(), m.end()) for m in pat.finditer(data)]
        return list(dict.fromkeys(hits))

    @staticmethod
    def _split_streams(sample: bytes) -> List[bytes]:
        """Separa 'stream ... endstream' sin descomprimir filtros."""
        chunks = []
        for m in re.finditer(rb"stream\s*[\r\n]+(.*?)\s*endstream", sample, re.DOTALL):
            chunks.append(m.group(1))
        return chunks or [sample]

    @staticmethod
    def _alpha_values(sample: bytes) -> List[float]:
        vals: List[float] = []
        for m in re.finditer(rb"/CA\s+([\d.]+)", sample):
            try: vals.append(float(m.group(1)))
            except: pass
        for m in re.finditer(rb"/ca\s+([\d.]+)", sample):
            try: vals.append(float(m.group(1)))
            except: pass
        return vals

    @staticmethod
    def _blend_modes(sample: bytes) -> List[str]:
        return [bm.decode("latin1", "ignore")
                for bm in re.findall(rb"/BM\s*/(\w+)", sample)[:20]]

    @staticmethod
    def _non_normal_bm_ratio(modes: List[str]) -> float:
        if not modes: return 0.0
        non_normal = [m for m in modes if m.lower() not in ("normal",)]
        return len(non_normal) / max(1, len(modes))

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    @staticmethod
    def _risk_level(p: float) -> str:
        return "HIGH" if p >= 0.75 else ("MEDIUM" if p >= 0.5 else "LOW")

    # ───────────── implementación robusta ─────────────

    def analyze(self) -> Dict[str, Any]:
        """
        Analiza objetos superpuestos, transparencias y efectos visuales.
        Returns:
            Dict con análisis detallado y score anti FP/FN
        """
        result = {
            "has_overlays": False,
            "overlay_count": 0,
            "transparency_count": 0,   # solo alpha < 1.0
            "blend_modes": [],
            "alpha_values": [],
            "suspicious_operators": 0,
            "content_streams": 0,
            "overlay_score": 0.0,
            "probability": 0.0,
            "risk_level": "LOW",
            "confidence": 0.0,
            "details": {}
        }

        sample: bytes = self.sample

        # ---- Config: patrones (usa tus LayerPatterns si están disponibles) ----
        OVERLAY_PATTERNS = getattr(
            globals().get("LayerPatterns", object), "OVERLAY_PATTERNS",
            # fallback genérico (tokens típicos de overlay/estado gráfico)
            [
                re.compile(rb"/ExtGState\b"),
                re.compile(rb"/Transparency\b"),
                re.compile(rb"/SMask\b"),
                re.compile(rb"/OC\b"),        # puede solaparse con OCG (otra clase)
                re.compile(rb"/GS\d+\b"),     # recursos de gráfico
            ]
        )
        SUSPICIOUS_OPERATORS = getattr(
            globals().get("LayerPatterns", object), "SUSPICIOUS_OPERATORS",
            # operadores de composición/pintado frecuentes en “parches”
            [
                re.compile(rb"\bg[s]\b"),     # set graphics state
                re.compile(rb"\bq\b"),        # save state
                re.compile(rb"\bQ\b"),        # restore state
                re.compile(rb"\bcm\b"),       # transform
                re.compile(rb"\bDo\b"),       # draw XObject (imágenes/objetos)
                re.compile(rb"\bBI\b"),       # inline image
                re.compile(rb"\bEI\b"),       # end inline image
            ]
        )

        # ---- Partir por streams para métricas más fiables ----
        streams = self._split_streams(sample)
        result["content_streams"] = len(streams)

        # ---- Overlays: contar coincidencias únicas globales ----
        overlay_count = 0
        for pat in OVERLAY_PATTERNS:
            overlay_count += len(self._find_unique(pat, sample))

        # ---- Alpha/Transparencia real ----
        alpha_vals = self._alpha_values(sample)
        alpha_lt_1 = [a for a in alpha_vals if a < 1.0]

        # ---- Blend modes ----
        modes = self._blend_modes(sample)
        bm_ratio = self._non_normal_bm_ratio(modes)

        # ---- Operadores sospechosos (de-dup) ----
        suspicious_ops = 0
        operator_details = []
        for pat in SUSPICIOUS_OPERATORS:
            cnt = len(self._find_unique(pat, sample))
            suspicious_ops += cnt
            if cnt:
                operator_details.append({
                    "operator": self._pattern_bytes(pat).decode("latin1", "ignore"),
                    "count": cnt
                })

        # ---- Normalizaciones para score ----
        overlays_norm = min(1.0, overlay_count / 20.0)  # cap suave
        alpha_any     = 1.0 if alpha_lt_1 else 0.0
        alpha_density = min(1.0, len(alpha_lt_1) / max(1, len(alpha_vals)))  # proporción real <1
        ops_norm      = min(1.0, suspicious_ops / 50.0)
        streams_norm  = min(1.0, len(streams) / 12.0)

        # ---- Score logístico (pesos conservadores; calibra con tu dataset) ----
        x = -2.0
        x += 2.0 * overlays_norm
        x += 1.3 * alpha_any
        x += 0.8 * alpha_density
        x += 0.9 * bm_ratio
        x += 0.7 * ops_norm
        x += 0.3 * streams_norm
        p = self._sigmoid(x)

        # Confianza: más alta con señales fuertes y consistentes
        strong = (alpha_any + (1 if bm_ratio > 0 else 0) + (1 if overlays_norm > 0.4 else 0))
        consistency = 0.5 * alpha_density + 0.5 * min(1.0, overlays_norm * 1.5)
        confidence = max(0.35, min(0.95, 0.40 + 0.18*strong + 0.25*consistency))

        # Señal binaria “has_overlays” más robusta que un simple >3
        has_overlays = (overlay_count > 3) or bool(alpha_lt_1) or (bm_ratio >= 0.2)

        result.update({
            "has_overlays": has_overlays,
            "overlay_count": overlay_count,
            "transparency_count": len(alpha_lt_1),
            "blend_modes": modes,
            "alpha_values": alpha_vals[:50],   # limita salida
            "suspicious_operators": suspicious_ops,
            "overlay_score": overlays_norm if overlay_count > 3 else 0.0,
            "probability": round(p, 4),
            "risk_level": self._risk_level(p),
            "confidence": round(confidence, 3),
            "details": {
                "operator_details": operator_details,
                "transparency_density": round(alpha_density, 3),
                "bm_non_normal_ratio": round(bm_ratio, 3),
                "streams_norm": round(streams_norm, 3),
                "per_stream": [
                    {
                        "index": i+1,
                        "alpha_count": len(self._alpha_values(s)),
                        "bm_found": self._blend_modes(s)[:5],
                        "length_bytes": len(s)
                    } for i, s in enumerate(streams[:20])
                ],
                "alpha_range": {
                    "min": (min(alpha_vals) if alpha_vals else 0.0),
                    "max": (max(alpha_vals) if alpha_vals else 0.0),
                    "avg": (sum(alpha_vals)/len(alpha_vals) if alpha_vals else 0.0)
                }
            }
        })
        return result


class TextOverlapAnalyzer:
    """Analizador especializado para superposición de texto."""
    
    def __init__(self, extracted_text: str):
        self.extracted_text = extracted_text or ""
        self.lines = [line.strip() for line in self.extracted_text.split('\n') if line.strip()]
    
    def analyze(self) -> Dict[str, Any]:
        """
        Analiza superposición y duplicación de texto.
        
        Returns:
            Dict con análisis detallado de texto
        """
        result = {
            "has_overlapping": False,
            "overlapping_probability": 0.0,
            "duplicate_lines": {},
            "similar_lines": [],
            "suspicious_formatting": [],
            "details": {}
        }
        
        if not self.extracted_text:
            return result
        
        # Análisis de líneas duplicadas
        duplicate_lines = self._analyze_duplicate_lines()
        
        # Análisis de líneas similares
        similar_lines = self._analyze_similar_lines()
        
        # Análisis de formato sospechoso
        suspicious_formatting = self._analyze_suspicious_formatting()
        
        # Calcular probabilidad de superposición
        overlapping_probability = self._calculate_overlapping_probability(
            duplicate_lines, similar_lines, suspicious_formatting
        )
        
        result.update({
            "has_overlapping": overlapping_probability > 0.3,
            "overlapping_probability": overlapping_probability,
            "duplicate_lines": duplicate_lines,
            "similar_lines": similar_lines,
            "suspicious_formatting": suspicious_formatting,
            "details": {
                "total_lines": len(self.lines),
                "unique_lines": len(set(self.lines)),
                "duplication_ratio": 1 - (len(set(self.lines)) / max(1, len(self.lines))),
                "avg_line_length": sum(len(line) for line in self.lines) / max(1, len(self.lines))
            }
        })
        
        return result
    
    def _analyze_duplicate_lines(self) -> Dict[str, int]:
        """Detecta líneas duplicadas exactas."""
        line_counts = Counter(self.lines)
        return {line: count for line, count in line_counts.items() if count > 1}
    
    def _analyze_similar_lines(self) -> List[Tuple[str, str, float]]:
        """Detecta líneas similares con alta coincidencia."""
        similar_pairs = []
        
        for i, line1 in enumerate(self.lines):
            for j, line2 in enumerate(self.lines[i+1:], i+1):
                similarity = SequenceMatcher(None, line1, line2).ratio()
                if 0.7 <= similarity < 1.0:  # Muy similar pero no idéntica
                    similar_pairs.append((line1, line2, similarity))
        
        return similar_pairs[:10]  # Limitar a 10 pares más relevantes
    
    def _analyze_suspicious_formatting(self) -> List[str]:
        """Detecta patrones de formato sospechosos."""
        suspicious = []
        
        # Detectar espaciado inusual
        unusual_spacing = [line for line in self.lines if re.search(r'\s{10,}', line)]
        if unusual_spacing:
            suspicious.append(f"Espaciado inusual en {len(unusual_spacing)} líneas")
        
        # Detectar caracteres de control
        control_chars = [line for line in self.lines if re.search(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', line)]
        if control_chars:
            suspicious.append(f"Caracteres de control en {len(control_chars)} líneas")
        
        # Detectar texto muy corto repetido
        short_repeated = [line for line in self.lines if len(line) <= 3 and self.lines.count(line) > 5]
        if short_repeated:
            suspicious.append(f"Texto muy corto repetido: {set(short_repeated)}")
        
        return suspicious
    
    def _calculate_overlapping_probability(self, duplicates: Dict, similar: List, suspicious: List) -> float:
        """Calcula probabilidad de superposición basada en evidencias."""
        score = 0.0
        
        # Peso por duplicados
        if duplicates:
            duplicate_ratio = len(duplicates) / max(1, len(self.lines))
            score += min(0.6, duplicate_ratio * 2)  # Máximo 60% por duplicados
        
        # Peso por similares
        if similar:
            similar_ratio = len(similar) / max(1, len(self.lines))
            score += min(0.3, similar_ratio * 5)  # Máximo 30% por similares
        
        # Peso por formato sospechoso
        if suspicious:
            score += min(0.1, len(suspicious) * 0.05)  # Máximo 10% por formato
        
        return min(1.0, score)


class StructureAnalyzer:
    """Analizador especializado para estructura PDF sospechosa."""
    
    def __init__(self, doc: fitz.Document):
        self.doc = doc
    
    def analyze(self) -> Dict[str, Any]:
        """
        Analiza la estructura interna del PDF para detectar anomalías.
        
        Returns:
            Dict con análisis estructural
        """
        result = {
            "suspicious_structure": False,
            "structure_score": 0.0,
            "details": [],
            "object_analysis": {},
            "page_analysis": []
        }
        
        try:
            # Análisis por página
            page_analysis = []
            total_objects = 0
            overlapping_blocks_total = 0
            
            for page_num in range(self.doc.page_count):
                page = self.doc.load_page(page_num)
                page_info = self._analyze_page_structure(page, page_num)
                page_analysis.append(page_info)
                
                total_objects += page_info["object_count"]
                overlapping_blocks_total += page_info["overlapping_blocks"]
            
            # Análisis global
            objects_per_page = total_objects / max(1, self.doc.page_count)
            
            # Determinar si la estructura es sospechosa
            suspicious_indicators = []
            
            if objects_per_page > 50:
                suspicious_indicators.append(f"Exceso de objetos por página: {objects_per_page:.1f}")
            
            if overlapping_blocks_total > 5:
                suspicious_indicators.append(f"Múltiples bloques superpuestos: {overlapping_blocks_total}")
            
            # Calcular score estructural
            structure_score = min(1.0, (objects_per_page / 100) + (overlapping_blocks_total / 10))
            
            result.update({
                "suspicious_structure": len(suspicious_indicators) > 0,
                "structure_score": structure_score,
                "details": suspicious_indicators,
                "object_analysis": {
                    "total_objects": total_objects,
                    "objects_per_page": objects_per_page,
                    "overlapping_blocks_total": overlapping_blocks_total
                },
                "page_analysis": page_analysis
            })
            
        except Exception as e:
            result["details"].append(f"Error en análisis estructural: {str(e)}")
        
        return result
    
    def _analyze_page_structure(self, page: fitz.Page, page_num: int) -> Dict[str, Any]:
        """Analiza la estructura de una página específica."""
        page_info = {
            "page_number": page_num + 1,
            "object_count": 0,
            "overlapping_blocks": 0,
            "drawings": 0,
            "images": 0,
            "text_blocks": 0
        }
        
        try:
            # Contar objetos por tipo
            drawings = page.get_drawings()
            images = page.get_images()
            text_dict = page.get_text("dict")
            
            page_info["drawings"] = len(drawings)
            page_info["images"] = len(images)
            page_info["text_blocks"] = len(text_dict.get('blocks', []))
            page_info["object_count"] = sum([page_info["drawings"], page_info["images"], page_info["text_blocks"]])
            
            # Analizar superposiciones de bloques de texto
            blocks = text_dict.get('blocks', [])
            overlapping_count = 0
            
            for i, block1 in enumerate(blocks):
                if block1.get('type') != 0:  # Solo bloques de texto
                    continue
                bbox1 = block1.get('bbox')
                if not bbox1:
                    continue
                
                for j, block2 in enumerate(blocks[i+1:], i+1):
                    if block2.get('type') != 0:
                        continue
                    bbox2 = block2.get('bbox')
                    if not bbox2:
                        continue
                    
                    # Verificar superposición de bounding boxes
                    if (bbox1[0] < bbox2[2] and bbox1[2] > bbox2[0] and 
                        bbox1[1] < bbox2[3] and bbox1[3] > bbox2[1]):
                        overlapping_count += 1
            
            page_info["overlapping_blocks"] = overlapping_count
            
        except Exception as e:
            page_info["error"] = str(e)
        
        return page_info


class RiskCalculator:
    """Calculadora de riesgo dinámico para capas múltiples."""
    
    def __init__(self, base_weight: int = None):
        self.base_weight = base_weight or RiskWeights.BASE_WEIGHT
        self.component_weights = RiskWeights.COMPONENT_WEIGHTS
        self.risk_thresholds = RiskWeights.RISK_THRESHOLDS
        self.risk_multipliers = RiskWeights.RISK_MULTIPLIERS
    
    def calculate_risk_score(self, 
                           ocg_analysis: Dict[str, Any],
                           overlay_analysis: Dict[str, Any],
                           text_analysis: Dict[str, Any],
                           structure_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula el score de riesgo basado en todos los componentes de análisis.
        
        Args:
            ocg_analysis: Resultado del análisis OCG
            overlay_analysis: Resultado del análisis de overlays
            text_analysis: Resultado del análisis de texto
            structure_analysis: Resultado del análisis estructural
            
        Returns:
            Dict con score, nivel de riesgo y desglose detallado
        """
        score = 0.0
        score_breakdown = {}
        
        # Componente OCG (35%)
        if ocg_analysis.get("has_ocg", False):
            ocg_contribution = ocg_analysis["confidence"] * self.component_weights["ocg_confidence"]
            score += ocg_contribution
            score_breakdown["ocg_contribution"] = round(ocg_contribution, 3)
        
        # Componente Overlay (25%)
        if overlay_analysis.get("has_overlays", False):
            overlay_score = overlay_analysis.get("overlay_score", 0.0)
            overlay_contribution = overlay_score * self.component_weights["overlay_presence"]
            score += overlay_contribution
            score_breakdown["overlay_contribution"] = round(overlay_contribution, 3)
        
        # Componente Texto (25%)
        text_score = text_analysis.get("overlapping_probability", 0.0)
        if text_score > 0:
            text_contribution = text_score * self.component_weights["text_overlapping"]
            score += text_contribution
            score_breakdown["text_contribution"] = round(text_contribution, 3)
        
        # Componente Estructura (15%)
        if structure_analysis.get("suspicious_structure", False):
            struct_score = structure_analysis.get("structure_score", 0.8)
            structure_contribution = struct_score * self.component_weights["structure_suspicious"]
            score += structure_contribution
            score_breakdown["structure_contribution"] = round(structure_contribution, 3)
        
        # Determinar nivel de riesgo y confianza
        risk_level = self._determine_risk_level(score)
        confidence = min(1.0, score + 0.1)
        probability_percentage = round(score * 100, 1)
        
        # Calcular penalización dinámica
        penalty_points = self._calculate_dynamic_penalty(score, risk_level)
        
        return {
            "score": round(score, 3),
            "probability_percentage": probability_percentage,
            "risk_level": risk_level,
            "confidence": round(confidence, 3),
            "penalty_points": penalty_points,
            "score_breakdown": score_breakdown,
            "weights_used": self.component_weights,
            "calculation_method": "dynamic_weighted"
        }
    
    def _determine_risk_level(self, score: float) -> str:
        """Determina el nivel de riesgo basado en el score."""
        if score >= self.risk_thresholds["VERY_HIGH"]:
            return "VERY_HIGH"
        elif score >= self.risk_thresholds["HIGH"]:
            return "HIGH"
        elif score >= self.risk_thresholds["MEDIUM"]:
            return "MEDIUM"
        elif score >= self.risk_thresholds["LOW"]:
            return "LOW"
        else:
            return "VERY_LOW"
    
    def _calculate_dynamic_penalty(self, score: float, risk_level: str) -> int:
        """Calcula penalización dinámica basada en el método recomendado."""
        # Método 1: Penalización proporcional
        proportional_penalty = round(score * self.base_weight)
        
        # Método 2: Penalización escalonada
        multiplier = self.risk_multipliers.get(risk_level, 0.2)
        scaled_penalty = round(self.base_weight * multiplier)
        
        # Usar el mayor de los dos métodos para ser más estricto
        return max(proportional_penalty, scaled_penalty)


class LayerDetector:
    """Clase principal para detección avanzada de capas múltiples."""
    
    def __init__(self, pdf_bytes: bytes, extracted_text: str = "", base_weight: int = None):
        self.pdf_bytes = pdf_bytes
        self.extracted_text = extracted_text
        self.base_weight = base_weight or RiskWeights.BASE_WEIGHT
        
        # Inicializar analizadores
        self.ocg_analyzer = OCGAnalyzer(pdf_bytes)
        self.overlay_analyzer = OverlayAnalyzer(pdf_bytes)
        self.text_analyzer = TextOverlapAnalyzer(extracted_text)
        self.risk_calculator = RiskCalculator(base_weight)
        
        # Para análisis estructural necesitamos el documento
        self.doc = None
        self.structure_analyzer = None
    
    def analyze(self) -> Dict[str, Any]:
        """
        Ejecuta análisis completo de capas múltiples.
        
        Returns:
            Dict con análisis completo y detallado
        """
        try:
            # Abrir documento para análisis estructural
            self.doc = fitz.open(stream=self.pdf_bytes, filetype="pdf")
            self.structure_analyzer = StructureAnalyzer(self.doc)
            
            # Ejecutar todos los análisis
            ocg_analysis = self.ocg_analyzer.analyze()
            overlay_analysis = self.overlay_analyzer.analyze()
            text_analysis = self.text_analyzer.analyze()
            structure_analysis = self.structure_analyzer.analyze()
            
            # Calcular riesgo final
            risk_result = self.risk_calculator.calculate_risk_score(
                ocg_analysis, overlay_analysis, text_analysis, structure_analysis
            )
            
            # Generar indicadores
            indicators = self._generate_indicators(
                ocg_analysis, overlay_analysis, text_analysis, structure_analysis
            )
            
            # Estimar número de capas
            layer_estimate = self._estimate_layer_count(ocg_analysis, overlay_analysis)
            
            # Construir resultado final
            result = {
                "has_layers": risk_result["risk_level"] != "VERY_LOW",
                "confidence": risk_result["confidence"],
                "probability_percentage": risk_result["probability_percentage"],
                "risk_level": risk_result["risk_level"],
                "penalty_points": risk_result["penalty_points"],
                "indicators": indicators,
                "layer_count_estimate": layer_estimate,
                
                # Datos técnicos detallados
                "ocg_objects": ocg_analysis["ocg_count"],
                "overlay_objects": overlay_analysis["overlay_count"],
                "transparency_objects": overlay_analysis["transparency_count"],
                "suspicious_operators": overlay_analysis["suspicious_operators"],
                "content_streams": overlay_analysis["content_streams"],
                "blend_modes": overlay_analysis["blend_modes"],
                "alpha_values": overlay_analysis["alpha_values"],
                
                # Desglose y análisis detallado
                "score_breakdown": risk_result["score_breakdown"],
                "weights_used": risk_result["weights_used"],
                "detailed_analysis": {
                    "ocg_patterns_found": ocg_analysis["patterns_found"],
                    "operator_details": overlay_analysis["details"]["operator_details"],
                    "transparency_analysis": {
                        "alpha_values": overlay_analysis["alpha_values"],
                        "blend_modes": overlay_analysis["blend_modes"],
                        "transparency_objects": overlay_analysis["transparency_count"],
                        "alpha_range": overlay_analysis["details"]["alpha_range"]
                    },
                    "text_overlap_analysis": {
                        "duplicate_lines": text_analysis["duplicate_lines"],
                        "similar_lines": text_analysis["similar_lines"],
                        "suspicious_formatting": text_analysis["suspicious_formatting"]
                    },
                    "structure_analysis": structure_analysis
                }
            }
            
            return result
            
        except Exception as e:
            return {
                "has_layers": False,
                "confidence": 0.0,
                "probability_percentage": 0.0,
                "risk_level": "VERY_LOW",
                "penalty_points": 0,
                "error": f"Error en análisis de capas: {str(e)}",
                "indicators": [],
                "layer_count_estimate": 0,
                "ocg_objects": 0,
                "overlay_objects": 0,
                "transparency_objects": 0,
                "suspicious_operators": 0,
                "content_streams": 0,
                "blend_modes": [],
                "alpha_values": [],
                "score_breakdown": {},
                "weights_used": RiskWeights.COMPONENT_WEIGHTS,
                "detailed_analysis": {}
            }
        finally:
            if self.doc:
                self.doc.close()
    
    def _generate_indicators(self, ocg_analysis: Dict, overlay_analysis: Dict, 
                           text_analysis: Dict, structure_analysis: Dict) -> List[str]:
        """Genera lista de indicadores detectados."""
        indicators = []
        
        # Indicadores OCG
        if ocg_analysis["has_ocg"]:
            indicators.append(f"Objetos OCG detectados: {ocg_analysis['ocg_count']}")
        
        # Indicadores de overlay
        if overlay_analysis["has_overlays"]:
            indicators.append(f"Objetos superpuestos: {overlay_analysis['overlay_count']}")
        
        if overlay_analysis["content_streams"] > 5:
            indicators.append(f"Múltiples content streams: {overlay_analysis['content_streams']}")
        
        if overlay_analysis["suspicious_operators"] > 20:
            indicators.append(f"Operadores sospechosos: {overlay_analysis['suspicious_operators']}")
        
        # Indicadores de texto
        if text_analysis["has_overlapping"]:
            prob = text_analysis["overlapping_probability"]
            indicators.append(f"Superposición de texto: {prob:.1%}")
        
        # Indicadores estructurales
        if structure_analysis["suspicious_structure"]:
            indicators.append("Estructura PDF sospechosa")
        
        return indicators
    
    def _estimate_layer_count(self, ocg_analysis: Dict, overlay_analysis: Dict) -> int:
        """Estima el número de capas basado en los análisis."""
        if ocg_analysis["ocg_count"] > 0:
            return min(ocg_analysis["ocg_count"] // 2, 10)
        elif overlay_analysis["overlay_count"] > 10:
            return min(overlay_analysis["overlay_count"] // 5, 8)
        else:
            return 0


# Funciones de conveniencia para compatibilidad con código existente

def detect_layers_advanced(pdf_bytes: bytes, extracted_text: str = "") -> Dict[str, Any]:
    """
    Función de conveniencia para mantener compatibilidad con código existente.
    
    Args:
        pdf_bytes: Contenido del PDF en bytes
        extracted_text: Texto extraído del PDF
        
    Returns:
        Dict con análisis completo de capas múltiples
    """
    detector = LayerDetector(pdf_bytes, extracted_text)
    return detector.analyze()


def calculate_dynamic_penalty(probability_percentage: float, base_weight: int = 15) -> int:
    """
    Calcula penalización dinámica basada en el porcentaje de probabilidad.
    
    Args:
        probability_percentage: Porcentaje de probabilidad de capas (0-100)
        base_weight: Peso base para el cálculo
        
    Returns:
        Puntos de penalización
    """
    score = probability_percentage / 100.0
    calculator = RiskCalculator(base_weight)
    risk_level = calculator._determine_risk_level(score)
    return calculator._calculate_dynamic_penalty(score, risk_level)
