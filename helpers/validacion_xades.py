"""
Módulo para validación de firmas XAdES (XML Advanced Electronic Signatures).

Implementa validación específica para:
1. Documentos XML firmados con XAdES
2. Validación de certificados digitales ecuatorianos
3. Verificación de timestamps
4. Validación de políticas de firma
5. Análisis de metadatos de firma

Autor: Sistema de Análisis Forense
Versión: 1.0
"""

import re
import base64
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import xml.etree.ElementTree as ET

try:
    from asn1crypto import cms, x509, algosz
    ASN1_AVAILABLE = True
except ImportError:
    cms = x509 = algos = None
    ASN1_AVAILABLE = False

try:
    import oscrypto
    OSCRYPTO_AVAILABLE = True
except ImportError:
    oscrypto = None
    OSCRYPTO_AVAILABLE = False

try:
    from certvalidator import ValidationContext, CertificateValidator
    import certifi
    CERTVALIDATOR_AVAILABLE = True
except ImportError:
    ValidationContext = CertificateValidator = certifi = None
    CERTVALIDATOR_AVAILABLE = False

from .type_conversion import safe_serialize_dict, ensure_python_bool


def validar_xades(xml_content: str) -> Dict[str, Any]:
    """
    Valida firmas XAdES en documentos XML.
    
    Args:
        xml_content: Contenido XML del documento
        
    Returns:
        Dict con resultado de validación XAdES
    """
    try:
        # Parsear XML
        root = ET.fromstring(xml_content)
        print(f"[DEBUG XAdES] XML parseado correctamente, root tag: {root.tag}")
        
        # Buscar firmas XAdES
        firmas_xades = _buscar_firmas_xades(root)
        print(f"[DEBUG XAdES] Firmas encontradas: {len(firmas_xades)}")
        
        if not firmas_xades:
            print("[DEBUG XAdES] No se encontraron firmas XAdES")
            return safe_serialize_dict({
                "firma_detectada": False,
                "tipo_firma": "ninguna",
                "firmas": [],
                "resumen": "No se detectaron firmas XAdES en el documento"
            })
        
        # Validar cada firma
        firmas_validadas = []
        for i, firma in enumerate(firmas_xades):
            validacion = _validar_firma_xades(firma, xml_content)
            validacion["indice"] = i + 1
            firmas_validadas.append(validacion)
        
        # Calcular resumen
        resumen = _calcular_resumen_xades(firmas_validadas)
        
        return safe_serialize_dict({
            "firma_detectada": True,
            "tipo_firma": "xades",
            "firmas": firmas_validadas,
            "resumen": resumen,
            "dependencias": {
                "asn1crypto": ASN1_AVAILABLE,
                "oscrypto": OSCRYPTO_AVAILABLE,
                "certvalidator": CERTVALIDATOR_AVAILABLE
            }
        })
        
    except Exception as e:
        return safe_serialize_dict({
            "firma_detectada": False,
            "error": f"Error procesando XML: {str(e)}",
            "firmas": [],
            "resumen": "Error en análisis"
        })


def _buscar_firmas_xades(root: ET.Element) -> List[Dict[str, Any]]:
    """
    Busca firmas XAdES en el documento XML.
    
    Args:
        root: Elemento raíz del XML
        
    Returns:
        Lista de firmas XAdES encontradas
    """
    firmas = []
    
    # Buscar en todos los namespaces
    namespaces = {
        'ds': 'http://www.w3.org/2000/09/xmldsig#',
        'xades': 'http://uri.etsi.org/01903/v1.3.2#',
        'xades141': 'http://uri.etsi.org/01903/v1.4.1#',
        'xades132': 'http://uri.etsi.org/01903/v1.3.2#',
        'xades111': 'http://uri.etsi.org/01903/v1.1.1#'
    }
    
    # Buscar elementos Signature
    for ns_prefix, ns_uri in namespaces.items():
        signatures = root.findall(f'.//{{{ns_uri}}}Signature')
        print(f"[DEBUG XAdES] Buscando en namespace {ns_prefix}: {ns_uri}, encontradas: {len(signatures)}")
        for sig in signatures:
            firma_info = _extraer_info_firma_xades(sig, ns_uri)
            if firma_info:
                firmas.append(firma_info)
                print(f"[DEBUG XAdES] Firma agregada: {firma_info.get('id', 'sin_id')}")
    
    print(f"[DEBUG XAdES] Total firmas encontradas: {len(firmas)}")
    return firmas


