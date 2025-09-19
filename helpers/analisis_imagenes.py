"""
Helper especializado para análisis forense de imágenes.

Analiza metadatos, capas, y posibles superposiciones en imágenes:
1. Metadatos EXIF, IPTC, XMP
2. Análisis de capas (PSD, TIFF con capas)
3. Detección de superposición de texto
4. Análisis de integridad de la imagen

Autor: Sistema de Análisis de Documentos
Versión: 1.0
"""

import base64
import io
import hashlib
import json
import xml.etree.ElementTree as ET
import re
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ExifTags
import exifread
import piexif
import imagehash
import numpy as np
from collections import defaultdict
from .type_conversion import ensure_python_bool, ensure_python_float, safe_serialize_dict


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


def detectar_tipo_archivo(archivo_base64: str) -> Dict[str, Any]:
    """
    Detecta el tipo de archivo basado en el contenido base64.
    
    Args:
        archivo_base64: Archivo codificado en base64
        
    Returns:
        Dict con información del tipo de archivo
    """
    try:
        # Decodificar base64
        archivo_bytes = base64.b64decode(archivo_base64)
        
        # Detectar tipo por magic bytes
        if archivo_bytes.startswith(b'%PDF'):
            return {
                "tipo": "PDF",
                "extension": "pdf",
                "mime_type": "application/pdf",
                "valido": True
            }
        elif archivo_bytes.startswith(b'\xff\xd8\xff'):
            return {
                "tipo": "JPEG",
                "extension": "jpg",
                "mime_type": "image/jpeg",
                "valido": True
            }
        elif archivo_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return {
                "tipo": "PNG",
                "extension": "png",
                "mime_type": "image/png",
                "valido": True
            }
        elif archivo_bytes.startswith(b'GIF87a') or archivo_bytes.startswith(b'GIF89a'):
            return {
                "tipo": "GIF",
                "extension": "gif",
                "mime_type": "image/gif",
                "valido": True
            }
        elif archivo_bytes.startswith(b'BM'):
            return {
                "tipo": "BMP",
                "extension": "bmp",
                "mime_type": "image/bmp",
                "valido": True
            }
        elif archivo_bytes.startswith(b'II*\x00') or archivo_bytes.startswith(b'MM\x00*'):
            return {
                "tipo": "TIFF",
                "extension": "tiff",
                "mime_type": "image/tiff",
                "valido": True
            }
        elif archivo_bytes.startswith(b'8BPS'):
            return {
                "tipo": "PSD",
                "extension": "psd",
                "mime_type": "image/vnd.adobe.photoshop",
                "valido": True
            }
        elif archivo_bytes.startswith(b'ftyp'):
            return {
                "tipo": "HEIC",
                "extension": "heic",
                "mime_type": "image/heic",
                "valido": True
            }
        else:
            return {
                "tipo": "UNKNOWN",
                "extension": "unknown",
                "mime_type": "application/octet-stream",
                "valido": False
            }
            
    except Exception as e:
        return {
            "tipo": "ERROR",
            "extension": "error",
            "mime_type": "application/octet-stream",
            "valido": False,
            "error": str(e)
        }


def analizar_metadatos_imagen(imagen_bytes: bytes) -> Dict[str, Any]:
    """
    Analiza metadatos de la imagen (EXIF, IPTC, XMP).
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        Dict con metadatos extraídos
    """
    metadatos = {
        "exif": {},
        "iptc": {},
        "xmp": {},
        "basicos": {},
        "sospechosos": []
    }
    
    try:
        # Abrir imagen con PIL
        imagen = Image.open(io.BytesIO(imagen_bytes))
        
        # Metadatos básicos
        metadatos["basicos"] = {
            "formato": imagen.format,
            "modo": imagen.mode,
            "tamaño": imagen.size,
            "ancho": imagen.width,
            "alto": imagen.height,
            "has_transparency": imagen.mode in ('RGBA', 'LA', 'P')
        }
        
        # EXIF data
        if hasattr(imagen, '_getexif') and imagen._getexif() is not None:
            exif_data = imagen._getexif()
            for tag_id, value in exif_data.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                metadatos["exif"][tag] = str(value)
        
        # Análisis con exifread para metadatos más detallados
        try:
            exif_tags = exifread.process_file(io.BytesIO(imagen_bytes))
            for tag, value in exif_tags.items():
                if not tag.startswith('JPEGThumbnail'):
                    metadatos["exif"][tag] = str(value)
        except:
            pass
        
        # Extraer metadatos XMP
        try:
            xmp_data = _extract_xmp_dict(imagen_bytes)
            metadatos["xmp"] = xmp_data
        except:
            pass
        
        # Detectar metadatos sospechosos
        metadatos["sospechosos"] = _detectar_metadatos_sospechosos(metadatos)
        
        return metadatos
        
    except Exception as e:
        return {
            "error": f"Error analizando metadatos: {str(e)}",
            "exif": {},
            "iptc": {},
            "xmp": {},
            "basicos": {},
            "sospechosos": []
        }


