import argparse
import sys
from pathlib import Path
from core.pipeline import AutoClipsPipeline
from core.config import get_system_status

def main():
    parser = argparse.ArgumentParser(
        description="AutoClips AI Studio CLI — Convierte videos de YouTube en Shorts/TikTok virales con RTX 4060."
    )
    parser.add_argument("--url", "-u", required=True, help="URL del video de YouTube o ruta de archivo local.")
    parser.add_argument("--clips", "-n", type=int, default=3, help="Cantidad de clips a generar (default: 3).")
    parser.add_argument("--min", type=int, default=30, help="Duración mínima en segundos (default: 30).")
    parser.add_argument("--max", type=int, default=60, help="Duración máxima en segundos (default: 60).")
    parser.add_argument(
        "--framing", "-f",
        choices=["smart_face", "blurred_bg", "center_crop"],
        default="smart_face",
        help="Modo de encuadre vertical 9:16 (default: smart_face)."
    )
    parser.add_argument(
        "--subtitles", "-s",
        choices=["karaoke_yellow", "karaoke_green", "karaoke_cyan", "none"],
        default="karaoke_yellow",
        help="Estilo de subtítulos dinámicos (default: karaoke_yellow)."
    )
    parser.add_argument(
        "--whisper-model", "-m",
        choices=["tiny", "base", "small", "medium"],
        default="base",
        help="Tamaño de modelo Faster-Whisper para GPU (default: base)."
    )
    parser.add_argument("--force-whisper", action="store_true", help="Forzar transcripción con Whisper aunque existan subtítulos en YouTube.")

    args = parser.parse_args()

    status = get_system_status()
    print("=" * 70)
    print("🎬 AUTOCLIPS AI STUDIO — MODO CONSOLA")
    print(f"GPU: {status['gpu_name']} | VRAM: {status['vram_gb']} GB | CUDA: {status['cuda_available']}")
    print(f"Gemini: {status['active_gemini_model']} | API Key: {'Configurada' if status['has_gemini_key'] else 'No detectada'}")
    print("=" * 70)

    pipeline = AutoClipsPipeline()
    try:
        res = pipeline.run(
            url_or_path=args.url,
            num_clips=args.clips,
            min_duration=args.min,
            max_duration=args.max,
            framing_mode=args.framing,
            subtitle_style=args.subtitles,
            model_size=args.whisper_model,
            force_whisper=args.force_whisper
        )
        print("\n" + "=" * 70)
        print("🎉 ¡TODOS LOS CLIPS HAN SIDO GENERADOS EXITOSAMENTE!")
        print(f"Directorio de salida: {res['job_folder']}")
        print(f"Paquete ZIP: {res['zip_path']}")
        print("=" * 70)
        for c in res["clips"]:
            print(f"\n[Clip {c['clip_index']}] {c['title']} ({c['duration']}s)")
            print(f"Archivo: {c['file_name']} ({c['file_size_mb']} MB)")
            print(f"Score Viral: {c['virality_score']}/100")
            print(f"Gancho: {c['hook']}")
            print(f"Hashtags: {' '.join(c['hashtags'])}")

    except Exception as e:
        print(f"\n❌ Error durante el procesamiento: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
