#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para debuggear con la imagen real de la carpeta img
"""

import os
import base64
import json
from PIL import Image
import io

def procesar_imagen_real():
    """Procesa la imagen real de la carpeta img"""
    print("🔬 DEBUGGING CON IMAGEN REAL")
    print("=" * 50)
    
    # Buscar archivos de imagen en la carpeta helpers/IMG
    img_folder = "helpers/IMG"
    if not os.path.exists(img_folder):
        print(f"❌ Carpeta {img_folder} no existe")
        return False
    
    # Buscar archivos de imagen
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff']:
        import glob
        image_files.extend(glob.glob(os.path.join(img_folder, ext)))
    
    if not image_files:
        print(f"❌ No se encontraron archivos de imagen en {img_folder}")
        print("   Archivos soportados: .png, .jpg, .jpeg, .bmp, .tiff")
        return False
    
    print(f"✅ Encontrados {len(image_files)} archivos de imagen:")
    for i, file in enumerate(image_files, 1):
        print(f"   {i}. {file}")
    
    # Usar el primer archivo encontrado
    imagen_path = image_files[0]
    print(f"\n🔄 Procesando: {imagen_path}")
    
    try:
        # Leer imagen
        with open(imagen_path, 'rb') as f:
            archivo_bytes = f.read()
        
        print(f"✅ Imagen leída: {len(archivo_bytes)} bytes")
        
        # Convertir a base64
        imagen_base64 = base64.b64encode(archivo_bytes).decode('utf-8')
        print(f"✅ Imagen codificada en base64: {len(imagen_base64)} caracteres")
        
        # Probar parser avanzado directamente
        print("\n🔍 PROBANDO PARSER AVANZADO DIRECTO:")
        try:
            from helpers.invoice_capture_parser import parse_capture_from_bytes
            
            # Detectar tipo de archivo
            img = Image.open(io.BytesIO(archivo_bytes))
            tipo_archivo = img.format
            print(f"✅ Tipo de archivo detectado: {tipo_archivo}")
            
            # Ejecutar parser
            parse_result = parse_capture_from_bytes(archivo_bytes, f"real.{tipo_archivo.lower()}")
            print("✅ Parser ejecutado exitosamente")
            
            # Mostrar resultados
            print(f"\n📋 RESULTADOS DEL PARSER:")
            print(f"   - Texto OCR: {len(parse_result.ocr_text)} caracteres")
            print(f"   - RUC: {parse_result.metadata.ruc}")
            print(f"   - Número factura: {parse_result.metadata.invoice_number}")
            print(f"   - Clave acceso: {parse_result.metadata.access_key}")
            print(f"   - Ambiente: {parse_result.metadata.environment}")
            print(f"   - Fecha: {parse_result.metadata.issue_datetime}")
            print(f"   - Comprador: {parse_result.metadata.buyer_name}")
            print(f"   - Emisor: {parse_result.metadata.emitter_name}")
            print(f"   - Total: {parse_result.totals.total}")
            print(f"   - Items: {len(parse_result.items)}")
            
            # Mostrar texto extraído
            print(f"\n📝 TEXTO EXTRAÍDO (primeros 500 chars):")
            print(parse_result.ocr_text[:500])
            if len(parse_result.ocr_text) > 500:
                print("...")
            
            # Mostrar items
            if parse_result.items:
                print(f"\n🛒 ITEMS DETECTADOS:")
                for i, item in enumerate(parse_result.items, 1):
                    print(f"   {i}. {item.description} - Cant: {item.qty} - Precio: ${item.unit_price} - Total: ${item.line_total}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error en parser avanzado: {e}")
            print(f"   Tipo de error: {type(e).__name__}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            return False
        
    except Exception as e:
        print(f"❌ Error procesando imagen: {e}")
        return False

def test_endpoint_con_imagen_real():
    """Prueba el endpoint con la imagen real"""
    print("\n🌐 PROBANDO ENDPOINT CON IMAGEN REAL")
    print("=" * 50)
    
    # Buscar archivos de imagen
    img_folder = "helpers/IMG"
    if not os.path.exists(img_folder):
        print(f"❌ Carpeta {img_folder} no existe")
        return False
    
    import glob
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff']:
        image_files.extend(glob.glob(os.path.join(img_folder, ext)))
    
    if not image_files:
        print(f"❌ No se encontraron archivos de imagen en {img_folder}")
        return False
    
    imagen_path = image_files[0]
    print(f"🔄 Usando imagen: {imagen_path}")
    
    try:
        # Leer imagen y convertir a base64
        with open(imagen_path, 'rb') as f:
            archivo_bytes = f.read()
        
        imagen_base64 = base64.b64encode(archivo_bytes).decode('utf-8')
        
        # Preparar request
        import requests
        url = "http://localhost:8001/validar-imagen"
        payload = {
            "imagen_base64": imagen_base64
        }
        
        print("📡 Enviando request al endpoint...")
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
            
            # Verificar texto extraído
            texto_extraido = data.get("texto_extraido", "")
            print(f"\n📝 TEXTO EXTRAÍDO:")
            print(f"   - Longitud: {len(texto_extraido)} caracteres")
            print(f"   - Primeros 300 chars: {texto_extraido[:300]}...")
            
            return True
            
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en request: {e}")
        return False

def main():
    print("🔬 DEBUG CON IMAGEN REAL DE LA CARPETA IMG")
    print("=" * 60)
    
    # Probar parser directo
    parser_ok = procesar_imagen_real()
    
    # Probar endpoint
    endpoint_ok = test_endpoint_con_imagen_real()
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN:")
    print(f"   Parser directo: {'✅' if parser_ok else '❌'}")
    print(f"   Endpoint: {'✅' if endpoint_ok else '❌'}")
    
    if not parser_ok:
        print("\n⚠️  PROBLEMAS EN EL PARSER:")
        print("   - Revisar patrones de regex")
        print("   - Verificar calidad del OCR")
        print("   - Ajustar configuración de Tesseract")
    elif not endpoint_ok:
        print("\n⚠️  PROBLEMAS EN EL ENDPOINT:")
        print("   - Verificar logs del servidor")
        print("   - Revisar integración del parser")
    else:
        print("\n🎉 ¡TODO FUNCIONANDO CORRECTAMENTE!")

if __name__ == "__main__":
    main()
