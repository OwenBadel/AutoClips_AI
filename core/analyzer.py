import os
import json
import re
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from .config import GEMINI_API_KEY, DEFAULT_GEMINI_MODEL

def format_timestamp(seconds: float) -> str:
    """Convierte segundos a formato MM:SS o HH:MM:SS."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def clean_json_response(raw_text: str) -> str:
    """Elimina delimitadores markdown ```json y ``` del output del LLM."""
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
        raw_text = re.sub(r"\n?```$", "", raw_text)
    return raw_text.strip()

def analyze_viral_moments_gemini(
    segments: List[Dict[str, Any]],
    video_duration: float,
    min_clip_duration: int = 30,
    max_clip_duration: int = 65,
    num_clips: int = 4
) -> List[Dict[str, Any]]:
    """
    Utiliza Gemini 3.6 Flash para analizar la transcripción completa del video e
    identificar los segmentos con mayor potencial viral para Shorts/TikTok/Kwai/Reels.
    """
    if not GEMINI_API_KEY:
        print("⚠️ No hay GEMINI_API_KEY configurada. Usando analizador heurístico de respaldo.")
        return fallback_heuristic_clips(segments, video_duration, min_clip_duration, max_clip_duration, num_clips)

    genai.configure(api_key=GEMINI_API_KEY)
    
    # Construir transcripción cronometrada comprimida
    transcript_lines = []
    for s in segments:
        start_str = format_timestamp(s["start"])
        end_str = format_timestamp(s["end"])
        transcript_lines.append(f"[{start_str} - {end_str}] {s['text']}")
    
    compact_transcript = "\n".join(transcript_lines)

    system_prompt = f"""
Eres un Estratega Experto en Redes Sociales y Director de Contenido Viral para TikTok, YouTube Shorts, Instagram Reels y Kwai.
Tu tarea es analizar la siguiente transcripción completa de un video de larga duración ({format_timestamp(video_duration)}) y seleccionar exactamente los {num_clips} MEJORES momentos para convertirlos en clips verticales virales.

CRITERIOS FUNDAMENTALES PARA CADA CLIP:
1. DURACIÓN: Cada clip DEBE durar obligatoriamente entre {min_clip_duration} y {max_clip_duration} segundos.
2. GANCHO (HOOK) INICIAL: Los primeros 3-5 segundos deben capturar la atención de inmediato (una afirmación impactante, una pregunta polémica, un dato sorprendente o una historia intrigante).
3. AUTOCONTENIDO: El clip debe tener sentido por sí mismo, con un inicio claro, un desarrollo interesante y una conclusión o remate potente sin dejar la idea a medias.
4. MÁXIMA RETENCIÓN: Prioriza momentos de alto valor educativo, revelaciones, debates acalorados, humor o reflexiones inspiradoras.

DEBES RESPONDER EXCLUSIVAMENTE EN FORMATO JSON VÁLIDO CON LA SIGUIENTE ESTRUCTURA EXACTA (SIN TEXTO ADICIONAL NI MARKDOWN FUERA DEL JSON):
{{
  "clips": [
    {{
      "start_time": 124.5,
      "end_time": 178.0,
      "title": "¡El Error Más Grave Que Todos Cometen! 😱",
      "hook": "La primera frase potente del clip",
      "virality_score": 95,
      "virality_reason": "Empieza con una revelación contraria al sentido común y remata con un ejemplo contundente.",
      "summary": "Explica por qué no debes cometer este error al emprender.",
      "hashtags": ["#Shorts", "#TikTok", "#Consejos", "#Viral", "#Aprende"]
    }}
  ]
}}
IMPORTANTE: 'start_time' y 'end_time' deben ser números flotantes en SEGUNDOS exactos basados en la transcripción.
"""

    try:
        model = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)
        response = model.generate_content(
            [system_prompt, f"TRANSCRIPCIÓN COMPLETA DEL VIDEO:\n{compact_transcript}"]
        )
        
        cleaned = clean_json_response(response.text)
        data = json.loads(cleaned)
        clips = data.get("clips", [])
        
        # Validar y normalizar los clips obtenidos
        validated_clips = []
        for c in clips:
            st = float(c.get("start_time", 0))
            et = float(c.get("end_time", st + min_clip_duration))
            duration = round(et - st, 2)
            
            # Ajustar límites
            if duration < min_clip_duration:
                et = min(video_duration, st + min_clip_duration)
                duration = round(et - st, 2)
            elif duration > max_clip_duration:
                et = st + max_clip_duration
                duration = round(et - st, 2)

            validated_clips.append({
                "start_time": round(st, 2),
                "end_time": round(et, 2),
                "duration": duration,
                "title": c.get("title", f"Momento Destacado {format_timestamp(st)}"),
                "hook": c.get("hook", ""),
                "virality_score": int(c.get("virality_score", 85)),
                "virality_reason": c.get("virality_reason", "Segmento con alta densidad de valor."),
                "summary": c.get("summary", ""),
                "hashtags": c.get("hashtags", ["#Shorts", "#TikTok", "#Viral"])
            })

        if validated_clips:
            # Ordenar por puntuación de viralidad descendente
            validated_clips.sort(key=lambda x: x["virality_score"], reverse=True)
            return validated_clips[:num_clips]

    except Exception as e:
        print(f"⚠️ Error al consultar Gemini API: {e}. Activando modo heurístico.")

    return fallback_heuristic_clips(segments, video_duration, min_clip_duration, max_clip_duration, num_clips)

def fallback_heuristic_clips(
    segments: List[Dict[str, Any]],
    video_duration: float,
    min_clip_duration: int = 30,
    max_clip_duration: int = 65,
    num_clips: int = 4
) -> List[Dict[str, Any]]:
    """
    Algoritmo heurístico local para extraer clips representativos cuando no hay conexión
    o se sobrepasa la cuota de la API.
    """
    if not segments or video_duration <= min_clip_duration:
        return [{
            "start_time": 0.0,
            "end_time": min(video_duration, float(max_clip_duration)),
            "duration": round(min(video_duration, float(max_clip_duration)), 2),
            "title": "Clip Principal Viral 🔥",
            "hook": "Inicio del video",
            "virality_score": 85,
            "virality_reason": "Selección automática del tramo inicial más relevante.",
            "summary": "Momento introductorio destacado.",
            "hashtags": ["#Shorts", "#TikTok", "#Viral"]
        }]

    # Dividir el video en ventanas y buscar segmentos con mayor densidad de palabras
    clips = []
    step = max(30.0, video_duration / (num_clips + 1))
    
    for i in range(num_clips):
        target_start = (i + 0.5) * step
        if target_start + min_clip_duration > video_duration:
            target_start = max(0.0, video_duration - min_clip_duration)

        # Encontrar el segmento más cercano
        closest_seg = min(segments, key=lambda s: abs(s["start"] - target_start))
        st = closest_seg["start"]
        et = min(video_duration, st + 45.0)

        clips.append({
            "start_time": round(st, 2),
            "end_time": round(et, 2),
            "duration": round(et - st, 2),
            "title": f"Parte {i+1}: Revelación Clave 💡",
            "hook": closest_seg.get("text", "")[:60] + "...",
            "virality_score": 80 - i * 2,
            "virality_reason": "Segmento con alta actividad vocal continua.",
            "summary": f"Tramo en el minuto {format_timestamp(st)} con contenido dinámico.",
            "hashtags": ["#Shorts", "#Viral", "#TikTok", "#Reels"]
        })

    return clips
