#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para simular exactamente lo que hace el endpoint validar_imagen
"""

import base64
import json
from PIL import Image, ImageDraw, ImageFont
import io
import time

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

def detectar_tipo_archivo(imagen_base64):
    """Simula la función detectar_tipo_archivo"""
    try:
        # Decodificar base64
        imagen_bytes = base64.b64decode(imagen_base64)
        
        # Detectar tipo usando PIL
        from PIL import Image
        import io
        
        img = Image.open(io.BytesIO(imagen_bytes))
        formato = img.format
        
        return {
            "valido": True,
            "tipo": formato,
            "extension": formato.lower(),
            "mime_type": f"image/{formato.lower()}"
        }
    except Exception as e:
        return {
            "valido": False,
            "error": str(e)
        }

def _extraer_texto_imagen(archivo_bytes):
    """Simula la función _extraer_texto_imagen"""
    try:
        from PIL import Image
        import pytesseract
        import io
        
        img = Image.open(io.BytesIO(archivo_bytes))
        texto = pytesseract.image_to_string(img, lang='spa')
        return texto
    except Exception as e:
        print(f"Error en OCR básico: {e}")
        return ""

def _extraer_campos_factura_imagen(texto):
    """Simula la función _extraer_campos_factura_imagen"""
    import re
    
    campos = {}
    
    # RUC
    ruc_match = re.search(r'RUC[:\s]*(\d{13})', texto)
    if ruc_match:
        campos['ruc'] = ruc_match.group(1)
    
    # Razón Social
    razon_match = re.search(r'Razón Social[:\s]*([^\n]+)', texto)
    if razon_match:
        campos['razonSocial'] = razon_match.group(1).strip()
    
    # Fecha
    fecha_match = re.search(r'Fecha[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', texto)
    if fecha_match:
        campos['fechaEmision'] = fecha_match.group(1)
    
    # Total
    total_match = re.search(r'Total[:\s]*\$?(\d+[.,]\d{2})', texto)
    if total_match:
        campos['importeTotal'] = float(total_match.group(1).replace(',', '.'))
    
    # Clave Acceso
    clave_match = re.search(r'(\d{49})', texto)
    if clave_match:
        campos['claveAcceso'] = clave_match.group(1)
    
    return campos

def simular_endpoint():
    """Simula exactamente el flujo del endpoint"""
    print("🔬 SIMULANDO ENDPOINT VALIDAR_IMAGEN")
    print("=" * 60)
    
    # 1) Crear imagen y convertir a base64
    img = crear_imagen_debug()
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    archivo_bytes = img_bytes.getvalue()
    
    imagen_base64 = base64.b64encode(archivo_bytes).decode('utf-8')
    print(f"✅ Imagen creada y codificada: {len(imagen_base64)} caracteres")
    
    # 2) Detectar tipo de archivo
    t0 = time.perf_counter()
    tipo_info = detectar_tipo_archivo(imagen_base64)
    if not tipo_info["valido"]:
        print(f"❌ Error en detección de tipo: {tipo_info.get('error')}")
        return False
    
    tipo_archivo = tipo_info["tipo"]
    print(f"✅ Tipo detectado: {tipo_archivo} ({time.perf_counter() - t0:.3f}s)")
    
    # 3) Parser avanzado de facturas SRI
    t0 = time.perf_counter()
    try:
        from helpers.invoice_capture_parser import parse_capture_from_bytes
        print("✅ Parser importado correctamente")
        
        print("🔄 Ejecutando parse_capture_from_bytes...")
        parse_result = parse_capture_from_bytes(archivo_bytes, f"capture.{tipo_archivo.lower()}")
        print("✅ Parser ejecutado exitosamente")
        
        texto_extraido = parse_result.ocr_text
        campos_factura_avanzados = {
            "ruc": parse_result.metadata.ruc,
            "razonSocial": parse_result.metadata.buyer_name,
            "fechaEmision": parse_result.metadata.issue_datetime,
            "importeTotal": parse_result.totals.total,
            "claveAcceso": parse_result.metadata.access_key,
            "detalles": [{
                "cantidad": item.qty or 0,
                "descripcion": item.description or "",
                "precioTotal": item.line_total or 0
            } for item in parse_result.items],
            "totals": {
                "subtotal15": parse_result.totals.subtotal15,
                "subtotal0": parse_result.totals.subtotal0,
                "subtotal_no_objeto": parse_result.totals.subtotal_no_objeto,
                "subtotal_sin_impuestos": parse_result.totals.subtotal_sin_impuestos,
                "descuento": parse_result.totals.descuento,
                "iva15": parse_result.totals.iva15,
                "total": parse_result.totals.total
            },
            "barcodes": parse_result.barcodes,
            "financial_checks": parse_result.checks,
            "metadata": {
                "invoice_number": parse_result.metadata.invoice_number,
                "authorization": parse_result.metadata.authorization,
                "environment": parse_result.metadata.environment,
                "buyer_id": parse_result.metadata.buyer_id,
                "emitter_name": parse_result.metadata.emitter_name,
                "file_metadata": {
                    "sha256": parse_result.metadata.sha256,
                    "width": parse_result.metadata.width,
                    "height": parse_result.metadata.height,
                    "dpi": parse_result.metadata.dpi,
                    "mode": parse_result.metadata.mode,
                    "format": parse_result.metadata.format
                }
            }
        }
        print(f"✅ Parser avanzado completado ({time.perf_counter() - t0:.3f}s)")
        
    except Exception as e:
        print(f"❌ Error en parser avanzado: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        # Fallback al método anterior
        texto_extraido = _extraer_texto_imagen(archivo_bytes)
        campos_factura_avanzados = _extraer_campos_factura_imagen(texto_extraido)
        print(f"✅ Fallback completado ({time.perf_counter() - t0:.3f}s)")
    
    # 4) Mostrar resultados
    print(f"\n📋 RESULTADOS:")
    print(f"   - RUC: {campos_factura_avanzados.get('ruc')}")
    print(f"   - Razón Social: {campos_factura_avanzados.get('razonSocial')}")
    print(f"   - Fecha Emisión: {campos_factura_avanzados.get('fechaEmision')}")
    print(f"   - Total: {campos_factura_avanzados.get('importeTotal')}")
    print(f"   - Clave Acceso: {campos_factura_avanzados.get('claveAcceso')}")
    print(f"   - Items: {len(campos_factura_avanzados.get('detalles', []))}")
    print(f"   - Texto extraído: {len(texto_extraido)} caracteres")
    
    return True

def main():
    print("🔬 DEBUG SIMULACIÓN DE ENDPOINT")
    print("=" * 60)
    
    success = simular_endpoint()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ¡SIMULACIÓN COMPLETADA!")
        print("   El parser debería funcionar en el endpoint")
    else:
        print("⚠️  HAY PROBLEMAS EN LA SIMULACIÓN")
        print("   Revisar los errores mostrados arriba")

if __name__ == "__main__":
    main()
