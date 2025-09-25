"""
Helper para análisis de consistencia de fuentes.

Analiza las fuentes tipográficas extraídas por OCR y determina la consistencia.
"""

import re
import math
from typing import Dict, Any, List, Optional
from collections import Counter
from domain.entities.forensic_ocr_details import AnalisisFuentes, FuenteDetectada, Palabra

# --- Helpers de normalización ---

_ALIAS_STANDARD = {
    "times new roman": "times",
    "times-roman": "times",
    "timesnewroman": "times",
    "arialmt": "arial",
    "arial unicode ms": "arial",
    "helvetica neue": "helvetica",
    "helveticaneue": "helvetica",
    "segoe ui variable": "segoe ui",
    "trebuchetms": "trebuchet ms",
    "couriernew": "courier new",
    "bookantiqua": "book antiqua",
    "centuryschoolbook": "century schoolbook",
}

_STANDARD_WHITELIST = {
    s.lower(): s for s in [
        "Arial", "Helvetica", "Times New Roman", "Times", "Courier New", "Courier",
        "Calibri", "Verdana", "Tahoma", "Georgia", "Palatino", "Garamond",
        "Book Antiqua", "Century Schoolbook", "Lucida Console", "Monaco",
        "Trebuchet MS", "Arial Black", "Impact", "Comic Sans MS", "Cambria", "Segoe UI"
    ]
}

_BLACKLIST_EXACT = {"wingdings", "webdings", "symbol", "marlett", "mt extra"}
_SUSPICIOUS_PATTERNS = re.compile(
    r"(crack|hack|pirat|illegal|stolen|fake|clone|copy|mod|cracked|hacked|proprietary|generated|auto)",
    re.IGNORECASE
)

def _normalize_family(name: str) -> str:
    n = (name or "").strip().lower()
    # quitar sufijos comunes
    n = re.sub(r"[-\s]?(bold|italic|oblique|regular|medium|light|semibold|black|mt|psmt)$", "", n)
    n = n.replace("-", " ").replace("_", " ")
    n = re.sub(r"\s+", " ", n).strip()
    # alias -> base
    n = _ALIAS_STANDARD.get(n, n)
    return n

def _normalize_style(style: Optional[str]) -> str:
    s = (style or "").lower()
    if "italic" in s or "oblique" in s:
        return "italic"
    return "normal"

def _normalize_weight(weight: Optional[str]) -> str:
    w = (str(weight or "")).lower()
    if w.isdigit():
        val = int(w)
        return "bold" if val >= 600 else "normal"
    if "bold" in w:
        return "bold"
    return "normal"


