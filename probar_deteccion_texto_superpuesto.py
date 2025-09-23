#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar específicamente la detección de texto superpuesto
"""

import requests
import json
import os
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np

def crear_imagen_con_texto_superpuesto():
    """Crea una imagen con texto superpuesto para probar la detección"""
    
    # Crear imagen base (simulando un documento escaneado)
    img = Image.new('RGB', (600, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Texto original (simulando texto del documento)
    draw.text((50, 50), "FACTURA DE VENTA", fill='black', font=font_large)
    draw.text((50, 100), "RUC: 1234567890123", fill='black', font=font_small)
    draw.text((50, 130), "Fecha: 2024-01-15", fill='black', font=font_small)
    draw.text((50, 160), "Cliente: Juan Pérez", fill='black', font=font_small)
    draw.text((50, 190), "Total: $150.00", fill='black', font=font_small)
    
    # Agregar texto superpuesto (simulando manipulación)
    # Este texto tendrá características típicas de texto digital superpuesto
    
    # Texto superpuesto 1: Muy uniforme, alto contraste
    overlay_text1 = "MODIFICADO"
    draw.rectangle([200, 200, 350, 230], fill='white', outline='black', width=2)
    draw.text((210, 205), overlay_text1, fill='black', font=font_small)
    
    # Texto superpuesto 2: Diferente tamaño de fuente
    overlay_text2 = "FALSO"
    draw.rectangle([400, 100, 480, 130], fill='white', outline='red', width=2)
    draw.text((410, 105), overlay_text2, fill='red', font=font_large)
    
    # Texto superpuesto 3: Con fondo sólido (típico de superposición)
    overlay_text3 = "ALTERADO"
    draw.rectangle([300, 300, 450, 330], fill='yellow', outline='black', width=1)
    draw.text((310, 305), overlay_text3, fill='black', font=font_small)
    
    # Agregar algo de ruido para simular escaneo
    img_array = np.array(img)
    noise = np.random.normal(0, 10, img_array.shape).astype(np.uint8)
    img_array = np.clip(img_array + noise, 0, 255)
    img = Image.fromarray(img_array.astype(np.uint8))
    
    # Guardar en memoria
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes.getvalue()

def crear_imagen_sin_manipulacion():
    """Crea una imagen sin texto superpuesto para comparar"""
    
    img = Image.new('RGB', (500, 300), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Solo texto original
    draw.text((50, 50), "DOCUMENTO ORIGINAL", fill='black', font=font)
    draw.text((50, 100), "RUC: 1234567890123", fill='black', font=font)
    draw.text((50, 130), "Fecha: 2024-01-15", fill='black', font=font)
    draw.text((50, 160), "Total: $100.00", fill='black', font=font)
    
    # Guardar en memoria
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes.getvalue()

def probar_deteccion_texto_superpuesto():
    """Prueba la detección de texto superpuesto"""
    
    print("🔍 PROBANDO DETECCIÓN DE TEXTO SUPERPUESTO")
    print("=" * 60)
    
    # Probar imagen con texto superpuesto
    print("\n1. Probando imagen CON texto superpuesto...")
    image_bytes = crear_imagen_con_texto_superpuesto()
    
    files = {'file': ('imagen_con_superposicion.png', image_bytes, 'image/png')}
    
    try:
        response = requests.post(
            "http://localhost:8001/analizar-imagen-forense",
            files=files,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            analisis = data.get('analisis_forense', {})
            
            print("   ✅ Análisis completado")
            
            # Mostrar detección de texto superpuesto
            overlays = analisis.get('text_overlays', {})
            print(f"   Textos sospechosos detectados: {overlays.get('count', 0)}")
            
            detections = overlays.get('detections', [])
            for i, det in enumerate(detections):
                print(f"   {i+1}. '{det.get('text', '')}' - Score: {det.get('suspicious_score', 0)}")
                print(f"      Razones: {', '.join(det.get('reasons', []))}")
                metrics = det.get('metrics', {})
                print(f"      Varianza: {metrics.get('var_intensity', 0):.2f}")
                print(f"      Contraste: {metrics.get('contrast', 0):.2f}")
                print(f"      Alineación bordes: {metrics.get('natural_edge_alignment', 0):.2f}")
            
            # Análisis de fuentes
            font_analysis = overlays.get('font_analysis', {})
            if font_analysis.get('suspicious', False):
                print(f"   ⚠️ Análisis de fuentes sospechoso")
                print(f"   Grupos de fuentes: {font_analysis.get('n_font_groups', 0)}")
            
            # Score de sospecha
            suspicion = analisis.get('suspicion', {})
            print(f"   Score total de sospecha: {suspicion.get('score_0_100', 0)}")
            print(f"   Score de texto superpuesto: {suspicion.get('breakdown', {}).get('text_overlays', 0)}")
            
        else:
            print(f"   ❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Probar imagen sin manipulación
    print("\n2. Probando imagen SIN texto superpuesto...")
    image_bytes = crear_imagen_sin_manipulacion()
    
    files = {'file': ('imagen_original.png', image_bytes, 'image/png')}
    
    try:
        response = requests.post(
            "http://localhost:8001/analizar-imagen-forense",
            files=files,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            analisis = data.get('analisis_forense', {})
            
            print("   ✅ Análisis completado")
            
            # Mostrar detección de texto superpuesto
            overlays = analisis.get('text_overlays', {})
            print(f"   Textos sospechosos detectados: {overlays.get('count', 0)}")
            
            # Score de sospecha
            suspicion = analisis.get('suspicion', {})
            print(f"   Score total de sospecha: {suspicion.get('score_0_100', 0)}")
            print(f"   Score de texto superpuesto: {suspicion.get('breakdown', {}).get('text_overlays', 0)}")
            
        else:
            print(f"   ❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    """Función principal"""
    
    print("🚀 PRUEBA DE DETECCIÓN DE TEXTO SUPERPUESTO")
    print("=" * 70)
    
    probar_deteccion_texto_superpuesto()
    
    print("\n✅ PRUEBA COMPLETADA")
    print("\n💡 Interpretación de resultados:")
    print("   - Textos con score >= 3 son considerados sospechosos")
    print("   - Razones comunes: baja_varianza, bordes_duros, no_alineado_bordes")
    print("   - Score de texto superpuesto se suma al score total de sospecha")

if __name__ == "__main__":
    main()
