#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test del análisis de texto inyectado
"""

import requests
import json
import os
import base64

def test_texto_inyectado():
    """Test del análisis de texto inyectado"""
    print("🔬 TEST ANÁLISIS DE TEXTO INYECTADO")
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
            
            # Verificar prioritarias
            if 'riesgo' in result:
                riesgo = result['riesgo']
                prioritarias = riesgo.get('prioritarias', [])
                
                print(f"\n🔍 PRIORITARIAS ({len(prioritarias)}):")
                
                texto_inyectado_encontrado = False
                for i, check in enumerate(prioritarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
                    
                    if check.get('check') == "Texto inyectado (números añadidos)":
                        texto_inyectado_encontrado = True
                        detalle = check.get('detalle', {})
                        print(f"      ✅ TEXTO INYECTADO ENCONTRADO EN PRIORITARIAS")
                        print(f"      Detectado: {detalle.get('detectado', 'N/A')}")
                        print(f"      Nivel: {detalle.get('nivel', 'N/A')}")
                        print(f"      Score parcial: {detalle.get('score_parcial', 'N/A')}")
                        print(f"      Número de sospechosos: {detalle.get('num_sospechosos', 'N/A')}")
                        print(f"      Interpretación: {detalle.get('interpretacion', 'N/A')}")
                        print(f"      Recomendación: {detalle.get('recomendacion', 'N/A')}")
                        
                        # Mostrar criterios
                        criterios = detalle.get('criterios', {})
                        if criterios:
                            print(f"      Criterios:")
                            for criterio, descripcion in criterios.items():
                                print(f"        - {criterio}: {descripcion}")
                        
                        # Mostrar sospechosos
                        sospechosos = detalle.get('sospechosos', [])
                        if sospechosos:
                            print(f"      Tokens sospechosos:")
                            for j, sospechoso in enumerate(sospechosos[:5]):  # Mostrar solo los primeros 5
                                print(f"        {j+1}. Texto: '{sospechoso.get('texto', 'N/A')}' (conf: {sospechoso.get('conf', 'N/A')})")
                                print(f"           Bbox: {sospechoso.get('bbox', 'N/A')}, Score: {sospechoso.get('score', 'N/A')}")
                                print(f"           Razones: {sospechoso.get('reasons', [])}")
                                
                                # Mostrar métricas del sospechoso
                                metrics = sospechoso.get('metrics', {})
                                if metrics:
                                    print(f"           Métricas:")
                                    print(f"             - W_mean: {metrics.get('w_mean', 'N/A'):.2f}")
                                    print(f"             - W_cv: {metrics.get('w_cv', 'N/A'):.3f}")
                                    print(f"             - ELA_ratio: {metrics.get('ela_ratio', 'N/A'):.2f}")
                                    print(f"             - ELA_roi: {metrics.get('ela_roi', 'N/A'):.3f}")
                                    print(f"             - Entropía: {metrics.get('entropia', 'N/A'):.2f}")
                                    print(f"             - Grad_ratio: {metrics.get('grad_ratio', 'N/A'):.3f}")
                        else:
                            print(f"      No hay tokens sospechosos específicos")
                
                if not texto_inyectado_encontrado:
                    print(f"\nℹ️  TEXTO INYECTADO NO ENCONTRADO EN PRIORITARIAS")
                    print(f"   Esto indica que la imagen no tiene números inyectados sospechosos")
                
                # Verificar secundarias
                secundarias = riesgo.get('secundarias', [])
                print(f"\n🔍 SECUNDARIAS ({len(secundarias)}):")
                
                for i, check in enumerate(secundarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
            
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
    test_texto_inyectado()
