"""
Caso de uso para actualizar risk weights.
"""

from typing import Dict, Any, List
from domain.ports.config.risk_weights_service import RiskWeightsServicePort
from domain.entities.config.risk_weight import RiskWeight


class UpdateRiskWeightsUseCase:
    """Caso de uso para actualizar risk weights"""
    
    def __init__(self, risk_weights_service: RiskWeightsServicePort):
        self.risk_weights_service = risk_weights_service
    
    def execute_single(self, key: str, weight_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza un risk weight específico.
        
        Args:
            key: Clave del risk weight
            weight_data: Datos del risk weight a actualizar
            
        Returns:
            Dict con el resultado de la actualización
        """
        try:
            # Validar datos requeridos
            if "valor" not in weight_data:
                return {
                    "success": False,
                    "error": "El campo 'valor' es requerido",
                    "updated": False
                }
            
            if "descripcion" not in weight_data:
                return {
                    "success": False,
                    "error": "El campo 'descripcion' es requerido",
                    "updated": False
                }
            
            if "explicacion" not in weight_data:
                return {
                    "success": False,
                    "error": "El campo 'explicacion' es requerido",
                    "updated": False
                }
            
            # Crear entidad RiskWeight
            weight = RiskWeight(
                key=key,
                valor=weight_data["valor"],
                descripcion=weight_data["descripcion"],
                explicacion=weight_data["explicacion"]
            )
            
            # Actualizar
            success = self.risk_weights_service.update_risk_weight(key, weight)
            
            if success:
                return {
                    "success": True,
                    "message": f"Risk weight '{key}' actualizado correctamente",
                    "data": {key: weight.to_dict()},
                    "updated": True
                }
            else:
                return {
                    "success": False,
                    "error": f"Risk weight '{key}' no encontrado",
                    "updated": False
                }
                
        except ValueError as e:
            return {
                "success": False,
                "error": f"Error de validación: {str(e)}",
                "updated": False
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error actualizando risk weight '{key}': {str(e)}",
                "updated": False
            }
    
    def execute_batch(self, updates: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Actualiza múltiples risk weights.
        
        Args:
            updates: Diccionario con las actualizaciones {key: weight_data}
            
        Returns:
            Dict con el resultado de las actualizaciones
        """
        try:
            results = {}
            success_count = 0
            error_count = 0
            errors = []
            
            for key, weight_data in updates.items():
                result = self.execute_single(key, weight_data)
                results[key] = result
                
                if result["success"]:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"{key}: {result['error']}")
            
            return {
                "success": error_count == 0,
                "message": f"Actualización completada: {success_count} exitosas, {error_count} errores",
                "results": results,
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error en actualización por lotes: {str(e)}",
                "results": {},
                "success_count": 0,
                "error_count": len(updates),
                "errors": [str(e)]
            }
