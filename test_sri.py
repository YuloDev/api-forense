#!/usr/bin/env python3
"""
Test para verificar la conectividad con el SRI y probar una clave de acceso específica.
"""

import json
import sys
from sri import sri_autorizacion_por_clave, parse_autorizacion_response, factura_xml_to_json, validar_clave_acceso_interna

def test_sri_connection(clave_acceso: str):
    """Prueba la conexión al SRI con una clave de acceso específica."""
    
    print("=" * 60)
    print("🇪🇨 TEST CONEXIÓN SRI - SERVICIO DE RENTAS INTERNAS")
    print("=" * 60)
    print(f"📋 Clave de acceso: {clave_acceso}")
    print(f"📏 Longitud: {len(clave_acceso)} caracteres")
    print()
    
    # PASO 1: Validación interna
    print("🔍 PASO 1: VALIDACIÓN INTERNA")
    print("-" * 40)
    try:
        es_valida, mensaje, detalles = validar_clave_acceso_interna(clave_acceso)
        
        if es_valida:
            print("✅ Validación interna: APROBADA")
            print(f"📝 {mensaje}")
            print()
            print("📊 Estructura de la clave:")
            estructura = detalles.get("estructura", {})
            for campo, valor in estructura.items():
                print(f"   {campo}: {valor}")
            print()
            print("✅ Validaciones pasadas:")
            for validacion in detalles.get("validaciones", []):
                for key, value in validacion.items():
                    print(f"   {key}: {value}")
            print()
        else:
            print("❌ Validación interna: FALLÓ")
            print(f"📝 {mensaje}")
            print()
            print("📋 Detalles del error:")
            print(f"   Longitud: {detalles['longitud']}")
            print(f"   Formato numérico: {detalles['formato_numerico']}")
            if detalles.get("validaciones"):
                print("   Validaciones pasadas:")
                for validacion in detalles["validaciones"]:
                    for key, value in validacion.items():
                        print(f"     {key}: {value}")
            print()
            print("⚠️  No se continuará con la consulta al SRI")
            return False, "VALIDACION_INTERNA_FALLIDA", detalles
            
    except Exception as e:
        print(f"❌ Error en validación interna: {e}")
        print("⚠️  Continuando con consulta al SRI...")
        print()
    
    # PASO 2: Consulta al SRI
    print("🌐 PASO 2: CONSULTA AL SRI")
    print("-" * 40)
    try:
        print("🔌 Conectando al SRI...")
        print("   URL WSDL: https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl")
        print()
        
        # Realizar consulta al SRI
        response = sri_autorizacion_por_clave(clave_acceso)
        print("✅ Respuesta recibida del SRI")
        print()
        
        # DEBUG: Mostrar respuesta raw
        print("🔍 DEBUG - Respuesta raw del SRI:")
        print(f"   Tipo: {type(response)}")
        print(f"   Contenido: {str(response)[:200]}...")
        print()
        
        # Procesar respuesta
        print("📊 Procesando respuesta...")
        autorizado, estado, xml_comprobante, raw_data = parse_autorizacion_response(response)
        
        print("🎯 RESULTADOS:")
        print("-" * 40)
        print(f"✨ Estado: {estado}")
        print(f"🔐 Autorizado: {'SÍ' if autorizado else 'NO'}")
        print(f"🗂️  Número de comprobantes: {raw_data.get('numeroComprobantes', 'N/A')}")
        print(f"🔑 Clave consultada: {raw_data.get('claveAccesoConsultada', 'N/A')}")
        print()
        
        # Mostrar autorizaciones
        autorizaciones = raw_data.get('autorizaciones', [])
        if autorizaciones:
            print("📋 DETALLES DE AUTORIZACIÓN:")
            print("-" * 40)
            for i, auth in enumerate(autorizaciones, 1):
                print(f"   Autorización #{i}:")
                print(f"      🏷️  Estado: {auth.get('estado', 'N/A')}")
                print(f"      🔢 Número: {auth.get('numeroAutorizacion', 'N/A')}")
                print(f"      📅 Fecha: {auth.get('fechaAutorizacion', 'N/A')}")
                print(f"      🌍 Ambiente: {auth.get('ambiente', 'N/A')}")
                print()
        
        # Si hay XML, procesarlo
        if xml_comprobante:
            print("📄 XML COMPROBANTE ENCONTRADO")
            print("-" * 40)
            print(f"📏 Tamaño del XML: {len(xml_comprobante)} caracteres")
            
            try:
                # Convertir XML a JSON
                factura_json = factura_xml_to_json(xml_comprobante)
                
                print("🔄 XML convertido a JSON exitosamente")
                print()
                
                # Mostrar información clave
                info_trib = factura_json.get('infoTributaria', {})
                info_fact = factura_json.get('infoFactura', {})
                detalles = factura_json.get('detalles', [])
                
                print("💼 INFORMACIÓN TRIBUTARIA:")
                print(f"   🏢 RUC: {info_trib.get('ruc', 'N/A')}")
                print(f"   🏪 Razón Social: {info_trib.get('razonSocial', 'N/A')}")
                print(f"   🔑 Clave de Acceso: {info_trib.get('claveAcceso', 'N/A')}")
                print(f"   📋 Código Documento: {info_trib.get('codDoc', 'N/A')}")
                print(f"   🏪 Establecimiento: {info_trib.get('estab', 'N/A')}")
                print(f"   🖨️  Punto Emisión: {info_trib.get('ptoEmi', 'N/A')}")
                print(f"   📄 Secuencial: {info_trib.get('secuencial', 'N/A')}")
                print()
                
                print("🧾 INFORMACIÓN DE FACTURA:")
                print(f"   📅 Fecha Emisión: {info_fact.get('fechaEmision', 'N/A')}")
                print(f"   👤 Comprador: {info_fact.get('razonSocialComprador', 'N/A')}")
                print(f"   🆔 ID Comprador: {info_fact.get('identificacionComprador', 'N/A')}")
                print(f"   💰 Total sin Impuestos: ${info_fact.get('totalSinImpuestos', 'N/A')}")
                print(f"   🎯 Total Descuento: ${info_fact.get('totalDescuento', 'N/A')}")
                print(f"   💵 Importe Total: ${info_fact.get('importeTotal', 'N/A')}")
                print(f"   💱 Moneda: {info_fact.get('moneda', 'N/A')}")
                print()
                
                print(f"📦 DETALLES: {len(detalles)} items")
                if detalles:
                    print("-" * 30)
                    for i, item in enumerate(detalles[:3], 1):  # Mostrar solo los primeros 3
                        print(f"   Item #{i}:")
                        print(f"      📝 Descripción: {item.get('descripcion', 'N/A')[:50]}...")
                        print(f"      🔢 Cantidad: {item.get('cantidad', 'N/A')}")
                        print(f"      💰 Precio Unitario: ${item.get('precioUnitario', 'N/A')}")
                        print(f"      💵 Total: ${item.get('precioTotalSinImpuesto', 'N/A')}")
                        print()
                    
                    if len(detalles) > 3:
                        print(f"   ... y {len(detalles) - 3} items más")
                        print()
                
                # Guardar JSON completo para inspección
                output_file = f"sri_response_{clave_acceso[:10]}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "clave_acceso": clave_acceso,
                        "autorizado": autorizado,
                        "estado": estado,
                        "raw_response": raw_data,
                        "factura_json": factura_json
                    }, f, indent=2, ensure_ascii=False)
                
                print(f"💾 Respuesta completa guardada en: {output_file}")
                
            except Exception as e:
                print(f"❌ Error procesando XML: {e}")
                print(f"📄 XML raw (primeros 500 chars):")
                print(xml_comprobante[:500])
                print("...")
        else:
            print("⚠️  No se encontró XML del comprobante")
        
        print()
        print("=" * 60)
        print("✅ TEST COMPLETADO")
        print("=" * 60)
        
        return autorizado, estado, raw_data
        
    except Exception as e:
        print(f"❌ ERROR en la consulta SRI: {e}")
        print(f"🔍 Tipo de error: {type(e).__name__}")
        import traceback
        print("\n📋 Traceback completo:")
        traceback.print_exc()
        return False, "ERROR", {"error": str(e)}

if __name__ == "__main__":
    # Clave de acceso AUTORIZADA según el SRI web (49 caracteres completos)
    clave_test = "1509202501179313133600120011010000003661234567811"
    
    print("🎯 PROBANDO CLAVE AUTORIZADA SEGÚN SRI WEB")
    print(f"   Clave: {clave_test}")
    print(f"   Estado esperado: AUTORIZADO")
    print()
    
    # Validar longitud de clave
    if len(clave_test) != 49:
        print(f"⚠️  ADVERTENCIA: La clave de acceso tiene {len(clave_test)} caracteres, se esperan 49")
    
    # Ejecutar test
    test_sri_connection(clave_test)
