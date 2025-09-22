#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para verificar si el servidor está usando la configuración correcta
"""

import requests
import json
import base64
import time

def verificar_servidor():
    """Verifica si el servidor está funcionando correctamente"""
    
    print("🔍 VERIFICANDO SERVIDOR")
    print("=" * 40)
    
    # Leer PDF de prueba
    pdf_path = "helpers/IMG/Factura_imagen.pdf"
    
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Convertir a base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        print(f"✅ PDF leído: {len(pdf_bytes)} bytes")
        print(f"✅ Base64: {len(pdf_base64)} caracteres")
        
        # Preparar petición
        payload = {"pdfbase64": pdf_base64}
        
        print("\n🚀 Enviando petición al servidor...")
        start_time = time.time()
        
        try:
            response = requests.post(
                "http://localhost:8001/validar-factura",
                json=payload,
                timeout=30
            )
            
            end_time = time.time()
            print(f"✅ Respuesta recibida en {end_time - start_time:.2f} segundos")
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\n📊 RESULTADO DEL SERVIDOR:")
                print(f"   SRI Verificado: {data.get('sri_verificado', 'N/A')}")
                print(f"   Mensaje: {data.get('mensaje', 'N/A')}")
                
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
                    print(f"   Posible causa: Servidor no usa configuración actualizada")
                
                # Verificar riesgo
                riesgo = data.get('riesgo', {})
                print(f"\n⚠️ ANÁLISIS DE RIESGO:")
                print(f"   Score: {riesgo.get('score', 'N/A')}")
                print(f"   Nivel: {riesgo.get('nivel', 'N/A')}")
                print(f"   Es Falso Probable: {riesgo.get('es_falso_probable', 'N/A')}")
                
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
    verificar_servidor()
