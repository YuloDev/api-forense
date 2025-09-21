#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script que simula exactamente lo que hace el endpoint para debuggear
"""

import base64
import io
from PIL import Image, ImageDraw, ImageFont

def crear_imagen_problema():
    """Crea una imagen PNG RGBA 646x817 que simula el problema"""
    img = Image.new('RGBA', (646, 817), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 10)
    except:
        font = ImageFont.load_default()
    
    # Texto muy pequeño y con transparencia
    draw.text((30, 100), "FACTURA", fill=(0, 0, 0, 150), font=font)
    draw.text((30, 120), "RUC: 1234567890001", fill=(0, 0, 0, 150), font=font)
    draw.text((30, 140), "TOTAL: $100.00", fill=(0, 0, 0, 150), font=font)
    
    return img

def simular_endpoint():
    """Simula exactamente el flujo del endpoint"""
    print("🔄 SIMULANDO ENDPOINT COMPLETO")
    print("=" * 40)
    
    # 1) Crear imagen de prueba
    print("1️⃣ Creando imagen de prueba...")
    img = crear_imagen_problema()
    print(f"   Imagen: {img.size} pixels, modo: {img.mode}")
    
    # 2) Convertir a bytes y base64
    print("\n2️⃣ Convirtiendo a bytes y base64...")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    
    imagen_base64 = base64.b64encode(img_bytes).decode('utf-8')
    print(f"   Bytes: {len(img_bytes)} bytes")
    print(f"   Base64: {len(imagen_base64)} caracteres")
    
    # 3) Detectar tipo de archivo
    print("\n3️⃣ Detectando tipo de archivo...")
    try:
        from helpers.analisis_imagenes import detectar_tipo_archivo
        tipo_info = detectar_tipo_archivo(imagen_base64)
        print(f"   Tipo detectado: {tipo_info}")
    except Exception as e:
        print(f"   ❌ Error detectando tipo: {e}")
        return False
    
    # 4) Parser avanzado
    print("\n4️⃣ Ejecutando parser avanzado...")
    try:
        from helpers.invoice_capture_parser import parse_capture_from_bytes
        
        parse_result = parse_capture_from_bytes(img_bytes, "test.png")
        print("   ✅ Parser ejecutado exitosamente")
        
        # Mostrar resultados
        print(f"   - Texto OCR: {len(parse_result.ocr_text)} caracteres")
        print(f"   - RUC: {parse_result.metadata.ruc}")
        print(f"   - Total: {parse_result.totals.total}")
        print(f"   - Códigos: {len(parse_result.barcodes)}")
        
        if len(parse_result.ocr_text) > 10:
            print("   ✅ OCR funcionando")
            print(f"   Texto: '{parse_result.ocr_text[:100]}...'")
        else:
            print("   ⚠️  OCR extrajo poco texto")
            print(f"   Texto: '{parse_result.ocr_text}'")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error en parser avanzado: {e}")
        print(f"   Tipo: {type(e).__name__}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def probar_ocr_individual():
    """Prueba el OCR individualmente"""
    print("\n🔍 PROBANDO OCR INDIVIDUAL")
    print("=" * 30)
    
    img = crear_imagen_problema()
    
    try:
        from helpers.invoice_capture_parser import ocr_image
        
        print("1️⃣ Probando OCR con imagen RGBA...")
        text = ocr_image(img)
        print(f"   Resultado: '{text}'")
        print(f"   Longitud: {len(text)} caracteres")
        
        if len(text) > 10:
            print("   ✅ OCR funcionando con imagen RGBA")
            return True
        else:
            print("   ⚠️  OCR no funciona con imagen RGBA")
            return False
            
    except Exception as e:
        print(f"   ❌ Error en OCR: {e}")
        return False

def probar_configuracion_tesseract():
    """Prueba la configuración de Tesseract"""
    print("\n⚙️ PROBANDO CONFIGURACIÓN TESSERACT")
    print("=" * 40)
    
    try:
        import pytesseract
        from PIL import Image, ImageDraw, ImageFont
        
        # Crear imagen simple
        img = Image.new('RGB', (200, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((20, 30), "TEST", fill='black')
        
        print("1️⃣ Probando Tesseract básico...")
        text = pytesseract.image_to_string(img, lang='eng')
        print(f"   Resultado: '{text.strip()}'")
        
        if len(text.strip()) > 2:
            print("   ✅ Tesseract básico funcionando")
        else:
            print("   ❌ Tesseract básico no funciona")
            return False
        
        print("\n2️⃣ Probando con español...")
        try:
            text_spa = pytesseract.image_to_string(img, lang='spa')
            print(f"   Resultado: '{text_spa.strip()}'")
        except Exception as e:
            print(f"   ⚠️  Error con español: {e}")
        
        print("\n3️⃣ Probando con spa+eng...")
        try:
            text_hibrido = pytesseract.image_to_string(img, lang='spa+eng')
            print(f"   Resultado: '{text_hibrido.strip()}'")
        except Exception as e:
            print(f"   ⚠️  Error con spa+eng: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error en configuración: {e}")
        return False

def main():
    print("🐛 DEBUG COMPLETO DEL PROBLEMA")
    print("=" * 50)
    
    # Probar configuración de Tesseract
    tesseract_ok = probar_configuracion_tesseract()
    
    # Probar OCR individual
    ocr_ok = probar_ocr_individual()
    
    # Simular endpoint completo
    endpoint_ok = simular_endpoint()
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN DEL DEBUG:")
    print(f"   Tesseract config: {'✅' if tesseract_ok else '❌'}")
    print(f"   OCR individual: {'✅' if ocr_ok else '❌'}")
    print(f"   Endpoint simulado: {'✅' if endpoint_ok else '❌'}")
    
    if not tesseract_ok:
        print("\n❌ PROBLEMA: Tesseract no está configurado correctamente")
        print("   Solución: python configurar_tesseract_windows.py")
    elif not ocr_ok:
        print("\n❌ PROBLEMA: OCR no funciona con imágenes RGBA")
        print("   Solución: Revisar función flatten_rgba_to_white")
    elif not endpoint_ok:
        print("\n❌ PROBLEMA: Parser avanzado está fallando")
        print("   Solución: Revisar implementación del parser")
    else:
        print("\n🎉 ¡Todo está funcionando correctamente!")

if __name__ == "__main__":
    main()
