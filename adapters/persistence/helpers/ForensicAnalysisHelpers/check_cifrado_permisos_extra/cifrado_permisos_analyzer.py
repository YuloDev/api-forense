"""
Helper para análisis de cifrado y permisos especiales.

Analiza cifrado o permisos especiales aplicados que pueden usarse para ocultar el método de creación.
"""

import re
from typing import Dict, Any, List, Optional
import fitz  # PyMuPDF
import pikepdf
from PIL import Image
from PIL.ExifTags import TAGS
import io


class CifradoPermisosAnalyzer:
    """Analizador de cifrado y permisos especiales"""
    
    def __init__(self):
        # Patrones de cifrado y permisos especiales
        self.encryption_patterns = [
            r'encrypt',
            r'cipher',
            r'password',
            r'security',
            r'protection',
            r'permissions',
            r'restrictions',
            r'access\s+control',
            r'digital\s+rights',
            r'drm',
            r'watermark',
            r'signature'
        ]
        
        # Tipos de permisos restrictivos
        self.restrictive_permissions = [
            'print',
            'modify',
            'copy',
            'extract',
            'assemble',
            'print_high_res',
            'fill_forms',
            'annotate',
            'modify_annotations'
        ]
        
        # Métodos de cifrado conocidos
        self.encryption_methods = [
            'AES-128',
            'AES-256',
            'RC4',
            'DES',
            '3DES',
            'Blowfish',
            'Twofish'
        ]
        
        # Patrones de restricciones
        self.restriction_patterns = [
            r'no\s+print',
            r'no\s+copy',
            r'no\s+modify',
            r'read\s+only',
            r'view\s+only',
            r'restricted\s+access',
            r'confidential',
            r'proprietary',
            r'classified'
        ]
    
    def analyze_pdf_cifrado_permisos(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza cifrado y permisos especiales en un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con información de cifrado y permisos
        """
        try:
            # Abrir PDF con PyMuPDF
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            metodos_cifrado = []
            restricciones_detectadas = []
            permisos_restrictivos = []
            indicadores_sospechosos = []
            
            # Analizar cifrado del PDF
            encryption_info = self._analyze_pdf_encryption(pdf_document)
            if encryption_info:
                metodos_cifrado.extend(encryption_info.get("metodos", []))
                restricciones_detectadas.extend(encryption_info.get("restricciones", []))
            
            # Analizar permisos del PDF
            permissions_info = self._analyze_pdf_permissions(pdf_document)
            if permissions_info:
                permisos_restrictivos.extend(permissions_info.get("permisos", []))
                restricciones_detectadas.extend(permissions_info.get("restricciones", []))
            
            # Analizar metadatos de seguridad
            security_metadata = self._analyze_security_metadata(pdf_document)
            if security_metadata:
                restricciones_detectadas.extend(security_metadata.get("restricciones", []))
                indicadores_sospechosos.extend(security_metadata.get("indicadores", []))
            
            # Analizar objetos de seguridad
            security_objects = self._analyze_security_objects(pdf_document)
            if security_objects:
                metodos_cifrado.extend(security_objects.get("metodos", []))
                restricciones_detectadas.extend(security_objects.get("restricciones", []))
            
            pdf_document.close()
            
            # Determinar si hay cifrado y permisos especiales
            cifrado_detectado = len(metodos_cifrado) > 0
            permisos_especiales = len(permisos_restrictivos) > 0
            
            # Determinar nivel de cifrado
            nivel_cifrado = self._determine_encryption_level(metodos_cifrado)
            
            # Generar indicadores sospechosos
            indicadores_sospechosos.extend(self._generate_suspicious_indicators(
                cifrado_detectado, permisos_especiales, metodos_cifrado, 
                permisos_restrictivos, restricciones_detectadas
            ))
            
            return {
                "cifrado_detectado": cifrado_detectado,
                "permisos_especiales": permisos_especiales,
                "nivel_cifrado": nivel_cifrado,
                "tipos_permisos": permisos_restrictivos,
                "metodos_cifrado": list(set(metodos_cifrado)),
                "restricciones_detectadas": restricciones_detectadas,
                "permisos_restrictivos": list(set(permisos_restrictivos)),
                "indicadores_sospechosos": indicadores_sospechosos
            }
            
        except Exception as e:
            return {
                "error": f"Error analizando cifrado y permisos del PDF: {str(e)}",
                "cifrado_detectado": False,
                "permisos_especiales": False,
                "nivel_cifrado": "none"
            }
    
    def analyze_image_cifrado_permisos(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza cifrado y permisos especiales en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con información de cifrado y permisos
        """
        try:
            # Abrir imagen con PIL
            image = Image.open(io.BytesIO(image_bytes))
            
            metodos_cifrado = []
            restricciones_detectadas = []
            permisos_restrictivos = []
            indicadores_sospechosos = []
            
            # Analizar metadatos EXIF para restricciones
            exif_data = image._getexif()
            if exif_data:
                exif_restrictions = self._analyze_exif_restrictions(exif_data)
                restricciones_detectadas.extend(exif_restrictions.get("restricciones", []))
                indicadores_sospechosos.extend(exif_restrictions.get("indicadores", []))
            
            # Analizar propiedades de la imagen
            image_properties = self._analyze_image_properties(image)
            if image_properties:
                restricciones_detectadas.extend(image_properties.get("restricciones", []))
                indicadores_sospechosos.extend(image_properties.get("indicadores", []))
            
            # Determinar si hay cifrado y permisos especiales
            cifrado_detectado = len(metodos_cifrado) > 0
            permisos_especiales = len(permisos_restrictivos) > 0
            
            # Determinar nivel de cifrado
            nivel_cifrado = self._determine_encryption_level(metodos_cifrado)
            
            # Generar indicadores sospechosos
            indicadores_sospechosos.extend(self._generate_suspicious_indicators(
                cifrado_detectado, permisos_especiales, metodos_cifrado, 
                permisos_restrictivos, restricciones_detectadas
            ))
            
            return {
                "cifrado_detectado": cifrado_detectado,
                "permisos_especiales": permisos_especiales,
                "nivel_cifrado": nivel_cifrado,
                "tipos_permisos": permisos_restrictivos,
                "metodos_cifrado": list(set(metodos_cifrado)),
                "restricciones_detectadas": restricciones_detectadas,
                "permisos_restrictivos": list(set(permisos_restrictivos)),
                "indicadores_sospechosos": indicadores_sospechosos
            }
            
        except Exception as e:
            return {
                "error": f"Error analizando cifrado y permisos de imagen: {str(e)}",
                "cifrado_detectado": False,
                "permisos_especiales": False,
                "nivel_cifrado": "none"
            }
    
    def _analyze_pdf_encryption(self, pdf_document) -> Optional[Dict[str, Any]]:
        """Analiza el cifrado del PDF"""
        try:
            metodos = []
            restricciones = []
            
            # Verificar si el PDF está cifrado
            if pdf_document.is_encrypted:
                metodos.append("PDF Encrypted")
                restricciones.append("Documento cifrado")
            
            # Verificar método de cifrado específico
            if hasattr(pdf_document, 'security'):
                security = pdf_document.security
                if security:
                    if security.get('encrypt'):
                        metodos.append("Standard Encryption")
                    if security.get('permissions'):
                        restricciones.append("Permisos restringidos")
            
            return {
                "metodos": metodos,
                "restricciones": restricciones
            }
            
        except Exception:
            return None
    
    def _analyze_pdf_permissions(self, pdf_document) -> Optional[Dict[str, Any]]:
        """Analiza los permisos del PDF"""
        try:
            permisos = []
            restricciones = []
            
            # Verificar permisos específicos
            if hasattr(pdf_document, 'permissions'):
                permissions = pdf_document.permissions
                if permissions:
                    for perm in self.restrictive_permissions:
                        if hasattr(permissions, perm):
                            if not getattr(permissions, perm, True):
                                permisos.append(perm)
                                restricciones.append(f"Permiso restringido: {perm}")
            
            return {
                "permisos": permisos,
                "restricciones": restricciones
            }
            
        except Exception:
            return None
    
    def _analyze_security_metadata(self, pdf_document) -> Optional[Dict[str, Any]]:
        """Analiza metadatos de seguridad"""
        try:
            restricciones = []
            indicadores = []
            
            # Obtener metadatos
            metadata = pdf_document.metadata
            
            for key, value in metadata.items():
                if value and isinstance(value, str):
                    # Buscar patrones de restricciones
                    for pattern in self.restriction_patterns:
                        if re.search(pattern, value.lower()):
                            restricciones.append(f"Restricción en {key}: {value}")
                            indicadores.append(f"Patrón restrictivo detectado: {pattern}")
            
            return {
                "restricciones": restricciones,
                "indicadores": indicadores
            }
            
        except Exception:
            return None
    
    def _analyze_security_objects(self, pdf_document) -> Optional[Dict[str, Any]]:
        """Analiza objetos de seguridad del PDF"""
        try:
            metodos = []
            restricciones = []
            
            # Buscar objetos de seguridad en el PDF
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Buscar anotaciones de seguridad
                annotations = page.annots()
                for annot in annotations:
                    if hasattr(annot, 'content') and annot.content:
                        content = annot.content.lower()
                        for pattern in self.encryption_patterns:
                            if re.search(pattern, content):
                                metodos.append(f"Security annotation: {pattern}")
                                restricciones.append(f"Anotación de seguridad: {annot.content}")
            
            return {
                "metodos": metodos,
                "restricciones": restricciones
            }
            
        except Exception:
            return None
    
    def _analyze_exif_restrictions(self, exif_data) -> Optional[Dict[str, Any]]:
        """Analiza restricciones en metadatos EXIF"""
        try:
            restricciones = []
            indicadores = []
            
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if isinstance(value, str):
                    # Buscar patrones de restricciones
                    for pattern in self.restriction_patterns:
                        if re.search(pattern, value.lower()):
                            restricciones.append(f"Restricción EXIF {tag}: {value}")
                            indicadores.append(f"Patrón restrictivo en EXIF: {pattern}")
            
            return {
                "restricciones": restricciones,
                "indicadores": indicadores
            }
            
        except Exception:
            return None
    
    def _analyze_image_properties(self, image) -> Optional[Dict[str, Any]]:
        """Analiza propiedades de la imagen"""
        try:
            restricciones = []
            indicadores = []
            
            # Verificar si la imagen tiene restricciones de acceso
            if hasattr(image, 'info'):
                info = image.info
                for key, value in info.items():
                    if isinstance(value, str):
                        # Buscar patrones de restricciones
                        for pattern in self.restriction_patterns:
                            if re.search(pattern, value.lower()):
                                restricciones.append(f"Restricción de imagen {key}: {value}")
                                indicadores.append(f"Patrón restrictivo en imagen: {pattern}")
            
            return {
                "restricciones": restricciones,
                "indicadores": indicadores
            }
            
        except Exception:
            return None
    
    def _determine_encryption_level(self, metodos_cifrado: List[str]) -> str:
        """Determina el nivel de cifrado basado en los métodos encontrados"""
        if not metodos_cifrado:
            return "none"
        
        # Verificar métodos de cifrado avanzado
        advanced_methods = ["AES-256", "3DES", "Twofish"]
        if any(method in " ".join(metodos_cifrado) for method in advanced_methods):
            return "high"
        
        # Verificar métodos de cifrado medio
        medium_methods = ["AES-128", "Blowfish"]
        if any(method in " ".join(metodos_cifrado) for method in medium_methods):
            return "medium"
        
        # Verificar métodos de cifrado básico
        basic_methods = ["RC4", "DES", "PDF Encrypted"]
        if any(method in " ".join(metodos_cifrado) for method in basic_methods):
            return "low"
        
        return "low"
    
    def _generate_suspicious_indicators(self, cifrado_detectado: bool, permisos_especiales: bool, 
                                      metodos_cifrado: List[str], permisos_restrictivos: List[str], 
                                      restricciones_detectadas: List[Dict[str, Any]]) -> List[str]:
        """Genera indicadores sospechosos basados en el análisis"""
        indicators = []
        
        if cifrado_detectado:
            indicators.append(f"Cifrado detectado en el documento ({len(metodos_cifrado)} métodos)")
        
        if permisos_especiales:
            indicators.append(f"Permisos especiales aplicados ({len(permisos_restrictivos)} restricciones)")
        
        if len(metodos_cifrado) > 1:
            indicators.append("Múltiples métodos de cifrado - posible ocultamiento avanzado")
        
        if len(permisos_restrictivos) > 3:
            indicators.append("Múltiples permisos restrictivos - posible restricción de acceso")
        
        if len(restricciones_detectadas) > 5:
            indicators.append("Alto número de restricciones - posible ocultamiento de información")
        
        if any("confidential" in str(rest).lower() for rest in restricciones_detectadas):
            indicators.append("Marcado como confidencial - posible restricción de acceso")
        
        if any("classified" in str(rest).lower() for rest in restricciones_detectadas):
            indicators.append("Marcado como clasificado - posible restricción de acceso")
        
        return indicators
