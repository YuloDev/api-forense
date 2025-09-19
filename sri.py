# sri.py
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Tuple, Any, List
from zeep import Client
from zeep.transports import Transport
try:
    from zeep.helpers import serialize_object as zeep_serialize
except Exception:
    zeep_serialize = None  # fallback simple

# Config externos (si no existen, usa defaults productivos seguros)
try:
    from config import SRI_WSDL, SRI_TIMEOUT
except Exception:
    SRI_WSDL = "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"
    SRI_TIMEOUT = 30.0

# Si tienes utils._to_float lo importas; si no, define uno simple aquí
try:
    from utils import _to_float
except Exception:
    def _to_float(val) -> Optional[float]:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        if not s:
            return None
        # Normaliza coma/punto y separadores de miles
        if "," in s and "." in s:
            last_comma = s.rfind(",")
            last_dot = s.rfind(".")
            if last_comma > last_dot:
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        else:
            if s.count(",") == 1 and s.count(".") == 0:
                s = s.replace(",", ".")
            elif s.count(".") > 1 and s.count(",") == 0:
                s = s.replace(".", "")
        try:
            return float(s)
        except Exception:
            return None

# ------------------------------------------------------------
# 1) Validación interna de clave de acceso (módulo 11 + estructura)
# ------------------------------------------------------------
def _clave_es_numerica(clave: str) -> bool:
    return clave.isdigit()

def _dv_mod11(clave_sin_dv: str) -> int:
    """Calcula DV (módulo 11) con pesos 2..7 repetidos desde la derecha."""
    pesos = [2, 3, 4, 5, 6, 7]
    total, p = 0, 0
    for d in reversed(clave_sin_dv):
        total += int(d) * pesos[p]
        p = (p + 1) % len(pesos)
    mod = total % 11
    calc = 11 - mod
    if calc == 11:
        return 0
    if calc == 10:
        return 1
    return calc

def descomponer_clave_acceso(clave: str) -> Dict[str, str]:
    """
    Estructura (49 dígitos), según SRI:
      1-8   : fecha (ddmmaaaa)
      9-10  : codDoc
      11-23 : RUC emisor (13)
      24    : ambiente (1: pruebas, 2: prod)
      25-30 : serie (estab+ptoEmi, 6)
      31-39 : secuencial (9)
      40-47 : código numérico (8)
      48    : tipoEmision (1)
      49    : dígito verificador (1)
    """
    return {
        "fecha": clave[0:8],
        "codDoc": clave[8:10],
        "ruc": clave[10:23],
        "ambiente": clave[23:24],
        "serie": clave[24:30],
        "secuencial": clave[30:39],
        "codigoNumerico": clave[39:47],
        "tipoEmision": clave[47:48],
        "dv": clave[48:49],
    }

def validar_clave_acceso_interna(clave: str) -> Tuple[bool, str, Dict[str, Any]]:
    detalles: Dict[str, Any] = {
        "longitud": len(clave),
        "formato_numerico": _clave_es_numerica(clave),
        "validaciones": []
    }
    if len(clave) != 49:
        return False, "La clave de acceso debe tener 49 dígitos.", detalles
    if not _clave_es_numerica(clave):
        return False, "La clave de acceso debe ser numérica.", detalles

    estr = descomponer_clave_acceso(clave)
    detalles["estructura"] = estr

    dv_real = int(estr["dv"])
    dv_calc = _dv_mod11(clave[:-1])
    detalles["validaciones"].append({"dv_calculado": dv_calc, "dv_en_clave": dv_real})

    if dv_real != dv_calc:
        return False, "Dígito verificador inválido (módulo 11).", detalles

    # Checks básicos adicionales (opcionales)
    if estr["ambiente"] not in ("1", "2"):
        detalles["validaciones"].append({"ambiente": "valor_no_estandar"})
    return True, "Clave válida (estructura y DV correctos).", detalles