def _detectar_metadatos_sospechosos(metadatos: Dict[str, Any]) -> List[str]:
    """
    Detecta metadatos sospechosos que podrían indicar manipulación.
    
    Args:
        metadatos: Metadatos extraídos de la imagen
        
    Returns:
        Lista de indicadores sospechosos
    """
    sospechosos = []
    
    exif = metadatos.get("exif", {})
    
    # Verificar software de edición
    software = exif.get("Software", "").lower()
    if any(editor in software for editor in ["photoshop", "gimp", "paint", "editor"]):
        sospechosos.append(f"Software de edición detectado: {exif.get('Software')}")
    
    # Verificar si hay múltiples fechas inconsistentes
    fechas = []
    for key in ["DateTime", "DateTimeOriginal", "DateTimeDigitized"]:
        if key in exif:
            fechas.append(exif[key])
    
    if len(set(fechas)) > 1:
        sospechosos.append("Múltiples fechas inconsistentes en EXIF")
    
    # Verificar si falta información de cámara (solo para análisis forense estricto)
    # Comentado para documentos fiscales - no es relevante para análisis de documentos oficiales
    # if not any(key in exif for key in ["Make", "Model", "LensModel"]):
    #     sospechosos.append("Falta información de cámara/dispositivo")
    
    # Verificar si hay metadatos de GPS (solo relevante para análisis forense estricto)
    # Comentado para documentos fiscales - no es crítico para documentos oficiales
    # if any(key in exif for key in ["GPS GPSLatitude", "GPS GPSLongitude"]):
    #     sospechosos.append("Metadatos de ubicación GPS presentes")
    
    # Verificar si hay comentarios sospechosos
    if "ImageDescription" in exif:
        desc = exif["ImageDescription"].lower()
        if any(word in desc for word in ["edit", "modify", "fake", "test"]):
            sospechosos.append(f"Descripción sospechosa: {exif['ImageDescription']}")
    
    # Criterios específicos para documentos fiscales
    # Verificar si hay evidencia de edición de software
    if "Software" in exif:
        software = exif["Software"].lower()
        if any(word in software for word in ["photoshop", "gimp", "paint", "editor"]):
            sospechosos.append(f"Imagen editada con: {exif['Software']}")
    
    # Verificar si hay metadatos de escáner (más relevante para documentos)
    if any(key in exif for key in ["Make", "Model"]):
        make_model = f"{exif.get('Make', '')} {exif.get('Model', '')}".lower()
        if any(word in make_model for word in ["scanner", "scan", "canon", "epson", "hp"]):
            # Esto es normal para documentos escaneados, no es sospechoso
            pass
    
    return sospechosos


def analizar_capas_imagen(imagen_bytes: bytes, tipo_archivo: str) -> Dict[str, Any]:
    """
    Analiza capas en imágenes que las soportan (PSD, TIFF con capas).
    
    Args:
        imagen_bytes: Bytes de la imagen
        tipo_archivo: Tipo de archivo detectado
        
    Returns:
        Dict con información de capas
    """
    capas_info = {
        "tiene_capas": False,
        "total_capas": 0,
        "capas": [],
        "capas_ocultas": 0,
        "modos_mezcla": [],
        "sospechosas": []
    }
    
    try:
        if tipo_archivo == "PSD":
            capas_info = _analizar_capas_psd(imagen_bytes)
        elif tipo_archivo == "TIFF":
            capas_info = _analizar_capas_tiff(imagen_bytes)
        else:
            capas_info["mensaje"] = f"Tipo de archivo {tipo_archivo} no soporta capas"
            
        return capas_info
        
    except Exception as e:
        return {
            "error": f"Error analizando capas: {str(e)}",
            "tiene_capas": False,
            "total_capas": 0,
            "capas": [],
            "capas_ocultas": 0,
            "modos_mezcla": [],
            "sospechosas": []
        }


def _analizar_capas_psd(imagen_bytes: bytes) -> Dict[str, Any]:
    """
    Analiza capas específicamente en archivos PSD.
    """
    # Por ahora, implementación básica
    # En una implementación completa, se usaría una librería como psd-tools
    return {
        "tiene_capas": True,
        "total_capas": 0,  # Se implementaría con psd-tools
        "capas": [],
        "capas_ocultas": 0,
        "modos_mezcla": [],
        "sospechosas": [],
        "mensaje": "Análisis de capas PSD requiere librería psd-tools"
    }


