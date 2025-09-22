#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para verificar si el servidor está ejecutando el código correcto
"""

import requests
import json
import base64

def verificar_codigo_servidor():
    """Verifica si el servidor está ejecutando el código correcto"""
    
    print("🔍 VERIFICANDO CÓDIGO DEL SERVIDOR")
    print("=" * 50)
    
    # Leer PDF de prueba
    pdf_path = "helpers/IMG/Factura_imagen.pdf"
    
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Convertir a base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        payload = {"pdfbase64": pdf_base64}
        
        print(f"✅ PDF leído: {len(pdf_bytes)} bytes")
        print(f"✅ Base64: {len(pdf_base64)} caracteres")
        
        print("\n🚀 Enviando petición al servidor...")
        
        try:
            response = requests.post(
                "http://localhost:8001/validar-factura",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\n📊 RESPUESTA DEL SERVIDOR:")
                print(f"   Status Code: {response.status_code}")
                print(f"   SRI Verificado: {data.get('sri_verificado', 'N/A')}")
                print(f"   Mensaje: {data.get('mensaje', 'N/A')}")
                
                # Verificar estructura de la respuesta
                print(f"\n📋 ESTRUCTURA DE LA RESPUESTA:")
                print(f"   Claves principales: {list(data.keys())}")
                
                # Verificar si tiene las claves esperadas del endpoint correcto
                claves_esperadas = [
                    'sri_verificado', 'mensaje', 'tipo_archivo', 'coincidencia',
                    'diferencias', 'diferenciasProductos', 'resumenProductos',
                    'factura', 'clave_acceso_parseada', 'riesgo', 'validacion_firmas'
                ]
                
                print(f"\n🔍 VERIFICACIÓN DE CLAVES:")
                for clave in claves_esperadas:
                    if clave in data:
                        print(f"   ✅ {clave}: Presente")
                    else:
                        print(f"   ❌ {clave}: Faltante")
                
                # Verificar si tiene las claves del endpoint incorrecto
                claves_incorrectas = ['prioritarias', 'secundarias', 'adicionales']
                
                print(f"\n🔍 VERIFICACIÓN DE CLAVES INCORRECTAS:")
                for clave in claves_incorrectas:
                    if clave in data:
                        print(f"   ❌ {clave}: Presente (esto indica endpoint incorrecto)")
                    else:
                        print(f"   ✅ {clave}: Faltante (correcto)")
                
                # Verificar sección factura
                if 'factura' in data:
                    print(f"\n✅ SECCIÓN 'FACTURA' PRESENTE")
                    factura = data['factura']
                    if isinstance(factura, dict):
                        print(f"   ✅ Es un diccionario")
                        print(f"   ✅ Claves: {list(factura.keys())}")
                        
                        # Verificar datos específicos
                        ruc = factura.get('ruc', 'N/A')
                        clave_acceso = factura.get('claveAcceso', 'N/A')
                        total = factura.get('total', 'N/A')
                        
                        if ruc != 'N/A' and clave_acceso != 'N/A':
                            print(f"   ✅ Datos extraídos correctamente")
                            print(f"   ✅ RUC: {ruc}")
                            print(f"   ✅ Clave Acceso: {clave_acceso}")
                            print(f"   ✅ Total: {total}")
                        else:
                            print(f"   ❌ Datos no extraídos correctamente")
                            print(f"   ❌ RUC: {ruc}")
                            print(f"   ❌ Clave Acceso: {clave_acceso}")
                            print(f"   ❌ Total: {total}")
                    else:
                        print(f"   ❌ No es un diccionario: {type(factura)}")
                else:
                    print(f"\n❌ SECCIÓN 'FACTURA' FALTANTE")
                    print(f"   Esto indica que el servidor no está usando el código correcto")
                
                # Verificar si tiene sección riesgo con estructura incorrecta
                if 'riesgo' in data:
                    riesgo = data['riesgo']
                    if isinstance(riesgo, dict):
                        if 'prioritarias' in riesgo:
                            print(f"\n❌ ESTRUCTURA DE RIESGO INCORRECTA")
                            print(f"   El servidor está usando una versión antigua del código")
                            print(f"   que devuelve 'prioritarias', 'secundarias', 'adicionales'")
                        else:
                            print(f"\n✅ ESTRUCTURA DE RIESGO CORRECTA")
                            print(f"   El servidor está usando la versión correcta del código")
                
                # Guardar respuesta
                with open("respuesta_verificacion_servidor.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"\n💾 Respuesta guardada en: respuesta_verificacion_servidor.json")
                
            else:
                print(f"❌ Error del servidor: {response.status_code}")
                print(f"   Respuesta: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Error de conexión: El servidor no está ejecutándose")
        except requests.exceptions.Timeout:
            print(f"❌ Timeout: El servidor tardó más de 30 segundos")
        except Exception as e:
            print(f"❌ Error: {e}")
            
    except FileNotFoundError:
        print(f"❌ Archivo PDF no encontrado: {pdf_path}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verificar_codigo_servidor()