def _extraer_info_firma_xades(signature: ET.Element, namespace: str) -> Optional[Dict[str, Any]]:
    """
    Extrae información de una firma XAdES.
    
    Args:
        signature: Elemento Signature
        namespace: Namespace de la firma
        
    Returns:
        Información de la firma
    """
    try:
        # Información básica
        info = {
            "namespace": namespace,
            "version": "XAdES",
            "metadatos": {},
            "certificados": [],
            "timestamps": [],
            "politicas": []
        }
        
        # Buscar SignedInfo
        signed_info = signature.find(f'.//{{{namespace}}}SignedInfo')
        if signed_info is not None:
            info["metadatos"]["signed_info"] = _extraer_signed_info(signed_info, namespace)
        
        # Buscar KeyInfo
        key_info = signature.find(f'.//{{{namespace}}}KeyInfo')
        if key_info is not None:
            info["certificados"] = _extraer_certificados(key_info, namespace)
        
        # Buscar Object (XAdES)
        objects = signature.findall(f'.//{{{namespace}}}Object')
        for obj in objects:
            # Timestamps
            timestamps = obj.findall(f'.//{{{namespace}}}EncapsulatedTimeStamp')
            for ts in timestamps:
                info["timestamps"].append({
                    "tipo": "timestamp",
                    "contenido": ts.text,
                    "encoding": ts.get("Encoding", "base64")
                })
            
            # Políticas de firma
            policies = obj.findall(f'.//{{{namespace}}}SignaturePolicyIdentifier')
            for policy in policies:
                info["politicas"].append(_extraer_politica_firma(policy, namespace))
        
        # Buscar QualifyingProperties (XAdES específico)
        qualifying_props = signature.find(f'.//{{{namespace}}}QualifyingProperties')
        if qualifying_props is not None:
            info["metadatos"]["qualifying_properties"] = _extraer_qualifying_properties(qualifying_props, namespace)
        
        return info
        
    except Exception as e:
        return None


def _extraer_signed_info(signed_info: ET.Element, namespace: str) -> Dict[str, Any]:
    """Extrae información de SignedInfo"""
    info = {}
    
    # CanonicalizationMethod
    canon_method = signed_info.find(f'.//{{{namespace}}}CanonicalizationMethod')
    if canon_method is not None:
        info["canonicalization_method"] = canon_method.get("Algorithm", "unknown")
    
    # SignatureMethod
    sig_method = signed_info.find(f'.//{{{namespace}}}SignatureMethod')
    if sig_method is not None:
        info["signature_method"] = sig_method.get("Algorithm", "unknown")
    
    # Reference elements
    references = signed_info.findall(f'.//{{{namespace}}}Reference')
    info["references"] = []
    for ref in references:
        ref_info = {
            "uri": ref.get("URI", ""),
            "type": ref.get("Type", ""),
            "digest_method": "",
            "digest_value": ""
        }
        
        digest_method = ref.find(f'.//{{{namespace}}}DigestMethod')
        if digest_method is not None:
            ref_info["digest_method"] = digest_method.get("Algorithm", "unknown")
        
        digest_value = ref.find(f'.//{{{namespace}}}DigestValue')
        if digest_value is not None:
            ref_info["digest_value"] = digest_value.text or ""
        
        info["references"].append(ref_info)
    
    return info


