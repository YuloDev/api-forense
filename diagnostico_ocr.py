#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de diagnóstico para verificar la configuración de OCR
"""

import subprocess
import sys
from PIL import Image
import io

def verificar_tesseract():
    """Verifica si Tesseract está instalado y qué idiomas tiene"""
    try:
        # Verificar versión
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Tesseract instalado:")
            print(f"   {result.stdout.strip()}")
        else:
            print("❌ Tesseract no encontrado")
            return False
    except FileNotFoundError:
        print("❌ Tesseract no está en el PATH")
        return False
    except Exception as e:
        print(f"❌ Error verificando Tesseract: {e}")
        return False
    
    try:
        # Verificar idiomas disponibles
        result = subprocess.run(['tesseract', '--list-langs'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            langs = result.stdout.strip().split('\n')[1:]  # Saltar la primera línea
            print(f"✅ Idiomas disponibles ({len(langs)}):")
            for lang in sorted(langs):
                print(f"   - {lang}")
            
            if 'spa' in langs:
                print("✅ Español (spa) disponible")
            else:
                print("⚠️  Español (spa) NO disponible - instala el paquete de idioma")
                
            if 'eng' in langs:
                print("✅ Inglés (eng) disponible")
            else:
                print("⚠️  Inglés (eng) NO disponible")
                
        else:
            print("❌ No se pudieron listar idiomas")
            return False
    except Exception as e:
        print(f"❌ Error listando idiomas: {e}")
        return False
    
    return True

def verificar_dependencias_python():
    """Verifica las dependencias de Python"""
    dependencias = [
        ('PIL', 'Pillow'),
        ('pytesseract', 'pytesseract'),
        ('cv2', 'opencv-python-headless'),
        ('numpy', 'numpy'),
        ('pyzbar', 'pyzbar'),
        ('dateutil', 'python-dateutil')
    ]
    
    print("\n🔍 Verificando dependencias de Python:")
    todas_ok = True
    
    for modulo, paquete in dependencias:
        try:
            __import__(modulo)
            print(f"✅ {paquete}")
        except ImportError:
            print(f"❌ {paquete} - instala con: pip install {paquete}")
            todas_ok = False
    
    # Verificar EasyOCR opcional
    try:
        import easyocr
        print("✅ easyocr (opcional)")
    except ImportError:
        print("ℹ️  easyocr (opcional) - instala con: pip install easyocr")
    
    return todas_ok

def probar_ocr_basico():
    """Prueba OCR básico con una imagen simple"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import pytesseract
        
        print("\n🧪 Probando OCR básico...")
        
        # Crear imagen de prueba con texto
        img = Image.new('RGB', (400, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # Intentar usar una fuente del sistema
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # Dibujar texto de prueba
        draw.text((20, 30), "FACTURA No. 001-001-000123456", fill='black', font=font)
        draw.text((20, 60), "RUC: 1234567890001", fill='black', font=font)
        
        # Probar OCR
        text = pytesseract.image_to_string(img, lang='spa+eng')
        print(f"✅ OCR básico funcionando:")
        print(f"   Texto extraído: '{text.strip()}'")
        
        if len(text.strip()) > 10:
            print("✅ OCR está extrayendo texto correctamente")
            return True
        else:
            print("⚠️  OCR extrajo poco texto - puede necesitar configuración")
            return False
            
    except Exception as e:
        print(f"❌ Error en prueba OCR: {e}")
        return False

def probar_parser_avanzado():
    """Prueba el parser avanzado con una imagen de prueba"""
    try:
        from helpers.invoice_capture_parser import parse_capture_from_bytes
        from PIL import Image, ImageDraw, ImageFont
        
        print("\n🔬 Probando parser avanzado...")
        
        # Crear imagen de prueba más realista
        img = Image.new('RGB', (600, 800), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Simular una factura básica
        y = 50
        draw.text((50, y), "FARMACIAS FYBECA", fill='black', font=font)
        y += 30
        draw.text((50, y), "RUC: 1234567890001", fill='black', font=font)
        y += 30
        draw.text((50, y), "FACTURA No. 001-001-000123456", fill='black', font=font)
        y += 30
        draw.text((50, y), "Clave de Acceso: 1234567890123456789012345678901234567890123456789", fill='black', font=font)
        y += 30
        draw.text((50, y), "Fecha: 2024-01-15 10:30:00", fill='black', font=font)
        y += 50
        draw.text((50, y), "SUBTOTAL 15%: $100.00", fill='black', font=font)
        y += 20
        draw.text((50, y), "IVA 15%: $15.00", fill='black', font=font)
        y += 20
        draw.text((50, y), "TOTAL: $115.00", fill='black', font=font)
        
        # Convertir a bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        # Probar parser
        result = parse_capture_from_bytes(img_bytes, "test.png")
        
        print(f"✅ Parser avanzado funcionando:")
        print(f"   RUC detectado: {result.metadata.ruc}")
        print(f"   Número factura: {result.metadata.invoice_number}")
        print(f"   Clave acceso: {result.metadata.access_key}")
        print(f"   Total: {result.totals.total}")
        print(f"   Texto OCR: {len(result.ocr_text)} caracteres")
        
        if result.metadata.ruc and result.totals.total:
            print("✅ Parser detectó campos principales correctamente")
            return True
        else:
            print("⚠️  Parser no detectó todos los campos esperados")
            return False
            
    except Exception as e:
        print(f"❌ Error en parser avanzado: {e}")
        return False

def main():
    print("🔍 DIAGNÓSTICO DE OCR Y PARSER AVANZADO")
    print("=" * 50)
    
    # Verificar Tesseract
    tesseract_ok = verificar_tesseract()
    
    # Verificar dependencias Python
    deps_ok = verificar_dependencias_python()
    
    if not tesseract_ok or not deps_ok:
        print("\n❌ Configuración incompleta. Instala las dependencias faltantes.")
        return
    
    # Probar OCR básico
    ocr_ok = probar_ocr_basico()
    
    # Probar parser avanzado
    parser_ok = probar_parser_avanzado()
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN:")
    print(f"   Tesseract: {'✅' if tesseract_ok else '❌'}")
    print(f"   Dependencias: {'✅' if deps_ok else '❌'}")
    print(f"   OCR básico: {'✅' if ocr_ok else '❌'}")
    print(f"   Parser avanzado: {'✅' if parser_ok else '❌'}")
    
    if all([tesseract_ok, deps_ok, ocr_ok, parser_ok]):
        print("\n🎉 ¡Todo está funcionando correctamente!")
    else:
        print("\n⚠️  Algunos componentes necesitan configuración")

if __name__ == "__main__":
    main()
