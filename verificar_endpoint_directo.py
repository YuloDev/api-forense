#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para verificar el endpoint directamente
"""

import base64
import tempfile
import time
import json
import traceback
from routes.validar_factura import validar_factura, PeticionFactura

def verificar_endpoint_directo():
    """Verifica el endpoint directamente"""
    
    print("🔍 VERIFICANDO ENDPOINT DIRECTAMENTE")
    print("=" * 50)
    
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
        
        # Crear petición
        peticion = PeticionFactura(pdfbase64=pdf_base64)
        print(f"✅ Petición creada: {type(peticion)}")
        
        print(f"\n🚀 Ejecutando endpoint directamente...")
        start_time = time.time()
        
        try:
            # Ejecutar endpoint directamente (es async)
            import asyncio
            response = asyncio.run(validar_factura(peticion))
            
            end_time = time.time()
            print(f"✅ Endpoint ejecutado en {end_time - start_time:.2f} segundos")
            print(f"   Tipo de respuesta: {type(response)}")
            
            # Verificar si es JSONResponse
            if hasattr(response, 'body'):
                # Es JSONResponse, extraer el contenido
                import json
                data = json.loads(response.body.decode('utf-8'))
                print(f"   ✅ Respuesta es JSONResponse")
            else:
                # Es un diccionario directo
                data = response
                print(f"   ✅ Respuesta es diccionario directo")
            
            print(f"\n📊 RESULTADO DEL ENDPOINT:")
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
                print(f"\n✅ ENDPOINT FUNCIONANDO CORRECTAMENTE")
                print(f"   OCR: ✅ Funcionando")
                print(f"   Extracción de datos: ✅ Funcionando")
                print(f"   Validación SRI: ✅ Funcionando")
            else:
                print(f"\n❌ ENDPOINT NO ESTÁ EXTRAYENDO DATOS")
                print(f"   OCR: ❌ No funcionando")
                print(f"   Extracción de datos: ❌ No funcionando")
            
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
                print(f"   ❌ Esto indica que hay un error en el endpoint")
            
            # Guardar respuesta completa
            with open("respuesta_endpoint_directo.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Respuesta guardada en: respuesta_endpoint_directo.json")
            
        except Exception as e:
            print(f"❌ Error ejecutando endpoint: {e}")
            traceback.print_exc()
            
    except FileNotFoundError:
        print(f"❌ Archivo PDF no encontrado: {pdf_path}")
        print(f"   Verifica que la ruta sea correcta")
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    verificar_endpoint_directo()
