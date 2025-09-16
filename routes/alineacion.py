from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import base64
import pdfplumber
from collections import defaultdict
import io

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

    
    
    # Crear un objeto BytesIO a partir de los bytes decodificados
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
                # Redondear 'top' para agrupar en la misma línea
                clave_fila = round(palabra['top'], 1)
                grupos_por_fila[clave_fila].append(palabra)

            for top, grupo in grupos_por_fila.items():
                # Comparar cada par de palabras en la misma fila
                for i, p1 in enumerate(grupo):
                    for j, p2 in enumerate(grupo):
                        if i >= j:
                            continue  # Evitar comparar consigo mismo o repetir pares

                        # Calcular solapamiento horizontal
                        solapamiento_x = max(0, min(p1['x1'], p2['x1']) - max(p1['x0'], p2['x0']))
                        ancho_promedio = (p1['x1'] - p1['x0'] + p2['x1'] - p2['x0']) / 2

                        # Si solapamiento > 50% del ancho promedio → ALERTA
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
    
    if not alertas:
        return {"texto_sobrepuesto_detectado": False}
    else:
        return {"texto_sobrepuesto_detectado": True, "alertas": alertas}


@router.post("/api/detectar_texto_sobrepuesto")
def detectar_texto_sobrepuesto_endpoint(pdf_request: PDFRequest):
    """
    Endpoint que recibe un PDF en Base64 y devuelve si se detectó texto sobrepuesto.
    """
    try:
        # Decodificar el PDF desde Base64
        pdf_bytes = base64.b64decode(pdf_request.pdfbase64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al decodificar Base64: {e}")
    
    # Llamar a la función para detectar texto sobrepuesto (con tolerancia predeterminada de 5)
    resultado = detectar_texto_sobrepuesto(pdf_bytes, tolerancia_solapamiento=5)
    
    return resultado


@router.get("/api/health")
def health():
    """
    Verifica el estado de la API.
    """
    return {
        "ok": True,
        "mode": "json + easyocr + compare-products + risk",
        "app_version": "1.50.0-risk",
    }
