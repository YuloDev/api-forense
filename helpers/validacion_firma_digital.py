"""
Módulo para validación completa de firmas digitales en PDFs.

Implementa:
1. Detección de todas las firmas del PDF
2. Cálculo del hash de los rangos /ByteRange
3. Extracción y parseo del CMS de /Contents
4. Comparación del hash con messageDigest firmado (integridad real)
5. Extracción de datos del firmante, algoritmo, fechas
6. Detección de modificaciones posteriores a la firma
7. Validación criptográfica opcional de la firma
8. Validación de cadena de confianza opcional

Autor: Sistema de Análisis Forense
Versión: 1.0
"""

import re
import binascii
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import base64

try:
    from asn1crypto import cms, x509, algos
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


def _map_hash_oid(oid: str) -> str:
    """
    Mapea OID de algoritmo hash a nombre de hashlib.
    
    Args:
        oid: OID del algoritmo hash
        
    Returns:
        Nombre del algoritmo para hashlib
    """
    hash_oid_map = {
        '1.3.14.3.2.26': 'sha1',
        '2.16.840.1.101.3.4.2.1': 'sha256',
        '2.16.840.1.101.3.4.2.2': 'sha384',
        '2.16.840.1.101.3.4.2.3': 'sha512',
        '2.16.840.1.101.3.4.2.4': 'sha224',
        '2.16.840.1.101.3.4.2.5': 'sha512_224',
        '2.16.840.1.101.3.4.2.6': 'sha512_256',
    }
    return hash_oid_map.get(str(oid), 'sha256')


def _map_signature_oid(oid: str) -> str:
    """
    Mapea OID de algoritmo de firma a nombre descriptivo.
    
    Args:
        oid: OID del algoritmo de firma
        
    Returns:
        Nombre descriptivo del algoritmo
    """
    sig_oid_map = {
        '1.2.840.113549.1.1.1': 'RSA',
        '1.2.840.113549.1.1.11': 'RSA-SHA256',
        '1.2.840.113549.1.1.12': 'RSA-SHA384',
        '1.2.840.113549.1.1.13': 'RSA-SHA512',
        '1.2.840.113549.1.1.10': 'RSA-PSS',
        '1.2.840.10045.4.3.2': 'ECDSA-SHA256',
        '1.2.840.10045.4.3.3': 'ECDSA-SHA384',
        '1.2.840.10045.4.3.4': 'ECDSA-SHA512',
    }
    return sig_oid_map.get(str(oid), f'Unknown ({oid})')


