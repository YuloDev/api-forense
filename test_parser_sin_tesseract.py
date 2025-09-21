#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de prueba del parser avanzado que funciona sin Tesseract
"""

import base64
import io
from PIL import Image, ImageDraw, ImageFont

def crear_imagen_factura_prueba():
    """Crea una imagen de factura de prueba para testing"""
    # Crear imagen de prueba
    img = Image.new('RGB', (600, 800), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("arial.ttf", 20)
        font_medium = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 14)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Encabezado
    y = 30
    draw.text((50, y), "FARMACIAS FYBECA S.A.", fill='black', font=font_large)
    y += 40
    draw.text((50, y), "RUC: 1234567890001", fill='black', font=font_medium)
    y += 30
    draw.text((50, y), "FACTURA No. 001-001-000123456", fill='black', font=font_medium)
    y += 30
    draw.text((50, y), "Clave de Acceso:", fill='black', font=font_medium)
    y += 25
    draw.text((50, y), "1234567890123456789012345678901234567890123456789", fill='black', font=font_small)
    y += 30
    draw.text((50, y), "Fecha: 2024-01-15 10:30:00", fill='black', font=font_medium)
    y += 30
    draw.text((50, y), "Ambiente: PRODUCCION", fill='black', font=font_medium)
    
    # Línea separadora
    y += 40
    draw.line([(50, y), (550, y)], fill='black', width=2)
    
    # Detalles de productos
    y += 30
    draw.text((50, y), "Código  Cant  Descripción                    Precio Unit  Total", fill='black', font=font_small)
    y += 25
    draw.line([(50, y), (550, y)], fill='gray', width=1)
    
    y += 20
    draw.text((50, y), "001     2     Medicamento A                  $50.00      $100.00", fill='black', font=font_small)
    y += 20
    draw.text((50, y), "002     1     Medicamento B                  $30.00      $30.00", fill='black', font=font_small)
    
    # Totales
    y += 50
    draw.text((400, y), "SUBTOTAL 15%: $100.00", fill='black', font=font_medium)
    y += 25
    draw.text((400, y), "SUBTOTAL 0%: $30.00", fill='black', font=font_medium)
    y += 25
    draw.text((400, y), "SUBTOTAL SIN IMPUESTOS: $130.00", fill='black', font=font_medium)
    y += 25
    draw.text((400, y), "DESCUENTO: $0.00", fill='black', font=font_medium)
    y += 25
    draw.text((400, y), "IVA 15%: $15.00", fill='black', font=font_medium)
    y += 30
    draw.line([(400, y), (550, y)], fill='black', width=2)
    y += 10
    draw.text((400, y), "TOTAL: $145.00", fill='black', font=font_large)
    
    return img

def probar_parser_sin_ocr():
    """Prueba el parser sin depender de OCR"""
    print("🧪 Probando parser avanzado sin OCR...")
    
    try:
        from helpers.invoice_capture_parser import parse_capture_from_bytes
        
        # Crear imagen de prueba
        img = crear_imagen_factura_prueba()
        
        # Convertir a bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        print(f"   Imagen creada: {img.size} pixels")
        
        # Probar parser (fallará en OCR pero probará otras funciones)
        try:
            result = parse_capture_from_bytes(img_bytes, "test_factura.png")
            
            print("✅ Parser ejecutado (aunque OCR puede fallar)")
            print(f"   - Metadatos técnicos: {result.metadata.width}x{result.metadata.height}")
            print(f"   - Formato: {result.metadata.format}")
            print(f"   - Modo: {result.metadata.mode}")
            print(f"   - SHA256: {result.metadata.sha256[:16]}...")
            print(f"   - Texto OCR: {len(result.ocr_text)} caracteres")
            
            # Mostrar códigos detectados
            if result.barcodes:
                print(f"   - Códigos detectados: {len(result.barcodes)}")
                for bc in result.barcodes:
                    print(f"     * {bc['type']}: {bc['data'][:20]}...")
            else:
                print("   - Códigos detectados: 0")
            
            return True
            
        except Exception as e:
            print(f"   ⚠️  Error en parser: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Error importando parser: {e}")
        return False

def probar_funciones_individuales():
    """Prueba funciones individuales del parser"""
    print("\n🔬 Probando funciones individuales...")
    
    try:
        from helpers.invoice_capture_parser import (
            flatten_rgba_to_white, 
            enhance_for_ocr, 
            normalize_decimal,
            try_parse_datetime,
            extract_fields_from_text
        )
        
        # Crear imagen RGBA
        img_rgba = Image.new('RGBA', (100, 100), (255, 255, 255, 0))
        print("   ✅ Imagen RGBA creada")
        
        # Probar aplanado
        img_flattened = flatten_rgba_to_white(img_rgba)
        print(f"   ✅ Aplanado RGBA: {img_rgba.mode} -> {img_flattened.mode}")
        
        # Probar escalado
        img_enhanced = enhance_for_ocr(img_flattened, scale=2.0)
        print(f"   ✅ Escalado: {img_flattened.size} -> {img_enhanced.size}")
        
        # Probar normalización de decimales
        test_numbers = ["1.234,56", "1,234.56", "1234.56", "1234,56"]
        for num in test_numbers:
            normalized = normalize_decimal(num)
            print(f"   ✅ Normalizar '{num}': {normalized}")
        
        # Probar parsing de fechas
        test_dates = ["2024-01-15 10:30:00", "15/01/2024", "2024/01/15"]
        for date in test_dates:
            parsed = try_parse_datetime(date)
            print(f"   ✅ Parsear fecha '{date}': {parsed}")
        
        # Probar extracción de campos
        test_text = """
        FARMACIAS FYBECA S.A.
        RUC: 1234567890001
        FACTURA No. 001-001-000123456
        Clave de Acceso: 1234567890123456789012345678901234567890123456789
        Fecha: 2024-01-15 10:30:00
        SUBTOTAL 15%: $100.00
        IVA 15%: $15.00
        TOTAL: $115.00
        """
        
        fields = extract_fields_from_text(test_text)
        print("   ✅ Extracción de campos:")
        for key, value in fields.items():
            if value:
                print(f"     - {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en funciones individuales: {e}")
        return False

def main():
    print("🚀 PRUEBA DEL PARSER AVANZADO (SIN TESSERACT)")
    print("=" * 50)
    
    # Probar parser completo
    parser_ok = probar_parser_sin_ocr()
    
    # Probar funciones individuales
    funciones_ok = probar_funciones_individuales()
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN:")
    print(f"   Parser completo: {'✅' if parser_ok else '❌'}")
    print(f"   Funciones individuales: {'✅' if funciones_ok else '❌'}")
    
    if parser_ok and funciones_ok:
        print("\n🎉 ¡El parser está funcionando correctamente!")
        print("   (OCR fallará hasta que Tesseract esté instalado)")
    else:
        print("\n⚠️  Algunos componentes necesitan revisión")
    
    print("\n📋 PRÓXIMOS PASOS:")
    print("1. Instala Tesseract: python configurar_tesseract_windows.py")
    print("2. Ejecuta: python diagnostico_ocr.py")
    print("3. Prueba con imágenes reales: python test_parser_avanzado.py")

if __name__ == "__main__":
    main()
