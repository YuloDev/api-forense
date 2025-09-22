#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Probar el nuevo detector de texto sobrepuesto
"""

import base64
import os
import json
from helpers.analisis_forense_profesional import detectar_texto_sobrepuesto, analisis_forense_completo

def test_detector_texto_sobrepuesto():
    """Probar el detector de texto sobrepuesto"""
    print("🔍 PROBANDO DETECTOR DE TEXTO SOBREPUESTO")
    print("=" * 50)
    
    # Usar la imagen de la factura
    pdf_path = r"C:\Users\Nexti\sources\api-forense\helpers\IMG\Factura_imagen.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Archivo no encontrado: {pdf_path}")
        return
    
    # Convertir PDF a imagen para prueba
    try:
        import fitz
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
    
    # Probar detector directo
    print(f"\n🔍 Probando detector directo...")
    try:
        resultado = detectar_texto_sobrepuesto(imagen_bytes)
        
        print(f"✅ Detector ejecutado correctamente")
        print(f"   Palabras detectadas: {resultado.get('resumen', {}).get('n_palabras', 0)}")
        print(f"   Overlays detectados: {resultado.get('resumen', {}).get('n_overlays', 0)}")
        print(f"   Score máximo: {resultado.get('resumen', {}).get('max_score', 0.0)}")
        
        # Mostrar algunos overlays si los hay
        items = resultado.get('items', [])
        overlays = [item for item in items if item.get('overlay', False)]
        
        if overlays:
            print(f"\n🚨 OVERLAYS DETECTADOS:")
            for i, overlay in enumerate(overlays[:5]):  # Mostrar solo los primeros 5
                print(f"   {i+1}. '{overlay['text']}' - Score: {overlay['score']:.3f}")
                print(f"      Bbox: {overlay['bbox']}")
                print(f"      Features: ELA={overlay['features']['ela_mean']:.3f}, "
                      f"Contrast={overlay['features']['contrast']:.3f}, "
                      f"Halo={overlay['features']['edge_halo']:.3f}")
        else:
            print(f"✅ No se detectaron overlays")
        
        # Guardar resultado completo
        with open('test_texto_sobrepuesto_resultado.json', 'w', encoding='utf-8') as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Resultado guardado en: test_texto_sobrepuesto_resultado.json")
        
    except Exception as e:
        print(f"❌ Error en detector directo: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
    
    # Probar integración en análisis completo
    print(f"\n🔍 Probando integración en análisis completo...")
    try:
        resultado_completo = analisis_forense_completo(imagen_bytes)
        
        print(f"✅ Análisis completo ejecutado")
        print(f"   Evidencias: {len(resultado_completo.get('evidencias', []))}")
        print(f"   Grado confianza: {resultado_completo.get('grado_confianza', 'N/A')}")
        print(f"   Porcentaje: {resultado_completo.get('porcentaje_confianza', 0.0):.1f}%")
        
        # Mostrar evidencias relacionadas con overlays
        evidencias = resultado_completo.get('evidencias', [])
        overlays_evidencias = [ev for ev in evidencias if 'sobrepuesto' in ev.lower()]
        
        if overlays_evidencias:
            print(f"\n🚨 EVIDENCIAS DE OVERLAYS:")
            for evidencia in overlays_evidencias:
                print(f"   - {evidencia}")
        else:
            print(f"✅ No hay evidencias de overlays en el análisis completo")
        
        # Mostrar resumen de overlays
        overlays_data = resultado_completo.get('overlays', {})
        if overlays_data:
            resumen = overlays_data.get('resumen', {})
            print(f"\n📊 RESUMEN DE OVERLAYS:")
            print(f"   Palabras totales: {resumen.get('n_palabras', 0)}")
            print(f"   Overlays detectados: {resumen.get('n_overlays', 0)}")
            print(f"   Score máximo: {resumen.get('max_score', 0.0):.3f}")
            print(f"   Score promedio overlays: {resumen.get('mean_score_overlay', 0.0):.3f}")
        
        # Guardar resultado completo
        with open('test_analisis_completo_con_overlays.json', 'w', encoding='utf-8') as f:
            json.dump(resultado_completo, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Análisis completo guardado en: test_analisis_completo_con_overlays.json")
        
    except Exception as e:
        print(f"❌ Error en análisis completo: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_detector_texto_sobrepuesto()
