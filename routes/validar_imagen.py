import base64
import io
import re
import time
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Configurar Tesseract ANTES de importar cualquier módulo que lo use
try:
    import pytesseract
    import os
    
    # Configurar ruta de Tesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    # Configurar TESSDATA_PREFIX para que encuentre los archivos de idioma
    tessdata_dir = r"C:\Program Files\Tesseract-OCR\tessdata"
    if os.path.exists(tessdata_dir):
        os.environ["TESSDATA_PREFIX"] = tessdata_dir
        print(f"✅ Tesseract configurado globalmente en validar_imagen")
        print(f"✅ TESSDATA_PREFIX configurado: {tessdata_dir}")
    else:
        print(f"⚠️ Directorio tessdata no encontrado: {tessdata_dir}")
        
except Exception as e:
    print(f"❌ Error configurando Tesseract: {e}")

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
                          analisis_forense_profesional: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Evalúa el riesgo de una imagen de factura usando la misma estructura que el PDF.
    """
    try:
        score = 0
        prioritarias = []
        secundarias = []
        adicionales = []
        
        # 1. Validación SRI (PRIORITARIO) - SIEMPRE APARECE
        sri_verificado = campos_factura.get("sri_verificado", False)
        penalizacion_sri = 15 if not sri_verificado else 0
        score += penalizacion_sri
        
        prioritarias.append({
            "check": "Validación SRI",
            "detalle": {
                "sri_verificado": sri_verificado,
                "clave_acceso": campos_factura.get("claveAcceso"),
                "estado_sri": "Verificado" if sri_verificado else "No verificado",
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
                    f"Clave Acceso: {campos_factura.get('claveAcceso', 'No disponible')[:10]}..." if campos_factura.get('claveAcceso') else "No disponible",
                    f"Estado SRI: {'Verificado' if sri_verificado else 'No verificado'}"
                ],
                "recomendacion": "Documento válido según SRI - verificar autenticidad del canal de origen" if sri_verificado else "Documento no validado con SRI - alto riesgo de falsificación"
            },
            "penalizacion": penalizacion_sri
        })
        
        # 2. Texto sintético (PRIORITARIO) - SIEMPRE APARECE
        texto_sintetico = analisis_forense_profesional.get("texto_sintetico", {}) if analisis_forense_profesional else {}
        tiene_texto_sintetico = texto_sintetico.get("tiene_texto_sintetico", False)
        nivel_sospecha_texto = texto_sintetico.get("nivel_sospecha", "BAJO")
        
        penalizacion_texto = 20 if tiene_texto_sintetico else 0
        score += penalizacion_texto
        
        prioritarias.append({
            "check": "Texto sintético detectado",
            "detalle": {
                "detectado": tiene_texto_sintetico,
                "nivel_sospecha": nivel_sospecha_texto,
                "cajas_texto_detectadas": texto_sintetico.get("swt_analisis", {}).get("cajas_texto_detectadas", 0),
                "stroke_width_mean": texto_sintetico.get("swt_analisis", {}).get("stroke_width_mean", 0),
                "stroke_width_std": texto_sintetico.get("swt_analisis", {}).get("stroke_width_std", 0),
                "color_trazo_promedio": texto_sintetico.get("color_antialias_analisis", {}).get("color_trazo_promedio", 0),
                "color_casi_puro": texto_sintetico.get("color_antialias_analisis", {}).get("color_casi_puro", False),
                "interpretacion": "Texto sintético aplanado detectado - posible edición de texto" if tiene_texto_sintetico else "Sin evidencia de texto sintético aplanado",
                "posibles_causas": [
                    "Edición de texto con herramientas de diseño",
                    "Reemplazo de texto original",
                    "Modificación de montos o fechas",
                    "Pegado de texto desde otra fuente",
                    "Renderizado sintético de texto"
                ] if tiene_texto_sintetico else [
                    "Texto natural de la imagen",
                    "Sin evidencia de edición textual",
                    "Características de texto original preservadas"
                ],
                "indicadores_clave": [
                    f"Cajas de texto: {texto_sintetico.get('swt_analisis', {}).get('cajas_texto_detectadas', 0)}",
                    f"Grosor promedio: {texto_sintetico.get('swt_analisis', {}).get('stroke_width_mean', 0):.2f}px",
                    f"Color casi puro: {texto_sintetico.get('color_antialias_analisis', {}).get('color_casi_puro', False)}",
                    f"Nivel de sospecha: {nivel_sospecha_texto}"
                ],
                "recomendacion": "Examinar áreas de texto con características sintéticas - posible edición" if tiene_texto_sintetico else "Imagen sin evidencia de texto sintético aplanado"
            },
            "penalizacion": penalizacion_texto
        })
        
        # 3. Análisis de bordes/ruido (PRIORITARIO) - SIEMPRE APARECE
        ruido_bordes = analisis_forense_profesional.get("ruido_bordes", {}) if analisis_forense_profesional else {}
        inconsistencias_ruido = ruido_bordes.get("ruido_analisis", {}).get("inconsistencias_ruido", "")
        tiene_inconsistencias = "INCONSISTENCIAS" in inconsistencias_ruido
        
        penalizacion_ruido = 18 if tiene_inconsistencias else 0
        score += penalizacion_ruido
        
        prioritarias.append({
            "check": "Inconsistencias de ruido y bordes",
            "detalle": {
                "detectado": tiene_inconsistencias,
                "laplacian_variance": ruido_bordes.get("ruido_analisis", {}).get("laplacian_variance", 0),
                "edge_density": ruido_bordes.get("bordes_analisis", {}).get("edge_density", 0),
                "num_lines": ruido_bordes.get("bordes_analisis", {}).get("num_lines", 0),
                "halo_ratio": ruido_bordes.get("halo_analisis", {}).get("halo_ratio", 0),
                "inconsistencias_ruido": inconsistencias_ruido,
                "interpretacion": "Análisis de ruido y bordes detecta inconsistencias en patrones locales" if tiene_inconsistencias else "Análisis de ruido y bordes no detecta inconsistencias significativas",
                "posibles_causas": [
                    "Edición local con herramientas de clonado",
                    "Pegado de elementos con diferentes niveles de ruido",
                    "Aplicación de filtros selectivos",
                    "Modificación de áreas específicas",
                    "Halos alrededor de trazos"
                ] if tiene_inconsistencias else [
                    "Imagen sin evidencia de edición local",
                    "Patrones de ruido consistentes",
                    "Bordes naturales sin manipulación"
                ],
                "indicadores_clave": [
                    f"Varianza Laplaciano: {ruido_bordes.get('ruido_analisis', {}).get('laplacian_variance', 0):.2f}",
                    f"Densidad de bordes: {ruido_bordes.get('bordes_analisis', {}).get('edge_density', 0):.2%}",
                    f"Líneas detectadas: {ruido_bordes.get('bordes_analisis', {}).get('num_lines', 0)}",
                    f"Ratio halo: {ruido_bordes.get('halo_analisis', {}).get('halo_ratio', 0):.2%}",
                    f"Inconsistencias: {inconsistencias_ruido if inconsistencias_ruido else 'Ninguna'}"
                ],
                "recomendacion": "Examinar áreas con patrones de ruido inconsistentes - posible edición local" if tiene_inconsistencias else "Imagen sin evidencia de edición local en análisis de ruido y bordes"
            },
            "penalizacion": penalizacion_ruido
        })
        
        # 4. Análisis ELA (PRIORITARIO) - SIEMPRE APARECE
        ela = analisis_forense_profesional.get("ela", {}) if analisis_forense_profesional else {}
        tiene_ediciones_ela = ela.get("tiene_ediciones", False)
        nivel_sospecha_ela = ela.get("nivel_sospecha", "NORMAL")
        
        penalizacion_ela = 12 if tiene_ediciones_ela else 0
        score += penalizacion_ela

        prioritarias.append({
            "check": "Análisis ELA sospechoso",
            "detalle": {
                "detectado": tiene_ediciones_ela,
                "nivel_sospecha": nivel_sospecha_ela,
                "ela_mean": ela.get("ela_mean", 0),
                "ela_std": ela.get("ela_std", 0),
                "ela_max": ela.get("ela_max", 0),
                "porcentaje_sospechoso": ela.get("porcentaje_sospechoso", 0),
                "edge_density": ela.get("edge_density", 0),
                "interpretacion": "Error Level Analysis detecta áreas con diferentes niveles de compresión" if tiene_ediciones_ela else "Error Level Analysis no detecta ediciones significativas",
                "posibles_causas": [
                    "Edición local de la imagen",
                    "Pegado de elementos externos",
                    "Modificación de colores o brillo",
                    "Aplicación de filtros o efectos"
                ] if tiene_ediciones_ela else [
                    "Imagen sin evidencia de edición",
                    "Niveles de compresión consistentes",
                    "Sin alteraciones detectadas"
                ],
                "indicadores_clave": [
                    f"ELA promedio: {ela.get('ela_mean', 0):.2f}",
                    f"ELA máximo: {ela.get('ela_max', 0)}",
                    f"Porcentaje sospechoso: {ela.get('porcentaje_sospechoso', 0):.2%}",
                    f"Densidad de bordes: {ela.get('edge_density', 0):.2%}",
                    f"Nivel de sospecha: {nivel_sospecha_ela}"
                ],
                "recomendacion": "Examinar áreas específicas con alta variación ELA" if tiene_ediciones_ela else "Imagen sin evidencia de edición en análisis ELA"
            },
            "penalizacion": penalizacion_ela
        })
        
        # 5. Doble compresión (SECUNDARIO) - SIEMPRE APARECE
        compresion = analisis_forense_profesional.get("compresion", {}) if analisis_forense_profesional else {}
        doble_compresion = compresion.get("doble_compresion", {})
        tiene_doble_compresion = doble_compresion.get("tiene_doble_compresion", False)
        
        penalizacion_doble_comp = 8 if tiene_doble_compresion else 0
        score += penalizacion_doble_comp
        
        secundarias.append({
            "check": "Doble compresión detectada",
            "detalle": {
                "detectado": tiene_doble_compresion,
                "periodicidad_detectada": doble_compresion.get("periodicidad_detectada", False),
                "confianza": doble_compresion.get("confianza", "BAJA"),
                "num_peaks": doble_compresion.get("num_peaks", 0),
                "ac_variance": doble_compresion.get("ac_variance", 0),
                "dc_variance": doble_compresion.get("dc_variance", 0),
                "interpretacion": "La imagen fue comprimida múltiples veces, indicando posible edición" if tiene_doble_compresion else "Sin evidencia de doble compresión JPEG",
                "posibles_causas": [
                    "Imagen editada y re-guardada",
                    "Conversión entre formatos múltiples",
                    "Optimización de imagen repetida",
                    "Edición con software que re-comprime"
                ] if tiene_doble_compresion else [
                    "Imagen sin evidencia de doble compresión",
                    "Compresión JPEG única",
                    "Formato original preservado"
                ],
                "indicadores_clave": [
                    f"Confianza: {doble_compresion.get('confianza', 'BAJA')}",
                    f"Periodicidad: {doble_compresion.get('periodicidad_detectada', False)}",
                    f"Número de picos: {doble_compresion.get('num_peaks', 0)}",
                    f"Varianza AC: {doble_compresion.get('ac_variance', 0):.2f}",
                    f"Varianza DC: {doble_compresion.get('dc_variance', 0):.2f}"
                ],
                "recomendacion": "Considerar doble compresión como señal de apoyo - no es prueba única de edición" if tiene_doble_compresion else "Imagen sin evidencia de doble compresión JPEG"
            },
            "penalizacion": penalizacion_doble_comp
        })
        
        # 6. Inconsistencias de hashes (SECUNDARIO) - SIEMPRE APARECE
        hashes = analisis_forense_profesional.get("hashes", {}) if analisis_forense_profesional else {}
        inconsistencias = hashes.get("inconsistencias", [])
        tiene_inconsistencias_hash = len(inconsistencias) > 0
        
        penalizacion_hashes = 10 if tiene_inconsistencias_hash else 0
        score += penalizacion_hashes
        
        secundarias.append({
            "check": "Inconsistencias de hashes",
            "detalle": {
                "detectado": tiene_inconsistencias_hash,
                "num_inconsistencias": len(inconsistencias),
                "inconsistencias": inconsistencias,
                "phash": hashes.get("hashes_analisis", {}).get("phash", ""),
                "dhash": hashes.get("hashes_analisis", {}).get("dhash", ""),
                "whash": hashes.get("hashes_analisis", {}).get("whash", ""),
                "interpretacion": "Inconsistencias entre diferentes tipos de hashes detectadas" if tiene_inconsistencias_hash else "Hashes consistentes - sin evidencia de manipulación",
                "posibles_causas": [
                    "Modificación de áreas específicas de la imagen",
                    "Pegado de elementos con diferentes características visuales",
                    "Aplicación de filtros o efectos selectivos",
                    "Edición local con herramientas de retoque"
                ] if tiene_inconsistencias_hash else [
                    "Imagen sin evidencia de manipulación",
                    "Hashes perceptuales consistentes",
                    "Características visuales uniformes"
                ],
                "indicadores_clave": [
                    f"Inconsistencias detectadas: {len(inconsistencias)}",
                    f"pHash: {hashes.get('hashes_analisis', {}).get('phash', 'N/A')[:16]}...",
                    f"dHash: {hashes.get('hashes_analisis', {}).get('dhash', 'N/A')[:16]}...",
                    f"wHash: {hashes.get('hashes_analisis', {}).get('whash', 'N/A')[:16]}..."
                ],
                "recomendacion": "Examinar áreas específicas donde se detectaron inconsistencias" if tiene_inconsistencias_hash else "Imagen sin evidencia de manipulación en análisis de hashes"
            },
            "penalizacion": penalizacion_hashes
        })
        
        # 7. Metadatos sospechosos (ADICIONAL) - SIEMPRE APARECE
        metadatos = analisis_forense_profesional.get("metadatos", {}) if analisis_forense_profesional else {}
        compresion_analisis = metadatos.get("compresion_analisis", [])
        tiene_metadatos_sospechosos = any("POSIBLE PROCESAMIENTO" in item for item in compresion_analisis)
        
        penalizacion_metadatos = 5 if tiene_metadatos_sospechosos else 0
        score += penalizacion_metadatos
        
        adicionales.append({
            "check": "Metadatos sospechosos",
            "detalle": {
                "detectado": tiene_metadatos_sospechosos,
                "exif_presente": len(metadatos.get("exif_completo", {})) > 0,
                "xmp_presente": len(metadatos.get("xmp", {})) > 0,
                "software_edicion": metadatos.get("software_edicion", []),
                "camara_analisis": metadatos.get("camara_analisis", []),
                "compresion_analisis": compresion_analisis,
                "interpretacion": "Metadatos contienen información sospechosa o inconsistente" if tiene_metadatos_sospechosos else "Metadatos normales - sin evidencia de manipulación",
                "posibles_causas": [
                    "Edición con software que modifica metadatos",
                    "Conversión entre formatos que altera metadatos",
                    "Manipulación intencional de metadatos",
                    "Uso de software de edición no estándar"
                ] if tiene_metadatos_sospechosos else [
                    "Metadatos originales preservados",
                    "Sin evidencia de edición en metadatos",
                    "Información de cámara/dispositivo consistente"
                ],
                "indicadores_clave": [
                    f"EXIF presente: {len(metadatos.get('exif_completo', {})) > 0}",
                    f"XMP presente: {len(metadatos.get('xmp', {})) > 0}",
                    f"Software edición: {len(metadatos.get('software_edicion', []))}",
                    f"Análisis cámara: {len(metadatos.get('camara_analisis', []))}",
                    f"Indicadores compresión: {len(compresion_analisis)}"
                ],
                "recomendacion": "Verificar consistencia de metadatos con el origen de la imagen" if tiene_metadatos_sospechosos else "Metadatos consistentes con imagen original"
            },
            "penalizacion": penalizacion_metadatos
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

    try:
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
        analisis_forense_profesional = None  # Inicializar variable para análisis forense profesional
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
            
            # Análisis forense profesional completo (único análisis forense)
            try:
                from helpers.analisis_forense_profesional import analisis_forense_completo
                analisis_forense_profesional = analisis_forense_completo(archivo_bytes)
            except Exception as e_profesional:
                print(f"Error en análisis forense profesional: {e_profesional}")
                analisis_forense_profesional = None
            
            log_step("5) análisis forense profesional", t0)
        except Exception as e:
            print(f"Error en análisis forense profesional: {e}")
            analisis_forense_profesional = None

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
        riesgo = _evaluar_riesgo_imagen(archivo_bytes, texto_extraido, factura_con_sri, analisis_forense_profesional)
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
                "analisis_forense_profesional": analisis_forense_profesional,
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
    
    except Exception as e:
        print(f"❌ Error global en validar-imagen: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        
        # Respuesta de error genérica
        return JSONResponse(
            status_code=500,
            content={
                "sri_verificado": False,
                "mensaje": f"Error interno del servidor: {str(e)}",
                "tipo_archivo": "ERROR",
                "coincidencia": "no",
                "diferencias": {},
                "diferenciasProductos": [],
                "resumenProductos": {
                    "num_sri": 0,
                    "num_imagen": 0,
                    "total_sri_items": 0,
                    "total_imagen_items": 0
                },
                "factura": {},
                "clave_acceso_parseada": None,
                "riesgo": {
                    "score": 100,
                    "nivel": "alto",
                    "es_falso_probable": True,
                    "prioritarias": [{
                        "check": "Error del sistema",
                        "detalle": {
                            "error": str(e),
                            "tipo_error": type(e).__name__,
                            "interpretacion": "Error interno del servidor durante el procesamiento",
                            "recomendacion": "Contactar al administrador del sistema"
                        },
                        "penalizacion": 100
                    }],
                    "secundarias": [],
                    "adicionales": []
                },
                "validacion_firmas": {
                    "resumen": {"total_firmas": 0, "firmas_validas": 0, "firmas_invalidas": 0, "con_certificados": 0, "con_timestamps": 0, "con_politicas": 0, "porcentaje_validas": 0},
                    "dependencias": {"asn1crypto": False, "oscrypto": False, "certvalidator": False},
                    "analisis_sri": {"es_documento_sri": False, "ruc_emisor": None, "razon_social": None, "numero_documento": None, "fecha_emision": None, "clave_acceso": None, "ambiente": None, "tipo_emision": None},
                    "validacion_pdf": {"firma_detectada": False, "tipo_firma": "ninguna", "es_pades": False, "metadatos": {"numero_firmas": 0}},
                    "tipo_documento": "error",
                    "firma_detectada": False
                },
                "analisis_forense_profesional": None,
                "texto_extraido": "",
                "parser_avanzado": {
                    "disponible": False,
                    "barcodes_detectados": 0,
                    "items_detectados": 0,
                    "validaciones_financieras": {},
                    "metadatos_avanzados": {}
                }
            }
        )
        
