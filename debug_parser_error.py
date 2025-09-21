#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para debuggear el error del parser avanzado
"""

import base64
import json
from PIL import Image, ImageDraw, ImageFont
import io

def crear_imagen_debug():
    """Crea una imagen simple para debug"""
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

def test_parser_directo():
    """Prueba el parser directamente para ver el error"""
    print("🔬 PROBANDO PARSER DIRECTO")
    print("=" * 50)
    
    # Crear imagen
    img = crear_imagen_debug()
    print(f"✅ Imagen creada: {img.size} pixels")
    
    # Convertir a bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    archivo_bytes = img_bytes.getvalue()
    print(f"✅ Imagen convertida a bytes: {len(archivo_bytes)} bytes")
    
    # Probar parser avanzado directamente
    try:
        from helpers.invoice_capture_parser import parse_capture_from_bytes
        print("✅ Parser importado correctamente")
        
        print("🔄 Ejecutando parser...")
        parse_result = parse_capture_from_bytes(archivo_bytes, "debug.png")
        print("✅ Parser ejecutado exitosamente")
        
        print(f"   - Texto OCR: {len(parse_result.ocr_text)} caracteres")
        print(f"   - RUC: {parse_result.metadata.ruc}")
        print(f"   - Número factura: {parse_result.metadata.invoice_number}")
        print(f"   - Clave acceso: {parse_result.metadata.access_key}")
        print(f"   - Total: {parse_result.totals.total}")
        print(f"   - Items: {len(parse_result.items)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en parser directo: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        import traceback
        print(f"   Traceback completo:")
        print(traceback.format_exc())
        return False

def test_parser_con_texto_real():
    """Prueba el parser con el texto real extraído"""
    print("\n🔬 PROBANDO PARSER CON TEXTO REAL")
    print("=" * 50)
    
    # Texto real extraído del JSON
    texto_real = "[FARMACIRS V COMISARIATOS DE MEDIGINAS SA.\n|FARCOMED\n\ncement pect te:\n\nRUC:\n\nFACTURA\nNo. 026-200-000021384\n\n4790710319001\n\nNUMERO DE AUTORIZACION\noecr20asots7907103190012025200000021 3845658032318\n\n| AMBIENTE: PRODUCCION\n\nFECHA Y HORA DE 2025-07-08 195813\n\n|CLAVE DE ACCESO\n\nRazin Socal/ Nombresy Apelidos: ROCIO VERDEZOTO\ndena srieeeso14\nFecha Emin n0772025\n\noa Pens escricn\n\nDIRECCION\nDESCUENTO\nDEDUCIELE MEDICINAS\nNOMBRE PACIENTE.\nOCUMENTO INTERNO\n\nForma Pago\n'TARJETADE CREDITO"
    
    try:
        from helpers.invoice_capture_parser import extract_fields_from_text
        print("✅ Función extract_fields_from_text importada correctamente")
        
        print("🔄 Ejecutando extracción de campos...")
        result = extract_fields_from_text(texto_real)
        print("✅ Extracción ejecutada exitosamente")
        
        fields = result["fields"]
        totals = result["totals"]
        items = result["items"]
        
        print(f"\n📋 CAMPOS EXTRAÍDOS:")
        print(f"   - RUC: {fields.get('ruc')}")
        print(f"   - Número factura: {fields.get('invoice_number')}")
        print(f"   - Clave acceso: {fields.get('access_key')}")
        print(f"   - Ambiente: {fields.get('environment')}")
        print(f"   - Fecha: {fields.get('issue_datetime')}")
        print(f"   - Comprador: {fields.get('buyer_name')}")
        print(f"   - Emisor: {fields.get('emitter_name')}")
        
        print(f"\n💰 TOTALS:")
        print(f"   - Total: {totals.total}")
        print(f"   - Subtotal 15%: {totals.subtotal15}")
        print(f"   - Subtotal 0%: {totals.subtotal0}")
        print(f"   - Descuento: {totals.descuento}")
        
        print(f"\n🛒 ITEMS ({len(items)}):")
        for i, item in enumerate(items, 1):
            print(f"   {i}. {item.description} - Cant: {item.qty} - Precio: ${item.unit_price} - Total: ${item.line_total}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en extracción de campos: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        import traceback
        print(f"   Traceback completo:")
        print(traceback.format_exc())
        return False

def main():
    print("🔬 DEBUG DEL PARSER AVANZADO")
    print("=" * 60)
    
    # Probar parser directo
    parser_ok = test_parser_directo()
    
    # Probar extracción de campos
    extraction_ok = test_parser_con_texto_real()
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN:")
    print(f"   Parser directo: {'✅' if parser_ok else '❌'}")
    print(f"   Extracción campos: {'✅' if extraction_ok else '❌'}")
    
    if not parser_ok or not extraction_ok:
        print("\n⚠️  PROBLEMAS DETECTADOS:")
        print("   - Revisar el error específico mostrado arriba")
        print("   - Verificar que todas las dependencias estén instaladas")
        print("   - Revisar la configuración de Tesseract")
    else:
        print("\n🎉 ¡PARSER FUNCIONANDO CORRECTAMENTE!")

if __name__ == "__main__":
    main()
