"""
Entidad para un reclamo individual.

Representa un reclamo con toda su información.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Proveedor:
    """Entidad que representa un proveedor"""
    
    nombre: str
    tipo_servicio: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entidad a diccionario"""
        return {
            "nombre": self.nombre,
            "tipo_servicio": self.tipo_servicio
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Proveedor':
        """Crea una instancia desde un diccionario"""
        return cls(
            nombre=data.get("nombre", ""),
            tipo_servicio=data.get("tipo_servicio", "")
        )


@dataclass
class Acciones:
    """Entidad que representa las acciones disponibles para un reclamo"""
    
    ver: bool
    subir: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entidad a diccionario"""
        return {
            "ver": self.ver,
            "subir": self.subir
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Acciones':
        """Crea una instancia desde un diccionario"""
        return cls(
            ver=data.get("ver", False),
            subir=data.get("subir", False)
        )


@dataclass
class Reclamo:
    """Entidad que representa un reclamo individual"""
    
    id_reclamo: str
    fecha_envio: str
    proveedor: Proveedor
    estado: str
    monto_solicitado: float
    monto_aprobado: Optional[float]
    moneda: str
    acciones: Acciones
    
    def __post_init__(self):
        """Validar datos después de la inicialización"""
        if not self.id_reclamo or not self.id_reclamo.strip():
            raise ValueError("El ID del reclamo es requerido")
        
        if not self.fecha_envio or not self.fecha_envio.strip():
            raise ValueError("La fecha de envío es requerida")
        
        if not self.estado or not self.estado.strip():
            raise ValueError("El estado es requerido")
        
        if self.monto_solicitado < 0:
            raise ValueError("El monto solicitado no puede ser negativo")
        
        if self.monto_aprobado is not None and self.monto_aprobado < 0:
            raise ValueError("El monto aprobado no puede ser negativo")
        
        if not self.moneda or not self.moneda.strip():
            raise ValueError("La moneda es requerida")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entidad a diccionario"""
        return {
            "id_reclamo": self.id_reclamo,
            "fecha_envio": self.fecha_envio,
            "proveedor": self.proveedor.to_dict(),
            "estado": self.estado,
            "monto_solicitado": self.monto_solicitado,
            "monto_aprobado": self.monto_aprobado,
            "moneda": self.moneda,
            "acciones": self.acciones.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Reclamo':
        """Crea una instancia desde un diccionario"""
        return cls(
            id_reclamo=data.get("id_reclamo", ""),
            fecha_envio=data.get("fecha_envio", ""),
            proveedor=Proveedor.from_dict(data.get("proveedor", {})),
            estado=data.get("estado", ""),
            monto_solicitado=data.get("monto_solicitado", 0.0),
            monto_aprobado=data.get("monto_aprobado"),
            moneda=data.get("moneda", "$"),
            acciones=Acciones.from_dict(data.get("acciones", {}))
        )
    
    def update_estado(self, nuevo_estado: str) -> None:
        """Actualiza el estado del reclamo"""
        if not nuevo_estado or not nuevo_estado.strip():
            raise ValueError("El nuevo estado no puede estar vacío")
        self.estado = nuevo_estado
    
    def update_monto_aprobado(self, monto: Optional[float]) -> None:
        """Actualiza el monto aprobado del reclamo"""
        if monto is not None and monto < 0:
            raise ValueError("El monto aprobado no puede ser negativo")
        self.monto_aprobado = monto
    
    def update_acciones(self, ver: bool = None, subir: bool = None) -> None:
        """Actualiza las acciones del reclamo"""
        if ver is not None:
            self.acciones.ver = ver
        if subir is not None:
            self.acciones.subir = subir
