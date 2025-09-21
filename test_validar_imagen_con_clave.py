#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar el endpoint validar_imagen con parsing de clave de acceso
"""

import requests
import json
import os
import base64

def test_validar_imagen():
    """Prueba el endpoint validar_imagen con una imagen de factura"""
    print("🔬 PROBANDO ENDPOINT VALIDAR_IMAGEN CON CLAVE DE ACCESO")
    print("=" * 70)
    
    # URL del endpoint
    url = "http://localhost:8001/validar-imagen"
    
    # Buscar una imagen de prueba en la carpeta helpers/IMG
    img_folder = "helpers/IMG"
    if not os.path.exists(img_folder):
        print(f"❌ Carpeta {img_folder} no existe")
        return False
    
    # Buscar archivos de imagen
    import glob
    img_files = glob.glob(os.path.join(img_folder, "*.png")) + glob.glob(os.path.join(img_folder, "*.jpg")) + glob.glob(os.path.join(img_folder, "*.jpeg"))
    
    if not img_files:
        print(f"❌ No se encontraron archivos de imagen en {img_folder}")
        return False
    
    print(f"✅ Encontrados {len(img_files)} archivos de imagen:")
    for i, file in enumerate(img_files, 1):
        print(f"   {i}. {file}")
    
    # Usar el primer archivo encontrado
    img_path = img_files[0]
    print(f"\n🔄 Procesando: {img_path}")
    
    try:
        # Leer la imagen
        with open(img_path, 'rb') as f:
            img_bytes = f.read()
        
        print(f"✅ Imagen leída: {len(img_bytes)} bytes")
        
        # Convertir a base64
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # Preparar request
        data = {
            'imagen_base64': img_base64
        }
        
        print("📡 Enviando request al endpoint...")
        response = requests.post(url, json=data, timeout=120)
        
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
            print(f"   - Razón Social: {factura.get('razonSocial')}")
            print(f"   - Fecha Emisión: {factura.get('fechaEmision')}")
            print(f"   - Total: {factura.get('importeTotal')}")
            print(f"   - Clave Acceso: {factura.get('claveAcceso')}")
            
            # Verificar clave parseada
            clave_parseada = data.get("clave_acceso_parseada")
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
            else:
                print(f"\n🔑 CLAVE DE ACCESO PARSEADA: No disponible")
            
            # Verificar parser avanzado
            parser_avanzado = data.get("parser_avanzado", {})
            print(f"\n🔍 PARSER AVANZADO:")
            print(f"   - Disponible: {parser_avanzado.get('disponible', False)}")
            print(f"   - Barcodes detectados: {parser_avanzado.get('barcodes_detectados', 0)}")
            print(f"   - Items detectados: {parser_avanzado.get('items_detectados', 0)}")
            
            # Verificar metadatos avanzados
            metadatos = parser_avanzado.get('metadatos_avanzados', {})
            print(f"\n📊 METADATOS AVANZADOS:")
            print(f"   - RUC: {metadatos.get('ruc')}")
            print(f"   - Número factura: {metadatos.get('invoice_number')}")
            print(f"   - Autorización: {metadatos.get('authorization')}")
            print(f"   - Ambiente: {metadatos.get('environment')}")
            print(f"   - Fecha emisión: {metadatos.get('issue_datetime')}")
            print(f"   - Comprador: {metadatos.get('buyer_name')}")
            print(f"   - ID comprador: {metadatos.get('buyer_id')}")
            print(f"   - Emisor: {metadatos.get('emitter_name')}")
            
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
    print("🔬 TEST ENDPOINT VALIDAR_IMAGEN CON CLAVE DE ACCESO")
    print("=" * 80)
    
    # Probar endpoint
    success = test_validar_imagen()
    
    print("\n" + "=" * 80)
    print("📊 RESUMEN:")
    print(f"   Endpoint: {'✅' if success else '❌'}")
    
    if not success:
        print("\n⚠️  PROBLEMAS:")
        print("   - Verificar que el servidor esté ejecutándose")
        print("   - Verificar que haya archivos de imagen en helpers/IMG/")
        print("   - Revisar logs del servidor")
    else:
        print("\n🎉 ¡ENDPOINT FUNCIONANDO CORRECTAMENTE!")

if __name__ == "__main__":
    main()
