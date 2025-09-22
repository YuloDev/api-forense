#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para verificar que todas las dependencias estén instaladas
"""

import sys
import importlib

def verificar_modulo(nombre_modulo, nombre_pip=None):
    """Verifica si un módulo está instalado"""
    if nombre_pip is None:
        nombre_pip = nombre_modulo
    
    try:
        importlib.import_module(nombre_modulo)
        print(f"✅ {nombre_modulo}")
        return True
    except ImportError as e:
        print(f"❌ {nombre_modulo} - {e}")
        print(f"   Instalar con: pip install {nombre_pip}")
        return False

def main():
    """Verifica todas las dependencias"""
    print("🔍 Verificando dependencias de la API forense...")
    
    # Lista de dependencias principales
    dependencias = [
        # FastAPI y web
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pydantic", "pydantic"),
        
        # PDF y documentos
        ("pdfminer", "pdfminer.six"),
        ("fitz", "PyMuPDF"),
        ("pdfplumber", "pdfplumber"),
        ("pikepdf", "pikepdf"),
        
        # Imágenes y OCR
        ("PIL", "Pillow"),
        ("cv2", "opencv-python-headless"),
        ("numpy", "numpy"),
        ("easyocr", "easyocr"),
        ("pytesseract", "pytesseract"),
        ("pyzbar", "pyzbar"),
        
        # Análisis forense
        ("imagehash", "imagehash"),
        ("exifread", "exifread"),
        ("piexif", "piexif"),
        
        # SRI y SOAP
        ("zeep", "zeep"),
        ("requests", "requests"),
        ("lxml", "lxml"),
        ("isodate", "isodate"),
        
        # Utilidades
        ("dateutil", "python-dateutil"),
        ("multipart", "python-multipart"),
        ("typing_extensions", "typing_extensions"),
    ]
    
    print(f"\n📦 Verificando {len(dependencias)} dependencias...")
    
    exitosos = 0
    fallidos = 0
    
    for modulo, pip_name in dependencias:
        if verificar_modulo(modulo, pip_name):
            exitosos += 1
        else:
            fallidos += 1
    
    print(f"\n📊 Resumen:")
    print(f"   ✅ Exitosos: {exitosos}")
    print(f"   ❌ Fallidos: {fallidos}")
    
    if fallidos == 0:
        print("\n🎉 Todas las dependencias están instaladas correctamente!")
        return True
    else:
        print(f"\n💥 {fallidos} dependencias faltantes")
        print("   Instala las dependencias faltantes con:")
        print("   pip install -r requerimientos.txt")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
