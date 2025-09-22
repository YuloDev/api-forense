#!/usr/bin/env python3
"""
Script para probar el endpoint validar-factura con un PDF específico
"""

import base64
import requests
import json
import time

def test_validar_factura():
    """Prueba el endpoint validar-factura con un PDF"""
    
    # Leer el archivo PDF
    pdf_path = r"C:\Users\Nexti\sources\api-forense\helpers\IMG\Factura_imagen.pdf"
    
    try:
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        print(f"✅ Archivo PDF leído exitosamente")
        print(f"   Tamaño: {len(pdf_bytes)} bytes")
        
        # Convertir a base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        print(f"✅ PDF convertido a base64")
        print(f"   Longitud base64: {len(pdf_base64)} caracteres")
        
    except Exception as e:
        print(f"❌ Error leyendo el archivo PDF: {e}")
        return
    
    # Preparar la petición
    url = "http://localhost:8001/validar-factura"
    payload = {
        "pdfbase64": pdf_base64
    }
    
    print(f"\n🚀 Enviando petición a: {url}")
    print(f"   Payload size: {len(json.dumps(payload))} caracteres")
    
    try:
        # Hacer la petición
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=600)  # 10 minutos timeout
        end_time = time.time()
        
        print(f"✅ Respuesta recibida en {end_time - start_time:.2f} segundos")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Mostrar información básica
            print(f"\n📊 RESULTADO DEL ANÁLISIS:")
            print(f"   SRI Verificado: {result.get('sri_verificado', 'N/A')}")
            print(f"   Mensaje: {result.get('mensaje', 'N/A')}")
            print(f"   Tipo Archivo: {result.get('tipo_archivo', 'N/A')}")
            
            # Mostrar información de la factura
            factura = result.get('factura', {})
            print(f"\n📋 INFORMACIÓN DE LA FACTURA:")
            print(f"   RUC: {factura.get('ruc', 'N/A')}")
            print(f"   Razón Social: {factura.get('razonSocial', 'N/A')}")
            print(f"   Fecha Emisión: {factura.get('fechaEmision', 'N/A')}")
            print(f"   Importe Total: {factura.get('importeTotal', 'N/A')}")
            print(f"   Clave Acceso: {factura.get('claveAcceso', 'N/A')}")
            
            # Mostrar validación SRI
            validacion_sri = factura.get('validacion_sri', {})
            print(f"\n🔍 VALIDACIÓN SRI:")
            print(f"   Válido: {validacion_sri.get('valido', 'N/A')}")
            print(f"   Error: {validacion_sri.get('error', 'N/A')}")
            
            # Mostrar análisis de riesgo
            riesgo = result.get('riesgo', {})
            print(f"\n⚠️ ANÁLISIS DE RIESGO:")
            print(f"   Score: {riesgo.get('score', 'N/A')}")
            print(f"   Nivel: {riesgo.get('nivel', 'N/A')}")
            print(f"   Es Falso Probable: {riesgo.get('es_falso_probable', 'N/A')}")
            
            # Mostrar checks prioritarios
            prioritarias = riesgo.get('prioritarias', [])
            if prioritarias:
                print(f"\n🚨 CHECKS PRIORITARIOS ({len(prioritarias)}):")
                for i, check in enumerate(prioritarias, 1):
                    print(f"   {i}. {check.get('check', 'N/A')} - Penalización: {check.get('penalizacion', 0)}")
                    detalle = check.get('detalle', {})
                    if isinstance(detalle, dict):
                        print(f"      Detectado: {detalle.get('detectado', 'N/A')}")
                        print(f"      Interpretación: {detalle.get('interpretacion', 'N/A')}")
                    else:
                        print(f"      Detalle: {detalle}")
            
            # Mostrar checks secundarios
            secundarias = riesgo.get('secundarias', [])
            if secundarias:
                print(f"\n⚠️ CHECKS SECUNDARIOS ({len(secundarias)}):")
                for i, check in enumerate(secundarias, 1):
                    print(f"   {i}. {check.get('check', 'N/A')} - Penalización: {check.get('penalizacion', 0)}")
                    detalle = check.get('detalle', {})
                    if isinstance(detalle, dict):
                        print(f"      Detectado: {detalle.get('detectado', 'N/A')}")
                        print(f"      Interpretación: {detalle.get('interpretacion', 'N/A')}")
                    else:
                        print(f"      Detalle: {detalle}")
            
            # Mostrar checks adicionales
            adicionales = riesgo.get('adicionales', [])
            if adicionales:
                print(f"\nℹ️ CHECKS ADICIONALES ({len(adicionales)}):")
                for i, check in enumerate(adicionales, 1):
                    print(f"   {i}. {check.get('check', 'N/A')} - Penalización: {check.get('penalizacion', 0)}")
                    detalle = check.get('detalle', {})
                    if isinstance(detalle, dict):
                        print(f"      Detectado: {detalle.get('detectado', 'N/A')}")
                        print(f"      Interpretación: {detalle.get('interpretacion', 'N/A')}")
                    else:
                        print(f"      Detalle: {detalle}")
            
            # Guardar respuesta completa en archivo
            with open('respuesta_validar_factura.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Respuesta completa guardada en: respuesta_validar_factura.json")
            
        else:
            print(f"❌ Error en la respuesta:")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"⏰ Timeout: La petición tardó más de 10 minutos")
    except requests.exceptions.ConnectionError:
        print(f"🔌 Error de conexión: ¿Está el servidor ejecutándose en localhost:8000?")
    except Exception as e:
        print(f"❌ Error en la petición: {e}")

if __name__ == "__main__":
    print("🧪 PRUEBA DEL ENDPOINT VALIDAR-FACTURA")
    print("=" * 50)
    test_validar_factura()
