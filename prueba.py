#!/usr/bin/env python3
"""
Analizador de Capas Múltiples en PDFs
Detecta modificaciones, superposiciones y capas ocultas en documentos PDF

Autor: Sistema de Análisis de Documentos
Versión: 2.0
"""

import re
import os
import sys
import json
import statistics
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional, Set
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import argparse

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF no está instalado. Instale con: pip install PyMuPDF")
    sys.exit(1)

try:
    import PyPDF2
except ImportError:
    print("Advertencia: PyPDF2 no está instalado. Algunas funciones estarán limitadas.")
    PyPDF2 = None


class PDFLayerAnalyzer:
    """Analizador avanzado de capas múltiples en PDFs"""
    
    def __init__(self, pdf_path: str, verbose: bool = False):
        self.pdf_path = pdf_path
        self.verbose = verbose
        self.pdf_bytes = None
        self.extracted_text = ""
        self.analysis_results = {}
        
        # Configuración de detección
        self.OCG_PATTERNS = [
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
        
        self.OVERLAY_PATTERNS = [
            rb"/Type\s*/XObject",
            rb"/Subtype\s*/Form",
            rb"/Group\s*<<",
            rb"/S\s*/Transparency",
            rb"/BM\s*/\w+",  # Blend modes
            rb"/CA\s+[\d\.]+",  # Constant alpha
            rb"/ca\s+[\d\.]+",  # Non-stroking alpha
        ]
        
        self.SUSPICIOUS_OPERATORS = [
            rb"q\s+[\d\.\-\s]+cm",  # Transformaciones de matriz
            rb"Do\s",  # XObject references
            rb"gs\s",  # Graphics state
            rb"/G\d+\s+gs",  # Graphics state references
        ]
        
    def load_pdf(self) -> bool:
        """Carga el archivo PDF y extrae el texto"""
        try:
            with open(self.pdf_path, 'rb') as f:
                self.pdf_bytes = f.read()
            
            # Extraer texto con PyMuPDF
            doc = fitz.open(self.pdf_path)
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            self.extracted_text = "\n".join(text_parts)
            doc.close()
            
            if self.verbose:
                print(f"✓ PDF cargado: {len(self.pdf_bytes)} bytes, {len(self.extracted_text)} caracteres de texto")
            
            return True
            
        except Exception as e:
            print(f"❌ Error cargando PDF: {e}")
            return False
    
    def detect_ocg_layers(self) -> Dict[str, Any]:
        """Detecta capas OCG (Optional Content Groups) estándar"""
        if not self.pdf_bytes:
            return {"error": "PDF no cargado"}
        
        sample_size = min(8_000_000, len(self.pdf_bytes))
        sample = self.pdf_bytes[:sample_size]
        
        results = {
            "has_ocg": False,
            "ocg_count": 0,
            "patterns_found": [],
            "confidence": 0.0,
            "layer_objects": []
        }
        
        total_matches = 0
        pattern_counts = {}
        
        for pattern in self.OCG_PATTERNS:
            matches = re.findall(pattern, sample)
            count = len(matches)
            if count > 0:
                pattern_name = pattern.decode('utf-8', errors='ignore')
                pattern_counts[pattern_name] = count
                total_matches += count
                results["patterns_found"].append({
                    "pattern": pattern_name,
                    "count": count,
                    "samples": [m.decode('utf-8', errors='ignore')[:50] for m in matches[:3]]
                })
        
        # Buscar referencias a grupos de contenido opcional
        ocg_refs = re.findall(rb"/OC\s+(\d+)\s+\d+\s+R", sample)
        if ocg_refs:
            results["layer_objects"] = [int(ref) for ref in ocg_refs[:10]]
        
        results["ocg_count"] = total_matches
        results["has_ocg"] = total_matches > 0
        
        # Calcular confianza basada en patrones encontrados
        if total_matches >= 5:
            results["confidence"] = min(0.95, 0.6 + (total_matches * 0.05))
        elif total_matches >= 2:
            results["confidence"] = 0.4 + (total_matches * 0.1)
        elif total_matches == 1:
            results["confidence"] = 0.2
        
        if self.verbose and results["has_ocg"]:
            print(f"✓ OCG detectado: {total_matches} patrones, confianza: {results['confidence']:.1%}")
        
        return results
    
    def detect_overlay_objects(self) -> Dict[str, Any]:
        """Detecta objetos superpuestos y transparencias"""
        if not self.pdf_bytes:
            return {"error": "PDF no cargado"}
        
        sample = self.pdf_bytes[:min(6_000_000, len(self.pdf_bytes))]
        
        results = {
            "has_overlays": False,
            "overlay_count": 0,
            "transparency_objects": 0,
            "blend_modes": [],
            "alpha_values": [],
            "xobject_count": 0
        }
        
        overlay_total = 0
        
        for pattern in self.OVERLAY_PATTERNS:
            matches = len(re.findall(pattern, sample))
            overlay_total += matches
            
            if b"Transparency" in pattern:
                results["transparency_objects"] += matches
            elif b"XObject" in pattern:
                results["xobject_count"] += matches
        
        # Buscar modos de fusión específicos
        blend_modes = re.findall(rb"/BM\s*/(\w+)", sample)
        results["blend_modes"] = [bm.decode('utf-8', errors='ignore') for bm in blend_modes[:10]]
        
        # Buscar valores alpha
        alpha_values = re.findall(rb"/CA\s+([\d\.]+)", sample)
        alpha_values.extend(re.findall(rb"/ca\s+([\d\.]+)", sample))
        results["alpha_values"] = [float(av) for av in alpha_values[:20] if av]
        
        results["overlay_count"] = overlay_total
        results["has_overlays"] = overlay_total > 3  # Umbral para considerar sospechoso
        
        if self.verbose and results["has_overlays"]:
            print(f"✓ Objetos superpuestos: {overlay_total}, transparencias: {results['transparency_objects']}")
        
        return results
    
    def analyze_content_streams(self) -> Dict[str, Any]:
        """Analiza múltiples streams de contenido"""
        if not self.pdf_bytes:
            return {"error": "PDF no cargado"}
        
        sample = self.pdf_bytes[:min(10_000_000, len(self.pdf_bytes))]
        
        # Contar streams de contenido
        content_streams = len(re.findall(rb"stream\s", sample))
        endstream_count = len(re.findall(rb"endstream", sample))
        
        # Analizar operadores gráficos sospechosos
        suspicious_ops = 0
        operator_details = []
        
        for pattern in self.SUSPICIOUS_OPERATORS:
            matches = re.findall(pattern, sample)
            count = len(matches)
            suspicious_ops += count
            if count > 0:
                operator_details.append({
                    "operator": pattern.decode('utf-8', errors='ignore'),
                    "count": count
                })
        
        # Detectar múltiples definiciones de estado gráfico
        graphics_states = len(re.findall(rb"/ExtGState", sample))
        
        results = {
            "content_streams": content_streams,
            "endstream_count": endstream_count,
            "stream_integrity": content_streams == endstream_count,
            "suspicious_operators": suspicious_ops,
            "graphics_states": graphics_states,
            "operator_details": operator_details,
            "risk_level": "low"
        }
        
        # Evaluar nivel de riesgo
        if content_streams > 20 or suspicious_ops > 50:
            results["risk_level"] = "high"
        elif content_streams > 10 or suspicious_ops > 20:
            results["risk_level"] = "medium"
        
        if self.verbose:
            print(f"✓ Content streams: {content_streams}, operadores sospechosos: {suspicious_ops}")
        
        return results
    
    def analyze_text_overlapping(self) -> Dict[str, Any]:
        """Analiza superposición y duplicación en el texto extraído"""
        if not self.extracted_text:
            return {"error": "No hay texto extraído"}
        
        lines = [line.strip() for line in self.extracted_text.split('\n') if line.strip()]
        
        results = {
            "has_duplicates": False,
            "duplicate_lines": {},
            "similar_pairs": [],
            "suspicious_formatting": [],
            "overlapping_probability": 0.0
        }
        
        # 1. Detectar líneas duplicadas exactas
        line_counts = Counter(lines)
        duplicates = {line: count for line, count in line_counts.items() if count > 1}
        
        if duplicates:
            results["has_duplicates"] = True
            results["duplicate_lines"] = {k: v for k, v in list(duplicates.items())[:10]}
        
        # 2. Detectar líneas muy similares
        similar_pairs = []
        for i, line1 in enumerate(lines[:100]):  # Limitar para performance
            for j, line2 in enumerate(lines[i+1:min(i+50, len(lines))], i+1):
                if len(line1) > 10 and len(line2) > 10:  # Solo líneas significativas
                    similarity = SequenceMatcher(None, line1, line2).ratio()
                    if 0.7 <= similarity < 1.0:
                        similar_pairs.append({
                            "line1": line1[:100],
                            "line2": line2[:100], 
                            "similarity": round(similarity, 3)
                        })
        
        results["similar_pairs"] = similar_pairs[:10]
        
        # 3. Detectar patrones de formato sospechosos
        suspicious_patterns = []
        
        for line in lines[:200]:  # Limitar para performance
            # Palabras pegadas anormalmente
            if re.search(r'[A-ZÁÉÍÓÚÑ]{3,}[a-záéíóúñ]+[A-ZÁÉÍÓÚÑ]{3,}', line):
                suspicious_patterns.append(f"Formato pegado: {line[:60]}")
            
            # Números mal formateados
            if re.search(r'\d{4,}\s+[A-Za-z]{1,3}\s+[A-Za-z]', line):
                suspicious_patterns.append(f"Número malformado: {line[:60]}")
            
            # Espaciado anómalo
            if re.search(r'\w{3,}\s{3,}\w{3,}', line):
                suspicious_patterns.append(f"Espaciado anómalo: {line[:60]}")
        
        results["suspicious_formatting"] = suspicious_patterns[:15]
        
        # 4. Calcular probabilidad de superposición
        prob = 0.0
        if duplicates:
            prob += min(0.4, len(duplicates) * 0.1)
        if similar_pairs:
            prob += min(0.3, len(similar_pairs) * 0.05)
        if suspicious_patterns:
            prob += min(0.3, len(suspicious_patterns) * 0.02)
        
        results["overlapping_probability"] = round(prob, 3)
        
        if self.verbose and prob > 0.2:
            print(f"✓ Superposición de texto detectada: {prob:.1%} probabilidad")
        
        return results
    
    def analyze_pdf_structure(self) -> Dict[str, Any]:
        """Analiza la estructura interna del PDF"""
        try:
            doc = fitz.open(self.pdf_path)
            
            results = {
                "pages": doc.page_count,
                "objects_per_page": [],
                "overlapping_blocks": 0,
                "suspicious_structure": False,
                "metadata": {},
                "incremental_updates": 0
            }
            
            # Analizar metadatos
            metadata = doc.metadata or {}
            results["metadata"] = {
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "mod_date": metadata.get("modDate", "")
            }
            
            # Analizar cada página
            total_overlaps = 0
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                
                # Obtener bloques de texto
                text_dict = page.get_text("dict")
                blocks = text_dict.get('blocks', [])
                
                # Contar objetos por página
                images = len(page.get_images())
                drawings = len(page.get_drawings())
                objects_count = len(blocks) + images + drawings
                results["objects_per_page"].append(objects_count)
                
                # Detectar bloques superpuestos
                page_overlaps = 0
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
                            overlap_area = (
                                min(bbox1[2], bbox2[2]) - max(bbox1[0], bbox2[0])
                            ) * (
                                min(bbox1[3], bbox2[3]) - max(bbox1[1], bbox2[1])
                            )
                            if overlap_area > 100:  # Área mínima significativa
                                page_overlaps += 1
                
                total_overlaps += page_overlaps
            
            results["overlapping_blocks"] = total_overlaps
            
            # Detectar actualizaciones incrementales
            if self.pdf_bytes:
                results["incremental_updates"] = self.pdf_bytes.count(b"startxref")
            
            # Evaluar si la estructura es sospechosa
            avg_objects = statistics.mean(results["objects_per_page"]) if results["objects_per_page"] else 0
            if (total_overlaps > 3 or 
                avg_objects > 100 or 
                results["incremental_updates"] > 2):
                results["suspicious_structure"] = True
            
            doc.close()
            
            if self.verbose:
                print(f"✓ Estructura: {results['pages']} páginas, {total_overlaps} superposiciones")
            
            return results
            
        except Exception as e:
            return {"error": f"Error analizando estructura: {e}"}
    
    def calculate_layer_probability(self) -> Dict[str, Any]:
        """Calcula la probabilidad final de capas múltiples"""
        ocg = self.analysis_results.get("ocg_detection", {})
        overlays = self.analysis_results.get("overlay_detection", {})
        text_analysis = self.analysis_results.get("text_analysis", {})
        structure = self.analysis_results.get("structure_analysis", {})
        
        # Pesos para cada indicador
        weights = {
            "ocg_confidence": 0.35,
            "overlay_presence": 0.25,
            "text_overlapping": 0.25,
            "structure_suspicious": 0.15
        }
        
        # Calcular score ponderado
        score = 0.0
        details = {}
        
        # OCG detection
        if ocg.get("has_ocg", False):
            ocg_score = ocg.get("confidence", 0.0)
            score += ocg_score * weights["ocg_confidence"]
            details["ocg_contribution"] = ocg_score * weights["ocg_confidence"]
        
        # Overlay objects
        if overlays.get("has_overlays", False):
            overlay_score = min(1.0, overlays.get("overlay_count", 0) / 20.0)
            score += overlay_score * weights["overlay_presence"]
            details["overlay_contribution"] = overlay_score * weights["overlay_presence"]
        
        # Text overlapping
        text_score = text_analysis.get("overlapping_probability", 0.0)
        score += text_score * weights["text_overlapping"]
        details["text_contribution"] = text_score * weights["text_overlapping"]
        
        # Structure analysis
        if structure.get("suspicious_structure", False):
            struct_score = 0.8
            score += struct_score * weights["structure_suspicious"]
            details["structure_contribution"] = struct_score * weights["structure_suspicious"]
        
        # Clasificar resultado
        if score >= 0.8:
            risk_level = "VERY_HIGH"
            recommendation = "REJECT - Highly likely to contain multiple layers"
        elif score >= 0.6:
            risk_level = "HIGH"
            recommendation = "INVESTIGATE - Strong indicators of layer manipulation"
        elif score >= 0.4:
            risk_level = "MEDIUM"
            recommendation = "CAUTION - Some suspicious patterns detected"
        elif score >= 0.2:
            risk_level = "LOW"
            recommendation = "MINOR - Few weak indicators"
        else:
            risk_level = "VERY_LOW"
            recommendation = "ACCEPT - No significant layer indicators"
        
        return {
            "probability": round(score, 3),
            "risk_level": risk_level,
            "recommendation": recommendation,
            "confidence": round(min(1.0, score + 0.1), 3),
            "score_breakdown": details,
            "weights_used": weights
        }
    
    def generate_report(self) -> str:
        """Genera un reporte legible del análisis"""
        if not self.analysis_results:
            return "❌ No hay resultados de análisis disponibles"
        
        final_assessment = self.analysis_results.get("final_assessment", {})
        prob = final_assessment.get("probability", 0.0)
        risk_level = final_assessment.get("risk_level", "UNKNOWN")
        
        report = []
        report.append("=" * 80)
        report.append("📄 REPORTE DE ANÁLISIS DE CAPAS MÚLTIPLES")
        report.append("=" * 80)
        report.append(f"📁 Archivo: {os.path.basename(self.pdf_path)}")
        report.append(f"📊 Probabilidad de Capas Múltiples: {prob:.1%}")
        report.append(f"⚠️  Nivel de Riesgo: {risk_level}")
        report.append(f"🎯 Recomendación: {final_assessment.get('recommendation', 'N/A')}")
        report.append("")
        
        # Resultados por categoría
        ocg = self.analysis_results.get("ocg_detection", {})
        if ocg.get("has_ocg"):
            report.append("🔴 CAPAS OCG DETECTADAS:")
            report.append(f"   Confianza: {ocg.get('confidence', 0):.1%}")
            report.append(f"   Objetos OCG: {ocg.get('ocg_count', 0)}")
            for pattern in ocg.get("patterns_found", []):
                report.append(f"   - {pattern['pattern']}: {pattern['count']} veces")
            report.append("")
        
        overlays = self.analysis_results.get("overlay_detection", {})
        if overlays.get("has_overlays"):
            report.append("🟡 OBJETOS SUPERPUESTOS DETECTADOS:")
            report.append(f"   Total objetos: {overlays.get('overlay_count', 0)}")
            report.append(f"   Transparencias: {overlays.get('transparency_objects', 0)}")
            if overlays.get("blend_modes"):
                report.append(f"   Modos de fusión: {', '.join(overlays['blend_modes'][:5])}")
            report.append("")
        
        text_analysis = self.analysis_results.get("text_analysis", {})
        if text_analysis.get("has_duplicates") or text_analysis.get("overlapping_probability", 0) > 0.2:
            report.append("🟠 SUPERPOSICIÓN DE TEXTO DETECTADA:")
            report.append(f"   Probabilidad: {text_analysis.get('overlapping_probability', 0):.1%}")
            
            duplicates = text_analysis.get("duplicate_lines", {})
            if duplicates:
                report.append("   Líneas duplicadas:")
                for line, count in list(duplicates.items())[:3]:
                    report.append(f"   - '{line[:50]}...' ({count} veces)")
            
            similar = text_analysis.get("similar_pairs", [])
            if similar:
                report.append("   Líneas similares:")
                for pair in similar[:2]:
                    report.append(f"   - Similitud {pair['similarity']:.1%}: '{pair['line1'][:40]}...'")
            report.append("")
        
        structure = self.analysis_results.get("structure_analysis", {})
        if structure.get("suspicious_structure"):
            report.append("⚠️  ESTRUCTURA SOSPECHOSA:")
            report.append(f"   Páginas: {structure.get('pages', 0)}")
            report.append(f"   Bloques superpuestos: {structure.get('overlapping_blocks', 0)}")
            report.append(f"   Actualizaciones incrementales: {structure.get('incremental_updates', 0)}")
            
            metadata = structure.get("metadata", {})
            if metadata.get("creator") or metadata.get("producer"):
                report.append(f"   Software: {metadata.get('creator', '')} / {metadata.get('producer', '')}")
            report.append("")
        
        # Desglose de puntuación
        score_breakdown = final_assessment.get("score_breakdown", {})
        if score_breakdown:
            report.append("📈 DESGLOSE DE PUNTUACIÓN:")
            for component, value in score_breakdown.items():
                component_name = component.replace("_contribution", "").replace("_", " ").title()
                report.append(f"   {component_name}: {value:.3f}")
            report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """Ejecuta el análisis completo del PDF"""
        if not self.load_pdf():
            return {"error": "No se pudo cargar el PDF"}
        
        if self.verbose:
            print("🔍 Iniciando análisis de capas múltiples...")
        
        # Ejecutar todos los análisis
        self.analysis_results["ocg_detection"] = self.detect_ocg_layers()
        self.analysis_results["overlay_detection"] = self.detect_overlay_objects()
        self.analysis_results["content_streams"] = self.analyze_content_streams()
        self.analysis_results["text_analysis"] = self.analyze_text_overlapping()
        self.analysis_results["structure_analysis"] = self.analyze_pdf_structure()
        
        # Cálculo final
        self.analysis_results["final_assessment"] = self.calculate_layer_probability()
        
        if self.verbose:
            print("✅ Análisis completado")
        
        return self.analysis_results
    
    def export_results(self, output_path: str, format_type: str = "json") -> bool:
        """Exporta los resultados en diferentes formatos"""
        try:
            if format_type.lower() == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(self.analysis_results, f, indent=2, ensure_ascii=False, default=str)
            
            elif format_type.lower() == "txt":
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(self.generate_report())
            
            else:
                print(f"❌ Formato no soportado: {format_type}")
                return False
            
            if self.verbose:
                print(f"✅ Resultados exportados a: {output_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error exportando resultados: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Analizador de Capas Múltiples en PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python pdf_layer_analyzer.py documento.pdf
  python pdf_layer_analyzer.py documento.pdf --verbose --output results.json
  python pdf_layer_analyzer.py documento.pdf --export-txt report.txt
        """
    )
    
    parser.add_argument("pdf_path", help="Ruta al archivo PDF a analizar")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar información detallada")
    parser.add_argument("--output", "-o", help="Exportar resultados a archivo JSON")
    parser.add_argument("--export-txt", help="Exportar reporte a archivo de texto")
    parser.add_argument("--threshold", type=float, default=0.6, 
                      help="Umbral de probabilidad para considerar sospechoso (0.0-1.0)")
    
    args = parser.parse_args()
    
    # Verificar que el archivo existe
    if not os.path.isfile(args.pdf_path):
        print(f"❌ Error: El archivo '{args.pdf_path}' no existe")
        sys.exit(1)
    
    # Crear analizador y ejecutar
    analyzer = PDFLayerAnalyzer(args.pdf_path, verbose=args.verbose)
    results = analyzer.run_full_analysis()
    
    if "error" in results:
        print(f"❌ Error en el análisis: {results['error']}")
        sys.exit(1)
    
    # Mostrar resultados
    final_assessment = results.get("final_assessment", {})
    probability = final_assessment.get("probability", 0.0)
    risk_level = final_assessment.get("risk_level", "UNKNOWN")
    
    print("\n" + analyzer.generate_report())
    
    # Exportar si se solicita
    if args.output:
        analyzer.export_results(args.output, "json")
    
    if args.export_txt:
        analyzer.export_results(args.export_txt, "txt")
    
    # Código de salida basado en probabilidad
    if probability >= args.threshold:
        print(f"\n🚨 ALERTA: Probabilidad de capas múltiples ({probability:.1%}) supera el umbral ({args.threshold:.1%})")
        sys.exit(2)  # Código de salida para indicar detección positiva
    else:
        print(f"\n✅ OK: Probabilidad de capas múltiples ({probability:.1%}) bajo el umbral ({args.threshold:.1%})")
        sys.exit(0)


if __name__ == "__main__":
    main()