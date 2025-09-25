"""
Helper para detección de texto superpuesto en PDFs
Migrado desde helpers/deteccion_texto_superpuesto.py a la nueva arquitectura
"""

import re
import base64
import fitz
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
import json
import io
import copy
import numpy as np
from PIL import ImageChops, Image
import pikepdf
import imagehash
import hashlib

# Constantes para análisis por stream
PA = 0.05  # umbral de % de píxeles distintos para decir "hay cambio"
PIX_DIFF_THRESHOLD = 0.05  # 5% de píxeles distintos => consideramos que "cambió"

def _render_png(pdf_bytes: bytes, page_index=0, dpi=144) -> Image.Image:
    """Renderiza una página del PDF como imagen PNG"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_index]
    pix = page.get_pixmap(dpi=dpi)
    doc.close()
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

def _diff_ratio(img_a: Image.Image, img_b: Image.Image) -> float:
    """Calcula el porcentaje de píxeles diferentes entre dos imágenes"""
    if img_a.size != img_b.size:
        return 1.0
    
    diff = ImageChops.difference(img_a, img_b)
    diff_array = np.array(diff)
    total_pixels = diff_array.size
    different_pixels = np.count_nonzero(diff_array)
    
    return different_pixels / total_pixels

def _set_ocg_on_prefix(pdf_bytes: bytes, k: int) -> bytes:
    """Establece el prefijo OCG ON para el stream k"""
    bio = io.BytesIO(pdf_bytes)
    pdf = pikepdf.Pdf.open(bio)
    
    # Buscar el stream k y establecer OCG ON
    for page in pdf.pages:
        if hasattr(page, 'Contents'):
            contents = page.Contents
            if isinstance(contents, list):
                if k < len(contents):
                    stream_obj = contents[k]
                    if hasattr(stream_obj, 'OC'):
                        stream_obj.OC = pikepdf.Name.ON
    
    bio = io.BytesIO()
    pdf.save(bio)
    return bio.getvalue()

def stack_compare(pdf_bytes: bytes, page_index: int = 0, dpi: int = 144) -> Dict[str, Any]:
    """
    Compara la renderización con y sin OCG para detectar overlays
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[page_index]
        
        # Renderizar página normal
        pix_normal = page.get_pixmap(dpi=dpi)
        img_normal = Image.frombytes("RGB", (pix_normal.width, pix_normal.height), pix_normal.samples)
        
        # Buscar streams en la página
        streams = []
        if hasattr(page, 'Contents'):
            contents = page.Contents
            if isinstance(contents, list):
                streams = contents
            else:
                streams = [contents]
        
        results = []
        for k, stream in enumerate(streams):
            try:
                # Crear versión con OCG ON para este stream
                pdf_with_ocg = _set_ocg_on_prefix(pdf_bytes, k)
                
                # Renderizar con OCG ON
                doc_ocg = fitz.open(stream=pdf_with_ocg, filetype="pdf")
                page_ocg = doc_ocg[page_index]
                pix_ocg = page_ocg.get_pixmap(dpi=dpi)
                img_ocg = Image.frombytes("RGB", (pix_ocg.width, pix_ocg.height), pix_ocg.samples)
                doc_ocg.close()
                
                # Comparar imágenes
                diff_ratio = _diff_ratio(img_normal, img_ocg)
                changed = diff_ratio > PIX_DIFF_THRESHOLD
                
                results.append({
                    "k": k,
                    "changed": changed,
                    "diff_ratio": diff_ratio
                })
                
            except Exception as e:
                results.append({
                    "k": k,
                    "changed": False,
                    "diff_ratio": 0.0,
                    "error": str(e)
                })
        
        doc.close()
        
        return {
            "page": page_index,
            "by_stream": results,
            "by_annot": [],  # Se puede implementar después
            "by_ocg": [],    # Se puede implementar después
            "threshold": PIX_DIFF_THRESHOLD,
            "dpi": dpi
        }
        
    except Exception as e:
        return {"error": f"Error en análisis por capas: {str(e)}"}

