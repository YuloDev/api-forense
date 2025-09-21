#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test del análisis forense avanzado integrado en validar_imagen
"""

import requests
import json
import base64
import os

def test_forensics_avanzado():
    """Test del endpoint validar_imagen con análisis forense avanzado"""
    
    # URL del endpoint
    url = "http://localhost:8001/validar-imagen"
    
    # Buscar una imagen de prueba
    test_images = [
        "helpers/IMG/Factura_imagen.pdf",  # PDF escaneado
        "helpers/IMG/test_image.jpg",      # Imagen de prueba
        "helpers/IMG/sample.png"           # Otra imagen de prueba
    ]
    
    test_image = None
    for img_path in test_images:
        if os.path.exists(img_path):
            test_image = img_path
            break
    
    if not test_image:
        print("❌ No se encontró ninguna imagen de prueba")
        return
    
    print(f"🔍 Probando con imagen: {test_image}")
    print(f"📏 Tamaño del archivo: {os.path.getsize(test_image)} bytes")
    
    try:
        # Leer la imagen y convertir a base64
        with open(test_image, 'rb') as f:
            image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Preparar request
        request_data = {
            "imagen_base64": image_base64,
            "validar_sri": True
        }
        
        print("📤 Enviando request al endpoint...")
        response = requests.post(url, json=request_data, timeout=120)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Verificar si el análisis forense avanzado está presente
            analisis_forense = result.get("analisis_detallado", {})
            forensics_avanzado = analisis_forense.get("forensics_avanzado", {})
            
            print("\n" + "="*60)
            print("📋 ANÁLISIS FORENSE AVANZADO")
            print("="*60)
            
            if forensics_avanzado.get("disponible", False):
                print(f"✅ Análisis forense avanzado: DISPONIBLE")
                print(f"📊 Score total: {forensics_avanzado.get('score_total', 0)}")
                print(f"🎯 Nivel de sospecha: {forensics_avanzado.get('nivel_sospecha', 'N/A')}")
                print(f"🔬 Metodología: {forensics_avanzado.get('metodologia', 'N/A')}")
                
                print("\n📈 MÉTRICAS DETALLADAS:")
                metricas = forensics_avanzado.get("metricas", {})
                for key, value in metricas.items():
                    print(f"  • {key}: {value}")
                
                print("\n🎯 SCORES DETALLADOS:")
                scores = forensics_avanzado.get("scores_detallados", {})
                for key, value in scores.items():
                    print(f"  • {key}: {value}")
                
                print("\n📅 METADATOS:")
                metadatos = forensics_avanzado.get("metadatos", {})
                for key, value in metadatos.items():
                    print(f"  • {key}: {value}")
                
                print("\n🔍 VALIDACIÓN TEMPORAL:")
                validacion_temporal = forensics_avanzado.get("validacion_temporal", {})
                print(f"  • Score: {validacion_temporal.get('score', 0)}")
                print(f"  • Issues: {len(validacion_temporal.get('issues', []))}")
                print(f"  • Warnings: {len(validacion_temporal.get('warnings', []))}")
                
                print("\n🔄 COPY-MOVE ANALYSIS:")
                copy_move = forensics_avanzado.get("copy_move_analysis", {})
                print(f"  • Disponible: {copy_move.get('available', False)}")
                print(f"  • Matches: {copy_move.get('matches', 0)}")
                print(f"  • Score: {copy_move.get('score_0_1', 0)}")
                
                print("\n💡 INTERPRETACIÓN:")
                interpretacion = forensics_avanzado.get("interpretacion", {})
                for key, value in interpretacion.items():
                    print(f"  • {key}: {value}")
                
            else:
                print(f"❌ Análisis forense avanzado: NO DISPONIBLE")
                if "error" in forensics_avanzado:
                    print(f"🚨 Error: {forensics_avanzado['error']}")
            
            # Verificar si aparece en las checks prioritarias
            print("\n" + "="*60)
            print("🎯 CHECKS PRIORITARIAS")
            print("="*60)
            
            riesgo = result.get("riesgo", {})
            prioritarias = riesgo.get("prioritarias", [])
            
            forensics_check = None
            for check in prioritarias:
                if check.get("check") == "Análisis forense avanzado":
                    forensics_check = check
                    break
            
            if forensics_check:
                print("✅ Check 'Análisis forense avanzado' encontrado en prioritarias")
                print(f"📊 Penalización: {forensics_check.get('penalizacion', 0)}")
                print(f"📋 Disponible: {forensics_check.get('detalle', {}).get('disponible', False)}")
                print(f"🎯 Score total: {forensics_check.get('detalle', {}).get('score_total', 0)}")
            else:
                print("❌ Check 'Análisis forense avanzado' NO encontrado en prioritarias")
            
            # Mostrar resumen de todas las checks prioritarias
            print(f"\n📋 Total de checks prioritarias: {len(prioritarias)}")
            for i, check in enumerate(prioritarias, 1):
                print(f"  {i}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
            
            print("\n" + "="*60)
            print("✅ TEST COMPLETADO")
            print("="*60)
            
        else:
            print(f"❌ Error en la respuesta del endpoint. Status Code: {response.status_code}")
            print("Respuesta completa:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión. ¿Está ejecutándose el servidor?")
    except requests.exceptions.Timeout:
        print("❌ Error de tiempo de espera. El servidor tardó demasiado en responder.")
    except json.JSONDecodeError:
        print("❌ Error al decodificar la respuesta JSON.")
        print("Respuesta recibida:")
        print(response.text)
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    test_forensics_avanzado()

