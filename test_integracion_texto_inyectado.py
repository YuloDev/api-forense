#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de integración del detector de texto inyectado en el check de texto sintético aplanado
"""

import requests
import json
import os
import base64

def test_integracion_texto_inyectado():
    """Test de integración del detector de texto inyectado"""
    print("🔗 TEST INTEGRACIÓN TEXTO INYECTADO")
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
                
                texto_sintetico_encontrado = False
                for i, check in enumerate(prioritarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
                    
                    if check.get('check') == "Texto sintético aplanado":
                        texto_sintetico_encontrado = True
                        detalle = check.get('detalle', {})
                        print(f"      ✅ TEXTO SINTÉTICO APLANADO ENCONTRADO")
                        print(f"      Detectado: {detalle.get('detectado', 'N/A')}")
                        print(f"      Nivel sospecha: {detalle.get('nivel_sospecha', 'N/A')}")
                        print(f"      Vía detección: {detalle.get('via_deteccion', 'N/A')}")
                        print(f"      Cajas texto detectadas: {detalle.get('cajas_texto_detectadas', 'N/A')}")
                        print(f"      Método detección: {detalle.get('metodo_deteccion', 'N/A')}")
                        print(f"      Coincide con montos/fechas: {detalle.get('coincide_con_montos_fechas', 'N/A')}")
                        
                        # Verificar información del texto inyectado
                        analisis_detallado = detalle.get('analisis_detallado', {})
                        texto_inyectado = analisis_detallado.get('texto_inyectado')
                        
                        if texto_inyectado:
                            print(f"      🔍 INFORMACIÓN TEXTO INYECTADO:")
                            print(f"         Match: {texto_inyectado.get('match', 'N/A')}")
                            print(f"         Nivel: {texto_inyectado.get('nivel', 'N/A')}")
                            print(f"         Score: {texto_inyectado.get('score', 'N/A')}")
                            print(f"         Sospechosos: {len(texto_inyectado.get('sospechosos', []))}")
                            
                            # Mostrar tokens sospechosos
                            sospechosos = texto_inyectado.get('sospechosos', [])
                            if sospechosos:
                                print(f"         Tokens sospechosos:")
                                for j, sospechoso in enumerate(sospechosos[:3]):  # Mostrar solo los primeros 3
                                    print(f"           {j+1}. Texto: '{sospechoso.get('texto', 'N/A')}' (conf: {sospechoso.get('conf', 'N/A')})")
                                    print(f"              Bbox: {sospechoso.get('bbox', 'N/A')}, Score: {sospechoso.get('score', 'N/A')}")
                                    print(f"              Razones: {sospechoso.get('reasons', [])}")
                        else:
                            print(f"      ℹ️  No hay información de texto inyectado")
                        
                        # Mostrar indicadores clave
                        indicadores = detalle.get('indicadores_clave', [])
                        if indicadores:
                            print(f"      Indicadores clave:")
                            for indicador in indicadores:
                                print(f"        - {indicador}")
                
                if not texto_sintetico_encontrado:
                    print(f"\nℹ️  TEXTO SINTÉTICO APLANADO NO ENCONTRADO EN PRIORITARIAS")
                    print(f"   Esto indica que la imagen no tiene texto sintético aplanado")
                
                # Verificar que no hay check separado de "Texto inyectado"
                texto_inyectado_separado = False
                for check in prioritarias:
                    if "inyectado" in check.get('check', '').lower():
                        texto_inyectado_separado = True
                        print(f"      ⚠️  CHECK SEPARADO DE TEXTO INYECTADO ENCONTRADO: {check.get('check')}")
                
                if not texto_inyectado_separado:
                    print(f"\n✅ NO HAY CHECK SEPARADO DE TEXTO INYECTADO")
                    print(f"   La integración es correcta - solo existe el check unificado de 'Texto sintético aplanado'")
            
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
    test_integracion_texto_inyectado()
