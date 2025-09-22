#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para verificar que Tesseract esté funcionando correctamente
en Windows (desarrollo) y Linux (Docker/producción)
"""

import os
import sys
import subprocess
import pytesseract
from PIL import Image
import tempfile

def verificar_tesseract():
    """Verifica que Tesseract esté instalado y funcionando"""
    print("🔍 Verificando configuración de Tesseract...")
    print(f"   Sistema operativo: {os.name}")
    print(f"   Plataforma: {sys.platform}")
    
    # 1. Verificar comando de Tesseract
    print("\n1️⃣ Verificando comando de Tesseract...")
    try:
        version = pytesseract.get_tesseract_version()
        print(f"   ✅ Tesseract versión: {version}")
    except Exception as e:
        print(f"   ❌ Error obteniendo versión: {e}")
        return False
    
    # 2. Verificar idiomas disponibles
    print("\n2️⃣ Verificando idiomas disponibles...")
    try:
        langs = pytesseract.get_languages()
        print(f"   ✅ Idiomas disponibles: {', '.join(langs)}")
        
        # Verificar idiomas específicos
        required_langs = ['eng', 'spa']
        missing_langs = [lang for lang in required_langs if lang not in langs]
        if missing_langs:
            print(f"   ⚠️ Idiomas faltantes: {', '.join(missing_langs)}")
        else:
            print(f"   ✅ Idiomas requeridos disponibles: {', '.join(required_langs)}")
    except Exception as e:
        print(f"   ❌ Error obteniendo idiomas: {e}")
        return False
    
    # 3. Crear imagen de prueba
    print("\n3️⃣ Creando imagen de prueba...")
    try:
        # Crear una imagen simple con texto
        from PIL import Image, ImageDraw, ImageFont
        
        # Crear imagen blanca
        img = Image.new('RGB', (200, 50), color='white')
        draw = ImageDraw.Draw(img)
        
        # Intentar usar una fuente, si no está disponible usar la por defecto
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        # Dibujar texto
        draw.text((10, 15), "Hello World", fill='black', font=font)
        
        print("   ✅ Imagen de prueba creada")
    except Exception as e:
        print(f"   ❌ Error creando imagen: {e}")
        return False
    
    # 4. Probar OCR
    print("\n4️⃣ Probando OCR...")
    try:
        # Extraer texto de la imagen
        text = pytesseract.image_to_string(img, lang='eng')
        print(f"   ✅ Texto extraído: '{text.strip()}'")
        
        if "Hello" in text or "World" in text:
            print("   ✅ OCR funcionando correctamente")
        else:
            print("   ⚠️ OCR funcionando pero texto no reconocido correctamente")
    except Exception as e:
        print(f"   ❌ Error en OCR: {e}")
        return False
    
    # 5. Probar con diferentes configuraciones
    print("\n5️⃣ Probando configuraciones avanzadas...")
    try:
        # Probar con configuración específica
        config = '--psm 6 --oem 3'
        text = pytesseract.image_to_string(img, lang='eng', config=config)
        print(f"   ✅ OCR con configuración avanzada: '{text.strip()}'")
    except Exception as e:
        print(f"   ⚠️ Error con configuración avanzada: {e}")
    
    print("\n✅ Verificación de Tesseract completada exitosamente")
    return True

def verificar_pyzbar():
    """Verifica que pyzbar esté funcionando"""
    print("\n🔍 Verificando pyzbar...")
    try:
        from pyzbar import pyzbar
        print("   ✅ pyzbar importado correctamente")
        
        # Probar con imagen vacía
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        barcodes = pyzbar.decode(img)
        print(f"   ✅ pyzbar funcionando (códigos encontrados: {len(barcodes)})")
        return True
    except Exception as e:
        print(f"   ❌ Error con pyzbar: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando verificación de dependencias OCR...")
    
    tesseract_ok = verificar_tesseract()
    pyzbar_ok = verificar_pyzbar()
    
    print(f"\n📊 Resumen:")
    print(f"   Tesseract: {'✅ OK' if tesseract_ok else '❌ ERROR'}")
    print(f"   pyzbar: {'✅ OK' if pyzbar_ok else '❌ ERROR'}")
    
    if tesseract_ok and pyzbar_ok:
        print("\n🎉 Todas las dependencias OCR están funcionando correctamente!")
        sys.exit(0)
    else:
        print("\n💥 Algunas dependencias OCR tienen problemas")
        sys.exit(1)