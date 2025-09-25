"""
Entidad para la colección de niveles de riesgo.

Maneja la colección completa de niveles de riesgo del sistema.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from .risk_level import RiskLevel


@dataclass
class RiskLevelsCollection:
    """Colección de niveles de riesgo del sistema"""
    
    levels: Dict[str, RiskLevel]
    
    def __post_init__(self):
        """Validar la colección después de la inicialización"""
        if not self.levels:
            raise ValueError("La colección de niveles de riesgo no puede estar vacía")
        
        # Verificar que no haya rangos superpuestos
        sorted_levels = sorted(self.levels.values(), key=lambda x: x.min_score)
        for i in range(len(sorted_levels) - 1):
            current = sorted_levels[i]
            next_level = sorted_levels[i + 1]
            if current.max_score >= next_level.min_score:
                raise ValueError(f"Los rangos de {current.name} y {next_level.name} se superponen")
    
    def get_level_by_score(self, score: int) -> Optional[RiskLevel]:
        """Obtiene el nivel de riesgo para un puntaje específico"""
        for level in self.levels.values():
            if level.contains_score(score):
                return level
        return None
    
    def get_level_by_name(self, name: str) -> Optional[RiskLevel]:
        """Obtiene un nivel de riesgo por su nombre"""
        return self.levels.get(name)
    
    def add_level(self, level: RiskLevel) -> None:
        """Agrega un nuevo nivel de riesgo"""
        if level.name in self.levels:
            raise ValueError(f"El nivel de riesgo '{level.name}' ya existe")
        
        # Verificar que no se superponga con niveles existentes
        for existing_level in self.levels.values():
            if (level.min_score <= existing_level.max_score and 
                level.max_score >= existing_level.min_score):
                raise ValueError(f"El rango de {level.name} se superpone con {existing_level.name}")
        
        self.levels[level.name] = level
    
    def update_level(self, name: str, level: RiskLevel) -> None:
        """Actualiza un nivel de riesgo existente"""
        if name not in self.levels:
            raise ValueError(f"El nivel de riesgo '{name}' no existe")
        
        # Verificar que no se superponga con otros niveles (excluyendo el actual)
        for existing_name, existing_level in self.levels.items():
            if existing_name != name:
                if (level.min_score <= existing_level.max_score and 
                    level.max_score >= existing_level.min_score):
                    raise ValueError(f"El rango de {level.name} se superpone con {existing_level.name}")
        
        self.levels[name] = level
    
    def remove_level(self, name: str) -> None:
        """Elimina un nivel de riesgo"""
        if name not in self.levels:
            raise ValueError(f"El nivel de riesgo '{name}' no existe")
        
        if len(self.levels) <= 1:
            raise ValueError("No se puede eliminar el último nivel de riesgo")
        
        del self.levels[name]
    
    def get_all_levels(self) -> List[RiskLevel]:
        """Obtiene todos los niveles de riesgo ordenados por puntaje mínimo"""
        return sorted(self.levels.values(), key=lambda x: x.min_score)
    
    def to_dict(self) -> Dict[str, List[int]]:
        """Convierte la colección a diccionario en formato JSON"""
        result = {}
        for name, level in self.levels.items():
            result[name] = level.range
        return result
    
    def to_detailed_dict(self) -> Dict[str, dict]:
        """Convierte la colección a diccionario detallado"""
        result = {}
        for name, level in self.levels.items():
            result[name] = level.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, List[int]]) -> 'RiskLevelsCollection':
        """Crea una instancia desde un diccionario JSON"""
        levels = {}
        for name, range_data in data.items():
            if isinstance(range_data, list) and len(range_data) == 2:
                level = RiskLevel(
                    name=name,
                    min_score=range_data[0],
                    max_score=range_data[1]
                )
                levels[name] = level
            else:
                raise ValueError(f"Formato inválido para el nivel '{name}': {range_data}")
        
        return cls(levels=levels)
    
    @classmethod
    def from_detailed_dict(cls, data: Dict[str, dict]) -> 'RiskLevelsCollection':
        """Crea una instancia desde un diccionario detallado"""
        levels = {}
        for name, level_data in data.items():
            level = RiskLevel.from_dict(name, level_data)
            levels[name] = level
        
        return cls(levels=levels)
