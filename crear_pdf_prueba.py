#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para crear un PDF de prueba con texto nativo
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import os

def crear_pdf_prueba():
    """Crea un PDF de prueba con texto nativo"""
    print("📄 CREANDO PDF DE PRUEBA")
    print("=" * 40)
    
    # Crear directorio si no existe
    os.makedirs("helpers/IMG", exist_ok=True)
    
    # Crear PDF
    filename = "helpers/IMG/factura_prueba.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 50, "FACTURA ELECTRÓNICA")
    
    # Información de la empresa
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 80, "FARMACIAS Y COMISARIATOS DE MEDICINAS S.A.")
    c.drawString(100, height - 100, "RUC: 1790710319001")
    c.drawString(100, height - 120, "Dirección: Av. Interoceánica S/N")
    
    # Número de factura
    c.drawString(100, height - 150, "FACTURA No. 026-200-000021384")
    
    # Número de autorización
    c.drawString(100, height - 180, "NÚMERO DE AUTORIZACIÓN")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, height - 200, "0807202501179071031900120262000000213845658032318")
    
    # Ambiente
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 230, "AMBIENTE: PRODUCCION")
    
    # Fecha
    c.drawString(100, height - 260, "FECHA Y HORA DE EMISIÓN: 2025-07-08 19:58:13")
    
    # Cliente
    c.drawString(100, height - 290, "Razón Social: ROCKO VERDEZOTO")
    c.drawString(100, height - 310, "Identificación: 1234567890")
    
    # Productos
    c.drawString(100, height - 350, "DETALLE DE PRODUCTOS:")
    c.drawString(120, height - 370, "1. MEDICAMENTO A - Cantidad: 1 - Precio: $23.00")
    c.drawString(120, height - 390, "2. MEDICAMENTO B - Cantidad: 2 - Precio: $15.50")
    
    # Totales
    c.drawString(100, height - 430, "SUBTOTAL: $54.00")
    c.drawString(100, height - 450, "IVA 15%: $8.10")
    c.drawString(100, height - 470, "TOTAL: $62.10")
    
    # Forma de pago
    c.drawString(100, height - 500, "FORMA DE PAGO: TARJETA DE CREDITO")
    
    # Guardar PDF
    c.save()
    
    print(f"✅ PDF creado: {filename}")
    print(f"   Tamaño: {os.path.getsize(filename)} bytes")
    
    return filename

if __name__ == "__main__":
    crear_pdf_prueba()

