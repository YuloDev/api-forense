# pdf_overlapping_detection.py
import pdfplumber
import base64
from collections import defaultdict
import io
 
def _detect_text_overlapping(extracted_text: str) -> bool:
    """
    Analiza el texto extraído para detectar superposiciones y duplicaciones
    que pueden indicar capas múltiples.
    """
    if not extracted_text:
        return False  # No hay texto, no puede haber superposición
    lines = [line.strip() for line in extracted_text.split('\n') if line.strip()]
    # Detectar líneas duplicadas exactas
    line_counts = Counter(lines)
    duplicates = {line: count for line, count in line_counts.items() if count > 1}
    if duplicates:
        return True  # Si hay líneas duplicadas, hay superposición
    # Detectar líneas similares
    similar_pairs = []
    for i, line1 in enumerate(lines):
        for j, line2 in enumerate(lines[i+1:], i+1):
            similarity = SequenceMatcher(None, line1, line2).ratio()
            if 0.7 <= similarity < 1.0:  # Muy similar pero no idéntica
                similar_pairs.append((line1, line2, similarity))
    if similar_pairs:
        return True  # Si hay líneas similares, hay superposición
    return False  # Si no se encuentran duplicados ni líneas similares, no hay superposición
 
 
def detectar_texto_sobrepuesto_base64(pdf_base64: str, tolerancia_solapamiento: float = 5.0) -> bool:
    """
    Detecta si hay texto sobrepuesto en un PDF en base64 comparando coordenadas de palabras.
    Args:
        pdf_base64: El archivo PDF en formato Base64
        tolerancia_solapamiento: En puntos (pt). Si dos textos están a menos de X pt, se consideran sobrepuestos.
    Returns:
        bool: Si se detectó texto sobrepuesto
    """
    try:
        # Decodificar el PDF desde Base64
        pdf_bytes = base64.b64decode(pdf_base64)
    except Exception as e:
        print(f"❌ Error al decodificar Base64: {e}")
        return False
    # Crear un objeto BytesIO a partir de los bytes decodificados
    pdf_stream = io.BytesIO(pdf_bytes)
 
    try:
        with pdfplumber.open(pdf_stream) as pdf:
            extracted_text = ""
            for pagina_num, pagina in enumerate(pdf.pages, start=1):
                palabras = pagina.extract_words(
                    x_tolerance=1,
                    y_tolerance=1,
                    keep_blank_chars=True,
                    use_text_flow=False,
                    extra_attrs=["top", "bottom", "x0", "x1"]
                )
                for palabra in palabras:
                    extracted_text += palabra['text'] + " "
        # Verificar si hay superposición de texto
        return _detect_text_overlapping(extracted_text)
    except Exception as e:
        print(f"❌ Error al procesar el archivo PDF: {e}")
        return False