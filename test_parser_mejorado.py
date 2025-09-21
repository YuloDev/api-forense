#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar las mejoras del parser avanzado
"""

import requests
import base64
import json
from PIL import Image, ImageDraw, ImageFont
import io

def crear_imagen_factura_mejorada():
    """Crea una imagen de factura mejorada basada en el texto real extraído"""
    # Crear imagen
    width, height = 800, 1200
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Fuentes
    try:
        font_large = ImageFont.truetype("arial.ttf", 20)
        font_medium = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 12)
        font_tiny = ImageFont.truetype("arial.ttf", 10)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny = ImageFont.load_default()
    
    y = 30
    
    # Header - Logo Fybeca
    draw.text((50, y), "Fybeca", fill='blue', font=font_large)
    draw.text((120, y), "Única en tu vida", fill='red', font=font_medium)
    y += 40
    
    # RUC
    draw.text((50, y), "R.U.C.:", fill='black', font=font_medium)
    draw.text((120, y), "1790710319001", fill='black', font=font_medium)
    y += 30
    
    # FACTURA
    draw.text((50, y), "FACTURA", fill='black', font=font_large)
    y += 25
    draw.text((50, y), "No, 026-200-000021384", fill='black', font=font_medium)
    y += 30
    
    # Número de autorización
    draw.text((50, y), "NUMERO DE AUTORIZACION", fill='black', font=font_small)
    y += 20
    draw.text((50, y), "0807202504 179071031900120262000000213845658032318", fill='black', font=font_tiny)
    y += 30
    
    # Ambiente
    draw.text((50, y), "AMBIENTE: PRODUCCION", fill='black', font=font_small)
    y += 25
    
    # Company info
    draw.text((50, y), "FARMACIAS Y COMISARIATOS DE MEDICINAS S.A.", fill='black', font=font_medium)
    y += 20
    draw.text((50, y), "FARCOMED", fill='black', font=font_medium)
    y += 30
    
    # Fecha y hora
    draw.text((50, y), "FECHA Y HORA DE : 2025-07-08 19:58:13", fill='black', font=font_small)
    y += 25
    draw.text((50, y), "EMISION: NORMAL", fill='black', font=font_small)
    y += 30
    
    # Clave de acceso
    draw.text((50, y), "CLAVE DE ACCESO", fill='black', font=font_small)
    y += 20
    draw.text((50, y), "0807202504 179071031900120262000000213845658032318", fill='black', font=font_tiny)
    y += 40
    
    # Customer info
    draw.text((50, y), "Razón Social / Nombres y Apellidos:", fill='black', font=font_small)
    y += 20
    draw.text((50, y), "ROCKO VERDEZOTO", fill='black', font=font_small)
    y += 20
    draw.text((50, y), "Identificación: 1718465014", fill='black', font=font_small)
    y += 20
    draw.text((50, y), "Fecha Emisión: 08/07/2025", fill='black', font=font_small)
    y += 40
    
    # Items table header
    draw.text((50, y), "Cod. Principal", fill='black', font=font_tiny)
    draw.text((150, y), "Cant.", fill='black', font=font_tiny)
    draw.text((200, y), "Descripción", fill='black', font=font_tiny)
    draw.text((450, y), "Precio Total", fill='black', font=font_tiny)
    y += 20
    
    # Items (basados en el texto real)
    items = [
        ("FLURITOK JARABE", "1", "5.25"),
        ("AVAMY SPRAY NASAL 27.5 MCG", "1", "15.12"),
        ("COSTO DOMICILIO", "1", "2.29")
    ]
    
    for desc, cant, precio in items:
        draw.text((50, y), cant, fill='black', font=font_tiny)
        draw.text((150, y), desc[:30], fill='black', font=font_tiny)
        draw.text((450, y), f"${precio}", fill='black', font=font_tiny)
        y += 20
    
    y += 20
    
    # Totals
    draw.text((400, y), "SUBTOTAL 15%: $2.29", fill='black', font=font_small)
    y += 20
    draw.text((400, y), "SUBTOTAL 0%: $20.37", fill='black', font=font_small)
    y += 20
    draw.text((400, y), "SUBTOTAL Sin Impuestos: $22.66", fill='black', font=font_small)
    y += 20
    draw.text((400, y), "IVA 15%: $0.34", fill='black', font=font_small)
    y += 20
    draw.text((400, y), "VALOR TOTAL: $23.00", fill='black', font=font_large)
    y += 40
    
    # Additional info
    draw.text((50, y), "DIRECCION: JUAN JOSE MATIU", fill='black', font=font_small)
    y += 20
    draw.text((50, y), "DESCUENTO: $5.91", fill='black', font=font_small)
    y += 20
    draw.text((50, y), "DOCUMENTO INTERNO: FCC10324426", fill='black', font=font_small)
    y += 20
    draw.text((50, y), "EMAIL: rocio.mary@gmail.com", fill='black', font=font_small)
    
    return img

def test_parser_mejorado():
    """Prueba el parser mejorado"""
    print("🧪 PROBANDO PARSER MEJORADO")
    print("=" * 50)
    
    # Crear imagen
    img = crear_imagen_factura_mejorada()
    print(f"✅ Imagen de factura mejorada creada: {img.size} pixels")
    
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
            print(f"   - Número Factura: {factura.get('metadata', {}).get('invoice_number')}")
            print(f"   - Fecha Emisión: {factura.get('fechaEmision')}")
            print(f"   - Total: {factura.get('importeTotal')}")
            print(f"   - Clave Acceso: {factura.get('claveAcceso')}")
            
            # Verificar items
            detalles = factura.get("detalles", [])
            print(f"\n🛒 ITEMS DETECTADOS ({len(detalles)}):")
            for i, item in enumerate(detalles, 1):
                print(f"   {i}. {item.get('descripcion', 'N/A')} - Cant: {item.get('cantidad', 0)} - Precio: ${item.get('precioTotal', 0)}")
            
            # Verificar totals
            totals = factura.get("totals", {})
            print(f"\n💰 TOTALS:")
            print(f"   - Subtotal 15%: ${totals.get('subtotal15', 0)}")
            print(f"   - Subtotal 0%: ${totals.get('subtotal0', 0)}")
            print(f"   - Subtotal Sin Impuestos: ${totals.get('subtotal_sin_impuestos', 0)}")
            print(f"   - IVA 15%: ${totals.get('iva15', 0)}")
            print(f"   - Total: ${totals.get('total', 0)}")
            
            # Verificar validaciones financieras
            financial_checks = factura.get("financial_checks", {})
            print(f"\n🔍 VALIDACIONES FINANCIERAS:")
            print(f"   - Suma items: {financial_checks.get('sum_items')}")
            print(f"   - Items vs Subtotal: {financial_checks.get('items_vs_subtotal_sin_impuestos')}")
            print(f"   - Total recompuesto: {financial_checks.get('recomputed_total')}")
            print(f"   - Total vs Declarado: {financial_checks.get('recomputed_total_vs_total')}")
            
            # Verificar texto extraído
            texto_extraido = data.get("texto_extraido", "")
            print(f"\n📝 TEXTO EXTRAÍDO:")
            print(f"   - Longitud: {len(texto_extraido)} caracteres")
            if len(texto_extraido) > 200:
                print(f"   - Primeros 200 chars: {texto_extraido[:200]}...")
            else:
                print(f"   - Texto completo: {texto_extraido}")
            
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
    print("🧪 PRUEBA DEL PARSER MEJORADO")
    print("=" * 60)
    
    success = test_parser_mejorado()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ¡PRUEBA COMPLETADA!")
        print("   Verificar si las mejoras funcionan correctamente")
    else:
        print("⚠️  HAY PROBLEMAS QUE RESOLVER")
        print("   Revisar logs y configuración")

if __name__ == "__main__":
    main()
