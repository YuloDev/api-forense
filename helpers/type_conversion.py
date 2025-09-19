"""
Helper functions to convert NumPy types to Python native types for JSON serialization.
This prevents Pydantic serialization errors with numpy.bool, numpy.int64, etc.
"""

import numpy as np
from typing import Any, Dict, List, Union


def convert_numpy_types(obj: Any) -> Any:
    """
    Recursively converts NumPy types to Python native types.
    
    Args:
        obj: Any object that might contain NumPy types
        
    Returns:
        Object with NumPy types converted to Python native types
    """
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return convert_numpy_types(obj.tolist())
    else:
        return obj


def safe_serialize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safely serializes a dictionary by converting all NumPy types to Python types.
    
    Args:
        data: Dictionary that might contain NumPy types
        
    Returns:
        Dictionary with all NumPy types converted to Python native types
    """
    return convert_numpy_types(data)


def ensure_python_bool(value: Any) -> bool:
    """
    Ensures a value is a Python bool, converting from numpy.bool if necessary.
    
    Args:
        value: Any value that should be a boolean
        
    Returns:
        Python bool value
    """
    if isinstance(value, np.bool_):
        return bool(value)
    elif isinstance(value, bool):
        return value
    else:
        return bool(value)


def ensure_python_float(value: Any) -> float:
    """
    Ensures a value is a Python float, converting from numpy types if necessary.
    
    Args:
        value: Any value that should be a float
        
    Returns:
        Python float value
    """
    if isinstance(value, np.floating):
        return float(value)
    elif isinstance(value, np.integer):
        return float(value)
    elif isinstance(value, (int, float)):
        return float(value)
    else:
        return float(value)


def ensure_python_int(value: Any) -> int:
    """
    Ensures a value is a Python int, converting from numpy types if necessary.
    
    Args:
        value: Any value that should be an int
        
    Returns:
        Python int value
    """
    if isinstance(value, np.integer):
        return int(value)
    elif isinstance(value, np.floating):
        return int(value)
    elif isinstance(value, (int, float)):
        return int(value)
    else:
        return int(value)