def _extraer_certificados(key_info: ET.Element, namespace: str) -> List[Dict[str, Any]]:
    """Extrae certificados del KeyInfo"""
    certificados = []
    
    # X509Data elements
    x509_data_list = key_info.findall(f'.//{{{namespace}}}X509Data')
    for x509_data in x509_data_list:
        # X509Certificate
        cert_elements = x509_data.findall(f'.//{{{namespace}}}X509Certificate')
        for cert_elem in cert_elements:
            if cert_elem.text:
                try:
                    cert_der = base64.b64decode(cert_elem.text)
                    cert_info = _analizar_certificado_x509(cert_der)
                    if cert_info:
                        certificados.append(cert_info)
                except Exception:
                    continue
    
    return certificados


def _analizar_certificado_x509(cert_der: bytes) -> Optional[Dict[str, Any]]:
    """Analiza un certificado X.509"""
    if not ASN1_AVAILABLE:
        return None
    
    try:
        cert = x509.Certificate.load(cert_der)
        
        # Información del sujeto
        subject = cert.subject.native
        subject_info = {
            "common_name": subject.get("common_name", ""),
            "organization": subject.get("organization_name", ""),
            "country": subject.get("country_name", ""),
            "email": subject.get("email_address", "")
        }
        
        # Información del emisor
        issuer = cert.issuer.native
        issuer_info = {
            "common_name": issuer.get("common_name", ""),
            "organization": issuer.get("organization_name", ""),
            "country": issuer.get("country_name", "")
        }
        
        # Validez temporal
        validity = cert["tbs_certificate"]["validity"]
        not_before = validity["not_before"].native
        not_after = validity["not_after"].native
        
        # Algoritmo de firma
        sig_algo = cert["tbs_certificate"]["signature"]["algorithm"].native
        
        return {
            "subject": subject_info,
            "issuer": issuer_info,
            "not_before": not_before.strftime("%Y-%m-%d %H:%M:%S") if isinstance(not_before, datetime) else str(not_before),
            "not_after": not_after.strftime("%Y-%m-%d %H:%M:%S") if isinstance(not_after, datetime) else str(not_after),
            "signature_algorithm": sig_algo,
            "serial_number": str(cert.serial_number),
            "version": cert.version.native
        }
        
    except Exception as e:
        return None


def _extraer_politica_firma(policy: ET.Element, namespace: str) -> Dict[str, Any]:
    """Extrae información de política de firma"""
    info = {
        "tipo": "signature_policy",
        "identificador": "",
        "descripcion": "",
        "hash": "",
        "hash_algorithm": ""
    }
    
    # SignaturePolicyId
    policy_id = policy.find(f'.//{{{namespace}}}SignaturePolicyId')
    if policy_id is not None:
        # SigPolicyId
        sig_policy_id = policy_id.find(f'.//{{{namespace}}}SigPolicyId')
        if sig_policy_id is not None:
            identifier = sig_policy_id.find(f'.//{{{namespace}}}Identifier')
            if identifier is not None:
                info["identificador"] = identifier.text or ""
        
        # SigPolicyHash
        sig_policy_hash = policy_id.find(f'.//{{{namespace}}}SigPolicyHash')
        if sig_policy_hash is not None:
            digest_method = sig_policy_hash.find(f'.//{{{namespace}}}DigestMethod')
            if digest_method is not None:
                info["hash_algorithm"] = digest_method.get("Algorithm", "unknown")
            
            digest_value = sig_policy_hash.find(f'.//{{{namespace}}}DigestValue')
            if digest_value is not None:
                info["hash"] = digest_value.text or ""
    
    return info


def _extraer_qualifying_properties(qualifying_props: ET.Element, namespace: str) -> Dict[str, Any]:
    """Extrae QualifyingProperties de XAdES"""
    info = {
        "target": qualifying_props.get("Target", ""),
        "signed_properties": {},
        "unsigned_properties": {}
    }
    
    # SignedProperties
    signed_props = qualifying_props.find(f'.//{{{namespace}}}SignedProperties')
    if signed_props is not None:
        info["signed_properties"] = _extraer_signed_properties(signed_props, namespace)
    
    # UnsignedProperties
    unsigned_props = qualifying_props.find(f'.//{{{namespace}}}UnsignedProperties')
    if unsigned_props is not None:
        info["unsigned_properties"] = _extraer_unsigned_properties(unsigned_props, namespace)
    
    return info


