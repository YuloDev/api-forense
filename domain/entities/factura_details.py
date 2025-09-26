from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class ItemFactura:
    """Entidad que representa un item de la factura"""
    codigo_principal: str
    codigo_auxiliar: str
    cantidad: int
    descripcion: str
    detalle_adicional: Optional[str] = None
    precio_unitario: float = 0.0
    descuento: float = 0.0
    precio_total: float = 0.0


@dataclass
class TotalesFactura:
    """Entidad que representa los totales de la factura"""
    subtotal_15: float = 0.0
    subtotal_0: float = 0.0
    subtotal_no_objeto_iva: float = 0.0
    subtotal_exento_iva: float = 0.0
    subtotal_sin_impuestos: float = 0.0
    total_descuento: float = 0.0
    ice: float = 0.0
    iva_15: float = 0.0
    irbpnr: float = 0.0
    total_general: float = 0.0


@dataclass
class DetalleFactura:
    """Entidad que representa el detalle completo de una factura"""
    # Información de la empresa
    razon_social: str
    nombre_comercial: str
    ruc: str
    direccion_matriz: str
    direccion_sucursal: str
    contribuyente_especial: str
    obligado_contabilidad: str
    
    # Información del documento
    tipo_documento: str
    numero_factura: str
    numero_autorizacion: str
    ambiente: str
    fecha_emision: str
    fecha_autorizacion: str
    emision: str
    clave_acceso: str
    codigo_barras: str
    
    # Información del cliente
    cliente_nombre: str
    cliente_identificacion: str
    cliente_direccion: str
    cliente_email: str
    
    # Items y totales
    items: List[ItemFactura]
    totales: TotalesFactura
    
    # Información adicional
    documento_interno: Optional[str] = None
    nombre_paciente: Optional[str] = None
    info_sri: Optional[str] = None
    deducible_medicinas: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entidad a diccionario para serialización JSON"""
        return {
            "empresa": {
                "razon_social": self.razon_social,
                "nombre_comercial": self.nombre_comercial,
                "ruc": self.ruc,
                "direccion_matriz": self.direccion_matriz,
                "direccion_sucursal": self.direccion_sucursal,
                "contribuyente_especial": self.contribuyente_especial,
                "obligado_contabilidad": self.obligado_contabilidad
            },
            "documento": {
                "tipo_documento": self.tipo_documento,
                "numero_factura": self.numero_factura,
                "numero_autorizacion": self.numero_autorizacion,
                "ambiente": self.ambiente,
                "fecha_emision": self.fecha_emision,
                "fecha_autorizacion": self.fecha_autorizacion,
                "emision": self.emision,
                "clave_acceso": self.clave_acceso,
                "codigo_barras": self.codigo_barras
            },
            "cliente": {
                "nombre": self.cliente_nombre,
                "identificacion": self.cliente_identificacion,
                "direccion": self.cliente_direccion,
                "email": self.cliente_email
            },
            "items": [
                {
                    "codigo_principal": item.codigo_principal,
                    "codigo_auxiliar": item.codigo_auxiliar,
                    "cantidad": item.cantidad,
                    "descripcion": item.descripcion,
                    "detalle_adicional": item.detalle_adicional,
                    "precio_unitario": item.precio_unitario,
                    "descuento": item.descuento,
                    "precio_total": item.precio_total
                }
                for item in self.items
            ],
            "totales": {
                "subtotal_15": self.totales.subtotal_15,
                "subtotal_0": self.totales.subtotal_0,
                "subtotal_no_objeto_iva": self.totales.subtotal_no_objeto_iva,
                "subtotal_exento_iva": self.totales.subtotal_exento_iva,
                "subtotal_sin_impuestos": self.totales.subtotal_sin_impuestos,
                "total_descuento": self.totales.total_descuento,
                "ice": self.totales.ice,
                "iva_15": self.totales.iva_15,
                "irbpnr": self.totales.irbpnr,
                "total_general": self.totales.total_general
            },
            "informacion_adicional": {
                "documento_interno": self.documento_interno,
                "nombre_paciente": self.nombre_paciente,
                "info_sri": self.info_sri,
                "deducible_medicinas": self.deducible_medicinas
            }
        }
