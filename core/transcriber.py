import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from faster_whisper import WhisperModel
from .config import CUDA_AVAILABLE, GPU_NAME

# Caché global del modelo para evitar recargarlo innecesariamente en memoria
_LOADED_MODEL = None
_CURRENT_MODEL_SIZE = None

def get_whisper_model(model_size: str = "base") -> WhisperModel:
    """
    Inicializa o recupera de caché el modelo Faster-Whisper optimizado en GPU RTX 4060.
    """
    global _LOADED_MODEL, _CURRENT_MODEL_SIZE
    if _LOADED_MODEL is not None and _CURRENT_MODEL_SIZE == model_size:
        return _LOADED_MODEL

    device = "cuda" if CUDA_AVAILABLE else "cpu"
    compute_type = "float16" if CUDA_AVAILABLE else "int8"
    
    print(f"⚡ Inicializando Faster-Whisper [{model_size}] en {device.upper()} ({compute_type}) | GPU: {GPU_NAME}")
    
    _LOADED_MODEL = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        cpu_threads=4,
        download_root=None
    )
    _CURRENT_MODEL_SIZE = model_size
    return _LOADED_MODEL

def transcribe_audio_gpu(
    audio_path: Path,
    model_size: str = "base",
    language: Optional[str] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Transcribe un archivo de audio local usando GPU NVIDIA RTX 4060 con marcas de tiempo a nivel de palabra.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de audio en: {audio_path}")

    start_time = time.time()
    if progress_callback:
        progress_callback(5.0, f"Cargando modelo Whisper ({model_size}) en GPU RTX 4060...")

    model = get_whisper_model(model_size)

    if progress_callback:
        progress_callback(15.0, "Transcribiendo audio por hardware CUDA...")

    # Ejecutar transcripción con marcas de tiempo de palabra (word_timestamps)
    segments_generator, info = model.transcribe(
        str(audio_path),
        language=language,
        task="transcribe",
        beam_size=5,
        word_timestamps=True,
        vad_filter=True, # Filtrado VAD para saltar silencios
        vad_parameters=dict(min_silence_duration_ms=500)
    )

    detected_lang = info.language
    duration_total = info.duration or 1.0
    segments_data: List[Dict[str, Any]] = []
    full_text_chunks: List[str] = []

    for i, seg in enumerate(segments_generator):
        # Actualizar progreso en base al timestamp del audio procesado
        current_audio_time = seg.end
        percent = min(95.0, 15.0 + (current_audio_time / duration_total) * 75.0)
        
        words_list = []
        if seg.words:
            for w in seg.words:
                words_list.append({
                    "word": w.word.strip(),
                    "start": round(w.start, 2),
                    "end": round(w.end, 2),
                    "probability": round(w.probability, 2)
                })

        seg_dict = {
            "id": i,
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "duration": round(seg.end - seg.start, 2),
            "text": seg.text.strip(),
            "words": words_list
        }
        segments_data.append(seg_dict)
        full_text_chunks.append(seg.text.strip())

        if progress_callback and i % 5 == 0:
            progress_callback(percent, f"Transcribiendo min {int(current_audio_time//60)}:{int(current_audio_time%60):02d}...")

    elapsed = round(time.time() - start_time, 2)
    if progress_callback:
        progress_callback(95.0, f"Transcripción completada en {elapsed}s.")

    return {
        "language": detected_lang,
        "language_probability": round(info.language_probability, 2),
        "duration": duration_total,
        "transcription_time_seconds": elapsed,
        "segments": segments_data,
        "full_text": " ".join(full_text_chunks)
    }