def _extraer_signed_properties(signed_props: ET.Element, namespace: str) -> Dict[str, Any]:
    """Extrae SignedProperties"""
    info = {
        "signing_time": None,
        "signing_certificate": {},
        "signature_policy": {},
        "data_object_format": []
    }
    
    # SigningTime
    signing_time = signed_props.find(f'.//{{{namespace}}}SigningTime')
    if signing_time is not None:
        info["signing_time"] = signing_time.text
    
    # SigningCertificate
    signing_cert = signed_props.find(f'.//{{{namespace}}}SigningCertificate')
    if signing_cert is not None:
        info["signing_certificate"] = _extraer_signing_certificate(signing_cert, namespace)
    
    # SignaturePolicyIdentifier
    sig_policy = signed_props.find(f'.//{{{namespace}}}SignaturePolicyIdentifier')
    if sig_policy is not None:
        info["signature_policy"] = _extraer_politica_firma(sig_policy, namespace)
    
    # DataObjectFormat
    data_obj_formats = signed_props.findall(f'.//{{{namespace}}}DataObjectFormat')
    for dof in data_obj_formats:
        format_info = {
            "object_reference": dof.get("ObjectReference", ""),
            "mime_type": "",
            "encoding": ""
        }
        
        mime_type = dof.find(f'.//{{{namespace}}}MimeType')
        if mime_type is not None:
            format_info["mime_type"] = mime_type.text or ""
        
        encoding = dof.find(f'.//{{{namespace}}}Encoding')
        if encoding is not None:
            format_info["encoding"] = encoding.text or ""
        
        info["data_object_format"].append(format_info)
    
    return info


def _extraer_signing_certificate(signing_cert: ET.Element, namespace: str) -> Dict[str, Any]:
    """Extrae información del certificado de firma"""
    info = {
        "cert_digest": "",
        "issuer_serial": {}
    }
    
    # CertDigest
    cert_digest = signing_cert.find(f'.//{{{namespace}}}CertDigest')
    if cert_digest is not None:
        digest_method = cert_digest.find(f'.//{{{namespace}}}DigestMethod')
        if digest_method is not None:
            info["digest_method"] = digest_method.get("Algorithm", "unknown")
        
        digest_value = cert_digest.find(f'.//{{{namespace}}}DigestValue')
        if digest_value is not None:
            info["cert_digest"] = digest_value.text or ""
    
    # IssuerSerial
    issuer_serial = signing_cert.find(f'.//{{{namespace}}}IssuerSerial')
    if issuer_serial is not None:
        # X509IssuerName
        issuer_name = issuer_serial.find(f'.//{{{namespace}}}X509IssuerName')
        if issuer_name is not None:
            info["issuer_serial"]["issuer_name"] = issuer_name.text or ""
        
        # X509SerialNumber
        serial_number = issuer_serial.find(f'.//{{{namespace}}}X509SerialNumber')
        if serial_number is not None:
            info["issuer_serial"]["serial_number"] = serial_number.text or ""
    
    return info


