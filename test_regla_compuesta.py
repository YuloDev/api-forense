#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de la regla compuesta: Texto sintético aplanado + Ruido/Bordes
"""

import requests
import json
import os
import base64

def test_regla_compuesta():
    """Test de la regla compuesta"""
    print("🔬 TEST REGLA COMPUESTA: TEXTO SINTÉTICO + RUIDO/BORDES")
    print("=" * 70)
    
    # URL del endpoint
    url = "http://localhost:8000/validar-imagen"
    
    # Imagen de prueba
    img_path = "helpers/IMG/Captura de pantalla 2025-09-19 120741.png"
    
    if not os.path.exists(img_path):
        print(f"❌ No se encontró la imagen: {img_path}")
        return
    
    print(f"📸 Procesando imagen: {img_path}")
    
    # Leer imagen y convertir a base64
    with open(img_path, 'rb') as f:
        img_bytes = f.read()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    
    # Datos de la petición
    data = {
        "imagen_base64": img_base64
    }
    
    try:
        # Hacer petición
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Respuesta exitosa!")
            
            # Verificar prioritarias
            if 'riesgo' in result:
                riesgo = result['riesgo']
                prioritarias = riesgo.get('prioritarias', [])
                
                print(f"\n🔍 PRIORITARIAS ({len(prioritarias)}):")
                
                regla_compuesta_encontrada = False
                for i, check in enumerate(prioritarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
                    
                    if check.get('check') == "Texto sintético aplanado + Ruido/Bordes":
                        regla_compuesta_encontrada = True
                        detalle = check.get('detalle', {})
                        print(f"      ✅ REGLA COMPUESTA ENCONTRADA EN PRIORITARIAS")
                        print(f"      Nivel: {detalle.get('nivel', 'N/A')}")
                        print(f"      Score parcial: {detalle.get('score_parcial', 'N/A')}")
                        print(f"      Razones: {detalle.get('razones', [])}")
                        print(f"      Interpretación: {detalle.get('interpretacion', 'N/A')}")
                        print(f"      Recomendación: {detalle.get('recomendacion', 'N/A')}")
                        
                        # Mostrar métricas
                        metricas = detalle.get('metricas', {})
                        if metricas:
                            print(f"      Métricas:")
                            print(f"        - Cajas de texto: {metricas.get('n_cajas', 'N/A')}")
                            print(f"        - CV grosor: {metricas.get('sw_cv', 'N/A')}")
                            print(f"        - Halo ratio: {metricas.get('halo_ratio', 'N/A')}")
                            print(f"        - Outlier ratio: {metricas.get('outlier_ratio', 'N/A')}")
                            print(f"        - Es localizado: {metricas.get('es_localizado', 'N/A')}")
                
                if not regla_compuesta_encontrada:
                    print(f"\n⚠️  REGLA COMPUESTA NO ENCONTRADA EN PRIORITARIAS")
                    print(f"   Esto puede ser normal si no se cumplen los criterios combinados")
                
                # Verificar secundarias
                secundarias = riesgo.get('secundarias', [])
                print(f"\n🔍 SECUNDARIAS ({len(secundarias)}):")
                
                indicadores_combinados = False
                for i, check in enumerate(secundarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
                    
                    if check.get('check') == "Indicadores combinados (no concluyente)":
                        indicadores_combinados = True
                        detalle = check.get('detalle', {})
                        print(f"      ⚠️  INDICADORES COMBINADOS ENCONTRADOS EN SECUNDARIAS")
                        print(f"      Nivel: {detalle.get('nivel', 'N/A')}")
                        print(f"      Score parcial: {detalle.get('score_parcial', 'N/A')}")
                        print(f"      Razones: {detalle.get('razones', [])}")
                
                if not indicadores_combinados and not regla_compuesta_encontrada:
                    print(f"\nℹ️  No se detectaron indicadores combinados significativos")
                    print(f"   Esto indica que la imagen no muestra patrones de edición con herramientas básicas")
            
        else:
            print(f"❌ Error en la respuesta: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión. ¿Está ejecutándose el servidor?")
        print("Ejecuta: python main.py")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_regla_compuesta()
