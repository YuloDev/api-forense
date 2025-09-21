import base64
import io
import re
import time
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from difflib import SequenceMatcher
import requests

from config import (
    MAX_PDF_BYTES,
    SRI_TIMEOUT,
    PRICE_EPS,
    QTY_EPS,
    TOTAL_EPS,
    MATCH_THRESHOLD,
)
from utils import log_step, normalize_comprobante_xml, strip_accents, _to_float
from helpers.type_conversion import safe_serialize_dict
from helpers.analisis_imagenes import analizar_imagen_completa, detectar_tipo_archivo
from helpers.analisis_forense_avanzado import analisis_forense_completo
from helpers.forensics_avanzado import analizar_forensics_avanzado
from helpers.invoice_capture_parser import parse_capture_from_bytes
from helpers.sri_validator import integrar_validacion_sri
from sri import sri_autorizacion_por_clave, parse_autorizacion_response
from PIL import ExifTags

router = APIRouter()

# --- Utilidades para extracción de fechas ---

def _try_parse_date(s: str) -> Optional[str]:
    """Devuelve ISO-8601 si puede parsear s; si no, None."""
    if not s:
        return None
    s = s.strip()
    # Formato EXIF clásico: 'YYYY:MM:DD HH:MM:SS'
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s[:19], fmt).replace(tzinfo=None)
            return dt.isoformat()
        except Exception:
            pass
    # ISO con zona: 2025-09-16T18:54:33-05:00
    try:
        # Normaliza 'YYYY-MM-DDTHH:MM:SS±HH:MM'
        if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$", s):
            s2 = s[:-3] + s[-2:]  # quita ':' de la zona para fromisoformat() viejo
            return datetime.fromisoformat(s2).isoformat()
        return datetime.fromisoformat(s).isoformat()
    except Exception:
        return None

def _exif_to_dict(exif) -> Dict[str, Any]:
    """Convierte EXIF de PIL a dict legible {tag_name: value}."""
    if not exif:
        return {}
    tagmap = {v: k for k, v in ExifTags.TAGS.items()}
    out = {}
    for tag_id, val in exif.items():
        name = ExifTags.TAGS.get(tag_id, str(tag_id))
        # Bytes → str seguro
        if isinstance(val, bytes):
            try:
                val = val.decode("utf-8", "ignore")
            except Exception:
                val = repr(val)
        out[name] = val
    return out

