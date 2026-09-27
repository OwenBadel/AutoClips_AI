import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from .config import DOWNLOADS_DIR, FFMPEG_EXE, FFMPEG_DIR

def extract_video_id(url: str) -> Optional[str]:
    """Extrae el ID del video de YouTube a partir de diversas variantes de URL."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/shorts\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/live\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def sanitize_filename(name: str) -> str:
    """Limpia una cadena para usarla con seguridad como nombre de archivo en Windows."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()[:80]

def get_video_info(url_or_path: str) -> Dict[str, Any]:
    """
    Obtiene los metadatos de un video de YouTube o de un archivo local.
    """
    # Si es un archivo local existente
    local_file = Path(url_or_path)
    if local_file.exists() and local_file.is_file():
        return {
            "id": local_file.stem,
            "title": local_file.stem,
            "duration": 0,
            "uploader": "Archivo Local",
            "thumbnail": "",
            "is_local": True,
            "source_path": str(local_file.resolve())
        }

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'ffmpeg_location': str(Path(FFMPEG_EXE).parent)
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_or_path, download=False)
        video_id = info.get('id', 'video')
        title = info.get('title', 'Video sin título')
        duration = info.get('duration', 0)
        uploader = info.get('uploader') or info.get('channel', 'Canal de YouTube')
        thumbnail = info.get('thumbnail', '')
        chapters = info.get('chapters', [])

        return {
            "id": video_id,
            "title": title,
            "duration": duration,
            "uploader": uploader,
            "thumbnail": thumbnail,
            "chapters": chapters,
            "is_local": False,
            "url": url_or_path
        }

def fetch_youtube_subtitles(url_or_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Intenta extraer subtítulos ya existentes en YouTube (español o inglés).
    Ahorra el 100% del tiempo de transcripción cuando están disponibles.
    """
    video_id = extract_video_id(url_or_id) or url_or_id
    if len(video_id) != 11:
        return None

    try:
        # Intentar obtener transcripciones en español, luego en inglés
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        transcript = None
        # Buscar manuales en español
        try:
            transcript = transcript_list.find_manually_created_transcript(['es', 'es-419', 'es-ES'])
        except Exception:
            pass

        # Buscar generados automáticamente en español
        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript(['es', 'es-419', 'es-ES'])
            except Exception:
                pass

        # Si no hay español, buscar en inglés
        if not transcript:
            try:
                transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
            except Exception:
                pass

        if transcript:
            fetched = transcript.fetch()
            # Formatear estándar
            formatted = []
            for item in fetched:
                start = float(item.get('start', 0.0))
                duration = float(item.get('duration', 0.0))
                text = str(item.get('text', '')).strip().replace('\n', ' ')
                if text:
                    formatted.append({
                        "start": start,
                        "end": start + duration,
                        "duration": duration,
                        "text": text
                    })
            return formatted
    except Exception as e:
        # No hay subtítulos o no están permitidos
        pass
    return None

def download_audio_for_transcription(url_or_path: str, video_id: str, progress_hook=None) -> Path:
    """
    Descarga la pista de audio optimizada (m4a/opus/mp3) para Faster-Whisper.
    """
    local_file = Path(url_or_path)
    if local_file.exists():
        return local_file

    output_template = str(DOWNLOADS_DIR / f"{video_id}_audio.%(ext)s")
    
    ydl_opts = {
        'format': 'ba/b',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_DIR,
    }

    if progress_hook:
        ydl_opts['progress_hooks'] = [progress_hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_or_path])

    # Buscar el archivo de audio descargado
    candidates = list(DOWNLOADS_DIR.glob(f"{video_id}_audio.*"))
    if candidates:
        return candidates[0]

    return DOWNLOADS_DIR / f"{video_id}_audio.m4a"

def download_full_video(url_or_path: str, video_id: str, max_height: int = 1080, progress_hook=None) -> Path:
    """
    Descarga el video completo en calidad HD (hasta 1080p o 720p) con contenedor MP4.
    """
    local_file = Path(url_or_path)
    if local_file.exists():
        return local_file

    target_path = DOWNLOADS_DIR / f"{video_id}_source.mp4"
    if target_path.exists() and target_path.stat().st_size > 1024 * 1024:
        return target_path

    ydl_opts = {
        'format': f'bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={max_height}][ext=mp4]/best',
        'outtmpl': str(target_path),
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_DIR,
        'merge_output_format': 'mp4'
    }

    if progress_hook:
        ydl_opts['progress_hooks'] = [progress_hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_or_path])

    return target_path
