#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test del endpoint validar_factura con validación SRI
"""

import requests
import json
import os

def test_validar_factura_sri():
    """Test del endpoint validar_factura con validación SRI"""
    print("🔬 TEST ENDPOINT VALIDAR_FACTURA CON SRI")
    print("=" * 60)
    
    # URL del endpoint
    url = "http://localhost:8000/validar-factura"
    
    # PDF de prueba (si existe)
    pdf_path = "helpers/IMG/factura_prueba.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ No se encontró el PDF: {pdf_path}")
        print("📝 Creando PDF de prueba...")
        
        # Crear un PDF de prueba simple
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, "FACTURA")
        c.drawString(100, 730, "RUC: 1790710319001")
        c.drawString(100, 710, "Clave de Acceso: 0807202501179071031900120262000000213845658032318")
        c.drawString(100, 690, "Fecha: 2025-07-08")
        c.drawString(100, 670, "Total: $47.00")
        c.save()
        
        print(f"✅ PDF de prueba creado: {pdf_path}")
    
    print(f"📄 Procesando PDF: {pdf_path}")
    
    # Leer PDF
    with open(pdf_path, 'rb') as f:
        files = {'archivo': (pdf_path, f, 'application/pdf')}
        data = {'validar_sri': True}
        
        try:
            # Hacer petición
            response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                
                print("✅ Respuesta exitosa!")
                
                # Verificar sri_verificado principal
                sri_verificado_principal = result.get('sri_verificado', False)
                mensaje_principal = result.get('mensaje', 'N/A')
                
                print(f"\n🔑 VALIDACIÓN SRI PRINCIPAL:")
                print(f"   sri_verificado: {sri_verificado_principal}")
                print(f"   mensaje: {mensaje_principal}")
                
                # Verificar sri_verificado en factura
                if 'factura' in result:
                    factura = result['factura']
                    sri_verificado_factura = factura.get('sri_verificado', False)
                    mensaje_factura = factura.get('mensaje', 'N/A')
                    
                    print(f"\n📄 VALIDACIÓN SRI EN FACTURA:")
                    print(f"   sri_verificado: {sri_verificado_factura}")
                    print(f"   mensaje: {mensaje_factura}")
                    
                    # Verificar validacion_sri
                    if 'validacion_sri' in factura:
                        validacion = factura['validacion_sri']
                        print(f"\n🔍 DETALLES VALIDACIÓN SRI:")
                        print(f"   válido: {validacion.get('valido', False)}")
                        print(f"   clave_acceso: {validacion.get('clave_acceso', 'N/A')}")
                        
                        if validacion.get('consulta_sri'):
                            sri = validacion['consulta_sri']
                            print(f"   estado: {sri.get('estado', 'N/A')}")
                            print(f"   fecha_autorizacion: {sri.get('fecha_autorizacion', 'N/A')}")
                    
                    # Mostrar datos de la factura
                    print(f"\n📊 DATOS DE LA FACTURA:")
                    print(f"   RUC: {factura.get('ruc', 'N/A')}")
                    print(f"   Razón Social: {factura.get('razonSocial', 'N/A')}")
                    print(f"   Fecha Emisión: {factura.get('fechaEmision', 'N/A')}")
                    print(f"   Clave Acceso: {factura.get('claveAcceso', 'N/A')}")
                
                # Verificar clave_acceso_parseada
                if 'clave_acceso_parseada' in result:
                    clave_parseada = result['clave_acceso_parseada']
                    print(f"\n🔑 CLAVE DE ACCESO PARSEADA:")
                    print(f"   válida: {clave_parseada.get('valida', False)}")
                    print(f"   clave_completa: {clave_parseada.get('clave_completa', 'N/A')}")
                    print(f"   fecha_emision: {clave_parseada.get('fecha_emision', 'N/A')}")
                    print(f"   ruc_emisor: {clave_parseada.get('ruc_emisor', 'N/A')}")
                
                # Verificar consistencia
                if sri_verificado_principal == sri_verificado_factura:
                    print(f"\n✅ CONSISTENCIA: Los valores de sri_verificado coinciden")
                else:
                    print(f"\n❌ INCONSISTENCIA: Los valores de sri_verificado NO coinciden")
                    print(f"   Principal: {sri_verificado_principal}")
                    print(f"   Factura: {sri_verificado_factura}")
                
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
    test_validar_factura_sri()
