#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar el endpoint real con la misma imagen
"""

import requests
import base64
import json
from PIL import Image, ImageDraw, ImageFont
import io

def crear_imagen_debug():
    """Crea la misma imagen que usamos en la simulación"""
    # Crear imagen
    width, height = 400, 600
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Fuentes
    try:
        font_large = ImageFont.truetype("arial.ttf", 20)
        font_medium = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    y = 50
    
    # Contenido simple
    draw.text((50, y), "FACTURA", fill='black', font=font_large)
    y += 40
    
    draw.text((50, y), "RUC: 1790710319001", fill='black', font=font_medium)
    y += 30
    
    draw.text((50, y), "No. 026-200-000021384", fill='black', font=font_medium)
    y += 30
    
    draw.text((50, y), "Clave de Acceso:", fill='black', font=font_small)
    y += 20
    draw.text((50, y), "0807202504 179071031900120262000000213845658032318", fill='black', font=font_small)
    y += 40
    
    draw.text((50, y), "Razón Social: ROCIO VERDEZOTO", fill='black', font=font_medium)
    y += 30
    
    draw.text((50, y), "Fecha: 08/07/2025", fill='black', font=font_medium)
    y += 30
    
    draw.text((50, y), "Total: $23.00", fill='black', font=font_large)
    
    return img

def test_endpoint_real():
    """Prueba el endpoint real"""
    print("🔬 PROBANDO ENDPOINT REAL")
    print("=" * 50)
    
    # Crear imagen
    img = crear_imagen_debug()
    print(f"✅ Imagen creada: {img.size} pixels")
    
    # Convertir a bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    archivo_bytes = img_bytes.getvalue()
    print(f"✅ Imagen convertida a bytes: {len(archivo_bytes)} bytes")
    
    # Convertir a base64
    imagen_base64 = base64.b64encode(archivo_bytes).decode('utf-8')
    print(f"✅ Imagen codificada en base64: {len(imagen_base64)} caracteres")
    
    # Preparar request
    url = "http://localhost:8001/validar-imagen"
    payload = {
        "imagen_base64": imagen_base64
    }
    
    try:
        print("\n📡 Enviando request al endpoint...")
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            print("✅ Request exitoso")
            data = response.json()
            
            # Verificar parser avanzado
            parser_avanzado = data.get("parser_avanzado", {})
            print(f"\n🔍 PARSER AVANZADO:")
            print(f"   - Disponible: {parser_avanzado.get('disponible', False)}")
            print(f"   - Barcodes detectados: {parser_avanzado.get('barcodes_detectados', 0)}")
            print(f"   - Items detectados: {parser_avanzado.get('items_detectados', 0)}")
            
            # Verificar campos de factura
            factura = data.get("factura", {})
            print(f"\n📋 CAMPOS DE FACTURA:")
            print(f"   - RUC: {factura.get('ruc')}")
            print(f"   - Razón Social: {factura.get('razonSocial')}")
            print(f"   - Fecha Emisión: {factura.get('fechaEmision')}")
            print(f"   - Total: {factura.get('importeTotal')}")
            print(f"   - Clave Acceso: {factura.get('claveAcceso')}")
            
            # Verificar items
            detalles = factura.get("detalles", [])
            print(f"\n🛒 ITEMS DETECTADOS ({len(detalles)}):")
            for i, item in enumerate(detalles, 1):
                print(f"   {i}. {item.get('descripcion', 'N/A')} - Cant: {item.get('cantidad', 0)} - Precio: ${item.get('precioTotal', 0)}")
            
            # Verificar texto extraído
            texto_extraido = data.get("texto_extraido", "")
            print(f"\n📝 TEXTO EXTRAÍDO:")
            print(f"   - Longitud: {len(texto_extraido)} caracteres")
            if len(texto_extraido) > 200:
                print(f"   - Primeros 200 chars: {texto_extraido[:200]}...")
            else:
                print(f"   - Texto completo: {texto_extraido}")
            
            # Verificar si el parser avanzado está funcionando
            if parser_avanzado.get('disponible', False):
                print("\n🎉 ¡PARSER AVANZADO FUNCIONANDO!")
                return True
            else:
                print("\n⚠️  PARSER AVANZADO NO DISPONIBLE")
                print("   - Revisar logs del servidor")
                print("   - Verificar que no haya errores en el catch")
                return False
            
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
    print("🔬 PRUEBA DEL ENDPOINT REAL")
    print("=" * 60)
    
    success = test_endpoint_real()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ¡ENDPOINT FUNCIONANDO CORRECTAMENTE!")
    else:
        print("⚠️  HAY PROBLEMAS EN EL ENDPOINT")
        print("   - Verificar logs del servidor")
        print("   - Revisar configuración del parser")

if __name__ == "__main__":
    main()