# ------------------------------------------------------------
# 2) XML -> JSON (igual a tu lógica, con pequeños guardas)
# ------------------------------------------------------------
def factura_xml_to_json(xml_str: str) -> Dict[str, Any]:
    """Convierte el XML de factura del SRI en un dict JSON."""
    # Algunos servicios devuelven CDATA; garantizar str
    xml_str = xml_str if isinstance(xml_str, str) else str(xml_str)
    root = ET.fromstring(xml_str.encode("utf-8"))

    info_trib: Dict[str, Any] = {}
    it = root.find("infoTributaria")
    if it is not None:
        def tx(tag: str) -> Optional[str]:
            v = it.findtext(tag)
            return v.strip() if isinstance(v, str) else v
        info_trib = {
            "ambiente": tx("ambiente"),
            "tipoEmision": tx("tipoEmision"),
            "razonSocial": tx("razonSocial"),
            "nombreComercial": tx("nombreComercial"),
            "ruc": tx("ruc"),
            "claveAcceso": tx("claveAcceso"),
            "codDoc": tx("codDoc"),
            "estab": tx("estab"),
            "ptoEmi": tx("ptoEmi"),
            "secuencial": tx("secuencial"),
            "dirMatriz": tx("dirMatriz"),
            "agenteRetencion": tx("agenteRetencion"),
        }

    info_fact: Dict[str, Any] = {}
    inf = root.find("infoFactura")
    if inf is not None:
        def fx(tag: str) -> Optional[str]:
            v = inf.findtext(tag)
            return v.strip() if isinstance(v, str) else v

        total_con_imps: List[Dict[str, Any]] = []
        tci = inf.find("totalConImpuestos")
        if tci is not None:
            for ti in tci.findall("totalImpuesto"):
                total_con_imps.append({
                    "codigo": (ti.findtext("codigo") or "").strip(),
                    "codigoPorcentaje": (ti.findtext("codigoPorcentaje") or "").strip(),
                    "baseImponible": _to_float(ti.findtext("baseImponible")),
                    "valor": _to_float(ti.findtext("valor")),
                })

        pagos_out: List[Dict[str, Any]] = []
        pagos = inf.find("pagos")
        if pagos is not None:
            for p in pagos.findall("pago"):
                pagos_out.append({
                    "formaPago": (p.findtext("formaPago") or "").strip(),
                    "total": _to_float(p.findtext("total")),
                    "plazo": (p.findtext("plazo") or "").strip(),
                    "unidadTiempo": (p.findtext("unidadTiempo") or "").strip(),
                })

        info_fact = {
            "fechaEmision": fx("fechaEmision"),
            "dirEstablecimiento": fx("dirEstablecimiento"),
            "obligadoContabilidad": fx("obligadoContabilidad"),
            "tipoIdentificacionComprador": fx("tipoIdentificacionComprador"),
            "razonSocialComprador": fx("razonSocialComprador"),
            "identificacionComprador": fx("identificacionComprador"),
            "direccionComprador": fx("direccionComprador"),
            "totalSinImpuestos": _to_float(inf.findtext("totalSinImpuestos")),
            "totalDescuento": _to_float(inf.findtext("totalDescuento")),
            "totalConImpuestos": total_con_imps,
            "propina": _to_float(inf.findtext("propina")),
            "importeTotal": _to_float(inf.findtext("importeTotal")),
            "moneda": fx("moneda"),
            "pagos": pagos_out,
        }

    detalles_out: List[Dict[str, Any]] = []
    dets = root.find("detalles")
    if dets is not None:
        for d in dets.findall("detalle"):
            imp_list: List[Dict[str, Any]] = []
            imps = d.find("impuestos")
            if imps is not None:
                for imp in imps.findall("impuesto"):
                    imp_list.append({
                        "codigo": (imp.findtext("codigo") or "").strip(),
                        "codigoPorcentaje": (imp.findtext("codigoPorcentaje") or "").strip(),
                        "tarifa": _to_float(imp.findtext("tarifa")),
                        "baseImponible": _to_float(imp.findtext("baseImponible")),
                        "valor": _to_float(imp.findtext("valor")),
                    })
            detalles_out.append({
                "codigoPrincipal": (d.findtext("codigoPrincipal") or "").strip(),
                "codigoAuxiliar": (d.findtext("codigoAuxiliar") or "").strip(),
                "descripcion": (d.findtext("descripcion") or "").strip(),
                "cantidad": _to_float(d.findtext("cantidad")),
                "precioUnitario": _to_float(d.findtext("precioUnitario")),
                "descuento": _to_float(d.findtext("descuento")),
                "precioTotalSinImpuesto": _to_float(d.findtext("precioTotalSinImpuesto")),
                "impuestos": imp_list,
            })

    info_adic: Dict[str, Any] = {}
    ia = root.find("infoAdicional")
    if ia is not None:
        for c in ia.findall("campoAdicional"):
            nombre = c.attrib.get("nombre")
            valor = (c.text or "").strip()
            if nombre:
                info_adic[nombre] = valor

    return {
        "infoTributaria": info_trib,
        "infoFactura": info_fact,
        "detalles": detalles_out,
        "infoAdicional": info_adic,
    }

# ------------------------------------------------------------
# 3) Cliente SRI + parseo robusto
# ------------------------------------------------------------
def sri_autorizacion_por_clave(clave: str, timeout: float = SRI_TIMEOUT):
    """
    Consulta la autorización del comprobante en el SRI por clave de acceso.
    Devuelve: (autorizado: bool, estado: str, xml_comprobante: Optional[str], raw_normalizado: dict)
    """
    try:
        session = requests.Session()
        transport = Transport(session=session, timeout=timeout)
        client = Client(wsdl=SRI_WSDL, transport=transport)
        resp = client.service.autorizacionComprobante(clave)
        return parse_autorizacion_response(resp)
    except Exception as e:
        print(f"[DEBUG SRI] Error en sri_autorizacion_por_clave: {e}")
        return False, f"ERROR_SRI: {str(e)}", None, {"error": str(e)}