class FontAnalyzer:
    """Analizador de consistencia de fuentes"""
    
    def __init__(self):
        pass
    
    def analyze_font_consistency(self, palabras: List[Palabra]) -> AnalisisFuentes:
        """
        Analiza la consistencia de fuentes en una lista de palabras.
        
        Args:
            palabras: Lista de palabras extraídas por OCR
            
        Returns:
            AnalisisFuentes: Análisis completo de consistencia de fuentes
        """
        if not palabras:
            return self._create_empty_analysis()
        
        # Extraer información de fuentes de las palabras
        font_data = self._extract_font_data(palabras)
        
        # Agrupar fuentes por características
        font_groups = self._group_fonts(font_data)
        
        # Calcular métricas de consistencia
        total_fuentes = len(font_data)
        fuentes_unicas = len(font_groups)
        indice_diversidad = self._calculate_diversity_index(font_groups)
        
        # Detectar fuentes sospechosas
        fuentes_sospechosas = self._detect_suspicious_fonts(font_groups)
        
        # Calcular score de consistencia
        consistencia_score = self._calculate_consistency_score(
            font_groups, total_fuentes, fuentes_unicas, indice_diversidad
        )
        
        # Crear lista de fuentes detectadas
        fuentes_detectadas = self._create_font_detected_list(font_groups, total_fuentes)
        
        return AnalisisFuentes(
            fuentes_detectadas=fuentes_detectadas,
            total_fuentes=total_fuentes,
            fuentes_unicas=fuentes_unicas,
            indice_diversidad=indice_diversidad,
            fuentes_sospechosas=fuentes_sospechosas,
            consistencia_score=consistencia_score
        )
    
    def _extract_font_data(self, palabras: List[Palabra]) -> List[Dict[str, Any]]:
        """Extrae datos de fuentes de las palabras con normalización"""
        font_data = []
        
        for p in palabras:
            if not getattr(p, "font_family", None):
                continue
            family_norm = _normalize_family(p.font_family)
            if not family_norm:
                continue
            size = float(getattr(p, "font_size", 0.0) or 0.0)
            style = _normalize_style(getattr(p, "font_style", None))
            weight = _normalize_weight(getattr(p, "font_weight", None))
            conf = float(getattr(p, "confidence", 0.0) or 0.0)
            
            # Filtrar fuentes con tamaño irreal o confianza muy baja
            if size < 5.0 or size > 72.0 or conf < 0.3:
                continue
                
            font_data.append({
                "font_family_raw": p.font_family,
                "font_family": family_norm,
                "font_size": size,
                "font_style": style,
                "font_weight": weight,
                "confidence": conf,
                "texto": getattr(p, "texto", "")
            })
        
        return font_data
    
    def _group_fonts(self, font_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Agrupa fuentes por características similares con bucketing de tamaño"""
        groups = {}
        
        for d in font_data:
            # bucket de 0.5 pt para evitar explosión de grupos
            size_bucket = round(d["font_size"] * 2) / 2.0
            key = f"{d['font_family']}|{size_bucket:.1f}|{d['font_style']}|{d['font_weight']}"
            
            g = groups.get(key)
            if not g:
                g = groups[key] = {
                    "font_family": d["font_family"],
                    "font_family_raw": set(),
                    "font_size": size_bucket,
                    "font_style": d["font_style"],
                    "font_weight": d["font_weight"],
                    "count": 0,
                    "confidence_sum": 0.0,
                    "textos": []
                }
            
            g["count"] += 1
            g["confidence_sum"] += d["confidence"]
            g["textos"].append(d["texto"])
            g["font_family_raw"].add(d["font_family_raw"])
        
        return groups
    
    def _calculate_diversity_index(self, font_groups: Dict[str, Dict[str, Any]]) -> float:
        """Calcula el índice de diversidad de fuentes usando Shannon normalizado (0-1)"""
        if not font_groups:
            return 0.0
        
        total = sum(g["count"] for g in font_groups.values())
        if total == 0:
            return 0.0
        
        ps = [g["count"] / total for g in font_groups.values()]
        H = -sum(p * math.log(p) for p in ps if p > 0)
        Hmax = math.log(len(ps)) if len(ps) > 1 else 1.0
        return min(max(H / Hmax, 0.0), 1.0)
    
    def _detect_suspicious_fonts(self, font_groups: Dict[str, Dict[str, Any]]) -> List[str]:
        """Detecta fuentes sospechosas usando sistema de puntuación"""
        if not font_groups:
            return []

        total = sum(g["count"] for g in font_groups.values())
        msgs = set()

        for g in font_groups.values():
            p = (g["count"] / total) if total else 0.0
            fam = g["font_family"]                       # normalizado
            fam_raws = ", ".join(sorted(g["font_family_raw"]))  # para contexto
            score = 0

            if fam in _BLACKLIST_EXACT:
                score += 2
            if _SUSPICIOUS_PATTERNS.search(fam):
                score += 1

            # lista blanca: coincide con algún estándar (post-normalización)
            whitelisted = any(_normalize_family(k) == fam for k in _STANDARD_WHITELIST.keys())
            if not whitelisted and p < 0.10:
                score += 1

            if score >= 2 and p < 0.20:
                msgs.add(f"Fuente sospechosa: '{fam}' (variantes: {fam_raws}) cobertura {p:.1%}, score {score}")

        return sorted(msgs)
    
    def _calculate_consistency_score(self, font_groups: Dict[str, Dict[str, Any]], 
                                   total_fuentes: int, fuentes_unicas: int, 
                                   indice_diversidad: float) -> float:
        """Calcula el score de consistencia usando Herfindahl-Hirschman y otros factores"""
        if total_fuentes <= 0 or not font_groups:
            return 1.0

        ps = [g["count"] / total_fuentes for g in font_groups.values()]
        hhi = sum(p * p for p in ps)                    # concentración: 1 mono, ~0 distribuido
        shannon_norm = indice_diversidad               # ya normalizado [0,1]
        families_penalty = max(0.0, (fuentes_unicas - 5) / 10.0)  # suave, a partir de 6+
        families_penalty = min(families_penalty, 0.4)

        # mayor es mejor
        score = (
            0.55 * hhi +            # distribución concentrada
            0.30 * (1.0 - shannon_norm) +  # baja diversidad
            0.15 * (1.0 - families_penalty)
        )
        return float(min(max(score, 0.0), 1.0))
    
    def _create_font_detected_list(self, font_groups: Dict[str, Dict[str, Any]], 
                                 total_fuentes: int) -> List[FuenteDetectada]:
        """Crea la lista de fuentes detectadas con información adicional"""
        fuentes_detectadas = []
        
        for group in font_groups.values():
            percentage = (group["count"] / total_fuentes) * 100 if total_fuentes > 0 else 0
            confidence_avg = group["confidence_sum"] / group["count"] if group["count"] > 0 else 0
            
            # Filtrar grupos con muy pocas palabras y baja confianza
            if group["count"] == 1 and confidence_avg < 0.5:
                continue
                
            fuentes_detectadas.append(FuenteDetectada(
                font_family=group["font_family"],
                font_size=group["font_size"],
                font_style=group["font_style"],
                font_weight=group["font_weight"],
                count=group["count"],
                percentage=percentage,
                confidence_avg=confidence_avg
            ))
        
        # Ordenar por frecuencia (más común primero)
        fuentes_detectadas.sort(key=lambda x: x.count, reverse=True)
        
        return fuentes_detectadas
    
    def _create_empty_analysis(self) -> AnalisisFuentes:
        """Crea un análisis vacío cuando no hay datos"""
        return AnalisisFuentes(
            fuentes_detectadas=[],
            total_fuentes=0,
            fuentes_unicas=0,
            indice_diversidad=0.0,
            fuentes_sospechosas=[],
            consistencia_score=1.0  # Sin datos = consistencia perfecta
        )