def _extraer_unsigned_properties(unsigned_props: ET.Element, namespace: str) -> Dict[str, Any]:
    """Extrae UnsignedProperties"""
    info = {
        "timestamps": [],
        "revocation_values": [],
        "archive_timestamps": []
    }
    
    # UnsignedSignatureProperties
    unsigned_sig_props = unsigned_props.find(f'.//{{{namespace}}}UnsignedSignatureProperties')
    if unsigned_sig_props is not None:
        # Timestamps
        timestamps = unsigned_sig_props.findall(f'.//{{{namespace}}}EncapsulatedTimeStamp')
        for ts in timestamps:
            info["timestamps"].append({
                "tipo": "timestamp",
                "contenido": ts.text,
                "encoding": ts.get("Encoding", "base64")
            })
        
        # RevocationValues
        revoc_values = unsigned_sig_props.findall(f'.//{{{namespace}}}RevocationValues')
        for rv in revoc_values:
            info["revocation_values"].append({
                "tipo": "revocation",
                "contenido": rv.text,
                "encoding": rv.get("Encoding", "base64")
            })
        
        # ArchiveTimestamps
        archive_timestamps = unsigned_sig_props.findall(f'.//{{{namespace}}}ArchiveTimeStamp')
        for ats in archive_timestamps:
            info["archive_timestamps"].append({
                "tipo": "archive_timestamp",
                "contenido": ats.text,
                "encoding": ats.get("Encoding", "base64")
            })
    
    return info


def _validar_firma_xades(firma: Dict[str, Any], xml_content: str) -> Dict[str, Any]:
    """
    Valida una firma XAdES individual.
    
    Args:
        firma: Información de la firma
        xml_content: Contenido XML completo
        
    Returns:
        Resultado de validación de la firma
    """
    resultado = {
        "valida": False,
        "tipo": "xades",
        "metadatos": firma.get("metadatos", {}),
        "certificados": firma.get("certificados", []),
        "timestamps": firma.get("timestamps", []),
        "politicas": firma.get("politicas", []),
        "errores": [],
        "advertencias": []
    }
    
    try:
        # Validar estructura básica
        if not firma.get("metadatos", {}).get("signed_info"):
            resultado["errores"].append("No se encontró SignedInfo")
            return resultado
        
        # Validar certificados
        if not firma.get("certificados"):
            resultado["advertencias"].append("No se encontraron certificados")
        else:
            # Validar cada certificado
            for cert in firma["certificados"]:
                if not _validar_certificado_x509(cert):
                    resultado["advertencias"].append(f"Certificado inválido: {cert.get('subject', {}).get('common_name', 'Unknown')}")
        
        # Validar timestamps
        if not firma.get("timestamps"):
            resultado["advertencias"].append("No se encontraron timestamps")
        
        # Validar políticas
        if not firma.get("politicas"):
            resultado["advertencias"].append("No se encontraron políticas de firma")
        
        # Si no hay errores críticos, considerar válida
        if not resultado["errores"]:
            resultado["valida"] = True
        
    except Exception as e:
        resultado["errores"].append(f"Error en validación: {str(e)}")
    
    return resultado


def _validar_certificado_x509(cert: Dict[str, Any]) -> bool:
    """Valida un certificado X.509"""
    try:
        # Verificar fechas de validez
        not_before = cert.get("not_before", "")
        not_after = cert.get("not_after", "")
        
        if not_before and not_after:
            # Verificar si el certificado está en su período de validez
            now = datetime.now()
            try:
                if isinstance(not_before, str):
                    not_before_dt = datetime.fromisoformat(not_before.replace('Z', '+00:00'))
                else:
                    not_before_dt = not_before
                
                if isinstance(not_after, str):
                    not_after_dt = datetime.fromisoformat(not_after.replace('Z', '+00:00'))
                else:
                    not_after_dt = not_after
                
                if now < not_before_dt or now > not_after_dt:
                    return False
            except Exception:
                return False
        
        # Verificar que tenga información básica
        if not cert.get("subject", {}).get("common_name"):
            return False
        
        return True
        
    except Exception:
        return False


