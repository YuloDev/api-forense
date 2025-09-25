"""
Entidad para un nivel de riesgo individual.

Representa un nivel de riesgo con su rango de puntuación.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class RiskLevel:
    """Entidad que representa un nivel de riesgo individual"""
    
    name: str
    min_score: int
    max_score: int
    description: str = ""
    
    def __post_init__(self):
        """Validar datos después de la inicialización"""
        if self.min_score < 0:
            raise ValueError("El puntaje mínimo no puede ser negativo")
        if self.max_score < self.min_score:
            raise ValueError("El puntaje máximo no puede ser menor al mínimo")
        if not self.name or not self.name.strip():
            raise ValueError("El nombre del nivel de riesgo es requerido")
    
    @property
    def range(self) -> List[int]:
        """Retorna el rango como lista [min, max]"""
        return [self.min_score, self.max_score]
    
    def contains_score(self, score: int) -> bool:
        """Verifica si un puntaje está dentro de este nivel de riesgo"""
        return self.min_score <= score <= self.max_score
    
    def to_dict(self) -> dict:
        """Convierte la entidad a diccionario"""
        return {
            "name": self.name,
            "min_score": self.min_score,
            "max_score": self.max_score,
            "description": self.description,
            "range": self.range
        }
    
    @classmethod
    def from_dict(cls, name: str, data: dict) -> 'RiskLevel':
        """Crea una instancia desde un diccionario"""
        if isinstance(data, list) and len(data) == 2:
            return cls(
                name=name,
                min_score=data[0],
                max_score=data[1],
                description=data.get("description", "")
            )
        else:
            return cls(
                name=name,
                min_score=data.get("min_score", 0),
                max_score=data.get("max_score", 0),
                description=data.get("description", "")
            )
