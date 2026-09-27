import os
import sys
from pathlib import Path
import shutil
import torch
import imageio_ffmpeg
from dotenv import load_dotenv

# Asegurar encoding UTF-8 en consola de Windows para emojis
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Cargar variables de entorno desde la raíz de la fábrica y el proyecto local
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
PROJECT_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = PROJECT_DIR / "storage"
DOWNLOADS_DIR = STORAGE_DIR / "downloads"
OUTPUTS_DIR = STORAGE_DIR / "outputs"
MODELS_DIR = PROJECT_DIR / "models"

BIN_DIR = PROJECT_DIR / "bin"
BIN_DIR.mkdir(parents=True, exist_ok=True)

# Crear directorios si no existen
for directory in [STORAGE_DIR, DOWNLOADS_DIR, OUTPUTS_DIR, MODELS_DIR, BIN_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Detección y preparación de binarios FFmpeg y FFprobe
try:
    _raw_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    _dst_ffmpeg = BIN_DIR / "ffmpeg.exe"
    _dst_ffprobe = BIN_DIR / "ffprobe.exe"
    if not _dst_ffmpeg.exists() or _dst_ffmpeg.stat().st_size == 0:
        shutil.copy2(_raw_ffmpeg, _dst_ffmpeg)
    if not _dst_ffprobe.exists() or _dst_ffprobe.stat().st_size == 0:
        shutil.copy2(_raw_ffmpeg, _dst_ffprobe)
    FFMPEG_EXE = str(_dst_ffmpeg.resolve())
    FFMPEG_DIR = str(BIN_DIR.resolve())
except Exception:
    FFMPEG_EXE = shutil.which("ffmpeg") or "ffmpeg"
    FFMPEG_DIR = str(Path(FFMPEG_EXE).parent) if shutil.which("ffmpeg") else ""

# Agregar bin/ al inicio del PATH del sistema para yt-dlp y subprocesos
if FFMPEG_DIR and FFMPEG_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

# Intentar cargar .env local y luego el .env de la raíz
load_dotenv(PROJECT_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_GEMINI_MODEL = os.getenv("DEFAULT_GEMINI_MODEL") or os.getenv("DEFAULT_LLM_MODEL") or "gemini-3.5-flash-lite"

# Detección de aceleración por hardware NVIDIA GPU
CUDA_AVAILABLE = torch.cuda.is_available()
GPU_NAME = torch.cuda.get_device_name(0) if CUDA_AVAILABLE else "CPU"
VRAM_GB = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2) if CUDA_AVAILABLE else 0.0

def get_system_status():
    """Devuelve el estado del sistema, GPU y dependencias."""
    return {
        "cuda_available": CUDA_AVAILABLE,
        "gpu_name": GPU_NAME,
        "vram_gb": VRAM_GB,
        "ffmpeg_path": FFMPEG_EXE,
        "has_gemini_key": bool(GEMINI_API_KEY and len(GEMINI_API_KEY) > 10),
        "active_gemini_model": DEFAULT_GEMINI_MODEL,
        "storage_dir": str(STORAGE_DIR),
        "outputs_dir": str(OUTPUTS_DIR)
    }