def localizar_overlay_por_stream(pdf_bytes: bytes, page_index: int = 0) -> Dict[str, Any]:
    """
    Localiza overlays analizando streams individualmente
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[page_index]
        
        # Obtener streams de la página
        streams = []
        if hasattr(page, 'Contents'):
            contents = page.Contents
            if isinstance(contents, list):
                streams = contents
            else:
                streams = [contents]
        
        # Analizar cada stream
        stream_analysis = []
        for k, stream in enumerate(streams):
            try:
                # Obtener contenido del stream
                if hasattr(stream, 'get_data'):
                    stream_data = stream.get_data()
                else:
                    stream_data = b""
                
                # Buscar patrones sospechosos
                suspicious_patterns = [
                    b"/OC",
                    b"/XObject",
                    b"/Form",
                    b"/Group",
                    b"/Transparency"
                ]
                
                pattern_matches = []
                for pattern in suspicious_patterns:
                    if pattern in stream_data:
                        pattern_matches.append(pattern.decode('utf-8', errors='ignore'))
                
                stream_analysis.append({
                    "stream_id": k,
                    "size_bytes": len(stream_data),
                    "suspicious_patterns": pattern_matches,
                    "has_overlay_indicators": len(pattern_matches) > 0
                })
                
            except Exception as e:
                stream_analysis.append({
                    "stream_id": k,
                    "error": str(e),
                    "has_overlay_indicators": False
                })
        
        doc.close()
        
        return {
            "page": page_index,
            "total_streams": len(streams),
            "stream_analysis": stream_analysis,
            "overlay_detected": any(s.get("has_overlay_indicators", False) for s in stream_analysis)
        }
        
    except Exception as e:
        return {"error": f"Error en análisis por stream: {str(e)}"}

def inspeccionar_overlay_avanzado(pdf_bytes: bytes, page_index: int = 0, buscar_texto: str = None) -> Dict[str, Any]:
    """
    Inspección avanzada de overlays usando múltiples técnicas
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[page_index]
        
        # Análisis de anotaciones
        annotations = []
        if hasattr(page, 'annots'):
            for annot in page.annots():
                annotations.append({
                    "type": annot.type[1] if annot.type else "unknown",
                    "rect": list(annot.rect),
                    "content": annot.content or "",
                    "suspicious": "overlay" in (annot.content or "").lower()
                })
        
        # Análisis de contenido de la página
        page_contents = []
        if hasattr(page, 'Contents'):
            contents = page.Contents
            if isinstance(contents, list):
                for i, content in enumerate(contents):
                    try:
                        if hasattr(content, 'get_data'):
                            data = content.get_data()
                            page_contents.append({
                                "stream_id": i,
                                "size": len(data),
                                "has_ocg": b"/OC" in data,
                                "has_transparency": b"/Transparency" in data
                            })
                    except:
                        pass
        
        # Buscar elementos sospechosos
        suspicious_elements = []
        if buscar_texto:
            # Buscar texto específico en la página
            text_instances = page.search_for(buscar_texto)
            for rect in text_instances:
                suspicious_elements.append({
                    "type": "text_match",
                    "bbox": list(rect),
                    "text": buscar_texto
                })
        
        # Análisis de renderización
        pix = page.get_pixmap(dpi=144)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        
        # Detectar diferencias visuales (simplificado)
        render_diff = False
        if len(page_contents) > 1:
            # Si hay múltiples streams, podría haber overlays
            render_diff = True
        
        doc.close()
        
        return {
            "page": page_index,
            "annotations": annotations,
            "page_contents": page_contents,
            "suspicious_elements": suspicious_elements,
            "render_diff": render_diff,
            "overlay_probability": len(suspicious_elements) / max(1, len(page_contents))
        }
        
    except Exception as e:
        return {"error": f"Error en inspección avanzada: {str(e)}"}