def _extract_xmp_dict(img_bytes: bytes) -> Dict[str, str]:
    """Extrae XMP básico (CreateDate/ModifyDate/DateTimeOriginal) si viene embebido."""
    start = img_bytes.find(b"<x:xmpmeta")
    if start == -1:
        return {}
    end = img_bytes.find(b"</x:xmpmeta>")
    if end == -1:
        return {}
    xmp_xml = img_bytes[start:end + len(b"</x:xmpmeta>")]
    try:
        root = ET.fromstring(xmp_xml)
    except Exception:
        return {}
    # Recolecta atributos típicos en <rdf:Description>
    ns_xmp = "http://ns.adobe.com/xap/1.0/"
    ns_exif = "http://ns.adobe.com/exif/1.0/"
    ns_ps = "http://ns.adobe.com/photoshop/1.0/"
    nsmap = {"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}
    data = {}
    for desc in root.findall(".//rdf:Description", nsmap):
        for k, v in desc.attrib.items():
            if any(ns in k for ns in (ns_xmp, ns_exif, ns_ps)):
                key = k.split("}")[-1]  # último segmento: CreateDate, ModifyDate, etc.
                data[key] = v
    return data

def _extraer_fechas_metadatos(exif_data: Dict[str, Any], xmp_data: Dict[str, str], basicos_data: Dict[str, Any] = None) -> Tuple[Optional[datetime], Optional[datetime], str]:
    """
    Extrae fechas de creación y modificación de metadatos EXIF, XMP y básicos.
    
    Returns:
        Tuple[fecha_creacion, fecha_modificacion, fuente_fechas]
    """
    fecha_creacion = None
    fecha_modificacion = None
    fuente_fechas = "No disponible"
    
    # Mapea campos de interés
    exif_dt_original = _try_parse_date(exif_data.get("DateTimeOriginal") or exif_data.get("DateTime"))
    exif_dt_digitized = _try_parse_date(exif_data.get("DateTimeDigitized"))
    exif_dt_modify = _try_parse_date(exif_data.get("DateTime"))
    
    xmp_create = _try_parse_date(xmp_data.get("CreateDate") or xmp_data.get("DateCreated"))
    xmp_modify = _try_parse_date(xmp_data.get("ModifyDate") or xmp_data.get("MetadataDate"))
    xmp_original = _try_parse_date(xmp_data.get("DateTimeOriginal"))
    
    # Prioridad para fecha de creación: EXIF DateTimeOriginal > XMP CreateDate > EXIF DateTimeDigitized
    if exif_dt_original:
        fecha_creacion = datetime.fromisoformat(exif_dt_original)
        fuente_fechas = "EXIF"
    elif xmp_create:
        fecha_creacion = datetime.fromisoformat(xmp_create)
        fuente_fechas = "XMP"
    elif exif_dt_digitized:
        fecha_creacion = datetime.fromisoformat(exif_dt_digitized)
        fuente_fechas = "EXIF"
    
    # Prioridad para fecha de modificación: EXIF DateTime > XMP ModifyDate
    if exif_dt_modify:
        fecha_modificacion = datetime.fromisoformat(exif_dt_modify)
        if fuente_fechas == "No disponible":
            fuente_fechas = "EXIF"
    elif xmp_modify:
        fecha_modificacion = datetime.fromisoformat(xmp_modify)
        if fuente_fechas == "No disponible":
            fuente_fechas = "XMP"
    
    # Si no hay fechas en metadatos, no inventar fechas
    if not fecha_creacion and not fecha_modificacion:
        # Para imágenes sin metadatos, no hay fechas reales disponibles
        fecha_creacion = None
        fecha_modificacion = None
        fuente_fechas = "No disponible"
    
    return fecha_creacion, fecha_modificacion, fuente_fechas


class PeticionImagen(BaseModel):
    imagen_base64: str


def _extraer_texto_imagen(imagen_bytes: bytes) -> str:
    """
    Extrae texto de una imagen usando OCR.
    """
    try:
        import pytesseract
        from PIL import Image, ExifTags
        
        # Abrir imagen
        img = Image.open(io.BytesIO(imagen_bytes))
        
        # Aplicar OCR
        texto = pytesseract.image_to_string(img, lang='spa+eng')
        
        return texto.strip()
        
    except ImportError:
        # Si no hay pytesseract, retornar texto vacío
        return ""
    except Exception as e:
        print(f"Error en OCR: {e}")
        return ""


def _extraer_campos_factura_imagen(texto: str) -> Dict[str, Any]:
    """
    Extrae campos de factura del texto OCR de una imagen.
    """
    campos = {
        "ruc": None,
        "razonSocial": None,
        "fechaEmision": None,
        "importeTotal": None,
        "claveAcceso": None,
        "detalles": []
    }
    
    try:
        # Patrones para extraer información
        patrones = {
            "ruc": [
                r"RUC[:\s]*(\d{13})",
                r"R\.U\.C[:\s]*(\d{13})",
                r"(\d{13})",
            ],
            "razonSocial": [
                r"Razón Social[:\s]*([^\n]+)",
                r"Razon Social[:\s]*([^\n]+)",
                r"Empresa[:\s]*([^\n]+)",
            ],
            "fechaEmision": [
                r"Fecha[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
                r"Emisión[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            ],
            "importeTotal": [
                r"Total[:\s]*\$?(\d+[.,]\d{2})",
                r"Importe Total[:\s]*\$?(\d+[.,]\d{2})",
                r"Valor Total[:\s]*\$?(\d+[.,]\d{2})",
            ],
            "claveAcceso": [
                r"Clave de Acceso[:\s]*(\d{49})",
                r"Clave Acceso[:\s]*(\d{49})",
                r"(\d{49})",
            ]
        }
        
        # Extraer cada campo
        for campo, patrones_campo in patrones.items():
            for patron in patrones_campo:
                match = re.search(patron, texto, re.IGNORECASE)
                if match:
                    valor = match.group(1).strip()
                    if campo == "importeTotal":
                        # Limpiar y convertir a float
                        valor_limpio = re.sub(r'[^\d.,]', '', valor)
                        valor_limpio = valor_limpio.replace(',', '.')
                        try:
                            campos[campo] = float(valor_limpio)
                        except:
                            pass
                    else:
                        campos[campo] = valor
                    break
        
        # Extraer detalles de productos (básico)
        lineas = texto.split('\n')
        for linea in lineas:
            # Buscar líneas que parezcan productos
            if re.search(r'\d+[.,]\d{2}', linea) and len(linea.strip()) > 10:
                # Intentar extraer cantidad, descripción y precio
                match = re.search(r'(\d+)\s+([^$]+?)\s+\$?(\d+[.,]\d{2})', linea)
                if match:
                    cantidad, descripcion, precio = match.groups()
                    try:
                        precio_limpio = float(precio.replace(',', '.'))
                        campos["detalles"].append({
                            "cantidad": int(cantidad),
                            "descripcion": descripcion.strip(),
                            "precioTotal": precio_limpio
                        })
                    except:
                        pass
        
        return campos
        
    except Exception as e:
        print(f"Error extrayendo campos: {e}")
        return campos


def _evaluar_riesgo_imagen(imagen_bytes: bytes, texto_extraido: str, campos_factura: Dict[str, Any], 
                          analisis_forense: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evalúa el riesgo de una imagen de factura usando la misma estructura que el PDF.
    """
    try:
        score = 0
        prioritarias = []
        secundarias = []
        adicionales = []
        
        # 1. JavaScript embebido (no aplica para imágenes) - ADICIONAL
        adicionales.append({
            "check": "JavaScript embebido",
            "detalle": {
                "aplicable": False,
                "explicacion": "Las imágenes no pueden contener código JavaScript embebido",
                "tipo_archivo": "imagen",
                "recomendacion": "Este check no es aplicable para archivos de imagen"
            },
            "penalizacion": 0
        })
        
        # 2. Validar fecha de creación vs fecha de modificación (PRIORITARIO)
        metadatos = analisis_forense.get("metadatos", {})
        exif_data = metadatos.get("exif", {})
        xmp_data = metadatos.get("xmp", {})
        basicos_data = metadatos.get("basicos", {})
        
        # Extraer fechas usando la lógica robusta
        fecha_creacion, fecha_modificacion, fuente_fechas = _extraer_fechas_metadatos(exif_data, xmp_data, basicos_data)
        
        # Calcular diferencia en días
        penalizacion_fechas = 0
        diferencia_dias = 0
        
        # Solo penalizar si hay metadatos reales y hay diferencia
        if fecha_creacion and fecha_modificacion and fuente_fechas not in ["No disponible"]:
            diferencia_dias = abs((fecha_modificacion - fecha_creacion).days)
            if diferencia_dias > 0:
                penalizacion_fechas = 12  # Según risk_weights.json: "fecha_mod_vs_creacion": 12
                score += penalizacion_fechas
        elif fecha_creacion and fecha_modificacion:
            # Calcular diferencia pero no penalizar si no hay metadatos reales
            diferencia_dias = abs((fecha_modificacion - fecha_creacion).days)
        
        # Determinar si hay metadatos disponibles
        tiene_metadatos_exif = bool(exif_data)
        tiene_metadatos_xmp = bool(xmp_data)
        
        # 2.1. Validación SRI (PRIORITARIO)
        validacion_sri = campos_factura.get("validacion_sri", {})
        sri_verificado = campos_factura.get("sri_verificado", False)
        clave_acceso = campos_factura.get("claveAcceso", "")
        
        penalizacion_sri = 0
        if not sri_verificado and clave_acceso:
            penalizacion_sri = 25  # Penalización alta por SRI no verificado
            score += penalizacion_sri
        elif not clave_acceso:
            penalizacion_sri = 15  # Penalización media por falta de clave de acceso
            score += penalizacion_sri
        
        prioritarias.append({
            "check": "Validación SRI",
            "detalle": {
                "sri_verificado": sri_verificado,
                "clave_acceso": clave_acceso,
                "clave_valida": validacion_sri.get("valido", False),
                "estado_sri": validacion_sri.get("consulta_sri", {}).get("estado", "No disponible"),
                "fecha_autorizacion": validacion_sri.get("consulta_sri", {}).get("fecha_autorizacion", "No disponible"),
                "ruc_emisor": validacion_sri.get("componentes", {}).get("ruc_emisor", "No disponible"),
                "tipo_comprobante": validacion_sri.get("componentes", {}).get("tipo_comprobante", "No disponible"),
                "serie": validacion_sri.get("componentes", {}).get("serie", "No disponible"),
                "secuencial": validacion_sri.get("componentes", {}).get("secuencial", "No disponible"),
                "interpretacion": "Factura validada exitosamente con SRI" if sri_verificado else "Factura no validada con SRI - posible documento falso",
                "posibles_causas": [
                    "Documento no autorizado por SRI",
                    "Clave de acceso inválida o corrupta",
                    "Documento modificado después de autorización",
                    "Error en extracción de datos",
                    "Documento de prueba o borrador"
                ] if not sri_verificado else [
                    "Documento válido según SRI",
                    "Clave de acceso correcta",
                    "Autorización vigente"
                ],
                "indicadores_clave": [
                    f"SRI Verificado: {'Sí' if sri_verificado else 'No'}",
                    f"Clave Acceso: {clave_acceso[:10]}..." if clave_acceso else "No disponible",
                    f"Estado SRI: {validacion_sri.get('consulta_sri', {}).get('estado', 'No disponible')}",
                    f"RUC Emisor: {validacion_sri.get('componentes', {}).get('ruc_emisor', 'No disponible')}",
                    f"Tipo: {validacion_sri.get('componentes', {}).get('tipo_comprobante', 'No disponible')}"
                ],
                "recomendacion": "Documento válido según SRI - verificar autenticidad del canal de origen" if sri_verificado else "Documento no validado con SRI - alto riesgo de falsificación"
            },
            "penalizacion": penalizacion_sri
        })
        
        prioritarias.append({
            "check": "Fecha de modificación vs fecha de creación",
            "detalle": {
                "fecha_creacion": fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if fecha_creacion else "No disponible",
                "fecha_modificacion": fecha_modificacion.strftime("%Y-%m-%d %H:%M:%S") if fecha_modificacion else "No disponible",
                "diferencia_dias": diferencia_dias,
                "fuente_fechas": fuente_fechas,
                "tiene_metadatos_exif": tiene_metadatos_exif,
                "tiene_metadatos_xmp": tiene_metadatos_xmp,
                "campos_exif_encontrados": list(exif_data.keys()) if exif_data else [],
                "campos_xmp_encontrados": list(xmp_data.keys()) if xmp_data else [],
                "interpretacion": "Diferencia entre fechas de creación y modificación puede indicar edición posterior" if fuente_fechas not in ["No disponible"] else "Imagen sin metadatos temporales - no se puede validar fechas de creación/modificación",
                "posibles_causas": [
                    "Imagen editada después de su creación original",
                    "Re-guardado con software diferente",
                    "Aplicación de filtros o efectos",
                    "Modificación de metadatos",
                    "Transferencia entre dispositivos"
                ] if fuente_fechas not in ["No disponible"] else [
                    "Imagen sin metadatos EXIF/XMP",
                    "Procesamiento que eliminó metadatos",
                    "Conversión de formato que perdió metadatos",
                    "Imagen generada por software que no guarda metadatos",
                    "Formato PNG no incluye metadatos temporales por defecto"
                ],
                "indicadores_clave": [
                    f"Diferencia: {diferencia_dias} días" if fecha_creacion and fecha_modificacion else "Fechas no disponibles",
                    f"Creación: {fecha_creacion.strftime('%Y-%m-%d %H:%M:%S')}" if fecha_creacion else "No disponible",
                    f"Modificación: {fecha_modificacion.strftime('%Y-%m-%d %H:%M:%S')}" if fecha_modificacion else "No disponible",
                    f"Fuente: {fuente_fechas}",
                    f"Metadatos EXIF: {'Sí' if tiene_metadatos_exif else 'No'}",
                    f"Metadatos XMP: {'Sí' if tiene_metadatos_xmp else 'No'}"
                ],
                "recomendacion": "Verificar si la diferencia temporal es justificable y revisar metadatos EXIF/XMP" if fuente_fechas not in ["No disponible"] else "Imagen sin metadatos temporales - considerar análisis forense alternativo para validar autenticidad"
            },
            "penalizacion": penalizacion_fechas
        })
        
        # 2.3. Análisis forense - Ruido y bordes (PRIORITARIO)
        from helpers.ruido_bordes_analisis import analizar_ruido_y_bordes
        
        # Realizar análisis robusto de ruido y bordes
        try:
            ruido_analisis = analizar_ruido_y_bordes(imagen_bytes)
        except Exception as e:
            print(f"Error en análisis de ruido y bordes: {e}")
            ruido_analisis = {
                "tiene_edicion_local": False,
                "nivel_sospecha": "BAJO",
                "laplacian_variance_global": 0,
                "edge_density_global": 0,
                "outliers": {"ratio": 0},
                "clusters": {"localized": 0},
                "halo_ratio": 0,
                "lines": {"total": 0, "parallel_groups": 0, "in_cluster_ratio": 0}
            }
        
        penalizacion_ruido = 0
        if ruido_analisis.get("tiene_edicion_local", False):
            penalizacion_ruido = 18  # Penalización alta por edición local detectada
            score += penalizacion_ruido
        
        prioritarias.append({
            "check": "Ruido y bordes",
            "detalle": {
                "detectado": ruido_analisis.get("tiene_edicion_local", False),
                "nivel_sospecha": ruido_analisis.get("nivel_sospecha", "BAJO"),
                "laplacian_variance": ruido_analisis.get("laplacian_variance_global", 0),
                "edge_density": ruido_analisis.get("edge_density_global", 0),
                "num_lines": ruido_analisis.get("lines", {}).get("total", 0),
                "parallel_lines": ruido_analisis.get("lines", {}).get("parallel_groups", 0),
                "outlier_ratio": ruido_analisis.get("outliers", {}).get("ratio", 0),
                "halo_ratio": ruido_analisis.get("halo_ratio", 0),
                "clusters_localizados": ruido_analisis.get("clusters", {}).get("localized", 0),
                "interpretacion": "Análisis de ruido y bordes detecta inconsistencias en patrones locales" if ruido_analisis.get("tiene_edicion_local", False) else "Análisis de ruido y bordes no detecta edición local",
                "posibles_causas": [
                    "Edición local con herramientas de clonado",
                    "Pegado de elementos con diferentes niveles de ruido",
                    "Aplicación de filtros selectivos",
                    "Modificación de áreas específicas",
                    "Halos alrededor de trazos (ratio halo ≳ 0.45)",
                    "Líneas paralelas anómalas"
                ] if ruido_analisis.get("tiene_edicion_local", False) else [
                    "Imagen sin evidencia de edición local",
                    "Patrones de ruido consistentes",
                    "Bordes naturales sin manipulación"
                ],
                "indicadores_clave": [
                    f"Ratio de outliers: {ruido_analisis.get('outliers', {}).get('ratio', 0):.2%}",
                    f"Densidad de bordes: {ruido_analisis.get('edge_density_global', 0):.2%}",
                    f"Líneas paralelas: {ruido_analisis.get('lines', {}).get('parallel_groups', 0)}",
                    f"Varianza Laplaciano: {ruido_analisis.get('laplacian_variance_global', 0):.2f}",
                    f"Ratio halo: {ruido_analisis.get('halo_ratio', 0):.2%}",
                    f"Clústeres localizados: {ruido_analisis.get('clusters', {}).get('localized', 0)}"
                ],
                "recomendacion": "Examinar áreas con patrones de ruido inconsistentes - posible edición local" if ruido_analisis.get("tiene_edicion_local", False) else "Imagen sin evidencia de edición local en análisis de ruido y bordes",
                "umbral_sugerido": "outlier_ratio > 5% y hay clúster/es localizados (no uniforme en toda la imagen)",
                "señales": [
                    "Varianza de Laplaciano muy distinta entre regiones",
                    "Edge_density alto en parches rectangulares", 
                    "Halos alrededor de trazos (ratio halo ≳ 0.45)",
                    "Líneas paralelas anómalas"
                ],
                "analisis_detallado": {
                    "grid": ruido_analisis.get("grid", {}),
                    "robust_stats": ruido_analisis.get("robust_stats", {}),
                    "outliers": ruido_analisis.get("outliers", {}),
                    "clusters": ruido_analisis.get("clusters", {}),
                    "lines": ruido_analisis.get("lines", {})
                }
            },
            "penalizacion": penalizacion_ruido
        })
        
        # 2.4. Análisis forense avanzado (PRIORITARIO)
        forensics_avanzado = analisis_forense.get("forensics_avanzado", {})
        penalizacion_forensics = 0
        
        if forensics_avanzado.get("disponible", False):
            score_forensics = forensics_avanzado.get("score_total", 0)
            if score_forensics > 0:
                # Convertir score 0-100 a penalización 0-25
                penalizacion_forensics = min(25, int(score_forensics * 0.25))
                score += penalizacion_forensics
        
        prioritarias.append({
            "check": "Análisis forense avanzado",
            "detalle": {
                "disponible": forensics_avanzado.get("disponible", False),
                "score_total": forensics_avanzado.get("score_total", 0),
                "nivel_sospecha": forensics_avanzado.get("nivel_sospecha", "No disponible"),
                "metodologia": forensics_avanzado.get("metodologia", "forensics_avanzado"),
                "metricas": forensics_avanzado.get("metricas", {}),
                "scores_detallados": forensics_avanzado.get("scores_detallados", {}),
                "metadatos": forensics_avanzado.get("metadatos", {}),
                "validacion_temporal": forensics_avanzado.get("validacion_temporal", {}),
                "copy_move_analysis": forensics_avanzado.get("copy_move_analysis", {}),
                "interpretacion": forensics_avanzado.get("interpretacion", {}),
                "error": forensics_avanzado.get("error") if not forensics_avanzado.get("disponible", False) else None,
                "explicacion": "Análisis forense avanzado usando técnicas ELA, Copy-Move, validación temporal y análisis de metadatos" if forensics_avanzado.get("disponible", False) else "Análisis forense avanzado no disponible",
                "posibles_causas": [
                    "Recompresión JPEG detectada (ELA ratio > 1.2)",
                    "Regiones clonadas encontradas (Copy-Move)",
                    "Inconsistencias en metadatos temporales",
                    "Software de edición detectado",
                    "Fechas futuras o inconsistentes",
                    "Metadatos EXIF mínimos o ausentes"
                ] if forensics_avanzado.get("disponible", False) and forensics_avanzado.get("score_total", 0) > 0 else [
                    "Análisis forense avanzado no detectó alteraciones",
                    "Metadatos consistentes",
                    "Sin evidencia de recompresión",
                    "Sin regiones clonadas detectadas"
                ],
                "indicadores_clave": [
                    f"ELA Ratio: {forensics_avanzado.get('metricas', {}).get('ela_ratio', 0):.4f}",
                    f"Outlier Rate: {forensics_avanzado.get('metricas', {}).get('outlier_rate', 0):.4f}",
                    f"Copy-Move Matches: {forensics_avanzado.get('metricas', {}).get('copy_move_matches', 0)}",
                    f"Quality Slope: {forensics_avanzado.get('metricas', {}).get('quality_slope', 0):.4f}",
                    f"EXIF Presente: {forensics_avanzado.get('metadatos', {}).get('exif_presente', False)}",
                    f"Fechas Encontradas: {forensics_avanzado.get('metadatos', {}).get('fechas_encontradas', 0)}"
                ] if forensics_avanzado.get("disponible", False) else [
                    "Análisis no disponible"
                ],
                "recomendacion": "Examinar detalladamente las métricas forenses - posible manipulación detectada" if forensics_avanzado.get("disponible", False) and forensics_avanzado.get("score_total", 0) > 25 else "Análisis forense avanzado no detecta alteraciones significativas" if forensics_avanzado.get("disponible", False) else "Análisis forense avanzado no disponible - usar otros métodos de validación",
                "umbral_sugerido": "Score > 25 indica sospecha moderada, Score > 50 indica alta sospecha",
                "señales": [
                    "ELA ratio > 1.2 (recompresión sospechosa)",
                    "Outlier rate > 15% (patrones anómalos)",
                    "Copy-Move matches > 0 (regiones clonadas)",
                    "Quality slope anómalo",
                    "Metadatos EXIF ausentes o mínimos",
                    "Fechas inconsistentes o futuras"
                ] if forensics_avanzado.get("disponible", False) else [
                    "Análisis no disponible"
                ],
                "analisis_detallado": forensics_avanzado
            },
            "penalizacion": penalizacion_forensics
        })
        
        # 2.4. Análisis ELA focalizado (PRIORITARIO si es local con texto)
        from helpers.ela_focalizado_analisis import analizar_ela_focalizado

        # Realizar análisis ELA focalizado
        try:
            ela_analisis = analizar_ela_focalizado(imagen_bytes)
        except Exception as e:
            print(f"Error en análisis ELA focalizado: {e}")
            ela_analisis = {
                "ela": {
                    "marca_editada": False,
                    "nivel_sospecha": "SECUNDARIO",
                    "clusters": {"localized": 0},
                    "texto": {"overlap_text": False, "overlap_digits": False, "peak_hits": 0},
                    "global": {"mean": 0, "std": 0, "max": 0},
                    "suspicious_global_ratio": 0
                }
            }

        # Determinar si va a prioritarias o secundarias
        es_prioritario = ela_analisis.get("ela", {}).get("nivel_sospecha") == "PRIORITARIO"
        es_secundario = ela_analisis.get("ela", {}).get("nivel_sospecha") == "SECUNDARIO"

        penalizacion_ela = 0
        if ela_analisis.get("ela", {}).get("marca_editada", False):
            if es_prioritario:
                penalizacion_ela = 20  # Penalización alta por ELA prioritario
            else:
                penalizacion_ela = 12  # Penalización media por ELA secundario
            score += penalizacion_ela

        # Crear el check de ELA
        ela_check = {
            "check": "ELA (Error Level Analysis) focalizado",
            "detalle": {
                "detectado": ela_analisis.get("ela", {}).get("marca_editada", False),
                "nivel_sospecha": ela_analisis.get("ela", {}).get("nivel_sospecha", "SECUNDARIO"),
                "clusters_localizados": ela_analisis.get("ela", {}).get("clusters", {}).get("localized", 0),
                "overlap_texto": ela_analisis.get("ela", {}).get("texto", {}).get("overlap_text", False),
                "overlap_digitos": ela_analisis.get("ela", {}).get("texto", {}).get("overlap_digits", False),
                "peak_hits": ela_analisis.get("ela", {}).get("texto", {}).get("peak_hits", 0),
                "ela_global_mean": ela_analisis.get("ela", {}).get("global", {}).get("mean", 0),
                "ela_global_max": ela_analisis.get("ela", {}).get("global", {}).get("max", 0),
                "suspicious_ratio": ela_analisis.get("ela", {}).get("suspicious_global_ratio", 0),
                "interpretacion": "ELA focalizado detecta edición local en áreas con texto/números" if ela_analisis.get("ela", {}).get("marca_editada", False) else "ELA focalizado no detecta edición local significativa",
                "posibles_causas": [
                    "Edición de texto o números en la imagen",
                    "Modificación de montos o fechas",
                    "Pegado de elementos textuales",
                    "Alteración de datos específicos",
                    "Reemplazo de texto original"
                ] if ela_analisis.get("ela", {}).get("marca_editada", False) else [
                    "Imagen sin evidencia de edición textual",
                    "Niveles de error consistentes",
                    "Sin alteraciones en áreas de texto"
                ],
                "indicadores_clave": [
                    f"Clústeres localizados: {ela_analisis.get('ela', {}).get('clusters', {}).get('localized', 0)}",
                    f"Overlap con texto: {ela_analisis.get('ela', {}).get('texto', {}).get('overlap_text', False)}",
                    f"Overlap con dígitos: {ela_analisis.get('ela', {}).get('texto', {}).get('overlap_digits', False)}",
                    f"Peak hits: {ela_analisis.get('ela', {}).get('texto', {}).get('peak_hits', 0)}",
                    f"ELA global mean: {ela_analisis.get('ela', {}).get('global', {}).get('mean', 0):.2f}",
                    f"ELA global max: {ela_analisis.get('ela', {}).get('global', {}).get('max', 0):.2f}",
                    f"Ratio sospechoso: {ela_analisis.get('ela', {}).get('suspicious_global_ratio', 0):.2%}"
                ],
                "recomendacion": "Examinar áreas de texto/números con alta actividad ELA - posible edición local" if ela_analisis.get("ela", {}).get("marca_editada", False) else "Imagen sin evidencia de edición textual en análisis ELA",
                "criterios": ela_analisis.get("ela", {}).get("criterios", {}),
                "analisis_detallado": {
                    "grid": ela_analisis.get("ela", {}).get("grid", {}),
                    "clusters": ela_analisis.get("ela", {}).get("clusters", {}),
                    "texto": ela_analisis.get("ela", {}).get("texto", {}),
                    "per_tile": ela_analisis.get("ela", {}).get("per_tile", {})
                }
            },
            "penalizacion": penalizacion_ela
        }

        # Agregar a la categoría correspondiente
        if es_prioritario:
            prioritarias.append(ela_check)
        elif es_secundario:
            secundarias.append(ela_check)

        # 2.5. Análisis de texto sintético aplanado (PRIORITARIO) - Misma lógica que detectar-texto-superpuesto-universal
        from helpers.texto_sintetico_analisis import detectar_texto_sintetico_aplanado
        from helpers.analisis_forense_profesional import detectar_texto_sintetico_aplanado as detectar_texto_sintetico_profesional

        # Obtener texto OCR para cruzar con montos/fechas
        texto_ocr = ""
        if 'parser_avanzado' in campos_factura and campos_factura['parser_avanzado']:
            parser_data = campos_factura['parser_avanzado']
            if 'texto_extraido' in parser_data:
                texto_ocr = parser_data['texto_extraido']

        # Realizar análisis de texto sintético usando la misma lógica que detectar-texto-superpuesto-universal
        try:
            # Usar el análisis profesional que incluye detección de tipo de imagen
            # Nota: imagen_bytes aquí es la imagen original, no la convertida a JPEG
            texto_sint_analisis = detectar_texto_sintetico_profesional(imagen_bytes, analisis_forense)
        except Exception as e:
            print(f"Error en análisis profesional de texto sintético: {e}")
            # Fallback al análisis básico
            try:
                texto_sint_analisis = detectar_texto_sintetico_aplanado(imagen_bytes, ocr_text=texto_ocr)
            except Exception as e2:
                print(f"Error en análisis básico de texto sintético: {e2}")
                texto_sint_analisis = {
                    "tiene_texto_sintetico": False,
                    "nivel_sospecha": "BAJO",
                    "swt_analisis": {"cajas_texto_detectadas": 0, "stroke_width_mean": 0, "stroke_width_std": 0, "stroke_width_uniforme": False},
                    "color_antialias_analisis": {"color_trazo_promedio": 0, "color_casi_puro": False},
                    "halo_analisis": {"halo_ratio_promedio": 0.0},
                    "reguardado_analisis": {"lineas_totales": 0, "horiz_vert": 0, "densidad_lineas_10kpx": 0.0},
                    "coincide_con_montos_fechas": False,
                    "detalles_cajas": [],
                    "tipo_imagen_analisis": {
                        "es_screenshot": False,
                        "resolucion_redonda": False,
                        "tiene_muchas_lineas": False,
                        "exif_vacio": False,
                        "cajas_texto_detectadas": 0
                    }
                }

        # Penalización basada en detección y coincidencia con montos/fechas - Misma lógica que detectar-texto-superpuesto-universal
        penalizacion_texto_sint = 0
        
        # Lógica mejorada para detección de texto sintético usando la misma lógica que detectar-texto-superpuesto-universal
        tiene_texto_sintetico = texto_sint_analisis.get("tiene_texto_sintetico", False)
        nivel_sospecha = texto_sint_analisis.get("nivel_sospecha", "BAJO")
        coincide_montos_fechas = texto_sint_analisis.get("coincide_con_montos_fechas", False)
        
        # Verificar tipo de imagen para ajustar la detección (misma lógica que detectar-texto-superpuesto-universal)
        tipo_imagen = texto_sint_analisis.get("tipo_imagen_analisis", {})
        es_screenshot = tipo_imagen.get("es_screenshot", False)
        cajas_detectadas = tipo_imagen.get("cajas_texto_detectadas", 0)
        resolucion_redonda = tipo_imagen.get("resolucion_redonda", False)
        tiene_muchas_lineas = tipo_imagen.get("tiene_muchas_lineas", False)
        exif_vacio = tipo_imagen.get("exif_vacio", False)
        
        # Ajustar la detección basada en el contexto (misma lógica que detectar-texto-superpuesto-universal)
        if es_screenshot:
            # Para screenshots, ser más conservador (misma lógica que detectar-texto-superpuesto-universal)
            if tiene_texto_sintetico and coincide_montos_fechas:
                penalizacion_texto_sint = 15  # Penalización reducida para screenshots
            elif tiene_texto_sintetico:
                penalizacion_texto_sint = 8   # Penalización muy reducida para screenshots
        elif resolucion_redonda and tiene_muchas_lineas and exif_vacio and cajas_detectadas > 50:
            # Para imágenes que parecen screenshots pero no se detectaron como tal
            if tiene_texto_sintetico and coincide_montos_fechas:
                penalizacion_texto_sint = 18  # Penalización intermedia
            elif tiene_texto_sintetico:
                penalizacion_texto_sint = 10  # Penalización reducida
        else:
            # Lógica normal para imágenes regulares
            if tiene_texto_sintetico and coincide_montos_fechas:
                penalizacion_texto_sint = 25  # Penalización alta si coincide con montos/fechas
            elif tiene_texto_sintetico and nivel_sospecha == "ALTO":
                penalizacion_texto_sint = 20  # Penalización media por texto sintético
            elif tiene_texto_sintetico and nivel_sospecha == "MEDIO":
                penalizacion_texto_sint = 12  # Penalización reducida para nivel medio
            elif tiene_texto_sintetico:
                penalizacion_texto_sint = 8   # Penalización mínima para nivel bajo
        
        score += penalizacion_texto_sint

        # Crear el check de texto sintético (integrado con texto inyectado)
        texto_inyectado_info = texto_sint_analisis.get("texto_inyectado")
        via_deteccion = texto_sint_analisis.get("via_deteccion", "neutro")
        
        # Determinar la vía de detección para el reporte
        if texto_inyectado_info and texto_inyectado_info.get("match"):
            if texto_sint_analisis.get("tiene_texto_sintetico", False):
                via_deteccion = "ambos"
            else:
                via_deteccion = "neutro"
        elif texto_sint_analisis.get("tiene_texto_sintetico", False):
            via_deteccion = "coloreado"
        
        texto_sint_check = {
            "check": "Texto sintético aplanado",
            "detalle": {
                "detectado": texto_sint_analisis.get("tiene_texto_sintetico", False),
                "nivel_sospecha": texto_sint_analisis.get("nivel_sospecha", "BAJO"),
                "via_deteccion": via_deteccion,
                "cajas_texto_detectadas": texto_sint_analisis.get("swt_analisis", {}).get("cajas_texto_detectadas", 0),
                "metodo_deteccion": texto_sint_analisis.get("swt_analisis", {}).get("metodo_deteccion", "MSER+filtros"),
                "stroke_width_mean": texto_sint_analisis.get("swt_analisis", {}).get("stroke_width_mean", 0.0),
                "stroke_width_std": texto_sint_analisis.get("swt_analisis", {}).get("stroke_width_std", 0.0),
                "stroke_width_uniforme": texto_sint_analisis.get("swt_analisis", {}).get("stroke_width_uniforme", False),
                "cv_stroke_width": texto_sint_analisis.get("swt_analisis", {}).get("cv_stroke_width", 0.0),
                "color_trazo_promedio": texto_sint_analisis.get("color_antialias_analisis", {}).get("color_trazo_promedio", 0.0),
                "color_casi_puro": texto_sint_analisis.get("color_antialias_analisis", {}).get("color_casi_puro", False),
                "ratio_cajas_puras": texto_sint_analisis.get("color_antialias_analisis", {}).get("ratio_cajas_puras", 0.0),
                "halo_ratio_promedio": texto_sint_analisis.get("halo_analisis", {}).get("halo_ratio_promedio", 0.0),
                "umbral_halo": texto_sint_analisis.get("halo_analisis", {}).get("umbral_halo", 0.45),
                "lineas_totales": texto_sint_analisis.get("reguardado_analisis", {}).get("lineas_totales", 0),
                "horiz_vert": texto_sint_analisis.get("reguardado_analisis", {}).get("horiz_vert", 0),
                "densidad_lineas_10kpx": texto_sint_analisis.get("reguardado_analisis", {}).get("densidad_lineas_10kpx", 0.0),
                "coincide_con_montos_fechas": texto_sint_analisis.get("coincide_con_montos_fechas", False),
                # Información del tipo de imagen (misma lógica que detectar-texto-superpuesto-universal)
                "tipo_imagen_analisis": {
                    "es_screenshot": es_screenshot,
                    "resolucion_redonda": resolucion_redonda,
                    "tiene_muchas_lineas": tiene_muchas_lineas,
                    "exif_vacio": exif_vacio,
                    "cajas_texto_detectadas": cajas_detectadas
                },
                "interpretacion": "Texto sintético aplanado detectado - posible edición de texto" if texto_sint_analisis.get("tiene_texto_sintetico", False) else "Sin evidencia de texto sintético aplanado",
                "posibles_causas": [
                    "Edición de texto con herramientas de diseño",
                    "Reemplazo de texto original",
                    "Modificación de montos o fechas",
                    "Pegado de texto desde otra fuente",
                    "Renderizado sintético de texto"
                ] if texto_sint_analisis.get("tiene_texto_sintetico", False) else [
                    "Texto natural de la imagen",
                    "Sin evidencia de edición textual",
                    "Características de texto original preservadas"
                ],
                "indicadores_clave": [
                    f"Cajas de texto: {texto_sint_analisis.get('swt_analisis', {}).get('cajas_texto_detectadas', 0)}",
                    f"Grosor uniforme: {texto_sint_analisis.get('swt_analisis', {}).get('stroke_width_uniforme', False)}",
                    f"CV grosor: {texto_sint_analisis.get('swt_analisis', {}).get('cv_stroke_width', 0.0):.3f}",
                    f"Color casi puro: {texto_sint_analisis.get('color_antialias_analisis', {}).get('color_casi_puro', False)}",
                    f"Ratio cajas puras: {texto_sint_analisis.get('color_antialias_analisis', {}).get('ratio_cajas_puras', 0.0):.2%}",
                    f"Halo ratio: {texto_sint_analisis.get('halo_analisis', {}).get('halo_ratio_promedio', 0.0):.3f}",
                    f"Coincide con montos/fechas: {texto_sint_analisis.get('coincide_con_montos_fechas', False)}",
                    f"Vía detección: {via_deteccion}"
                ],
                "recomendacion": "Examinar áreas de texto con características sintéticas - posible edición" if texto_sint_analisis.get("tiene_texto_sintetico", False) else "Imagen sin evidencia de texto sintético aplanado",
                "criterios": {
                    "muchas_cajas": texto_sint_analisis.get("swt_analisis", {}).get("cajas_texto_detectadas", 0) >= 30,
                    "trazo_uniforme": texto_sint_analisis.get("swt_analisis", {}).get("stroke_width_uniforme", False),
                    "color_casi_puro": texto_sint_analisis.get("color_antialias_analisis", {}).get("color_casi_puro", False),
                    "halo_alto": texto_sint_analisis.get("halo_analisis", {}).get("halo_ratio_promedio", 0.0) >= 0.45
                },
                "analisis_detallado": {
                    "detalles_cajas": texto_sint_analisis.get("detalles_cajas", []),
                    "swt_analisis": texto_sint_analisis.get("swt_analisis", {}),
                    "color_antialias_analisis": texto_sint_analisis.get("color_antialias_analisis", {}),
                    "halo_analisis": texto_sint_analisis.get("halo_analisis", {}),
                    "reguardado_analisis": texto_sint_analisis.get("reguardado_analisis", {}),
                    "texto_inyectado": texto_inyectado_info if texto_inyectado_info else None
                }
            },
            "penalizacion": penalizacion_texto_sint
        }

        # Agregar a prioritarias (siempre es prioritario)
        prioritarias.append(texto_sint_check)
        
        # 2.6. Regla compuesta PRIORITARIA: Texto aplanado + Ruido/Bordes
        from helpers.decision_texto_aplanado_ruido import decision_texto_aplanado_ruido
        
        # Preparar datos de análisis forense para la regla compuesta
        analisis_forense_compuesto = {
            "analisis_forense_profesional": {
                "texto_sintetico": {
                    "tiene_texto_sintetico": texto_sint_analisis.get("tiene_texto_sintetico", False),
                    "cajas_texto_detectadas": texto_sint_analisis.get("swt_analisis", {}).get("cajas_texto_detectadas", 0),
                    "stroke_width_mean": texto_sint_analisis.get("swt_analisis", {}).get("stroke_width_mean", 0.0),
                    "stroke_width_std": texto_sint_analisis.get("swt_analisis", {}).get("stroke_width_std", 0.0),
                    "color_casi_puro": texto_sint_analisis.get("color_antialias_analisis", {}).get("color_casi_puro", False)
                },
                "ela_focalizado_analisis": {
                    "ela_promedio_cajas": ela_analisis.get("ela", {}).get("suspicious_global_ratio", 0.0) * 100
                }
            },
            "ruido_bordes": {
                "halo_ratio": ruido_analisis.get("halo_ratio", 0.0),
                "outlier_ratio": ruido_analisis.get("outlier_ratio", 0.0),
                "edge_density": ruido_analisis.get("edge_density", 0.0)
            },
            "ela": {
                "porcentaje_sospechoso": ela_analisis.get("ela", {}).get("suspicious_global_ratio", 0.0) * 100
            }
        }
        
        # Aplicar regla compuesta
        try:
            # Preparar contexto para reducir falsos positivos
            contexto = {
                "is_screenshot": False,  # TODO: detectar si es screenshot
                "is_whatsapp_like": False,  # TODO: detectar si viene de WhatsApp
                "dpi": 0,  # TODO: extraer DPI de metadatos
                "ancho": 0,  # TODO: extraer dimensiones
                "alto": 0
            }
            
            comp = decision_texto_aplanado_ruido(
                analisis_forense_compuesto, 
                rois_montos_fechas=None,
                policy="balanced",
                contexto=contexto
            )
            
            if comp["match_prioritario"]:
                inc = 28
                score += inc
                prioritarias.append({
                    "check": "Texto sintético aplanado + Ruido/Bordes",
                    "detalle": {
                        "nivel": comp["nivel"],
                        "score_parcial": comp["score"],
                        "razones": comp["razones"],
                        "metricas": comp["metricas"],
                        "umbrales": comp["umbrales"],
                        "interpretacion": "Edición probable por texto aplanado (Paint u otros) - combinación de texto sintético y ruido/bordes localizados",
                        "posibles_causas": [
                            "Edición con Paint u otro software básico",
                            "Aplanado y recompresión de texto añadido",
                            "Modificación de montos o fechas con herramientas simples",
                            "Pegado de texto desde otra fuente y aplanado"
                        ],
                        "indicadores_clave": [
                            f"Texto sintético: {comp['metricas']['n_cajas']} cajas, CV={comp['metricas']['sw_cv']:.2f}",
                            f"Ruido/bordes: halo={comp['metricas']['halo_ratio']:.2f}, outliers={comp['metricas']['outlier_ratio']:.2%}",
                            f"Localización: {comp['metricas']['es_localizado']}, densidad={comp['metricas']['densidad_bordes_sospechosos']:.3f}",
                            f"ELA: regional={comp['metricas']['ela_pct_reg']:.1f}%, global={comp['metricas']['ela_pct_global']:.1f}%"
                        ],
                        "flags": comp.get("flags", {}),
                        "policy": comp.get("umbrales", {}).get("policy", "balanced"),
                        "recomendacion": "Examinar áreas de texto con características sintéticas y patrones de ruido localizados - posible edición con herramientas básicas"
                    },
                    "penalizacion": inc
                })
            elif comp["score"] >= 45:
                inc = 12
                score += inc
                secundarias.append({
                    "check": "Indicadores combinados (no concluyente)",
                    "detalle": {
                        "nivel": comp["nivel"],
                        "score_parcial": comp["score"],
                        "razones": comp["razones"],
                        "interpretacion": "Algunos indicadores de edición detectados pero no concluyentes",
                        "recomendacion": "Revisar indicadores individuales para mayor detalle"
                    },
                    "penalizacion": inc
                })
        except Exception as e:
            print(f"Error en regla compuesta texto aplanado + ruido: {e}")
        
        # 2.7. Análisis de overlays coloreados (PRIORITARIO) - Mejorado
        from helpers.overlays_coloreados_analisis import detectar_overlays_coloreados
        
        # Obtener cajas de texto del análisis de texto sintético para reducir falsos positivos
        text_boxes = []
        if 'texto_sint_analisis' in locals() and texto_sint_analisis.get('cajas_texto'):
            text_boxes = texto_sint_analisis['cajas_texto']
        
        # Convertir imagen_bytes a BGR para el análisis
        try:
            import cv2
            import numpy as np
            
            # Decodificar imagen
            img_array = np.frombuffer(imagen_bytes, np.uint8)
            img_bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img_bgr is not None:
                overlays_analisis = detectar_overlays_coloreados(img_bgr, text_boxes=text_boxes)
            else:
                overlays_analisis = {
                    "match": False,
                    "score": 0,
                    "color_ratio": 0.0,
                    "num_componentes_coloreados": 0,
                    "componentes_disparados": []
                }
        except Exception as e:
            print(f"Error en análisis de overlays coloreados: {e}")
            overlays_analisis = {
                "match": False,
                "score": 0,
                "color_ratio": 0.0,
                "num_componentes_coloreados": 0,
                "componentes_disparados": []
            }
        
        # Penalización basada en detección
        penalizacion_overlays = 0
        if overlays_analisis.get("match", False):
            penalizacion_overlays = 25  # Penalización alta por overlays coloreados
            score += penalizacion_overlays
        
        # Crear el check de overlays coloreados
        overlays_check = {
            "check": "Overlays coloreados (strokes/garabatos)",
            "detalle": {
                "detectado": overlays_analisis.get("match", False),
                "score_parcial": overlays_analisis.get("score", 0),
                "color_ratio": overlays_analisis.get("color_ratio", 0.0),
                "num_componentes_coloreados": overlays_analisis.get("num_componentes_coloreados", 0),
                "componentes_disparados": overlays_analisis.get("componentes_disparados", []),
                "interpretacion": "Overlays coloreados detectados - posible edición con Paint u otras herramientas" if overlays_analisis.get("match", False) else "Sin evidencia de overlays coloreados",
                "posibles_causas": [
                    "Garabatos o anotaciones con Paint",
                    "Figuras o líneas coloreadas añadidas",
                    "Marcas o resaltados en color",
                    "Elementos gráficos superpuestos",
                    "Edición con herramientas de dibujo"
                ] if overlays_analisis.get("match", False) else [
                    "Documento sin overlays coloreados",
                    "Sin evidencia de edición con herramientas de dibujo",
                    "Colores consistentes con documento original"
                ],
                "indicadores_clave": [
                    f"Score: {overlays_analisis.get('score', 0)}/100",
                    f"Ratio de color: {overlays_analisis.get('color_ratio', 0.0):.2%}",
                    f"Componentes coloreados: {overlays_analisis.get('num_componentes_coloreados', 0)}",
                    f"Componentes disparados: {len(overlays_analisis.get('componentes_disparados', []))}"
                ],
                "recomendacion": "Examinar áreas con elementos coloreados - posible edición con herramientas de dibujo" if overlays_analisis.get("match", False) else "Imagen sin evidencia de overlays coloreados",
                "criterios": {
                    "croma_alto": "Croma alto en Lab o saturación HSV alta",
                    "forma_trazo": "Blobs elongados con ancho casi constante",
                    "interseccion_texto": "Intersección con texto/bordes refuerza",
                    "color_ratio_ok": overlays_analisis.get("color_ratio", 0.0) <= 0.02
                },
                "analisis_detallado": {
                    "componentes_disparados": overlays_analisis.get("componentes_disparados", []),
                    "metodologia": "Detección de croma alto en Lab/HSV + análisis de forma de trazo + intersección con texto"
                }
            },
            "penalizacion": penalizacion_overlays
        }
        
        # Agregar a prioritarias (siempre es prioritario cuando se detecta)
        if overlays_analisis.get("match", False):
            prioritarias.append(overlays_check)
        
        # 3. Verificar si hay texto extraído
        if not texto_extraido or len(texto_extraido.strip()) < 50:
            score += 30
            caracteres_extraidos = len(texto_extraido) if texto_extraido else 0
            prioritarias.append({
                "check": "Extracción de texto OCR",
                "detalle": {
                    "caracteres_extraidos": caracteres_extraidos,
                    "umbral_minimo": 50,
                    "porcentaje_extraccion": f"{(caracteres_extraidos/50)*100:.1f}%",
                    "calidad_imagen": "BAJA" if caracteres_extraidos < 10 else "MEDIA" if caracteres_extraidos < 30 else "ALTA",
                    "posibles_causas": [
                        "Imagen de baja resolución",
                        "Texto muy pequeño o borroso",
                        "Fondo con poco contraste",
                        "Imagen escaneada de mala calidad"
                    ],
                    "recomendacion": "Mejorar calidad de imagen o usar OCR más avanzado"
                },
                "penalizacion": 30
            })
        
        # 4. Verificar clave de acceso
        if not campos_factura.get("claveAcceso"):
            score += 20
            prioritarias.append({
                "check": "Clave de acceso SRI",
                "detalle": {
                    "clave_encontrada": False,
                    "longitud_esperada": 49,
                    "patron_buscado": r"(\d{49})",
                    "ubicaciones_buscadas": [
                        "Clave de Acceso:",
                        "Clave Acceso:",
                        "Código de autorización:",
                        "Número de autorización:"
                    ],
                    "posibles_causas": [
                        "Clave de acceso no visible en la imagen",
                        "Formato de clave no reconocido",
                        "Texto muy pequeño o borroso",
                        "Clave en ubicación inusual"
                    ],
                    "impacto": "Sin clave de acceso no se puede validar con SRI",
                    "recomendacion": "Verificar que la clave de acceso esté visible y legible"
                },
                "penalizacion": 20
            })
        
        # 5. Análisis forense - Doble compresión (SECUNDARIA)
        analisis_forense_detalle = analisis_forense.get("analisis_forense", {})
        doble_compresion = analisis_forense_detalle.get("doble_compresion", {})
        if doble_compresion.get("tiene_doble_compresion", False):
            score += 15
            secundarias.append({
                "check": "Doble compresión detectada",
                "detalle": {
                    "detectado": True,
                    "confianza": doble_compresion.get("confianza", "N/A"),
                    "periodicidad_detectada": doble_compresion.get("periodicidad_detectada", False),
                    "varianza_alta": doble_compresion.get("varianza_alta", False),
                    "num_peaks": doble_compresion.get("num_peaks", 0),
                    "ac_variance": doble_compresion.get("ac_variance", 0),
                    "dc_variance": doble_compresion.get("dc_variance", 0),
                    "interpretacion": "La imagen fue comprimida múltiples veces, indicando posible edición",
                    "posibles_causas": [
                        "Imagen editada y re-guardada",
                        "Conversión entre formatos múltiples",
                        "Optimización de imagen repetida",
                        "Edición con software que re-comprime"
                    ],
                    "nivel_sospecha": "ALTO" if doble_compresion.get("confianza") == "ALTA" else "MEDIO",
                    "recomendacion": "Verificar historial de edición de la imagen"
                },
                "penalizacion": 15
            })
        
        # 6. Análisis forense - ELA (SECUNDARIA)
        ela = analisis_forense_detalle.get("ela", {})
        if ela.get("tiene_ediciones", False):
            score += 12
            secundarias.append({
                "check": "Análisis ELA sospechoso",
                "detalle": {
                    "detectado": True,
                    "nivel_sospecha": ela.get("nivel_sospecha", "N/A"),
                    "ela_mean": ela.get("ela_mean", 0),
                    "ela_std": ela.get("ela_std", 0),
                    "ela_max": ela.get("ela_max", 0),
                    "porcentaje_sospechoso": ela.get("porcentaje_sospechoso", 0),
                    "edge_density": ela.get("edge_density", 0),
                    "interpretacion": "Error Level Analysis detecta áreas con diferentes niveles de compresión",
                    "posibles_causas": [
                        "Edición local de la imagen",
                        "Pegado de elementos externos",
                        "Modificación de colores o brillo",
                        "Aplicación de filtros o efectos"
                    ],
                    "areas_afectadas": "Áreas con alta variación en ELA",
                    "recomendacion": "Examinar áreas específicas con alta variación ELA"
                },
                "penalizacion": 12
            })
        
        
        # 7. Análisis forense - pHash (SECUNDARIA)
        phash = analisis_forense_detalle.get("phash_bloques", {})
        if phash.get("tiene_diferencias_locales", False):
            score += 10
            secundarias.append({
                "check": "Análisis perceptual hash sospechoso",
                "detalle": {
                    "detectado": True,
                    "nivel_sospecha": phash.get("nivel_sospecha", "N/A"),
                    "num_bloques": phash.get("num_bloques", 0),
                    "mean_difference": phash.get("mean_difference", 0),
                    "std_difference": phash.get("std_difference", 0),
                    "max_difference": phash.get("max_difference", 0),
                    "outlier_ratio": phash.get("outlier_ratio", 0),
                    "interpretacion": "Análisis perceptual hash por bloques detecta diferencias locales significativas",
                    "posibles_causas": [
                        "Modificación de áreas específicas de la imagen",
                        "Pegado de elementos con diferentes características visuales",
                        "Aplicación de filtros o efectos selectivos",
                        "Edición local con herramientas de retoque"
                    ],
                    "metodologia": "Comparación de hashes perceptuales en bloques de 8x8 píxeles",
                    "indicadores_clave": [
                        f"Bloques analizados: {phash.get('num_bloques', 0)}",
                        f"Diferencia promedio: {phash.get('mean_difference', 0):.1f}",
                        f"Ratio de outliers: {phash.get('outlier_ratio', 0):.2%}"
                    ],
                    "recomendacion": "Examinar bloques con alta diferencia perceptual"
                },
                "penalizacion": 12
            })
        
        # 10. Análisis forense - SSIM (SECUNDARIA)
        ssim = analisis_forense_detalle.get("ssim_regional", {})
        if ssim.get("tiene_inconsistencias", False):
            score += 8
            secundarias.append({
                "check": "Análisis SSIM regional sospechoso",
                "detalle": {
                    "detectado": True,
                    "nivel_sospecha": ssim.get("nivel_sospecha", "N/A"),
                    "num_comparaciones": ssim.get("num_comparaciones", 0),
                    "mean_ssim": ssim.get("mean_ssim", 0),
                    "std_ssim": ssim.get("std_ssim", 0),
                    "min_ssim": ssim.get("min_ssim", 0),
                    "low_similarity_ratio": ssim.get("low_similarity_ratio", 0),
                    "interpretacion": "Análisis SSIM regional detecta inconsistencias en similitud estructural",
                    "posibles_causas": [
                        "Edición local que afecta la estructura de la imagen",
                        "Pegado de elementos con diferentes características estructurales",
                        "Aplicación de filtros que modifican la estructura local",
                        "Modificación de texturas o patrones específicos"
                    ],
                    "metodologia": "Comparación de similitud estructural en regiones superpuestas",
                    "indicadores_clave": [
                        f"Comparaciones realizadas: {ssim.get('num_comparaciones', 0)}",
                        f"SSIM promedio: {ssim.get('mean_ssim', 0):.3f}",
                        f"SSIM mínimo: {ssim.get('min_ssim', 0):.3f}",
                        f"Ratio de baja similitud: {ssim.get('low_similarity_ratio', 0):.2%}"
                    ],
                    "recomendacion": "Examinar regiones con baja similitud estructural"
                },
                "penalizacion": 10
            })
        
        # 11. Metadatos sospechosos (ADICIONAL)
        metadatos = analisis_forense.get("metadatos", {})
        if metadatos.get("tiene_metadatos_sospechosos", False):
            score += 5
            adicionales.append({
                "check": "Metadatos sospechosos",
                "detalle": {
                    "detectado": True,
                    "metadatos_exif": metadatos.get("exif", {}),
                    "metadatos_iptc": metadatos.get("iptc", {}),
                    "metadatos_xmp": metadatos.get("xmp", {}),
                    "metadatos_basicos": metadatos.get("basicos", {}),
                    "sospechosos": metadatos.get("sospechosos", []),
                    "interpretacion": "Metadatos EXIF/IPTC/XMP contienen información sospechosa o inconsistente",
                    "posibles_causas": [
                        "Edición con software que modifica metadatos",
                        "Conversión entre formatos que altera metadatos",
                        "Manipulación intencional de metadatos",
                        "Uso de software de edición no estándar"
                    ],
                    "tipos_metadatos": {
                        "exif": "Datos de cámara y configuración",
                        "iptc": "Información editorial y derechos",
                        "xmp": "Metadatos extensibles de Adobe"
                    },
                    "indicadores_clave": [
                        f"EXIF: {len(metadatos.get('exif', {}))} campos",
                        f"IPTC: {len(metadatos.get('iptc', {}))} campos",
                        f"XMP: {len(metadatos.get('xmp', {}))} campos",
                        f"Sospechosos: {len(metadatos.get('sospechosos', []))} elementos"
                    ],
                    "recomendacion": "Verificar consistencia de metadatos con el origen de la imagen"
                },
                "penalizacion": 5
            })
        
        # 12. Superposición de texto (ADICIONAL)
        superposicion = analisis_forense.get("superposicion_texto", {})
        if superposicion.get("tiene_texto_superpuesto", False):
            score += 25
            adicionales.append({
                "check": "Texto superpuesto",
                "detalle": {
                    "detectado": True,
                    "probabilidad": superposicion.get("probabilidad", 0),
                    "areas_sospechosas": superposicion.get("areas_sospechosas", []),
                    "indicadores": superposicion.get("indicadores", []),
                    "interpretacion": "Detección de texto superpuesto indica posible edición o manipulación",
                    "posibles_causas": [
                        "Agregado de texto sobre contenido existente",
                        "Modificación de valores numéricos",
                        "Ocultación de información original",
                        "Edición de fechas o montos"
                    ],
                    "metodologia": "Análisis de patrones de texto y detección de superposición",
                    "indicadores_clave": [
                        f"Probabilidad de superposición: {superposicion.get('probabilidad', 0):.1%}",
                        f"Áreas sospechosas: {len(superposicion.get('areas_sospechosas', []))}",
                        f"Indicadores detectados: {len(superposicion.get('indicadores', []))}"
                    ],
                    "recomendacion": "Examinar áreas específicas donde se detectó superposición de texto"
                },
                "penalizacion": 20
            })
        
        # 13. Capas ocultas (ADICIONAL)
        capas = analisis_forense.get("capas", {})
        if capas.get("tiene_capas_ocultas", False):
            score += 20
            adicionales.append({
                "check": "Capas ocultas",
                "detalle": {
                    "detectado": True,
                    "tiene_capas": capas.get("tiene_capas", False),
                    "total_capas": capas.get("total_capas", 0),
                    "capas_ocultas": capas.get("capas_ocultas", 0),
                    "capas_detalle": capas.get("capas", []),
                    "modos_mezcla": capas.get("modos_mezcla", []),
                    "sospechosas": capas.get("sospechosas", []),
                    "mensaje": capas.get("mensaje", ""),
                    "interpretacion": "Presencia de capas ocultas indica posible edición con software avanzado",
                    "posibles_causas": [
                        "Edición con Photoshop o software similar",
                        "Ocultación intencional de información",
                        "Uso de capas para modificar contenido",
                        "Preservación de elementos editables"
                    ],
                    "tipos_capas": {
                        "normales": "Capas visibles y editables",
                        "ocultas": "Capas no visibles pero presentes",
                        "sospechosas": "Capas con características anómalas"
                    },
                    "indicadores_clave": [
                        f"Total de capas: {capas.get('total_capas', 0)}",
                        f"Capas ocultas: {capas.get('capas_ocultas', 0)}",
                        f"Modos de mezcla: {len(capas.get('modos_mezcla', []))}",
                        f"Sospechosas: {len(capas.get('sospechosas', []))}"
                    ],
                    "recomendacion": "Examinar capas ocultas y sus contenidos"
                },
                "penalizacion": 20
            })
        
        # 14. Elementos sospechosos detectados (shapes/rectángulos)
        analisis_avanzado = analisis_forense.get("analisis_avanzado_overlay", {})
        elementos_sospechosos = analisis_avanzado.get("total_elementos_sospechosos", 0)
        if elementos_sospechosos > 0:
            score += 25
            prioritarias.append({
                "check": "Elementos sospechosos detectados",
                "detalle": {
                    "detectado": True,
                    "total_elementos": elementos_sospechosos,
                    "probabilidad_overlay": analisis_avanzado.get("probabilidad_overlay", 0),
                    "nivel_riesgo": analisis_avanzado.get("nivel_riesgo", "LOW"),
                    "detalles_por_pagina": analisis_avanzado.get("detalles_por_pagina", []),
                    "interpretacion": "Detección de elementos sospechosos (shapes/rectángulos) indica posible edición",
                    "posibles_causas": [
                        "Agregado de rectángulos para ocultar texto",
                        "Modificación de áreas específicas",
                        "Pegado de elementos gráficos",
                        "Edición con herramientas de dibujo"
                    ],
                    "tipos_elementos": {
                        "shapes": "Formas geométricas (rectángulos, círculos)",
                        "rectangulos": "Rectángulos que pueden ocultar contenido",
                        "elementos_graficos": "Elementos gráficos superpuestos"
                    },
                    "indicadores_clave": [
                        f"Total elementos sospechosos: {elementos_sospechosos}",
                        f"Probabilidad overlay: {analisis_avanzado.get('probabilidad_overlay', 0):.1%}",
                        f"Nivel de riesgo: {analisis_avanzado.get('nivel_riesgo', 'N/A')}"
                    ],
                    "recomendacion": "Examinar elementos sospechosos y sus ubicaciones"
                },
                "penalizacion": 25
            })
        
        # 15. Cambios en streams detectados
        analisis_capas = analisis_forense.get("analisis_por_capas", {})
        streams_con_cambios = analisis_capas.get("streams_con_cambios", 0)
        if streams_con_cambios > 0:
            score += 20
            prioritarias.append({
                "check": "Cambios en streams detectados",
                "detalle": {
                    "detectado": True,
                    "total_streams": analisis_capas.get("total_streams", 0),
                    "streams_con_cambios": streams_con_cambios,
                    "probabilidad_overlay": analisis_capas.get("probabilidad_overlay", 0),
                    "nivel_riesgo": analisis_capas.get("nivel_riesgo", "LOW"),
                    "threshold_pixels": analisis_capas.get("threshold_pixels", 0),
                    "detalles_por_pagina": analisis_capas.get("detalles_por_pagina", []),
                    "interpretacion": "Cambios en streams de contenido indican posible edición o superposición",
                    "posibles_causas": [
                        "Agregado de contenido sobre el original",
                        "Modificación de streams existentes",
                        "Superposición de elementos",
                        "Edición de contenido de página"
                    ],
                    "metodologia": "Análisis por capas comparando streams individuales",
                    "indicadores_clave": [
                        f"Total streams: {analisis_capas.get('total_streams', 0)}",
                        f"Streams con cambios: {streams_con_cambios}",
                        f"Probabilidad overlay: {analisis_capas.get('probabilidad_overlay', 0):.1%}",
                        f"Threshold píxeles: {analisis_capas.get('threshold_pixels', 0):.1%}"
                    ],
                    "recomendacion": "Examinar streams específicos que muestran cambios"
                },
                "penalizacion": 20
            })
        
        # 16. Overlay detectado en análisis avanzado
        overlay_detectado = analisis_capas.get("indicadores_clave", {}).get("overlay_detectado", False)
        if overlay_detectado:
            score += 30
            prioritarias.append({
                "check": "Overlay detectado en análisis avanzado",
                "detalle": {
                    "detectado": True,
                    "metodo": "Análisis por capas (más avanzado)",
                    "total_streams": analisis_capas.get("total_streams", 0),
                    "streams_con_cambios": streams_con_cambios,
                    "probabilidad_overlay": analisis_capas.get("probabilidad_overlay", 0),
                    "nivel_riesgo": analisis_capas.get("nivel_riesgo", "LOW"),
                    "interpretacion": "Análisis avanzado por capas confirma detección de overlay/superposición",
                    "posibles_causas": [
                        "Texto superpuesto sobre contenido original",
                        "Elementos gráficos agregados",
                        "Modificación de contenido existente",
                        "Edición con herramientas de superposición"
                    ],
                    "metodologia": "Comparación de streams individuales para detectar cambios",
                    "indicadores_clave": [
                        f"Overlay confirmado: {overlay_detectado}",
                        f"Método más avanzado: {analisis_capas.get('indicadores_clave', {}).get('metodo_mas_avanzado', False)}",
                        f"Streams con cambios: {streams_con_cambios}",
                        f"Probabilidad: {analisis_capas.get('probabilidad_overlay', 0):.1%}"
                    ],
                    "recomendacion": "Confirmar detección de overlay con análisis visual"
                },
                "penalizacion": 30
            })
        
        # 17. Validaciones financieras avanzadas (PRIORITARIO)
        financial_checks = campos_factura.get("financial_checks", {})
        if financial_checks:
            # Check: Suma de ítems vs subtotal sin impuestos
            items_vs_subtotal = financial_checks.get("items_vs_subtotal_sin_impuestos")
            if items_vs_subtotal is False:
                score += 25
                prioritarias.append({
                    "check": "Inconsistencia financiera: ítems vs subtotal",
                    "detalle": {
                        "detectado": True,
                        "suma_items": financial_checks.get("sum_items"),
                        "subtotal_sin_impuestos": campos_factura.get("totals", {}).get("subtotal_sin_impuestos"),
                        "diferencia": abs((financial_checks.get("sum_items") or 0) - (campos_factura.get("totals", {}).get("subtotal_sin_impuestos") or 0)),
                        "interpretacion": "La suma de ítems no coincide con el subtotal sin impuestos",
                        "posibles_causas": [
                            "Manipulación de totales en la factura",
                            "Error en cálculo de subtotales",
                            "Edición posterior de montos",
                            "Factura generada incorrectamente"
                        ],
                        "indicadores_clave": [
                            f"Suma ítems: ${financial_checks.get('sum_items', 0):.2f}",
                            f"Subtotal: ${campos_factura.get('totals', {}).get('subtotal_sin_impuestos', 0):.2f}",
                            f"Diferencia: ${abs((financial_checks.get('sum_items') or 0) - (campos_factura.get('totals', {}).get('subtotal_sin_impuestos') or 0)):.2f}"
                        ],
                        "recomendacion": "Verificar cálculos matemáticos de la factura"
                    },
                    "penalizacion": 25
                })
            
            # Check: Total recompuesto vs total declarado
            recomputed_vs_total = financial_checks.get("recomputed_total_vs_total")
            if recomputed_vs_total is False:
                score += 30
                prioritarias.append({
                    "check": "Inconsistencia financiera: total recompuesto vs declarado",
                    "detalle": {
                        "detectado": True,
                        "total_recompuesto": financial_checks.get("recomputed_total"),
                        "total_declarado": campos_factura.get("importeTotal"),
                        "diferencia": abs((financial_checks.get("recomputed_total") or 0) - (campos_factura.get("importeTotal") or 0)),
                        "interpretacion": "El total calculado no coincide con el total declarado",
                        "posibles_causas": [
                            "Manipulación del total de la factura",
                            "Error en aplicación de impuestos",
                            "Descuentos no aplicados correctamente",
                            "Edición posterior de totales"
                        ],
                        "indicadores_clave": [
                            f"Total recompuesto: ${financial_checks.get('recomputed_total', 0):.2f}",
                            f"Total declarado: ${campos_factura.get('importeTotal', 0):.2f}",
                            f"Diferencia: ${abs((financial_checks.get('recomputed_total') or 0) - (campos_factura.get('importeTotal') or 0)):.2f}"
                        ],
                        "recomendacion": "Verificar cálculos de impuestos y totales"
                    },
                    "penalizacion": 30
                })

        # 17. Análisis de doble compresión JPEG (SECUNDARIO)
        from helpers.doble_compresion_analisis import detectar_doble_compresion
        
        # Realizar análisis de doble compresión
        try:
            doble_comp_analisis = detectar_doble_compresion(imagen_bytes)
        except Exception as e:
            print(f"Error en análisis de doble compresión: {e}")
            doble_comp_analisis = {
                "tiene_doble_compresion": False,
                "periodicidad_detectada": False,
                "confianza": "BAJA",
                "num_peaks": 0,
                "consistencia_componentes": 0.0,
                "ac_variance": 0.0,
                "dc_variance": 0.0
            }
        
        # Solo penalizar si hay doble compresión con confianza ALTA
        penalizacion_doble_comp = 0
        if (doble_comp_analisis.get("tiene_doble_compresion", False) and 
            doble_comp_analisis.get("confianza") == "ALTA" and 
            doble_comp_analisis.get("periodicidad_detectada", False)):
            penalizacion_doble_comp = 8  # Penalización baja por doble compresión
            score += penalizacion_doble_comp
        
        secundarias.append({
            "check": "Doble compresión JPEG",
            "detalle": {
                "detectado": doble_comp_analisis.get("tiene_doble_compresion", False),
                "periodicidad_detectada": doble_comp_analisis.get("periodicidad_detectada", False),
                "confianza": doble_comp_analisis.get("confianza", "BAJA"),
                "num_peaks": doble_comp_analisis.get("num_peaks", 0),
                "consistencia_componentes": doble_comp_analisis.get("consistencia_componentes", 0.0),
                "ac_variance": doble_comp_analisis.get("ac_variance", 0.0),
                "dc_variance": doble_comp_analisis.get("dc_variance", 0.0),
                "is_jpeg": doble_comp_analisis.get("info_jpeg", {}).get("is_jpeg", False),
                "qtables_disponibles": doble_comp_analisis.get("info_jpeg", {}).get("qtables_disponibles", False),
                "interpretacion": "Doble compresión JPEG detectada - posible recompresión" if doble_comp_analisis.get("tiene_doble_compresion", False) else "Sin evidencia de doble compresión JPEG",
                "posibles_causas": [
                    "Recompresión de imagen JPEG",
                    "Edición y re-guardado en formato JPEG",
                    "Procesamiento por aplicaciones de mensajería",
                    "Capturas de pantalla de imágenes JPEG",
                    "Exportación desde software de edición"
                ] if doble_comp_analisis.get("tiene_doble_compresion", False) else [
                    "Imagen sin evidencia de doble compresión",
                    "Compresión JPEG única",
                    "Formato original preservado"
                ],
                "indicadores_clave": [
                    f"Confianza: {doble_comp_analisis.get('confianza', 'BAJA')}",
                    f"Periodicidad: {doble_comp_analisis.get('periodicidad_detectada', False)}",
                    f"Número de picos: {doble_comp_analisis.get('num_peaks', 0)}",
                    f"Consistencia: {doble_comp_analisis.get('consistencia_componentes', 0.0):.2%}",
                    f"Varianza AC: {doble_comp_analisis.get('ac_variance', 0.0):.2f}",
                    f"Varianza DC: {doble_comp_analisis.get('dc_variance', 0.0):.2f}",
                    f"Es JPEG: {doble_comp_analisis.get('info_jpeg', {}).get('is_jpeg', False)}"
                ],
                "recomendacion": "Considerar doble compresión como señal de apoyo - no es prueba única de edición" if doble_comp_analisis.get("tiene_doble_compresion", False) else "Imagen sin evidencia de doble compresión JPEG",
                "nota_importante": "WhatsApp, capturas y exportaciones generan doble compresión sin edición",
                "analisis_detallado": {
                    "detalles_componentes": doble_comp_analisis.get("detalles_componentes", []),
                    "info_jpeg": doble_comp_analisis.get("info_jpeg", {}),
                    "nota": doble_comp_analisis.get("nota", "")
                }
            },
            "penalizacion": penalizacion_doble_comp
        })
        
        # Determinar nivel de riesgo
        if score >= 80:
            nivel = "alto"
            es_falso_probable = True
        elif score >= 50:
            nivel = "medio"
            es_falso_probable = False
        else:
            nivel = "bajo"
            es_falso_probable = False
        
        return {
            "score": score,
            "nivel": nivel,
            "es_falso_probable": es_falso_probable,
            "prioritarias": prioritarias,
            "secundarias": secundarias,
            "adicionales": adicionales
        }
        
    except Exception as e:
        return {
            "score": 100,
            "nivel": "alto",
            "es_falso_probable": True,
            "prioritarias": [{
                "check": "Error en evaluación",
                "detalle": f"Error: {str(e)}",
                "penalizacion": 100
            }],
            "secundarias": [],
            "adicionales": []
        }




@router.post("/validar-imagen")
async def validar_imagen(req: PeticionImagen):
    t_all = time.perf_counter()

    # 1) Decodificar base64
    t0 = time.perf_counter()
    try:
        archivo_bytes = base64.b64decode(req.imagen_base64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="El campo 'imagen_base64' no es base64 válido.")
    
    if len(archivo_bytes) > MAX_PDF_BYTES:  # Usar el mismo límite por ahora
        raise HTTPException(status_code=413, detail=f"El archivo excede el tamaño máximo permitido ({MAX_PDF_BYTES} bytes).")
    log_step("1) decode base64", t0)

    # 2) Detectar tipo de archivo
    t0 = time.perf_counter()
    tipo_info = detectar_tipo_archivo(req.imagen_base64)
    if not tipo_info["valido"] or tipo_info["tipo"] not in ["PNG", "JPEG", "JPG", "TIFF", "BMP", "WEBP"]:
        raise HTTPException(status_code=400, detail=f"Archivo no es una imagen válida: {tipo_info.get('error', 'Tipo no soportado')}")
    tipo_archivo = tipo_info["tipo"]
    log_step("2) detectar tipo imagen", t0)

    # 3) Parser avanzado de facturas SRI
    t0 = time.perf_counter()
    try:
        parse_result = parse_capture_from_bytes(archivo_bytes, f"capture.{tipo_archivo.lower()}")
        texto_extraido = parse_result.ocr_text
        campos_factura_avanzados = {
            "ruc": parse_result.metadata.ruc,
            "razonSocial": parse_result.metadata.buyer_name,
            "fechaEmision": parse_result.metadata.issue_datetime,
            "importeTotal": parse_result.totals.total,
            "claveAcceso": parse_result.metadata.access_key,
            "detalles": [{
                "cantidad": item.qty or 0,
                "descripcion": item.description or "",
                "precioTotal": item.line_total or 0
            } for item in parse_result.items],
            "totals": {
                "subtotal15": parse_result.totals.subtotal15,
                "subtotal0": parse_result.totals.subtotal0,
                "subtotal_no_objeto": parse_result.totals.subtotal_no_objeto,
                "subtotal_sin_impuestos": parse_result.totals.subtotal_sin_impuestos,
                "descuento": parse_result.totals.descuento,
                "iva15": parse_result.totals.iva15,
                "total": parse_result.totals.total
            },
            "barcodes": parse_result.barcodes,
            "financial_checks": parse_result.checks,
            "metadata": {
                "invoice_number": parse_result.metadata.invoice_number,
                "authorization": parse_result.metadata.authorization,
                "environment": parse_result.metadata.environment,
                "buyer_id": parse_result.metadata.buyer_id,
                "emitter_name": parse_result.metadata.emitter_name,
                "file_metadata": {
                    "sha256": parse_result.metadata.sha256,
                    "width": parse_result.metadata.width,
                    "height": parse_result.metadata.height,
                    "dpi": parse_result.metadata.dpi,
                    "mode": parse_result.metadata.mode,
                    "format": parse_result.metadata.format
                }
            }
        }
        log_step("3) parser avanzado facturas SRI", t0)
    except Exception as e:
        print(f"❌ Error en parser avanzado: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        # Fallback al método anterior
        texto_extraido = _extraer_texto_imagen(archivo_bytes)
        campos_factura_avanzados = _extraer_campos_factura_imagen(texto_extraido)
        log_step("3) fallback extracción básica", t0)

    # 4) Usar campos avanzados como campos_factura
    campos_factura = campos_factura_avanzados

    # 5) Análisis forense completo
    t0 = time.perf_counter()
    try:
        # Convertir imagen a JPEG si no es JPEG/JPG para análisis forense
        imagen_bytes_jpeg = archivo_bytes
        # Detectar tipo de archivo para conversión
        tipo_info = detectar_tipo_archivo(req.imagen_base64)
        tipo_archivo = tipo_info.get("tipo", "UNKNOWN").upper()
        if not tipo_archivo in ["JPEG", "JPG"]:
            try:
                from PIL import Image
                import io
                
                # Abrir imagen original
                img_original = Image.open(io.BytesIO(archivo_bytes))
                
                # Convertir a RGB si es necesario
                if img_original.mode not in ("RGB", "L"):
                    img_original = img_original.convert("RGB")
                
                # Convertir a JPEG con calidad 95
                jpeg_buffer = io.BytesIO()
                img_original.save(jpeg_buffer, format="JPEG", quality=95, optimize=True)
                imagen_bytes_jpeg = jpeg_buffer.getvalue()
                
                # Convertir a base64 para el análisis
                imagen_base64_jpeg = base64.b64encode(imagen_bytes_jpeg).decode('utf-8')
                
                print(f"Imagen convertida a JPEG para análisis forense. Tamaño original: {len(archivo_bytes)} bytes, JPEG: {len(imagen_bytes_jpeg)} bytes")
                
            except Exception as e:
                print(f"Error convirtiendo imagen a JPEG: {e}")
                # Usar imagen original si falla la conversión
                imagen_base64_jpeg = req.imagen_base64
        else:
            imagen_base64_jpeg = req.imagen_base64
        
        # Análisis forense básico
        analisis_forense = analizar_imagen_completa(imagen_base64_jpeg)
        
        # Análisis forense avanzado (nuevo)
        try:
            # Guardar imagen JPEG convertida temporalmente para análisis avanzado
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(imagen_bytes_jpeg)
                temp_path = temp_file.name
            
            analisis_forense_avanzado = analizar_forensics_avanzado(temp_path)
            
            # Integrar análisis avanzado en el resultado
            analisis_forense["forensics_avanzado"] = analisis_forense_avanzado
            
            # Limpiar archivo temporal
            os.unlink(temp_path)
            
        except Exception as e_avanzado:
            print(f"Error en análisis forense avanzado: {e_avanzado}")
            analisis_forense["forensics_avanzado"] = {
                "disponible": False,
                "error": str(e_avanzado)
            }
        
        log_step("5) análisis forense completo", t0)
    except Exception as e:
        print(f"Error en análisis forense: {e}")
        analisis_forense = {
            "error": f"Error en análisis forense: {str(e)}",
            "probabilidad_manipulacion": 0.5,
            "nivel_riesgo": "MEDIO",
            "forensics_avanzado": {
                "disponible": False,
                "error": "Análisis forense básico falló"
            }
        }

    # 6) Preparar validación de firmas (siempre falsa para imágenes)
    validacion_firmas = {
        "resumen": {"total_firmas": 0, "firmas_validas": 0, "firmas_invalidas": 0, "con_certificados": 0, "con_timestamps": 0, "con_politicas": 0, "porcentaje_validas": 0},
        "dependencias": {"asn1crypto": False, "oscrypto": False, "certvalidator": False},
        "analisis_sri": {"es_documento_sri": False, "ruc_emisor": None, "razon_social": None, "numero_documento": None, "fecha_emision": None, "clave_acceso": None, "ambiente": None, "tipo_emision": None},
        "validacion_pdf": {"firma_detectada": False, "tipo_firma": "ninguna", "es_pades": False, "metadatos": {"numero_firmas": 0}},
        "tipo_documento": tipo_archivo.lower(),
        "firma_detectada": False
    }

    # 7) Integrar validación SRI en los datos de la factura
    factura_con_sri = integrar_validacion_sri(campos_factura)
    
    # 8) Evaluación de riesgo (después de la validación SRI)
    t0 = time.perf_counter()
    riesgo = _evaluar_riesgo_imagen(archivo_bytes, texto_extraido, factura_con_sri, analisis_forense)
    log_step("8) evaluación de riesgo", t0)


    # 9) Preparar respuesta final
    log_step("TOTAL", t_all)
    
    # Usar el resultado de la validación SRI para el mensaje principal
    sri_verificado = factura_con_sri.get("sri_verificado", False)
    mensaje_sri = factura_con_sri.get("mensaje", f"Análisis forense de imagen {tipo_archivo} completado.")
    
    return JSONResponse(
        status_code=200,
        content=safe_serialize_dict({
            "sri_verificado": sri_verificado,
            "mensaje": mensaje_sri,
            "tipo_archivo": tipo_archivo,
            "coincidencia": "no",  # Las imágenes no se pueden comparar con SRI
            "diferencias": {},
            "diferenciasProductos": [],
            "resumenProductos": {
                "num_sri": 0,
                "num_imagen": len(campos_factura.get("detalles", [])),
                "total_sri_items": 0,
                "total_imagen_items": sum(d.get("precioTotal", 0) for d in campos_factura.get("detalles", []))
            },
            "factura": factura_con_sri,
            "clave_acceso_parseada": parse_result.access_key_parsed if 'parse_result' in locals() else None,
            "riesgo": riesgo,
            "validacion_firmas": validacion_firmas,
            "analisis_detallado": analisis_forense,
            "texto_extraido": texto_extraido[:1000] + "..." if len(texto_extraido) > 1000 else texto_extraido,
            "parser_avanzado": {
                "disponible": "financial_checks" in campos_factura,
                "barcodes_detectados": len(campos_factura.get("barcodes", [])),
                "items_detectados": len(campos_factura.get("detalles", [])),
                "validaciones_financieras": campos_factura.get("financial_checks", {}),
                "metadatos_avanzados": campos_factura.get("metadata", {})
            }
        })
    )
