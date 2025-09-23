#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar el endpoint de análisis forense de imágenes
"""

import requests
import json
import os
from PIL import Image
import io

def crear_imagen_prueba():
    """Crea una imagen de prueba simple"""
    # Crear una imagen simple con texto
    img = Image.new('RGB', (400, 200), color='white')
    
    # Agregar texto usando PIL
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)
    
    try:
        # Intentar usar una fuente del sistema
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Agregar texto de prueba
    draw.text((20, 50), "FACTURA DE PRUEBA", fill='black', font=font)
    draw.text((20, 80), "RUC: 1234567890123", fill='black', font=font)
    draw.text((20, 110), "TOTAL: $100.00", fill='black', font=font)
    draw.text((20, 140), "FECHA: 2024-01-15", fill='black', font=font)
    
    # Guardar en memoria
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes.getvalue()

def probar_endpoint_forense():
    """Prueba el endpoint de análisis forense"""
    
    print("🔍 PROBANDO ENDPOINT DE ANÁLISIS FORENSE")
    print("=" * 60)
    
    # Crear imagen de prueba
    print("1. Creando imagen de prueba...")
    image_bytes = crear_imagen_prueba()
    print(f"   ✅ Imagen creada: {len(image_bytes)} bytes")
    
    # Preparar petición
    print("\n2. Preparando petición...")
    files = {
        'file': ('imagen_prueba.png', image_bytes, 'image/png')
    }
    
    try:
        print("3. Enviando petición al servidor...")
        response = requests.post(
            "http://localhost:8001/analizar-imagen-forense",
            files=files,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📊 RESULTADO DEL ANÁLISIS FORENSE:")
            print(f"   ✅ Éxito: {data.get('success', False)}")
            print(f"   📁 Archivo: {data.get('filename', 'N/A')}")
            print(f"   📏 Tamaño: {data.get('file_size', 0)} bytes")
            
            # Mostrar análisis forense
            analisis = data.get('analisis_forense', {})
            
            print(f"\n🔍 ANÁLISIS FORENSE DETALLADO:")
            print(f"   Tipo: {analisis.get('type', 'N/A')}")
            print(f"   Formato: {analisis.get('format', 'N/A')}")
            
            # Metadatos
            meta = analisis.get('meta', {})
            print(f"\n📋 METADATOS:")
            print(f"   EXIF presente: {meta.get('exif_present', False)}")
            print(f"   Software EXIF: {meta.get('exif_software', 'N/A')}")
            print(f"   XMP presente: {meta.get('xmp_present', False)}")
            
            # ELA
            ela = analisis.get('ela', {})
            print(f"\n🔬 ANÁLISIS ELA:")
            print(f"   Media: {ela.get('mean', 0):.2f}")
            print(f"   Desviación: {ela.get('std', 0):.2f}")
            print(f"   Percentil 95: {ela.get('p95', 0):.2f}")
            print(f"   Ratio suave/borde: {ela.get('smooth_edge_ratio', 0):.2f}")
            print(f"   Tasa de outliers: {ela.get('outlier_rate', 0):.2f}")
            print(f"   Pendiente calidad: {ela.get('quality_slope', 0):.2f}")
            
            # Copy-Move mejorado
            cm = analisis.get('copy_move', {})
            print(f"\n🔄 DETECCIÓN COPY-MOVE MEJORADA:")
            print(f"   Disponible: {cm.get('available', False)}")
            print(f"   Coincidencias totales: {cm.get('total_matches', 0)}")
            print(f"   Score combinado: {cm.get('combined_score', 0):.2f}")
            
            methods = cm.get('methods', {})
            if 'orb' in methods:
                orb = methods['orb']
                print(f"   ORB - Coincidencias: {orb.get('matches', 0)}")
            if 'sift' in methods:
                sift = methods['sift']
                print(f"   SIFT - Coincidencias: {sift.get('matches', 0)}")
            if 'patch_correlation' in methods:
                patch = methods['patch_correlation']
                print(f"   Patches - Correlaciones altas: {patch.get('high_correlation_pairs', 0)}")
            
            # Texto superpuesto
            overlays = analisis.get('text_overlays', {})
            print(f"\n📝 DETECCIÓN DE TEXTO SUPERPUESTO:")
            print(f"   Disponible: {overlays.get('available', False)}")
            print(f"   Textos sospechosos: {overlays.get('count', 0)}")
            print(f"   Regiones de texto totales: {overlays.get('total_text_regions', 0)}")
            
            font_analysis = overlays.get('font_analysis', {})
            if font_analysis.get('suspicious', False):
                print(f"   ⚠️ Análisis de fuentes sospechoso")
                print(f"   Grupos de fuentes: {font_analysis.get('n_font_groups', 0)}")
                print(f"   Razones: {', '.join(font_analysis.get('reasons', []))}")
            
            # Detecciones específicas
            detections = overlays.get('detections', [])
            for i, det in enumerate(detections[:3]):  # Mostrar solo las primeras 3
                print(f"   {i+1}. '{det.get('text', '')}' - Score: {det.get('suspicious_score', 0)}")
                print(f"      Razones: {', '.join(det.get('reasons', []))}")
            
            # Capas PDF
            pdf_layers = analisis.get('pdf_layers', {})
            print(f"\n📄 DETECCIÓN DE CAPAS PDF:")
            print(f"   Disponible: {pdf_layers.get('available', False)}")
            print(f"   Patrones PDF encontrados: {len(pdf_layers.get('pdf_patterns_found', []))}")
            print(f"   Streams: {pdf_layers.get('stream_count', 0)}")
            print(f"   Sospechoso: {pdf_layers.get('suspicious', False)}")
            if pdf_layers.get('pdf_patterns_found'):
                print(f"   Patrones: {', '.join(pdf_layers.get('pdf_patterns_found', []))}")
            
            # OCR
            ocr = analisis.get('ocr_rules', {})
            print(f"\n📝 ANÁLISIS OCR:")
            print(f"   Disponible: {ocr.get('available', False)}")
            print(f"   Texto extraído: {ocr.get('text_excerpt', '')[:100]}...")
            
            # Suspicion
            suspicion = analisis.get('suspicion', {})
            print(f"\n⚠️ NIVEL DE SOSPECHA:")
            print(f"   Score (0-100): {suspicion.get('score_0_100', 0)}")
            print(f"   Etiqueta: {suspicion.get('label', 'N/A')}")
            print(f"   Certeza falsificación: {suspicion.get('certeza_falsificacion_pct', 0)}%")
            
            # Breakdown
            breakdown = suspicion.get('breakdown', {})
            print(f"\n📊 DESGLOSE DE PUNTUACIÓN:")
            breakdown_labels = {
                "ela_ratio": "ELA - Ratio suave/borde",
                "outliers": "ELA - Outliers",
                "ela_intensity": "ELA - Intensidad",
                "quality_slope": "ELA - Pendiente calidad",
                "copy_move": "Copy-Move",
                "text_overlays": "Texto superpuesto",
                "pdf_layers": "Capas PDF",
                "ocr_inconsistency": "OCR - Inconsistencias",
                "editor_software": "Software de edición",
                "date_validation": "Validación temporal"
            }
            
            for key, value in breakdown.items():
                label = breakdown_labels.get(key, key)
                print(f"   {label}: {value}")
            
            # Conclusión
            print(f"\n🎯 CONCLUSIÓN:")
            print(f"   {analisis.get('conclusion', 'N/A')}")
            
            # Guardar resultado completo
            with open("resultado_analisis_forense.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Resultado completo guardado en: resultado_analisis_forense.json")
            
            print(f"\n✅ ANÁLISIS FORENSE COMPLETADO EXITOSAMENTE")
            
        else:
            print(f"❌ Error del servidor: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Error de conexión: El servidor no está ejecutándose")
        print(f"   Inicia el servidor con: python start_server.py")
    except requests.exceptions.Timeout:
        print(f"❌ Timeout: El servidor tardó más de 60 segundos")
    except Exception as e:
        print(f"❌ Error: {e}")

def probar_info_endpoint():
    """Prueba el endpoint de información"""
    
    print("\n🔍 PROBANDO ENDPOINT DE INFORMACIÓN")
    print("=" * 60)
    
    try:
        response = requests.get("http://localhost:8001/analisis-forense-info", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Endpoint de información funcionando")
            print(f"   Endpoint: {data.get('endpoint', 'N/A')}")
            print(f"   Método: {data.get('metodo', 'N/A')}")
            print(f"   Análisis incluidos: {len(data.get('analisis_incluidos', []))}")
            print(f"   Formatos soportados: {data.get('formatos_soportados', [])}")
            print(f"   Dependencias: {data.get('dependencias', {})}")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Función principal"""
    
    print("🚀 PRUEBA COMPLETA DEL ENDPOINT DE ANÁLISIS FORENSE")
    print("=" * 70)
    
    # Probar endpoint de información
    probar_info_endpoint()
    
    # Probar endpoint principal
    probar_endpoint_forense()
    
    print("\n✅ PRUEBA COMPLETADA")

if __name__ == "__main__":
    main()