def _analizar_capas_tiff(imagen_bytes: bytes) -> Dict[str, Any]:
    """
    Analiza capas en archivos TIFF.
    """
    try:
        imagen = Image.open(io.BytesIO(imagen_bytes))
        
        # TIFF puede tener múltiples páginas/capas
        capas = []
        try:
            for i in range(imagen.n_frames):
                imagen.seek(i)
                capas.append({
                    "indice": i,
                    "tamaño": imagen.size,
                    "modo": imagen.mode,
                    "visible": True  # Asumir visible por defecto
                })
        except:
            capas = [{
                "indice": 0,
                "tamaño": imagen.size,
                "modo": imagen.mode,
                "visible": True
            }]
        
        return {
            "tiene_capas": len(capas) > 1,
            "total_capas": len(capas),
            "capas": capas,
            "capas_ocultas": 0,
            "modos_mezcla": [],
            "sospechosas": []
        }
        
    except Exception as e:
        return {
            "error": f"Error analizando TIFF: {str(e)}",
            "tiene_capas": False,
            "total_capas": 0,
            "capas": [],
            "capas_ocultas": 0,
            "modos_mezcla": [],
            "sospechosas": []
        }


def detectar_superposicion_texto_imagen(imagen_bytes: bytes) -> Dict[str, Any]:
    """
    Detecta posibles superposiciones de texto en la imagen.
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        Dict con análisis de superposición
    """
    try:
        imagen = Image.open(io.BytesIO(imagen_bytes))
        
        # Convertir a array numpy para análisis
        img_array = np.array(imagen)
        
        # Análisis básico de superposición
        analisis = {
            "tiene_texto_superpuesto": False,
            "areas_sospechosas": [],
            "indicadores": [],
            "probabilidad": 0.0
        }
        
        # Detectar bordes rectangulares (posibles parches)
        bordes_rectangulares = _detectar_bordes_rectangulares(img_array)
        if bordes_rectangulares:
            analisis["indicadores"].append("Bordes rectangulares detectados")
            analisis["probabilidad"] += 0.3
        
        # Detectar áreas con poca variación de color (posibles fondos)
        areas_uniformes = _detectar_areas_uniformes(img_array)
        if areas_uniformes:
            analisis["indicadores"].append("Áreas con poca variación de color")
            analisis["probabilidad"] += 0.2
        
        # Detectar patrones de texto (bordes rectos, alineación)
        patrones_texto = _detectar_patrones_texto(img_array)
        if patrones_texto:
            analisis["indicadores"].append("Patrones de texto detectados")
            analisis["probabilidad"] += 0.4
        
        # Determinar si hay superposición
        analisis["tiene_texto_superpuesto"] = ensure_python_bool(analisis["probabilidad"] > 0.5)
        
        return safe_serialize_dict(analisis)
        
    except Exception as e:
        return {
            "error": f"Error analizando superposición: {str(e)}",
            "tiene_texto_superpuesto": False,
            "areas_sospechosas": [],
            "indicadores": [],
            "probabilidad": 0.0
        }


def _detectar_bordes_rectangulares(img_array: np.ndarray) -> bool:
    """Detecta si hay bordes rectangulares en la imagen"""
    try:
        if len(img_array.shape) == 3:
            gray = np.mean(img_array, axis=2)
        else:
            gray = img_array
            
        # Detectar bordes usando gradientes
        grad_x = np.abs(np.diff(gray, axis=1))
        grad_y = np.abs(np.diff(gray, axis=0))
        
        # Si hay muchos bordes rectos, es sospechoso
        straight_edges_x = np.sum(grad_x > 50) / grad_x.size
        straight_edges_y = np.sum(grad_y > 50) / grad_y.size
        
        return ensure_python_bool(straight_edges_x > 0.1 or straight_edges_y > 0.1)
        
    except:
        return False


def _detectar_areas_uniformes(img_array: np.ndarray) -> bool:
    """Detecta áreas con poca variación de color"""
    try:
        if len(img_array.shape) == 3:
            color_variance = np.var(img_array, axis=(0, 1))
            return ensure_python_bool(np.mean(color_variance) < 10)
        return False
    except:
        return False


def _detectar_patrones_texto(img_array: np.ndarray) -> bool:
    """Detecta patrones que podrían indicar texto superpuesto"""
    try:
        if len(img_array.shape) == 3:
            gray = np.mean(img_array, axis=2)
        else:
            gray = img_array
            
        # Detectar líneas horizontales y verticales (características del texto)
        grad_x = np.abs(np.diff(gray, axis=1))
        grad_y = np.abs(np.diff(gray, axis=0))
        
        # Contar líneas horizontales y verticales
        lines_h = np.sum(grad_x > 30) / grad_x.size
        lines_v = np.sum(grad_y > 30) / grad_y.size
        
        return ensure_python_bool(lines_h > 0.05 or lines_v > 0.05)
        
    except:
        return False


