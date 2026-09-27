import os
import json
import time
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from .config import DOWNLOADS_DIR, OUTPUTS_DIR, CUDA_AVAILABLE, GPU_NAME
from .downloader import (
    get_video_info,
    fetch_youtube_subtitles,
    download_audio_for_transcription,
    download_full_video,
    sanitize_filename
)
from .transcriber import transcribe_audio_gpu
from .analyzer import analyze_viral_moments_gemini
from .subtitles import generate_ass_subtitles
from .renderer import render_vertical_clip

class AutoClipsPipeline:
    """
    Orquestador principal que ejecuta el flujo completo de transformación
    de video de YouTube a clips verticales virales listos para publicar.
    """

    def __init__(self, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.progress_callback = progress_callback

    def notify(self, stage: str, percent: float, message: str, data: Optional[Dict[str, Any]] = None):
        if self.progress_callback:
            payload = {
                "stage": stage,
                "percent": round(percent, 1),
                "message": message,
                "timestamp": time.time(),
                "data": data or {}
            }
            self.progress_callback(payload)
        print(f"[{percent:5.1f}%] [{stage.upper()}] {message}")

    def run(
        self,
        url_or_path: str,
        num_clips: int = 3,
        min_duration: int = 30,
        max_duration: int = 60,
        framing_mode: str = "smart_face",
        subtitle_style: str = "karaoke_yellow",
        model_size: str = "base",
        force_whisper: bool = False
    ) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo de generación de clips.
        """
        start_time_total = time.time()

        # 1. Obtener información básica del video
        self.notify("info", 5.0, "Analizando metadatos del video...")
        info = get_video_info(url_or_path)
        video_id = info["id"]
        title = info["title"]
        video_duration = info["duration"]
        clean_title = sanitize_filename(title)

        self.notify("info", 10.0, f"Video identificado: {title[:50]}... ({int(video_duration//60)} min)", info)

        # 2. Obtener transcripción (vía YouTube Subtitles o Faster-Whisper GPU)
        transcript_segments = None
        
        if not force_whisper and not info.get("is_local"):
            self.notify("transcribe_check", 12.0, "Verificando subtítulos nativos en YouTube...")
            transcript_segments = fetch_youtube_subtitles(url_or_path)
            if transcript_segments:
                self.notify("transcribe_check", 25.0, "✅ Subtítulos de YouTube encontrados. Ahorro de transcripción activado.")

        if not transcript_segments:
            # Descargar audio para Faster-Whisper
            self.notify("download_audio", 15.0, "Descargando pista de audio para análisis de voz...")
            audio_path = download_audio_for_transcription(url_or_path, video_id)

            # Transcribir en GPU NVIDIA RTX 4060
            def whisper_cb(pct, msg):
                # Escalar progreso de Whisper entre 20% y 45%
                scaled_pct = 20.0 + (pct / 100.0) * 25.0
                self.notify("transcribing_gpu", scaled_pct, msg)

            whisper_result = transcribe_audio_gpu(
                audio_path=audio_path,
                model_size=model_size,
                progress_callback=whisper_cb
            )
            transcript_segments = whisper_result["segments"]
            if video_duration <= 0:
                video_duration = whisper_result["duration"]

        self.notify("transcribe_complete", 48.0, f"Transcripción lista con {len(transcript_segments)} segmentos.")

        # 3. Análisis Inteligente con Gemini 3.6 Flash
        self.notify("analyzing_viral", 52.0, "Analizando momentos virales con Gemini 3.6 Flash...")
        analyzed_clips = analyze_viral_moments_gemini(
            segments=transcript_segments,
            video_duration=video_duration or 300.0,
            min_clip_duration=min_duration,
            max_clip_duration=max_duration,
            num_clips=num_clips
        )

        if not analyzed_clips:
            raise RuntimeError("No se pudieron determinar momentos virales en el video.")

        self.notify("analyzed_viral", 60.0, f"¡{len(analyzed_clips)} momentos virales detectados con alto potencial!", {"clips": analyzed_clips})

        # 4. Descargar video completo HD (si aún no se ha descargado)
        self.notify("download_video", 62.0, "Preparando flujo de video HD para renderizado...")
        source_video_path = download_full_video(url_or_path, video_id)

        # 5. Generación y Renderizado de cada Clip
        job_output_folder = OUTPUTS_DIR / f"{video_id}_{int(time.time())}"
        job_output_folder.mkdir(parents=True, exist_ok=True)

        rendered_clips_data = []
        total_clips = len(analyzed_clips)

        for idx, clip in enumerate(analyzed_clips):
            clip_num = idx + 1
            st = clip["start_time"]
            et = clip["end_time"]
            dur = clip["duration"]
            clip_title = clip["title"]
            clean_clip_title = sanitize_filename(f"clip_{clip_num}_{clip_title}")

            base_progress = 65.0 + (idx / total_clips) * 30.0
            self.notify("rendering_clip", base_progress, f"Procesando Clip {clip_num}/{total_clips}: {clip_title[:40]}...")

            # A. Generar archivo de subtítulos ASS
            sub_file = None
            if subtitle_style != "none":
                sub_file = job_output_folder / f"{clean_clip_title}.ass"
                generate_ass_subtitles(
                    segments=transcript_segments,
                    clip_start=st,
                    clip_end=et,
                    output_path=sub_file,
                    style_preset=subtitle_style
                )

            # B. Renderizar con FFmpeg + NVENC
            clip_out_path = job_output_folder / f"{clean_clip_title}.mp4"
            render_res = render_vertical_clip(
                source_video_path=source_video_path,
                start_time=st,
                duration=dur,
                output_path=clip_out_path,
                framing_mode=framing_mode,
                subtitles_path=sub_file,
                use_nvenc=CUDA_AVAILABLE
            )

            # C. Guardar metadata del clip individual
            clip_meta = {
                **clip,
                "clip_index": clip_num,
                "file_path": render_res["output_path"],
                "file_name": render_res["filename"],
                "file_size_mb": render_res["file_size_mb"],
                "render_time_s": render_res["elapsed_seconds"],
                "framing_mode": framing_mode,
                "subtitle_style": subtitle_style,
                "used_nvenc": render_res["used_nvenc"]
            }
            rendered_clips_data.append(clip_meta)

        # 6. Crear archivo ZIP empaquetado con todos los clips y su descripción
        self.notify("packaging", 96.0, "Empaquetando clips y metadatos virales en archivo ZIP...")
        zip_filename = f"{clean_title[:30]}_Shorts_Pack.zip"
        zip_path = job_output_folder / zip_filename

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Añadir videos
            for c in rendered_clips_data:
                p = Path(c["file_path"])
                if p.exists():
                    zipf.write(p, arcname=p.name)
            
            # Añadir resumen de textos, ganchos y hashtags para copiar y pegar
            summary_txt = [f"=== CLIPS VIRALES GENERADOS POR AUTOCLIPS AI ===\nVideo Original: {title}\nTotal Clips: {len(rendered_clips_data)}\n\n"]
            for c in rendered_clips_data:
                summary_txt.append(f"--- CLIP {c['clip_index']}: {c['title']} ---")
                summary_txt.append(f"Puntuación Viral: {c['virality_score']}/100")
                summary_txt.append(f"Gancho: {c['hook']}")
                summary_txt.append(f"Resumen: {c['summary']}")
                summary_txt.append(f"Hashtags sugeridos: {' '.join(c['hashtags'])}\n")
            
            zipf.writestr("COPIAR_Y_PEGAR_HASHTAGS.txt", "\n".join(summary_txt))

        total_elapsed = round(time.time() - start_time_total, 2)
        
        final_result = {
            "success": True,
            "video_id": video_id,
            "title": title,
            "total_duration_seconds": video_duration,
            "total_clips_generated": len(rendered_clips_data),
            "total_process_time_seconds": total_elapsed,
            "hardware": {
                "gpu": GPU_NAME,
                "cuda": CUDA_AVAILABLE,
                "nvenc_used": CUDA_AVAILABLE
            },
            "job_folder": str(job_output_folder.resolve()),
            "zip_path": str(zip_path.resolve()),
            "zip_filename": zip_filename,
            "clips": rendered_clips_data
        }

        self.notify("complete", 100.0, f"¡Proceso completado con éxito en {total_elapsed}s!", final_result)
        return final_result
