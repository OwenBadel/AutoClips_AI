import os
import sys
import unittest
import subprocess
from pathlib import Path

# Asegurar encoding UTF-8 en consola de Windows para emojis
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Añadir el directorio del proyecto al path
PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

from core.config import get_system_status, FFMPEG_EXE, CUDA_AVAILABLE, GPU_NAME
from core.subtitles import generate_ass_subtitles
from core.renderer import render_vertical_clip
from core.analyzer import analyze_viral_moments_gemini, fallback_heuristic_clips

class TestAutoClipsStudio(unittest.TestCase):

    def test_01_system_status_and_gpu(self):
        """Verifica que el sistema detecte la GPU NVIDIA RTX 4060 y FFmpeg."""
        status = get_system_status()
        self.assertTrue(status["cuda_available"], "CUDA debe estar disponible en la máquina del usuario.")
        self.assertIn("RTX 4060", status["gpu_name"], f"Se esperaba RTX 4060, detectada: {status['gpu_name']}")
        self.assertTrue(Path(status["ffmpeg_path"]).exists(), "El binario de FFmpeg debe existir.")
        print(f"\n[OK] GPU Detectada: {status['gpu_name']} ({status['vram_gb']} GB) | CUDA: {status['cuda_available']}")

    def test_02_nvenc_hardware_encoding(self):
        """Verifica que el codificador por hardware NVENC funcione correctamente en FFmpeg."""
        test_output = PROJECT_DIR / "storage" / "test_nvenc_render.mp4"
        if test_output.exists():
            test_output.unlink()

        cmd = [
            str(FFMPEG_EXE), "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=1080x1920:rate=30",
            "-c:v", "h264_nvenc", "-preset", "fast",
            str(test_output)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Error en NVENC: {res.stderr}")
        self.assertTrue(test_output.exists() and test_output.stat().st_size > 0)
        test_output.unlink()
        print("\n[OK] Codificador por Hardware NVIDIA NVENC verificado exitosamente.")

    def test_03_ass_subtitles_generation(self):
        """Verifica la generación de archivo ASS con estilo dinámico y marcas de tiempo."""
        sample_segments = [
            {
                "id": 0,
                "start": 0.0,
                "end": 2.5,
                "text": "Bienvenidos al estudio de clips virales",
                "words": [
                    {"word": "Bienvenidos", "start": 0.0, "end": 0.6},
                    {"word": "al", "start": 0.6, "end": 0.8},
                    {"word": "estudio", "start": 0.8, "end": 1.4},
                    {"word": "de", "start": 1.4, "end": 1.6},
                    {"word": "clips", "start": 1.6, "end": 2.0},
                    {"word": "virales", "start": 2.0, "end": 2.5}
                ]
            }
        ]
        sub_path = PROJECT_DIR / "storage" / "test_sample.ass"
        generate_ass_subtitles(
            segments=sample_segments,
            clip_start=0.0,
            clip_end=2.5,
            output_path=sub_path,
            style_preset="karaoke_yellow"
        )
        self.assertTrue(sub_path.exists())
        content = sub_path.read_text(encoding="utf-8")
        self.assertIn("TikTokDefault", content)
        self.assertIn("BIENVENIDOS", content)
        sub_path.unlink()
        print("\n[OK] Generador de subtítulos ASS dinámico verificado exitosamente.")

    def test_04_gemini_analyzer_or_fallback(self):
        """Verifica el análisis de viralidad con Gemini o el modo heurístico."""
        sample_segments = [
            {"start": 0.0, "end": 15.0, "text": "Hoy les voy a revelar el truco definitivo para multiplicar su productividad."},
            {"start": 15.0, "end": 35.0, "text": "La mayoría de las personas pierde 3 horas al día por este simple error."},
            {"start": 35.0, "end": 60.0, "text": "Si aplicas esta regla de 2 minutos, tu vida cambiará por completo."}
        ]
        clips = analyze_viral_moments_gemini(
            segments=sample_segments,
            video_duration=60.0,
            min_clip_duration=25,
            max_clip_duration=60,
            num_clips=1
        )
        self.assertTrue(len(clips) >= 1)
        clip = clips[0]
        self.assertIn("title", clip)
        self.assertIn("virality_score", clip)
        self.assertTrue(clip["virality_score"] >= 50)
        print(f"\n[OK] Analizador Viral verificado. Clip propuesto: '{clip['title']}' (Score: {clip['virality_score']})")

if __name__ == "__main__":
    unittest.main()
