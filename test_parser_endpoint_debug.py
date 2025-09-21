#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para debuggear el parser avanzado en el endpoint validar_imagen
"""

import requests
import base64
import json
from PIL import Image, ImageDraw, ImageFont
import io

def crear_imagen_factura():
    """Crea una imagen de factura de prueba"""
    # Crear imagen
    width, height = 646, 817
    img = Image.new('RGBA', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Fuentes
    try:
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_medium = ImageFont.truetype("arial.ttf", 18)
        font_small = ImageFont.truetype("arial.ttf", 14)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Contenido de la factura
    y = 50
    draw.text((50, y), "FARMACIAS FYBECA S.A.", fill='black', font=font_large)
    y += 40
    
    draw.text((50, y), "RUC: 1234567890001", fill='black', font=font_medium)
    y += 30
    
    draw.text((50, y), "FACTURA No. 001-001-000123456", fill='black', font=font_medium)
    y += 30
    
    draw.text((50, y), "Clave de Acceso:", fill='black', font=font_medium)
    y += 25
    draw.text((50, y), "1234567890123456789012345678901234567890123456789", fill='black', font=font_small)
    y += 40
    
    draw.text((50, y), "Fecha: 2024-01-15 10:30:00", fill='black', font=font_medium)
    y += 30
    
    draw.text((50, y), "Ambiente: PRODUCCION", fill='black', font=font_medium)
    y += 40
    
    # Productos
    draw.text((50, y), "PRODUCTOS:", fill='black', font=font_medium)
    y += 30
    
    productos = [
        ("1", "Medicamento A", "10.00"),
        ("2", "Medicamento B", "5.00")
    ]
    
    for cant, desc, precio in productos:
        draw.text((50, y), f"{cant} {desc} ${precio}", fill='black', font=font_small)
        y += 25
    
    y += 20
    draw.text((400, y), "Subtotal: $15.00", fill='black', font=font_medium)
    y += 25
    draw.text((400, y), "IVA 15%: $2.25", fill='black', font=font_medium)
    y += 25
    draw.text((400, y), "TOTAL: $17.25", fill='black', font=font_large)
    
    return img

def test_parser_avanzado_directo():
    """Prueba el parser avanzado directamente"""
    print("🔬 PROBANDO PARSER AVANZADO DIRECTO")
    print("=" * 50)
    
    # Crear imagen
    img = crear_imagen_factura()
    print(f"✅ Imagen creada: {img.size} pixels, modo: {img.mode}")
    
    # Convertir a bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    archivo_bytes = img_bytes.getvalue()
    print(f"✅ Imagen convertida a bytes: {len(archivo_bytes)} bytes")
    
    # Probar parser avanzado
    try:
        from helpers.invoice_capture_parser import parse_capture_from_bytes
        print("✅ Parser importado correctamente")
        
        parse_result = parse_capture_from_bytes(archivo_bytes, "capture.png")
        print("✅ Parser ejecutado exitosamente")
        
        print(f"   - Texto OCR: {len(parse_result.ocr_text)} caracteres")
        print(f"   - RUC: {parse_result.metadata.ruc}")
        print(f"   - Número factura: {parse_result.metadata.invoice_number}")
        print(f"   - Clave acceso: {parse_result.metadata.access_key}")
        print(f"   - Total: {parse_result.totals.total}")
        print(f"   - Items: {len(parse_result.items)}")
        print(f"   - Códigos: {len(parse_result.barcodes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en parser directo: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def test_endpoint_completo():
    """Prueba el endpoint completo"""
    print("\n🌐 PROBANDO ENDPOINT COMPLETO")
    print("=" * 50)
    
    # Crear imagen y convertir a base64
    img = crear_imagen_factura()
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    archivo_bytes = img_bytes.getvalue()
    
    imagen_base64 = base64.b64encode(archivo_bytes).decode('utf-8')
    print(f"✅ Imagen codificada en base64: {len(imagen_base64)} caracteres")
    
    # Preparar request
    url = "http://localhost:8001/validar-imagen"
    payload = {
        "imagen_base64": imagen_base64
    }
    
    try:
        print("📡 Enviando request...")
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            print("✅ Request exitoso")
            data = response.json()
            
            # Verificar parser avanzado
            parser_avanzado = data.get("parser_avanzado", {})
            print(f"   - Parser disponible: {parser_avanzado.get('disponible', False)}")
            print(f"   - Barcodes detectados: {parser_avanzado.get('barcodes_detectados', 0)}")
            print(f"   - Items detectados: {parser_avanzado.get('items_detectados', 0)}")
            
            # Verificar campos de factura
            factura = data.get("factura", {})
            print(f"   - RUC: {factura.get('ruc')}")
            print(f"   - Razón Social: {factura.get('razonSocial')}")
            print(f"   - Total: {factura.get('importeTotal')}")
            print(f"   - Clave Acceso: {factura.get('claveAcceso')}")
            
            # Verificar texto extraído
            texto_extraido = data.get("texto_extraido", "")
            print(f"   - Texto extraído: {len(texto_extraido)} caracteres")
            if len(texto_extraido) > 100:
                print(f"   - Primeros 100 chars: {texto_extraido[:100]}...")
            
            return True
            
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar al servidor. ¿Está ejecutándose?")
        return False
    except Exception as e:
        print(f"❌ Error en request: {e}")
        return False

def main():
    print("🔬 DEBUG DEL PARSER AVANZADO EN ENDPOINT")
    print("=" * 60)
    
    # Probar parser directo
    parser_ok = test_parser_avanzado_directo()
    
    # Probar endpoint completo
    endpoint_ok = test_endpoint_completo()
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN:")
    print(f"   Parser directo: {'✅' if parser_ok else '❌'}")
    print(f"   Endpoint completo: {'✅' if endpoint_ok else '❌'}")
    
    if not parser_ok:
        print("\n⚠️  PROBLEMAS DETECTADOS:")
        print("   - El parser avanzado no funciona correctamente")
        print("   - Verificar configuración de Tesseract")
        print("   - Revisar dependencias del parser")
    elif not endpoint_ok:
        print("\n⚠️  PROBLEMAS DETECTADOS:")
        print("   - El endpoint no está funcionando")
        print("   - Verificar que el servidor esté ejecutándose")
        print("   - Revisar logs del servidor")
    else:
        print("\n🎉 ¡TODO FUNCIONANDO CORRECTAMENTE!")

if __name__ == "__main__":
    main()
