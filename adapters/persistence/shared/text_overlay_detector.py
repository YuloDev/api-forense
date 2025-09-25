"""
Detector principal de texto superpuesto en PDFs.

Orquesta todos los análisis modulares para detectar texto superpuesto.
"""

import base64
import fitz
from typing import Dict, Any
from helpers.type_conversion import safe_serialize_dict

from .stream_analyzer import localizar_overlay_por_stream
from .layer_analyzer import stack_compare
from .annotation_analyzer import inspeccionar_overlay_avanzado, analyze_annotations
from .image_analyzer import analyze_images


class TextOverlayDetector:
    """Detector especializado de texto superpuesto en PDFs"""
    
    def __init__(self, pdf_bytes: bytes):
        self.pdf_bytes = pdf_bytes
        self.doc = None
        self.analysis_results = {
            "zona_1_anotaciones": {},
            "zona_2_contenido_pagina": {},
            "zona_3_form_xobject": {},
            "zona_4_acroform": {},
            "resumen_general": {},
            "xml_estructura": {}
        }
    
    def analyze_pdf(self) -> Dict[str, Any]:
        """Ejecuta el análisis completo del PDF"""
        try:
            self.doc = fitz.open(stream=self.pdf_bytes, filetype="pdf")
            
            # Analizar cada zona
            self.analysis_results["zona_1_anotaciones"] = self._analyze_annotations()
            self.analysis_results["zona_2_contenido_pagina"] = self._analyze_page_contents()
            self.analysis_results["zona_3_form_xobject"] = self._analyze_form_xobjects()
            self.analysis_results["zona_4_acroform"] = self._analyze_acroform()
            
            # NUEVA: Análisis avanzado de overlay
            self.analysis_results["analisis_avanzado_overlay"] = self._analyze_advanced_overlay()
            
            # NUEVA: Análisis por stream (método más preciso)
            self.analysis_results["analisis_por_stream"] = self._analyze_stream_overlay()
            
            # NUEVA: Análisis por capas (método más avanzado)
            self.analysis_results["analisis_por_capas"] = self._analyze_stack_layers()
            
            # NUEVA: Análisis de imágenes
            self.analysis_results["analisis_imagenes"] = self._analyze_images()
            
            # Generar resumen general
            self.analysis_results["resumen_general"] = self._generate_summary()
            
            # Extraer XML/estructura del PDF
            self.analysis_results["xml_estructura"] = self._extract_pdf_structure()
            
            # Devolver la estructura original del análisis
            return self.analysis_results
            
        except Exception as e:
            return {"error": f"Error analizando PDF: {str(e)}"}
        finally:
            if self.doc:
                self.doc.close()
    
    def _analyze_annotations(self) -> Dict[str, Any]:
        """ZONA 1: Analiza anotaciones (Annotations) sobre la página"""
        try:
            results = {
                "has_annotations": False,
                "total_annotations": 0,
                "annotation_types": {},
                "overlapping_annotations": [],
                "text_annotations": [],
                "rect_annotations": [],
                "suspicious_patterns": []
            }
            
            total_annotations = 0
            overlapping_count = 0
            
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                page_results = analyze_annotations(self.doc, page_num)
                
                # Consolidar resultados de la página
                total_annotations += page_results.get("total_annotations", 0)
                overlapping_count += page_results.get("overlapping_count", 0)
                
                # Consolidar tipos de anotaciones
                for subtype, count in page_results.get("annotation_types", {}).items():
                    if subtype not in results["annotation_types"]:
                        results["annotation_types"][subtype] = 0
                    results["annotation_types"][subtype] += count
                
                # Consolidar listas
                results["text_annotations"].extend(page_results.get("text_annotations", []))
                results["rect_annotations"].extend(page_results.get("rect_annotations", []))
                results["overlapping_annotations"].extend(page_results.get("overlapping_annotations", []))
                results["suspicious_patterns"].extend(page_results.get("suspicious_patterns", []))
            
            results["has_annotations"] = total_annotations > 0
            results["total_annotations"] = total_annotations
            results["overlapping_count"] = overlapping_count
            
            return results
            
        except Exception as e:
            return {"error": f"Error analizando anotaciones: {str(e)}"}
    
    def _analyze_page_contents(self) -> Dict[str, Any]:
        """ZONA 2: Analiza contenido nuevo en la propia página"""
        results = {
            "has_multiple_streams": False,
            "stream_count": 0,
            "text_commands": [],
            "rectangle_commands": [],
            "color_commands": [],
            "suspicious_sequences": [],
            "overlapping_content": []
        }
        
        try:
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                
                # Obtener streams de contenido
                contents = page.get_contents()
                if contents:
                    if isinstance(contents, list):
                        results["stream_count"] += len(contents)
                        results["has_multiple_streams"] = len(contents) > 1
                    else:
                        results["stream_count"] = 1
                    
                    # Analizar cada stream
                    for stream_id in (contents if isinstance(contents, list) else [contents]):
                        stream_analysis = self._analyze_content_stream(stream_id, page_num)
                        
                        results["text_commands"].extend(stream_analysis["text_commands"])
                        results["rectangle_commands"].extend(stream_analysis["rectangle_commands"])
                        results["color_commands"].extend(stream_analysis["color_commands"])
                        results["suspicious_sequences"].extend(stream_analysis["suspicious_sequences"])
                        results["overlapping_content"].extend(stream_analysis["overlapping_content"])
        
        except Exception as e:
            results["error"] = f"Error analizando contenido de página: {str(e)}"
        
        return results
    
    def _analyze_form_xobjects(self) -> Dict[str, Any]:
        """ZONA 3: Analiza Form XObjects llamados desde la página"""
        results = {
            "has_form_xobjects": False,
            "xobject_count": 0,
            "form_xobjects": [],
            "text_xobjects": [],
            "suspicious_xobjects": []
        }
        
        try:
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                
                # Obtener recursos de la página
                resources = page.get_contents()
                if resources:
                    # Buscar XObjects en el diccionario de recursos
                    xobjects = self._extract_xobjects_from_page(page)
                    
                    for xobj_name, xobj_info in xobjects.items():
                        results["xobject_count"] += 1
                        results["form_xobjects"].append(xobj_info)
                        
                        # Analizar si contiene texto
                        if xobj_info.get("has_text", False):
                            results["text_xobjects"].append(xobj_info)
                        
                        # Detectar XObjects sospechosos
                        if self._is_suspicious_xobject(xobj_info):
                            results["suspicious_xobjects"].append(xobj_info)
            
            results["has_form_xobjects"] = results["xobject_count"] > 0
        
        except Exception as e:
            results["error"] = f"Error analizando Form XObjects: {str(e)}"
        
        return results
    
    def _analyze_acroform(self) -> Dict[str, Any]:
        """ZONA 4: Analiza campos de formulario (AcroForm)"""
        results = {
            "has_acroform": False,
            "form_fields": [],
            "widget_annotations": [],
            "text_fields": [],
            "overlapping_fields": []
        }
        
        try:
            # Verificar si el documento tiene AcroForm
            if hasattr(self.doc, 'metadata') and self.doc.metadata:
                # Buscar AcroForm en el catálogo
                acroform_info = self._extract_acroform_info()
                
                if acroform_info:
                    results["has_acroform"] = True
                    results["form_fields"] = acroform_info.get("fields", [])
                    
                    # Analizar campos de texto específicamente
                    for field in acroform_info.get("fields", []):
                        if field.get("type") == "text":
                            results["text_fields"].append(field)
                        
                        # Verificar si el campo se superpone con contenido
                        if self._check_field_overlap(field):
                            results["overlapping_fields"].append(field)
        
        except Exception as e:
            results["error"] = f"Error analizando AcroForm: {str(e)}"
        
        return results
    
    def _analyze_advanced_overlay(self) -> Dict[str, Any]:
        """Análisis avanzado de overlay usando la lógica mejorada"""
        try:
            # Usar la función avanzada para cada página
            resultados_paginas = []
            
            for page_num in range(self.doc.page_count):
                resultado_pagina = inspeccionar_overlay_avanzado(
                    self.pdf_bytes, 
                    page_index=page_num
                )
                resultados_paginas.append(resultado_pagina)
            
            # Consolidar resultados
            total_annots = sum(len(p.get("annots", [])) for p in resultados_paginas)
            total_sospechosos = sum(len(p.get("sospechosos", [])) for p in resultados_paginas)
            paginas_con_render_diff = sum(1 for p in resultados_paginas if p.get("render_diff", False))
            
            # Calcular probabilidad de overlay
            probabilidad_overlay = 0.0
            if total_annots > 0:
                probabilidad_overlay += 0.4  # Anotaciones son indicador fuerte
            if total_sospechosos > 0:
                probabilidad_overlay += 0.3  # Elementos sospechosos
            if paginas_con_render_diff > 0:
                probabilidad_overlay += 0.3  # Diferencia visual
            
            # Determinar nivel de riesgo
            if probabilidad_overlay >= 0.7:
                nivel_riesgo = "HIGH"
            elif probabilidad_overlay >= 0.4:
                nivel_riesgo = "MEDIUM"
            else:
                nivel_riesgo = "LOW"
            
            return {
                "total_paginas_analizadas": self.doc.page_count,
                "total_anotaciones": total_annots,
                "total_elementos_sospechosos": total_sospechosos,
                "paginas_con_render_diff": paginas_con_render_diff,
                "probabilidad_overlay": round(probabilidad_overlay, 3),
                "nivel_riesgo": nivel_riesgo,
                "detalles_por_pagina": resultados_paginas,
                "indicadores_clave": {
                    "tiene_anotaciones": total_annots > 0,
                    "tiene_elementos_sospechosos": total_sospechosos > 0,
                    "tiene_diferencia_visual": paginas_con_render_diff > 0,
                    "overlay_detectado": probabilidad_overlay > 0.5
                }
            }
            
        except Exception as e:
            return {"error": f"Error en análisis avanzado: {str(e)}"}
    
    def _analyze_stream_overlay(self) -> Dict[str, Any]:
        """Análisis por stream para detectar overlay con máxima precisión"""
        try:
            resultados_paginas = []
            
            for page_num in range(self.doc.page_count):
                resultado_pagina = localizar_overlay_por_stream(
                    self.pdf_bytes, 
                    page_index=page_num
                )
                resultado_pagina["page"] = page_num + 1
                resultados_paginas.append(resultado_pagina)
            
            # Consolidar resultados
            total_streams = sum(p.get("streams", 0) for p in resultados_paginas)
            paginas_con_overlay = sum(1 for p in resultados_paginas if p.get("detected", False))
            streams_sospechosos = [p for p in resultados_paginas if p.get("overlay_stream") is not None]
            
            # Calcular probabilidad basada en detección por stream
            probabilidad_stream = 0.0
            if total_streams > 0:
                probabilidad_stream = len(streams_sospechosos) / len(resultados_paginas)
            
            # Aplicar factor de contexto para reducir falsos positivos
            factor_contexto = self._calcular_factor_contexto()
            probabilidad_stream *= factor_contexto
            
            # Determinar nivel de riesgo (umbrales ajustados)
            if probabilidad_stream >= 0.6:
                nivel_riesgo = "HIGH"
            elif probabilidad_stream >= 0.3:
                nivel_riesgo = "MEDIUM"
            else:
                nivel_riesgo = "LOW"
            
            return {
                "total_paginas_analizadas": self.doc.page_count,
                "total_streams": total_streams,
                "paginas_con_overlay": paginas_con_overlay,
                "streams_sospechosos": len(streams_sospechosos),
                "probabilidad_overlay": round(probabilidad_stream, 3),
                "nivel_riesgo": nivel_riesgo,
                "threshold_pixels": 0.05,
                "detalles_por_pagina": resultados_paginas,
                "indicadores_clave": {
                    "overlay_detectado": paginas_con_overlay > 0,
                    "tiene_streams_sospechosos": len(streams_sospechosos) > 0,
                    "metodo_mas_preciso": True
                }
            }
            
        except Exception as e:
            return {"error": f"Error en análisis por stream: {str(e)}"}
    
    def _analyze_stack_layers(self) -> Dict[str, Any]:
        """Análisis por capas - método más avanzado y preciso"""
        try:
            resultados_paginas = []
            
            for page_num in range(self.doc.page_count):
                resultado_pagina = stack_compare(
                    self.pdf_bytes, 
                    page_index=page_num
                )
                resultados_paginas.append(resultado_pagina)
            
            # Consolidar resultados
            total_streams = sum(len(p.get("by_stream", [])) for p in resultados_paginas)
            total_annots = sum(len(p.get("by_annot", [])) for p in resultados_paginas)
            total_ocgs = sum(len(p.get("by_ocg", [])) for p in resultados_paginas)
            
            # Contar cambios detectados
            streams_con_cambios = sum(
                sum(1 for s in p.get("by_stream", []) if s.get("changed", False))
                for p in resultados_paginas
            )
            annots_con_cambios = sum(
                sum(1 for a in p.get("by_annot", []) if a.get("changed", False))
                for p in resultados_paginas
            )
            ocgs_con_cambios = sum(
                sum(1 for o in p.get("by_ocg", []) if o.get("changed", False))
                for p in resultados_paginas
            )
            
            # Calcular probabilidad basada en análisis por capas
            total_cambios = streams_con_cambios + annots_con_cambios + ocgs_con_cambios
            total_elementos = total_streams + total_annots + total_ocgs
            
            probabilidad_capas = 0.0
            if total_elementos > 0:
                probabilidad_capas = total_cambios / total_elementos
            
            # Aplicar factor de contexto para reducir falsos positivos
            factor_contexto = self._calcular_factor_contexto()
            probabilidad_capas *= factor_contexto
            
            # Determinar nivel de riesgo (umbrales ajustados)
            if probabilidad_capas >= 0.6:
                nivel_riesgo = "HIGH"
            elif probabilidad_capas >= 0.3:
                nivel_riesgo = "MEDIUM"
            else:
                nivel_riesgo = "LOW"
            
            return {
                "total_paginas_analizadas": self.doc.page_count,
                "total_streams": total_streams,
                "total_annots": total_annots,
                "total_ocgs": total_ocgs,
                "streams_con_cambios": streams_con_cambios,
                "annots_con_cambios": annots_con_cambios,
                "ocgs_con_cambios": ocgs_con_cambios,
                "probabilidad_overlay": round(probabilidad_capas, 3),
                "nivel_riesgo": nivel_riesgo,
                "threshold_pixels": 0.05,
                "detalles_por_pagina": resultados_paginas,
                "indicadores_clave": {
                    "overlay_detectado": total_cambios > 0,
                    "tiene_streams_cambios": streams_con_cambios > 0,
                    "tiene_annots_cambios": annots_con_cambios > 0,
                    "tiene_ocgs_cambios": ocgs_con_cambios > 0,
                    "metodo_mas_avanzado": True
                }
            }
            
        except Exception as e:
            return {"error": f"Error en análisis por capas: {str(e)}"}
    
    def _analyze_images(self) -> Dict[str, Any]:
        """Análisis de imágenes en el PDF para detectar parches sospechosos"""
        return analyze_images(self.doc, self.doc.page_count, self.pdf_bytes)
    
    def _calcular_factor_contexto(self) -> float:
        """
        Calcula un factor de contexto para reducir falsos positivos.
        
        Considera:
        - Fechas de creación y modificación iguales (indica documento original)
        - Número de streams (muy pocos streams pueden ser normales)
        - Metadatos del PDF
        """
        try:
            factor = 1.0  # Factor base
            
            # Verificar fechas de creación y modificación
            if hasattr(self.doc, 'metadata') and self.doc.metadata:
                metadata = dict(self.doc.metadata)
                creation_date = metadata.get('creationDate', '')
                mod_date = metadata.get('modDate', '')
                
                # Si las fechas son iguales, es menos probable que sea editado
                if creation_date and mod_date and creation_date == mod_date:
                    factor *= 0.3  # Reducir significativamente la probabilidad
                
                # Si el productor es conocido (como iText), puede ser normal tener múltiples streams
                producer = metadata.get('producer', '').lower()
                if 'itext' in producer or 'adobe' in producer:
                    factor *= 0.7  # Reducir ligeramente
            
            # Verificar número de streams
            total_streams = 0
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                contents = page.get_contents()
                if contents:
                    if isinstance(contents, list):
                        total_streams += len(contents)
                    else:
                        total_streams += 1
            
            # Si hay muy pocos streams (1-2), es menos sospechoso
            if total_streams <= 2:
                factor *= 0.5
            
            return max(factor, 0.1)  # Mínimo factor de 0.1
            
        except Exception:
            return 1.0  # Si hay error, usar factor neutro
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Genera un resumen general del análisis con la nueva estructura"""
        
        # Obtener análisis de cada método
        analisis_avanzado = self.analysis_results.get("analisis_avanzado_overlay", {})
        analisis_stream = self.analysis_results.get("analisis_por_stream", {})
        analisis_capas = self.analysis_results.get("analisis_por_capas", {})
        analisis_imagenes = self.analysis_results.get("analisis_imagenes", {})
        
        # Calcular probabilidad general (usar la más alta)
        probabilidades = [
            analisis_avanzado.get("probabilidad_overlay", 0.0),
            analisis_stream.get("probabilidad_overlay", 0.0),
            analisis_capas.get("probabilidad_overlay", 0.0),
            analisis_imagenes.get("probabilidad_overlay_imagenes", 0.0)
        ]
        overlay_probability = max(probabilidades) if probabilidades else 0.0
        
        # Determinar nivel de riesgo (umbrales más altos para reducir falsos positivos)
        niveles_riesgo = [
            analisis_avanzado.get("nivel_riesgo", "LOW"),
            analisis_stream.get("nivel_riesgo", "LOW"),
            analisis_capas.get("nivel_riesgo", "LOW"),
            analisis_imagenes.get("nivel_riesgo_imagenes", "LOW")
        ]
        
        # Contar cuántos análisis indican HIGH
        high_count = niveles_riesgo.count("HIGH")
        
        # Lógica más sensible para detectar riesgo
        if high_count >= 1 or overlay_probability >= 0.6:
            risk_level = "HIGH"
            recommendations = ["Alto riesgo de texto superpuesto detectado"]
        elif overlay_probability >= 0.3:
            risk_level = "MEDIUM"
            recommendations = ["Riesgo medio de texto superpuesto"]
        else:
            risk_level = "LOW"
            recommendations = ["Bajo riesgo de texto superpuesto"]
        
        # Contar zonas con overlay
        zones_with_overlay = sum([
            1 for analisis in [analisis_avanzado, analisis_stream, analisis_capas, analisis_imagenes]
            if analisis.get("overlay_detectado", False) or analisis.get("tiene_parches_sospechosos", False)
        ])
        
        # Generar resumen con la nueva estructura
        resumen = {
            "probabilidad_manipulacion": overlay_probability,
            "nivel_riesgo": risk_level,
            "total_zones_analyzed": 8,
            "zones_with_overlay": zones_with_overlay,
            "overlay_probability": overlay_probability,
            "risk_level": risk_level,
            "recommendations": recommendations,
            "analisis_avanzado": {
                "total_anotaciones": analisis_avanzado.get("total_anotaciones", 0),
                "elementos_sospechosos": analisis_avanzado.get("total_elementos_sospechosos", 0),
                "diferencia_visual": analisis_avanzado.get("paginas_con_render_diff", 0),
                "probabilidad_overlay": analisis_avanzado.get("probabilidad_overlay", 0.0)
            },
            "analisis_por_stream": {
                "total_streams": analisis_stream.get("total_streams", 0),
                "streams_sospechosos": analisis_stream.get("streams_sospechosos", 0),
                "paginas_con_overlay": analisis_stream.get("paginas_con_overlay", 0),
                "probabilidad_overlay": analisis_stream.get("probabilidad_overlay", 0.0),
                "threshold_pixels": analisis_stream.get("threshold_pixels", 0.01)
            },
            "analisis_por_capas": {
                "total_streams": analisis_capas.get("total_streams", 0),
                "total_annots": analisis_capas.get("total_annots", 0),
                "total_ocgs": analisis_capas.get("total_ocgs", 0),
                "streams_con_cambios": analisis_capas.get("streams_con_cambios", 0),
                "annots_con_cambios": analisis_capas.get("annots_con_cambios", 0),
                "ocgs_con_cambios": analisis_capas.get("ocgs_con_cambios", 0),
                "probabilidad_overlay": analisis_capas.get("probabilidad_overlay", 0.0),
                "threshold_pixels": analisis_capas.get("threshold_pixels", 0.01)
            }
        }
        
        return resumen
    
    def _extract_pdf_structure(self) -> Dict[str, Any]:
        """Extrae la estructura XML/PDF del documento"""
        structure = {
            "pdf_version": None,
            "page_count": 0,
            "metadata": {},
            "catalog_info": {},
            "xref_info": {}
        }
        
        try:
            # Información básica del PDF
            structure["page_count"] = self.doc.page_count
            
            # Metadatos
            if hasattr(self.doc, 'metadata') and self.doc.metadata:
                structure["metadata"] = dict(self.doc.metadata)
            
            # Información del catálogo (simplificada)
            structure["catalog_info"] = {
                "has_acroform": False,  # Se detectaría en análisis completo
                "has_outline": False,
                "has_pages": True
            }
            
        except Exception as e:
            structure["error"] = f"Error extrayendo estructura: {str(e)}"
        
        return structure
    
    # Métodos auxiliares que necesitan implementación
    def _analyze_content_stream(self, stream_id, page_num: int) -> Dict[str, Any]:
        """Analiza un stream de contenido específico"""
        return {
            "text_commands": [],
            "rectangle_commands": [],
            "color_commands": [],
            "suspicious_sequences": [],
            "overlapping_content": []
        }
    
    def _extract_xobjects_from_page(self, page) -> Dict[str, Dict[str, Any]]:
        """Extrae información de XObjects de una página"""
        return {}
    
    def _is_suspicious_xobject(self, xobj_info: Dict[str, Any]) -> bool:
        """Detecta XObjects sospechosos"""
        return False
    
    def _extract_acroform_info(self) -> Dict[str, Any]:
        """Extrae información del AcroForm del documento"""
        return None
    
    def _check_field_overlap(self, field: Dict[str, Any]) -> bool:
        """Verifica si un campo se superpone con contenido"""
        return False


def detectar_texto_superpuesto_detallado(pdf_base64: str) -> Dict[str, Any]:
    """
    Función principal para detectar texto superpuesto en un PDF.
    
    Args:
        pdf_base64: PDF codificado en base64
        
    Returns:
        Dict con análisis detallado de las 4 zonas de superposición
    """
    try:
        # Decodificar PDF
        pdf_bytes = base64.b64decode(pdf_base64)
        
        # Crear detector y analizar
        detector = TextOverlayDetector(pdf_bytes)
        results = detector.analyze_pdf()
        
        return safe_serialize_dict(results)
        
    except Exception as e:
        return {"error": f"Error procesando PDF: {str(e)}"}
