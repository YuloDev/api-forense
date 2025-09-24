#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Servicio de OCR forense para extracción de texto de imágenes y PDFs
con análisis detallado para validación forense
"""

import time
import base64
import io
import hashlib
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter
import fitz  # PyMuPDF
import cv2
import numpy as np

# Usar configuración global de Tesseract
import configurar_tesseract_global
import pytesseract
from pytesseract import Output


class ForensicOCRService:
    """Servicio de OCR forense para análisis detallado de documentos"""
    
    def __init__(self):
        """Inicializar el servicio"""
        self.default_language = "spa+eng"
        self.default_min_confidence = 30
        self.default_config = '--oem 3 --psm 6'
        self.tesseract_version = self._get_tesseract_version()
    
    def _get_tesseract_version(self) -> str:
        """Obtener versión de Tesseract"""
        try:
            version = pytesseract.get_tesseract_version()
            return str(version)  # Convertir a string para serialización JSON
        except:
            return "unknown"
    
    def _calculate_file_hash(self, file_bytes: bytes) -> str:
        """Calcular SHA256 del archivo"""
        return hashlib.sha256(file_bytes).hexdigest()
    
    def _analyze_image_metadata(self, img: Image.Image) -> Dict[str, Any]:
        """Analizar metadatos de la imagen"""
        return {
            "size_pixels": img.size,
            "color_mode": img.mode,
            "dpi_estimated": self._estimate_dpi(img),
            "has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info,
            "format": img.format
        }
    
    def _estimate_dpi(self, img: Image.Image) -> Tuple[int, int]:
        """Estimar DPI de la imagen"""
        try:
            dpi = img.info.get('dpi', (72, 72))
            if isinstance(dpi, tuple) and len(dpi) == 2:
                return dpi
            return (72, 72)
        except:
            return (72, 72)
    
    def _preprocess_image(self, img: Image.Image) -> Tuple[Image.Image, Dict[str, Any]]:
        """Preprocesar imagen para OCR"""
        preprocessing_steps = []
        original_img = img.copy()
        
        # Convertir a RGB si es necesario
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
            preprocessing_steps.append("convert_to_rgb")
        
        # Detectar y corregir inclinación (deskew)
        deskew_angle = self._detect_skew(img)
        if abs(deskew_angle) > 0.5:
            img = img.rotate(-deskew_angle, expand=True)
            preprocessing_steps.append(f"deskew_{deskew_angle:.2f}")
        
        # Mejorar contraste
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        preprocessing_steps.append("contrast_enhancement")
        
        # Redimensionar si es muy pequeña
        resize_factor = 1.0
        if img.width < 800 or img.height < 600:
            scale = max(800 / img.width, 600 / img.height)
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            resize_factor = scale
            preprocessing_steps.append(f"resize_{scale:.2f}")
        
        return img, {
            "steps": preprocessing_steps,
            "deskew_angle": deskew_angle,
            "resize_factor": resize_factor,
            "original_size": original_img.size,
            "processed_size": img.size
        }
    
    def _detect_skew(self, img: Image.Image) -> float:
        """Detectar ángulo de inclinación de la imagen"""
        try:
            # Convertir a escala de grises
            gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
            
            # Aplicar detección de bordes
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Detectar líneas
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                angles = []
                for line in lines:
                    rho, theta = line[0]
                    angle = theta * 180 / np.pi
                    if 45 < angle < 135:  # Líneas horizontales
                        angles.append(90 - angle)
                
                if angles:
                    return float(np.median(angles))
            
            return 0.0
        except:
            return 0.0
    
    def _extract_tokens_with_geometry(self, data: Dict, img: Image.Image) -> List[Dict[str, Any]]:
        """Extraer tokens con geometría detallada"""
        tokens = []
        
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if not text:
                continue
            
            conf = int(data['conf'][i]) if data['conf'][i] != '-1' else 0
            x, y, w, h = int(data['left'][i]), int(data['top'][i]), int(data['width'][i]), int(data['height'][i])
            
            # Análisis de flags forenses
            flags = self._analyze_token_flags(text, conf, x, y, w, h, img)
            
            # Análisis de artefactos visuales
            artifacts = self._analyze_visual_artifacts(x, y, w, h, img)
            
            token = {
                "text": text,
                "normalized": self._normalize_text(text),
                "confidence": conf,
                "bbox": [x, y, w, h],
                "baseline": y + h,  # Aproximación
                "page_index": 0,  # Se actualizará por página
                "reading_order": i,
                "flags": flags,
                "artifacts": artifacts
            }
            
            tokens.append(token)
        
        return tokens
    
    def _analyze_token_flags(self, text: str, conf: int, x: int, y: int, w: int, h: int, img: Image.Image) -> Dict[str, Any]:
        """Analizar flags forenses del token"""
        return {
            "suspect": conf < 60 or self._has_irregular_borders(x, y, w, h, img),
            "digit_like": bool(re.match(r'^[\d\.,\-\+\(\)\s]+$', text)),
            "uppercase": text.isupper(),
            "low_confidence": conf < 60,
            "has_halo": self._detect_halo(x, y, w, h, img),
            "irregular_shape": self._is_irregular_shape(w, h)
        }
    
    def _has_irregular_borders(self, x: int, y: int, w: int, h: int, img: Image.Image) -> bool:
        """Detectar bordes irregulares en el token"""
        try:
            # Extraer región del token
            region = img.crop((x, y, x + w, y + h))
            gray = cv2.cvtColor(np.array(region), cv2.COLOR_RGB2GRAY)
            
            # Detectar bordes
            edges = cv2.Canny(gray, 50, 150)
            
            # Calcular irregularidad de bordes
            edge_density = float(np.sum(edges > 0) / (w * h))
            return edge_density > 0.3  # Umbral empírico
        except:
            return False
    
    def _detect_halo(self, x: int, y: int, w: int, h: int, img: Image.Image) -> bool:
        """Detectar halo alrededor del texto"""
        try:
            # Expandir región para analizar halo
            margin = 5
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(img.width, x + w + margin)
            y2 = min(img.height, y + h + margin)
            
            region = img.crop((x1, y1, x2, y2))
            gray = cv2.cvtColor(np.array(region), cv2.COLOR_RGB2GRAY)
            
            # Detectar gradientes alrededor del texto
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
            
            # Calcular score de halo
            halo_score = float(np.mean(gradient_magnitude))
            return halo_score > 50  # Umbral empírico
        except:
            return False
    
    def _is_irregular_shape(self, w: int, h: int) -> bool:
        """Detectar si la forma del token es irregular"""
        aspect_ratio = w / h if h > 0 else 1
        return aspect_ratio < 0.1 or aspect_ratio > 10  # Muy ancho o muy alto
    
    def _analyze_visual_artifacts(self, x: int, y: int, w: int, h: int, img: Image.Image) -> Dict[str, Any]:
        """Analizar artefactos visuales alrededor del texto"""
        try:
            region = img.crop((x, y, x + w, y + h))
            gray = cv2.cvtColor(np.array(region), cv2.COLOR_RGB2GRAY)
            
            # Análisis de ruido local
            noise = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            
            # Análisis de compresión JPEG
            jpeg_artifacts = self._detect_jpeg_artifacts(gray)
            
            return {
                "local_noise": float(noise),
                "jpeg_blockiness": jpeg_artifacts,
                "edge_halo_score": self._calculate_halo_score(gray)
            }
        except:
            return {
                "local_noise": 0.0,
                "jpeg_blockiness": 0.0,
                "edge_halo_score": 0.0
            }
    
    def _detect_jpeg_artifacts(self, gray: np.ndarray) -> float:
        """Detectar artefactos de compresión JPEG"""
        try:
            # Detectar patrones de bloques 8x8 típicos de JPEG
            h, w = gray.shape
            block_artifacts = 0
            
            for i in range(0, h-8, 8):
                for j in range(0, w-8, 8):
                    block = gray[i:i+8, j:j+8]
                    if block.shape == (8, 8):
                        # Calcular variación en bordes del bloque
                        edge_variation = float(np.var(block[0, :]) + np.var(block[:, 0]))
                        block_artifacts += edge_variation
            
            return float(block_artifacts / ((h//8) * (w//8)))
        except:
            return 0.0
    
    def _calculate_halo_score(self, gray: np.ndarray) -> float:
        """Calcular score de halo alrededor del texto"""
        try:
            # Detectar bordes
            edges = cv2.Canny(gray, 50, 150)
            
            # Calcular densidad de bordes en los márgenes
            h, w = gray.shape
            margin_size = min(5, h//4, w//4)
            
            if margin_size > 0:
                top_margin = edges[:margin_size, :]
                bottom_margin = edges[-margin_size:, :]
                left_margin = edges[:, :margin_size]
                right_margin = edges[:, -margin_size:]
                
                margin_density = float((
                    np.sum(top_margin > 0) + np.sum(bottom_margin > 0) +
                    np.sum(left_margin > 0) + np.sum(right_margin > 0)
                ) / (4 * margin_size * w))
                
                return float(margin_density)
            
            return 0.0
        except:
            return 0.0
    
    def _normalize_text(self, text: str) -> str:
        """Normalizar texto (lowercase, sin tildes, espacios normalizados)"""
        # Convertir a lowercase
        normalized = text.lower()
        
        # Remover tildes
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'ü': 'u'
        }
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        # Normalizar espacios
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _extract_entities(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extraer entidades financieras del texto"""
        entities = {
            "fechas": [],
            "montos": [],
            "monedas": [],
            "porcentajes_iva": [],
            "ruc_nif": [],
            "numeros_factura": [],
            "emails": [],
            "telefonos": []
        }
        
        # Detectar fechas
        fecha_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\b',
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
        ]
        for pattern in fecha_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities["fechas"].append({
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end()
                })
        
        # Detectar montos
        monto_patterns = [
            r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
            r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*USD',
            r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*EUR'
        ]
        for pattern in monto_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities["montos"].append({
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end()
                })
        
        # Detectar RUC/NIF
        ruc_pattern = r'\b\d{2,3}\s*\d{6,8}\s*\d{1}\b'
        for match in re.finditer(ruc_pattern, text):
            entities["ruc_nif"].append({
                "text": match.group(),
                "start": match.start(),
                "end": match.end()
            })
        
        # Detectar emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            entities["emails"].append({
                "text": match.group(),
                "start": match.start(),
                "end": match.end()
            })
        
        return entities
    
    def _extract_financial_totals(self, tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extraer totales financieros del documento"""
        totals = {
            "subtotal": None,
            "iva": None,
            "total": None,
            "items": []
        }
        
        # Buscar patrones de totales
        for token in tokens:
            text = token["normalized"]
            
            # Buscar subtotal
            if any(keyword in text for keyword in ["subtotal", "sub total", "base imponible"]):
                # Buscar número asociado
                for other_token in tokens:
                    if (other_token["bbox"][1] - token["bbox"][1]) < 20:  # Misma línea
                        if re.match(r'^\d+[.,]\d{2}$', other_token["text"]):
                            totals["subtotal"] = {
                                "value": other_token["text"],
                                "bbox": other_token["bbox"],
                                "confidence": other_token["confidence"]
                            }
                            break
            
            # Buscar IVA
            elif any(keyword in text for keyword in ["iva", "impuesto", "tax"]):
                for other_token in tokens:
                    if (other_token["bbox"][1] - token["bbox"][1]) < 20:
                        if re.match(r'^\d+[.,]\d{2}$', other_token["text"]):
                            totals["iva"] = {
                                "value": other_token["text"],
                                "bbox": other_token["bbox"],
                                "confidence": other_token["confidence"]
                            }
                            break
            
            # Buscar total
            elif any(keyword in text for keyword in ["total", "suma total"]):
                for other_token in tokens:
                    if (other_token["bbox"][1] - token["bbox"][1]) < 20:
                        if re.match(r'^\d+[.,]\d{2}$', other_token["text"]):
                            totals["total"] = {
                                "value": other_token["text"],
                                "bbox": other_token["bbox"],
                                "confidence": other_token["confidence"]
                            }
                            break
        
        return totals
    
    def _analyze_consistency(self, totals: Dict[str, Any]) -> Dict[str, Any]:
        """Analizar consistencia financiera"""
        consistency = {
            "subtotal_iva_equals_total": False,
            "items_sum_equals_subtotal": False,
            "warnings": []
        }
        
        try:
            # Convertir valores a números
            subtotal_val = self._parse_amount(totals.get("subtotal", {}).get("value", "0"))
            iva_val = self._parse_amount(totals.get("iva", {}).get("value", "0"))
            total_val = self._parse_amount(totals.get("total", {}).get("value", "0"))
            
            # Verificar si subtotal + IVA = total
            if subtotal_val > 0 and iva_val > 0 and total_val > 0:
                calculated_total = subtotal_val + iva_val
                if abs(calculated_total - total_val) < 0.01:  # Tolerancia de 1 centavo
                    consistency["subtotal_iva_equals_total"] = True
                else:
                    consistency["warnings"].append(f"Subtotal + IVA ({calculated_total:.2f}) ≠ Total ({total_val:.2f})")
            
        except Exception as e:
            consistency["warnings"].append(f"Error en análisis de consistencia: {str(e)}")
        
        return consistency
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parsear string de monto a float"""
        if not amount_str:
            return 0.0
        
        # Limpiar string
        cleaned = re.sub(r'[^\d.,]', '', amount_str)
        
        # Detectar separador decimal
        if ',' in cleaned and '.' in cleaned:
            # Formato: 1,234.56
            cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            # Formato: 1234,56
            cleaned = cleaned.replace(',', '.')
        
        try:
            return float(cleaned)
        except:
            return 0.0
    
    def extract_from_image(self, image_base64: str) -> Dict[str, Any]:
        """
        Extraer texto de una imagen con análisis forense completo
        
        Args:
            image_base64: Imagen codificada en base64
            
        Returns:
            Dict con análisis forense completo
        """
        start_time = time.perf_counter()
        
        try:
            # Decodificar imagen base64
            image_bytes = base64.b64decode(image_base64, validate=True)
            file_hash = self._calculate_file_hash(image_bytes)
            
            # Abrir imagen
            img = Image.open(io.BytesIO(image_bytes))
            
            # Analizar metadatos
            image_metadata = self._analyze_image_metadata(img)
            
            # Preprocesar imagen
            processed_img, preprocessing = self._preprocess_image(img)
            
            # Extraer datos detallados del OCR
            data = pytesseract.image_to_data(
                processed_img, 
                lang=self.default_language, 
                config=self.default_config,
                output_type=Output.DICT
            )
            
            # Procesar datos
            words = []
            total_confidence = 0
            valid_words = 0
            
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                if not text:
                    continue
                
                conf = int(data['conf'][i]) if data['conf'][i] != '-1' else 0
                
                if conf >= self.default_min_confidence:
                    words.append(text)
                    total_confidence += conf
                    valid_words += 1
            
            # Extraer tokens con geometría
            tokens = self._extract_tokens_with_geometry(data, processed_img)
            
            # Calcular estadísticas
            full_text = ' '.join(words)
            normalized_text = self._normalize_text(full_text)
            avg_confidence = total_confidence / valid_words if valid_words > 0 else 0
            
            # Extraer entidades
            entities = self._extract_entities(full_text)
            
            # Extraer totales financieros
            financial_totals = self._extract_financial_totals(tokens)
            
            # Analizar consistencia
            consistency = self._analyze_consistency(financial_totals)
            
            # Calcular estadísticas de confianza
            confidences = [t["confidence"] for t in tokens if t["confidence"] > 0]
            low_conf_count = len([c for c in confidences if c < 60])
            
            processing_time = time.perf_counter() - start_time
            
            return {
                "success": True,
                "identification": {
                    "doc_sha256": file_hash,
                    "source_type": "image",
                    "pages": 1,
                    "dpi_estimated": list(image_metadata["dpi_estimated"]),  # Convertir a lista
                    "size_pixels": list(image_metadata["size_pixels"]),  # Convertir a lista
                    "color_mode": str(image_metadata["color_mode"])  # Convertir a string
                },
                "preprocessing": preprocessing,
                "ocr_engine": {
                    "name": "tesseract",
                    "version": str(self.tesseract_version),  # Asegurar string
                    "lang_models": [self.default_language],
                    "config": self.default_config,
                    "binary_path": str(pytesseract.pytesseract.tesseract_cmd)  # Convertir a string
                },
                "document_analysis": {
                    "text_raw": full_text,
                    "text_normalized": normalized_text,
                    "confidence_mean": float(round(avg_confidence, 2)),  # Convertir a float nativo
                    "confidence_median": float(round(np.median(confidences) if confidences else 0, 2)),  # Convertir a float nativo
                    "low_conf_percentage": float(round((low_conf_count / len(confidences) * 100) if confidences else 0, 2)),  # Convertir a float nativo
                    "language_probs": {self.default_language: 1.0},
                    "script_stats": {"latin": len(words)}
                },
                "tokens": tokens,
                "entities": entities,
                "financial_analysis": {
                    "totals_extracted": financial_totals,
                    "consistency_hints": consistency
                },
                "processing_time": float(round(processing_time, 3)),  # Convertir a float nativo
                "error": None
            }
            
        except Exception as e:
            processing_time = time.perf_counter() - start_time
            
            return {
                "success": False,
                "identification": {
                    "doc_sha256": "",
                    "source_type": "image",
                    "pages": 0,
                    "dpi_estimated": [0, 0],
                    "size_pixels": [0, 0],
                    "color_mode": "unknown"
                },
                "preprocessing": {"steps": [], "deskew_angle": 0.0, "resize_factor": 1.0},
                "ocr_engine": {
                    "name": "tesseract",
                    "version": str(self.tesseract_version),
                    "lang_models": [],
                    "config": self.default_config,
                    "binary_path": ""
                },
                "document_analysis": {
                    "text_raw": "",
                    "text_normalized": "",
                    "confidence_mean": 0.0,
                    "confidence_median": 0.0,
                    "low_conf_percentage": 0.0,
                    "language_probs": {},
                    "script_stats": {}
                },
                "tokens": [],
                "entities": {},
                "financial_analysis": {
                    "totals_extracted": {},
                    "consistency_hints": {}
                },
                "processing_time": float(round(processing_time, 3)),
                "error": str(e)
            }
    
    def extract_from_pdf(self, pdf_base64: str) -> Dict[str, Any]:
        """
        Extraer texto de un PDF con análisis forense completo
        
        Args:
            pdf_base64: PDF codificado en base64
            
        Returns:
            Dict con análisis forense completo
        """
        start_time = time.perf_counter()
        
        try:
            # Decodificar PDF base64
            pdf_bytes = base64.b64decode(pdf_base64, validate=True)
            file_hash = self._calculate_file_hash(pdf_bytes)
            
            # Abrir PDF
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = pdf_document.page_count
            
            # Procesar cada página
            pages_data = []
            all_tokens = []
            all_entities = {}
            all_financial_totals = {}
            
            for page_num in range(total_pages):
                page = pdf_document[page_num]
                
                # Convertir página a imagen
                mat = fitz.Matrix(2.0, 2.0)  # Aumentar resolución
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Convertir a PIL Image
                img = Image.open(io.BytesIO(img_data))
                
                # Analizar metadatos de la página
                page_metadata = self._analyze_image_metadata(img)
                
                # Preprocesar imagen
                processed_img, preprocessing = self._preprocess_image(img)
                
                # Extraer texto con OCR
                data = pytesseract.image_to_data(
                    processed_img, 
                    lang=self.default_language, 
                    config=self.default_config,
                    output_type=Output.DICT
                )
                
                # Procesar datos de la página
                words = []
                page_confidence = 0
                valid_words = 0
                
                for i in range(len(data['text'])):
                    text = data['text'][i].strip()
                    if not text:
                        continue
                    
                    conf = int(data['conf'][i]) if data['conf'][i] != '-1' else 0
                    
                    if conf >= self.default_min_confidence:
                        words.append(text)
                        page_confidence += conf
                        valid_words += 1
                
                # Extraer tokens con geometría
                page_tokens = self._extract_tokens_with_geometry(data, processed_img)
                for token in page_tokens:
                    token["page_index"] = page_num
                
                # Extraer entidades de la página
                page_text = ' '.join(words)
                page_entities = self._extract_entities(page_text)
                
                # Extraer totales financieros de la página
                page_financial_totals = self._extract_financial_totals(page_tokens)
                
                # Calcular estadísticas de la página
                page_text_normalized = self._normalize_text(page_text)
                avg_page_confidence = page_confidence / valid_words if valid_words > 0 else 0
                
                pages_data.append({
                    "page_number": page_num + 1,
                    "text_raw": page_text,
                    "text_normalized": page_text_normalized,
                    "confidence": round(avg_page_confidence, 2),
                    "word_count": len(words),
                    "image_size": img.size,
                    "dpi_estimated": page_metadata["dpi_estimated"],
                    "preprocessing": preprocessing,
                    "tokens": page_tokens,
                    "entities": page_entities,
                    "financial_totals": page_financial_totals
                })
                
                all_tokens.extend(page_tokens)
                
                # Consolidar entidades
                for entity_type, entity_list in page_entities.items():
                    if entity_type not in all_entities:
                        all_entities[entity_type] = []
                    all_entities[entity_type].extend(entity_list)
            
            # Calcular estadísticas globales
            all_texts = [page["text_raw"] for page in pages_data]
            full_text = '\n\n'.join(all_texts)
            normalized_text = self._normalize_text(full_text)
            
            all_confidences = [t["confidence"] for t in all_tokens if t["confidence"] > 0]
            avg_confidence = float(np.mean(all_confidences)) if all_confidences else 0.0
            low_conf_count = len([c for c in all_confidences if c < 60])
            
            # Consolidar totales financieros
            for page in pages_data:
                page_totals = page["financial_totals"]
                for key, value in page_totals.items():
                    if value and key not in all_financial_totals:
                        all_financial_totals[key] = value
            
            # Analizar consistencia global
            consistency = self._analyze_consistency(all_financial_totals)
            
            processing_time = time.perf_counter() - start_time
            
            pdf_document.close()
            
            return {
                "success": True,
                "identification": {
                    "doc_sha256": file_hash,
                    "source_type": "pdf",
                    "pages": total_pages,
                    "dpi_estimated": [72, 72],  # PDFs no tienen DPI fijo
                    "size_pixels": list(pages_data[0]["image_size"]) if pages_data else [0, 0],
                    "color_mode": "RGB"
                },
                "preprocessing": {
                    "steps": ["pdf_to_image", "resize_2x"],
                    "deskew_angle": 0.0,
                    "resize_factor": 2.0
                },
                "ocr_engine": {
                    "name": "tesseract",
                    "version": str(self.tesseract_version),
                    "lang_models": [self.default_language],
                    "config": self.default_config,
                    "binary_path": str(pytesseract.pytesseract.tesseract_cmd)
                },
                "document_analysis": {
                    "text_raw": full_text,
                    "text_normalized": normalized_text,
                    "confidence_mean": float(round(avg_confidence, 2)),
                    "confidence_median": float(round(np.median(all_confidences) if all_confidences else 0, 2)),
                    "low_conf_percentage": float(round((low_conf_count / len(all_confidences) * 100) if all_confidences else 0, 2)),
                    "language_probs": {self.default_language: 1.0},
                    "script_stats": {"latin": len(all_tokens)}
                },
                "pages": pages_data,
                "tokens": all_tokens,
                "entities": all_entities,
                "financial_analysis": {
                    "totals_extracted": all_financial_totals,
                    "consistency_hints": consistency
                },
                "processing_time": float(round(processing_time, 3)),
                "error": None
            }
            
        except Exception as e:
            processing_time = time.perf_counter() - start_time
            
            return {
                "success": False,
                "identification": {
                    "doc_sha256": "",
                    "source_type": "pdf",
                    "pages": 0,
                    "dpi_estimated": [0, 0],
                    "size_pixels": [0, 0],
                    "color_mode": "unknown"
                },
                "preprocessing": {"steps": [], "deskew_angle": 0.0, "resize_factor": 1.0},
                "ocr_engine": {
                    "name": "tesseract",
                    "version": str(self.tesseract_version),
                    "lang_models": [],
                    "config": self.default_config,
                    "binary_path": ""
                },
                "document_analysis": {
                    "text_raw": "",
                    "text_normalized": "",
                    "confidence_mean": 0.0,
                    "confidence_median": 0.0,
                    "low_conf_percentage": 0.0,
                    "language_probs": {},
                    "script_stats": {}
                },
                "pages": [],
                "tokens": [],
                "entities": {},
                "financial_analysis": {
                    "totals_extracted": {},
                    "consistency_hints": {}
                },
                "processing_time": float(round(processing_time, 3)),
                "error": str(e)
            }


# Alias para compatibilidad
OCRService = ForensicOCRService