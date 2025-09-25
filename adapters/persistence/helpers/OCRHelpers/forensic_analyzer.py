"""
Helper para análisis forense en OCR
"""
import re
import statistics
from typing import List, Tuple
from domain.entities.forensic_ocr_details import (
    Bloque, AlertaForense, ForenseInfo, ResumenForense, BBox
)
from .image_processor import ImageProcessor

class ForensicAnalyzer:
    """Helper para análisis forense"""
    
    @staticmethod
    def analyze_forensic_heuristics(bloques: List[Bloque]) -> Tuple[List[AlertaForense], ResumenForense]:
        """Analiza heurísticas forenses"""
        alertas = []
        
        # Análisis de sobreposiciones sospechosas
        for bloque in bloques:
            for linea in bloque.lineas:
                if len(linea.palabras) > 1:
                    # Verificar alineación de baseline
                    baselines = [p.bbox.y + p.bbox.h for p in linea.palabras]
                    if baselines:
                        baseline_var = float(statistics.variance(baselines))
                        if baseline_var > 9:  # >3px de varianza
                            alertas.append(AlertaForense(
                                tipo="sobreposicion_sospechosa",
                                severidad="medium",
                                detalle=f"Desviación alta de baseline: {baseline_var:.2f}px",
                                bbox=linea.bbox
                            ))
                    
                    # Verificar overlap de bounding boxes
                    for i, palabra1 in enumerate(linea.palabras):
                        for j, palabra2 in enumerate(linea.palabras[i+1:], i+1):
                            if ImageProcessor.boxes_overlap(palabra1.bbox, palabra2.bbox):
                                alertas.append(AlertaForense(
                                    tipo="sobreposicion_sospechosa",
                                    severidad="high",
                                    detalle="Overlap de bounding boxes detectado",
                                    bbox=palabra1.bbox
                                ))

        # Análisis de zonas de baja confianza
        for bloque in bloques:
            for linea in bloque.lineas:
                confidences = [p.confidence for p in linea.palabras]
                if confidences:
                    avg_conf = float(statistics.mean(confidences))
                    if avg_conf < 0.55:
                        alertas.append(AlertaForense(
                            tipo="baja_confianza_local",
                            severidad="low",
                            detalle=f"Confianza promedio baja: {avg_conf:.2f}",
                            bbox=linea.bbox
                        ))

        # Análisis de formato inconsistente
        for bloque in bloques:
            for linea in bloque.lineas:
                # Verificar mezcla de separadores decimales
                if ',' in linea.texto and '.' in linea.texto:
                    # Verificar si hay números con diferentes separadores
                    numeros = re.findall(r'[\d.,]+', linea.texto)
                    if len(numeros) > 1:
                        separadores = set()
                        for num in numeros:
                            if ',' in num and '.' in num:
                                separadores.add('mixed')
                            elif ',' in num:
                                separadores.add('comma')
                            elif '.' in num:
                                separadores.add('dot')
                        
                        if len(separadores) > 1:
                            alertas.append(AlertaForense(
                                tipo="formato_inconsistente",
                                severidad="medium",
                                detalle="Mezcla de separadores decimales detectada",
                                bbox=linea.bbox
                            ))

        # Calcular scores
        score_calidad_ocr = ForensicAnalyzer._calculate_ocr_quality_score(bloques)
        score_integridad_textual = ForensicAnalyzer._calculate_text_integrity_score(bloques)
        tiene_inconsistencias_monetarias = any(a.tipo == "aritmetica_inconsistente" for a in alertas)
        tiene_sobreposiciones_sospechosas = any(a.tipo == "sobreposicion_sospechosa" for a in alertas)

        resumen = ResumenForense(
            score_calidad_ocr=score_calidad_ocr,
            score_integridad_textual=score_integridad_textual,
            tiene_inconsistencias_monetarias=tiene_inconsistencias_monetarias,
            tiene_sobreposiciones_sospechosas=tiene_sobreposiciones_sospechosas
        )

        return alertas, resumen

    @staticmethod
    def _calculate_ocr_quality_score(bloques: List[Bloque]) -> float:
        """Calcula el score de calidad OCR"""
        if not bloques:
            return 0.0
        
        all_confidences = []
        for bloque in bloques:
            for linea in bloque.lineas:
                for palabra in linea.palabras:
                    all_confidences.append(palabra.confidence)
        
        if not all_confidences:
            return 0.0
        
        # Score basado en confianza promedio
        avg_conf = float(statistics.mean(all_confidences))
        return min(avg_conf * 1.2, 1.0)  # Escalar y limitar a 1.0

    @staticmethod
    def _calculate_text_integrity_score(bloques: List[Bloque]) -> float:
        """Calcula el score de integridad textual"""
        if not bloques:
            return 0.0
        
        # Score basado en consistencia de confianza y estructura
        all_confidences = []
        for bloque in bloques:
            for linea in bloque.lineas:
                for palabra in linea.palabras:
                    all_confidences.append(palabra.confidence)
        
        if not all_confidences:
            return 0.0
        
        # Calcular varianza de confianza (menor varianza = mayor integridad)
        conf_std = float(statistics.stdev(all_confidences)) if len(all_confidences) > 1 else 0.0
        integrity_score = max(0.0, 1.0 - conf_std)
        
        return integrity_score
