"""
Helper para análisis de alineación de texto.

Analiza la alineación correcta de elementos de texto basado en resultados OCR.
"""

import math
import statistics
from typing import Dict, Any, List, Optional, Tuple
from domain.entities.forensic_ocr_details import Palabra, Linea, Bloque, BBox


class AlignmentAnalyzer:
    """Analizador de alineación de texto"""
    
    def __init__(self):
        # Umbrales para detección de alineación
        self.alignment_thresholds = {
            "perfect": 1.0,      # Alineación perfecta
            "good": 3.0,         # Alineación buena
            "acceptable": 5.0,   # Alineación aceptable
            "poor": 10.0,        # Alineación pobre
            "bad": 20.0          # Alineación muy mala
        }
        
        # Tipos de alineación estándar
        self.standard_alignments = ["left", "right", "center", "justify"]
        
        # Umbrales para rotación sospechosa
        self.rotation_thresholds = {
            "slight": 2.0,       # Rotación ligera
            "moderate": 5.0,     # Rotación moderada
            "severe": 15.0,      # Rotación severa
            "extreme": 45.0      # Rotación extrema
        }
    
    def analyze_text_alignment(self, ocr_result: Dict[str, Any], source_type: str) -> Dict[str, Any]:
        """
        Analiza la alineación de texto basado en resultado OCR.
        
        Args:
            ocr_result: Resultado del análisis OCR
            source_type: Tipo de archivo ("pdf" o "image")
            
        Returns:
            Dict con información de alineación y análisis
        """
        try:
            if not ocr_result or not ocr_result.get("success", False):
                return {
                    "error": "No se proporcionó resultado OCR válido",
                    "elementos_analizados": 0,
                    "alineacion_correcta": False
                }
            
            # Extraer elementos de texto del resultado OCR
            palabras = self._extract_words_from_ocr(ocr_result)
            lineas = self._extract_lines_from_ocr(ocr_result)
            bloques = self._extract_blocks_from_ocr(ocr_result)
            
            if not palabras and not lineas and not bloques:
                return {
                    "error": "No se encontraron elementos de texto para analizar",
                    "elementos_analizados": 0,
                    "alineacion_correcta": False
                }
            
            # Analizar alineación de palabras
            word_alignment = self._analyze_word_alignment(palabras)
            
            # Analizar alineación de líneas
            line_alignment = self._analyze_line_alignment(lineas)
            
            # Analizar alineación de bloques
            block_alignment = self._analyze_block_alignment(bloques)
            
            # Combinar análisis
            combined_analysis = self._combine_alignment_analysis(
                word_alignment, line_alignment, block_alignment
            )
            
            # Detectar indicadores sospechosos
            suspicious_indicators = self._detect_suspicious_alignment(
                combined_analysis, palabras, lineas, bloques
            )
            
            return {
                "elementos_analizados": combined_analysis["total_elements"],
                "alineacion_correcta": combined_analysis["is_aligned"],
                "desviacion_promedio": combined_analysis["average_deviation"],
                "alineaciones_detectadas": combined_analysis["detected_alignments"],
                "desviaciones_por_elemento": combined_analysis["deviations_per_element"],
                "elementos_mal_alineados": combined_analysis["misaligned_elements"],
                "suspicious_indicators": suspicious_indicators,
                "word_analysis": word_alignment,
                "line_analysis": line_alignment,
                "block_analysis": block_alignment
            }
            
        except Exception as e:
            return {
                "error": f"Error analizando alineación de texto: {str(e)}",
                "elementos_analizados": 0,
                "alineacion_correcta": False
            }
    
    def _extract_words_from_ocr(self, ocr_result: Dict[str, Any]) -> List[Palabra]:
        """Extrae palabras del resultado OCR"""
        palabras = []
        try:
            if "palabras" in ocr_result:
                for palabra_data in ocr_result["palabras"]:
                    palabra = Palabra(
                        texto=palabra_data.get("texto", ""),
                        confianza=palabra_data.get("confianza", 0.0),
                        bbox=palabra_data.get("bbox", [0, 0, 0, 0]),
                        font_family=palabra_data.get("font_family"),
                        font_size=palabra_data.get("font_size"),
                        font_style=palabra_data.get("font_style"),
                        font_weight=palabra_data.get("font_weight")
                    )
                    palabras.append(palabra)
        except Exception:
            pass
        return palabras
    
    def _extract_lines_from_ocr(self, ocr_result: Dict[str, Any]) -> List[Linea]:
        """Extrae líneas del resultado OCR"""
        lineas = []
        try:
            if "lineas" in ocr_result:
                for linea_data in ocr_result["lineas"]:
                    linea = Linea(
                        texto=linea_data.get("texto", ""),
                        confianza=linea_data.get("confianza", 0.0),
                        bbox=linea_data.get("bbox", [0, 0, 0, 0])
                    )
                    lineas.append(linea)
        except Exception:
            pass
        return lineas
    
    def _extract_blocks_from_ocr(self, ocr_result: Dict[str, Any]) -> List[Bloque]:
        """Extrae bloques del resultado OCR"""
        bloques = []
        try:
            if "bloques" in ocr_result:
                for bloque_data in ocr_result["bloques"]:
                    # Crear BBox desde la lista
                    bbox_data = bloque_data.get("bbox", [0, 0, 0, 0])
                    bbox = BBox(
                        x=bbox_data[0],
                        y=bbox_data[1], 
                        w=bbox_data[2] - bbox_data[0],
                        h=bbox_data[3] - bbox_data[1]
                    )
                    
                    # Extraer líneas del bloque
                    lineas = []
                    for linea_data in bloque_data.get("lineas", []):
                        linea_bbox_data = linea_data.get("bbox", [0, 0, 0, 0])
                        linea_bbox = BBox(
                            x=linea_bbox_data[0],
                            y=linea_bbox_data[1],
                            w=linea_bbox_data[2] - linea_bbox_data[0],
                            h=linea_bbox_data[3] - linea_bbox_data[1]
                        )
                        
                        # Extraer palabras de la línea
                        palabras = []
                        for palabra_data in linea_data.get("palabras", []):
                            palabra_bbox_data = palabra_data.get("bbox", [0, 0, 0, 0])
                            palabra_bbox = BBox(
                                x=palabra_bbox_data[0],
                                y=palabra_bbox_data[1],
                                w=palabra_bbox_data[2] - palabra_bbox_data[0],
                                h=palabra_bbox_data[3] - palabra_bbox_data[1]
                            )
                            
                            palabra = Palabra(
                                bbox=palabra_bbox,
                                confidence=palabra_data.get("confianza", 0.0),
                                texto=palabra_data.get("texto", ""),
                                font_family=palabra_data.get("font_family"),
                                font_size=palabra_data.get("font_size"),
                                font_style=palabra_data.get("font_style"),
                                font_weight=palabra_data.get("font_weight")
                            )
                            palabras.append(palabra)
                        
                        linea = Linea(
                            bbox=linea_bbox,
                            confidence=linea_data.get("confianza", 0.0),
                            texto=linea_data.get("texto", ""),
                            palabras=palabras
                        )
                        lineas.append(linea)
                    
                    bloque = Bloque(
                        bbox=bbox,
                        confidence=bloque_data.get("confianza", 0.0),
                        lang=bloque_data.get("lang", "es"),
                        lineas=lineas
                    )
                    bloques.append(bloque)
        except Exception:
            pass
        return bloques
    
    def _analyze_word_alignment(self, palabras: List[Palabra]) -> Dict[str, Any]:
        """Analiza la alineación de palabras"""
        if not palabras:
            return {"elements": 0, "is_aligned": True, "deviation": 0.0, "alignments": []}
        
        # Agrupar palabras por línea (misma coordenada Y)
        lines = self._group_words_by_line(palabras)
        
        alignments = []
        deviations = []
        misaligned = []
        
        for line_words in lines:
            if len(line_words) < 2:
                continue
                
            # Calcular alineación de la línea
            line_alignment = self._calculate_line_alignment(line_words)
            alignments.append(line_alignment["type"])
            deviations.append(line_alignment["deviation"])
            
            if line_alignment["deviation"] > self.alignment_thresholds["acceptable"]:
                misaligned.append({
                    "type": "line",
                    "text": " ".join([w.texto for w in line_words]),
                    "deviation": line_alignment["deviation"],
                    "alignment": line_alignment["type"]
                })
        
        return {
            "elements": len(palabras),
            "is_aligned": len(misaligned) == 0,
            "deviation": statistics.mean(deviations) if deviations else 0.0,
            "alignments": alignments,
            "misaligned": misaligned
        }
    
    def _analyze_line_alignment(self, lineas: List[Linea]) -> Dict[str, Any]:
        """Analiza la alineación de líneas"""
        if not lineas:
            return {"elements": 0, "is_aligned": True, "deviation": 0.0, "alignments": []}
        
        alignments = []
        deviations = []
        misaligned = []
        
        for linea in lineas:
            # Calcular alineación de la línea
            line_alignment = self._calculate_line_alignment([linea])
            alignments.append(line_alignment["type"])
            deviations.append(line_alignment["deviation"])
            
            if line_alignment["deviation"] > self.alignment_thresholds["acceptable"]:
                misaligned.append({
                    "type": "line",
                    "text": linea.texto,
                    "deviation": line_alignment["deviation"],
                    "alignment": line_alignment["type"]
                })
        
        return {
            "elements": len(lineas),
            "is_aligned": len(misaligned) == 0,
            "deviation": statistics.mean(deviations) if deviations else 0.0,
            "alignments": alignments,
            "misaligned": misaligned
        }
    
    def _analyze_block_alignment(self, bloques: List[Bloque]) -> Dict[str, Any]:
        """Analiza la alineación de bloques"""
        if not bloques:
            return {"elements": 0, "is_aligned": True, "deviation": 0.0, "alignments": []}
        
        alignments = []
        deviations = []
        misaligned = []
        
        for bloque in bloques:
            # Calcular alineación del bloque
            block_alignment = self._calculate_block_alignment(bloque)
            alignments.append(block_alignment["type"])
            deviations.append(block_alignment["deviation"])
            
            if block_alignment["deviation"] > self.alignment_thresholds["acceptable"]:
                # Obtener texto del bloque desde las líneas
                bloque_texto = " ".join([linea.texto for linea in bloque.lineas])
                misaligned.append({
                    "type": "block",
                    "text": bloque_texto[:50] + "..." if len(bloque_texto) > 50 else bloque_texto,
                    "deviation": block_alignment["deviation"],
                    "alignment": block_alignment["type"]
                })
        
        return {
            "elements": len(bloques),
            "is_aligned": len(misaligned) == 0,
            "deviation": statistics.mean(deviations) if deviations else 0.0,
            "alignments": alignments,
            "misaligned": misaligned
        }
    
    def _group_words_by_line(self, palabras: List[Palabra]) -> List[List[Palabra]]:
        """Agrupa palabras por línea basado en coordenada Y"""
        if not palabras:
            return []
        
        # Ordenar palabras por coordenada Y
        sorted_words = sorted(palabras, key=lambda w: w.bbox.y)
        
        lines = []
        current_line = [sorted_words[0]]
        current_y = sorted_words[0].bbox.y
        
        for palabra in sorted_words[1:]:
            # Si la diferencia en Y es pequeña, es la misma línea
            if abs(palabra.bbox.y - current_y) < 10:  # 10 píxeles de tolerancia
                current_line.append(palabra)
            else:
                lines.append(current_line)
                current_line = [palabra]
                current_y = palabra.bbox.y
        
        lines.append(current_line)
        return lines
    
    def _calculate_line_alignment(self, words: List[Palabra]) -> Dict[str, Any]:
        """Calcula la alineación de una línea de palabras"""
        if len(words) < 2:
            return {"type": "single", "deviation": 0.0}
        
        # Obtener coordenadas Y de las palabras
        y_coords = [w.bbox.y for w in words]
        
        # Calcular desviación estándar de las coordenadas Y
        deviation = statistics.stdev(y_coords) if len(y_coords) > 1 else 0.0
        
        # Determinar tipo de alineación
        if deviation <= self.alignment_thresholds["perfect"]:
            alignment_type = "perfect"
        elif deviation <= self.alignment_thresholds["good"]:
            alignment_type = "good"
        elif deviation <= self.alignment_thresholds["acceptable"]:
            alignment_type = "acceptable"
        elif deviation <= self.alignment_thresholds["poor"]:
            alignment_type = "poor"
        else:
            alignment_type = "bad"
        
        return {"type": alignment_type, "deviation": deviation}
    
    def _calculate_block_alignment(self, bloque: Bloque) -> Dict[str, Any]:
        """Calcula la alineación de un bloque"""
        # Para bloques, analizamos la consistencia de las líneas dentro del bloque
        if not bloque.lineas:
            return {"type": "single", "deviation": 0.0}
        
        # Obtener coordenadas Y de las líneas del bloque
        y_coords = [linea.bbox.y for linea in bloque.lineas]
        
        # Calcular desviación estándar de las coordenadas Y
        deviation = statistics.stdev(y_coords) if len(y_coords) > 1 else 0.0
        
        # Determinar tipo de alineación
        if deviation <= self.alignment_thresholds["perfect"]:
            alignment_type = "perfect"
        elif deviation <= self.alignment_thresholds["good"]:
            alignment_type = "good"
        elif deviation <= self.alignment_thresholds["acceptable"]:
            alignment_type = "acceptable"
        elif deviation <= self.alignment_thresholds["poor"]:
            alignment_type = "poor"
        else:
            alignment_type = "bad"
        
        return {"type": alignment_type, "deviation": deviation}
    
    def _combine_alignment_analysis(self, word_analysis: Dict, line_analysis: Dict, 
                                  block_analysis: Dict) -> Dict[str, Any]:
        """Combina los análisis de alineación"""
        total_elements = (word_analysis["elements"] + 
                         line_analysis["elements"] + 
                         block_analysis["elements"])
        
        # Calcular desviación promedio ponderada
        total_deviation = 0.0
        total_weight = 0
        
        if word_analysis["elements"] > 0:
            total_deviation += word_analysis["deviation"] * word_analysis["elements"]
            total_weight += word_analysis["elements"]
        
        if line_analysis["elements"] > 0:
            total_deviation += line_analysis["deviation"] * line_analysis["elements"]
            total_weight += line_analysis["elements"]
        
        if block_analysis["elements"] > 0:
            total_deviation += block_analysis["deviation"] * block_analysis["elements"]
            total_weight += block_analysis["elements"]
        
        average_deviation = total_deviation / total_weight if total_weight > 0 else 0.0
        
        # Determinar si está alineado
        is_aligned = (average_deviation <= self.alignment_thresholds["acceptable"] and
                     len(word_analysis["misaligned"]) == 0 and
                     len(line_analysis["misaligned"]) == 0 and
                     len(block_analysis["misaligned"]) == 0)
        
        # Combinar alineaciones detectadas
        detected_alignments = list(set(
            word_analysis["alignments"] + 
            line_analysis["alignments"] + 
            block_analysis["alignments"]
        ))
        
        # Combinar desviaciones por elemento
        deviations_per_element = (
            word_analysis["deviations"] if "deviations" in word_analysis else [] +
            line_analysis["deviations"] if "deviations" in line_analysis else [] +
            block_analysis["deviations"] if "deviations" in block_analysis else []
        )
        
        # Combinar elementos mal alineados
        misaligned_elements = (
            word_analysis["misaligned"] + 
            line_analysis["misaligned"] + 
            block_analysis["misaligned"]
        )
        
        return {
            "total_elements": total_elements,
            "is_aligned": is_aligned,
            "average_deviation": average_deviation,
            "detected_alignments": detected_alignments,
            "deviations_per_element": deviations_per_element,
            "misaligned_elements": misaligned_elements
        }
    
    def _detect_suspicious_alignment(self, combined_analysis: Dict, palabras: List[Palabra], 
                                   lineas: List[Linea], bloques: List[Bloque]) -> List[str]:
        """Detecta indicadores sospechosos en la alineación"""
        indicators = []
        
        # Verificar desviación alta
        if combined_analysis["average_deviation"] > self.alignment_thresholds["poor"]:
            indicators.append(f"Desviación de alineación muy alta: {combined_analysis['average_deviation']:.2f}")
        
        # Verificar elementos mal alineados
        if len(combined_analysis["misaligned_elements"]) > 0:
            indicators.append(f"{len(combined_analysis['misaligned_elements'])} elementos mal alineados detectados")
        
        # Verificar alineaciones inconsistentes
        if len(combined_analysis["detected_alignments"]) > 3:
            indicators.append("Múltiples tipos de alineación detectados - posible manipulación")
        
        # Verificar rotaciones extrañas
        rotated_elements = self._detect_rotated_elements(palabras, lineas, bloques)
        if rotated_elements:
            indicators.append(f"{len(rotated_elements)} elementos con rotación extraña detectados")
        
        # Verificar alineación no estándar
        non_standard_alignments = [a for a in combined_analysis["detected_alignments"] 
                                 if a not in self.standard_alignments]
        if non_standard_alignments:
            indicators.append(f"Alineaciones no estándar detectadas: {non_standard_alignments}")
        
        return indicators
    
    def _detect_rotated_elements(self, palabras: List[Palabra], lineas: List[Linea], 
                               bloques: List[Bloque]) -> List[Dict[str, Any]]:
        """Detecta elementos con rotación extraña"""
        rotated = []
        
        # Analizar palabras
        for palabra in palabras:
            rotation = self._calculate_rotation([palabra.bbox.x, palabra.bbox.y, 
                                               palabra.bbox.x + palabra.bbox.w, 
                                               palabra.bbox.y + palabra.bbox.h])
            if abs(rotation) > self.rotation_thresholds["slight"]:
                rotated.append({
                    "type": "word",
                    "text": palabra.texto,
                    "rotation": rotation
                })
        
        # Analizar líneas
        for linea in lineas:
            rotation = self._calculate_rotation([linea.bbox.x, linea.bbox.y, 
                                               linea.bbox.x + linea.bbox.w, 
                                               linea.bbox.y + linea.bbox.h])
            if abs(rotation) > self.rotation_thresholds["slight"]:
                rotated.append({
                    "type": "line",
                    "text": linea.texto,
                    "rotation": rotation
                })
        
        # Analizar bloques
        for bloque in bloques:
            rotation = self._calculate_rotation([bloque.bbox.x, bloque.bbox.y, 
                                               bloque.bbox.x + bloque.bbox.w, 
                                               bloque.bbox.y + bloque.bbox.h])
            if abs(rotation) > self.rotation_thresholds["slight"]:
                # Obtener texto del bloque desde las líneas
                bloque_texto = " ".join([linea.texto for linea in bloque.lineas])
                rotated.append({
                    "type": "block",
                    "text": bloque_texto[:50] + "..." if len(bloque_texto) > 50 else bloque_texto,
                    "rotation": rotation
                })
        
        return rotated
    
    def _calculate_rotation(self, bbox: List[float]) -> float:
        """Calcula la rotación de un elemento basado en su bbox"""
        if len(bbox) < 4:
            return 0.0
        
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        
        # Calcular ángulo de rotación basado en la relación altura/ancho
        if width > 0:
            angle = math.atan(height / width) * 180 / math.pi
            return angle - 90  # Normalizar a 0 grados para texto horizontal
        
        return 0.0
