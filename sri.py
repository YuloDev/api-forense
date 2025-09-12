import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Tuple, Any, List
from zeep import Client
from zeep.transports import Transport

from config import SRI_WSDL, SRI_TIMEOUT
from utils import _to_float

# ------------------------ SRI & XML --------------------
def factura_xml_to_json(xml_str: str) -> Dict[str, Any]:
    """Convierte el XML de factura del SRI en un dict JSON."""
    root = ET.fromstring(xml_str.encode("utf-8"))

    # Info tributaria
    it = root.find("infoTributaria")
    info_trib: Dict[str, Any] = {}
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

    # Info factura
    inf = root.find("infoFactura")
    info_fact: Dict[str, Any] = {}
    if inf is not None:
        def fx(tag: str) -> Optional[str]:
            v = inf.findtext(tag)
            return v.strip() if isinstance(v, str) else v

        # impuestos totales
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

        # pagos
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

    # Detalles
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

    # Info adicional
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

def sri_autorizacion_por_clave(clave: str, timeout: float = SRI_TIMEOUT):
    """Consulta la autorización de un comprobante en el SRI por clave de acceso."""
    session = requests.Session()
    transport = Transport(session=session, timeout=timeout)
    client = Client(wsdl=SRI_WSDL, transport=transport)
    return client.service.autorizacionComprobante(clave)

def parse_autorizacion_response(resp) -> Tuple[bool, str, Optional[str], Dict]:
    """Procesa la respuesta del servicio de autorización SRI."""
    try:
        raw = {
            "claveAccesoConsultada": getattr(resp, "claveAccesoConsultada", None),
            "numeroComprobantes": getattr(resp, "numeroComprobantes", None),
            "autorizaciones": None,
        }
        auts = getattr(resp, "autorizaciones", None)
        aut_list = list(auts.autorizacion) if auts and hasattr(auts, "autorizacion") else []

        raw_auts = []
        xml = None
        estado = ""
        for a in aut_list:
            d = {
                "estado": getattr(a, "estado", None),
                "numeroAutorizacion": getattr(a, "numeroAutorizacion", None),
                "fechaAutorizacion": str(getattr(a, "fechaAutorizacion", None)),
                "ambiente": getattr(a, "ambiente", None),
            }
            raw_auts.append(d)
            if not xml and hasattr(a, "comprobante"):
                xml = a.comprobante
            if hasattr(a, "estado") and a.estado:
                estado = a.estado
        raw["autorizaciones"] = raw_auts

        ok = (len(aut_list) > 0 and str(estado).upper() == "AUTORIZADO")
        return ok, estado, xml, raw
    except Exception:
        try:
            raw = dict(resp)
        except Exception:
            raw = {"_repr": str(resp)}
        return False, "", None, raw
