"""
Análisis forense avanzado para imágenes.

Implementa técnicas forenses profesionales:
1. Guardado de hashes y metadatos
2. ELA (Error Level Analysis) para JPEG
3. Detección de doble compresión
4. Análisis de ruido y bordes locales
5. pHash por bloques y SSIM regional
6. Sistema de grado de confianza

Autor: Sistema de Análisis Forense
Versión: 2.0
"""

import hashlib
import base64
import io
import json
import numpy as np
from PIL import Image
import cv2
from skimage.metrics import structural_similarity as ssim
from .type_conversion import ensure_python_bool, ensure_python_float, safe_serialize_dict
from skimage import measure
import imagehash
from typing import Dict, Any, List, Tuple, Optional
import datetime


def generar_hashes_completos(imagen_bytes: bytes) -> Dict[str, str]:
    """
    Genera todos los hashes forenses del archivo.
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        Dict con todos los hashes calculados
    """
    hashes = {
        "md5": hashlib.md5(imagen_bytes).hexdigest(),
        "sha1": hashlib.sha1(imagen_bytes).hexdigest(),
        "sha256": hashlib.sha256(imagen_bytes).hexdigest(),
        "sha512": hashlib.sha512(imagen_bytes).hexdigest(),
        "blake2b": hashlib.blake2b(imagen_bytes).hexdigest(),
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Hash perceptual para comparación visual
    try:
        img = Image.open(io.BytesIO(imagen_bytes))
        
        # Métodos disponibles en imagehash
        hash_methods = {
            "phash": imagehash.phash,
            "dhash": imagehash.dhash,
            "whash": imagehash.whash
        }
        
        # Verificar métodos adicionales disponibles
        if hasattr(imagehash, 'ahash'):
            hash_methods["ahash"] = imagehash.ahash
        if hasattr(imagehash, 'colorhash'):
            hash_methods["colorhash"] = imagehash.colorhash
        if hasattr(imagehash, 'crop_resistant_hash'):
            hash_methods["crop_resistant_hash"] = imagehash.crop_resistant_hash
        
        # Calcular hashes disponibles
        for hash_name, hash_func in hash_methods.items():
            try:
                hashes[hash_name] = str(hash_func(img))
            except Exception as e:
                hashes[hash_name] = f"Error: {str(e)}"
                
    except Exception as e:
        # Si hay error general, establecer todos los hashes como error
        hashes["phash"] = f"Error: {str(e)}"
        hashes["dhash"] = f"Error: {str(e)}"
        hashes["whash"] = f"Error: {str(e)}"
        hashes["ahash"] = f"Error: {str(e)}"
    
    return hashes


def analisis_ela_jpeg(imagen_bytes: bytes, calidad: int = 95) -> Dict[str, Any]:
    """
    Realiza Error Level Analysis (ELA) para detectar ediciones en JPEG.
    
    Args:
        imagen_bytes: Bytes de la imagen JPEG
        calidad: Calidad para recompresión (95 por defecto)
        
    Returns:
        Dict con resultados del análisis ELA
    """
    try:
        # Cargar imagen original
        img_original = Image.open(io.BytesIO(imagen_bytes))
        
        # Recompresión con calidad específica
        buffer_recomp = io.BytesIO()
        img_original.save(buffer_recomp, format='JPEG', quality=calidad, optimize=False)
        buffer_recomp.seek(0)
        img_recomp = Image.open(buffer_recomp)
        
        # Convertir a arrays numpy
        orig_array = np.array(img_original.convert('RGB'))
        recomp_array = np.array(img_recomp.convert('RGB'))
        
        # Calcular diferencia (ELA)
        ela_array = np.abs(orig_array.astype(np.float32) - recomp_array.astype(np.float32))
        ela_max = np.max(ela_array)
        
        # Normalizar ELA
        if ela_max > 0:
            ela_normalized = (ela_array / ela_max * 255).astype(np.uint8)
        else:
            ela_normalized = ela_array.astype(np.uint8)
        
        # Análisis estadístico
        ela_mean = np.mean(ela_array)
        ela_std = np.std(ela_array)
        ela_max_val = np.max(ela_array)
        
        # Detectar áreas sospechosas (valores altos en ELA) - Umbrales más conservadores
        threshold = ela_mean + 3 * ela_std  # Aumentado de 2 a 3 desviaciones estándar
        areas_sospechosas = np.sum(ela_array > threshold)
        porcentaje_sospechoso = (areas_sospechosas / ela_array.size) * 100
        
        # Detectar bordes en ELA (posibles ediciones) - Umbrales más estrictos
        gray_ela = cv2.cvtColor(ela_normalized, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray_ela, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # Umbrales balanceados: evita falsos positivos pero detecta ediciones reales
        # Considera sospechoso si hay evidencia clara de edición
        tiene_ediciones = (porcentaje_sospechoso > 8.0 and edge_density > 0.12) or \
                         (porcentaje_sospechoso > 15.0) or \
                         (edge_density > 0.13)  # Reducido de 0.18 a 0.13 para detectar ediciones de Paint
        
        # Niveles de sospecha balanceados
        if porcentaje_sospechoso > 25.0 or edge_density > 0.25:
            nivel_sospecha = "ALTO"
        elif porcentaje_sospechoso > 15.0 or edge_density > 0.18:
            nivel_sospecha = "MEDIO"
        elif porcentaje_sospechoso > 8.0 or edge_density > 0.13:  # Ajustado para detectar ediciones de Paint
            nivel_sospecha = "BAJO"
        else:
            nivel_sospecha = "NORMAL"
        
        return {
            "ela_mean": float(ela_mean),
            "ela_std": float(ela_std),
            "ela_max": float(ela_max_val),
            "porcentaje_sospechoso": float(porcentaje_sospechoso),
            "edge_density": float(edge_density),
            "tiene_ediciones": tiene_ediciones,
            "nivel_sospecha": nivel_sospecha
        }
        
    except Exception as e:
        return {
            "error": f"Error en análisis ELA: {str(e)}",
            "tiene_ediciones": False,
            "nivel_sospecha": "ERROR"
        }


def detectar_doble_compresion_jpeg(imagen_bytes: bytes) -> Dict[str, Any]:
    """
    Detecta doble compresión en archivos JPEG.
    
    Args:
        imagen_bytes: Bytes de la imagen JPEG
        
    Returns:
        Dict con resultados de detección de doble compresión
    """
    try:
        # Cargar imagen
        img = Image.open(io.BytesIO(imagen_bytes))
        
        # Convertir a escala de grises
        gray = img.convert('L')
        gray_array = np.array(gray)
        
        # Análisis de DCT (Discrete Cosine Transform)
        # En JPEG, la doble compresión deja patrones en los coeficientes DCT
        from scipy.fft import dct
        
        # Dividir en bloques de 8x8 (estándar JPEG)
        h, w = gray_array.shape
        bloques_8x8 = []
        
        for i in range(0, h-7, 8):
            for j in range(0, w-7, 8):
                bloque = gray_array[i:i+8, j:j+8]
                if bloque.shape == (8, 8):
                    bloques_8x8.append(bloque)
        
        if not bloques_8x8:
            return {"error": "Imagen demasiado pequeña para análisis DCT"}
        
        # Calcular DCT para cada bloque
        dct_coeffs = []
        for bloque in bloques_8x8:
            dct_block = dct(dct(bloque.T, norm='ortho').T, norm='ortho')
            dct_coeffs.append(dct_block)
        
        # Análisis de patrones de doble compresión
        dct_array = np.array(dct_coeffs)
        
        # El coeficiente DC (0,0) muestra patrones de doble compresión
        dc_coeffs = dct_array[:, 0, 0]
        dc_hist, dc_bins = np.histogram(dc_coeffs, bins=50)
        
        # Detectar periodicidad en histograma (indicador de doble compresión)
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(dc_hist, height=np.max(dc_hist) * 0.1)
        
        # Análisis de varianza en coeficientes AC
        ac_coeffs = dct_array[:, 1:, 1:].flatten()
        ac_variance = np.var(ac_coeffs)
        
        # Criterios para detectar doble compresión
        tiene_periodicidad = len(peaks) > 3
        varianza_alta = ac_variance > np.var(dc_coeffs) * 2
        
        doble_compresion = tiene_periodicidad or varianza_alta
        
        return safe_serialize_dict({
            "tiene_doble_compresion": ensure_python_bool(doble_compresion),
            "periodicidad_detectada": ensure_python_bool(tiene_periodicidad),
            "varianza_alta": ensure_python_bool(varianza_alta),
            "num_peaks": len(peaks),
            "ac_variance": ensure_python_float(ac_variance),
            "dc_variance": ensure_python_float(np.var(dc_coeffs)),
            "confianza": "ALTA" if doble_compresion and tiene_periodicidad else "MEDIA" if doble_compresion else "BAJA"
        })
        
    except Exception as e:
        return {
            "error": f"Error en detección de doble compresión: {str(e)}",
            "tiene_doble_compresion": False,
            "confianza": "ERROR"
        }


def analisis_ruido_bordes_locales(imagen_bytes: bytes) -> Dict[str, Any]:
    """
    Analiza ruido y bordes locales para detectar pegado/edición.
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        Dict con análisis de ruido y bordes
    """
    try:
        img = Image.open(io.BytesIO(imagen_bytes))
        img_array = np.array(img.convert('RGB'))
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Análisis de ruido
        # Calcular la varianza del Laplaciano (indicador de ruido)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Análisis de bordes
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # Detectar bordes rectos (posibles ediciones)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=50, maxLineGap=10)
        
        if lines is not None:
            num_lines = len(lines)
            # Calcular ángulos de las líneas
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                angles.append(angle)
            
            # Detectar líneas paralelas (indicador de edición)
            angle_hist, _ = np.histogram(angles, bins=36, range=(-180, 180))
            parallel_lines = np.sum(angle_hist > 1)  # Múltiples líneas en la misma dirección
        else:
            num_lines = 0
            parallel_lines = 0
        
        # Análisis de textura local
        # Dividir imagen en bloques y analizar cada uno
        h, w = gray.shape
        block_size = 64
        blocks_h = h // block_size
        blocks_w = w // block_size
        
        block_variances = []
        for i in range(blocks_h):
            for j in range(blocks_w):
                block = gray[i*block_size:(i+1)*block_size, j*block_size:(j+1)*block_size]
                block_var = np.var(block)
                block_variances.append(block_var)
        
        # Detectar bloques con varianza muy diferente (posible pegado)
        if block_variances:
            mean_var = np.mean(block_variances)
            std_var = np.std(block_variances)
            outliers = np.sum(np.abs(np.array(block_variances) - mean_var) > 2 * std_var)
            outlier_ratio = outliers / len(block_variances)
        else:
            outlier_ratio = 0
        
        # Detectar discontinuidades en bordes
        # Usar gradiente para detectar cambios abruptos
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # Detectar picos en el gradiente (posibles bordes de edición)
        gradient_peaks = np.sum(gradient_magnitude > np.mean(gradient_magnitude) + 2 * np.std(gradient_magnitude))
        peak_ratio = gradient_peaks / gradient_magnitude.size
        
        return {
            "laplacian_variance": float(laplacian_var),
            "edge_density": float(edge_density),
            "num_lines": int(num_lines),
            "parallel_lines": int(parallel_lines),
            "outlier_ratio": float(outlier_ratio),
            "gradient_peaks": int(gradient_peaks),
            "peak_ratio": float(peak_ratio),
            "tiene_edicion_local": outlier_ratio > 0.1 or peak_ratio > 0.05,
            "nivel_sospecha": "ALTO" if outlier_ratio > 0.2 or peak_ratio > 0.1 else "MEDIO" if outlier_ratio > 0.1 or peak_ratio > 0.05 else "BAJO"
        }
        
    except Exception as e:
        return {
            "error": f"Error en análisis de ruido y bordes: {str(e)}",
            "tiene_edicion_local": False,
            "nivel_sospecha": "ERROR"
        }


def phash_por_bloques(imagen_bytes: bytes, block_size: int = 64) -> Dict[str, Any]:
    """
    Calcula pHash por bloques para detectar diferencias locales.
    
    Args:
        imagen_bytes: Bytes de la imagen
        block_size: Tamaño de cada bloque
        
    Returns:
        Dict con análisis de pHash por bloques
    """
    try:
        img = Image.open(io.BytesIO(imagen_bytes))
        img_array = np.array(img.convert('RGB'))
        
        h, w = img_array.shape[:2]
        blocks_h = h // block_size
        blocks_w = w // block_size
        
        block_hashes = []
        block_differences = []
        
        for i in range(blocks_h):
            for j in range(blocks_w):
                # Extraer bloque
                block = img_array[i*block_size:(i+1)*block_size, j*block_size:(j+1)*block_size]
                block_img = Image.fromarray(block)
                
                # Calcular pHash del bloque
                block_hash = imagehash.phash(block_img)
                block_hashes.append(str(block_hash))
        
        # Calcular diferencias entre bloques adyacentes
        for i in range(len(block_hashes) - 1):
            hash1 = imagehash.hex_to_hash(block_hashes[i])
            hash2 = imagehash.hex_to_hash(block_hashes[i + 1])
            diff = hash1 - hash2
            block_differences.append(diff)
        
        if block_differences:
            mean_diff = np.mean(block_differences)
            std_diff = np.std(block_differences)
            max_diff = np.max(block_differences)
            
            # Detectar bloques muy diferentes (posible edición)
            outliers = np.sum(np.array(block_differences) > mean_diff + 2 * std_diff)
            outlier_ratio = outliers / len(block_differences)
        else:
            mean_diff = 0
            std_diff = 0
            max_diff = 0
            outlier_ratio = 0
        
        return {
            "num_bloques": len(block_hashes),
            "mean_difference": float(mean_diff),
            "std_difference": float(std_diff),
            "max_difference": int(max_diff),
            "outlier_ratio": float(outlier_ratio),
            "tiene_diferencias_locales": outlier_ratio > 0.2,
            "nivel_sospecha": "ALTO" if outlier_ratio > 0.3 else "MEDIO" if outlier_ratio > 0.2 else "BAJO"
        }
        
    except Exception as e:
        return {
            "error": f"Error en pHash por bloques: {str(e)}",
            "tiene_diferencias_locales": False,
            "nivel_sospecha": "ERROR"
        }


def ssim_regional(imagen_bytes: bytes, region_size: int = 128) -> Dict[str, Any]:
    """
    Calcula SSIM regional para detectar inconsistencias.
    
    Args:
        imagen_bytes: Bytes de la imagen
        region_size: Tamaño de cada región
        
    Returns:
        Dict con análisis SSIM regional
    """
    try:
        img = Image.open(io.BytesIO(imagen_bytes))
        gray = img.convert('L')
        gray_array = np.array(gray)
        
        h, w = gray_array.shape
        regions_h = h // region_size
        regions_w = w // region_size
        
        ssim_values = []
        
        # Comparar cada región con sus vecinas
        for i in range(regions_h):
            for j in range(regions_w):
                region = gray_array[i*region_size:(i+1)*region_size, j*region_size:(j+1)*region_size]
                
                # Comparar con región derecha
                if j < regions_w - 1:
                    right_region = gray_array[i*region_size:(i+1)*region_size, (j+1)*region_size:(j+2)*region_size]
                    ssim_val = ssim(region, right_region)
                    ssim_values.append(ssim_val)
                
                # Comparar con región inferior
                if i < regions_h - 1:
                    bottom_region = gray_array[(i+1)*region_size:(i+2)*region_size, j*region_size:(j+1)*region_size]
                    ssim_val = ssim(region, bottom_region)
                    ssim_values.append(ssim_val)
        
        if ssim_values:
            mean_ssim = np.mean(ssim_values)
            std_ssim = np.std(ssim_values)
            min_ssim = np.min(ssim_values)
            
            # Detectar regiones con baja similitud (posible edición)
            low_similarity = np.sum(np.array(ssim_values) < mean_ssim - 2 * std_ssim)
            low_sim_ratio = low_similarity / len(ssim_values)
        else:
            mean_ssim = 1.0
            std_ssim = 0.0
            min_ssim = 1.0
            low_sim_ratio = 0.0
        
        return {
            "num_comparaciones": len(ssim_values),
            "mean_ssim": float(mean_ssim),
            "std_ssim": float(std_ssim),
            "min_ssim": float(min_ssim),
            "low_similarity_ratio": float(low_sim_ratio),
            "tiene_inconsistencias": low_sim_ratio > 0.1,
            "nivel_sospecha": "ALTO" if low_sim_ratio > 0.2 else "MEDIO" if low_sim_ratio > 0.1 else "BAJO"
        }
        
    except Exception as e:
        return {
            "error": f"Error en SSIM regional: {str(e)}",
            "tiene_inconsistencias": False,
            "nivel_sospecha": "ERROR"
        }


def calcular_grado_confianza(analisis_completo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula el grado de confianza final basado en todos los análisis.
    
    Args:
        analisis_completo: Resultado de todos los análisis forenses
        
    Returns:
        Dict con grado de confianza y justificación
    """
    evidencias = []
    puntuacion = 0
    max_puntuacion = 0
    
    # Análisis ELA
    if "ela" in analisis_completo and not analisis_completo["ela"].get("error"):
        ela = analisis_completo["ela"]
        if ela.get("tiene_ediciones"):
            evidencias.append(f"ELA detectó ediciones (nivel: {ela.get('nivel_sospecha', 'N/A')})")
            if ela.get("nivel_sospecha") == "ALTO":
                puntuacion += 3
            elif ela.get("nivel_sospecha") == "MEDIO":
                puntuacion += 2
            else:
                puntuacion += 1
        max_puntuacion += 3
    
    # Doble compresión
    if "doble_compresion" in analisis_completo and not analisis_completo["doble_compresion"].get("error"):
        dc = analisis_completo["doble_compresion"]
        if dc.get("tiene_doble_compresion"):
            evidencias.append(f"Doble compresión detectada (confianza: {dc.get('confianza', 'N/A')})")
            if dc.get("confianza") == "ALTA":
                puntuacion += 3
            elif dc.get("confianza") == "MEDIA":
                puntuacion += 2
            else:
                puntuacion += 1
        max_puntuacion += 3
    
    # Ruido y bordes
    if "ruido_bordes" in analisis_completo and not analisis_completo["ruido_bordes"].get("error"):
        rb = analisis_completo["ruido_bordes"]
        if rb.get("tiene_edicion_local"):
            evidencias.append(f"Edición local detectada (nivel: {rb.get('nivel_sospecha', 'N/A')})")
            if rb.get("nivel_sospecha") == "ALTO":
                puntuacion += 2
            elif rb.get("nivel_sospecha") == "MEDIO":
                puntuacion += 1
        max_puntuacion += 2
    
    # pHash por bloques
    if "phash_bloques" in analisis_completo and not analisis_completo["phash_bloques"].get("error"):
        ph = analisis_completo["phash_bloques"]
        if ph.get("tiene_diferencias_locales"):
            evidencias.append(f"Diferencias locales detectadas (nivel: {ph.get('nivel_sospecha', 'N/A')})")
            if ph.get("nivel_sospecha") == "ALTO":
                puntuacion += 2
            elif ph.get("nivel_sospecha") == "MEDIO":
                puntuacion += 1
        max_puntuacion += 2
    
    # SSIM regional
    if "ssim_regional" in analisis_completo and not analisis_completo["ssim_regional"].get("error"):
        ss = analisis_completo["ssim_regional"]
        if ss.get("tiene_inconsistencias"):
            evidencias.append(f"Inconsistencias regionales detectadas (nivel: {ss.get('nivel_sospecha', 'N/A')})")
            if ss.get("nivel_sospecha") == "ALTO":
                puntuacion += 2
            elif ss.get("nivel_sospecha") == "MEDIO":
                puntuacion += 1
        max_puntuacion += 2
    
    # Calcular porcentaje de confianza
    if max_puntuacion > 0:
        porcentaje = (puntuacion / max_puntuacion) * 100
    else:
        porcentaje = 0
    
    # Determinar grado de confianza
    if porcentaje >= 70:
        grado = "ALTO"
        justificacion = "Múltiples evidencias forenses indican manipulación"
    elif porcentaje >= 40:
        grado = "MEDIO"
        justificacion = "Algunas evidencias sugieren posible manipulación"
    else:
        grado = "BAJO"
        justificacion = "Pocas o ninguna evidencia de manipulación"
    
    return {
        "grado_confianza": grado,
        "porcentaje_confianza": round(porcentaje, 1),
        "puntuacion": puntuacion,
        "max_puntuacion": max_puntuacion,
        "evidencias": evidencias,
        "justificacion": justificacion,
        "recomendacion": _generar_recomendacion(grado, evidencias)
    }


def _generar_recomendacion(grado: str, evidencias: List[str]) -> str:
    """Genera recomendación basada en el grado de confianza"""
    if grado == "ALTO":
        return "IMAGEN ALTAMENTE SOSPECHOSA - Se recomienda análisis forense adicional y verificación de origen"
    elif grado == "MEDIO":
        return "IMAGEN MODERADAMENTE SOSPECHOSA - Se recomienda verificación adicional del canal de origen"
    else:
        return "IMAGEN APARENTEMENTE AUTÉNTICA - Sin embargo, se recomienda verificar el canal de origen"


def analisis_forense_completo(imagen_bytes: bytes, tipo_archivo: str) -> Dict[str, Any]:
    """
    Realiza análisis forense completo de la imagen.
    
    Args:
        imagen_bytes: Bytes de la imagen
        tipo_archivo: Tipo de archivo detectado
        
    Returns:
        Dict con análisis forense completo
    """
    resultado = {
        "hashes": generar_hashes_completos(imagen_bytes),
        "timestamp_analisis": datetime.datetime.now().isoformat(),
        "tipo_archivo": tipo_archivo
    }
    
    # Análisis específicos para JPEG
    if tipo_archivo.upper() in ["JPEG", "JPG"]:
        resultado["ela"] = analisis_ela_jpeg(imagen_bytes)
        resultado["doble_compresion"] = detectar_doble_compresion_jpeg(imagen_bytes)
    
    # Análisis generales
    resultado["ruido_bordes"] = analisis_ruido_bordes_locales(imagen_bytes)
    resultado["phash_bloques"] = phash_por_bloques(imagen_bytes)
    resultado["ssim_regional"] = ssim_regional(imagen_bytes)
    
    # Calcular grado de confianza final
    resultado["grado_confianza"] = calcular_grado_confianza(resultado)
    
    return resultado