def _calcular_resumen_xades(firmas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcula resumen de validación XAdES"""
    total = len(firmas)
    validas = sum(1 for f in firmas if f.get("valida", False))
    con_certificados = sum(1 for f in firmas if f.get("certificados"))
    con_timestamps = sum(1 for f in firmas if f.get("timestamps"))
    con_politicas = sum(1 for f in firmas if f.get("politicas"))
    
    return {
        "total_firmas": total,
        "firmas_validas": validas,
        "firmas_invalidas": total - validas,
        "con_certificados": con_certificados,
        "con_timestamps": con_timestamps,
        "con_politicas": con_politicas,
        "porcentaje_validas": (validas / total * 100) if total > 0 else 0
    }


def generar_reporte_xades(validacion_result: Dict[str, Any]) -> str:
    """
    Genera un reporte legible de la validación XAdES.
    
    Args:
        validacion_result: Resultado de validar_xades
        
    Returns:
        Reporte en texto legible
    """
    if not validacion_result.get('firma_detectada'):
        return "❌ No se detectaron firmas XAdES en el documento"
    
    report = []
    report.append("🔐 ANÁLISIS DE FIRMAS XAdES")
    report.append("=" * 50)
    
    resumen = validacion_result.get('resumen', {})
    report.append(f"📊 RESUMEN:")
    report.append(f"   Total de firmas: {resumen.get('total_firmas', 0)}")
    report.append(f"   Firmas válidas: {resumen.get('firmas_validas', 0)}")
    report.append(f"   Con certificados: {resumen.get('con_certificados', 0)}")
    report.append(f"   Con timestamps: {resumen.get('con_timestamps', 0)}")
    report.append(f"   Con políticas: {resumen.get('con_politicas', 0)}")
    report.append(f"   Porcentaje válidas: {resumen.get('porcentaje_validas', 0):.1f}%")
    report.append("")
    
    # Detalles por firma
    for i, firma in enumerate(validacion_result.get('firmas', []), 1):
        report.append(f"🔍 FIRMA XAdES {i}:")
        
        if firma.get('valida'):
            report.append("   ✅ Estado: VÁLIDA")
        else:
            report.append("   ❌ Estado: INVÁLIDA")
        
        # Metadatos
        metadatos = firma.get('metadatos', {})
        if metadatos.get('signed_info'):
            si = metadatos['signed_info']
            if si.get('signature_method'):
                report.append(f"   🔐 Algoritmo: {si['signature_method']}")
            if si.get('canonicalization_method'):
                report.append(f"   📝 Canonicalización: {si['canonicalization_method']}")
        
        # Certificados
        certificados = firma.get('certificados', [])
        if certificados:
            report.append(f"   📜 Certificados: {len(certificados)}")
            for j, cert in enumerate(certificados, 1):
                subject = cert.get('subject', {})
                if subject.get('common_name'):
                    report.append(f"      {j}. {subject['common_name']}")
                    if subject.get('organization'):
                        report.append(f"         Organización: {subject['organization']}")
                    if subject.get('country'):
                        report.append(f"         País: {subject['country']}")
        
        # Timestamps
        timestamps = firma.get('timestamps', [])
        if timestamps:
            report.append(f"   ⏰ Timestamps: {len(timestamps)}")
        
        # Políticas
        politicas = firma.get('politicas', [])
        if politicas:
            report.append(f"   📋 Políticas: {len(politicas)}")
            for policy in politicas:
                if policy.get('identificador'):
                    report.append(f"      - {policy['identificador']}")
        
        # Errores y advertencias
        if firma.get('errores'):
            report.append("   ❌ Errores:")
            for error in firma['errores']:
                report.append(f"      - {error}")
        
        if firma.get('advertencias'):
            report.append("   ⚠️  Advertencias:")
            for warning in firma['advertencias']:
                report.append(f"      - {warning}")
        
        report.append("")
    
    # Dependencias
    deps = validacion_result.get('dependencias', {})
    if not all(deps.values()):
        report.append("⚠️  DEPENDENCIAS FALTANTES:")
        if not deps.get('asn1crypto'):
            report.append("   - asn1crypto: Para análisis de certificados")
        if not deps.get('oscrypto'):
            report.append("   - oscrypto: Para verificación criptográfica")
        if not deps.get('certvalidator'):
            report.append("   - certvalidator: Para validación de cadena")
        report.append("")
    
    return "\n".join(report)
