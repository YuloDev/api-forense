#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar el endpoint validar_factura con análisis completo
"""

import requests
import json
import os
import base64

def test_validar_factura():
    """Prueba el endpoint validar_factura con un PDF de prueba"""
    print("🔬 PROBANDO ENDPOINT VALIDAR_FACTURA COMPLETO")
    print("=" * 60)
    
    # URL del endpoint
    url = "http://localhost:8001/validar-factura"
    
    # Buscar un PDF de prueba en la carpeta helpers/IMG
    pdf_folder = "helpers/IMG"
    if not os.path.exists(pdf_folder):
        print(f"❌ Carpeta {pdf_folder} no existe")
        return False
    
    # Buscar archivos PDF
    import glob
    pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))
    
    if not pdf_files:
        print(f"❌ No se encontraron archivos PDF en {pdf_folder}")
        print("   Creando PDF de prueba...")
        
        # Crear PDF de prueba
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        filename = os.path.join(pdf_folder, "factura_prueba.pdf")
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        
        # Título
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 50, "FACTURA ELECTRÓNICA")
        
        # Información de la empresa
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 80, "FARMACIAS Y COMISARIATOS DE MEDICINAS S.A.")
        c.drawString(100, height - 100, "RUC: 1790710319001")
        c.drawString(100, height - 120, "Dirección: Av. Interoceánica S/N")
        
        # Número de factura
        c.drawString(100, height - 150, "FACTURA No. 026-200-000021384")
        
        # Número de autorización
        c.drawString(100, height - 180, "NÚMERO DE AUTORIZACIÓN")
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, height - 200, "0807202501179071031900120262000000213845658032318")
        
        # Ambiente
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 230, "AMBIENTE: PRODUCCION")
        
        # Fecha
        c.drawString(100, height - 260, "FECHA Y HORA DE EMISIÓN: 2025-07-08 19:58:13")
        
        # Cliente
        c.drawString(100, height - 290, "Razón Social: ROCKO VERDEZOTO")
        c.drawString(100, height - 310, "Identificación: 1234567890")
        
        # Productos
        c.drawString(100, height - 350, "DETALLE DE PRODUCTOS:")
        c.drawString(120, height - 370, "1. MEDICAMENTO A - Cantidad: 1 - Precio: $23.00")
        c.drawString(120, height - 390, "2. MEDICAMENTO B - Cantidad: 2 - Precio: $15.50")
        
        # Totales
        c.drawString(100, height - 430, "SUBTOTAL: $54.00")
        c.drawString(100, height - 450, "IVA 15%: $8.10")
        c.drawString(100, height - 470, "TOTAL: $62.10")
        
        # Forma de pago
        c.drawString(100, height - 500, "FORMA DE PAGO: TARJETA DE CREDITO")
        
        # Guardar PDF
        c.save()
        print(f"✅ PDF creado: {filename}")
        pdf_files = [filename]
    
    # Usar el primer archivo encontrado
    pdf_path = pdf_files[0]
    print(f"\n🔄 Procesando: {pdf_path}")
    
    try:
        # Leer el PDF
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        print(f"✅ PDF leído: {len(pdf_bytes)} bytes")
        
        # Preparar request
        files = {
            'archivo': ('test.pdf', pdf_bytes, 'application/pdf')
        }
        data = {
            'validar_sri': True
        }
        
        print("📡 Enviando request al endpoint...")
        response = requests.post(url, files=files, data=data, timeout=120)
        
        if response.status_code == 200:
            print("✅ Request exitoso")
            data = response.json()
            
            # Verificar campos principales
            print(f"\n📋 RESULTADOS PRINCIPALES:")
            print(f"   - SRI Verificado: {data.get('sri_verificado', False)}")
            print(f"   - Tipo Archivo: {data.get('tipo_archivo', 'N/A')}")
            print(f"   - Coincidencia: {data.get('coincidencia', 'N/A')}")
            
            # Verificar factura
            factura = data.get("factura", {})
            print(f"\n📄 CAMPOS DE FACTURA:")
            print(f"   - RUC: {factura.get('ruc')}")
            print(f"   - Fecha Emisión: {factura.get('fechaEmision')}")
            print(f"   - Clave Acceso: {factura.get('claveAcceso')}")
            print(f"   - Número Factura: {factura.get('metadata', {}).get('invoice_number')}")
            print(f"   - Ambiente: {factura.get('metadata', {}).get('environment')}")
            
            # Verificar clave parseada
            clave_parseada = factura.get("claveAccesoParseada", {})
            if clave_parseada:
                print(f"\n🔑 CLAVE DE ACCESO PARSEADA:")
                print(f"   - Válida: {clave_parseada.get('valida', False)}")
                print(f"   - Fecha: {clave_parseada.get('fecha_emision')}")
                print(f"   - RUC: {clave_parseada.get('ruc_emisor')}")
                print(f"   - Tipo: {clave_parseada.get('tipo_comprobante', {}).get('descripcion')}")
                print(f"   - Serie: {clave_parseada.get('serie')}")
                print(f"   - Secuencial: {clave_parseada.get('secuencial')}")
                print(f"   - Emisión: {clave_parseada.get('tipo_emision', {}).get('descripcion')}")
                print(f"   - Código: {clave_parseada.get('codigo_numerico')}")
                print(f"   - DV: {clave_parseada.get('digito_verificador')}")
            
            # Verificar parser avanzado
            parser_avanzado = data.get("parser_avanzado", {})
            print(f"\n🔍 PARSER AVANZADO:")
            print(f"   - Disponible: {parser_avanzado.get('disponible', False)}")
            print(f"   - Barcodes detectados: {parser_avanzado.get('barcodes_detectados', 0)}")
            print(f"   - Items detectados: {parser_avanzado.get('items_detectados', 0)}")
            
            # Verificar metadatos avanzados
            metadatos = parser_avanzado.get('metadatos_avanzados', {})
            print(f"\n📊 METADATOS AVANZADOS:")
            print(f"   - Páginas procesadas: {metadatos.get('pages_processed', 0)}")
            print(f"   - Métodos de texto: {metadatos.get('text_methods', [])}")
            print(f"   - Longitud texto: {metadatos.get('text_length', 0)}")
            print(f"   - Clave acceso encontrada: {metadatos.get('access_key_found', False)}")
            print(f"   - Códigos de barras encontrados: {metadatos.get('barcodes_found', False)}")
            
            # Verificar riesgo
            riesgo = data.get("riesgo", {})
            print(f"\n⚠️  ANÁLISIS DE RIESGO:")
            print(f"   - Score: {riesgo.get('score', 0)}")
            print(f"   - Nivel: {riesgo.get('nivel', 'N/A')}")
            print(f"   - Es falso probable: {riesgo.get('es_falso_probable', False)}")
            
            # Verificar texto extraído
            texto_extraido = data.get("texto_extraido", "")
            print(f"\n📝 TEXTO EXTRAÍDO:")
            print(f"   - Longitud: {len(texto_extraido)} caracteres")
            print(f"   - Primeros 300 chars: {texto_extraido[:300]}...")
            
            return True
            
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en request: {e}")
        return False

def main():
    print("🔬 TEST ENDPOINT VALIDAR_FACTURA COMPLETO")
    print("=" * 70)
    
    # Probar endpoint
    success = test_validar_factura()
    
    print("\n" + "=" * 70)
    print("📊 RESUMEN:")
    print(f"   Endpoint: {'✅' if success else '❌'}")
    
    if not success:
        print("\n⚠️  PROBLEMAS:")
        print("   - Verificar que el servidor esté ejecutándose")
        print("   - Verificar que haya archivos PDF en helpers/IMG/")
        print("   - Revisar logs del servidor")
    else:
        print("\n🎉 ¡ENDPOINT FUNCIONANDO CORRECTAMENTE!")

if __name__ == "__main__":
    main()
