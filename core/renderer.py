import os
import time
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from .config import FFMPEG_EXE, CUDA_AVAILABLE
from .reframer import build_reframe_filter

def escape_ffmpeg_filter_path(path: Path) -> str:
    """
    Escapa adecuadamente rutas en Windows para filtros de FFmpeg (subtitles/ass).
    Convierte 'D:\\foo\\bar.ass' en 'D\\:/foo/bar.ass' para evitar que FFmpeg interprete los ':' como separadores de opciones.
    """
    posix_path = str(path.resolve()).replace("\\", "/")
    if len(posix_path) > 1 and posix_path[1] == ":":
        posix_path = posix_path[0] + "\\:" + posix_path[2:]
    # Escapar comillas simples si las hubiera
    posix_path = posix_path.replace("'", "\\'")
    return posix_path

def render_vertical_clip(
    source_video_path: Path,
    start_time: float,
    duration: float,
    output_path: Path,
    framing_mode: str = "smart_face",
    subtitles_path: Optional[Path] = None,
    use_nvenc: bool = True
) -> Dict[str, Any]:
    """
    Renderiza un clip vertical 9:16 (1080x1920) recortado y subtitulado
    con aceleración por hardware NVIDIA NVENC en la RTX 4060.
    """
    if not source_video_path.exists():
        raise FileNotFoundError(f"Video origen no encontrado: {source_video_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    start_bench = time.time()

    # 1. Construir filtro de encuadre 9:16
    base_filter = build_reframe_filter(
        mode=framing_mode,
        source_path=source_video_path,
        start_time=start_time,
        duration=duration
    )

    # 2. Agregar filtro de subtítulos ASS si se proporcionó
    if subtitles_path and subtitles_path.exists():
        escaped_sub = escape_ffmpeg_filter_path(subtitles_path)
        filter_complex = f"{base_filter};[v_out]ass='{escaped_sub}'[final_v]"
    else:
        filter_complex = f"{base_filter};[v_out]null[final_v]"

    # 3. Determinar codificador de video (NVENC para RTX 4060 o x264 software)
    use_gpu_encoder = use_nvenc and CUDA_AVAILABLE
    
    cmd = [
        str(FFMPEG_EXE),
        "-y",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", str(source_video_path),
        "-filter_complex", filter_complex,
        "-map", "[final_v]",
        "-map", "0:a?",
    ]

    if use_gpu_encoder:
        cmd.extend([
            "-c:v", "h264_nvenc",
            "-preset", "p4",           # Calidad balanceada en NVENC
            "-b:v", "6000k",           # Bitrate óptimo para 1080x1920
            "-maxrate", "8000k",
            "-bufsize", "12000k",
            "-pix_fmt", "yuv420p"
        ])
    else:
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p"
        ])

    # Normalización de audio para presencia en smartphones
    cmd.extend([
        "-c:a", "aac",
        "-b:a", "192k",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-movflags", "+faststart",
        str(output_path)
    ])

    print(f"🎬 Iniciando renderizado de clip [{framing_mode}] | NVENC: {use_gpu_encoder} | Salida: {output_path.name}")
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    # Si falla con NVENC, reintentar automáticamente con libx264
    if res.returncode != 0 and use_gpu_encoder:
        print("⚠️ Fallo en codificador NVENC, reintentando con libx264 CPU...")
        cmd_fallback = [
            str(FFMPEG_EXE), "-y",
            "-ss", str(start_time), "-t", str(duration),
            "-i", str(source_video_path),
            "-filter_complex", filter_complex,
            "-map", "[final_v]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path)
        ]
        res = subprocess.run(cmd_fallback, capture_output=True, text=True)

    if res.returncode != 0:
        err_msg = res.stderr[-800:] if res.stderr else "Error desconocido en FFmpeg"
        raise RuntimeError(f"Error al renderizar el clip con FFmpeg:\n{err_msg}")

    elapsed = round(time.time() - start_bench, 2)
    file_size_mb = round(output_path.stat().st_size / (1024 * 1024), 2)
    
    print(f"✅ Clip generado exitosamente en {elapsed}s ({file_size_mb} MB) -> {output_path.name}")

    return {
        "output_path": str(output_path.resolve()),
        "filename": output_path.name,
        "elapsed_seconds": elapsed,
        "file_size_mb": file_size_mb,
        "used_nvenc": use_gpu_encoder
    }
