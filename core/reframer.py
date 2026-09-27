import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

def detect_face_center_x(video_path: Path, start_time: float, duration: float, sample_fps: float = 2.0) -> Optional[float]:
    """
    Muestrea fotogramas del video en el intervalo [start_time, start_time + duration]
    y calcula la posición horizontal promedio del orador principal usando OpenCV.
    Compatible con OpenCV 4.x y OpenCV 5.x.
    Devuelve la coordenada X normalizada (entre 0.0 y 1.0) o None si no hay detección.
    """
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return None

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
        if width <= 0 or height <= 0:
            cap.release()
            return None

        # Verificar si CascadeClassifier existe en esta versión de OpenCV (OpenCV 4.x)
        face_cascade = None
        if hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
            try:
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                face_cascade = cv2.CascadeClassifier(cascade_path)
            except Exception:
                face_cascade = None

        start_frame = int(start_time * fps)
        total_frames_to_sample = int(duration * fps)
        step = max(1, int(fps / sample_fps))

        detected_centers_x = []
        prev_gray = None

        for f_idx in range(start_frame, start_frame + total_frames_to_sample, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if not ret:
                break

            # Reducir tamaño para detección rápida
            small = cv2.resize(frame, (640, int(640 * height / width)))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

            # 1. Intentar con clasificador facial si está disponible
            if face_cascade and not face_cascade.empty():
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                if len(faces) > 0:
                    largest_face = max(faces, key=lambda b: b[2] * b[3])
                    fx, fy, fw, fh = largest_face
                    center_norm = (fx + fw / 2.0) / 640.0
                    detected_centers_x.append(center_norm)
                    continue

            # 2. Alternativa universal (OpenCV 5.x): Centroide de movimiento del orador
            if prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                thresh = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)[1]
                M = cv2.moments(thresh)
                if M["m00"] > 500: # Movimiento perceptible del orador
                    motion_x = (M["m10"] / M["m00"]) / 640.0
                    # Limitar a rango central razonable
                    if 0.15 <= motion_x <= 0.85:
                        detected_centers_x.append(motion_x)

            prev_gray = gray

        cap.release()

        if detected_centers_x:
            # Mediana para descartar movimientos atípicos
            median_x = float(np.median(detected_centers_x))
            return median_x
            
    except Exception as e:
        print(f"ℹ️ [AutoClips] Nota en seguimiento visual ({e}). Usando recorte centrado.")

    return None

def build_reframe_filter(
    mode: str,
    source_path: Path,
    start_time: float,
    duration: float,
    target_w: int = 1080,
    target_h: int = 1920
) -> str:
    """
    Construye la cadena de filtros de video para FFmpeg según el modo seleccionado:
    - 'smart_face': Recorte 9:16 dinámico centrado en el orador detectado con OpenCV.
    - 'blurred_bg': Video horizontal original centrado con fondo desenfocado (estilo podcast).
    - 'center_crop': Recorte 9:16 centrado directo.
    """
    if mode == "blurred_bg":
        # Video centrado nítido con fondo desenfocado y oscurecido
        filter_str = (
            f"[0:v]split=2[fg_raw][bg_raw];"
            f"[bg_raw]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},"
            f"boxblur=luma_radius=25:luma_power=2,colorlevels=rimax=0.6:gimax=0.6:bimax=0.6[bg];"
            f"[fg_raw]scale={target_w}:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v_out]"
        )
        return filter_str

    elif mode == "smart_face":
        # Intentar detectar rostro
        face_x_norm = detect_face_center_x(source_path, start_time, duration)
        
        # Proporción 9:16 -> ancho requerido en la fuente = in_h * 9 / 16
        if face_x_norm is not None:
            # Calcular offset horizontal centrado en el rostro
            filter_str = (
                f"[0:v]crop=w=ih*9/16:h=ih:"
                f"x='max(0, min(iw-ow, {face_x_norm:.3f}*iw - ow/2))':y=0,"
                f"scale={target_w}:{target_h}[v_out]"
            )
            return filter_str
        else:
            # Fallback a recorte centrado
            return f"[0:v]crop=w=ih*9/16:h=ih:x=(iw-ow)/2:y=0,scale={target_w}:{target_h}[v_out]"

    else:
        # Modo 'center_crop' por defecto
        return f"[0:v]crop=w=ih*9/16:h=ih:x=(iw-ow)/2:y=0,scale={target_w}:{target_h}[v_out]"