def analizar_imagen_completa(archivo_base64: str) -> Dict[str, Any]:
    """
    Análisis completo de una imagen con técnicas forenses avanzadas.
    
    Args:
        archivo_base64: Imagen codificada en base64
        
    Returns:
        Dict con análisis completo incluyendo análisis forense
    """
    try:
        # Detectar tipo de archivo
        tipo_info = detectar_tipo_archivo(archivo_base64)
        
        if not tipo_info["valido"]:
            return {
                "error": f"Archivo no válido: {tipo_info.get('error', 'Tipo desconocido')}",
                "tipo_archivo": tipo_info
            }
        
        # Decodificar archivo
        archivo_bytes = base64.b64decode(archivo_base64)
        
        # Análisis básico
        metadatos = analizar_metadatos_imagen(archivo_bytes)
        capas = analizar_capas_imagen(archivo_bytes, tipo_info["tipo"])
        superposicion = detectar_superposicion_texto_imagen(archivo_bytes)
        
        # Análisis forense avanzado
        try:
            from helpers.analisis_forense_avanzado import analisis_forense_completo
            analisis_forense = analisis_forense_completo(archivo_bytes, tipo_info["tipo"])
        except ImportError:
            analisis_forense = {"error": "Módulo de análisis forense no disponible"}
        except Exception as e:
            analisis_forense = {"error": f"Error en análisis forense: {str(e)}"}
        
        # Calcular probabilidad general de manipulación
        probabilidad = 0.0
        indicadores = []
        
        # Metadatos sospechosos
        if metadatos.get("sospechosos"):
            probabilidad += 0.2
            indicadores.extend(metadatos["sospechosos"])
        
        # Superposición de texto
        if superposicion.get("tiene_texto_superpuesto"):
            probabilidad += 0.3
            indicadores.extend(superposicion.get("indicadores", []))
        
        # Capas ocultas
        if capas.get("capas_ocultas", 0) > 0:
            probabilidad += 0.2
            indicadores.append("Capas ocultas detectadas")
        
        # Análisis forense (peso mayor)
        if analisis_forense and not analisis_forense.get("error"):
            grado_confianza = analisis_forense.get("grado_confianza", {})
            if grado_confianza.get("grado_confianza") == "ALTO":
                probabilidad += 0.5
                indicadores.append("Análisis forense: ALTA sospecha")
            elif grado_confianza.get("grado_confianza") == "MEDIO":
                probabilidad += 0.3
                indicadores.append("Análisis forense: MEDIA sospecha")
            else:
                probabilidad += 0.1
        
        # Limitar probabilidad a 1.0
        probabilidad = min(probabilidad, 1.0)
        
        # Determinar nivel de riesgo
        if probabilidad >= 0.7:
            nivel_riesgo = "HIGH"
        elif probabilidad >= 0.4:
            nivel_riesgo = "MEDIUM"
        else:
            nivel_riesgo = "LOW"
        
        return safe_serialize_dict({
            "tipo_archivo": tipo_info,
            "metadatos": metadatos,
            "capas": capas,
            "superposicion_texto": superposicion,
            "analisis_forense": analisis_forense,
            "probabilidad_manipulacion": round(probabilidad, 3),
            "nivel_riesgo": nivel_riesgo,
            "indicadores_sospechosos": indicadores,
            "resumen": {
                "tiene_metadatos_sospechosos": ensure_python_bool(len(metadatos.get("sospechosos", [])) > 0),
                "tiene_texto_superpuesto": ensure_python_bool(superposicion.get("tiene_texto_superpuesto", False)),
                "tiene_capas_ocultas": ensure_python_bool(capas.get("capas_ocultas", 0) > 0),
                "tiene_evidencias_forenses": ensure_python_bool(analisis_forense.get("grado_confianza", {}).get("grado_confianza") in ["ALTO", "MEDIO"]),
                "total_indicadores": len(indicadores)
            }
        })
        
    except Exception as e:
        return {
            "error": f"Error en análisis completo: {str(e)}",
            "tipo_archivo": {"tipo": "ERROR", "valido": False},
            "metadatos": {},
            "capas": {},
            "superposicion_texto": {},
            "analisis_forense": {},
            "probabilidad_manipulacion": 0.0,
            "nivel_riesgo": "UNKNOWN",
            "indicadores_sospechosos": [],
            "resumen": {}
        }
