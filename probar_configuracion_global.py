#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar que la configuración global de Tesseract funcione en todos los endpoints
"""

import requests
import json
import os
from PIL import Image, ImageDraw, ImageFont
import io
import base64

def crear_imagen_prueba():
    """Crea una imagen de prueba simple"""
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    draw.text((20, 50), "FACTURA DE PRUEBA", fill='black', font=font)
    draw.text((20, 80), "RUC: 1234567890123", fill='black', font=font)
    draw.text((20, 110), "TOTAL: $100.00", fill='black', font=font)
    draw.text((20, 140), "FECHA: 2024-01-15", fill='black', font=font)
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes.getvalue()

def crear_pdf_prueba():
    """Crea un PDF de prueba simple"""
    # Para esta prueba, usaremos la imagen como base64
    img_bytes = crear_imagen_prueba()
    return base64.b64encode(img_bytes).decode('utf-8')

def probar_endpoint(endpoint, data, nombre):
    """Prueba un endpoint específico"""
    print(f"\n🔍 PROBANDO {nombre}")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"http://localhost:8001{endpoint}",
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"   ✅ {nombre} funcionando correctamente")
            result = response.json()
            
            # Verificar si hay datos extraídos
            if 'factura' in result:
                factura = result['factura']
                print(f"   📋 Datos extraídos:")
                print(f"      RUC: {factura.get('ruc', 'N/A')}")
                print(f"      Total: {factura.get('total', 'N/A')}")
                print(f"      Clave Acceso: {factura.get('claveAcceso', 'N/A')}")
            
            if 'sri_verificado' in result:
                print(f"   🔍 SRI Verificado: {result.get('sri_verificado', False)}")
            
            if 'text_overlays' in result:
                overlays = result['text_overlays']
                print(f"   📝 Texto superpuesto: {overlays.get('available', False)}")
                print(f"      Textos detectados: {overlays.get('count', 0)}")
            
            return True
            
        else:
            print(f"   ❌ Error en {nombre}: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error en {nombre}: {e}")
        return False

def probar_analisis_forense():
    """Prueba el endpoint de análisis forense"""
    print(f"\n🔍 PROBANDO ANÁLISIS FORENSE")
    print("=" * 50)
    
    # Crear imagen de prueba
    img_bytes = crear_imagen_prueba()
    
    files = {'file': ('imagen_prueba.png', img_bytes, 'image/png')}
    
    try:
        response = requests.post(
            "http://localhost:8001/analizar-imagen-forense",
            files=files,
            timeout=60
        )
        
        if response.status_code == 200:
            print("   ✅ Análisis forense funcionando correctamente")
            result = response.json()
            
            analisis = result.get('analisis_forense', {})
            overlays = analisis.get('text_overlays', {})
            print(f"   📝 Texto superpuesto: {overlays.get('available', False)}")
            print(f"      Textos detectados: {overlays.get('count', 0)}")
            
            suspicion = analisis.get('suspicion', {})
            print(f"   ⚠️ Nivel de sospecha: {suspicion.get('score_0_100', 0)}")
            
            return True
        else:
            print(f"   ❌ Error en análisis forense: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error en análisis forense: {e}")
        return False

def main():
    """Función principal"""
    
    print("🚀 PRUEBA DE CONFIGURACIÓN GLOBAL DE TESSERACT")
    print("=" * 70)
    
    # Crear datos de prueba
    pdf_base64 = crear_pdf_prueba()
    
    # Lista de endpoints a probar
    endpoints = [
        {
            "endpoint": "/validar-factura-nuevo",
            "data": {"pdfbase64": pdf_base64},
            "nombre": "VALIDAR FACTURA NUEVO"
        },
        {
            "endpoint": "/validar-factura",
            "data": {"pdfbase64": pdf_base64},
            "nombre": "VALIDAR FACTURA"
        },
        {
            "endpoint": "/validar-imagen",
            "data": {"imagenbase64": base64.b64encode(crear_imagen_prueba()).decode('utf-8')},
            "nombre": "VALIDAR IMAGEN"
        }
    ]
    
    resultados = []
    
    # Probar endpoints
    for ep in endpoints:
        resultado = probar_endpoint(ep["endpoint"], ep["data"], ep["nombre"])
        resultados.append((ep["nombre"], resultado))
    
    # Probar análisis forense
    resultado_forense = probar_analisis_forense()
    resultados.append(("ANÁLISIS FORENSE", resultado_forense))
    
    # Resumen
    print(f"\n📊 RESUMEN DE PRUEBAS")
    print("=" * 70)
    
    exitosos = 0
    total = len(resultados)
    
    for nombre, resultado in resultados:
        status = "✅ ÉXITO" if resultado else "❌ FALLO"
        print(f"   {nombre}: {status}")
        if resultado:
            exitosos += 1
    
    print(f"\n🎯 RESULTADO FINAL:")
    print(f"   Exitosos: {exitosos}/{total}")
    print(f"   Porcentaje: {(exitosos/total)*100:.1f}%")
    
    if exitosos == total:
        print("   🎉 ¡TODOS LOS ENDPOINTS FUNCIONANDO CORRECTAMENTE!")
        print("   ✅ La configuración global de Tesseract está funcionando")
    else:
        print("   ⚠️ Algunos endpoints fallaron")
        print("   🔧 Verifica la configuración de Tesseract")

if __name__ == "__main__":
    main()
