#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para verificar que Tesseract esté funcionando correctamente en el servidor
"""

# Configurar Tesseract ANTES de importar cualquier módulo
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

import sys
import os
import json
from PIL import Image
import numpy as np

def verificar_tesseract():
    """Verifica que Tesseract esté funcionando correctamente"""
    
    print("🔍 VERIFICANDO TESSERACT")
    print("=" * 50)
    
    try:
        # Verificar que pytesseract esté disponible
        print("1. Verificando pytesseract...")
        print(f"   ✅ pytesseract importado correctamente")
        
        # Verificar la ruta configurada
        print("2. Verificando ruta de Tesseract...")
        tesseract_cmd = pytesseract.pytesseract.tesseract_cmd
        print(f"   Ruta configurada: {tesseract_cmd}")
        
        if os.path.exists(tesseract_cmd):
            print(f"   ✅ Archivo encontrado en: {tesseract_cmd}")
        else:
            print(f"   ❌ Archivo NO encontrado en: {tesseract_cmd}")
            return False
        
        # Verificar versión de Tesseract
        print("3. Verificando versión de Tesseract...")
        try:
            version = pytesseract.get_tesseract_version()
            print(f"   ✅ Versión de Tesseract: {version}")
        except Exception as e:
            print(f"   ❌ Error obteniendo versión: {e}")
            return False
        
        # Crear una imagen de prueba simple
        print("4. Creando imagen de prueba...")
        img = Image.new('RGB', (200, 50), color='white')
        
        # Agregar texto simple a la imagen
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        
        # Intentar usar una fuente del sistema
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((10, 15), "TEST OCR 123", fill='black', font=font)
        
        print("   ✅ Imagen de prueba creada")
        
        # Probar OCR
        print("5. Probando OCR...")
        try:
            text = pytesseract.image_to_string(img, lang='eng')
            print(f"   ✅ OCR funcionando")
            print(f"   Texto extraído: '{text.strip()}'")
            
            if "TEST" in text and "123" in text:
                print("   ✅ OCR extrajo el texto correctamente")
            else:
                print("   ⚠️ OCR extrajo texto pero no es el esperado")
                
        except Exception as e:
            print(f"   ❌ Error en OCR: {e}")
            return False
        
        # Probar con configuración específica
        print("6. Probando configuración específica...")
        try:
            config = "--oem 3 --psm 6"
            text = pytesseract.image_to_string(img, lang='eng', config=config)
            print(f"   ✅ OCR con configuración específica funcionando")
            print(f"   Texto extraído: '{text.strip()}'")
        except Exception as e:
            print(f"   ❌ Error en OCR con configuración: {e}")
            return False
        
        print("\n✅ TESSERACT FUNCIONANDO CORRECTAMENTE")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR VERIFICANDO TESSERACT: {e}")
        return False

def verificar_importaciones():
    """Verifica que las importaciones necesarias funcionen"""
    
    print("\n🔍 VERIFICANDO IMPORTACIONES")
    print("=" * 50)
    
    try:
        # Verificar importaciones básicas
        print("1. Verificando importaciones básicas...")
        import fitz
        print("   ✅ PyMuPDF (fitz) importado")
        
        import cv2
        print("   ✅ OpenCV importado")
        
        import numpy as np
        print("   ✅ NumPy importado")
        
        from PIL import Image
        print("   ✅ Pillow importado")
        
        # Verificar importaciones del proyecto
        print("2. Verificando importaciones del proyecto...")
        
        # Cambiar al directorio del proyecto
        project_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, project_dir)
        
        from helpers.pdf_factura_parser import extraer_datos_factura_pdf
        print("   ✅ pdf_factura_parser importado")
        
        print("\n✅ TODAS LAS IMPORTACIONES FUNCIONANDO")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR EN IMPORTACIONES: {e}")
        return False

def main():
    """Función principal"""
    
    print("🚀 VERIFICACIÓN COMPLETA DEL SERVIDOR")
    print("=" * 60)
    
    # Verificar Tesseract
    tesseract_ok = verificar_tesseract()
    
    # Verificar importaciones
    imports_ok = verificar_importaciones()
    
    # Resumen final
    print("\n📊 RESUMEN FINAL")
    print("=" * 60)
    print(f"Tesseract: {'✅ OK' if tesseract_ok else '❌ ERROR'}")
    print(f"Importaciones: {'✅ OK' if imports_ok else '❌ ERROR'}")
    
    if tesseract_ok and imports_ok:
        print("\n🎉 SERVIDOR LISTO PARA FUNCIONAR")
        print("   Puedes iniciar el servidor con: python start_server.py")
    else:
        print("\n⚠️ HAY PROBLEMAS QUE RESOLVER")
        if not tesseract_ok:
            print("   - Verifica que Tesseract esté instalado correctamente")
        if not imports_ok:
            print("   - Verifica que todas las dependencias estén instaladas")

if __name__ == "__main__":
    main()