def inventariar_imagenes(pdf_bytes: bytes, page_index: int = 0) -> Dict[str, Any]:
    """
    Inventaria imágenes en la página para detectar overlays
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[page_index]
        
        # Obtener imágenes de la página
        image_list = page.get_images()
        images = []
        
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    images.append({
                        "index": img_index,
                        "xref": xref,
                        "width": pix.width,
                        "height": pix.height,
                        "colorspace": pix.colorspace.name if pix.colorspace else "unknown",
                        "size_bytes": len(pix.tobytes()),
                        "suspicious": pix.width < 50 or pix.height < 50  # Imágenes muy pequeñas
                    })
                
                pix = None
                
            except Exception as e:
                images.append({
                    "index": img_index,
                    "error": str(e),
                    "suspicious": False
                })
        
        doc.close()
        
        return {
            "page": page_index,
            "total_images": len(images),
            "images": images,
            "suspicious_images": [img for img in images if img.get("suspicious", False)]
        }
        
    except Exception as e:
        return {"error": f"Error inventariando imágenes: {str(e)}"}

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
            
            # Análisis avanzado de overlay
            self.analysis_results["analisis_avanzado_overlay"] = self._analyze_advanced_overlay()
            
            # Análisis por stream (método más preciso)
            self.analysis_results["analisis_por_stream"] = self._analyze_stream_overlay()
            
            # Análisis por capas (método más avanzado)
            self.analysis_results["analisis_por_capas"] = self._analyze_stack_layers()
            
            # Análisis de imágenes
            self.analysis_results["analisis_imagenes"] = self._analyze_images()
            
            # Generar resumen general
            self.analysis_results["resumen_general"] = self._generate_summary()
            
            # Extraer XML/estructura del PDF
            self.analysis_results["xml_estructura"] = self._extract_pdf_structure()
            
            return self.analysis_results
            
        except Exception as e:
            return {"error": f"Error en análisis PDF: {str(e)}"}
        finally:
            if self.doc:
                self.doc.close()
    
    def _analyze_annotations(self) -> Dict[str, Any]:
        """Analiza anotaciones en el PDF"""
        try:
            total_annotations = 0
            suspicious_annotations = []
            
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                # Usar el método correcto para iterar anotaciones
                a = page.first_annot
                while a:
                    total_annotations += 1
                    # Obtener contenido usando el método correcto
                    content = ""
                    try:
                        if hasattr(a, 'info') and a.info:
                            content = a.info.get("content", "")
                        elif hasattr(a, 'content'):
                            content = a.content or ""
                        else:
                            # Intentar obtener el contenido de otras formas
                            content = str(a) if a else ""
                    except Exception:
                        content = ""
                    
                    if "overlay" in content.lower():
                        suspicious_annotations.append({
                            "page": page_num,
                            "type": a.type[1] if a.type else "unknown",
                            "content": content
                        })
                    
                    a = a.next
            
            return {
                "total_annotations": total_annotations,
                "suspicious_annotations": suspicious_annotations,
                "has_suspicious": len(suspicious_annotations) > 0
            }
            
        except Exception as e:
            return {"error": f"Error analizando anotaciones: {str(e)}"}
    
    def _analyze_page_contents(self) -> Dict[str, Any]:
        """Analiza contenido de las páginas"""
        try:
            total_streams = 0
            streams_with_ocg = 0
            
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                if hasattr(page, 'Contents'):
                    contents = page.Contents
                    if isinstance(contents, list):
                        total_streams += len(contents)
                        for content in contents:
                            try:
                                if hasattr(content, 'get_data'):
                                    data = content.get_data()
                                    if b"/OC" in data:
                                        streams_with_ocg += 1
                            except:
                                pass
            
            return {
                "total_streams": total_streams,
                "streams_with_ocg": streams_with_ocg,
                "ocg_percentage": streams_with_ocg / max(1, total_streams)
            }
            
        except Exception as e:
            return {"error": f"Error analizando contenido: {str(e)}"}
    
    def _analyze_form_xobjects(self) -> Dict[str, Any]:
        """Analiza Form XObjects"""
        try:
            total_forms = 0
            suspicious_forms = []
            
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                try:
                    if hasattr(page, 'get_xobjects'):
                        xobjects = page.get_xobjects()
                        # Verificar si xobjects es un diccionario o una lista
                        if isinstance(xobjects, dict):
                            for name, xobj in xobjects.items():
                                if isinstance(xobj, dict) and xobj.get("Subtype") == "/Form":
                                    total_forms += 1
                                    if "overlay" in name.lower():
                                        suspicious_forms.append({
                                            "page": page_num,
                                            "name": name,
                                            "xobj": xobj
                                        })
                        elif isinstance(xobjects, list):
                            # Si es una lista, iterar sobre ella
                            for i, xobj in enumerate(xobjects):
                                if isinstance(xobj, dict) and xobj.get("Subtype") == "/Form":
                                    total_forms += 1
                                    name = f"xobject_{i}"
                                    if "overlay" in name.lower():
                                        suspicious_forms.append({
                                            "page": page_num,
                                            "name": name,
                                            "xobj": xobj
                                        })
                except Exception as page_error:
                    # Continuar con la siguiente página si hay error
                    continue
            
            return {
                "total_forms": total_forms,
                "suspicious_forms": suspicious_forms,
                "has_suspicious": len(suspicious_forms) > 0
            }
            
        except Exception as e:
            return {"error": f"Error analizando Form XObjects: {str(e)}"}
    
    def _analyze_acroform(self) -> Dict[str, Any]:
        """Analiza campos de formulario AcroForm"""
        try:
            if hasattr(self.doc, 'metadata'):
                metadata = self.doc.metadata
                has_acroform = "AcroForm" in str(metadata)
            else:
                has_acroform = False
            
            return {
                "has_acroform": has_acroform,
                "suspicious_fields": []
            }
            
        except Exception as e:
            return {"error": f"Error analizando AcroForm: {str(e)}"}
    
    def _analyze_advanced_overlay(self) -> Dict[str, Any]:
        """Análisis avanzado de overlay"""
        try:
            total_pages = self.doc.page_count
            total_annotations = 0
            total_suspicious = 0
            pages_with_render_diff = 0
            total_probability = 0.0
            
            details_by_page = []
            
            for page_num in range(total_pages):
                # Usar la función de inspección avanzada
                result = inspeccionar_overlay_avanzado(self.pdf_bytes, page_num)
                
                if "error" not in result:
                    total_annotations += len(result.get("annots", []))
                    total_suspicious += len(result.get("sospechosos", []))
                    if result.get("render_diff", False):
                        pages_with_render_diff += 1
                    
                    # Calcular probabilidad basada en la presencia de elementos sospechosos
                    page_probability = 0.0
                    if result.get("annots"):
                        page_probability += 0.3
                    if result.get("render_diff"):
                        page_probability += 0.4
                    if result.get("sospechosos"):
                        page_probability += 0.3
                    
                    total_probability += page_probability
                    
                    details_by_page.append({
                        "page": page_num + 1,  # +1 para que coincida con el formato original
                        "annots": result.get("annots", []),
                        "render_diff": result.get("render_diff", False),
                        "sospechosos": result.get("sospechosos", []),
                        "contents_tail": result.get("contents_tail", ""),
                        "matches": result.get("matches", [])
                    })
            
            # Calcular probabilidad promedio
            avg_probability = total_probability / max(1, total_pages)
            
            # Determinar nivel de riesgo
            if avg_probability > 0.7:
                risk_level = "HIGH"
            elif avg_probability > 0.3:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            return {
                "total_paginas_analizadas": total_pages,
                "total_anotaciones": total_annotations,
                "total_elementos_sospechosos": total_suspicious,
                "paginas_con_render_diff": pages_with_render_diff,
                "probabilidad_overlay": avg_probability,
                "nivel_riesgo": risk_level,
                "detalles_por_pagina": details_by_page,
                "indicadores_clave": {
                    "tiene_anotaciones": total_annotations > 0,
                    "tiene_elementos_sospechosos": total_suspicious > 0,
                    "tiene_diferencia_visual": pages_with_render_diff > 0,
                    "overlay_detectado": avg_probability > 0.3
                }
            }
            
        except Exception as e:
            return {"error": f"Error en análisis avanzado: {str(e)}"}
    
    def _analyze_stream_overlay(self) -> Dict[str, Any]:
        """Análisis por stream - método más preciso"""
        try:
            total_streams = 0
            streams_with_changes = 0
            pages_with_overlay = 0
            total_probability = 0.0
            
            for page_num in range(self.doc.page_count):
                result = localizar_overlay_por_stream(self.pdf_bytes, page_num)
                
                if "error" not in result:
                    total_streams += result.get("total_streams", 0)
                    if result.get("overlay_detected", False):
                        pages_with_overlay += 1
                        streams_with_changes += 1
                    
                    # Calcular probabilidad para esta página
                    page_streams = result.get("total_streams", 0)
                    if page_streams > 0:
                        page_probability = streams_with_changes / page_streams
                        total_probability += page_probability
            
            avg_probability = total_probability / max(1, self.doc.page_count)
            
            return {
                "total_streams": total_streams,
                "streams_con_cambios": streams_with_changes,
                "paginas_con_overlay": pages_with_overlay,
                "probabilidad_overlay": avg_probability,
                "threshold_pixels": PIX_DIFF_THRESHOLD
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
            if probabilidad_capas > 0.5:
                nivel_riesgo = "HIGH"
            elif probabilidad_capas > 0.2:
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
                "probabilidad_overlay": probabilidad_capas,
                "nivel_riesgo": nivel_riesgo,
                "threshold_pixels": PIX_DIFF_THRESHOLD,
                "detalles_por_pagina": resultados_paginas,
                "indicadores_clave": {
                    "overlay_detectado": probabilidad_capas > 0.2,
                    "tiene_streams_cambios": streams_con_cambios > 0,
                    "tiene_annots_cambios": annots_con_cambios > 0,
                    "tiene_ocgs_cambios": ocgs_con_cambios > 0,
                    "metodo_mas_avanzado": True
                }
            }
            
        except Exception as e:
            return {"error": f"Error en análisis por capas: {str(e)}"}
    
    def _analyze_images(self) -> Dict[str, Any]:
        """Análisis de imágenes para detectar overlays"""
        try:
            total_pages = self.doc.page_count
            total_images = 0
            total_suspicious_patches = 0
            total_bytes_images = 0
            total_probability = 0.0
            
            detalles_por_pagina = []
            
            for page_num in range(total_pages):
                result = inventariar_imagenes(self.pdf_bytes, page_num)
                
                if "error" not in result:
                    page_images = result.get("images", [])
                    suspicious_images = result.get("suspicious_images", [])
                    
                    total_images += len(page_images)
                    total_suspicious_patches += len(suspicious_images)
                    
                    page_bytes = sum(img.get("size_bytes", 0) for img in page_images)
                    total_bytes_images += page_bytes
                    
                    # Calcular probabilidad para esta página
                    if len(page_images) > 0:
                        page_probability = len(suspicious_images) / len(page_images)
                        total_probability += page_probability
                    
                    detalles_por_pagina.append({
                        "pagina": page_num + 1,
                        "total_imagenes": len(page_images),
                        "parches_sospechosos": len(suspicious_images),
                        "bytes_imagenes": page_bytes,
                        "imagenes": page_images,
                        "indicadores_sospechosos": {
                            "tiene_parches": len(suspicious_images) > 0,
                            "imagenes_pequenas": any(img.get("width", 0) < 50 for img in page_images),
                            "imagenes_uniformes": len(set(img.get("colorspace", "") for img in page_images)) == 1,
                            "imagenes_rectangulares": all(img.get("width", 0) > img.get("height", 0) for img in page_images)
                        }
                    })
            
            avg_probability = total_probability / max(1, total_pages)
            
            # Determinar nivel de riesgo
            if avg_probability > 0.6:
                nivel_riesgo = "HIGH"
            elif avg_probability > 0.3:
                nivel_riesgo = "MEDIUM"
            else:
                nivel_riesgo = "LOW"
            
            return {
                "total_paginas_analizadas": total_pages,
                "total_imagenes": total_images,
                "total_parches_sospechosos": total_suspicious_patches,
                "total_bytes_imagenes": total_bytes_images,
                "probabilidad_overlay_imagenes": avg_probability,
                "nivel_riesgo_imagenes": nivel_riesgo,
                "detalles_por_pagina": detalles_por_pagina,
                "indicadores_clave": {
                    "tiene_imagenes": total_images > 0,
                    "tiene_parches_sospechosos": total_suspicious_patches > 0,
                    "imagenes_pequenas_detectadas": any(
                        any(img.get("width", 0) < 50 for img in page.get("imagenes", []))
                        for page in detalles_por_pagina
                    ),
                    "imagenes_uniformes_detectadas": any(
                        len(set(img.get("colorspace", "") for img in page.get("imagenes", []))) == 1
                        for page in detalles_por_pagina
                    )
                }
            }
            
        except Exception as e:
            return {"error": f"Error analizando imágenes: {str(e)}"}
    
    def _calcular_factor_contexto(self) -> float:
        """Calcula factor de contexto para reducir falsos positivos"""
        try:
            # Factor basado en el número de páginas
            if self.doc.page_count <= 1:
                return 0.5  # PDFs de una página son más sospechosos
            elif self.doc.page_count <= 3:
                return 0.8
            else:
                return 1.0  # PDFs largos son menos sospechosos
        except:
            return 1.0
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Genera resumen general del análisis"""
        try:
            # Obtener resultados de todos los análisis
            analisis_avanzado = self.analysis_results.get("analisis_avanzado_overlay", {})
            analisis_stream = self.analysis_results.get("analisis_por_stream", {})
            analisis_capas = self.analysis_results.get("analisis_por_capas", {})
            analisis_imagenes = self.analysis_results.get("analisis_imagenes", {})
            
            # Calcular probabilidad general (promedio ponderado)
            probabilidades = [
                analisis_avanzado.get("probabilidad_overlay", 0.0),
                analisis_stream.get("probabilidad_overlay", 0.0),
                analisis_capas.get("probabilidad_overlay", 0.0),
                analisis_imagenes.get("probabilidad_overlay_imagenes", 0.0)
            ]
            
            probabilidad_general = sum(probabilidades) / len(probabilidades)
            
            # Determinar nivel de riesgo general
            if probabilidad_general > 0.6:
                nivel_riesgo_general = "HIGH"
            elif probabilidad_general > 0.3:
                nivel_riesgo_general = "MEDIUM"
            else:
                nivel_riesgo_general = "LOW"
            
            return {
                "probabilidad_general": probabilidad_general,
                "nivel_riesgo_general": nivel_riesgo_general,
                "metodos_utilizados": [
                    "analisis_avanzado_overlay",
                    "analisis_por_stream", 
                    "analisis_por_capas",
                    "analisis_imagenes"
                ],
                "confiabilidad": "alta" if len([p for p in probabilidades if p > 0]) > 1 else "media"
            }
            
        except Exception as e:
            return {"error": f"Error generando resumen: {str(e)}"}
    
    def _extract_pdf_structure(self) -> Dict[str, Any]:
        """Extrae estructura XML/PDF del documento"""
        try:
            # Información básica del PDF
            metadata = self.doc.metadata or {}
            
            return {
                "page_count": self.doc.page_count,
                "metadata": metadata,
                "has_acroform": "AcroForm" in str(metadata),
                "pdf_version": getattr(self.doc, 'pdf_version', "unknown")
            }
            
        except Exception as e:
            return {"error": f"Error extrayendo estructura: {str(e)}"}

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
        
        return results
        
    except Exception as e:
        return {"error": f"Error procesando PDF: {str(e)}"}
