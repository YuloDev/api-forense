"""
Entidad para un risk weight individual.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskWeight:
    """Entidad que representa un risk weight individual"""
    
    key: str
    valor: int
    descripcion: str
    explicacion: str
    
    def __post_init__(self):
        """Validaciones post-construcción"""
        if self.valor < 0:
            raise ValueError("El valor del risk weight no puede ser negativo")
        if not self.key or not self.key.strip():
            raise ValueError("La clave del risk weight no puede estar vacía")
        if not self.descripcion or not self.descripcion.strip():
            raise ValueError("La descripción del risk weight no puede estar vacía")
        if not self.explicacion or not self.explicacion.strip():
            raise ValueError("La explicación del risk weight no puede estar vacía")
    
    def to_dict(self) -> dict:
        """Convierte la entidad a diccionario"""
        return {
            "valor": self.valor,
            "descripcion": self.descripcion,
            "explicacion": self.explicacion
        }
    
    @classmethod
    def from_dict(cls, key: str, data: dict) -> 'RiskWeight':
        """Crea una instancia desde un diccionario"""
        return cls(
            key=key,
            valor=data.get("valor", 0),
            descripcion=data.get("descripcion", ""),
            explicacion=data.get("explicacion", "")
        )
