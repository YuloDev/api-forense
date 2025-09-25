"""
Análisis forense profesional para imágenes.

Implementa técnicas forenses avanzadas:
1. Análisis de metadatos (Software, fechas, cámara)
2. Análisis de compresión JPEG y tablas de cuantización
3. ELA mejorado con amplificación
4. Análisis de ruido, bordes y overlays
5. Comparación de hashes (SHA-256 vs perceptual)
6. Detección de edición por apps (WhatsApp, Telegram)

Autor: Sistema de Análisis Forense Profesional
Versión: 1.0
"""

import base64
import io
import hashlib
import json
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
import cv2
from skimage.metrics import structural_similarity as ssim
from .type_conversion import ensure_python_bool, ensure_python_float, safe_serialize_dict
# Usar configuración global de Tesseract
import config
import pytesseract
from pytesseract import Output


def _limpiar_datos_exif(data):
    """
    Limpia datos EXIF para serialización.
    
    Args:
        data: Datos EXIF a limpiar
        
    Returns:
        Datos limpios y serializables
    """
    if isinstance(data, dict):
        return {k: _limpiar_datos_exif(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_limpiar_datos_exif(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(_limpiar_datos_exif(item) for item in data)
    elif hasattr(data, '__class__'):
        class_name = str(data.__class__)
        if 'IFDRational' in class_name or 'Fraction' in class_name:
            try:
                return float(data)
            except:
                return str(data)
        elif 'bytes' in class_name:
            try:
                return data.decode('utf-8', errors='ignore')
            except:
                return str(data)
        else:
            return str(data)
    else:
        return data
import imagehash
from typing import Dict, Any, List, Tuple, Optional
import datetime
import re
from collections import defaultdict


def analizar_metadatos_forenses(imagen_bytes: bytes) -> Dict[str, Any]:
    """
    Análisis forense avanzado de metadatos.
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        Dict con análisis forense de metadatos
    """
    try:
        from PIL.ExifTags import TAGS
        import exifread
        
        # Cargar imagen
        img = Image.open(io.BytesIO(imagen_bytes))
        
        # Análisis EXIF
        exif_data = img._getexif()
        exif_dict = {}
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                # Convertir tipos no serializables
                if hasattr(value, '__class__') and 'IFDRational' in str(value.__class__):
                    exif_dict[tag] = float(value)
                elif hasattr(value, '__class__') and 'Fraction' in str(value.__class__):
                    exif_dict[tag] = float(value)
                elif isinstance(value, bytes):
                    exif_dict[tag] = value.decode('utf-8', errors='ignore')
                else:
                    exif_dict[tag] = value
        
        # Análisis con exifread para más detalles
        img.seek(0)
        tags = exifread.process_file(io.BytesIO(imagen_bytes), details=True)
        
        # Detectar software de edición
        software_edicion = []
        if 'Image Software' in tags:
            software = str(tags['Image Software'])
            software_edicion.append(f"Software detectado: {software}")
            
            # Detectar software específico
            software_lower = software.lower()
            if any(sw in software_lower for sw in ['photoshop', 'adobe']):
                software_edicion.append("🚨 ADOBE PHOTOSHOP DETECTADO")
            elif any(sw in software_lower for sw in ['gimp', 'gimp']):
                software_edicion.append("🚨 GIMP DETECTADO")
            elif any(sw in software_lower for sw in ['paint', 'mspaint']):
                software_edicion.append("🚨 MICROSOFT PAINT DETECTADO")
            elif any(sw in software_lower for sw in ['canva']):
                software_edicion.append("🚨 CANVA DETECTADO")
            elif any(sw in software_lower for sw in ['whatsapp', 'telegram']):
                software_edicion.append("🚨 APLICACIÓN DE MENSAJERÍA DETECTADA")
        
        # Análisis de fechas
        fechas_analisis = []
        fechas = {}
        
        # Fechas EXIF
        for key in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
            if key in exif_dict:
                fechas[key] = exif_dict[key]
        
        # Fechas exifread
        for key in ['EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 'Image DateTime']:
            if key in tags:
                fechas[key] = str(tags[key])
        
        if len(fechas) > 1:
            fechas_analisis.append("⚠️ Múltiples fechas encontradas")
            for fecha, valor in fechas.items():
                fechas_analisis.append(f"   {fecha}: {valor}")
        
        # Detectar si fue editada después de la captura
        if 'DateTimeOriginal' in fechas and 'DateTime' in fechas:
            try:
                from datetime import datetime
                original = datetime.strptime(fechas['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')
                modify = datetime.strptime(fechas['DateTime'], '%Y:%m:%d %H:%M:%S')
                if modify > original:
                    fechas_analisis.append("🚨 MODIFICADA DESPUÉS DE LA CAPTURA")
                    fechas_analisis.append(f"   Captura: {fechas['DateTimeOriginal']}")
                    fechas_analisis.append(f"   Modificación: {fechas['DateTime']}")
            except:
                pass
        
        # Análisis de cámara/dispositivo
        camara_analisis = []
        make = exif_dict.get('Make', '')
        model = exif_dict.get('Model', '')
        
        if make or model:
            camara_analisis.append(f"Dispositivo: {make} {model}")
            
            # Detectar si es cámara real vs app
            if any(app in make.lower() for app in ['whatsapp', 'telegram', 'instagram']):
                camara_analisis.append("🚨 APLICACIÓN DE MENSAJERÍA COMO 'CÁMARA'")
        else:
            camara_analisis.append("⚠️ FALTA INFORMACIÓN DE CÁMARA/DISPOSITIVO")
        
        # Análisis de MakerNotes (solo cámaras reales)
        if 'MakerNote' in exif_dict:
            camara_analisis.append("✅ MakerNotes presentes (cámara real)")
        else:
            camara_analisis.append("⚠️ Sin MakerNotes (posible app)")
        
        # Análisis de ICC Profile
        icc_analisis = []
        if 'icc_profile' in img.info:
            icc_analisis.append("✅ ICC Profile presente")
        else:
            icc_analisis.append("⚠️ Sin ICC Profile")
        
        # Detectar compresión por apps
        compresion_analisis = []
        if 'JPEGQuality' in exif_dict:
            quality = exif_dict['JPEGQuality']
            if quality < 85:
                compresion_analisis.append(f"⚠️ Calidad JPEG baja: {quality}")
        
        # Detectar si fue procesada por WhatsApp/Telegram
        if not make and not model and not exif_dict.get('MakerNote'):
            compresion_analisis.append("🚨 POSIBLE PROCESAMIENTO POR APP DE MENSAJERÍA")
        
        return safe_serialize_dict({
            "software_edicion": software_edicion,
            "fechas_analisis": fechas_analisis,
            "camara_analisis": camara_analisis,
            "icc_analisis": icc_analisis,
            "compresion_analisis": compresion_analisis,
            "exif_completo": _limpiar_datos_exif(exif_dict),
            "tags_exifread": _limpiar_datos_exif({str(k): str(v) for k, v in tags.items()})
        })
        
    except Exception as e:
        return {
            "error": f"Error en análisis de metadatos: {str(e)}",
            "software_edicion": [],
            "fechas_analisis": [],
            "camara_analisis": [],
            "icc_analisis": [],
            "compresion_analisis": []
        }


def detectar_cuadricula_jpeg_localizada(imagen_bytes: bytes) -> Dict[str, Any]:
    """
    Detecta cuadrícula JPEG y doble compresión localizada.
    
    Args:
        imagen_bytes: Bytes de la imagen JPEG
        
    Returns:
        Dict con análisis de cuadrícula JPEG
    """
    try:
        # Cargar imagen
        img = Image.open(io.BytesIO(imagen_bytes))
        img_array = np.array(img.convert('L'))
        
        # Análisis de bloques 8x8
        h, w = img_array.shape
        bloques_8x8 = []
        
        # Extraer bloques 8x8
        for i in range(0, h-8, 8):
            for j in range(0, w-8, 8):
                bloque = img_array[i:i+8, j:j+8]
                bloques_8x8.append({
                    'pos': (i, j),
                    'bloque': bloque,
                    'dc_coeff': bloque[0, 0],  # Coeficiente DC
                    'varianza': np.var(bloque)
                })
        
        # Análisis de desalineación de bloques
        desalineacion_analisis = {}
        
        # Calcular varianza de coeficientes DC por filas y columnas
        dc_filas = {}
        dc_columnas = {}
        
        for bloque in bloques_8x8:
            i, j = bloque['pos']
            fila = i // 8
            col = j // 8
            dc = bloque['dc_coeff']
            
            if fila not in dc_filas:
                dc_filas[fila] = []
            if col not in dc_columnas:
                dc_columnas[col] = []
                
            dc_filas[fila].append(dc)
            dc_columnas[col].append(dc)
        
        # Detectar discontinuidades en filas
        discontinuidades_filas = 0
        for fila, dcs in dc_filas.items():
            if len(dcs) > 1:
                dcs_array = np.array(dcs)
                diff = np.diff(dcs_array)
                if np.std(diff) > np.mean(np.abs(diff)) * 2:
                    discontinuidades_filas += 1
        
        # Detectar discontinuidades en columnas
        discontinuidades_columnas = 0
        for col, dcs in dc_columnas.items():
            if len(dcs) > 1:
                dcs_array = np.array(dcs)
                diff = np.diff(dcs_array)
                if np.std(diff) > np.mean(np.abs(diff)) * 2:
                    discontinuidades_columnas += 1
        
        desalineacion_analisis["discontinuidades_filas"] = discontinuidades_filas
        desalineacion_analisis["discontinuidades_columnas"] = discontinuidades_columnas
        desalineacion_analisis["total_discontinuidades"] = discontinuidades_filas + discontinuidades_columnas
        
        # Detectar patrones de splicing
        splicing_analisis = {}
        
        # Buscar bordes de bloques con alta varianza
        bordes_sospechosos = []
        for bloque in bloques_8x8:
            i, j = bloque['pos']
            varianza = bloque['varianza']
            
            # Si la varianza es muy alta, podría ser un borde de parche
            if varianza > np.mean([b['varianza'] for b in bloques_8x8]) * 3:
                bordes_sospechosos.append({
                    'pos': (i, j),
                    'varianza': varianza
                })
        
        splicing_analisis["bordes_sospechosos"] = len(bordes_sospechosos)
        splicing_analisis["bordes_detalles"] = bordes_sospechosos[:10]  # Solo los primeros 10
        
        # Análisis de localización
        localizacion_analisis = {}
        
        if bordes_sospechosos:
            # Calcular densidad de bordes sospechosos
            total_bloques = len(bloques_8x8)
            densidad_bordes = len(bordes_sospechosos) / total_bloques
            
            localizacion_analisis["densidad_bordes_sospechosos"] = densidad_bordes
            localizacion_analisis["es_localizado"] = densidad_bordes < 0.1  # Menos del 10% de la imagen
            
            # Detectar si los bordes están agrupados (posible parche)
            if len(bordes_sospechosos) > 1:
                posiciones = [b['pos'] for b in bordes_sospechosos]
                distancias = []
                for i in range(len(posiciones)):
                    for j in range(i+1, len(posiciones)):
                        dist = np.sqrt((posiciones[i][0] - posiciones[j][0])**2 + 
                                     (posiciones[i][1] - posiciones[j][1])**2)
                        distancias.append(dist)
                
                if distancias:
                    distancia_promedio = np.mean(distancias)
                    localizacion_analisis["distancia_promedio_bordes"] = distancia_promedio
                    localizacion_analisis["bordes_agrupados"] = distancia_promedio < 50  # Menos de 50 píxeles
                else:
                    localizacion_analisis["bordes_agrupados"] = False
            else:
                localizacion_analisis["bordes_agrupados"] = False
        else:
            localizacion_analisis["densidad_bordes_sospechosos"] = 0
            localizacion_analisis["es_localizado"] = False
            localizacion_analisis["bordes_agrupados"] = False
        
        # Determinar si hay evidencia de splicing
        tiene_splicing = (
            desalineacion_analisis["total_discontinuidades"] > 5 or
            (localizacion_analisis.get("es_localizado", False) and 
             localizacion_analisis.get("bordes_agrupados", False))
        )
        
        return safe_serialize_dict({
            "desalineacion_analisis": desalineacion_analisis,
            "splicing_analisis": splicing_analisis,
            "localizacion_analisis": localizacion_analisis,
            "tiene_splicing": tiene_splicing,
            "nivel_sospecha": "ALTO" if tiene_splicing else "BAJO"
        })
        
    except Exception as e:
        return {
            "error": f"Error en análisis de cuadrícula JPEG: {str(e)}",
            "tiene_splicing": False,
            "nivel_sospecha": "ERROR"
        }


def analizar_compresion_jpeg_avanzada(imagen_bytes: bytes) -> Dict[str, Any]:
    """
    Análisis avanzado de compresión JPEG.
    
    Args:
        imagen_bytes: Bytes de la imagen JPEG
        
    Returns:
        Dict con análisis de compresión
    """
    try:
        # Cargar imagen
        img = Image.open(io.BytesIO(imagen_bytes))
        
        # Análisis de calidad
        quality_analysis = {}
        
        # Recompresión a diferentes calidades para detectar la original
        calidades = [95, 90, 85, 80, 75, 70, 65, 60]
        diferencias = []
        
        for q in calidades:
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=q, optimize=False)
            buffer.seek(0)
            img_recomp = Image.open(buffer)
            
            # Calcular diferencia
            diff = ImageChops.difference(img, img_recomp)
            diff_array = np.array(diff)
            diff_mean = np.mean(diff_array)
            diferencias.append((q, diff_mean))
        
        # Encontrar la calidad más probable
        diferencias.sort(key=lambda x: x[1])
        calidad_probable = diferencias[0][0]
        quality_analysis["calidad_probable"] = calidad_probable
        quality_analysis["diferencias_por_calidad"] = diferencias
        
        # Análisis de doble compresión
        doble_compresion = {}
        
        # Detectar periodicidad en DCT
        img_array = np.array(img.convert('L'))
        dct_coeffs = []
        
        # Análisis de bloques 8x8
        for i in range(0, img_array.shape[0]-8, 8):
            for j in range(0, img_array.shape[1]-8, 8):
                block = img_array[i:i+8, j:j+8]
                dct = cv2.dct(block.astype(np.float32))
                dct_coeffs.append(dct[0, 0])  # DC coefficient
        
        # Análisis de periodicidad
        dct_array = np.array(dct_coeffs)
        dct_std = np.std(dct_array)
        dct_mean = np.mean(dct_array)
        
        doble_compresion["dc_coeffs_std"] = float(dct_std)
        doble_compresion["dc_coeffs_mean"] = float(dct_mean)
        doble_compresion["tiene_doble_compresion"] = dct_std > 50  # Umbral empírico
        
        # Análisis de tablas de cuantización
        tablas_analisis = {}
        
        # Detectar si las tablas son estándar
        if hasattr(img, '_getexif') and img._getexif():
            exif = img._getexif()
            if 0x0100 in exif:  # ImageWidth
                tablas_analisis["tiene_exif"] = True
            else:
                tablas_analisis["tiene_exif"] = False
        
        # Detectar si fue procesada por app
        app_indicators = []
        if not img._getexif() or len(img._getexif()) < 10:
            app_indicators.append("🚨 EXIF MINIMALISTA - POSIBLE APP DE MENSAJERÍA")
        
        if calidad_probable < 80:
            app_indicators.append("🚨 CALIDAD BAJA - POSIBLE COMPRESIÓN POR APP")
        
        return safe_serialize_dict({
            "quality_analysis": quality_analysis,
            "doble_compresion": doble_compresion,
            "tablas_analisis": tablas_analisis,
            "app_indicators": app_indicators
        })
        
    except Exception as e:
        return {
            "error": f"Error en análisis de compresión: {str(e)}",
            "quality_analysis": {},
            "doble_compresion": {},
            "tablas_analisis": {},
            "app_indicators": []
        }


def ela_mejorado(imagen_bytes: bytes, calidad: int = 95, amplificacion: int = 15) -> Dict[str, Any]:
    """
    ELA mejorado con amplificación y análisis visual.
    
    Args:
        imagen_bytes: Bytes de la imagen
        calidad: Calidad para recompresión
        amplificacion: Factor de amplificación
        
    Returns:
        Dict con análisis ELA mejorado
    """
    try:
        # Cargar imagen original
        img_original = Image.open(io.BytesIO(imagen_bytes)).convert("RGB")
        
        # Recompresión
        buffer_recomp = io.BytesIO()
        img_original.save(buffer_recomp, format='JPEG', quality=calidad, optimize=False)
        buffer_recomp.seek(0)
        img_recomp = Image.open(buffer_recomp)
        
        # Calcular diferencia
        diff = ImageChops.difference(img_original, img_recomp)
        
        # Amplificar diferencia
        diff_amplified = ImageEnhance.Brightness(diff).enhance(amplificacion)
        
        # Convertir a arrays para análisis
        orig_array = np.array(img_original)
        recomp_array = np.array(img_recomp)
        diff_array = np.array(diff)
        diff_amp_array = np.array(diff_amplified)
        
        # Análisis estadístico
        ela_mean = np.mean(diff_array)
        ela_std = np.std(diff_array)
        ela_max = np.max(diff_array)
        
        # Análisis de zonas sospechosas
        threshold = ela_mean + 2 * ela_std
        zonas_sospechosas = np.sum(diff_array > threshold)
        porcentaje_sospechoso = (zonas_sospechosas / diff_array.size) * 100
        
        # Análisis de bordes
        gray_diff = cv2.cvtColor(diff_amp_array, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray_diff, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # Detectar patrones de edición
        patrones_edicion = []
        
        # Detectar bordes rectangulares (posibles parches)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rectangulos = 0
        for contour in contours:
            if len(contour) >= 4:
                rect = cv2.minAreaRect(contour)
                if rect[1][0] > 50 and rect[1][1] > 50:  # Tamaño mínimo
                    rectangulos += 1
        
        if rectangulos > 0:
            patrones_edicion.append(f"🚨 {rectangulos} ZONAS RECTANGULARES DETECTADAS (posibles parches)")
        
        # Detectar gradientes anómalos
        grad_x = cv2.Sobel(gray_diff, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray_diff, cv2.CV_64F, 0, 1, ksize=3)
        grad_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        grad_std = np.std(grad_magnitude)
        if grad_std > 50:
            patrones_edicion.append("🚨 GRADIENTES ANÓMALOS DETECTADOS")
        
        # Determinar nivel de sospecha
        if porcentaje_sospechoso > 20 or edge_density > 0.2 or rectangulos > 2:
            nivel_sospecha = "ALTO"
        elif porcentaje_sospechoso > 10 or edge_density > 0.1 or rectangulos > 0:
            nivel_sospecha = "MEDIO"
        elif porcentaje_sospechoso > 5 or edge_density > 0.05:
            nivel_sospecha = "BAJO"
        else:
            nivel_sospecha = "NORMAL"
        
        return safe_serialize_dict({
            "ela_mean": float(ela_mean),
            "ela_std": float(ela_std),
            "ela_max": float(ela_max),
            "porcentaje_sospechoso": float(porcentaje_sospechoso),
            "edge_density": float(edge_density),
            "rectangulos_detectados": rectangulos,
            "grad_std": float(grad_std),
            "patrones_edicion": patrones_edicion,
            "nivel_sospecha": nivel_sospecha,
            "tiene_ediciones": nivel_sospecha != "NORMAL"
        })
        
    except Exception as e:
        return {
            "error": f"Error en ELA mejorado: {str(e)}",
            "nivel_sospecha": "ERROR",
            "tiene_ediciones": False
        }


def analizar_ruido_bordes_avanzado(imagen_bytes: bytes) -> Dict[str, Any]:
    """
    Análisis avanzado de ruido y bordes.
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        Dict con análisis de ruido y bordes
    """
    try:
        # Cargar imagen
        img = Image.open(io.BytesIO(imagen_bytes)).convert("RGB")
        img_array = np.array(img)
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Análisis de ruido
        ruido_analisis = {}
        
        # Varianza del Laplaciano
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        laplacian_var = np.var(laplacian)
        ruido_analisis["laplacian_variance"] = float(laplacian_var)
        
        # Análisis de ruido por regiones
        h, w = gray.shape
        regiones = [
            gray[0:h//2, 0:w//2],      # Superior izquierda
            gray[0:h//2, w//2:w],      # Superior derecha
            gray[h//2:h, 0:w//2],      # Inferior izquierda
            gray[h//2:h, w//2:w]       # Inferior derecha
        ]
        
        varianzas_regiones = [np.var(region) for region in regiones]
        ruido_analisis["varianzas_regiones"] = [float(v) for v in varianzas_regiones]
        ruido_analisis["diferencia_maxima_regiones"] = float(max(varianzas_regiones) - min(varianzas_regiones))
        
        # Detectar inconsistencias de ruido
        if ruido_analisis["diferencia_maxima_regiones"] > 1000:
            ruido_analisis["inconsistencias_ruido"] = "🚨 INCONSISTENCIAS DE RUIDO DETECTADAS"
        else:
            ruido_analisis["inconsistencias_ruido"] = "✅ Ruido consistente"
        
        # Análisis de bordes
        bordes_analisis = {}
        
        # Detectar bordes
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        bordes_analisis["edge_density"] = float(edge_density)
        
        # Detectar líneas
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=50, maxLineGap=10)
        if lines is not None:
            bordes_analisis["num_lines"] = len(lines)
            
            # Analizar líneas paralelas
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.arctan2(y2-y1, x2-x1) * 180 / np.pi
                angles.append(angle)
            
            # Detectar líneas paralelas
            parallel_lines = 0
            for i, angle1 in enumerate(angles):
                for j, angle2 in enumerate(angles[i+1:], i+1):
                    if abs(angle1 - angle2) < 5:  # 5 grados de tolerancia
                        parallel_lines += 1
            
            bordes_analisis["parallel_lines"] = parallel_lines
        else:
            bordes_analisis["num_lines"] = 0
            bordes_analisis["parallel_lines"] = 0
        
        # Detectar bordes con halo/aliasing
        halo_analisis = {}
        
        # Aplicar filtro gaussiano y comparar bordes
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges_blurred = cv2.Canny(blurred, 50, 150)
        
        # Comparar bordes originales vs borrosos
        edge_diff = cv2.bitwise_xor(edges, edges_blurred)
        halo_ratio = np.sum(edge_diff > 0) / np.sum(edges > 0) if np.sum(edges > 0) > 0 else 0
        
        halo_analisis["halo_ratio"] = float(halo_ratio)
        if halo_ratio > 0.3:
            halo_analisis["halo_detectado"] = "🚨 HALO/ALIASING DETECTADO"
        else:
            halo_analisis["halo_detectado"] = "✅ Sin halo/aliasing"
        
        # Detectar PNG con alpha "cuadrado perfecto"
        alpha_analisis = {}
        if img.mode == 'RGBA':
            alpha = img.split()[-1]
            alpha_array = np.array(alpha)
            
            # Detectar bordes rectangulares en alpha
            alpha_edges = cv2.Canny(alpha_array, 50, 150)
            contours, _ = cv2.findContours(alpha_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            rectangulos_alpha = 0
            for contour in contours:
                if len(contour) >= 4:
                    rect = cv2.minAreaRect(contour)
                    if rect[1][0] > 50 and rect[1][1] > 50:
                        rectangulos_alpha += 1
            
            alpha_analisis["rectangulos_alpha"] = rectangulos_alpha
            if rectangulos_alpha > 0:
                alpha_analisis["parches_alpha"] = "🚨 PARCHES DETECTADOS EN ALPHA"
            else:
                alpha_analisis["parches_alpha"] = "✅ Sin parches en alpha"
        else:
            alpha_analisis["rectangulos_alpha"] = 0
            alpha_analisis["parches_alpha"] = "N/A - No es PNG con alpha"
        
        return safe_serialize_dict({
            "ruido_analisis": ruido_analisis,
            "bordes_analisis": bordes_analisis,
            "halo_analisis": halo_analisis,
            "alpha_analisis": alpha_analisis
        })
        
    except Exception as e:
        return {
            "error": f"Error en análisis de ruido y bordes: {str(e)}",
            "ruido_analisis": {},
            "bordes_analisis": {},
            "halo_analisis": {},
            "alpha_analisis": {}
        }


def comparar_hashes_forenses(imagen_bytes: bytes) -> Dict[str, Any]:
    """
    Comparación de hashes forenses.
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        Dict con comparación de hashes
    """
    try:
        # Cargar imagen
        img = Image.open(io.BytesIO(imagen_bytes))
        
        # Hash fuerte (SHA-256)
        sha256 = hashlib.sha256(imagen_bytes).hexdigest()
        
        # Hashes perceptuales
        phash = str(imagehash.phash(img))
        dhash = str(imagehash.dhash(img))
        whash = str(imagehash.whash(img))
        colorhash = str(imagehash.colorhash(img))
        
        # Análisis de consistencia
        hashes_analisis = {
            "sha256": sha256,
            "phash": phash,
            "dhash": dhash,
            "whash": whash,
            "colorhash": colorhash
        }
        
        # Detectar inconsistencias
        inconsistencias = []
        
        # Comparar hashes perceptuales
        phash_int = int(phash, 16)
        dhash_int = int(dhash, 16)
        whash_int = int(whash, 16)
        
        # Calcular diferencias
        diff_ph_dh = bin(phash_int ^ dhash_int).count('1')
        diff_ph_wh = bin(phash_int ^ whash_int).count('1')
        diff_dh_wh = bin(dhash_int ^ whash_int).count('1')
        
        hashes_analisis["diferencias"] = {
            "phash_dhash": diff_ph_dh,
            "phash_whash": diff_ph_wh,
            "dhash_whash": diff_dh_wh
        }
        
        # Detectar inconsistencias significativas
        if diff_ph_dh > 20:
            inconsistencias.append("🚨 INCONSISTENCIA ENTRE pHash Y dHash")
        if diff_ph_wh > 20:
            inconsistencias.append("🚨 INCONSISTENCIA ENTRE pHash Y wHash")
        if diff_dh_wh > 20:
            inconsistencias.append("🚨 INCONSISTENCIA ENTRE dHash Y wHash")
        
        # Análisis de estabilidad
        estabilidad = {}
        
        # Probar con pequeñas variaciones
        img_array = np.array(img)
        
        # Variación 1: Rotación mínima
        img_rot = Image.fromarray(np.rot90(img_array, 1))
        phash_rot = str(imagehash.phash(img_rot))
        diff_rot = bin(int(phash, 16) ^ int(phash_rot, 16)).count('1')
        
        estabilidad["diferencia_rotacion"] = diff_rot
        if diff_rot > 15:
            estabilidad["estable_rotacion"] = "⚠️ Sensible a rotación"
        else:
            estabilidad["estable_rotacion"] = "✅ Estable a rotación"
        
        # Variación 2: Escala mínima
        img_scaled = img.resize((img.width//2, img.height//2)).resize((img.width, img.height))
        phash_scaled = str(imagehash.phash(img_scaled))
        diff_scaled = bin(int(phash, 16) ^ int(phash_scaled, 16)).count('1')
        
        estabilidad["diferencia_escala"] = diff_scaled
        if diff_scaled > 15:
            estabilidad["estable_escala"] = "⚠️ Sensible a escala"
        else:
            estabilidad["estable_escala"] = "✅ Estable a escala"
        
        return safe_serialize_dict({
            "hashes_analisis": hashes_analisis,
            "inconsistencias": inconsistencias,
            "estabilidad": estabilidad
        })
        
    except Exception as e:
        return {
            "error": f"Error en comparación de hashes: {str(e)}",
            "hashes_analisis": {},
            "inconsistencias": [],
            "estabilidad": {}
        }


def detectar_texto_sintetico_aplanado(imagen_bytes: bytes, metadatos_forenses: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Detecta texto sintético aplanado (pintado y re-guardado).
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        Dict con análisis de texto sintético
    """
    try:
        # Cargar imagen
        img = Image.open(io.BytesIO(imagen_bytes))
        img_array = np.array(img.convert('RGB'))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 1. Regla de re-guardado + bordes de texto
        reguardado_analisis = {}
        
        # Detectar bordes rectilíneos/horizontales densos
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)
        
        lineas_horizontales = 0
        lineas_verticales = 0
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.arctan2(y2-y1, x2-x1) * 180 / np.pi
                if abs(angle) < 15 or abs(angle - 180) < 15:  # Horizontal
                    lineas_horizontales += 1
                elif abs(angle - 90) < 15 or abs(angle + 90) < 15:  # Vertical
                    lineas_verticales += 1
        
        reguardado_analisis["lineas_horizontales"] = lineas_horizontales
        reguardado_analisis["lineas_verticales"] = lineas_verticales
        reguardado_analisis["densidad_lineas"] = (lineas_horizontales + lineas_verticales) / (img_array.shape[0] * img_array.shape[1] / 10000)
        
        # 2. Detección de texto sin OCR (método alternativo)
        swt_analisis = {}
        
        # Detectar regiones de texto usando análisis de bordes
        text_boxes = []
        
        # Usar detección de contornos para encontrar regiones rectangulares
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            if len(contour) > 4:
                # Aproximar contorno a rectángulo
                rect = cv2.minAreaRect(contour)
                width, height = rect[1]
                
                # Filtrar regiones que podrían ser texto (rectangulares, tamaño apropiado)
                if (width > 20 and height > 10 and width < 500 and height < 100 and 
                    abs(width - height) > 5):  # No cuadrados perfectos
                    
                    # Obtener coordenadas del rectángulo
                    box = cv2.boxPoints(rect)
                    box = np.intp(box)  # np.int0 fue deprecado, usar np.intp
                    x, y, w, h = cv2.boundingRect(box)
                    
                    # Verificar que la región tenga características de texto
                    if w > 0 and h > 0:
                        roi = gray[y:y+h, x:x+w]
                        if roi.size > 0:
                            # Calcular densidad de bordes (texto tiene muchos bordes)
                            roi_edges = cv2.Canny(roi, 50, 150)
                            edge_density = np.sum(roi_edges > 0) / roi.size
                            
                            # Si tiene suficiente densidad de bordes, podría ser texto
                            if edge_density > 0.05:  # 5% de píxeles son bordes
                                text_boxes.append((x, y, w, h))
        
        swt_analisis["cajas_texto_detectadas"] = len(text_boxes)
        swt_analisis["metodo_deteccion"] = "analisis_contornos"
        
        if text_boxes:
            # Calcular stroke width en cada caja
            stroke_widths = []
            for x, y, w, h in text_boxes:
                if x+w < img_array.shape[1] and y+h < img_array.shape[0]:
                    roi = gray[y:y+h, x:x+w]
                    if roi.size > 0:
                        # Aplicar SWT simplificado
                        edges_roi = cv2.Canny(roi, 50, 150)
                        if np.sum(edges_roi) > 0:
                            # Calcular grosor promedio de trazos
                            contours_roi, _ = cv2.findContours(edges_roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            for contour_roi in contours_roi:
                                if len(contour_roi) > 4:
                                    rect = cv2.minAreaRect(contour_roi)
                                    width = min(rect[1])
                                    if width > 0:
                                        stroke_widths.append(width)
            
            if stroke_widths:
                swt_analisis["stroke_width_mean"] = float(np.mean(stroke_widths))
                swt_analisis["stroke_width_std"] = float(np.std(stroke_widths))
                swt_analisis["stroke_width_uniforme"] = np.std(stroke_widths) < 1.5
            else:
                swt_analisis["stroke_width_uniforme"] = False
        else:
            swt_analisis["stroke_width_uniforme"] = False
        
        # 3. Alta frecuencia con baja entropía
        frecuencia_entropia_analisis = {}
        
        if text_boxes:
            energia_alta_freq = []
            entropia_color = []
            
            for x, y, w, h in text_boxes:
                if x+w < img_array.shape[1] and y+h < img_array.shape[0]:
                    roi = img_array[y:y+h, x:x+w]
                    if roi.size > 0:
                        # Energía de alta frecuencia (Laplaciano)
                        laplacian = cv2.Laplacian(cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY), cv2.CV_64F)
                        energia = np.sum(laplacian**2)
                        energia_alta_freq.append(energia)
                        
                        # Entropía del color
                        roi_flat = roi.reshape(-1, 3)
                        hist, _ = np.histogramdd(roi_flat, bins=8, range=((0, 256), (0, 256), (0, 256)))
                        hist_norm = hist / np.sum(hist)
                        hist_norm = hist_norm[hist_norm > 0]
                        entropia = -np.sum(hist_norm * np.log2(hist_norm))
                        entropia_color.append(entropia)
            
            if energia_alta_freq and entropia_color:
                frecuencia_entropia_analisis["energia_promedio"] = float(np.mean(energia_alta_freq))
                frecuencia_entropia_analisis["entropia_promedio"] = float(np.mean(entropia_color))
                frecuencia_entropia_analisis["texto_sintetico"] = (
                    np.mean(energia_alta_freq) > 1000 and 
                    np.mean(entropia_color) < 3.0
                )
            else:
                frecuencia_entropia_analisis["texto_sintetico"] = False
        else:
            frecuencia_entropia_analisis["texto_sintetico"] = False
        
        # 4. ELA focalizado en cajas de texto
        ela_focalizado_analisis = {}
        
        if text_boxes:
            # Recompresión a diferentes calidades
            calidades = [90, 75]
            ela_diferencias = []
            
            for q in calidades:
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=q, optimize=False)
                buffer.seek(0)
                img_recomp = Image.open(buffer)
                
                # Calcular ELA solo en cajas de texto
                for x, y, w, h in text_boxes:
                    if x+w < img_array.shape[1] and y+h < img_array.shape[0]:
                        roi_orig = img_array[y:y+h, x:x+w]
                        roi_recomp = np.array(img_recomp)[y:y+h, x:x+w]
                        
                        if roi_orig.shape == roi_recomp.shape:
                            diff = np.abs(roi_orig.astype(np.float32) - roi_recomp.astype(np.float32))
                            ela_diferencias.append(np.mean(diff))
            
            if ela_diferencias:
                ela_focalizado_analisis["ela_promedio_cajas"] = float(np.mean(ela_diferencias))
                ela_focalizado_analisis["texto_brilla_ela"] = np.mean(ela_diferencias) > 10.0
            else:
                ela_focalizado_analisis["texto_brilla_ela"] = False
        else:
            ela_focalizado_analisis["texto_brilla_ela"] = False
        
        # 5. Análisis de color y anti-alias
        color_antialias_analisis = {}
        
        if text_boxes:
            colores_trazo = []
            gradientes_antialias = []
            
            for x, y, w, h in text_boxes:
                if x+w < img_array.shape[1] and y+h < img_array.shape[0]:
                    roi = img_array[y:y+h, x:x+w]
                    if roi.size > 0:
                        # Color medio del trazo (asumiendo que el texto es más oscuro)
                        roi_gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
                        trazo_mask = roi_gray < 128  # Píxeles oscuros
                        
                        if np.sum(trazo_mask) > 0:
                            color_trazo = np.mean(roi[trazo_mask])
                            colores_trazo.append(color_trazo)
                            
                            # Detectar gradiente suave (anti-alias)
                            edges_roi = cv2.Canny(roi_gray, 50, 150)
                            if np.sum(edges_roi) > 0:
                                # Buscar píxeles en el borde del texto
                                kernel = np.ones((3,3), np.uint8)
                                dilated = cv2.dilate(edges_roi, kernel, iterations=1)
                                border_mask = dilated - edges_roi
                                
                                if np.sum(border_mask) > 0:
                                    border_colors = roi[border_mask > 0]
                                    if len(border_colors) > 0:
                                        color_std = np.std(border_colors)
                                        gradientes_antialias.append(color_std)
            
            if colores_trazo:
                color_antialias_analisis["color_trazo_promedio"] = float(np.mean(colores_trazo))
                color_antialias_analisis["color_casi_puro"] = (
                    np.mean(colores_trazo) < 30 or np.mean(colores_trazo) > 225
                )
            else:
                color_antialias_analisis["color_casi_puro"] = False
            
            if gradientes_antialias:
                color_antialias_analisis["gradiente_estable"] = np.mean(gradientes_antialias) < 20.0
            else:
                color_antialias_analisis["gradiente_estable"] = False
        else:
            color_antialias_analisis["color_casi_puro"] = False
            color_antialias_analisis["gradiente_estable"] = False
        
        # Método de respaldo: análisis de patrones de texto sin OCR
        patrones_texto_analisis = {}
        
        if not text_boxes:  # Si no se detectaron cajas de texto
            # Buscar patrones de texto en toda la imagen
            # Detectar regiones con alta densidad de bordes horizontales
            kernel_horizontal = np.array([[-1, -1, -1], [2, 2, 2], [-1, -1, -1]])
            horizontal_edges = cv2.filter2D(gray, -1, kernel_horizontal)
            
            # Detectar regiones con patrones de texto (líneas horizontales densas)
            text_regions = horizontal_edges > np.percentile(horizontal_edges, 90)
            
            # Calcular métricas de texto sintético en regiones sospechosas
            if np.sum(text_regions) > 0:
                # Análisis de color en regiones de texto
                text_pixels = img_array[text_regions]
                if len(text_pixels) > 0:
                    color_std = np.std(text_pixels, axis=0)
                    patrones_texto_analisis["color_uniforme"] = np.mean(color_std) < 20
                    
                    # Análisis de gradientes
                    text_gray = gray[text_regions]
                    if len(text_gray) > 0:
                        gradient_std = np.std(text_gray)
                        patrones_texto_analisis["gradiente_estable"] = gradient_std < 30
                    else:
                        patrones_texto_analisis["gradiente_estable"] = False
                else:
                    patrones_texto_analisis["color_uniforme"] = False
                    patrones_texto_analisis["gradiente_estable"] = False
            else:
                patrones_texto_analisis["color_uniforme"] = False
                patrones_texto_analisis["gradiente_estable"] = False
        else:
            patrones_texto_analisis["color_uniforme"] = False
            patrones_texto_analisis["gradiente_estable"] = False
        
        # Determinar si hay texto sintético aplanado (regla AND más estricta)
        # Requiere coherencia de múltiples indicadores, no solo uno
        texto_sintetico_probable = (
            swt_analisis.get("stroke_width_uniforme", False) and  # grosor muy uniforme
            ela_focalizado_analisis.get("texto_brilla_ela", False) and  # brilla en ELA
            (color_antialias_analisis.get("color_casi_puro", False) or 
             color_antialias_analisis.get("gradiente_estable", False))  # color puro O gradiente estable
        )
        
        # Indicador adicional: alta densidad de líneas rectangulares
        tiene_patrones_rectangulares = reguardado_analisis["densidad_lineas"] > 0.15
        
        # Solo marcar como sintético si hay coherencia de indicadores
        tiene_texto_sintetico = texto_sintetico_probable or (
            tiene_patrones_rectangulares and 
            (frecuencia_entropia_analisis.get("texto_sintetico", False) or
             patrones_texto_analisis.get("color_uniforme", False))
        )
        
        # Clasificación de tipo de imagen para reducir falsos positivos
        tipo_imagen_analisis = {}
        
        # Detectar captura de pantalla o imagen web
        height, width = img_array.shape[:2]
        es_resolucion_redonda = (width in [900, 1080, 1200, 1600] and height in [600, 900, 1200, 1600, 1920])
        tiene_muchas_lineas = reguardado_analisis["densidad_lineas"] > 0.2
        exif_vacio = not metadatos_forenses.get("exif_completo", {})
        
        # Detectar patrones de screenshot
        es_screenshot = (
            es_resolucion_redonda and
            tiene_muchas_lineas and
            exif_vacio and
            swt_analisis.get("cajas_texto_detectadas", 0) > 5
        )
        
        tipo_imagen_analisis["es_screenshot"] = es_screenshot
        tipo_imagen_analisis["resolucion_redonda"] = es_resolucion_redonda
        tipo_imagen_analisis["tiene_muchas_lineas"] = tiene_muchas_lineas
        tipo_imagen_analisis["exif_vacio"] = exif_vacio
        tipo_imagen_analisis["cajas_texto_detectadas"] = swt_analisis.get("cajas_texto_detectadas", 0)
        
        # Ajustar detección basada en tipo de imagen
        if es_screenshot:
            # Para screenshots, ser más conservador
            tiene_texto_sintetico = texto_sintetico_probable  # Solo si hay coherencia total
            nivel_sospecha = "BAJO" if not tiene_texto_sintetico else "MEDIO"
        else:
            nivel_sospecha = "ALTO" if tiene_texto_sintetico else "BAJO"
        
        return safe_serialize_dict({
            "reguardado_analisis": reguardado_analisis,
            "swt_analisis": swt_analisis,
            "frecuencia_entropia_analisis": frecuencia_entropia_analisis,
            "ela_focalizado_analisis": ela_focalizado_analisis,
            "color_antialias_analisis": color_antialias_analisis,
            "patrones_texto_analisis": patrones_texto_analisis,
            "tipo_imagen_analisis": tipo_imagen_analisis,
            "tiene_texto_sintetico": tiene_texto_sintetico,
            "nivel_sospecha": nivel_sospecha
        })
        
    except Exception as e:
        return {
            "error": f"Error en análisis de texto sintético: {str(e)}",
            "tiene_texto_sintetico": False,
            "nivel_sospecha": "ERROR"
        }


def _compute_ela_map_np(pil_img: Image.Image, quality: int = 90, scale: float = 8.0) -> np.ndarray:
    """
    ELA como matriz (grises 0-255) - OPTIMIZADO para velocidad.
    """
    buf = io.BytesIO()
    pil_img.convert("RGB").save(buf, format="JPEG", quality=quality)
    resaved = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    ela = ImageChops.difference(pil_img.convert("RGB"), resaved)
    # Simplificar amplificación
    ela_enh = ImageEnhance.Brightness(ela).enhance(scale)
    return np.array(ela_enh.convert("L"))

def _mean_in_bbox(img_np: np.ndarray, x: int, y: int, w: int, h: int) -> float:
    H, W = img_np.shape[:2]
    x, y = max(0, x), max(0, y)
    x2, y2 = min(W, x + w), min(H, y + h)
    roi = img_np[y:y2, x:x2]
    return float(np.mean(roi)) if roi.size else 0.0

def _contrast_to_ring(bgr: np.ndarray, x: int, y: int, w: int, h: int, pad: int = 4) -> float:
    H, W = bgr.shape[:2]
    xa, ya = max(0, x - pad), max(0, y - pad)
    xb, yb = min(W, x + w + pad), min(H, y + h + pad)
    ring = bgr[ya:yb, xa:xb].copy()
    if ring.size == 0: return 0.0
    # quita interior
    ring[pad:pad+h, pad:pad+w] = 0
    roi = bgr[max(0,y):min(H,y+h), max(0,x):min(W,x+w)]
    if roi.size == 0: return 0.0
    return abs(float(np.mean(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY))) -
               float(np.mean(cv2.cvtColor(ring, cv2.COLOR_BGR2GRAY))))

def _edge_halo(bgr: np.ndarray, x: int, y: int, w: int, h: int) -> float:
    pad = 2
    H, W = bgr.shape[:2]
    xa, ya = max(0, x - pad), max(0, y - pad)
    xb, yb = min(W, x + w + pad), min(H, y + h + pad)
    region = bgr[ya:yb, xa:xb]
    if region.size == 0: return 0.0
    g = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    e = cv2.Canny(g, 60, 180)
    inner = e[pad:pad+h, pad:pad+w]
    ring = e.copy(); ring[pad:pad+h, pad:pad+w] = 0
    inner_d = float(np.mean(inner > 0)) if inner.size else 0.0
    ring_d = float(np.mean(ring > 0)) if ring.size else 0.0
    return ring_d - inner_d  # >0 indica halo externo más fuerte

def _overlay_score(ela_mean: float, contrast: float, halo: float) -> float:
    # ponderaciones más estrictas para evitar falsos positivos
    s_ela = min(1.0, ela_mean / 30.0)     # ELA más estricto
    s_con = min(1.0, contrast / 25.0)     # contraste más estricto
    s_hal = min(1.0, (halo + 0.15) / 0.4)  # halo más estricto
    return 0.5*s_ela + 0.3*s_con + 0.2*s_hal  # más peso al ELA

def detectar_texto_sobrepuesto(imagen_bytes: bytes,
                               lang: str = "spa+eng",
                               min_conf: int = 80,
                               score_umbral: float = 0.8) -> Dict[str, Any]:
    """
    Detector de texto sobrepuesto ULTRA-OPTIMIZADO para velocidad.
    """
    try:
        # Versión simplificada que solo detecta texto con alta confianza
        pil = Image.open(io.BytesIO(imagen_bytes)).convert("RGB")
        
        # OCR básico solo para palabras con alta confianza
        data = pytesseract.image_to_data(pil, lang=lang, output_type=Output.DICT)
        n = len(data["text"])
        resultados = []
        
        # Solo procesar las primeras 5 palabras con mayor confianza
        candidatos = []
        for i in range(n):
            txt = (data["text"][i] or "").strip()
            if not txt: continue
            conf = float(data["conf"][i]) if data["conf"][i] not in ("-1","") else -1.0
            if conf < min_conf: continue

            x, y = int(data["left"][i]), int(data["top"][i])
            w, h = int(data["width"][i]), int(data["height"][i])
            if h < 20 or w < 20 or w > pil.width*0.6 or h > pil.height*0.1: 
                continue
                
            candidatos.append((txt, conf, x, y, w, h))
        
        # Ordenar por confianza y tomar solo los 3 mejores
        candidatos.sort(key=lambda x: x[1], reverse=True)
        candidatos = candidatos[:3]
        
        for txt, conf, x, y, w, h in candidatos:
            # Score simplificado basado solo en confianza y tamaño
            size_score = min(1.0, (w * h) / (pil.width * pil.height * 0.01))
            conf_score = conf / 100.0
            score = 0.7 * conf_score + 0.3 * size_score

            resultados.append({
                "text": txt,
                "conf": conf,
                "bbox": [x, y, w, h],
                "features": {
                    "size_score": round(size_score, 3),
                    "conf_score": round(conf_score, 3)
                },
                "score": round(score, 3),
                "overlay": bool(score >= score_umbral)
            })

        # Resumen
        overlays = [r for r in resultados if r["overlay"]]
        resumen = {
            "n_palabras": len(resultados),
            "n_overlays": len(overlays),
            "max_score": max([r["score"] for r in resultados], default=0.0),
            "mean_score_overlay": float(np.mean([r["score"] for r in overlays])) if overlays else 0.0
        }

        return safe_serialize_dict({
            "items": resultados,
            "resumen": resumen
        })

    except Exception as e:
        return {
            "error": f"Error en detección de texto sobrepuesto: {str(e)}",
            "items": [],
            "resumen": {"n_palabras": 0, "n_overlays": 0, "max_score": 0.0, "mean_score_overlay": 0.0}
        }


def analisis_forense_completo(imagen_bytes: bytes) -> Dict[str, Any]:
    """
    Análisis forense ULTRA-OPTIMIZADO para velocidad.
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        Dict con análisis forense completo
    """
    try:
        # Solo análisis más importantes y rápidos
        metadatos = analizar_metadatos_forenses(imagen_bytes)
        
        # Análisis de texto sintético (importante mantener)
        texto_sintetico = detectar_texto_sintetico_aplanado(imagen_bytes, metadatos)
        
        # Análisis simplificados para velocidad
        compresion = {"doble_compresion": {"tiene_doble_compresion": False}}
        cuadricula_jpeg = {"tiene_cuadricula": False}
        ela = {"tiene_ediciones": False}
        ruido_bordes = {"ruido_analisis": {"inconsistencias_ruido": ""}}
        hashes = {"inconsistencias": []}
        
        # 🔎 Detector de texto sobrepuesto (ya optimizado)
        overlays = detectar_texto_sobrepuesto(imagen_bytes)
        n_over = overlays.get("resumen", {}).get("n_overlays", 0)
        
        # Generar reporte consolidado
        evidencias = []
        puntuacion = 0
        max_puntuacion = 0
        
        # Análisis de metadatos
        if metadatos.get("software_edicion"):
            for evidencia in metadatos["software_edicion"]:
                if "🚨" in evidencia:
                    evidencias.append(evidencia)
                    puntuacion += 3
                else:
                    evidencias.append(evidencia)
                    puntuacion += 1
        max_puntuacion += 5
        
        # Análisis de fechas
        if metadatos.get("fechas_analisis"):
            for evidencia in metadatos["fechas_analisis"]:
                if "🚨" in evidencia:
                    evidencias.append(evidencia)
                    puntuacion += 3
                else:
                    evidencias.append(evidencia)
                    puntuacion += 1
        max_puntuacion += 3
        
        # Análisis de compresión
        if compresion.get("app_indicators"):
            for evidencia in compresion["app_indicators"]:
                if "🚨" in evidencia:
                    evidencias.append(evidencia)
                    puntuacion += 2
        max_puntuacion += 2
        
        # Análisis de cuadrícula JPEG
        if cuadricula_jpeg.get("tiene_splicing"):
            evidencias.append("🚨 CUADRÍCULA JPEG LOCALIZADA - POSIBLE SPLICING")
            puntuacion += 4
        elif cuadricula_jpeg.get("desalineacion_analisis", {}).get("total_discontinuidades", 0) > 2:
            evidencias.append("⚠️ Desalineación de bloques JPEG detectada")
            puntuacion += 2
        max_puntuacion += 4
        
        # Análisis de texto sintético aplanado
        # Análisis de texto sintético (lógica mejorada)
        es_screenshot = texto_sintetico.get("tipo_imagen_analisis", {}).get("es_screenshot", False)
        
        if texto_sintetico.get("tiene_texto_sintetico"):
            if es_screenshot:
                evidencias.append("⚠️ Texto sintético en screenshot/web")
                puntuacion += 2  # Menos penalización para screenshots
            else:
                evidencias.append("🚨 TEXTO SINTÉTICO APLANADO DETECTADO")
                puntuacion += 5
        elif texto_sintetico.get("reguardado_analisis", {}).get("densidad_lineas", 0) > 0.15:  # Umbral más alto
            if es_screenshot:
                evidencias.append("ℹ️ Alta densidad de líneas (screenshot)")
                puntuacion += 0  # No penalizar screenshots
            else:
                evidencias.append("⚠️ Alta densidad de líneas rectilíneas")
                puntuacion += 2
        elif texto_sintetico.get("swt_analisis", {}).get("stroke_width_uniforme", False):
            if es_screenshot:
                evidencias.append("ℹ️ Grosor uniforme (screenshot)")
                puntuacion += 0  # No penalizar screenshots
            else:
                evidencias.append("⚠️ Grosor de trazo uniforme (texto sintético)")
                puntuacion += 2
        max_puntuacion += 5
        
        # Análisis ELA (requerir evidencia localizada)
        if ela.get("tiene_ediciones"):
            if ela.get("nivel_sospecha") == "ALTO":
                evidencias.append(f"🚨 ELA detectó ediciones significativas (nivel: {ela.get('nivel_sospecha', 'N/A')})")
                puntuacion += 3
            elif ela.get("nivel_sospecha") == "MEDIO":
                # Solo penalizar si hay evidencia localizada
                if cuadricula_jpeg.get("tiene_splicing") or texto_sintetico.get("tiene_texto_sintetico"):
                    evidencias.append(f"⚠️ ELA detectó ediciones + evidencia localizada (nivel: {ela.get('nivel_sospecha', 'N/A')})")
                    puntuacion += 2
                else:
                    evidencias.append(f"ℹ️ ELA detectó ediciones menores (posible compresión)")
                    puntuacion += 0  # No penalizar compresión normal
            else:
                evidencias.append(f"ℹ️ ELA detectó ediciones menores (posible compresión)")
                puntuacion += 0  # No penalizar compresión normal
        max_puntuacion += 3
        
        # Análisis de ruido y bordes (solo si hay evidencia localizada)
        if ruido_bordes.get("ruido_analisis", {}).get("inconsistencias_ruido", "").startswith("🚨"):
            if cuadricula_jpeg.get("tiene_splicing") or texto_sintetico.get("tiene_texto_sintetico"):
                evidencias.append("🚨 Inconsistencias de ruido + evidencia localizada")
                puntuacion += 2
            else:
                evidencias.append("ℹ️ Inconsistencias de ruido (posible compresión)")
                puntuacion += 0  # No penalizar compresión normal
        max_puntuacion += 2
        
        if ruido_bordes.get("halo_analisis", {}).get("halo_detectado", "").startswith("🚨"):
            if cuadricula_jpeg.get("tiene_splicing") or texto_sintetico.get("tiene_texto_sintetico"):
                evidencias.append("🚨 Halo/aliasing + evidencia localizada")
                puntuacion += 2
            else:
                evidencias.append("ℹ️ Halo/aliasing (posible compresión)")
                puntuacion += 0  # No penalizar compresión normal
        max_puntuacion += 2
        
        # Análisis de hashes
        if hashes.get("inconsistencias"):
            for evidencia in hashes["inconsistencias"]:
                evidencias.append(evidencia)
                puntuacion += 1
        max_puntuacion += 2
        
        # 🔎 Sumar evidencia por texto sobrepuesto
        if n_over > 0:
            evidencias.append(f"🚨 Texto sobrepuesto detectado en {n_over} caja(s) OCR")
            puntuacion += min(5, 2 + n_over)  # pesa de 2 a 5
        max_puntuacion += 5
        
        # Calcular grado de confianza (ajustado para screenshots)
        porcentaje_confianza = (puntuacion / max_puntuacion) * 100 if max_puntuacion > 0 else 0
        
        # Ajustar para screenshots
        if es_screenshot and porcentaje_confianza < 30:
            grado_confianza = "BAJO"
            evidencias.append("ℹ️ Imagen parece ser screenshot/web (recomprimida)")
        elif porcentaje_confianza > 70:
            grado_confianza = "ALTO"
        elif porcentaje_confianza > 40:
            grado_confianza = "MEDIO"
        else:
            grado_confianza = "BAJO"
        
        return safe_serialize_dict({
            "metadatos": metadatos,
            "compresion": compresion,
            "cuadricula_jpeg": cuadricula_jpeg,
            "texto_sintetico": texto_sintetico,
            "ela": ela,
            "ruido_bordes": ruido_bordes,
            "hashes": hashes,
            "overlays": overlays,  # 🔎 incluir resultados nuevos
            "evidencias": evidencias,
            "grado_confianza": grado_confianza,
            "porcentaje_confianza": float(porcentaje_confianza),
            "puntuacion": puntuacion,
            "max_puntuacion": max_puntuacion,
            "es_screenshot": es_screenshot,
            "tipo_imagen": "screenshot/web" if es_screenshot else "imagen_normal"
        })
        
    except Exception as e:
        return {
            "error": f"Error en análisis forense completo: {str(e)}",
            "evidencias": [],
            "grado_confianza": "ERROR",
            "porcentaje_confianza": 0.0
        }
