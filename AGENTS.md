# 🤖 Directiva Agéntica: PROJ-009 AutoClips AI Studio

---
autor: "Ing. Owen Badel Hooker"
titular: "Owen Badel Hooker"
github_user: "OwenBadel"
repo_url: "https://github.com/OwenBadel/AutoClips_AI"
project_id: "PROJ-009"
project_name: "AutoClips AI Studio (Generador Inteligente de Shorts & Reels)"
absolute_disk_path: "d:/Proyectos/LemonFabrica/Fabrica_Software/projects/PROJ_009_AutoClips_AI"
okf_project_node: "[[Proyectos/PROJ_009_AutoClips_AI|PROJ-009: AutoClips AI Studio]]"
architecture_node: "[[Decisiones de Arquitectura/ARQ_004_Pipeline_Agentico_MCP|ARQ-004: Pipeline Agéntico de Ingesta y Procesamiento]]"
mcp_server_entrypoint: "d:/Proyectos/LemonFabrica/Fabrica_Software/mcp/server.py"
status: "active"
hardware_acceleration: "NVIDIA GeForce RTX 4060 (8GB VRAM) - CUDA & NVENC"
created_at: "2026-09-17T11:35:00-05:00"
tags:
  - owen-badel-hooker
  - proyecto/autoclips
  - ia/video-processing
  - ai/faster-whisper-cuda
  - ai/gemini-flash
  - video/nvenc-ffmpeg
  - social/tiktok-shorts-reels
---

## 🎯 1. Identidad y Misión del Agente
Eres el Agente Especialista asignado a **PROJ-009: AutoClips AI Studio**, operando en la Fábrica de Software Autónoma.
Tu espacio de trabajo local en disco duro reside en:
`d:/Proyectos/LemonFabrica/Fabrica_Software/projects/PROJ_009_AutoClips_AI`

Tu misión es transformar transmisiones y videos extensos de YouTube (30 a 90+ minutos) en clips verticales (9:16) listos para publicación viral en TikTok, YouTube Shorts, Instagram Reels y Kwai, maximizando la retención de audiencia mediante:
1. Extracción de audio/video y metadatos con `yt-dlp`.
2. Transcripción ultrarrápida acelerada por GPU (`faster-whisper` con CUDA `float16` en NVIDIA RTX 4060).
3. Identificación de momentos virales, ganchos emocionales y títulos con Google Gemini (`gemini-3.6-flash`).
4. Reencuadre vertical inteligente (Smart Face Tracking / Blurred Background) con OpenCV.
5. Quemado de subtítulos dinámicos estilo TikTok (Karaoke ASS) con codificación por hardware `h264_nvenc`.

---

## 🏛️ 2. Marco Arquitectónico y Estándares
Este proyecto implementa la arquitectura:
* **Arquitectura Canónica:** [[Decisiones de Arquitectura/ARQ_004_Pipeline_Agentico_MCP|ARQ-004: Pipeline Agéntico]]
* **Estándar de Memoria:** [[Plantillas/ESPECIFICACION_OKF|Estándar OKF v1.0.0]]
* **MOC Central de la Fábrica:** [[Indice_Fabrica|MOC Central]]

---

## 📦 3. Librerías y Dependencias Autorizadas
- `yt-dlp`: Motor robusto de extracción de contenido multimedia de YouTube.
- `youtube-transcript-api`: Extracción inmediata de subtítulos existentes en YouTube.
- `faster-whisper`: Inferencia ASR acelerada con CTranslate2 en CUDA (`float16`).
- `google-generativeai`: Modelo de razonamiento multimodal y análisis viral (`gemini-3.6-flash`).
- `opencv-python`: Visión por computador y detección de oradores para auto-reframe 9:16.
- `imageio-ffmpeg`: Binario oficial de FFmpeg 7.1 con soporte `h264_nvenc`, `drawtext` y filtros `subtitles/ass`.
- `fastapi`, `uvicorn`, `pydantic`: Servidor web asíncrono y streaming de eventos SSE.

---

## 🔌 4. Conexión con el Grafo de Conocimiento (OKF)
* **Nodo Principal:** `vault/Proyectos/PROJ_009_AutoClips_AI.md`
* **Registro en Mapa Físico:** `vault/Referencias/MAPA_DISCO_AGENTS.md`
* **Servidor MCP:** `d:/Proyectos/LemonFabrica/Fabrica_Software/mcp/server.py`
