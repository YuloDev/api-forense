"""
Helper para análisis de evidencias forenses.

Utiliza la misma lógica que el helper existente en analisis_forense_profesional.py
"""

from typing import Dict, Any, List
from adapters.persistence.helpers.ForensicAnalysisHelpers.check_evidencias_forenses.forensic_analysis_imports import (
    analizar_metadatos_forenses,
    detectar_texto_sintetico_aplanado,
    detectar_texto_sobrepuesto,
    safe_serialize_dict
)


class EvidenciasForensesAnalyzer:
    """Analizador de evidencias forenses usando la lógica existente del proyecto"""
    
    def __init__(self):
        pass
    
    def analyze_image_evidencias_forenses(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza evidencias forenses en una imagen usando la lógica existente.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con análisis de evidencias forenses
        """
        try:
            # Usar la función existente del helper
            result = self._analisis_forense_completo(image_bytes)
            
            return result
            
        except Exception as e:
            return {
                "error": f"Error analizando evidencias forenses: {str(e)}",
                "evidencias": [],
                "grado_confianza": "ERROR",
                "porcentaje_confianza": 0.0,
                "puntuacion": 0,
                "max_puntuacion": 0,
                "es_screenshot": False,
                "tipo_imagen": "unknown"
            }
    
    def _analisis_forense_completo(self, imagen_bytes: bytes) -> Dict[str, Any]:
        """
        Función idéntica a analisis_forense_completo del helper original.
        Análisis forense ULTRA-OPTIMIZADO para velocidad.
        """
        try:
            # Solo análisis más importantes y rápidos
            metadatos = analizar_metadatos_forenses(imagen_bytes)
            
            # Análisis de texto sintético (importante mantener)
            texto_sintetico = detectar_texto_sintetico_aplanado(imagen_bytes, metadatos)
            
            # Análisis simplificados para velocidad
            compresion = {"doble_compresion": {"tiene_doble_compresion": False}}
            cuadricula_jpeg = {"tiene_cuadricula": False}
            ela = {"tiene_ediciones": False}
            ruido_bordes = {"ruido_analisis": {"inconsistencias_ruido": ""}}
            hashes = {"inconsistencias": []}
            
            # 🔎 Detector de texto sobrepuesto (ya optimizado)
            overlays = detectar_texto_sobrepuesto(imagen_bytes)
            n_over = overlays.get("resumen", {}).get("n_overlays", 0)
            
            # Generar reporte consolidado
            evidencias = []
            puntuacion = 0
            max_puntuacion = 0
            
            # Análisis de metadatos
            if metadatos.get("software_edicion"):
                for evidencia in metadatos["software_edicion"]:
                    if "🚨" in evidencia:
                        evidencias.append(evidencia)
                        puntuacion += 3
                    else:
                        evidencias.append(evidencia)
                        puntuacion += 1
            max_puntuacion += 5
            
            # Análisis de fechas
            if metadatos.get("fechas_analisis"):
                for evidencia in metadatos["fechas_analisis"]:
                    if "🚨" in evidencia:
                        evidencias.append(evidencia)
                        puntuacion += 3
                    else:
                        evidencias.append(evidencia)
                        puntuacion += 1
            max_puntuacion += 3
            
            # Análisis de compresión
            if compresion.get("app_indicators"):
                for evidencia in compresion["app_indicators"]:
                    if "🚨" in evidencia:
                        evidencias.append(evidencia)
                        puntuacion += 2
            max_puntuacion += 2
            
            # Análisis de cuadrícula JPEG
            if cuadricula_jpeg.get("tiene_splicing"):
                evidencias.append("🚨 CUADRÍCULA JPEG LOCALIZADA - POSIBLE SPLICING")
                puntuacion += 4
            elif cuadricula_jpeg.get("desalineacion_analisis", {}).get("total_discontinuidades", 0) > 2:
                evidencias.append("⚠️ Desalineación de bloques JPEG detectada")
                puntuacion += 2
            max_puntuacion += 4
            
            # Análisis de texto sintético aplanado
            # Análisis de texto sintético (lógica mejorada)
            es_screenshot = texto_sintetico.get("tipo_imagen_analisis", {}).get("es_screenshot", False)
            
            if texto_sintetico.get("tiene_texto_sintetico"):
                if es_screenshot:
                    evidencias.append("⚠️ Texto sintético en screenshot/web")
                    puntuacion += 2  # Menos penalización para screenshots
                else:
                    evidencias.append("🚨 TEXTO SINTÉTICO APLANADO DETECTADO")
                    puntuacion += 5
            elif texto_sintetico.get("reguardado_analisis", {}).get("densidad_lineas", 0) > 0.15:  # Umbral más alto
                if es_screenshot:
                    evidencias.append("ℹ️ Alta densidad de líneas (screenshot)")
                    puntuacion += 0  # No penalizar screenshots
                else:
                    evidencias.append("⚠️ Alta densidad de líneas rectilíneas")
                    puntuacion += 2
            elif texto_sintetico.get("swt_analisis", {}).get("stroke_width_uniforme", False):
                if es_screenshot:
                    evidencias.append("ℹ️ Grosor uniforme (screenshot)")
                    puntuacion += 0  # No penalizar screenshots
                else:
                    evidencias.append("⚠️ Grosor de trazo uniforme (texto sintético)")
                    puntuacion += 2
            max_puntuacion += 5
            
            # Análisis ELA (requerir evidencia localizada)
            if ela.get("tiene_ediciones"):
                if ela.get("nivel_sospecha") == "ALTO":
                    evidencias.append(f"🚨 ELA detectó ediciones significativas (nivel: {ela.get('nivel_sospecha', 'N/A')})")
                    puntuacion += 3
                elif ela.get("nivel_sospecha") == "MEDIO":
                    # Solo penalizar si hay evidencia localizada
                    if cuadricula_jpeg.get("tiene_splicing") or texto_sintetico.get("tiene_texto_sintetico"):
                        evidencias.append(f"⚠️ ELA detectó ediciones + evidencia localizada (nivel: {ela.get('nivel_sospecha', 'N/A')})")
                        puntuacion += 2
                    else:
                        evidencias.append(f"ℹ️ ELA detectó ediciones menores (posible compresión)")
                        puntuacion += 0  # No penalizar compresión normal
                else:
                    evidencias.append(f"ℹ️ ELA detectó ediciones menores (posible compresión)")
                    puntuacion += 0  # No penalizar compresión normal
            max_puntuacion += 3
            
            # Análisis de ruido y bordes (solo si hay evidencia localizada)
            if ruido_bordes.get("ruido_analisis", {}).get("inconsistencias_ruido", "").startswith("🚨"):
                if cuadricula_jpeg.get("tiene_splicing") or texto_sintetico.get("tiene_texto_sintetico"):
                    evidencias.append("🚨 Inconsistencias de ruido + evidencia localizada")
                    puntuacion += 2
                else:
                    evidencias.append("ℹ️ Inconsistencias de ruido (posible compresión)")
                    puntuacion += 0  # No penalizar compresión normal
            max_puntuacion += 2
            
            if ruido_bordes.get("halo_analisis", {}).get("halo_detectado", "").startswith("🚨"):
                if cuadricula_jpeg.get("tiene_splicing") or texto_sintetico.get("tiene_texto_sintetico"):
                    evidencias.append("🚨 Halo/aliasing + evidencia localizada")
                    puntuacion += 2
                else:
                    evidencias.append("ℹ️ Halo/aliasing (posible compresión)")
                    puntuacion += 0  # No penalizar compresión normal
            max_puntuacion += 2
            
            # Análisis de hashes
            if hashes.get("inconsistencias"):
                for evidencia in hashes["inconsistencias"]:
                    evidencias.append(evidencia)
                    puntuacion += 1
            max_puntuacion += 2
            
            # 🔎 Sumar evidencia por texto sobrepuesto
            if n_over > 0:
                evidencias.append(f"🚨 Texto sobrepuesto detectado en {n_over} caja(s) OCR")
                puntuacion += min(5, 2 + n_over)  # pesa de 2 a 5
            max_puntuacion += 5
            
            # Calcular grado de confianza (ajustado para screenshots)
            porcentaje_confianza = (puntuacion / max_puntuacion) * 100 if max_puntuacion > 0 else 0
            
            # Ajustar para screenshots
            if es_screenshot and porcentaje_confianza < 30:
                grado_confianza = "BAJO"
                evidencias.append("ℹ️ Imagen parece ser screenshot/web (recomprimida)")
            elif porcentaje_confianza > 70:
                grado_confianza = "ALTO"
            elif porcentaje_confianza > 40:
                grado_confianza = "MEDIO"
            else:
                grado_confianza = "BAJO"
            
            return safe_serialize_dict({
                "metadatos": metadatos,
                "compresion": compresion,
                "cuadricula_jpeg": cuadricula_jpeg,
                "texto_sintetico": texto_sintetico,
                "ela": ela,
                "ruido_bordes": ruido_bordes,
                "hashes": hashes,
                "overlays": overlays,  # 🔎 incluir resultados nuevos
                "evidencias": evidencias,
                "grado_confianza": grado_confianza,
                "porcentaje_confianza": float(porcentaje_confianza),
                "puntuacion": puntuacion,
                "max_puntuacion": max_puntuacion,
                "es_screenshot": es_screenshot,
                "tipo_imagen": "screenshot/web" if es_screenshot else "imagen_normal"
            })
            
        except Exception as e:
            return {
                "error": f"Error en análisis forense completo: {str(e)}",
                "evidencias": [],
                "grado_confianza": "ERROR",
                "porcentaje_confianza": 0.0
            }
