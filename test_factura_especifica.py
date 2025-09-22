#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar el endpoint con el archivo específico
"""

import requests
import json
import base64
import time

def test_factura_especifica():
    """Prueba el endpoint con el archivo específico"""
    
    print("🔍 PROBANDO VALIDAR-FACTURA CON ARCHIVO ESPECÍFICO")
    print("=" * 60)
    
    # Leer PDF específico
    pdf_path = r"C:\Users\Nexti\sources\api-forense\helpers\IMG\Factura_imagen.pdf"
    
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        print(f"✅ PDF leído: {len(pdf_bytes)} bytes")
        print(f"✅ Ruta: {pdf_path}")
        
        # Convertir a base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        print(f"✅ Base64: {len(pdf_base64)} caracteres")
        
        # Preparar petición
        payload = {"pdfbase64": pdf_base64}
        
        print(f"\n🚀 Enviando petición a: http://localhost:8001/validar-factura")
        print(f"   Payload size: {len(str(payload))} caracteres")
        
        start_time = time.time()
        
        try:
            response = requests.post(
                "http://localhost:8001/validar-factura",
                json=payload,
                timeout=60
            )
            
            end_time = time.time()
            print(f"✅ Respuesta recibida en {end_time - start_time:.2f} segundos")
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\n📊 RESULTADO DEL SERVIDOR:")
                print(f"   SRI Verificado: {data.get('sri_verificado', 'N/A')}")
                print(f"   Mensaje: {data.get('mensaje', 'N/A')}")
                print(f"   Tipo Archivo: {data.get('tipo_archivo', 'N/A')}")
                
                # Verificar si se extrajeron datos
                factura = data.get('factura', {})
                print(f"\n📋 DATOS EXTRAÍDOS:")
                print(f"   RUC: {factura.get('ruc', 'N/A')}")
                print(f"   Razón Social: {factura.get('razonSocial', 'N/A')}")
                print(f"   Fecha Emisión: {factura.get('fechaEmision', 'N/A')}")
                print(f"   Importe Total: {factura.get('total', 'N/A')}")
                print(f"   Clave Acceso: {factura.get('claveAcceso', 'N/A')}")
                
                # Verificar si el OCR está funcionando
                if factura.get('ruc') and factura.get('ruc') != 'N/A':
                    print(f"\n✅ SERVIDOR FUNCIONANDO CORRECTAMENTE")
                    print(f"   OCR: ✅ Funcionando")
                    print(f"   Extracción de datos: ✅ Funcionando")
                    print(f"   Validación SRI: ✅ Funcionando")
                else:
                    print(f"\n❌ SERVIDOR NO ESTÁ EXTRAYENDO DATOS")
                    print(f"   OCR: ❌ No funcionando")
                    print(f"   Extracción de datos: ❌ No funcionando")
                    
                    # Verificar el mensaje de error
                    mensaje = data.get('mensaje', '')
                    if 'No se pudo obtener una Clave de Acceso válida' in mensaje:
                        print(f"\n🔍 DIAGNÓSTICO:")
                        print(f"   El servidor no puede extraer la clave de acceso")
                        print(f"   Esto indica que Tesseract no está funcionando")
                        print(f"   Posible causa: Servidor no usa configuración actualizada")
                    elif 'El comprobante no está AUTORIZADO' in mensaje:
                        print(f"\n🔍 DIAGNÓSTICO:")
                        print(f"   El servidor extrajo la clave de acceso")
                        print(f"   Pero la validación SRI falló")
                        print(f"   Esto indica que Tesseract SÍ está funcionando")
                        print(f"   Pero los datos no aparecen en la respuesta")
                
                # Verificar estructura de la respuesta
                print(f"\n📋 ESTRUCTURA DE LA RESPUESTA:")
                print(f"   Claves principales: {list(data.keys())}")
                
                if 'factura' in data:
                    print(f"   ✅ Sección 'factura' presente")
                    factura_data = data['factura']
                    if isinstance(factura_data, dict):
                        print(f"   ✅ Sección 'factura' es un diccionario")
                        print(f"   ✅ Claves en 'factura': {list(factura_data.keys())}")
                    else:
                        print(f"   ❌ Sección 'factura' no es un diccionario: {type(factura_data)}")
                else:
                    print(f"   ❌ Sección 'factura' NO presente")
                    print(f"   ❌ Esto indica que el servidor no está usando el código actualizado")
                
                # Verificar riesgo
                riesgo = data.get('riesgo', {})
                print(f"\n⚠️ ANÁLISIS DE RIESGO:")
                print(f"   Score: {riesgo.get('score', 'N/A')}")
                print(f"   Nivel: {riesgo.get('nivel', 'N/A')}")
                print(f"   Es Falso Probable: {riesgo.get('es_falso_probable', 'N/A')}")
                
                # Guardar respuesta completa
                with open("respuesta_factura_especifica.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"\n💾 Respuesta completa guardada en: respuesta_factura_especifica.json")
                
            else:
                print(f"❌ Error del servidor: {response.status_code}")
                print(f"   Respuesta: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Error de conexión: El servidor no está ejecutándose")
            print(f"   Asegúrate de que el servidor esté ejecutándose en el puerto 8001")
        except requests.exceptions.Timeout:
            print(f"❌ Timeout: El servidor tardó más de 60 segundos")
        except Exception as e:
            print(f"❌ Error: {e}")
            
    except FileNotFoundError:
        print(f"❌ Archivo PDF no encontrado: {pdf_path}")
        print(f"   Verifica que la ruta sea correcta")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_factura_especifica()
