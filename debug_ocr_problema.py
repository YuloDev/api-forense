#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para debuggear el problema de OCR que no detecta nada
"""

import base64
import io
from PIL import Image, ImageDraw, ImageFont

def crear_imagen_debug():
    """Crea una imagen de prueba simple para debuggear"""
    # Crear imagen simple con texto grande y claro
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    # Texto simple y grande
    draw.text((20, 50), "FACTURA", fill='black', font=font)
    draw.text((20, 100), "RUC: 1234567890001", fill='black', font=font)
    draw.text((20, 150), "TOTAL: $100.00", fill='black', font=font)
    
    return img

def probar_ocr_paso_a_paso():
    """Prueba cada paso del OCR para ver dónde falla"""
    print("🔍 DEBUGGING OCR PASO A PASO")
    print("=" * 40)
    
    # Crear imagen de prueba
    img = crear_imagen_debug()
    print(f"✅ Imagen creada: {img.size} pixels, modo: {img.mode}")
    
    try:
        from helpers.invoice_capture_parser import (
            flatten_rgba_to_white,
            enhance_for_ocr,
            try_tess_configs,
            ocr_image
        )
        
        # Paso 1: Aplanar transparencia
        print("\n1️⃣ Probando aplanado de transparencia...")
        img_flattened = flatten_rgba_to_white(img)
        print(f"   Resultado: {img_flattened.mode} {img_flattened.size}")
        
        # Paso 2: Mejorar para OCR
        print("\n2️⃣ Probando mejora para OCR...")
        img_enhanced = enhance_for_ocr(img, scale=2.5)
        print(f"   Resultado: {img_enhanced.mode} {img_enhanced.size}")
        
        # Paso 3: Probar configuraciones Tesseract
        print("\n3️⃣ Probando configuraciones Tesseract...")
        try:
            text_configs = try_tess_configs(img_enhanced)
            print(f"   Texto extraído: '{text_configs[:100]}...'")
            print(f"   Longitud: {len(text_configs)} caracteres")
        except Exception as e:
            print(f"   ❌ Error en configuraciones: {e}")
            return False
        
        # Paso 4: OCR completo
        print("\n4️⃣ Probando OCR completo...")
        try:
            text_completo = ocr_image(img)
            print(f"   Texto final: '{text_completo[:100]}...'")
            print(f"   Longitud final: {len(text_completo)} caracteres")
            
            if len(text_completo) > 10:
                print("   ✅ OCR funcionando correctamente")
                return True
            else:
                print("   ⚠️  OCR extrajo poco texto")
                return False
                
        except Exception as e:
            print(f"   ❌ Error en OCR completo: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Error importando funciones: {e}")
        return False

def probar_tesseract_directo():
    """Prueba Tesseract directamente sin el parser"""
    print("\n🔧 PROBANDO TESSERACT DIRECTO")
    print("=" * 40)
    
    try:
        import pytesseract
        from PIL import Image
        
        # Crear imagen simple
        img = crear_imagen_debug()
        
        # Probar Tesseract básico
        print("1️⃣ Probando Tesseract básico...")
        try:
            text_basico = pytesseract.image_to_string(img, lang='eng')
            print(f"   Texto básico: '{text_basico.strip()}'")
            print(f"   Longitud: {len(text_basico)} caracteres")
        except Exception as e:
            print(f"   ❌ Error Tesseract básico: {e}")
            return False
        
        # Probar con español
        print("\n2️⃣ Probando con español...")
        try:
            text_español = pytesseract.image_to_string(img, lang='spa')
            print(f"   Texto español: '{text_español.strip()}'")
            print(f"   Longitud: {len(text_español)} caracteres")
        except Exception as e:
            print(f"   ❌ Error con español: {e}")
        
        # Probar con configuración específica
        print("\n3️⃣ Probando con configuración específica...")
        try:
            text_config = pytesseract.image_to_string(img, lang='eng', config='--psm 6')
            print(f"   Texto con PSM 6: '{text_config.strip()}'")
            print(f"   Longitud: {len(text_config)} caracteres")
        except Exception as e:
            print(f"   ❌ Error con PSM 6: {e}")
        
        return len(text_basico) > 10
        
    except ImportError as e:
        print(f"❌ Error importando pytesseract: {e}")
        return False

def probar_con_imagen_real():
    """Prueba con la imagen real que está fallando"""
    print("\n🖼️ PROBANDO CON IMAGEN REAL")
    print("=" * 40)
    
    # Simular la imagen PNG RGBA 646x817 que está fallando
    img = Image.new('RGBA', (646, 817), (255, 255, 255, 0))  # Transparente
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except:
        font = ImageFont.load_default()
    
    # Simular texto de factura
    draw.text((50, 100), "FACTURA", fill=(0, 0, 0, 200), font=font)
    draw.text((50, 150), "RUC: 1234567890001", fill=(0, 0, 0, 200), font=font)
    draw.text((50, 200), "TOTAL: $100.00", fill=(0, 0, 0, 200), font=font)
    
    print(f"✅ Imagen RGBA creada: {img.size} pixels, modo: {img.mode}")
    
    try:
        from helpers.invoice_capture_parser import ocr_image
        
        # Probar OCR en imagen RGBA
        print("1️⃣ Probando OCR en imagen RGBA...")
        text_rgba = ocr_image(img)
        print(f"   Texto RGBA: '{text_rgba[:100]}...'")
        print(f"   Longitud: {len(text_rgba)} caracteres")
        
        if len(text_rgba) > 10:
            print("   ✅ OCR funciona con imagen RGBA")
            return True
        else:
            print("   ⚠️  OCR no funciona con imagen RGBA")
            return False
            
    except Exception as e:
        print(f"❌ Error probando imagen RGBA: {e}")
        return False

def main():
    print("🐛 DEBUGGING PROBLEMA DE OCR")
    print("=" * 50)
    
    # Probar paso a paso
    paso_a_paso_ok = probar_ocr_paso_a_paso()
    
    # Probar Tesseract directo
    tesseract_ok = probar_tesseract_directo()
    
    # Probar con imagen real
    imagen_real_ok = probar_con_imagen_real()
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN DEL DEBUG:")
    print(f"   Paso a paso: {'✅' if paso_a_paso_ok else '❌'}")
    print(f"   Tesseract directo: {'✅' if tesseract_ok else '❌'}")
    print(f"   Imagen real: {'✅' if imagen_real_ok else '❌'}")
    
    if not tesseract_ok:
        print("\n❌ PROBLEMA: Tesseract no está funcionando")
        print("   Solución: Ejecuta python configurar_tesseract_windows.py")
    elif not paso_a_paso_ok:
        print("\n❌ PROBLEMA: El parser avanzado tiene errores")
        print("   Solución: Revisar la implementación del parser")
    elif not imagen_real_ok:
        print("\n❌ PROBLEMA: No funciona con imágenes RGBA")
        print("   Solución: Mejorar el aplanado de transparencia")
    else:
        print("\n🎉 ¡Todo está funcionando correctamente!")

if __name__ == "__main__":
    main()
