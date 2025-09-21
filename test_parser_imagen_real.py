#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar el parser avanzado con la imagen real que está fallando
"""

import base64
import io
from PIL import Image, ImageDraw, ImageFont

def crear_imagen_png_rgba_646x817():
    """Crea una imagen PNG RGBA 646x817 similar a la que está fallando"""
    # Crear imagen RGBA exactamente como la que está fallando
    img = Image.new('RGBA', (646, 817), (255, 255, 255, 0))  # Transparente
    draw = ImageDraw.Draw(img)
    
    try:
        font_small = ImageFont.truetype("arial.ttf", 10)
        font_medium = ImageFont.truetype("arial.ttf", 12)
    except:
        font_small = ImageFont.load_default()
        font_medium = ImageFont.load_default()
    
    # Simular una factura real con texto pequeño
    y = 50
    draw.text((30, y), "FARMACIAS FYBECA S.A.", fill=(0, 0, 0, 200), font=font_medium)
    y += 25
    draw.text((30, y), "RUC: 1234567890001", fill=(0, 0, 0, 200), font=font_small)
    y += 20
    draw.text((30, y), "FACTURA No. 001-001-000123456", fill=(0, 0, 0, 200), font=font_small)
    y += 20
    draw.text((30, y), "Clave de Acceso:", fill=(0, 0, 0, 200), font=font_small)
    y += 15
    draw.text((30, y), "1234567890123456789012345678901234567890123456789", fill=(0, 0, 0, 200), font=font_small)
    y += 25
    draw.text((30, y), "Fecha: 2024-01-15 10:30:00", fill=(0, 0, 0, 200), font=font_small)
    y += 20
    draw.text((30, y), "Ambiente: PRODUCCION", fill=(0, 0, 0, 200), font=font_small)
    
    # Línea separadora
    y += 30
    draw.line([(30, y), (600, y)], fill=(0, 0, 0, 150), width=1)
    
    # Detalles
    y += 20
    draw.text((30, y), "Código  Cant  Descripción                    Precio", fill=(0, 0, 0, 200), font=font_small)
    y += 15
    draw.line([(30, y), (600, y)], fill=(0, 0, 0, 100), width=1)
    
    y += 15
    draw.text((30, y), "001     2     Medicamento A                  $50.00", fill=(0, 0, 0, 200), font=font_small)
    y += 15
    draw.text((30, y), "002     1     Medicamento B                  $30.00", fill=(0, 0, 0, 200), font=font_small)
    
    # Totales
    y += 40
    draw.text((400, y), "SUBTOTAL 15%: $100.00", fill=(0, 0, 0, 200), font=font_small)
    y += 15
    draw.text((400, y), "SUBTOTAL 0%: $30.00", fill=(0, 0, 0, 200), font=font_small)
    y += 15
    draw.text((400, y), "SUBTOTAL SIN IMPUESTOS: $130.00", fill=(0, 0, 0, 200), font=font_small)
    y += 15
    draw.text((400, y), "DESCUENTO: $0.00", fill=(0, 0, 0, 200), font=font_small)
    y += 15
    draw.text((400, y), "IVA 15%: $15.00", fill=(0, 0, 0, 200), font=font_small)
    y += 20
    draw.line([(400, y), (600, y)], fill=(0, 0, 0, 200), width=1)
    y += 10
    draw.text((400, y), "TOTAL: $145.00", fill=(0, 0, 0, 200), font=font_medium)
    
    return img

def probar_parser_con_imagen_real():
    """Prueba el parser con la imagen real que está fallando"""
    print("🧪 PROBANDO PARSER CON IMAGEN REAL")
    print("=" * 50)
    
    # Crear imagen PNG RGBA 646x817
    img = crear_imagen_png_rgba_646x817()
    print(f"✅ Imagen creada: {img.size} pixels, modo: {img.mode}")
    
    # Convertir a bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    
    # Codificar en base64
    imagen_base64 = base64.b64encode(img_bytes).decode('utf-8')
    print(f"✅ Imagen codificada en base64: {len(imagen_base64)} caracteres")
    
    try:
        from helpers.invoice_capture_parser import parse_capture_from_bytes
        
        print("\n🔍 Probando parser avanzado...")
        result = parse_capture_from_bytes(img_bytes, "test_real.png")
        
        print("✅ Parser ejecutado exitosamente")
        print(f"   - Texto OCR: {len(result.ocr_text)} caracteres")
        print(f"   - RUC: {result.metadata.ruc}")
        print(f"   - Número factura: {result.metadata.invoice_number}")
        print(f"   - Clave acceso: {result.metadata.access_key}")
        print(f"   - Total: {result.totals.total}")
        print(f"   - Códigos detectados: {len(result.barcodes)}")
        
        if len(result.ocr_text) > 50:
            print("✅ OCR funcionando correctamente")
            print(f"   Texto extraído: '{result.ocr_text[:200]}...'")
        else:
            print("⚠️  OCR extrajo poco texto")
            print(f"   Texto extraído: '{result.ocr_text}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en parser: {e}")
        print(f"   Tipo: {type(e).__name__}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def probar_endpoint_completo():
    """Prueba el endpoint completo con la imagen real"""
    print("\n🌐 PROBANDO ENDPOINT COMPLETO")
    print("=" * 50)
    
    try:
        import requests
        
        # Crear imagen
        img = crear_imagen_png_rgba_646x817()
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        imagen_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # Preparar request
        payload = {
            "imagen_base64": imagen_base64
        }
        
        url = "http://localhost:8000/validar-imagen"
        print(f"📡 Enviando request a: {url}")
        
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Respuesta exitosa")
            
            # Verificar parser avanzado
            parser_info = result.get('parser_avanzado', {})
            print(f"   - Parser disponible: {parser_info.get('disponible')}")
            print(f"   - Códigos detectados: {parser_info.get('barcodes_detectados')}")
            print(f"   - Ítems detectados: {parser_info.get('items_detectados')}")
            
            # Verificar campos de factura
            factura = result.get('factura', {})
            print(f"   - RUC: {factura.get('ruc')}")
            print(f"   - Razón Social: {factura.get('razonSocial')}")
            print(f"   - Total: {factura.get('importeTotal')}")
            print(f"   - Clave Acceso: {factura.get('claveAcceso')}")
            
            # Verificar texto extraído
            texto = result.get('texto_extraido', '')
            print(f"   - Texto extraído: {len(texto)} caracteres")
            if texto:
                print(f"   - Primeros 100 chars: '{texto[:100]}...'")
            
            return True
        else:
            print(f"❌ Error en respuesta: {response.status_code}")
            print(f"   Detalle: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar al servidor. ¿Está ejecutándose?")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def main():
    print("🔬 PRUEBA DEL PARSER CON IMAGEN REAL")
    print("=" * 60)
    
    # Probar parser directamente
    parser_ok = probar_parser_con_imagen_real()
    
    # Probar endpoint completo
    endpoint_ok = probar_endpoint_completo()
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN:")
    print(f"   Parser directo: {'✅' if parser_ok else '❌'}")
    print(f"   Endpoint completo: {'✅' if endpoint_ok else '❌'}")
    
    if parser_ok and endpoint_ok:
        print("\n🎉 ¡El parser está funcionando correctamente!")
    else:
        print("\n⚠️  Hay problemas que necesitan ser resueltos")
        
        if not parser_ok:
            print("   - El parser avanzado está fallando")
            print("   - Revisar configuración de Tesseract")
            print("   - Ejecutar: python configurar_tesseract_windows.py")
        
        if not endpoint_ok:
            print("   - El endpoint no está funcionando")
            print("   - Verificar que el servidor esté ejecutándose")
            print("   - Revisar logs del servidor")

if __name__ == "__main__":
    main()
