from pathlib import Path
from typing import List, Dict, Any

def format_ass_time(seconds: float) -> str:
    """Convierte segundos a formato ASS timestamp H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def generate_ass_subtitles(
    segments: List[Dict[str, Any]],
    clip_start: float,
    clip_end: float,
    output_path: Path,
    style_preset: str = "karaoke_yellow",
    font_name: str = "Arial Black",
    font_size: int = 42,
    margin_v: int = 340
) -> Path:
    """
    Genera un archivo de subtítulos .ass dinámico estilo TikTok / Hormozi
    con efecto de resaltado karaoke y posición vertical óptima.
    """
    # Configuración de colores según preset (formato ASS es &HAABBGGRR&)
    if style_preset == "karaoke_yellow":
        highlight_color = "&H0000FFFF&" # Amarillo vibrante en BGR
        base_color = "&H00FFFFFF&"      # Blanco puro
    elif style_preset == "karaoke_green":
        highlight_color = "&H0033FF00&" # Verde lima neón
        base_color = "&H00FFFFFF&"
    elif style_preset == "karaoke_cyan":
        highlight_color = "&H00FFFF00&" # Cyan neón
        base_color = "&H00FFFFFF&"
    else:
        highlight_color = "&H0000FFFF&"
        base_color = "&H00FFFFFF&"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokDefault,{font_name},{font_size},{base_color},&H000000FF&,&H00000000&,&H80000000&,-1,0,0,0,100,100,0,0,1,5.0,2.5,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []

    # Filtrar segmentos dentro del rango del clip y ajustar tiempos relativos
    clip_segments = [s for s in segments if s["end"] > clip_start and s["start"] < clip_end]

    for seg in clip_segments:
        # Verificar si tenemos marcas de tiempo a nivel de palabra
        words = seg.get("words", [])
        if words:
            # Agrupar palabras en paquetes de 3 a 5 palabras para ritmo dinámico en pantalla
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i + chunk_size]
                if not chunk:
                    continue

                chunk_start = max(0.0, chunk[0]["start"] - clip_start)
                chunk_end = max(chunk_start + 0.3, chunk[-1]["end"] - clip_start)

                if chunk_end <= 0 or chunk_start >= (clip_end - clip_start):
                    continue

                # Generar evento con cada palabra resaltada individualmente durante su pronunciación
                for current_idx, active_word in enumerate(chunk):
                    w_start = max(0.0, active_word["start"] - clip_start)
                    w_end = max(w_start + 0.15, active_word["end"] - clip_start)
                    
                    if w_end <= 0 or w_start >= (clip_end - clip_start):
                        continue

                    # Construir la línea donde active_word está en highlight_color
                    rendered_words = []
                    for w_idx, w in enumerate(chunk):
                        word_text = w["word"].upper()
                        if w_idx == current_idx:
                            rendered_words.append(f"{{\\c{highlight_color}\\b1}}{word_text}{{\\c{base_color}\\b0}}")
                        else:
                            rendered_words.append(word_text)

                    line_text = " ".join(rendered_words)
                    events.append(
                        f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},TikTokDefault,,0,0,0,,{line_text}"
                    )
        else:
            # Subtítulos estándar sin división por palabra
            s_start = max(0.0, seg["start"] - clip_start)
            s_end = min(clip_end - clip_start, seg["end"] - clip_start)
            if s_end > s_start:
                text = seg["text"].upper()
                events.append(
                    f"Dialogue: 0,{format_ass_time(s_start)},{format_ass_time(s_end)},TikTokDefault,,0,0,0,,{{\\b1}}{text}{{\\b0}}"
                )

    ass_content = header + "\n".join(events) + "\n"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    return output_path
