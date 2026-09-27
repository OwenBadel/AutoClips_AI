# 🎬 AutoClips AI Studio

> **Generador Autónomo de Clips Verticales Virales (9:16) para TikTok, YouTube Shorts, Instagram Reels y Kwai.**  
> Acelerado por GPU **NVIDIA GeForce RTX 4060 (8 GB VRAM)**, **Faster-Whisper CUDA**, **Google Gemini 3.6 Flash** y codificación por hardware **FFmpeg NVENC**.

---

**Autor y Titular:** Ingeniero Owen Badel Hooker  
**GitHub:** [OwenBadel](https://github.com/OwenBadel)  
**Repositorio Oficial:** [AutoClips_AI](https://github.com/OwenBadel/AutoClips_AI)  

---

## 🌟 Características Principales

1. **Aceleración Extrema por GPU NVIDIA RTX 4060:**
   - **Faster-Whisper en CUDA (`float16`):** Transcribe audios de 30 a 60 minutos en menos de 45 segundos con marcas de tiempo a nivel de palabra.
   - **Ruta ultrarrápida de subtítulos:** Si el video de YouTube ya contiene subtítulos nativos, los descarga y procesa en 1 segundo.
   - **Codificación por Hardware `h264_nvenc`:** Renderizado a alta velocidad sin sobrecargar la CPU.

2. **Detección Viral con Google Gemini 3.6 Flash:**
   - Su ventana de contexto de más de 1 millón de tokens analiza el video completo sin truncar nada.
   - Detecta los mejores ganchos iniciales (*hooks*), momentos de mayor tensión o valor formativo y remates.
   - Genera automáticamente títulos virales con emojis, justificación de viralidad (1-100), resumen y hashtags listos para copiar y pegar.

3. **Reencuadre 9:16 Inteligente:**
   - **Smart Face Tracking:** Detección de oradores mediante visión por computador (OpenCV) y suavizado de encuadre.
   - **Fondo Desenfocado (Podcast/Entrevista):** Video original nítido centrado con fondo ambiental difuminado y oscurecido.
   - **Recorte Centrado Directo:** Máxima resolución para tomas ya encuadradas.

4. **Subtítulos Dinámicos Estilo TikTok (Alex Hormozi / Karaoke):**
   - Subtítulos ASS vectoriales quemados directamente en el video.
   - Resaltado dinámico palabra por palabra en colores vibrantes (Amarillo Neón, Verde Lima, Cyan Eléctrico) con contorno negro pronunciado.

5. **Doble Interfaz de Usuario:**
   - **Estudio Web Moderno:** Interfaz gráfica oscura con estética *glassmorphism*, barra de progreso en vivo vía SSE, reproductor de clips vertical interactivo y descarga en un clic (individual o paquete .ZIP con archivo de hashtags).
   - **CLI de Alta Eficiencia:** Ejecutable directamente desde consola para automatizaciones o procesamiento por lotes.

---

## 🚀 Inicio Rápido

### Modo 1: Interfaz Web Gráfica (Recomendado)
Haz doble clic sobre el archivo:
```bash
INICIAR_APP.bat
```
O desde la terminal en esta carpeta:
```bash
python app.py
```
Abre tu navegador en [http://127.0.0.1:8080](http://127.0.0.1:8080).

### Modo 2: Consola / Terminal (CLI)
```bash
# Generar 3 clips virales de entre 30 y 60 segundos
python cli.py --url "https://www.youtube.com/watch?v=TU_VIDEO" --clips 3 --framing smart_face --subtitles karaoke_yellow

# Generar clips de fondo desenfocado para un podcast
python cli.py --url "https://www.youtube.com/watch?v=TU_VIDEO" --clips 5 --framing blurred_bg --subtitles karaoke_green
```

---

## 🏛️ Estructura del Proyecto

```
PROJ_009_AutoClips_AI/
├── AGENTS.md                  # Directiva agéntica del proyecto
├── README.md                  # Documentación integral en español
├── INICIAR_APP.bat            # Lanzador de un clic para Windows
├── requirements.txt           # Dependencias del proyecto
├── app.py                     # Servidor FastAPI y API de Streaming SSE
├── cli.py                     # Interfaz de línea de comandos
├── core/
│   ├── __init__.py
│   ├── config.py              # Detección de GPU, rutas y variables de entorno
│   ├── downloader.py          # Extracción con yt-dlp y youtube-transcript-api
│   ├── transcriber.py         # Faster-Whisper optimizado en GPU RTX 4060
│   ├── analyzer.py            # Estratega de momentos virales con Gemini 3.6 Flash
│   ├── reframer.py            # Visión artificial y filtros de encuadre 9:16
│   ├── subtitles.py           # Generador de subtítulos ASS dinámicos estilo TikTok
│   ├── renderer.py            # Renderizado por hardware FFmpeg + NVENC
│   └── pipeline.py            # Orquestador del flujo integral de transformación
├── web/
│   ├── index.html             # Dashboard web moderno con glassmorphism
│   ├── style.css              # Hoja de estilos con variables HSL y animaciones
│   └── app.js                 # Controlador frontend y receptor de eventos en tiempo real
└── storage/
    ├── downloads/             # Archivos fuente descargados temporalmente
    └── outputs/               # Clips verticales renderizados y paquetes ZIP
```

---

## 📋 Requisitos de Hardware y Software
- **Sistema Operativo:** Windows 10/11 (64-bit).
- **GPU:** NVIDIA GeForce RTX 4060 (8 GB VRAM) con soporte CUDA 12.x y controladores actualizados.
- **Python:** 3.10 o superior (verificado con Python 3.12).
- **FFmpeg:** Incluido automáticamente mediante `imageio-ffmpeg` con soporte oficial de `h264_nvenc`.
- **API Key:** Google Gemini configurada en `.env` en la raíz del entorno.
