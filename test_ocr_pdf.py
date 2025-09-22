#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar la extracción de texto OCR de un PDF escaneado
"""

import base64
import fitz
import pytesseract
from PIL import Image
import numpy as np
import cv2
import io

# Configurar ruta de Tesseract para Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_for_ocr(img_bgr):
    """Preprocesamiento ligero para OCR"""
    g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    # ligera normalización y binarización adaptable
    g = cv2.bilateralFilter(g, 7, 40, 40)
    th = cv2.adaptiveThreshold(g,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 31, 15)
    return th

def test_ocr_pdf():
    """Prueba la extracción de texto OCR del PDF"""
    
    # Leer el PDF de prueba
    pdf_path = "helpers/IMG/Factura_imagen.pdf"
    
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        print(f"✅ PDF leído: {len(pdf_bytes)} bytes")
        
        # Abrir PDF con PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        print(f"📄 Páginas en PDF: {doc.page_count}")
        
        texto_total = ""
        
        for page_num, page in enumerate(doc):
            print(f"\n🔍 Procesando página {page_num + 1}...")
            
            # Intentar extracción de texto nativo primero
            texto_nativo = page.get_text("text")
            print(f"   Texto nativo: {len(texto_nativo)} caracteres")
            print(f"   Primeros 100 caracteres: {texto_nativo[:100]}")
            
            if len(texto_nativo.strip()) < 80:
                print("   📄 Usando OCR (texto nativo insuficiente)...")
                
                # Renderizar página como imagen
                pix = page.get_pixmap(dpi=200, alpha=False)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
                
                print(f"   Imagen renderizada: {img.shape}")
                
                # Preprocesar para OCR
                img_proc = preprocess_for_ocr(img)
                
                # Configuración OCR
                conf = "--oem 3 --psm 6"
                
                # Extraer texto con OCR
                texto_ocr = pytesseract.image_to_string(img_proc, lang='spa+eng', config=conf)
                
                print(f"   Texto OCR: {len(texto_ocr)} caracteres")
                print(f"   Primeros 200 caracteres OCR:")
                print(f"   {texto_ocr[:200]}")
                
                texto_total += "\n" + texto_ocr
            else:
                print("   ✅ Usando texto nativo (suficiente)")
                texto_total += "\n" + texto_nativo
        
        doc.close()
        
        print(f"\n📊 RESUMEN:")
        print(f"   Texto total extraído: {len(texto_total)} caracteres")
        print(f"   Primeros 500 caracteres:")
        print(f"   {texto_total[:500]}")
        
        # Buscar patrones de factura
        import re
        
        # Buscar RUC
        ruc_match = re.search(r'(?:R\.?U\.?C\.?:?|RUC[:\s]*)\s*([0-9]{13})', texto_total, re.I)
        if ruc_match:
            print(f"\n✅ RUC encontrado: {ruc_match.group(1)}")
        else:
            print(f"\n❌ RUC no encontrado")
        
        # Buscar Razón Social
        razon_match = re.search(r'(Raz[oó]n Social.*?:\s*)([^\n\r]+)', texto_total, re.I)
        if razon_match:
            print(f"✅ Razón Social encontrada: {razon_match.group(2).strip()}")
        else:
            print(f"❌ Razón Social no encontrada")
        
        # Buscar Fecha
        fecha_match = re.search(r'(?:Fecha(?: de Emisi[oó]n)?[:\s]*)\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', texto_total, re.I)
        if fecha_match:
            print(f"✅ Fecha encontrada: {fecha_match.group(1)}")
        else:
            print(f"❌ Fecha no encontrada")
        
        # Buscar Clave de Acceso
        clave_match = re.search(r'(?:Clave.*Acceso|N[uú]mero de autorizaci[oó]n)[:\s]*([0-9\s]{45,60})', texto_total, re.I)
        if clave_match:
            print(f"✅ Clave de Acceso encontrada: {clave_match.group(1)}")
        else:
            print(f"❌ Clave de Acceso no encontrada")
        
        # Buscar Total
        total_match = re.search(r'(VALOR\s+TOTAL|TOTAL)\D{0,30}([0-9]+[.,][0-9]{2})', texto_total, re.I)
        if total_match:
            print(f"✅ Total encontrado: {total_match.group(2)}")
        else:
            print(f"❌ Total no encontrado")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ocr_pdf()
