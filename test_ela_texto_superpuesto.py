#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test del análisis ELA focalizado con detector de texto superpuesto integrado
"""

import requests
import json
import os
import base64

def test_ela_texto_superpuesto():
    """Test del análisis ELA con detector de texto superpuesto"""
    print("🔍 TEST ELA FOCALIZADO + TEXTO SUPERPUESTO")
    print("=" * 60)
    
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
            
            # Verificar prioritarias y secundarias
            if 'riesgo' in result:
                riesgo = result['riesgo']
                prioritarias = riesgo.get('prioritarias', [])
                secundarias = riesgo.get('secundarias', [])
                
                print(f"\n🔍 PRIORITARIAS ({len(prioritarias)}):")
                
                ela_encontrado = False
                for i, check in enumerate(prioritarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
                    
                    if "ELA" in check.get('check', ''):
                        ela_encontrado = True
                        detalle = check.get('detalle', {})
                        print(f"      ✅ ELA FOCALIZADO ENCONTRADO")
                        print(f"      Detectado: {detalle.get('detectado', 'N/A')}")
                        print(f"      Nivel sospecha: {detalle.get('nivel_sospecha', 'N/A')}")
                        print(f"      Marca editada: {detalle.get('marca_editada', 'N/A')}")
                        print(f"      Interpretación: {detalle.get('interpretacion', 'N/A')}")
                        print(f"      Recomendación: {detalle.get('recomendacion', 'N/A')}")
                        
                        # Verificar información del texto superpuesto
                        analisis_detallado = detalle.get('analisis_detallado', {})
                        texto_superpuesto = analisis_detallado.get('texto_superpuesto')
                        
                        if texto_superpuesto:
                            print(f"      🔍 INFORMACIÓN TEXTO SUPERPUESTO:")
                            print(f"         Match: {texto_superpuesto.get('match', 'N/A')}")
                            print(f"         Localized: {texto_superpuesto.get('localized', 'N/A')}")
                            print(f"         Número de sospechosos: {texto_superpuesto.get('num_sospechosos', 'N/A')}")
                            
                            # Mostrar sospechosos
                            sospechosos = texto_superpuesto.get('sospechosos', [])
                            if sospechosos:
                                print(f"         Sospechosos detectados:")
                                for j, sospechoso in enumerate(sospechosos[:3]):  # Mostrar solo los primeros 3
                                    print(f"           {j+1}. Bbox: {sospechoso.get('bbox', 'N/A')}")
                                    print(f"              Score: {sospechoso.get('score', 'N/A')}")
                                    print(f"              Tipo: {sospechoso.get('tipo', 'N/A')}")
                                    
                                    # Mostrar métricas
                                    metricas = sospechoso.get('metricas', {})
                                    if metricas:
                                        print(f"              Métricas:")
                                        print(f"                - SW_CV: {metricas.get('sw_cv', 'N/A'):.3f}")
                                        print(f"                - Halo: {metricas.get('halo', 'N/A'):.3f}")
                                        print(f"                - ELA boost: {metricas.get('ela_boost', 'N/A'):.3f}")
                                        print(f"                - Z_HF: {metricas.get('z_hf', 'N/A'):.3f}")
                                        print(f"                - Edge coherence: {metricas.get('edge_coherence', 'N/A'):.3f}")
                                        print(f"                - Entropy: {metricas.get('entropy', 'N/A'):.3f}")
                                        print(f"                - Dominant bins: {metricas.get('dominant_bins', 'N/A')}")
                                        print(f"                - Colorish: {metricas.get('colorish', 'N/A')}")
                                        print(f"                - Is numeric: {metricas.get('is_numeric', 'N/A')}")
                        else:
                            print(f"      ℹ️  No hay información de texto superpuesto")
                        
                        # Mostrar indicadores clave
                        indicadores = detalle.get('indicadores_clave', [])
                        if indicadores:
                            print(f"      Indicadores clave:")
                            for indicador in indicadores:
                                print(f"        - {indicador}")
                
                if not ela_encontrado:
                    print(f"\n🔍 SECUNDARIAS ({len(secundarias)}):")
                    for i, check in enumerate(secundarias):
                        print(f"   {i+1}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
                        if "ELA" in check.get('check', ''):
                            print(f"      ✅ ELA FOCALIZADO ENCONTRADO EN SECUNDARIAS")
                            detalle = check.get('detalle', {})
                            print(f"      Detectado: {detalle.get('detectado', 'N/A')}")
                            print(f"      Nivel sospecha: {detalle.get('nivel_sospecha', 'N/A')}")
                
                if not any("ELA" in check.get('check', '') for check in prioritarias + secundarias):
                    print(f"\nℹ️  ELA FOCALIZADO NO ENCONTRADO")
                    print(f"   Esto indica que la imagen no tiene evidencia de edición local")
            
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
    test_ela_texto_superpuesto()
