@echo off
chcp 65001 > nul
title AutoClips AI Studio — Generador de Shorts & TikTok (RTX 4060)

echo ======================================================================
echo           🎬 AUTOCLIPS AI STUDIO - LANZADOR OFICIAL
echo   De YouTube a Shorts, TikTok y Reels con NVIDIA RTX 4060 y Gemini
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/2] Verificando entorno de Python y aceleración CUDA...
python -c "import torch; print('GPU detectada:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

echo [2/2] Iniciando servidor web de AutoClips Studio...
echo (El navegador se abrirá automáticamente en el puerto disponible)
echo Para detener la aplicación presiona CTRL + C.
echo.
python app.py

pause
