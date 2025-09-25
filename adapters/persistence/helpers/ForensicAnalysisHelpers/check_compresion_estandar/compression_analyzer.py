"""
Helper para análisis de compresión estándar.

Analiza los métodos de compresión utilizados en documentos PDF e imágenes.
"""

import zlib
import struct
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
import fitz  # PyMuPDF
import io


class CompressionAnalyzer:
    """Analizador de compresión estándar"""
    
    def __init__(self):
        # Métodos de compresión estándar para PDF
        self.standard_pdf_compressions = [
            "FlateDecode",      # ZIP/Deflate (más común)
            "DCTDecode",        # JPEG
            "CCITTFaxDecode",   # CCITT Group 3/4 (fax)
            "LZWDecode",        # LZW
            "RunLengthDecode",  # RLE
            "ASCII85Decode",    # ASCII85
            "ASCIIHexDecode"    # ASCII Hex
        ]
        
        # Métodos de compresión sospechosos para PDF
        self.suspicious_pdf_compressions = [
            "JBIG2Decode",      # JBIG2 (puede ser usado para ocultar texto)
            "Crypt",            # Cifrado personalizado
            "CustomDecode",     # Decodificador personalizado
            "UnknownDecode"     # Desconocido
        ]
        
        # Métodos de compresión estándar para imágenes
        self.standard_image_compressions = [
            "JPEG",             # JPEG estándar
            "PNG",              # PNG con compresión Deflate
            "LZW",              # LZW (TIFF)
            "RLE",              # Run Length Encoding
            "Deflate",          # Deflate (PNG)
            "None"              # Sin compresión
        ]
        
        # Métodos de compresión sospechosos para imágenes
        self.suspicious_image_compressions = [
            "Custom",           # Compresión personalizada
            "Encrypted",        # Cifrada
            "Proprietary",      # Propietaria
            "Unknown"           # Desconocida
        ]
    
    def analyze_pdf_compression(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza la compresión estándar de un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con información de compresión y análisis
        """
        try:
            # Abrir PDF con PyMuPDF
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            compression_methods = set()
            suspicious_methods = set()
            
            # Analizar cada página
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Obtener streams de la página
                streams = page.get_contents()
                if streams:
                    for stream in streams:
                        # Analizar compresión del stream
                        stream_compression = self._analyze_pdf_stream_compression(stream)
                        if stream_compression:
                            compression_methods.add(stream_compression)
                            
                            # Verificar si es sospechoso
                            if stream_compression in self.suspicious_pdf_compressions:
                                suspicious_methods.add(stream_compression)
                
                # Analizar imágenes en la página
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        pix = fitz.Pixmap(pdf_document, xref)
                        
                        # Analizar compresión de la imagen
                        img_compression = self._analyze_pdf_image_compression(pix)
                        if img_compression:
                            compression_methods.add(img_compression)
                            
                            # Verificar si es sospechoso
                            if img_compression in self.suspicious_pdf_compressions:
                                suspicious_methods.add(img_compression)
                        
                        pix = None  # Liberar memoria
                        
                    except Exception:
                        # Continuar con la siguiente imagen si hay error
                        continue
            
            pdf_document.close()
            
            # Realizar análisis de compresión
            analysis = self._analyze_compression_standards(
                list(compression_methods), 
                list(suspicious_methods), 
                "pdf"
            )
            
            return analysis
            
        except Exception as e:
            return {
                "error": f"Error analizando compresión del PDF: {str(e)}",
                "compression_methods": [],
                "suspicious_methods": []
            }
    
    def analyze_image_compression(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza la compresión estándar de una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con información de compresión y análisis
        """
        try:
            # Abrir imagen con PIL
            image = Image.open(io.BytesIO(image_bytes))
            
            # Obtener información de compresión
            compression_info = self._get_image_compression_info(image)
            
            # Analizar compresión
            analysis = self._analyze_compression_standards(
                [compression_info["method"]], 
                [compression_info["method"]] if compression_info["suspicious"] else [], 
                "image"
            )
            
            return analysis
            
        except Exception as e:
            return {
                "error": f"Error analizando compresión de la imagen: {str(e)}",
                "compression_methods": [],
                "suspicious_methods": []
            }
    
    def _analyze_pdf_stream_compression(self, stream) -> Optional[str]:
        """Analiza la compresión de un stream PDF"""
        try:
            # Obtener filtros de compresión del stream
            if hasattr(stream, 'get_filters'):
                filters = stream.get_filters()
                if filters:
                    # Tomar el primer filtro (más común)
                    return filters[0][0] if isinstance(filters[0], tuple) else filters[0]
            
            # Intentar detectar compresión por contenido
            stream_data = stream.get_data()
            if stream_data:
                return self._detect_compression_by_content(stream_data)
            
            return None
            
        except Exception:
            return None
    
    def _analyze_pdf_image_compression(self, pix) -> Optional[str]:
        """Analiza la compresión de una imagen en PDF"""
        try:
            # Obtener información de la imagen
            if hasattr(pix, 'get_pixmap'):
                # Verificar si es JPEG
                if pix.colorspace.name == "DeviceRGB" and pix.alpha == 0:
                    return "DCTDecode"  # JPEG
                elif pix.colorspace.name == "DeviceGray":
                    return "FlateDecode"  # Probablemente PNG
                else:
                    return "FlateDecode"  # Por defecto
            
            return None
            
        except Exception:
            return None
    
    def _get_image_compression_info(self, image: Image.Image) -> Dict[str, Any]:
        """Obtiene información de compresión de una imagen PIL"""
        try:
            format_name = image.format or "Unknown"
            
            # Mapear formatos a métodos de compresión
            compression_map = {
                "JPEG": "JPEG",
                "PNG": "PNG",
                "TIFF": "LZW",
                "BMP": "None",
                "GIF": "LZW",
                "WEBP": "Deflate"
            }
            
            method = compression_map.get(format_name, "Unknown")
            suspicious = method in self.suspicious_image_compressions
            
            return {
                "method": method,
                "format": format_name,
                "suspicious": suspicious
            }
            
        except Exception:
            return {
                "method": "Unknown",
                "format": "Unknown",
                "suspicious": True
            }
    
    def _detect_compression_by_content(self, data: bytes) -> Optional[str]:
        """Detecta el tipo de compresión por el contenido de los datos"""
        try:
            # Verificar JPEG
            if data.startswith(b'\xff\xd8\xff'):
                return "DCTDecode"
            
            # Verificar PNG
            if data.startswith(b'\x89PNG\r\n\x1a\n'):
                return "FlateDecode"
            
            # Verificar ZIP/Deflate
            if data.startswith(b'PK') or data.startswith(b'\x78\x9c'):
                return "FlateDecode"
            
            # Verificar LZW
            if data.startswith(b'\x80\x2a'):
                return "LZWDecode"
            
            # Verificar RLE
            if len(data) > 4 and struct.unpack('>I', data[:4])[0] == 0x80000000:
                return "RunLengthDecode"
            
            return "UnknownDecode"
            
        except Exception:
            return "UnknownDecode"
    
    def _analyze_compression_standards(self, compression_methods: List[str], 
                                     suspicious_methods: List[str], 
                                     source_type: str) -> Dict[str, Any]:
        """Analiza si los métodos de compresión son estándar"""
        if not compression_methods:
            return {
                "compression_methods": [],
                "suspicious_methods": [],
                "is_standard": True,
                "is_suspicious": False,
                "main_compression": "None",
                "secondary_compression": None,
                "suspicious_indicators": []
            }
        
        # Determinar compresión principal
        main_compression = compression_methods[0] if compression_methods else "None"
        secondary_compression = compression_methods[1] if len(compression_methods) > 1 else None
        
        # Verificar si es estándar
        standard_compressions = (self.standard_pdf_compressions if source_type == "pdf" 
                               else self.standard_image_compressions)
        
        is_standard = all(method in standard_compressions for method in compression_methods)
        
        # Verificar si es sospechoso
        is_suspicious = len(suspicious_methods) > 0
        
        # Generar indicadores sospechosos
        suspicious_indicators = self._generate_suspicious_indicators(
            compression_methods, suspicious_methods, is_standard, source_type
        )
        
        return {
            "compression_methods": compression_methods,
            "suspicious_methods": suspicious_methods,
            "is_standard": is_standard,
            "is_suspicious": is_suspicious,
            "main_compression": main_compression,
            "secondary_compression": secondary_compression,
            "suspicious_indicators": suspicious_indicators
        }
    
    def _generate_suspicious_indicators(self, compression_methods: List[str], 
                                      suspicious_methods: List[str], 
                                      is_standard: bool, source_type: str) -> List[str]:
        """Genera indicadores sospechosos basados en el análisis de compresión"""
        indicators = []
        
        if not is_standard:
            indicators.append("Uso de métodos de compresión no estándar")
        
        if suspicious_methods:
            indicators.append(f"Métodos de compresión sospechosos: {suspicious_methods}")
        
        if len(compression_methods) > 2:
            indicators.append("Múltiples métodos de compresión - posible manipulación")
        
        if source_type == "pdf":
            if "JBIG2Decode" in compression_methods:
                indicators.append("Uso de JBIG2 - posible ocultamiento de texto")
            if "Crypt" in compression_methods:
                indicators.append("Uso de cifrado personalizado - posible protección maliciosa")
        else:
            if "Custom" in compression_methods:
                indicators.append("Compresión personalizada - posible manipulación")
            if "Encrypted" in compression_methods:
                indicators.append("Imagen cifrada - posible ocultamiento de datos")
        
        if not compression_methods:
            indicators.append("No se detectaron métodos de compresión - posible archivo corrupto")
        
        return indicators