def _find_signatures(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Encuentra todas las parejas ByteRange/Contents en el PDF.
    
    Args:
        pdf_bytes: Contenido del PDF en bytes
        
    Returns:
        Lista de firmas encontradas con sus datos
    """
    text = pdf_bytes.decode('latin-1', errors='ignore')
    sigs = []
    
    # Buscar patrones de ByteRange
    for m in re.finditer(r'/ByteRange\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]', text):
        br = tuple(map(int, m.groups()))
        
        # Buscar Contents después del ByteRange
        after = text[m.end(): m.end()+20000]
        m_contents = re.search(r'/Contents\s*<([0-9A-Fa-f\s]+)>', after)
        
        if not m_contents:
            # Buscar antes del ByteRange
            before = text[max(0, m.start()-20000): m.start()]
            m_contents = re.search(r'/Contents\s*<([0-9A-Fa-f\s]+)>', before)
        
        if not m_contents:
            continue
            
        hex_sig = m_contents.group(1).replace(' ', '').replace('\n', '')
        try:
            der = binascii.unhexlify(hex_sig)
        except Exception:
            continue

        # Buscar SubFilter (tipo de firma)
        around = text[max(0, m.start()-2000): m.end()+2000]
        m_sub = re.search(r'/SubFilter\s*/([A-Za-z0-9\.\-]+)', around)
        subfilter = m_sub.group(1) if m_sub else None
        
        # Detectar PAdES específicamente
        es_pades = False
        if subfilter:
            subfilter_lower = subfilter.lower()
            if any(pades_indicator in subfilter_lower for pades_indicator in [
                'etsi.cades', 'etsi.cades.detached', 'etsi.cades.bes', 
                'etsi.cades.epes', 'etsi.cades.t', 'etsi.cades.c', 
                'etsi.cades.x', 'etsi.cades.xl', 'etsi.cades.a',
                'pades', 'cades'
            ]):
                es_pades = True
        
        # Buscar Location (ubicación)
        m_loc = re.search(r'/Location\s*\(([^)]+)\)', around)
        location = m_loc.group(1) if m_loc else None
        
        # Buscar Reason (razón)
        m_reason = re.search(r'/Reason\s*\(([^)]+)\)', around)
        reason = m_reason.group(1) if m_reason else None
        
        # Buscar Name (nombre del firmante)
        m_name = re.search(r'/Name\s*\(([^)]+)\)', around)
        name = m_name.group(1) if m_name else None

        sigs.append({
            'byte_range': br,
            'contents_der': der,
            'subfilter': subfilter,
            'es_pades': es_pades,
            'location': location,
            'reason': reason,
            'name': name
        })
    
    return sigs


def _doc_digest_for_byterange(pdf_bytes: bytes, br: tuple, algo_name: str) -> bytes:
    """
    Calcula el hash del documento según el ByteRange.
    
    Args:
        pdf_bytes: Contenido del PDF
        br: ByteRange (start1, len1, start2, len2)
        algo_name: Nombre del algoritmo hash
        
    Returns:
        Hash calculado
    """
    s1, l1, s2, l2 = br
    h = hashlib.new(algo_name)
    h.update(pdf_bytes[s1:s1+l1])
    h.update(pdf_bytes[s2:s2+l2])
    return h.digest()


def _verify_cryptographic_signature(signer_info, signed_attrs_der: bytes, 
                                  signer_cert, algo_name: str) -> Dict[str, Any]:
    """
    Verifica la firma criptográfica usando oscrypto.
    
    Args:
        signer_info: Información del firmante del CMS
        signed_attrs_der: Atributos firmados en DER
        signer_cert: Certificado del firmante
        algo_name: Nombre del algoritmo hash
        
    Returns:
        Resultado de la verificación criptográfica
    """
    if not OSCRYPTO_AVAILABLE:
        return {
            'crypto_verification': False,
            'crypto_error': 'oscrypto no disponible'
        }
    
    try:
        # Obtener algoritmo de firma
        sig_algo = signer_info['signature_algorithm']
        sig_algo_oid = sig_algo['algorithm'].dotted
        sig_algo_name = _map_signature_oid(sig_algo_oid)
        
        # Obtener clave pública del certificado
        public_key = signer_cert.public_key
        
        # Obtener firma
        signature = signer_info['signature'].native
        
        # Verificar según el tipo de algoritmo
        if 'RSA' in sig_algo_name:
            if 'PSS' in sig_algo_name:
                # RSA-PSS
                mgf1_algo = sig_algo['parameters']['hash_algorithm']['algorithm'].dotted
                salt_length = sig_algo['parameters']['salt_length'].native
                
                result = oscrypto.asymmetric.rsa_pss_verify(
                    public_key, signature, signed_attrs_der, 
                    mgf1_algo, salt_length
                )
            else:
                # RSA PKCS#1 v1.5
                result = oscrypto.asymmetric.rsa_pkcs1v15_verify(
                    public_key, signature, signed_attrs_der, algo_name
                )
        elif 'ECDSA' in sig_algo_name:
            # ECDSA
            result = oscrypto.asymmetric.ecdsa_verify(
                public_key, signature, signed_attrs_der, algo_name
            )
        else:
            return {
                'crypto_verification': False,
                'crypto_error': f'Algoritmo no soportado: {sig_algo_name}'
            }
        
        return {
            'crypto_verification': result,
            'signature_algorithm': sig_algo_name,
            'crypto_error': None
        }
        
    except Exception as e:
        return {
            'crypto_verification': False,
            'crypto_error': f'Error en verificación criptográfica: {str(e)}'
        }


def _validate_certificate_chain(signer_cert, intermediate_certs: List) -> Dict[str, Any]:
    """
    Valida la cadena de certificados usando certvalidator.
    
    Args:
        signer_cert: Certificado del firmante
        intermediate_certs: Certificados intermedios
        
    Returns:
        Resultado de la validación de cadena
    """
    if not CERTVALIDATOR_AVAILABLE:
        return {
            'chain_validation': False,
            'chain_error': 'certvalidator no disponible'
        }
    
    try:
        # Cargar raíces de confianza de Mozilla
        roots = []
        with open(certifi.where(), 'rb') as f:
            pem_data = f.read()
        
        # Dividir PEM concatenado
        for m in re.finditer(b'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', 
                           pem_data, re.DOTALL):
            try:
                cert = x509.Certificate.load(m.group(0))
                roots.append(cert)
            except Exception:
                continue
        
        if not roots:
            return {
                'chain_validation': False,
                'chain_error': 'No se pudieron cargar certificados raíz'
            }
        
        # Crear contexto de validación
        vc = ValidationContext(
            trust_roots=roots, 
            allow_fetching=True,  # Para OCSP/CRL
            revocation_mode='soft-fail'  # No fallar si no se puede verificar revocación
        )
        
        # Validar cadena
        validator = CertificateValidator(
            signer_cert, 
            intermediate_certs=intermediate_certs, 
            validation_context=vc
        )
        
        path = validator.validate_usage(set())
        
        return {
            'chain_validation': True,
            'validation_path': [cert.subject.native.get('common_name', 'Unknown') 
                              for cert in path],
            'chain_error': None
        }
        
    except Exception as e:
        return {
            'chain_validation': False,
            'chain_error': f'Error en validación de cadena: {str(e)}'
        }


def validate_pdf_signatures(pdf_bytes: bytes, 
                          verify_crypto: bool = False,
                          verify_chain: bool = False) -> Dict[str, Any]:
    """
    Valida todas las firmas digitales en un PDF.
    
    Args:
        pdf_bytes: Contenido del PDF en bytes
        verify_crypto: Si verificar la firma criptográfica
        verify_chain: Si verificar la cadena de certificados
        
    Returns:
        Dict con resultado completo de validación
    """
    result = {
        'firma_detectada': False,
        'firmas': [],
        'resumen': {
            'total_firmas': 0,
            'firmas_validas': 0,
            'firmas_integridad_ok': 0,
            'firmas_sin_modificaciones': 0,
            'firmas_crypto_ok': 0,
            'firmas_chain_ok': 0,
            'firmas_pades': 0
        },
        'dependencias': {
            'asn1crypto': ASN1_AVAILABLE,
            'oscrypto': OSCRYPTO_AVAILABLE,
            'certvalidator': CERTVALIDATOR_AVAILABLE
        }
    }
    
    # Buscar firmas
    sigs = _find_signatures(pdf_bytes)
    if not sigs:
        return safe_serialize_dict(result)
    
    result['firma_detectada'] = True
    result['resumen']['total_firmas'] = len(sigs)
    
    for i, s in enumerate(sigs):
        item = {
            'indice': i + 1,
            'subfilter': s.get('subfilter'),
            'es_pades': s.get('es_pades', False),
            'location': s.get('location'),
            'reason': s.get('reason'),
            'name': s.get('name'),
            'hash_algoritmo': None,
            'message_digest_match': False,
            'doc_modified_after_signature': None,
            'signing_time': None,
            'signer_common_name': None,
            'issuer_common_name': None,
            'cert_not_before': None,
            'cert_not_after': None,
            'crypto_verification': None,
            'chain_validation': None,
            'observaciones': []
        }
        
        # Verificar si hubo modificaciones después de la firma
        s1, l1, s2, l2 = s['byte_range']
        end_covered = s2 + l2
        item['doc_modified_after_signature'] = ensure_python_bool(end_covered != len(pdf_bytes))
        
        if not ASN1_AVAILABLE:
            item['observaciones'].append('Instala asn1crypto para analizar el CMS de Contents')
            result['firmas'].append(item)
            continue
        
        try:
            # Parsear CMS
            ci = cms.ContentInfo.load(s['contents_der'])
            sd = ci['content']
            
            # Obtener algoritmo hash
            algo_oid = None
            if len(sd['digest_algorithms']) > 0:
                algo_oid = sd['digest_algorithms'][0]['algorithm'].dotted
            algo_name = _map_hash_oid(algo_oid or '')
            item['hash_algoritmo'] = algo_name
            
            # Obtener información del firmante
            si = sd['signer_infos'][0]
            attrs = si['signed_attrs']
            
            # Buscar signing-time
            try:
                st = next(a for a in attrs if a['type'].native == 'signing_time')
                dt = st['values'][0].native
                if isinstance(dt, datetime):
                    item['signing_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            except StopIteration:
                pass
            
            # Verificar messageDigest
            try:
                md = next(a for a in attrs if a['type'].native == 'message_digest')['values'][0].native
                doc_digest = _doc_digest_for_byterange(pdf_bytes, s['byte_range'], algo_name)
                item['message_digest_match'] = ensure_python_bool(md == doc_digest)
            except StopIteration:
                item['observaciones'].append('No se encontró messageDigest en atributos firmados')
            
            # Obtener certificados
            certs = [c.chosen for c in sd['certificates']] if sd['certificates'] is not None else []
            
            # Buscar certificado del firmante
            signer_sid = si['sid'].chosen
            signer_cert = None
            for c in certs:
                if (c.issuer == signer_sid['issuer']) and (c.serial_number == signer_sid['serial_number'].native):
                    signer_cert = c
                    break
            if signer_cert is None and certs:
                signer_cert = certs[0]  # fallback
            
            if signer_cert:
                subj = signer_cert.subject.native
                issr = signer_cert.issuer.native
                item['signer_common_name'] = (subj.get('common_name') or 
                                            subj.get('organization_name') or 
                                            subj.get('email_address'))
                item['issuer_common_name'] = (issr.get('common_name') or 
                                            issr.get('organization_name'))
                
                try:
                    item['cert_not_before'] = signer_cert['tbs_certificate']['validity']['not_before'].native.strftime('%Y-%m-%d %H:%M:%S')
                    item['cert_not_after'] = signer_cert['tbs_certificate']['validity']['not_after'].native.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    item['observaciones'].append(f'Error extrayendo fechas del certificado: {e}')
                
                # Verificación criptográfica opcional
                if verify_crypto:
                    try:
                        signed_attrs_der = si['signed_attrs'].dump()
                        crypto_result = _verify_cryptographic_signature(
                            si, signed_attrs_der, signer_cert, algo_name
                        )
                        item['crypto_verification'] = crypto_result
                    except Exception as e:
                        item['crypto_verification'] = {
                            'crypto_verification': False,
                            'crypto_error': f'Error en verificación criptográfica: {e}'
                        }
                
                # Validación de cadena opcional
                if verify_chain:
                    try:
                        chain_result = _validate_certificate_chain(signer_cert, certs)
                        item['chain_validation'] = chain_result
                    except Exception as e:
                        item['chain_validation'] = {
                            'chain_validation': False,
                            'chain_error': f'Error en validación de cadena: {e}'
                        }
            else:
                item['observaciones'].append('No se encontró certificado del firmante')
                
        except Exception as e:
            item['observaciones'].append(f'Error procesando firma: {str(e)}')
        
        result['firmas'].append(item)
    
    # Calcular resumen
    for firma in result['firmas']:
        if firma.get('message_digest_match'):
            result['resumen']['firmas_integridad_ok'] += 1
        if not firma.get('doc_modified_after_signature'):
            result['resumen']['firmas_sin_modificaciones'] += 1
        if firma.get('crypto_verification', {}).get('crypto_verification'):
            result['resumen']['firmas_crypto_ok'] += 1
        if firma.get('chain_validation', {}).get('chain_validation'):
            result['resumen']['firmas_chain_ok'] += 1
        if firma.get('es_pades'):
            result['resumen']['firmas_pades'] += 1
    
    # Determinar firmas válidas (integridad + sin modificaciones)
    result['resumen']['firmas_validas'] = sum(
        1 for f in result['firmas'] 
        if f.get('message_digest_match') and not f.get('doc_modified_after_signature')
    )
    
    return safe_serialize_dict(result)


def detectar_firmas_pdf_simple(pdf_bytes: bytes) -> bool:
    """
    Detección simple de firmas digitales en PDF (sin análisis detallado).
    
    Args:
        pdf_bytes: Contenido del PDF en bytes
        
    Returns:
        True si el PDF tiene firmas digitales
    """
    try:
        text = pdf_bytes.decode('latin-1', errors='ignore')
        return bool(re.search(r'/ByteRange\s*\[', text))
    except Exception:
        return False


def generar_reporte_firmas(validacion_result: Dict[str, Any]) -> str:
    """
    Genera un reporte legible de la validación de firmas.
    
    Args:
        validacion_result: Resultado de validate_pdf_signatures
        
    Returns:
        Reporte en texto legible
    """
    if not validacion_result.get('firma_detectada'):
        return "❌ No se detectaron firmas digitales en el documento"
    
    report = []
    report.append("🔐 ANÁLISIS DE FIRMAS DIGITALES")
    report.append("=" * 50)
    
    resumen = validacion_result.get('resumen', {})
    report.append(f"📊 RESUMEN:")
    report.append(f"   Total de firmas: {resumen.get('total_firmas', 0)}")
    report.append(f"   Firmas válidas: {resumen.get('firmas_validas', 0)}")
    report.append(f"   Integridad OK: {resumen.get('firmas_integridad_ok', 0)}")
    report.append(f"   Sin modificaciones: {resumen.get('firmas_sin_modificaciones', 0)}")
    
    if resumen.get('firmas_pades', 0) > 0:
        report.append(f"   Firmas PAdES: {resumen.get('firmas_pades', 0)}")
    if resumen.get('firmas_crypto_ok', 0) > 0:
        report.append(f"   Verificación criptográfica OK: {resumen.get('firmas_crypto_ok', 0)}")
    if resumen.get('firmas_chain_ok', 0) > 0:
        report.append(f"   Cadena de certificados OK: {resumen.get('firmas_chain_ok', 0)}")
    
    report.append("")
    
    # Detalles por firma
    for i, firma in enumerate(validacion_result.get('firmas', []), 1):
        report.append(f"🔍 FIRMA {i}:")
        
        if firma.get('subfilter'):
            report.append(f"   Tipo: {firma['subfilter']}")
        if firma.get('es_pades'):
            report.append("   📋 Estándar: PAdES (PDF Advanced Electronic Signatures)")
        if firma.get('signer_common_name'):
            report.append(f"   Firmante: {firma['signer_common_name']}")
        if firma.get('issuer_common_name'):
            report.append(f"   Emisor: {firma['issuer_common_name']}")
        if firma.get('signing_time'):
            report.append(f"   Fecha: {firma['signing_time']}")
        if firma.get('hash_algoritmo'):
            report.append(f"   Algoritmo: {firma['hash_algoritmo']}")
        
        # Estado de validación
        if firma.get('message_digest_match'):
            report.append("   ✅ Integridad: VÁLIDA")
        else:
            report.append("   ❌ Integridad: INVÁLIDA")
        
        if firma.get('doc_modified_after_signature'):
            report.append("   ⚠️  Modificaciones posteriores: SÍ")
        else:
            report.append("   ✅ Modificaciones posteriores: NO")
        
        if firma.get('crypto_verification'):
            crypto = firma['crypto_verification']
            if crypto.get('crypto_verification'):
                report.append(f"   ✅ Verificación criptográfica: VÁLIDA ({crypto.get('signature_algorithm', 'Unknown')})")
            else:
                report.append(f"   ❌ Verificación criptográfica: INVÁLIDA ({crypto.get('crypto_error', 'Unknown error')})")
        
        if firma.get('chain_validation'):
            chain = firma['chain_validation']
            if chain.get('chain_validation'):
                report.append("   ✅ Cadena de certificados: VÁLIDA")
            else:
                report.append(f"   ❌ Cadena de certificados: INVÁLIDA ({chain.get('chain_error', 'Unknown error')})")
        
        if firma.get('observaciones'):
            report.append("   📝 Observaciones:")
            for obs in firma['observaciones']:
                report.append(f"      - {obs}")
        
        report.append("")
    
    # Dependencias
    deps = validacion_result.get('dependencias', {})
    if not all(deps.values()):
        report.append("⚠️  DEPENDENCIAS FALTANTES:")
        if not deps.get('asn1crypto'):
            report.append("   - asn1crypto: Para análisis detallado de CMS")
        if not deps.get('oscrypto'):
            report.append("   - oscrypto: Para verificación criptográfica")
        if not deps.get('certvalidator'):
            report.append("   - certvalidator: Para validación de cadena de certificados")
        report.append("")
    
    return "\n".join(report)
