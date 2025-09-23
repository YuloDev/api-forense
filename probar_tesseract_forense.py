#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar específicamente la configuración de Tesseract en el análisis forense
"""

import requests
import json
import os
from PIL import Image, ImageDraw, ImageFont
import io

def crear_imagen_con_texto():
    """Crea una imagen simple con texto para probar OCR"""
    
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Agregar texto de prueba
    draw.text((20, 50), "PRUEBA OCR TESSERACT", fill='black', font=font)
    draw.text((20, 80), "RUC: 1234567890123", fill='black', font=font)
    draw.text((20, 110), "TOTAL: $100.00", fill='black', font=font)
    draw.text((20, 140), "FECHA: 2024-01-15", fill='black', font=font)
    
    # Guardar en memoria
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes.getvalue()

def probar_configuracion_tesseract():
    """Prueba la configuración de Tesseract"""
    
    print("🔍 PROBANDO CONFIGURACIÓN DE TESSERACT")
    print("=" * 60)
    
    # Crear imagen de prueba
    print("1. Creando imagen de prueba...")
    image_bytes = crear_imagen_con_texto()
    print(f"   ✅ Imagen creada: {len(image_bytes)} bytes")
    
    # Probar endpoint
    print("\n2. Probando endpoint de análisis forense...")
    files = {'file': ('imagen_prueba.png', image_bytes, 'image/png')}
    
    try:
        response = requests.post(
            "http://localhost:8001/analizar-imagen-forense",
            files=files,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Respuesta recibida del servidor")
            
            # Verificar análisis forense
            analisis = data.get('analisis_forense', {})
            
            # Verificar texto superpuesto
            overlays = analisis.get('text_overlays', {})
            print(f"\n📝 DETECCIÓN DE TEXTO SUPERPUESTO:")
            print(f"   Disponible: {overlays.get('available', False)}")
            
            if overlays.get('available', False):
                print("   ✅ Tesseract funcionando correctamente")
                print(f"   Regiones de texto detectadas: {overlays.get('total_text_regions', 0)}")
                print(f"   Textos sospechosos: {overlays.get('count', 0)}")
                
                # Mostrar detecciones
                detections = overlays.get('detections', [])
                if detections:
                    print("   Detecciones específicas:")
                    for i, det in enumerate(detections[:3]):
                        print(f"     {i+1}. '{det.get('text', '')}' - Score: {det.get('suspicious_score', 0)}")
                else:
                    print("   ✅ No se detectaron textos sospechosos (normal para imagen limpia)")
            else:
                print(f"   ❌ Tesseract no disponible: {overlays.get('reason', 'Error desconocido')}")
            
            # Verificar OCR general
            ocr = analisis.get('ocr_rules', {})
            print(f"\n📖 OCR GENERAL:")
            print(f"   Disponible: {ocr.get('available', False)}")
            if ocr.get('available', False):
                text_excerpt = ocr.get('text_excerpt', '')
                print(f"   Texto extraído: {text_excerpt[:100]}...")
                print("   ✅ OCR funcionando correctamente")
            else:
                print("   ❌ OCR no disponible")
            
            # Verificar dependencias
            print(f"\n🔧 DEPENDENCIAS:")
            print(f"   OpenCV: {analisis.get('copy_move', {}).get('available', False)}")
            print(f"   Tesseract: {overlays.get('available', False)}")
            print(f"   PIL: True")
            
            # Score de sospecha
            suspicion = analisis.get('suspicion', {})
            print(f"\n⚠️ NIVEL DE SOSPECHA:")
            print(f"   Score total: {suspicion.get('score_0_100', 0)}")
            print(f"   Etiqueta: {suspicion.get('label', 'N/A')}")
            
            # Guardar resultado
            with open("resultado_tesseract_forense.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Resultado guardado en: resultado_tesseract_forense.json")
            
        else:
            print(f"   ❌ Error del servidor: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Error de conexión: El servidor no está ejecutándose")
        print("   Inicia el servidor con: python configurar_tesseract_global.py")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def probar_info_endpoint():
    """Prueba el endpoint de información"""
    
    print("\n🔍 PROBANDO ENDPOINT DE INFORMACIÓN")
    print("=" * 60)
    
    try:
        response = requests.get("http://localhost:8001/analisis-forense-info", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Endpoint de información funcionando")
            
            dependencias = data.get('dependencias', {})
            print(f"\n📋 DEPENDENCIAS:")
            print(f"   OpenCV: {dependencias.get('opencv', False)}")
            print(f"   Tesseract: {dependencias.get('pytesseract', False)}")
            print(f"   Sklearn: {dependencias.get('sklearn', False)}")
            print(f"   PIL: {dependencias.get('pil', False)}")
            
            analisis_incluidos = data.get('analisis_incluidos', [])
            print(f"\n🔍 ANÁLISIS INCLUIDOS:")
            for i, analisis in enumerate(analisis_incluidos, 1):
                print(f"   {i}. {analisis}")
                
        else:
            print(f"   ❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    """Función principal"""
    
    print("🚀 PRUEBA DE CONFIGURACIÓN TESSERACT EN ANÁLISIS FORENSE")
    print("=" * 70)
    
    # Probar endpoint de información
    probar_info_endpoint()
    
    # Probar configuración de Tesseract
    probar_configuracion_tesseract()
    
    print("\n✅ PRUEBA COMPLETADA")
    print("\n💡 Si Tesseract no funciona:")
    print("   1. Verifica que esté instalado en: C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
    print("   2. Inicia el servidor con: python configurar_tesseract_global.py")
    print("   3. Verifica que no haya otros procesos usando Tesseract")

if __name__ == "__main__":
    main()
