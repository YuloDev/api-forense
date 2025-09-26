import base64
import io
import time
import re
import numpy as np
import cv2
from datetime import datetime
from typing import List, Dict, Any, Optional
import pytesseract
from PIL import Image
import fitz  # PyMuPDF

try:
    from pyzbar.pyzbar import decode as zbar_decode
except Exception:
    zbar_decode = None

# Importar helpers migrados a la nueva arquitectura
from adapters.persistence.helpers.PDFHelpers import (
    is_scanned_image_pdf,
    extract_page_factura_data,
    extract_barcodes_from_image,
    preprocess_for_ocr_robust,
    validar_clave_acceso,
    intentar_corregir_clave,
    extraer_datos_factura_pdf_robust
)

from domain.entities.ocr_text import OCRText
from domain.ports.ocr_service import OCRServicePort


class OCRServiceAdapter(OCRServicePort):
    """Adaptador que implementa el servicio de OCR usando Tesseract"""
    
    def __init__(self, language: str = "spa+eng", min_confidence: int = 50):
        self.language = language
        self.min_confidence = min_confidence
    
    def extract_text_from_image(self, image_base64: str) -> OCRText:
        start_time = time.time()
        try:
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            processed = self._preprocess_image_for_ocr(image)

            cfg = "--oem 1 --psm 6 -c preserve_interword_spaces=1 -c user_defined_dpi=360"
            text_raw, avg_conf = self._ocr_with_conf(processed, cfg, self.language)

            text_norm = self._normalize_text_keep_lines(text_raw)
            text_norm = self._post_fix_long_digits(text_norm)

            return OCRText(
                text_raw=text_raw,
                text_normalized=text_norm,
                confidence=avg_conf,
                language=self.language,
                processing_time=time.time() - start_time,
                created_at=datetime.now(),
                source_type="image"
            )
        except Exception:
            return OCRText(
                text_raw="",
                text_normalized="",
                confidence=0.0,
                language=self.language,
                processing_time=time.time() - start_time,
                created_at=datetime.now(),
                source_type="image"
            )
    
    def extract_text_from_pdf(self, pdf_base64: str) -> List[OCRText]:
        start_time = time.time()
        out: List[OCRText] = []
        try:
            pdf_data = base64.b64decode(pdf_base64)
            
            # Primero intentar extracción de texto nativo
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            texto_nativo = ""
            for page in doc:
                texto_nativo += page.get_text("text") or ""
            doc.close()
            
            # Detectar si es PDF escaneado
            is_scanned = is_scanned_image_pdf(pdf_data, texto_nativo)
            
            if is_scanned:
                # Usar lógica robusta original para extraer datos
                factura_data = self._extract_factura_data_robust(pdf_data)
                
                # Procesar páginas individualmente para concatenar texto
                doc = fitz.open(stream=pdf_data, filetype="pdf")
                texto_total_raw = ""
                texto_total_normalized = ""
                confidences = []
                
                for i, page in enumerate(doc):
                    t0 = time.time()
                    
                    # Render a 200 DPI aprox
                    pix = page.get_pixmap(dpi=200, alpha=False)
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
                    img_proc = preprocess_for_ocr_robust(img)

                    # OCR texto corrido
                    conf = "--oem 3 --psm 6"
                    raw_text = pytesseract.image_to_string(img_proc, lang=self.language, config=conf)
                    
                    # Normalizar texto
                    norm_text = self._normalize_text_keep_lines(raw_text)
                    norm_text = self._post_fix_long_digits(norm_text)

                    # Concatenar texto de todas las páginas
                    if i > 0:
                        texto_total_raw += f"\n\n--- PÁGINA {i + 1} ---\n\n"
                        texto_total_normalized += f"\n\n--- PÁGINA {i + 1} ---\n\n"
                    
                    texto_total_raw += raw_text
                    texto_total_normalized += norm_text

                    # Calcular confianza de esta página
                    page_confidence = 95.0 if factura_data.get("claveAcceso") else 85.0
                    confidences.append(page_confidence)
                
                # Calcular confianza promedio de todas las páginas
                avg_confidence = sum(confidences) / len(confidences) if confidences else 85.0
                
                # Un solo resultado con texto de todas las páginas y datos extraídos
                out.append(OCRText(
                    text_raw=texto_total_raw,
                    text_normalized=texto_total_normalized,
                    confidence=avg_confidence,
                    language=self.language,
                    processing_time=time.time() - start_time,
                    created_at=datetime.now(),
                    source_type="pdf_scanned",
                    page_number=1,  # Un solo resultado
                    metadata={
                        "ruc": factura_data.get("ruc"),
                        "claveAcceso": factura_data.get("claveAcceso"),
                        "total": factura_data.get("total"),
                        "barcode_detected": factura_data.get("fuentes", {}).get("barcode", False),
                        "total_pages": len(doc),
                        "claves_barcode": factura_data.get("fuentes", {}).get("claves_barcode", [])
                    }
                ))
                
                doc.close()
            else:
                # Usar lógica normal para PDFs con texto nativo
                doc = fitz.open(stream=pdf_data, filetype="pdf")
                for i, page in enumerate(doc):
                    t0 = time.time()
                    if self._has_pdf_text_layer(page):
                        # Usa texto nativo
                        raw = page.get_text("text") or ""
                        norm = self._normalize_text_keep_lines(raw)
                        norm = self._post_fix_long_digits(norm)
                        conf = 100.0  # capa de texto
                    else:
                        # Rasteriza + preprocesa + OCR
                        pil = self._render_page(page, dpi=360)
                        pil = self._preprocess_image_for_ocr(pil)
                        cfg = "--oem 1 --psm 6 -c user_defined_dpi=360 -c preserve_interword_spaces=1"
                        raw, conf = self._ocr_with_conf(pil, cfg, self.language)
                        norm = self._normalize_text_keep_lines(raw)
                        norm = self._post_fix_long_digits(norm)

                    out.append(OCRText(
                        text_raw=raw,
                        text_normalized=norm,
                        confidence=conf,
                        language=self.language,
                        processing_time=time.time() - t0,
                        created_at=datetime.now(),
                        source_type="pdf",
                        page_number=i + 1
                    ))
                doc.close()
                
        except Exception as e:
            out.append(OCRText(
                text_raw="",
                text_normalized="",
                confidence=0.0,
                language=self.language,
                processing_time=time.time() - start_time,
                created_at=datetime.now(),
                source_type="pdf"
            ))
        return out
    
    def validate_text_quality(self, ocr_text: OCRText) -> bool:
        """Valida la calidad del texto extraído"""
        return (
            ocr_text.is_valid() and
            ocr_text.confidence >= self.min_confidence and
            len(ocr_text.get_clean_text()) > 0
        )
    
    def _normalize_text(self, text: str) -> str:
        """(Si aún la usas en algún lugar) redirige a la versión segura."""
        return self._normalize_text_keep_lines(text)
    
    def _extract_barcodes_from_image(self, img_array):
        """Extrae códigos de barras usando pyzbar"""
        return extract_barcodes_from_image(img_array)
    
    def _extract_page_factura_data(self, text: str) -> Dict[str, Any]:
        """Extrae datos de factura de una página específica"""
        return extract_page_factura_data(text)
    
    def _extract_factura_data_robust(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extrae datos de factura PDF usando OCR robusto y validación SRI
        Usa el helper migrado a la nueva arquitectura
        """
        return extraer_datos_factura_pdf_robust(pdf_bytes, self.language)
    
    def _has_pdf_text_layer(self, page) -> bool:
        txt = page.get_text("text") or ""
        return len(txt.strip()) >= 80  # umbral simple

    def _render_page(self, page, dpi: int = 360) -> Image.Image:
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    def _ocr_with_conf(self, img: Image.Image, config: str, lang: str) -> tuple[str, float]:
        """Ejecuta OCR con la misma config para texto y TSV y devuelve (texto, confianza_media)."""
        text = pytesseract.image_to_string(img, lang=lang, config=config)
        try:
            data = pytesseract.image_to_data(img, lang=lang, config=config, output_type=pytesseract.Output.DICT)
            vals = []
            for c in data.get("conf", []):
                try:
                    f = float(c)
                    if f >= 0:  # ignora -1
                        vals.append(f)
                except Exception:
                    continue
            avg_conf = (sum(vals) / len(vals)) if vals else 0.0
        except Exception:
            avg_conf = 0.0
        return text, avg_conf

    def _normalize_text_keep_lines(self, text: str) -> str:
        """Limpia sin destruir saltos de línea ni números."""
        if not text:
            return ""
        import re
        out = []
        for raw in text.replace("\r", "").split("\n"):
            ln = re.sub(r"[ \t]+", " ", raw).strip()
            # Correcciones SOLO en palabras, nunca tocar dígitos:
            ln = re.sub(r"\bee\s+NUMERO\s+DE\s+AUTORIZACI[ÓO0]N\b", "NUMERO DE AUTORIZACION", ln, flags=re.IGNORECASE)
            ln = re.sub(r"Razon\s+Social\s*/\s*Nombres\s+y\s+Apellidos\s*:\s*", "Razon Social / Nombres y Apellidos: ", ln, flags=re.IGNORECASE)
            ln = re.sub(r"Identificaci[oó0]n\s*:\s*", "Identificacion: ", ln, flags=re.IGNORECASE)
            ln = re.sub(r"Fecha\s+Emisi[oó0]n\s*:\s*", "Fecha Emision: ", ln, flags=re.IGNORECASE)
            out.append(ln)
        # Compacta líneas vacías múltiples
        text = "\n".join(l for l in out if l)
        return text.strip()

    def _post_fix_long_digits(self, text: str) -> str:
        """Une dígitos separados por espacios/guiones después de anclas típicas."""
        import re
        def _join_digits(s: str) -> str:
            return re.sub(r"(?<=\d)[\s-]+(?=\d)", "", s)
        labels = [r"CLAVE\s+DE\s+ACCESO", r"NUMERO\s+DE\s+AUTORIZACI[ÓO]N"]
        for lab in labels:
            for m in re.finditer(lab + r".{0,120}", text, flags=re.IGNORECASE | re.DOTALL):
                frag = text[m.start():m.end()]
                fixed = _join_digits(frag)
                text = text[:m.start()] + fixed + text[m.end():]
        return text

    def _preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Deskew + CLAHE + binarización adaptativa (mejor que OTSU puro)."""
        import cv2, numpy as np
        img = np.array(image)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # Upscale si es pequeño
        h, w = gray.shape
        if max(h, w) < 1200:
            sf = 1200.0 / max(h, w)
            gray = cv2.resize(gray, (int(w*sf), int(h*sf)), interpolation=cv2.INTER_CUBIC)

        # CLAHE para contraste local
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)

        # Deskew (estimación simple)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
        angle = 0.0
        if lines is not None:
            angs = []
            for rho, theta in lines[:,0]:
                deg = theta * 180 / np.pi
                if 80 < deg < 100:
                    angs.append(deg - 90)
            if angs:
                angle = float(np.median(angs))
        if abs(angle) > 0.3:
            (hh, ww) = gray.shape[:2]
            M = cv2.getRotationMatrix2D((ww/2, hh/2), angle, 1.0)
            gray = cv2.warpAffine(gray, M, (ww, hh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

        # Binarización adaptativa
        bin_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY, 31, 9)
        return Image.fromarray(bin_img)
