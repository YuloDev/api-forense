#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Probar el endpoint /validar-imagen con el nuevo detector de texto sobrepuesto
"""

import requests
import json
import base64
import os
import fitz

def test_validar_imagen_con_overlays():
    """Probar el endpoint validar-imagen con overlays"""
    print("🔍 PROBANDO /validar-imagen CON DETECTOR DE OVERLAYS")
    print("=" * 60)
    
    # Usar la factura PDF
    pdf_path = r"C:\Users\Nexti\sources\api-forense\helpers\IMG\Factura_imagen.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Archivo no encontrado: {pdf_path}")
        return
    
    # Convertir PDF a imagen
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)  # Zoom 2x
        pix = page.get_pixmap(matrix=mat, alpha=False)
        imagen_bytes = pix.tobytes("jpeg")
        doc.close()
        print(f"✅ PDF convertido a imagen: {len(imagen_bytes)} bytes")
    except Exception as e:
        print(f"❌ Error convirtiendo PDF: {e}")
        return
    
    # Convertir a base64
    imagen_base64 = base64.b64encode(imagen_bytes).decode('utf-8')
    
    # Preparar petición
    url = "http://localhost:8001/validar-imagen"
    payload = {"imagenbase64": imagen_base64}
    
    print(f"🔗 URL: {url}")
    print(f"📦 Payload size: {len(json.dumps(payload))} caracteres")
    
    try:
        print(f"\n🚀 Enviando petición...")
        response = requests.post(url, json=payload, timeout=60)
        
        print(f"✅ Respuesta recibida")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Verificar si tiene análisis forense profesional
            analisis_forense = data.get("analisis_forense_profesional", {})
            
            if analisis_forense:
                print(f"\n📊 ANÁLISIS FORENSE PROFESIONAL:")
                print(f"   Grado confianza: {analisis_forense.get('grado_confianza', 'N/A')}")
                print(f"   Porcentaje: {analisis_forense.get('porcentaje_confianza', 0.0):.1f}%")
                print(f"   Evidencias: {len(analisis_forense.get('evidencias', []))}")
                
                # Mostrar evidencias
                evidencias = analisis_forense.get('evidencias', [])
                if evidencias:
                    print(f"\n🔍 EVIDENCIAS DETECTADAS:")
                    for evidencia in evidencias:
                        print(f"   - {evidencia}")
                
                # Verificar si tiene overlays
                overlays = analisis_forense.get('overlays', {})
                if overlays:
                    resumen = overlays.get('resumen', {})
                    print(f"\n🔎 DETECTOR DE TEXTO SOBREPUESTO:")
                    print(f"   Palabras detectadas: {resumen.get('n_palabras', 0)}")
                    print(f"   Overlays detectados: {resumen.get('n_overlays', 0)}")
                    print(f"   Score máximo: {resumen.get('max_score', 0.0):.3f}")
                    print(f"   Score promedio overlays: {resumen.get('mean_score_overlay', 0.0):.3f}")
                    
                    # Mostrar overlays específicos
                    items = overlays.get('items', [])
                    overlays_items = [item for item in items if item.get('overlay', False)]
                    
                    if overlays_items:
                        print(f"\n🚨 OVERLAYS DETECTADOS:")
                        for i, overlay in enumerate(overlays_items[:10]):  # Mostrar hasta 10
                            print(f"   {i+1}. '{overlay['text']}' - Score: {overlay['score']:.3f}")
                            print(f"      Bbox: {overlay['bbox']}")
                            print(f"      Features: ELA={overlay['features']['ela_mean']:.3f}, "
                                  f"Contrast={overlay['features']['contrast']:.3f}, "
                                  f"Halo={overlay['features']['edge_halo']:.3f}")
                    else:
                        print(f"   ✅ No se detectaron overlays específicos")
                    
                    # Verificar si hay imagen anotada
                    if overlays.get('annotated_image_b64'):
                        print(f"   📷 Imagen anotada disponible (base64)")
                    else:
                        print(f"   ❌ No hay imagen anotada")
                else:
                    print(f"\n❌ No se encontraron datos de overlays en la respuesta")
                
                # Verificar otros análisis
                print(f"\n📋 OTROS ANÁLISIS:")
                print(f"   Metadatos: {'✅' if analisis_forense.get('metadatos') else '❌'}")
                print(f"   Compresión: {'✅' if analisis_forense.get('compresion') else '❌'}")
                print(f"   Cuadrícula JPEG: {'✅' if analisis_forense.get('cuadricula_jpeg') else '❌'}")
                print(f"   Texto sintético: {'✅' if analisis_forense.get('texto_sintetico') else '❌'}")
                print(f"   ELA: {'✅' if analisis_forense.get('ela') else '❌'}")
                print(f"   Ruido/bordes: {'✅' if analisis_forense.get('ruido_bordes') else '❌'}")
                print(f"   Hashes: {'✅' if analisis_forense.get('hashes') else '❌'}")
                
            else:
                print(f"\n❌ No se encontró análisis forense profesional en la respuesta")
            
            # Guardar respuesta completa
            with open('test_validar_imagen_overlays_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Respuesta completa guardada en: test_validar_imagen_overlays_response.json")
            
        else:
            print(f"❌ Error del servidor: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Error de conexión: El servidor no está ejecutándose")
        print(f"   Asegúrate de que el servidor esté ejecutándose en el puerto 8001")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    test_validar_imagen_con_overlays()
