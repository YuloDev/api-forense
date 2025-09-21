#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de prueba para el parser avanzado de facturas SRI integrado en validar-imagen
"""

import base64
import requests
import json
from pathlib import Path

def test_parser_avanzado():
    """Prueba el parser avanzado con una imagen de ejemplo"""
    
    # URL del endpoint
    url = "http://localhost:8000/validar-imagen"
    
    # Crear una imagen de prueba más realista
    from PIL import Image, ImageDraw, ImageFont
    import io
    
    # Crear imagen de prueba con texto
    img = Image.new('RGB', (600, 800), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
    
    # Simular una factura básica
    y = 50
    draw.text((50, y), "FARMACIAS FYBECA", fill='black', font=font)
    y += 30
    draw.text((50, y), "RUC: 1234567890001", fill='black', font=font)
    y += 30
    draw.text((50, y), "FACTURA No. 001-001-000123456", fill='black', font=font)
    y += 30
    draw.text((50, y), "Clave de Acceso: 1234567890123456789012345678901234567890123456789", fill='black', font=font)
    y += 30
    draw.text((50, y), "Fecha: 2024-01-15 10:30:00", fill='black', font=font)
    y += 50
    draw.text((50, y), "SUBTOTAL 15%: $100.00", fill='black', font=font)
    y += 20
    draw.text((50, y), "IVA 15%: $15.00", fill='black', font=font)
    y += 20
    draw.text((50, y), "TOTAL: $115.00", fill='black', font=font)
    
    # Convertir a bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    
    # Codificar en base64
    imagen_base64 = base64.b64encode(img_bytes).decode('utf-8')
    
    # Preparar request
    payload = {
        "imagen_base64": imagen_base64
    }
    
    try:
        print("🧪 Probando parser avanzado de facturas SRI...")
        print(f"📡 Enviando request a: {url}")
        
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Respuesta exitosa!")
            print(f"📊 Tipo de archivo: {result.get('tipo_archivo')}")
            print(f"📝 Mensaje: {result.get('mensaje')}")
            
            # Verificar parser avanzado
            parser_info = result.get('parser_avanzado', {})
            print(f"\n🔍 Parser Avanzado:")
            print(f"   - Disponible: {parser_info.get('disponible')}")
            print(f"   - Códigos detectados: {parser_info.get('barcodes_detectados')}")
            print(f"   - Ítems detectados: {parser_info.get('items_detectados')}")
            
            # Verificar validaciones financieras
            financial_checks = parser_info.get('validaciones_financieras', {})
            if financial_checks:
                print(f"\n💰 Validaciones Financieras:")
                print(f"   - Suma ítems: {financial_checks.get('sum_items')}")
                print(f"   - Items vs subtotal: {financial_checks.get('items_vs_subtotal_sin_impuestos')}")
                print(f"   - Total recompuesto: {financial_checks.get('recomputed_total')}")
                print(f"   - Recompuesto vs total: {financial_checks.get('recomputed_total_vs_total')}")
            
            # Verificar metadatos avanzados
            metadata = parser_info.get('metadatos_avanzados', {})
            if metadata:
                print(f"\n📋 Metadatos Avanzados:")
                print(f"   - RUC: {metadata.get('ruc')}")
                print(f"   - Número factura: {metadata.get('invoice_number')}")
                print(f"   - Clave acceso: {metadata.get('authorization')}")
                print(f"   - Ambiente: {metadata.get('environment')}")
                print(f"   - Emisor: {metadata.get('emitter_name')}")
            
            # Verificar checks de riesgo
            riesgo = result.get('riesgo', {})
            print(f"\n⚠️  Evaluación de Riesgo:")
            print(f"   - Score: {riesgo.get('score')}")
            print(f"   - Nivel: {riesgo.get('nivel')}")
            print(f"   - Es falso probable: {riesgo.get('es_falso_probable')}")
            
            # Mostrar checks prioritarias
            prioritarias = riesgo.get('prioritarias', [])
            if prioritarias:
                print(f"\n🔴 Checks Prioritarias ({len(prioritarias)}):")
                for i, check in enumerate(prioritarias, 1):
                    print(f"   {i}. {check.get('check')} (penalización: {check.get('penalizacion')})")
            
            # Mostrar checks secundarias
            secundarias = riesgo.get('secundarias', [])
            if secundarias:
                print(f"\n🟡 Checks Secundarias ({len(secundarias)}):")
                for i, check in enumerate(secundarias, 1):
                    print(f"   {i}. {check.get('check')} (penalización: {check.get('penalizacion')})")
            
            # Mostrar checks adicionales
            adicionales = riesgo.get('adicionales', [])
            if adicionales:
                print(f"\n🟢 Checks Adicionales ({len(adicionales)}):")
                for i, check in enumerate(adicionales, 1):
                    print(f"   {i}. {check.get('check')} (penalización: {check.get('penalizacion')})")
            
            print(f"\n📄 Texto extraído (primeros 200 chars):")
            texto = result.get('texto_extraido', '')
            print(f"   {texto[:200]}{'...' if len(texto) > 200 else ''}")
            
        else:
            print(f"❌ Error en la respuesta: {response.status_code}")
            print(f"   Detalle: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se puede conectar al servidor. ¿Está ejecutándose en localhost:8000?")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

def test_parser_con_imagen_real():
    """Prueba con una imagen real si está disponible"""
    
    # Buscar imágenes de prueba en el directorio
    image_extensions = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']
    test_images = []
    
    for ext in image_extensions:
        test_images.extend(Path('.').glob(f'*{ext}'))
        test_images.extend(Path('.').glob(f'*{ext.upper()}'))
    
    if not test_images:
        print("ℹ️  No se encontraron imágenes de prueba en el directorio actual")
        return
    
    print(f"🖼️  Encontradas {len(test_images)} imágenes de prueba:")
    for img in test_images:
        print(f"   - {img.name}")
    
    # Probar con la primera imagen encontrada
    test_image = test_images[0]
    print(f"\n🧪 Probando con: {test_image.name}")
    
    try:
        # Leer y codificar imagen
        with open(test_image, 'rb') as f:
            image_bytes = f.read()
        
        imagen_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Preparar request
        payload = {
            "imagen_base64": imagen_base64
        }
        
        url = "http://localhost:8000/validar-imagen"
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Análisis exitoso!")
            
            # Mostrar información del parser avanzado
            parser_info = result.get('parser_avanzado', {})
            print(f"\n🔍 Parser Avanzado:")
            print(f"   - Disponible: {parser_info.get('disponible')}")
            print(f"   - Códigos detectados: {parser_info.get('barcodes_detectados')}")
            print(f"   - Ítems detectados: {parser_info.get('items_detectados')}")
            
            # Mostrar información financiera
            financial_checks = parser_info.get('validaciones_financieras', {})
            if financial_checks:
                print(f"\n💰 Validaciones Financieras:")
                for key, value in financial_checks.items():
                    print(f"   - {key}: {value}")
            
            # Mostrar metadatos
            metadata = parser_info.get('metadatos_avanzados', {})
            if metadata:
                print(f"\n📋 Metadatos:")
                for key, value in metadata.items():
                    if isinstance(value, dict):
                        print(f"   - {key}:")
                        for subkey, subvalue in value.items():
                            print(f"     - {subkey}: {subvalue}")
                    else:
                        print(f"   - {key}: {value}")
            
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error procesando imagen: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando pruebas del parser avanzado de facturas SRI")
    print("=" * 60)
    
    # Prueba básica
    test_parser_avanzado()
    
    print("\n" + "=" * 60)
    
    # Prueba con imagen real si está disponible
    test_parser_con_imagen_real()
    
    print("\n✅ Pruebas completadas!")
