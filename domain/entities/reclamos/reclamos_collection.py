"""
Entidad para la colección de reclamos.

Maneja la colección completa de reclamos del sistema.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from .reclamo import Reclamo


@dataclass
class ReclamosCollection:
    """Colección de reclamos del sistema"""
    
    reclamos: List[Reclamo]
    
    def __post_init__(self):
        """Validar la colección después de la inicialización"""
        if self.reclamos is None:
            self.reclamos = []
    
    def get_reclamo_by_id(self, id_reclamo: str) -> Optional[Reclamo]:
        """Obtiene un reclamo por su ID"""
        for reclamo in self.reclamos:
            if reclamo.id_reclamo == id_reclamo:
                return reclamo
        return None
    
    def add_reclamo(self, reclamo: Reclamo) -> None:
        """Agrega un nuevo reclamo"""
        if self.get_reclamo_by_id(reclamo.id_reclamo):
            raise ValueError(f"Ya existe un reclamo con ID '{reclamo.id_reclamo}'")
        
        self.reclamos.append(reclamo)
    
    def update_reclamo(self, id_reclamo: str, reclamo: Reclamo) -> None:
        """Actualiza un reclamo existente"""
        for i, existing_reclamo in enumerate(self.reclamos):
            if existing_reclamo.id_reclamo == id_reclamo:
                self.reclamos[i] = reclamo
                return
        
        raise ValueError(f"No se encontró reclamo con ID '{id_reclamo}'")
    
    def remove_reclamo(self, id_reclamo: str) -> None:
        """Elimina un reclamo"""
        for i, reclamo in enumerate(self.reclamos):
            if reclamo.id_reclamo == id_reclamo:
                del self.reclamos[i]
                return
        
        raise ValueError(f"No se encontró reclamo con ID '{id_reclamo}'")
    
    def get_reclamos_by_estado(self, estado: str) -> List[Reclamo]:
        """Obtiene reclamos por estado"""
        return [r for r in self.reclamos if r.estado.lower() == estado.lower()]
    
    def get_reclamos_by_proveedor(self, nombre_proveedor: str) -> List[Reclamo]:
        """Obtiene reclamos por nombre de proveedor"""
        return [r for r in self.reclamos if nombre_proveedor.lower() in r.proveedor.nombre.lower()]
    
    def get_reclamos_by_fecha(self, fecha: str) -> List[Reclamo]:
        """Obtiene reclamos por fecha de envío"""
        return [r for r in self.reclamos if r.fecha_envio == fecha]
    
    def get_all_reclamos(self) -> List[Reclamo]:
        """Obtiene todos los reclamos"""
        return self.reclamos.copy()
    
    def get_count(self) -> int:
        """Obtiene el número total de reclamos"""
        return len(self.reclamos)
    
    def get_count_by_estado(self, estado: str) -> int:
        """Obtiene el número de reclamos por estado"""
        return len(self.get_reclamos_by_estado(estado))
    
    def to_dict(self) -> Dict[str, List[Dict]]:
        """Convierte la colección a diccionario en formato JSON"""
        return {
            "reclamos": [reclamo.to_dict() for reclamo in self.reclamos]
        }
    
    def to_list(self) -> List[Dict]:
        """Convierte la colección a lista de diccionarios"""
        return [reclamo.to_dict() for reclamo in self.reclamos]
    
    @classmethod
    def from_dict(cls, data: Dict[str, List[Dict]]) -> 'ReclamosCollection':
        """Crea una instancia desde un diccionario JSON"""
        reclamos_data = data.get("reclamos", [])
        reclamos = [Reclamo.from_dict(reclamo_data) for reclamo_data in reclamos_data]
        return cls(reclamos=reclamos)
    
    @classmethod
    def from_list(cls, reclamos_data: List[Dict]) -> 'ReclamosCollection':
        """Crea una instancia desde una lista de diccionarios"""
        reclamos = [Reclamo.from_dict(reclamo_data) for reclamo_data in reclamos_data]
        return cls(reclamos=reclamos)
