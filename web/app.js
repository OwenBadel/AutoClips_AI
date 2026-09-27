/**
 * AutoClips AI Studio — Client Controller
 * Conecta con el backend FastAPI mediante REST y Server-Sent Events (SSE).
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elementos del DOM
  const youtubeUrlInput = document.getElementById('youtubeUrlInput');
  const clearInputBtn = document.getElementById('clearInputBtn');
  const inspectVideoBtn = document.getElementById('inspectVideoBtn');
  const startGenerationBtn = document.getElementById('startGenerationBtn');
  
  const videoPreviewBox = document.getElementById('videoPreviewBox');
  const previewThumbnail = document.getElementById('previewThumbnail');
  const previewTitle = document.getElementById('previewTitle');
  const previewChannel = document.getElementById('previewChannel');
  const previewDuration = document.getElementById('previewDuration');
  const previewSubsBadge = document.getElementById('previewSubsBadge');

  const numClipsSelect = document.getElementById('numClipsSelect');
  const durationSelect = document.getElementById('durationSelect');
  const framingSelect = document.getElementById('framingSelect');
  const subtitlesSelect = document.getElementById('subtitlesSelect');

  const progressSection = document.getElementById('progressSection');
  const progressBarFill = document.getElementById('progressBarFill');
  const progressPercent = document.getElementById('progressPercent');
  const currentStageMessage = document.getElementById('currentStageMessage');
  const consoleLogFeed = document.getElementById('consoleLogFeed');

  const resultsSection = document.getElementById('resultsSection');
  const resultsSubtitle = document.getElementById('resultsSubtitle');
  const clipsGrid = document.getElementById('clipsGrid');
  const downloadZipBtn = document.getElementById('downloadZipBtn');

  // Modal
  const videoModal = document.getElementById('videoModal');
  const modalVideoPlayer = document.getElementById('modalVideoPlayer');
  const modalClipTitle = document.getElementById('modalClipTitle');
  const modalViralityBadge = document.getElementById('modalViralityBadge');
  const modalDurationBadge = document.getElementById('modalDurationBadge');
  const modalCopyText = document.getElementById('modalCopyText');
  const modalCopyBtn = document.getElementById('modalCopyBtn');
  const closeModalBtn = document.getElementById('closeModalBtn');

  // Variables de estado
  let activeEventSource = null;
  let currentVideoInfo = null;

  // 1. Cargar estado del sistema (GPU y Gemini)
  async function loadSystemStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      if (data.cuda_available) {
        document.getElementById('gpuNameText').textContent = `${data.gpu_name} (${data.vram_gb} GB VRAM)`;
      } else {
        document.getElementById('gpuNameText').textContent = 'CPU (Sin CUDA)';
      }
      if (data.active_gemini_model) {
        document.getElementById('aiModelText').textContent = data.active_gemini_model;
      }
    } catch (e) {
      console.warn('No se pudo obtener el estado del sistema:', e);
    }
  }
  loadSystemStatus();

  // 2. Control de Entrada URL
  youtubeUrlInput.addEventListener('input', () => {
    clearInputBtn.style.display = youtubeUrlInput.value ? 'block' : 'none';
  });

  clearInputBtn.addEventListener('click', () => {
    youtubeUrlInput.value = '';
    clearInputBtn.style.display = 'none';
    videoPreviewBox.classList.add('hidden');
    currentVideoInfo = null;
  });

  youtubeUrlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      inspectVideoBtn.click();
    }
  });

  // 3. Inspeccionar Video
  inspectVideoBtn.addEventListener('click', async () => {
    const url = youtubeUrlInput.value.trim();
    if (!url) {
      alert('Por favor, ingresa un enlace válido de YouTube.');
      return;
    }

    inspectVideoBtn.disabled = true;
    inspectVideoBtn.innerHTML = '<span>Inspeccionando...</span>';

    try {
      const res = await fetch('/api/inspect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      const data = await res.json();
      
      if (!res.ok || data.error) {
        throw new Error(data.error || 'No se pudo inspeccionar el video');
      }

      currentVideoInfo = data;
      previewTitle.textContent = data.title;
      previewChannel.textContent = data.uploader || 'YouTube';
      previewThumbnail.src = data.thumbnail || '';
      
      // Formatear duración
      const dur = data.duration || 0;
      const m = Math.floor(dur / 60);
      const s = Math.floor(dur % 60);
      previewDuration.textContent = `${m}:${s.toString().padStart(2, '0')}`;

      if (data.has_subtitles) {
        previewSubsBadge.textContent = '✅ Subtítulos de YouTube disponibles (Proceso Ultra Rápido)';
        previewSubsBadge.style.color = 'var(--accent-emerald)';
      } else {
        previewSubsBadge.textContent = '⚡ Faster-Whisper GPU listo para transcripción automática';
        previewSubsBadge.style.color = 'var(--accent-cyan)';
      }

      videoPreviewBox.classList.remove('hidden');

    } catch (err) {
      alert(`Error al inspeccionar el video: ${err.message}`);
    } finally {
      inspectVideoBtn.disabled = false;
      inspectVideoBtn.innerHTML = '<span>Inspeccionar</span>';
    }
  });

  // 4. Iniciar Generación de Clips
  startGenerationBtn.addEventListener('click', async () => {
    const url = youtubeUrlInput.value.trim();
    if (!url) {
      alert('Ingresa primero el enlace de YouTube.');
      return;
    }

    // Extraer rango de duración
    const [minDur, maxDur] = durationSelect.value.split('-').map(Number);

    const payload = {
      url: url,
      num_clips: parseInt(numClipsSelect.value, 10),
      min_duration: minDur,
      max_duration: maxDur,
      framing_mode: framingSelect.value,
      subtitle_style: subtitlesSelect.value
    };

    // UI Feedback
    startGenerationBtn.disabled = true;
    progressSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    clipsGrid.innerHTML = '';
    consoleLogFeed.innerHTML = '';
    progressBarFill.style.width = '0%';
    progressPercent.textContent = '0%';
    resetStepper();

    appendLog('info', `[ORDEN] Iniciando proceso para URL: ${url}`);
    appendLog('info', `[CONFIG] Clips solicitados: ${payload.num_clips} | Duración: ${minDur}-${maxDur}s | Encuadre: ${payload.framing_mode}`);

    try {
      const res = await fetch('/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!res.ok || data.error) {
        throw new Error(data.error || 'Error al iniciar la tarea.');
      }

      const jobId = data.job_id;
      appendLog('info', `[TAREA] Identificador asignado: ${jobId}`);
      subscribeToJobEvents(jobId);

    } catch (err) {
      alert(`No se pudo iniciar el proceso: ${err.message}`);
      startGenerationBtn.disabled = false;
    }
  });

  // 5. Suscripción a Eventos SSE en Tiempo Real
  function subscribeToJobEvents(jobId) {
    if (activeEventSource) {
      activeEventSource.close();
    }

    activeEventSource = new EventSource(`/api/progress/${jobId}`);

    activeEventSource.onmessage = (event) => {
      try {
        const item = JSON.parse(event.data);
        updateProgressUI(item);
      } catch (e) {
        console.error('Error parseando evento SSE:', e);
      }
    };

    activeEventSource.onerror = (err) => {
      console.warn('Conexión SSE cerrada o con error:', err);
      activeEventSource.close();
    };
  }

  // 6. Actualización Visual de la Barra y Pasos
  function updateProgressUI(item) {
    const { stage, percent, message, data } = item;

    progressBarFill.style.width = `${percent}%`;
    progressPercent.textContent = `${Math.round(percent)}%`;
    currentStageMessage.textContent = message;

    appendLog(getLogClass(stage), `[${stage.toUpperCase()}] ${message}`);

    // Actualizar nodos del stepper
    updateStepper(stage);

    // Si terminó con éxito
    if (stage === 'complete') {
      if (activeEventSource) {
        activeEventSource.close();
      }
      startGenerationBtn.disabled = false;
      appendLog('success', '✨ [COMPLETADO] ¡Todos los clips fueron renderizados exitosamente!');
      
      if (data && data.clips) {
        renderResultsGallery(data);
      }
    } else if (stage === 'error') {
      if (activeEventSource) {
        activeEventSource.close();
      }
      startGenerationBtn.disabled = false;
      appendLog('error', `❌ [ERROR CRÍTICO] ${message}`);
      alert(`Ocurrió un error en el pipeline: ${message}`);
    }
  }

  function getLogClass(stage) {
    if (stage.includes('error')) return 'error';
    if (stage.includes('complete')) return 'success';
    if (stage.includes('viral') || stage.includes('analyz')) return 'warn';
    return 'info';
  }

  function appendLog(type, text) {
    const div = document.createElement('div');
    div.className = `log-line ${type}`;
    div.textContent = text;
    consoleLogFeed.appendChild(div);
    consoleLogFeed.scrollTop = consoleLogFeed.scrollHeight;
  }

  function resetStepper() {
    ['info', 'transcribe', 'analyze', 'render', 'complete'].forEach(id => {
      const node = document.getElementById(`step-${id}`);
      if (node) {
        node.classList.remove('active', 'done');
      }
    });
  }

  function updateStepper(stage) {
    const nodeInfo = document.getElementById('step-info');
    const nodeTrans = document.getElementById('step-transcribe');
    const nodeAnaly = document.getElementById('step-analyze');
    const nodeRend = document.getElementById('step-render');
    const nodeComp = document.getElementById('step-complete');

    if (stage === 'info') {
      nodeInfo.classList.add('active');
    } else if (stage.includes('transcribe') || stage.includes('audio')) {
      nodeInfo.classList.add('done');
      nodeTrans.classList.add('active');
    } else if (stage.includes('analyz') || stage.includes('viral')) {
      nodeTrans.classList.add('done');
      nodeAnaly.classList.add('active');
    } else if (stage.includes('render') || stage.includes('video') || stage.includes('pack')) {
      nodeAnaly.classList.add('done');
      nodeRend.classList.add('active');
    } else if (stage === 'complete') {
      nodeRend.classList.add('done');
      nodeComp.classList.add('done');
    }
  }

  // 7. Renderizar Galería de Resultados
  function renderResultsGallery(finalData) {
    resultsSection.classList.remove('hidden');
    resultsSubtitle.textContent = `${finalData.total_clips_generated} clips optimizados para retención • Procesado en ${finalData.total_process_time_seconds}s en GPU ${finalData.hardware.gpu}`;
    
    // Botón de descarga ZIP
    if (finalData.zip_filename) {
      downloadZipBtn.href = `/api/download?file=${encodeURIComponent(finalData.zip_path)}`;
      downloadZipBtn.setAttribute('download', finalData.zip_filename);
    }

    clipsGrid.innerHTML = '';

    finalData.clips.forEach(clip => {
      const card = document.createElement('div');
      card.className = 'clip-card';

      const durM = Math.floor(clip.duration / 60);
      const durS = Math.floor(clip.duration % 60);
      const durationStr = `${durM}:${durS.toString().padStart(2, '0')}`;
      const videoStreamUrl = `/api/stream?path=${encodeURIComponent(clip.file_path)}`;

      card.innerHTML = `
        <div class="clip-video-preview">
          <video src="${videoStreamUrl}" preload="metadata" muted playsinline></video>
          <span class="score-badge">🔥 ${clip.virality_score}/100</span>
          <span class="duration-badge">${durationStr}</span>
        </div>
        <div class="clip-body">
          <h3 class="clip-title">${clip.title}</h3>
          <div class="clip-hook-quote">"${clip.hook || 'Gancho de alto impacto'}"</div>
          <div class="clip-hashtags">
            ${(clip.hashtags || []).map(t => `<span class="tag-pill">${t}</span>`).join('')}
          </div>
          <div class="clip-footer-actions">
            <button class="card-btn primary-card-btn preview-clip-btn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              <span>Ver Clip</span>
            </button>
            <a href="/api/download?file=${encodeURIComponent(clip.file_path)}" download="${clip.file_name}" class="card-btn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
              <span>MP4</span>
            </a>
          </div>
        </div>
      `;

      // Evento de previsualización en modal
      const previewBtn = card.querySelector('.preview-clip-btn');
      previewBtn.addEventListener('click', () => {
        openModalWithClip(clip, videoStreamUrl, durationStr);
      });

      clipsGrid.appendChild(card);
    });

    // Desplazarse suavemente hasta los resultados
    resultsSection.scrollIntoView({ behavior: 'smooth' });
  }

  // 8. Modal de Video
  function openModalWithClip(clip, streamUrl, durationStr) {
    modalClipTitle.textContent = clip.title;
    modalViralityBadge.textContent = `🔥 ${clip.virality_score}/100 Viral`;
    modalDurationBadge.textContent = durationStr;
    modalVideoPlayer.src = streamUrl;
    modalVideoPlayer.play();

    const copyBody = `${clip.title}\n\n${clip.summary}\n\n${(clip.hashtags || []).join(' ')}`;
    modalCopyText.value = copyBody;

    videoModal.classList.remove('hidden');
  }

  closeModalBtn.addEventListener('click', () => {
    modalVideoPlayer.pause();
    modalVideoPlayer.src = '';
    videoModal.classList.add('hidden');
  });

  videoModal.addEventListener('click', (e) => {
    if (e.target === videoModal) {
      closeModalBtn.click();
    }
  });

  modalCopyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(modalCopyText.value).then(() => {
      const original = modalCopyBtn.textContent;
      modalCopyBtn.textContent = '✅ ¡Copiado al portapapeles!';
      setTimeout(() => {
        modalCopyBtn.textContent = original;
      }, 2000);
    });
  });

});
