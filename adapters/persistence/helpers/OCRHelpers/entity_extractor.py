"""
Helper para extracción de entidades en análisis forense OCR
"""
import re
from typing import List, Tuple
from domain.entities.forensic_ocr_details import (
    FechaNormalizada, MonedaNormalizada, Identificador, CampoClave, BBox
)

class EntityExtractor:
    """Helper para extracción de entidades del texto"""
    
    @staticmethod
    def extract_entities(text: str) -> Tuple[List[FechaNormalizada], List[MonedaNormalizada], List[Identificador]]:
        """Extrae entidades del texto"""
        fechas = []
        monedas = []
        identificadores = []

        # Patrones de regex para fechas
        fecha_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
            r'(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})'
        ]
        
        # Patrones de regex para monedas
        moneda_patterns = [
            r'[\$€£¥]\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
            r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*[\$€£¥]',
            r'USD\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
            r'EUR\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)'
        ]
        
        # Patrones de regex para identificadores
        ruc_pattern = r'(\d{13})'
        ci_pattern = r'(\d{10})'
        factura_pattern = r'(?:FACTURA|FACT\.?)\s*[N°#]?\s*(\d+)'

        # Buscar fechas
        for pattern in fecha_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                fecha_texto = match.group(1)
                try:
                    # Convertir a ISO 8601 (simplificado)
                    if '/' in fecha_texto:
                        parts = fecha_texto.split('/')
                        if len(parts[2]) == 2:
                            parts[2] = '20' + parts[2]
                        iso_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                    else:
                        iso_date = fecha_texto
                    
                    fechas.append(FechaNormalizada(
                        texto_raw=fecha_texto,
                        iso8601=iso_date,
                        bbox=BBox(0, 0, 0, 0)  # Se llenará con coordenadas reales
                    ))
                except:
                    pass

        # Buscar monedas
        for pattern in moneda_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                valor_texto = match.group(1)
                try:
                    # Normalizar separadores decimales
                    valor_normalizado = valor_texto.replace(',', '.')
                    if valor_normalizado.count('.') > 1:
                        # Separador de miles
                        valor_normalizado = valor_normalizado.replace('.', '', valor_normalizado.count('.') - 1)
                    
                    valor_num = float(valor_normalizado)
                    moneda = "USD" if '$' in match.group(0) else "EUR" if '€' in match.group(0) else "USD"
                    
                    monedas.append(MonedaNormalizada(
                        texto_raw=match.group(0),
                        valor=valor_num,
                        moneda=moneda,
                        bbox=BBox(0, 0, 0, 0)  # Se llenará con coordenadas reales
                    ))
                except:
                    pass

        # Buscar identificadores
        # RUC
        ruc_matches = re.finditer(ruc_pattern, text)
        for match in ruc_matches:
            identificadores.append(Identificador(
                tipo="RUC",
                texto_raw=match.group(1),
                valor=match.group(1),
                bbox=BBox(0, 0, 0, 0),
                regex=ruc_pattern
            ))

        # Cédula
        ci_matches = re.finditer(ci_pattern, text)
        for match in ci_matches:
            identificadores.append(Identificador(
                tipo="CI",
                texto_raw=match.group(1),
                valor=match.group(1),
                bbox=BBox(0, 0, 0, 0),
                regex=ci_pattern
            ))

        # Número de factura
        factura_matches = re.finditer(factura_pattern, text, re.IGNORECASE)
        for match in factura_matches:
            identificadores.append(Identificador(
                tipo="FACTURA",
                texto_raw=match.group(1),
                valor=match.group(1),
                bbox=BBox(0, 0, 0, 0),
                regex=factura_pattern
            ))

        return fechas, monedas, identificadores

    @staticmethod
    def extract_financial_totals(text: str) -> List[CampoClave]:
        """Extrae totales financieros del texto"""
        campos_clave = []
        
        # Patrones para campos financieros
        patterns = {
            "TOTAL": r'(?:TOTAL|TOTAL\s+GENERAL)\s*:?\s*([\d.,]+)',
            "SUBTOTAL": r'(?:SUBTOTAL|SUB\s+TOTAL)\s*:?\s*([\d.,]+)',
            "IVA": r'(?:IVA|I\.V\.A\.?)\s*:?\s*([\d.,]+)',
            "DESCUENTO": r'(?:DESCUENTO|DESC\.?)\s*:?\s*([\d.,]+)'
        }
        
        for label, pattern in patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    valor_texto = match.group(1)
                    valor_normalizado = float(valor_texto.replace(',', '.'))
                    
                    campos_clave.append(CampoClave(
                        label_detectada=label,
                        bbox_label=BBox(0, 0, 0, 0),
                        valor_raw=valor_texto,
                        valor_normalizado=valor_normalizado,
                        bbox_valor=BBox(0, 0, 0, 0)
                    ))
                except:
                    pass
        
        return campos_clave