def _serialize_zeep(obj) -> Dict[str, Any]:
    """Convierte objetos zeep a dict, con fallback."""
    if zeep_serialize is not None:
        try:
            return zeep_serialize(obj)
        except Exception:
            pass
    # Fallback muy simple
    try:
        return dict(obj)
    except Exception:
        return {"_repr": str(obj)}

def parse_autorizacion_response(resp) -> Tuple[bool, str, Optional[str], Dict]:
    """
    Procesa la respuesta del servicio de autorización SRI.
    Devuelve: (autorizado: bool, estado: str, xml_comprobante: Optional[str], raw_normalizado: dict)
    - 'autorizado' True si alguna autorización viene con estado 'AUTORIZADO'
    - 'xml_comprobante' es el nodo 'comprobante' del primer autorizado (o el primero disponible)
    """
    try:
        # Normaliza toda la respuesta a dict
        raw_dict = _serialize_zeep(resp)
        print(f"[DEBUG SRI] Raw dict después de serializar: {raw_dict}")

        # Estructura esperada:
        # { 'claveAccesoConsultada': ..., 'numeroComprobantes': ..., 'autorizaciones': { 'autorizacion': [...] } }
        clave = raw_dict.get("claveAccesoConsultada")
        ncomp = raw_dict.get("numeroComprobantes")
        print(f"[DEBUG SRI] Clave consultada: {clave}, Número comprobantes: {ncomp}")

        auts = raw_dict.get("autorizaciones") or {}
        print(f"[DEBUG SRI] Sección autorizaciones: {auts}")
        
        aut_list = auts.get("autorizacion")
        if aut_list and not isinstance(aut_list, list):
            aut_list = [aut_list]
        aut_list = aut_list or []
        print(f"[DEBUG SRI] Lista de autorizaciones procesada: {len(aut_list)} elementos")

        raw_auts: List[Dict[str, Any]] = []
        xml = None
        estado_global = ""
        autorizado = False

        for i, a in enumerate(aut_list):
            # cada 'a' es dict ya serializado
            estado = (a.get("estado") or "").strip()
            print(f"[DEBUG SRI] Autorización {i}: estado='{estado}', tipo={type(a)}")
            print(f"[DEBUG SRI] Autorización {i} completa: {a}")
            
            estado_global = estado_global or estado  # guarda el primero visto
            d = {
                "estado": estado,
                "numeroAutorizacion": a.get("numeroAutorizacion"),
                "fechaAutorizacion": str(a.get("fechaAutorizacion")),
                "ambiente": a.get("ambiente"),
            }
            raw_auts.append(d)
            
            # Verificar si está autorizado (case insensitive y variaciones)
            estado_normalizado = estado.upper().strip()
            estados_validos = ["AUTORIZADO", "AUTHORIZED", "VIGENTE", "VALID"]
            
            if estado_normalizado in estados_validos:
                print(f"[DEBUG SRI] ENCONTRADO estado válido '{estado}' (normalizado: '{estado_normalizado}') en autorización {i}")
                autorizado = True
                xml = a.get("comprobante")
                if xml:
                    print(f"[DEBUG SRI] XML comprobante obtenido (longitud: {len(str(xml))})")
                else:
                    print(f"[DEBUG SRI] ADVERTENCIA: Estado {estado} pero sin XML comprobante")
            else:
                print(f"[DEBUG SRI] Estado no válido: '{estado}' (normalizado: '{estado_normalizado}')")

        # Si no encontramos ningún AUTORIZADO, verificar si hay comprobantes para debug
        if not autorizado and aut_list:
            print(f"[DEBUG SRI] No hay estados AUTORIZADO. Buscando primer comprobante para debug...")
            for i, a in enumerate(aut_list):
                if a.get("comprobante"):
                    xml = a.get("comprobante")
                    print(f"[DEBUG SRI] Tomando XML de autorización {i} para debug")
                    break

        print(f"[DEBUG SRI] Resultado final: autorizado={autorizado}, estado_global='{estado_global}'")

        raw = {
            "claveAccesoConsultada": clave,
            "numeroComprobantes": ncomp,
            "autorizaciones": raw_auts
        }
        
        resultado_estado = estado_global if estado_global else ("AUTORIZADO" if autorizado else "SIN_ESTADO")
        print(f"[DEBUG SRI] Retornando: autorizado={autorizado}, estado='{resultado_estado}'")
        
        return autorizado, resultado_estado, xml, raw

    except Exception as e:
        print(f"[DEBUG SRI] ERROR en parse_autorizacion_response: {e}")
        print(f"[DEBUG SRI] Tipo de respuesta recibida: {type(resp)}")
        
        # Fallback: intenta al menos repr
        try:
            raw = dict(resp)  # puede fallar
        except Exception as e2:
            print(f"[DEBUG SRI] Error en fallback dict(): {e2}")
            raw = {"_repr": str(resp), "_error": str(e)}
        return False, f"ERROR_PARSING: {str(e)}", None, raw
