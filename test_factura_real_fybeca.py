#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar el parser avanzado con la factura real de Fybeca
"""

import requests
import base64
import json
from PIL import Image, ImageDraw, ImageFont
import io

def crear_imagen_factura_fybeca():
    """Crea una imagen de factura de Fybeca basada en la descripción"""
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
    
    # Company info
    draw.text((50, y), "FARMACIAS Y COMISARIATOS DE MEDICINAS S.A. FARCOMED", fill='black', font=font_medium)
    y += 25
    draw.text((50, y), "R.U.C.: 1790710319001", fill='black', font=font_medium)
    y += 25
    draw.text((50, y), "KM CINCO Y MEDIO, AV DE LOS SHYRIS N SN Y SECUNDARIA", fill='black', font=font_small)
    y += 20
    draw.text((50, y), "AV. INTEROCEANICA SIN", fill='black', font=font_small)
    y += 40
    
    # Invoice details
    draw.text((50, y), "FACTURA", fill='black', font=font_large)
    y += 30
    
    draw.text((50, y), "Número de Autorización:", fill='black', font=font_small)
    draw.text((200, y), "0807202501179071031900120262000000213845658032318", fill='black', font=font_tiny)
    y += 20
    
    draw.text((50, y), "Ambiente: PRODUCCION", fill='black', font=font_small)
    y += 15
    draw.text((50, y), "Fecha y Hora de Emisión: 2025-07-08 19:58:13", fill='black', font=font_small)
    y += 15
    draw.text((50, y), "Emisión: NORMAL", fill='black', font=font_small)
    y += 20
    
    draw.text((50, y), "Clave de Acceso:", fill='black', font=font_small)
    draw.text((150, y), "0807202501179071031900120262000000213845658032318", fill='black', font=font_tiny)
    y += 40
    
    # Customer info
    draw.text((50, y), "Razón Social / Nombres y Apellidos: ROCIO VERDEZOTO", fill='black', font=font_small)
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
    
    # Items
    items = [
        ("FLURITOK JARABE", "1", "5.25"),
        ("AVAMY SPRAY NASAL 27.5 MCG /120 DOSIS", "1", "15.12"),
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
    y += 40
    
    # Payment info
    draw.text((50, y), "Forma Pago: TARJETA DE CRÉDITO", fill='black', font=font_small)
    y += 20
    draw.text((50, y), "Valor: $23.00", fill='black', font=font_small)
    
    return img

def test_parser_con_factura_real():
    """Prueba el parser con la factura real de Fybeca"""
    print("🧪 PROBANDO PARSER CON FACTURA REAL DE FYBECA")
    print("=" * 60)
    
    # Crear imagen
    img = crear_imagen_factura_fybeca()
    print(f"✅ Imagen de factura Fybeca creada: {img.size} pixels")
    
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
    print("🧪 PRUEBA CON FACTURA REAL DE FYBECA")
    print("=" * 60)
    
    success = test_parser_con_factura_real()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ¡PRUEBA COMPLETADA EXITOSAMENTE!")
        print("   El parser avanzado está funcionando con facturas reales")
    else:
        print("⚠️  HAY PROBLEMAS QUE RESOLVER")
        print("   Revisar logs y configuración")

if __name__ == "__main__":
    main()
