import os
import asyncio
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
import threading

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import (
    get_system_status,
    PROJECT_DIR,
    OUTPUTS_DIR,
    DOWNLOADS_DIR
)
from core.downloader import get_video_info, fetch_youtube_subtitles
from core.pipeline import AutoClipsPipeline

app = FastAPI(
    title="AutoClips AI Studio",
    description="Generador Autónomo de Clips Verticales Virales para Redes Sociales con RTX 4060 y Gemini",
    version="1.0.0"
)

# Permitir CORS para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos del frontend
WEB_DIR = PROJECT_DIR / "web"
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

# Diccionario de colas para Server-Sent Events (SSE) en memoria
JOB_QUEUES: Dict[str, asyncio.Queue] = {}
JOB_RESULTS: Dict[str, Any] = {}

class InspectRequest(BaseModel):
    url: str

class ProcessRequest(BaseModel):
    url: str
    num_clips: int = 3
    min_duration: int = 30
    max_duration: int = 60
    framing_mode: str = "smart_face"
    subtitle_style: str = "karaoke_yellow"
    whisper_model: str = "base"
    force_whisper: bool = False

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    """Sirve la página principal del estudio."""
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html no encontrado")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/status")
async def api_status():
    """Devuelve las especificaciones del sistema, GPU y modelos activos."""
    return get_system_status()

@app.post("/api/inspect")
async def api_inspect(req: InspectRequest):
    """Inspecciona un video de YouTube para extraer título, autor, duración y disponibilidad de subtítulos."""
    try:
        url = req.url.strip()
        if not url:
            raise HTTPException(status_code=400, detail="URL requerida")
        
        # Obtener info sin descargar el video
        info = get_video_info(url)
        
        # Chequear subtítulos nativos en YouTube
        has_subtitles = False
        if not info.get("is_local"):
            subs = fetch_youtube_subtitles(url)
            has_subtitles = bool(subs and len(subs) > 0)
        
        return {
            **info,
            "has_subtitles": has_subtitles
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

def run_pipeline_thread(job_id: str, loop: asyncio.AbstractEventLoop, req: ProcessRequest):
    """Ejecuta el pipeline en un hilo separado y emite eventos a la cola asíncrona."""
    queue = JOB_QUEUES.get(job_id)

    def on_progress(payload: Dict[str, Any]):
        if queue:
            asyncio.run_coroutine_threadsafe(queue.put(payload), loop)

    try:
        pipeline = AutoClipsPipeline(progress_callback=on_progress)
        result = pipeline.run(
            url_or_path=req.url,
            num_clips=req.num_clips,
            min_duration=req.min_duration,
            max_duration=req.max_duration,
            framing_mode=req.framing_mode,
            subtitle_style=req.subtitle_style,
            model_size=req.whisper_model,
            force_whisper=req.force_whisper
        )
        JOB_RESULTS[job_id] = result
    except Exception as exc:
        error_payload = {
            "stage": "error",
            "percent": 0.0,
            "message": f"Error durante la ejecución: {str(exc)}",
            "data": {"error": str(exc)}
        }
        if queue:
            asyncio.run_coroutine_threadsafe(queue.put(error_payload), loop)

@app.post("/api/process")
async def api_process(req: ProcessRequest):
    """Inicia la tarea de procesamiento en segundo plano y devuelve un ID de seguimiento."""
    job_id = str(uuid.uuid4())[:8]
    loop = asyncio.get_running_loop()
    
    # Crear cola SSE para este trabajo
    queue = asyncio.Queue()
    JOB_QUEUES[job_id] = queue

    # Lanzar el hilo de trabajo
    thread = threading.Thread(
        target=run_pipeline_thread,
        args=(job_id, loop, req),
        daemon=True
    )
    thread.start()

    return {
        "job_id": job_id,
        "status": "processing",
        "stream_url": f"/api/progress/{job_id}"
    }

@app.get("/api/progress/{job_id}")
async def api_progress(job_id: str):
    """Canal Server-Sent Events (SSE) para recibir el estado y porcentaje en vivo."""
    if job_id not in JOB_QUEUES:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")

    queue = JOB_QUEUES[job_id]

    async def event_generator():
        try:
            while True:
                item = await queue.get()
                yield f"data: {json.dumps(item)}\n\n"
                
                # Si terminó o falló, salir del generador
                stage = item.get("stage", "")
                if stage in ["complete", "error"]:
                    break
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/stream")
async def api_stream_video(path: str):
    """Transmite un archivo de video MP4 con soporte de encabezados Range para reproducción fluida."""
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo de video no encontrado")
    return FileResponse(path=file_path, media_type="video/mp4")

@app.get("/api/download")
async def api_download_file(file: str):
    """Permite descargar directamente un clip MP4 o el archivo ZIP generado."""
    file_path = Path(file)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream"
    )

def find_available_port(start_port: int = 8090, max_tries: int = 25) -> int:
    """Busca el primer puerto libre disponible en localhost para evitar colisiones."""
    import socket
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return start_port

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import time
    
    port = int(os.getenv("PORT", find_available_port(8090)))
    url = f"http://127.0.0.1:{port}"
    print(f"\n🚀 Servidor web de AutoClips activo en: {url}")
    
    def open_browser():
        time.sleep(1.2)
        try:
            webbrowser.open(url)
        except Exception:
            pass
            
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=False)
