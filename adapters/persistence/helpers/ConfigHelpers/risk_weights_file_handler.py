"""
Helper para manejar la persistencia de risk weights en archivos JSON.
"""

import json
import os
from typing import Dict, Optional
from domain.entities.config.risk_weights_collection import RiskWeightsCollection
from domain.entities.config.risk_weight import RiskWeight


class RiskWeightsFileHandler:
    """Maneja la lectura y escritura de risk weights desde/hacia archivos JSON"""
    
    def __init__(self, file_path: str = "risk_weights_descriptions.json"):
        self.file_path = file_path
    
    def load_risk_weights(self) -> RiskWeightsCollection:
        """
        Carga los risk weights desde el archivo JSON.
        
        Returns:
            RiskWeightsCollection: Colección de risk weights cargada
        """
        try:
            if not os.path.exists(self.file_path):
                return RiskWeightsCollection(weights={})
            
            with open(self.file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            return RiskWeightsCollection.from_dict(data)
            
        except Exception as e:
            raise Exception(f"Error cargando risk weights desde {self.file_path}: {str(e)}")
    
    def save_risk_weights(self, weights: RiskWeightsCollection) -> bool:
        """
        Guarda los risk weights en el archivo JSON.
        
        Args:
            weights: Colección de risk weights a guardar
            
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            # Crear backup del archivo actual si existe
            if os.path.exists(self.file_path):
                backup_path = f"{self.file_path}.backup"
                with open(self.file_path, 'r', encoding='utf-8') as original:
                    with open(backup_path, 'w', encoding='utf-8') as backup:
                        backup.write(original.read())
            
            # Guardar los nuevos datos
            with open(self.file_path, 'w', encoding='utf-8') as file:
                json.dump(weights.to_json_dict(), file, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            raise Exception(f"Error guardando risk weights en {self.file_path}: {str(e)}")
    
    def get_risk_weight(self, key: str) -> Optional[RiskWeight]:
        """
        Obtiene un risk weight específico.
        
        Args:
            key: Clave del risk weight
            
        Returns:
            RiskWeight: El risk weight solicitado o None si no existe
        """
        try:
            weights = self.load_risk_weights()
            return weights.get_weight(key)
        except Exception:
            return None
    
    def update_risk_weight(self, key: str, weight: RiskWeight) -> bool:
        """
        Actualiza un risk weight existente.
        
        Args:
            key: Clave del risk weight
            weight: Nuevo risk weight
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            weights = self.load_risk_weights()
            if key not in weights:
                return False
            
            weights.set_weight(key, weight)
            return self.save_risk_weights(weights)
            
        except Exception:
            return False
    
    def create_risk_weight(self, key: str, weight: RiskWeight) -> bool:
        """
        Crea un nuevo risk weight.
        
        Args:
            key: Clave del risk weight
            weight: Risk weight a crear
            
        Returns:
            bool: True si se creó correctamente
        """
        try:
            weights = self.load_risk_weights()
            if key in weights:
                return False
            
            weights.set_weight(key, weight)
            return self.save_risk_weights(weights)
            
        except Exception:
            return False
    
    def delete_risk_weight(self, key: str) -> bool:
        """
        Elimina un risk weight.
        
        Args:
            key: Clave del risk weight a eliminar
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            weights = self.load_risk_weights()
            if key not in weights:
                return False
            
            weights.remove_weight(key)
            return self.save_risk_weights(weights)
            
        except Exception:
            return False
