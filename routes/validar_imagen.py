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
        
        # 4. Verificar campos críticos
        campos_criticos = ["ruc", "razonSocial", "fechaEmision", "importeTotal"]
        campos_faltantes = [campo for campo in campos_criticos if not campos_factura.get(campo)]
        campos_encontrados = [campo for campo in campos_criticos if campos_factura.get(campo)]
        
        if campos_faltantes:
            score += len(campos_faltantes) * 10
            prioritarias.append({
                "check": "Campos críticos de factura",
                "detalle": {
                    "campos_faltantes": campos_faltantes,
                    "campos_encontrados": campos_encontrados,
                    "total_campos": len(campos_criticos),
                    "porcentaje_completitud": f"{(len(campos_encontrados)/len(campos_criticos))*100:.1f}%",
                    "campos_detalle": {
                        "ruc": {
                            "encontrado": "ruc" in campos_encontrados,
                            "valor": campos_factura.get("ruc"),
                            "patron_buscado": r"RUC[:\s]*(\d{13})"
                        },
                        "razonSocial": {
                            "encontrado": "razonSocial" in campos_encontrados,
                            "valor": campos_factura.get("razonSocial"),
                            "patron_buscado": r"Razón Social[:\s]*([^\n]+)"
                        },
                        "fechaEmision": {
                            "encontrado": "fechaEmision" in campos_encontrados,
                            "valor": campos_factura.get("fechaEmision"),
                            "patron_buscado": r"Fecha[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"
                        },
                        "importeTotal": {
                            "encontrado": "importeTotal" in campos_encontrados,
                            "valor": campos_factura.get("importeTotal"),
                            "patron_buscado": r"Total[:\s]*\$?(\d+[.,]\d{2})"
                        }
                    },
                    "posibles_causas": [
                        "Texto no reconocido por OCR",
                        "Formato de factura no estándar",
                        "Campos en ubicaciones inusuales",
                        "Calidad de imagen insuficiente"
                    ],
                    "recomendacion": "Verificar formato de factura y calidad de imagen"
                },
                "penalizacion": len(campos_faltantes) * 10
            })
        
        # 5. Verificar clave de acceso
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
        
        # 6. Análisis forense - Doble compresión (SECUNDARIA)
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
        
        # 7. Análisis forense - ELA (SECUNDARIA)
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
        
        # 8. Análisis forense - Ruido y bordes (SECUNDARIA)
        ruido_bordes = analisis_forense_detalle.get("ruido_bordes", {})
        if ruido_bordes.get("tiene_edicion_local", False):
            score += 18
            secundarias.append({
                "check": "Inconsistencias en ruido y bordes",
                "detalle": {
                    "detectado": True,
                    "nivel_sospecha": ruido_bordes.get("nivel_sospecha", "N/A"),
                    "laplacian_variance": ruido_bordes.get("laplacian_variance", 0),
                    "edge_density": ruido_bordes.get("edge_density", 0),
                    "num_lines": ruido_bordes.get("num_lines", 0),
                    "parallel_lines": ruido_bordes.get("parallel_lines", 0),
                    "outlier_ratio": ruido_bordes.get("outlier_ratio", 0),
                    "gradient_peaks": ruido_bordes.get("gradient_peaks", 0),
                    "peak_ratio": ruido_bordes.get("peak_ratio", 0),
                    "interpretacion": "Análisis de ruido y bordes detecta inconsistencias en patrones locales",
                    "posibles_causas": [
                        "Edición local con herramientas de clonado",
                        "Pegado de elementos con diferentes niveles de ruido",
                        "Aplicación de filtros selectivos",
                        "Modificación de áreas específicas"
                    ],
                    "indicadores_clave": [
                        f"Ratio de outliers: {ruido_bordes.get('outlier_ratio', 0):.2%}",
                        f"Densidad de bordes: {ruido_bordes.get('edge_density', 0):.2%}",
                        f"Líneas paralelas: {ruido_bordes.get('parallel_lines', 0)}"
                    ],
                    "recomendacion": "Examinar áreas con patrones de ruido inconsistentes"
                },
                "penalizacion": 18
            })
        
        # 9. Análisis forense - pHash (SECUNDARIA)
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
        
        # 17. Evidencias forenses de manipulación (check general) - SECUNDARIA
        grado_confianza = analisis_forense.get("analisis_forense", {}).get("grado_confianza", {})
        tiene_evidencias_forenses = grado_confianza.get("grado_confianza") in ["BAJO", "MEDIO"]
        
        if tiene_evidencias_forenses:
            score += 15
            secundarias.append({
                "check": "Evidencias forenses de manipulación",
                "detalle": {
                    "detectado": True,
                    "grado_confianza": grado_confianza.get("grado_confianza", "N/A"),
                    "porcentaje_confianza": grado_confianza.get("porcentaje_confianza", 0),
                    "puntuacion": grado_confianza.get("puntuacion", 0),
                    "max_puntuacion": grado_confianza.get("max_puntuacion", 12),
                    "evidencias": grado_confianza.get("evidencias", []),
                    "justificacion": grado_confianza.get("justificacion", ""),
                    "recomendacion": grado_confianza.get("recomendacion", ""),
                    "interpretacion": "Análisis forense general detecta indicadores de manipulación",
                    "posibles_causas": [
                        "Múltiples indicadores de edición detectados",
                        "Inconsistencias en análisis técnicos",
                        "Patrones anómalos en la imagen",
                        "Evidencias de procesamiento no estándar"
                    ],
                    "metodologia": "Evaluación integral de múltiples técnicas forenses",
                    "indicadores_clave": [
                        f"Grado de confianza: {grado_confianza.get('grado_confianza', 'N/A')}",
                        f"Porcentaje: {grado_confianza.get('porcentaje_confianza', 0):.1f}%",
                        f"Puntuación: {grado_confianza.get('puntuacion', 0)}/{grado_confianza.get('max_puntuacion', 12)}",
                        f"Evidencias: {len(grado_confianza.get('evidencias', []))}"
                    ],
                    "recomendacion": "Revisar todas las evidencias forenses detectadas"
                },
                "penalizacion": 15
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

    # 3) Extraer texto con OCR
    t0 = time.perf_counter()
    texto_extraido = _extraer_texto_imagen(archivo_bytes)
    log_step("3) extraer texto OCR", t0)

    # 4) Extraer campos de factura
    t0 = time.perf_counter()
    campos_factura = _extraer_campos_factura_imagen(texto_extraido)
    log_step("4) extraer campos factura", t0)

    # 5) Análisis forense completo
    t0 = time.perf_counter()
    try:
        analisis_forense = analizar_imagen_completa(req.imagen_base64)
        log_step("5) análisis forense completo", t0)
    except Exception as e:
        print(f"Error en análisis forense: {e}")
        analisis_forense = {
            "error": f"Error en análisis forense: {str(e)}",
            "probabilidad_manipulacion": 0.5,
            "nivel_riesgo": "MEDIO"
        }

    # 6) Evaluación de riesgo
    t0 = time.perf_counter()
    riesgo = _evaluar_riesgo_imagen(archivo_bytes, texto_extraido, campos_factura, analisis_forense)
    log_step("6) evaluación de riesgo", t0)


    # 8) Preparar validación de firmas (siempre falsa para imágenes)
    validacion_firmas = {
        "resumen": {"total_firmas": 0, "firmas_validas": 0, "firmas_invalidas": 0, "con_certificados": 0, "con_timestamps": 0, "con_politicas": 0, "porcentaje_validas": 0},
        "dependencias": {"asn1crypto": False, "oscrypto": False, "certvalidator": False},
        "analisis_sri": {"es_documento_sri": False, "ruc_emisor": None, "razon_social": None, "numero_documento": None, "fecha_emision": None, "clave_acceso": None, "ambiente": None, "tipo_emision": None},
        "validacion_pdf": {"firma_detectada": False, "tipo_firma": "ninguna", "es_pades": False, "metadatos": {"numero_firmas": 0}},
        "tipo_documento": tipo_archivo.lower(),
        "firma_detectada": False
    }

    # 9) Preparar respuesta final
    log_step("TOTAL", t_all)
    
    return JSONResponse(
        status_code=200,
        content=safe_serialize_dict({
            "sri_verificado": False,
            "mensaje": f"Análisis forense de imagen {tipo_archivo} completado. No se puede validar con SRI (solo PDFs).",
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
            "factura": campos_factura,
            "riesgo": riesgo,
            "validacion_firmas": validacion_firmas,
            "analisis_detallado": analisis_forense,
            "texto_extraido": texto_extraido[:1000] + "..." if len(texto_extraido) > 1000 else texto_extraido
        })
    )
