from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import base64
import pdfplumber
from collections import defaultdict
import io
import os
import json

# --------------------------- CONFIG ----------------------------------
CONFIG_FILE = "risk_weights.json"

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        RISK_WEIGHTS = json.load(f)
else:
    # Fallback
    RISK_WEIGHTS = {"alineacion_texto": 6}

# Define el modelo para la solicitud (Base64 del PDF)
class PDFRequest(BaseModel):
    pdfbase64: str

# Crear un router para los endpoints
router = APIRouter()


def detectar_texto_sobrepuesto(pdf_bytes: bytes, tolerancia_solapamiento=5):
    """
    Detecta texto sobrepuesto en un PDF comparando coordenadas de palabras.
    - tolerancia_solapamiento: en puntos (pt). Si dos textos están a menos de X pt, se consideran sobrepuestos.
    """
    alertas = []

    pdf_stream = io.BytesIO(pdf_bytes)

    with pdfplumber.open(pdf_stream) as pdf:
        for pagina_num, pagina in enumerate(pdf.pages, start=1):
            palabras = pagina.extract_words(
                x_tolerance=1,
                y_tolerance=1,
                keep_blank_chars=True,
                use_text_flow=False,
                extra_attrs=["top", "bottom", "x0", "x1"]
            )

            if not palabras:
                continue

            # Agrupar por posición vertical aproximada
            grupos_por_fila = defaultdict(list)
            for palabra in palabras:
                clave_fila = round(palabra['top'], 1)
                grupos_por_fila[clave_fila].append(palabra)

            for top, grupo in grupos_por_fila.items():
                for i, p1 in enumerate(grupo):
                    for j, p2 in enumerate(grupo):
                        if i >= j:
                            continue

                        solapamiento_x = max(0, min(p1['x1'], p2['x1']) - max(p1['x0'], p2['x0']))
                        ancho_promedio = (p1['x1'] - p1['x0'] + p2['x1'] - p2['x0']) / 2

                        if solapamiento_x > 0.5 * ancho_promedio:
                            alertas.append({
                                'pagina': pagina_num,
                                'posicion': f"Y≈{top}",
                                'texto1': p1['text'],
                                'coord1': (p1['x0'], p1['top']),
                                'texto2': p2['text'],
                                'coord2': (p2['x0'], p2['top']),
                                'solapamiento_px': round(solapamiento_x, 2)
                            })

    # Construir respuesta con penalización desde risk_weights.json
    if not alertas:
        return {
            "texto_sobrepuesto_detectado": False,
            "detalle": {
                "alineacion_promedio": 1.0,
                "rotacion_promedio": 0.0
            },
            "penalizacion":  0
        }
    else:
        return {
            "texto_sobrepuesto_detectado": True,
            "alertas": alertas,
            "detalle": {
                "alineacion_promedio": 0.0,  # ejemplo si quieres calcular un score
                "rotacion_promedio": 0.0
            },
            "penalizacion": RISK_WEIGHTS.get("alineacion_texto")
        }


@router.post("/api/detectar_texto_sobrepuesto")
def detectar_texto_sobrepuesto_endpoint(pdf_request: PDFRequest):
    """
    Endpoint que recibe un PDF en Base64 y devuelve si se detectó texto sobrepuesto,
    reemplazando el bloque 'Alineación de elementos de texto' y devolviendo penalización.
    """
    try:
        pdf_bytes = base64.b64decode(pdf_request.pdfbase64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al decodificar Base64: {e}")

    resultado = detectar_texto_sobrepuesto(pdf_bytes, tolerancia_solapamiento=5)

    return {
        "check": "Alineación de elementos de texto",
        "detalle": resultado.get("detalle", {}),
        "alertas": resultado.get("alertas", []),
        "penalizacion": resultado.get("penalizacion"),
        "texto_sobrepuesto_detectado": resultado["texto_sobrepuesto_detectado"]
    }
