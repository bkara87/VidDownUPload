/**
 * VidDownUPload v2.0 — Main Application Controller
 * Handles: tabs, terminal log, video grids, studio canvas, upload flow
 */

// ────────────────────────────────────────────────────────────
// STATE
// ────────────────────────────────────────────────────────────

const State = {
  currentTab: 'download',
  downloadedVideos: [],
  processedVideos: [],
  currentStudioPath: null,
  uploadTargetPath: null,
  profileScanItems: [],
  logoRelX: 0.78,
  logoRelY: 0.88,
  blurRelX: 0.65,
  blurRelY: 0.88,
  quality: 'Yüksek Kalite (Varsayılan)',
  eqAnimId: null,
  eqRunning: false,
  logCollapsed: false,
  previewLogoBitmap: null,
  logoDragging: false,
  blurDragging: false,
  updateDownloadUrl: ''
};

// ────────────────────────────────────────────────────────────
// INIT
// ────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initEqualizer();
  initPreviewCanvas();
  setupPreviewDrag();

  // Wait for pywebview API to be ready
  const waitForApi = () => {
    if (window.pywebview && window.pywebview.api) {
      onApiReady();
    } else {
      setTimeout(waitForApi, 100);
    }
  };
  waitForApi();
});

function onApiReady() {
  appendLog('VidDownUPload v2.0 başlatıldı. Hazır.', 'success');

  // Load app version
  window.pywebview.api.get_app_info().then(info => {
    if (info && info.version) {
      document.getElementById('appVersion').textContent = 'v' + info.version;
      document.getElementById('settingsVersion').textContent = 'v' + info.version;
    }
  });

  // Load video grids
  refreshDownloads();
  refreshStudioGrid();
  refreshQueueGrid();
  loadApiKeys();
}

// ────────────────────────────────────────────────────────────
// TABS
// ────────────────────────────────────────────────────────────

function switchTab(name) {
  // Deactivate all
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

  // Activate target
  document.getElementById('tab-' + name).classList.add('active');
  document.getElementById('panel-' + name).classList.add('active');
  State.currentTab = name;

  if (name === 'studio') refreshStudioGrid();
  if (name === 'queue')  refreshQueueGrid();
}

// ────────────────────────────────────────────────────────────
// TERMINAL LOG
// ────────────────────────────────────────────────────────────

window.appendLog = function(message, type = 'info') {
  const out = document.getElementById('terminalOutput');
  if (!out) return;

  const line = document.createElement('div');
  line.className = 'log-line log-' + type;
  const ts = new Date().toLocaleTimeString('tr-TR');
  line.textContent = '[' + ts + '] ' + message;
  out.appendChild(line);
  out.scrollTop = out.scrollHeight;

  // Also kick the equalizer
  eqKick();
};

function clearLog() {
  const out = document.getElementById('terminalOutput');
  if (out) out.innerHTML = '';
}

function toggleLog() {
  const out = document.getElementById('terminalOutput');
  const btn = document.getElementById('btnToggleLog');
  State.logCollapsed = !State.logCollapsed;
  if (State.logCollapsed) {
    out.classList.add('collapsed');
    btn.textContent = '▲ Göster';
  } else {
    out.classList.remove('collapsed');
    btn.textContent = '▼ Gizle';
  }
}

// ────────────────────────────────────────────────────────────
// EQUALIZER ANIMATION
// ────────────────────────────────────────────────────────────

function initEqualizer() {
  const container = document.getElementById('equalizer');
  if (!container) return;
  for (let i = 0; i < 32; i++) {
    const bar = document.createElement('div');
    bar.className = 'eq-bar';
    bar.style.height = '2px';
    bar.style.flex = '1';
    container.appendChild(bar);
  }
}

function eqKick() {
  if (State.eqRunning) return;
  State.eqRunning = true;
  let ticks = 0;
  const bars = document.querySelectorAll('.eq-bar');
  const animate = () => {
    bars.forEach(bar => {
      const h = Math.random() * 18 + 2;
      bar.style.height = h + 'px';
    });
    ticks++;
    if (ticks < 25) {
      State.eqAnimId = requestAnimationFrame(animate);
    } else {
      // Wind down
      bars.forEach(bar => { bar.style.height = '2px'; });
      State.eqRunning = false;
    }
  };
  State.eqAnimId = requestAnimationFrame(animate);
}

// ────────────────────────────────────────────────────────────
// UPDATE LOGIC
// ────────────────────────────────────────────────────────────

function checkUpdates() {
  const btn = document.getElementById('btnUpdate');
  btn.disabled = true;
  btn.textContent = '⏳ Kontrol...';
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.check_for_updates();
  }
  setTimeout(() => {
    btn.disabled = false;
    btn.textContent = '🔄 Güncelle';
  }, 4000);
}

window.showUpdatePrompt = function(newVer, dlUrl) {
  State.updateDownloadUrl = dlUrl;
  document.getElementById('newVerTag').textContent = 'v' + newVer;
  openModal('updateModal');
};

document.getElementById('btnApplyUpdate').addEventListener('click', () => {
  if (State.updateDownloadUrl && window.pywebview && window.pywebview.api) {
    window.pywebview.api.apply_update(State.updateDownloadUrl);
    closeModal('updateModal');
  }
});

// ────────────────────────────────────────────────────────────
// MODALS
// ────────────────────────────────────────────────────────────

function openModal(id) {
  document.getElementById(id).classList.add('open');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

// ────────────────────────────────────────────────────────────
// VIDEO GRID BUILDER
// ────────────────────────────────────────────────────────────

/**
 * Renders a list of video objects into a grid container.
 * @param {string} gridId - DOM id of the video-grid div
 * @param {string} emptyId - DOM id of the empty state element (or null)
 * @param {Array}  videos  - Array of video info objects from api
 * @param {Object} opts    - Options: { showStudio, showUpload, showDelete }
 */
function renderVideoGrid(gridId, emptyId, videos, opts = {}) {
  const grid = document.getElementById(gridId);
  if (!grid) return;

  // Clear old cards (keep empty-state if present)
  const existing = grid.querySelectorAll('.video-card');
  existing.forEach(el => el.remove());

  if (emptyId) {
    document.getElementById(emptyId).style.display = videos.length ? 'none' : '';
  }

  videos.forEach(v => {
    const card = buildVideoCard(v, opts);
    grid.appendChild(card);
  });
}

function buildVideoCard(v, opts) {
  const card = document.createElement('div');
  card.className = 'video-card fade-in';
  card.dataset.path = v.path;

  // Thumbnail
  const thumbDiv = document.createElement('div');
  thumbDiv.className = 'video-thumb';

  const placeholder = document.createElement('div');
  placeholder.className = 'video-thumb-placeholder';
  placeholder.textContent = '🎬';
  thumbDiv.appendChild(placeholder);

  const badge = document.createElement('div');
  badge.className = 'video-card-badge';
  badge.textContent = '✦ İşlendi';
  badge.style.display = v.path.includes('processed') ? '' : 'none';
  thumbDiv.appendChild(badge);

  const ratio = document.createElement('div');
  ratio.className = 'video-ratio-label';
  ratio.textContent = '9:16';
  thumbDiv.appendChild(ratio);

  card.appendChild(thumbDiv);

  // Instant thumbnail load if pre-cached
  if (v.thumbnail && v.thumbnail.startsWith('data:')) {
    const img = document.createElement('img');
    img.src = v.thumbnail;
    img.style.width = '100%';
    img.style.height = '100%';
    img.style.objectFit = 'cover';
    img.style.position = 'absolute';
    img.style.top = '0';
    img.style.left = '0';
    thumbDiv.style.position = 'relative';
    thumbDiv.insertBefore(img, placeholder);
    placeholder.style.display = 'none';
  } else {
    loadThumbnail(v.path, thumbDiv, placeholder);
  }

  // Info
  const info = document.createElement('div');
  info.className = 'video-card-info';

  const title = document.createElement('div');
  title.className = 'video-card-title';
  title.textContent = v.title || v.filename;
  info.appendChild(title);

  const meta = document.createElement('div');
  meta.className = 'video-card-meta';
  meta.textContent = v.size_mb + ' MB  •  ' + (v.modified || '');
  info.appendChild(meta);

  card.appendChild(info);

  // Action buttons
  const actions = document.createElement('div');
  actions.className = 'video-card-actions';

  if (opts.showStudio) {
    const btnS = document.createElement('button');
    btnS.className = 'btn btn-secondary';
    btnS.textContent = '🎨 Stüdyo';
    btnS.title = 'Stüdyoya Aç';
    btnS.onclick = e => { e.stopPropagation(); openInStudio(v.path, v.filename); };
    actions.appendChild(btnS);
  }

  if (opts.showUpload) {
    const btnU = document.createElement('button');
    btnU.className = 'btn btn-primary';
    btnU.textContent = '🚀 Yükle';
    btnU.title = 'Platforma Yükle';
    btnU.onclick = e => { e.stopPropagation(); openUploadModal(v.path, v.filename, v.caption, v.hashtags_str); };
    actions.appendChild(btnU);
  }

  const btnLoc = document.createElement('button');
  btnLoc.className = 'btn btn-secondary btn-icon';
  btnLoc.textContent = '📂';
  btnLoc.title = 'Dosya Konumunda Göster';
  btnLoc.onclick = e => { e.stopPropagation(); openFileLocation(v.path); };
  actions.appendChild(btnLoc);

  const btnDel = document.createElement('button');
  btnDel.className = 'btn btn-danger btn-icon';
  btnDel.textContent = '🗑';
  btnDel.title = 'Sil';
  btnDel.onclick = e => { e.stopPropagation(); deleteVideoConfirm(v.path, card); };
  actions.appendChild(btnDel);

  card.appendChild(actions);

  // Click to open in studio
  if (opts.showStudio) {
    card.onclick = () => openInStudio(v.path, v.filename);
  }

  return card;
}

window.openFolder = function(type = 'downloads') {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.open_folder(type);
  }
};

window.openFileLocation = function(videoPath) {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.open_file_location(videoPath);
  }
};

function loadThumbnail(videoPath, thumbDiv, placeholder) {
  if (!window.pywebview || !window.pywebview.api) return;
  window.pywebview.api.get_video_thumbnail(videoPath).then(dataUrl => {
    if (dataUrl && dataUrl.startsWith('data:')) {
      const img = document.createElement('img');
      img.src = dataUrl;
      img.style.width = '100%';
      img.style.height = '100%';
      img.style.objectFit = 'cover';
      img.style.position = 'absolute';
      img.style.top = '0';
      img.style.left = '0';
      thumbDiv.style.position = 'relative';
      thumbDiv.insertBefore(img, placeholder);
      placeholder.style.display = 'none';
    }
  }).catch(() => {});
}

// ────────────────────────────────────────────────────────────
// DOWNLOADS TAB
// ────────────────────────────────────────────────────────────

let urlFetchTimer = null;

function onUrlInput(value) {
  clearTimeout(urlFetchTimer);
  const infoCard = document.getElementById('urlInfoCard');
  if (!value || value.length < 15) {
    infoCard.classList.remove('visible');
    return;
  }
  urlFetchTimer = setTimeout(() => fetchUrlInfo(value), 900);
}

function fetchUrlInfo(url) {
  if (!window.pywebview || !window.pywebview.api) return;
  window.pywebview.api.fetch_video_info(url).then(info => {
    if (info && info.title) {
      document.getElementById('urlTitle').textContent = info.title.substring(0, 80);
      document.getElementById('urlSub').textContent =
        (info.uploader || '') + '  •  ' + (info.platform || '') + '  •  ' + (info.duration_str || '');

      const thumbEl = document.getElementById('urlThumb');
      if (info.thumbnail_url) {
        thumbEl.src = info.thumbnail_url;
        thumbEl.style.display = '';
      } else {
        thumbEl.style.display = 'none';
      }
      document.getElementById('urlInfoCard').classList.add('visible');
    }
  }).catch(() => {});
}

function startDownload() {
  const url = document.getElementById('urlInput').value.trim();
  if (!url) {
    appendLog('⚠️ Lütfen geçerli bir video bağlantısı girin!', 'warning');
    return;
  }
  if (!window.pywebview || !window.pywebview.api) {
    appendLog('❌ Python API bağlantısı henüz hazır değil.', 'error');
    return;
  }

  const btn = document.getElementById('btnDownload');
  btn.disabled = true;
  btn.textContent = '⏳ İndiriliyor...';
  document.getElementById('dlProgressWrap').style.display = '';

  window.pywebview.api.start_download(url);
}

window.onDownloadComplete = function(filePath) {
  const btn = document.getElementById('btnDownload');
  btn.disabled = false;
  btn.textContent = '⬇️ İndir';
  document.getElementById('dlProgressWrap').style.display = 'none';

  appendLog('✅ İndirme tamamlandı!', 'success');
  refreshDownloads();

  // Auto-open in studio
  if (filePath) {
    const fn = filePath.split(/[\\/]/).pop();
    setTimeout(() => openInStudio(filePath, fn), 300);
  }
};

function refreshDownloads() {
  if (!window.pywebview || !window.pywebview.api) return;
  window.pywebview.api.get_downloaded_videos().then(videos => {
    State.downloadedVideos = videos;
    renderVideoGrid('downloadGrid', 'downloadEmpty', videos, {
      showStudio: true, showDelete: true
    });
    refreshStudioGrid();
  }).catch(() => {});
}

function startScanProfile() {
  const url = document.getElementById('urlInput').value.trim();
  if (!url) {
    appendLog('⚠️ Lütfen profil / kanal URL\'si girin!', 'warning');
    return;
  }
  const btn = document.getElementById('btnScan');
  btn.disabled = true;
  btn.textContent = '⏳ Taranıyor...';

  document.getElementById('profileResultsWrap').style.display = 'none';

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.scan_profile(url);
  }

  setTimeout(() => {
    btn.disabled = false;
    btn.textContent = '🔍 Tara';
  }, 5000);
}

window.onProfileScanComplete = function(items) {
  State.profileScanItems = items || [];
  const btn = document.getElementById('btnScan');
  btn.disabled = false;
  btn.textContent = '🔍 Tara';

  if (!items || items.length === 0) {
    appendLog('⚠️ Profil videoları bulunamadı.', 'warning');
    return;
  }

  appendLog('✅ ' + items.length + ' video bulundu.', 'success');
  document.getElementById('profileResultCount').textContent = items.length + ' video';
  document.getElementById('profileResultsWrap').style.display = '';
  renderProfileResults(items);
};

function renderProfileResults(items) {
  const container = document.getElementById('profileResults');
  container.innerHTML = '';

  items.slice(0, 50).forEach(item => {
    const card = document.createElement('div');
    card.className = 'profile-reel-card';

    const thumb = document.createElement('div');
    thumb.className = 'profile-reel-thumb';
    thumb.textContent = '🎬';

    if (item.thumbnail_url) {
      const img = document.createElement('img');
      img.src = item.thumbnail_url;
      img.style.cssText = 'width:120px;height:213px;object-fit:cover;display:block;';
      img.onerror = () => {};
      thumb.textContent = '';
      thumb.appendChild(img);
    }

    const title = document.createElement('div');
    title.className = 'profile-reel-title';
    title.textContent = (item.title || 'Reel Video').substring(0, 30);

    const btn = document.createElement('button');
    btn.className = 'btn btn-primary';
    btn.textContent = '⚡ İndir';
    btn.onclick = () => {
      document.getElementById('urlInput').value = item.url || '';
      startDownload();
    };

    card.appendChild(thumb);
    card.appendChild(title);
    card.appendChild(btn);
    container.appendChild(card);
  });
}

function batchDownloadAll() {
  const items = State.profileScanItems;
  if (!items || items.length === 0) return;
  appendLog('⚡ Toplu indirme başlatılıyor: ' + items.length + ' video...', 'info');

  let idx = 0;
  const next = () => {
    if (idx >= items.length) {
      appendLog('🎉 Toplu indirme tamamlandı!', 'success');
      refreshDownloads();
      return;
    }
    const item = items[idx++];
    if (!item.url) { next(); return; }
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.start_download(item.url).then(() => {
        setTimeout(next, 500);
      }).catch(() => next());
    }
  };
  next();
}

// ────────────────────────────────────────────────────────────
// STUDIO TAB
// ────────────────────────────────────────────────────────────

function refreshStudioGrid() {
  if (!window.pywebview || !window.pywebview.api) return;
  window.pywebview.api.get_downloaded_videos().then(videos => {
    renderVideoGrid('studioGrid', 'studioEmpty', videos, { showStudio: false, showDelete: false });
    // Attach click handlers manually
    document.querySelectorAll('#studioGrid .video-card').forEach(card => {
      card.onclick = () => openInStudio(card.dataset.path, card.dataset.path.split(/[\\/]/).pop());
    });
  }).catch(() => {});
}

function formatFileUrl(pathStr) {
  if (!pathStr) return '';
  const normalized = pathStr.replace(/\\/g, '/');
  const parts = normalized.split('/');
  const encodedParts = parts.map((part, idx) => {
    if (idx === 0 && part.endsWith(':')) return part;
    return encodeURIComponent(part);
  });
  let result = encodedParts.join('/');
  if (!result.startsWith('/')) result = '/' + result;
  return 'file://' + result;
}

function openInStudio(videoPath, filename) {
  State.currentStudioPath = videoPath;
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.set_studio_video(videoPath);
  }

  // Load video into preview with proper URL encoding
  const video = document.getElementById('previewVideo');
  video.src = formatFileUrl(videoPath);
  video.load();
  video.play().then(() => {
    startPreviewAnimation();
  }).catch(() => {
    updatePreview();
  });

  document.getElementById('studioFileName').textContent = filename;

  // Mark selected in studio grid
  document.querySelectorAll('#studioGrid .video-card').forEach(c => {
    c.classList.toggle('selected', c.dataset.path === videoPath);
  });

  appendLog('🎬 Stüdyoya yüklendi: ' + filename, 'info');
  switchTab('studio');
  updatePreview();
}

function applyPreset(preset) {
  if (preset === 'reels') {
    document.getElementById('chkLogo').checked = true;
    document.getElementById('chkBlur').checked = true;
    setLogoPreset('logo_724mizah_transparent.png');
    appendLog('✅ Instagram Reels şablonu uygulandı.', 'success');
  } else if (preset === 'tiktok') {
    document.getElementById('chkLogo').checked = true;
    document.getElementById('chkBlur').checked = true;
    setLogoPreset('logo_724mizah_dark.png');
    appendLog('✅ TikTok şablonu uygulandı.', 'success');
  } else if (preset === 'shorts') {
    document.getElementById('chkLogo').checked = true;
    document.getElementById('chkBlur').checked = true;
    setLogoPreset('logo_724mizah_light.png');
    appendLog('✅ YouTube Shorts şablonu uygulandı.', 'success');
  }
  updatePreview();
}

function setLogoPreset(filename) {
  // Get base path from API
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.get_app_info().then(info => {
      if (info && info.base_dir) {
        const logoPath = info.base_dir + '\\assets\\' + filename;
        document.getElementById('logoPath').value = logoPath;
        loadLogoPreview(logoPath);
        updatePreview();
      }
    });
  }
}

function browseLogo() {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.select_logo_file().then(path => {
      if (path) {
        document.getElementById('logoPath').value = path;
        loadLogoPreview(path);
        updatePreview();
        appendLog('Logo seçildi: ' + path.split(/[\\/]/).pop(), 'info');
      }
    });
  }
}

function startProcess() {
  if (!State.currentStudioPath) {
    appendLog('⚠️ Önce bir video seçin!', 'warning');
    return;
  }

  const frameEnabled = document.getElementById('chkFrame') && document.getElementById('chkFrame').checked && !!selectedFrameTemplate;
  const frameZoom = document.getElementById('sliderFrameZoom') ? parseInt(document.getElementById('sliderFrameZoom').value) / 100 : 1.0;
  const frameOffX = document.getElementById('sliderFrameOffX') ? parseInt(document.getElementById('sliderFrameOffX').value) : 0;
  const frameOffY = document.getElementById('sliderFrameOffY') ? parseInt(document.getElementById('sliderFrameOffY').value) : 0;

  // Active Multi-Blur Boxes (B1..B5)
  const activeBlurBoxes = blurSlots
    .filter(slot => slot.enabled)
    .map(slot => [slot.rx, slot.ry, slot.rw, slot.rh]);

  const options = {
    source_path: State.currentStudioPath,
    logo_enabled: document.getElementById('chkLogo').checked,
    logo_path: document.getElementById('logoPath').value.trim() || null,
    logo_scale: parseInt(document.getElementById('sliderLogoScale').value) / 100,
    logo_x: State.logoRelX,
    logo_y: State.logoRelY,

    // Multi-Blur Parameters
    blur_enabled: activeBlurBoxes.length > 0,
    blur_boxes: activeBlurBoxes,

    text_watermark: document.getElementById('textWatermark').value.trim() || null,
    quality_label: State.quality,

    // Frame Studio Parameters
    frame_enabled: frameEnabled,
    frame_png_path: frameEnabled && selectedFrameTemplate ? selectedFrameTemplate.png_path : null,
    frame_config: frameEnabled && selectedFrameTemplate ? selectedFrameTemplate : null,
    frame_adjustments: frameEnabled ? { zoom: frameZoom, offsetX: frameOffX, offsetY: frameOffY } : null
  };

  const btn = document.getElementById('btnProcess');
  btn.disabled = true;
  btn.textContent = '⏳ İşleniyor...';
  document.getElementById('processProgressWrap').style.display = '';

  appendLog('🎨 Video işleniyor...', 'info');

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.start_process(options);
  }
}

window.onProcessComplete = function(outPath) {
  const btn = document.getElementById('btnProcess');
  btn.disabled = false;
  btn.textContent = '✨ Videoyu İşle ve Yüksek Kalitede Kaydet';
  document.getElementById('processProgressWrap').style.display = 'none';
  appendLog('🎉 İşlem tamamlandı! → ' + (outPath.split(/[\\/]/).pop()), 'success');
  refreshQueueGrid();
  setTimeout(() => switchTab('queue'), 500);
};

// ────────────────────────────────────────────────────────────
// CANVAS PREVIEW (9:16 overlay with drag support)
// ────────────────────────────────────────────────────────────

let canvasCtx = null;
let logoPosX = 0.78, logoPosY = 0.88;
let logoImg = null;
let isDraggingLogo = false;
let draggingBlurIndex = -1;

// Multi-Blur Slots B1 - B5
let blurSlots = [
  { enabled: true,  rx: 0.65, ry: 0.88, rw: 0.35, rh: 0.12 }, // B1
  { enabled: false, rx: 0.35, ry: 0.88, rw: 0.35, rh: 0.12 }, // B2
  { enabled: false, rx: 0.50, ry: 0.50, rw: 0.35, rh: 0.12 }, // B3
  { enabled: false, rx: 0.50, ry: 0.30, rw: 0.35, rh: 0.12 }, // B4
  { enabled: false, rx: 0.50, ry: 0.70, rw: 0.35, rh: 0.12 }  // B5
];
let activeBlurIndex = 0;

function switchBlurSlot(index) {
  activeBlurIndex = index;
  for (let i = 0; i < 5; i++) {
    const btn = document.getElementById('btnBlurSlot' + i);
    if (btn) {
      if (i === index) {
        btn.style.background = 'rgba(59,130,246,0.2)';
        btn.style.borderColor = 'var(--accent-blue)';
      } else {
        btn.style.background = 'transparent';
        btn.style.borderColor = 'rgba(255,255,255,0.1)';
      }
    }
  }

  const slot = blurSlots[index];
  const titleEl = document.getElementById('lblActiveBlurSlotTitle');
  if (titleEl) titleEl.textContent = `B${index + 1} Blur Kutusu`;

  const chk = document.getElementById('chkActiveBlur');
  if (chk) chk.checked = slot.enabled;

  const sliderW = document.getElementById('sliderBlurW');
  const sliderH = document.getElementById('sliderBlurH');
  if (sliderW) {
    sliderW.value = Math.round(slot.rw * 100);
    const wVal = document.getElementById('blurWVal');
    if (wVal) wVal.textContent = sliderW.value + '%';
  }
  if (sliderH) {
    sliderH.value = Math.round(slot.rh * 100);
    const hVal = document.getElementById('blurHVal');
    if (hVal) hVal.textContent = sliderH.value + '%';
  }
  updatePreview();
}

function toggleActiveBlurSlot(checked) {
  blurSlots[activeBlurIndex].enabled = checked;
  updatePreview();
}

function onBlurWidthChange(val) {
  blurSlots[activeBlurIndex].rw = parseInt(val) / 100;
  const wVal = document.getElementById('blurWVal');
  if (wVal) wVal.textContent = val + '%';
  updatePreview();
}

function onBlurHeightChange(val) {
  blurSlots[activeBlurIndex].rh = parseInt(val) / 100;
  const hVal = document.getElementById('blurHVal');
  if (hVal) hVal.textContent = val + '%';
  updatePreview();
}

let previewAnimFrameId = null;

function startPreviewAnimation() {
  if (previewAnimFrameId) cancelAnimationFrame(previewAnimFrameId);

  function renderLoop() {
    const vid = document.getElementById('previewVideo');
    if (vid && !vid.paused && !vid.ended) {
      drawOverlay();
      previewAnimFrameId = requestAnimationFrame(renderLoop);
    } else {
      previewAnimFrameId = null;
    }
  }
  previewAnimFrameId = requestAnimationFrame(renderLoop);
}

function stopPreviewAnimation() {
  if (previewAnimFrameId) {
    cancelAnimationFrame(previewAnimFrameId);
    previewAnimFrameId = null;
  }
}

function initPreviewCanvas() {
  const canvas = document.getElementById('previewCanvas');
  if (!canvas) return;
  canvasCtx = canvas.getContext('2d');

  const video = document.getElementById('previewVideo');
  if (video) {
    video.onplay = () => startPreviewAnimation();
    video.onpause = () => { stopPreviewAnimation(); drawOverlay(); };
    video.onseeked = () => drawOverlay();
    video.onloadeddata = () => drawOverlay();
    video.ontimeupdate = () => {
      if (!previewAnimFrameId) drawOverlay();
    };
  }

  drawOverlay();
}

function loadLogoPreview(path) {
  if (!path) { logoImg = null; drawOverlay(); return; }
  const img = new Image();
  img.onload = () => { logoImg = img; drawOverlay(); };
  img.onerror = () => { logoImg = null; };
  img.src = formatFileUrl(path);
}

function updatePreview() {
  State.logoRelX = logoPosX;
  State.logoRelY = logoPosY;
  drawOverlay();
}

function drawOverlay() {
  const canvas = document.getElementById('previewCanvas');
  if (!canvasCtx || !canvas) return;
  const W = canvas.width;   // 540
  const H = canvas.height;  // 960

  canvasCtx.clearRect(0, 0, W, H);

  // Draw Custom Frame Overlay & Video Clip if active
  const frameEnabled = document.getElementById('chkFrame') && document.getElementById('chkFrame').checked && selectedFrameTemplate && selectedFrameImageObj;
  if (frameEnabled) {
    canvasCtx.fillStyle = '#0B0F19';
    canvasCtx.fillRect(0, 0, W, H);

    const va = selectedFrameTemplate.videoArea || { x: 0, y: 0, width: 1080, height: 1920 };
    const refW = selectedFrameTemplate.canvasWidth || 1080;
    const refH = selectedFrameTemplate.canvasHeight || 1920;

    const scaleX = W / refW;
    const scaleY = H / refH;

    const fbx = va.x * scaleX;
    const fby = va.y * scaleY;
    const fbw = va.width * scaleX;
    const fbh = va.height * scaleY;

    const zoom = document.getElementById('sliderFrameZoom') ? parseInt(document.getElementById('sliderFrameZoom').value) / 100 : 1.0;
    const offX = document.getElementById('sliderFrameOffX') ? parseInt(document.getElementById('sliderFrameOffX').value) * scaleX : 0;
    const offY = document.getElementById('sliderFrameOffY') ? parseInt(document.getElementById('sliderFrameOffY').value) * scaleY : 0;

    const vid = document.getElementById('previewVideo');
    if (vid && vid.readyState >= 1 && vid.videoWidth > 0) {
      canvasCtx.save();
      canvasCtx.beginPath();
      canvasCtx.rect(fbx, fby, fbw, fbh);
      canvasCtx.clip();

      const vw = fbw * zoom;
      const vh = fbh * zoom;
      const vx = fbx + (fbw - vw) / 2 + offX;
      const vy = fby + (fbh - vh) / 2 + offY;

      canvasCtx.drawImage(vid, vx, vy, vw, vh);
      canvasCtx.restore();
    }

    // CRITICAL: Draw Frame PNG Overlay ALWAYS ON TOP of video
    canvasCtx.drawImage(selectedFrameImageObj, 0, 0, W, H);
  }

  // Draw Multi-Blur Boxes (B1 - B5)
  const vid = document.getElementById('previewVideo');
  blurSlots.forEach((slot, idx) => {
    if (!slot.enabled) return;

    const bw = slot.rw * W;
    const bh = slot.rh * H;
    const bx = slot.rx * W - bw / 2;
    const by = slot.ry * H - bh / 2;

    canvasCtx.save();
    if (vid && vid.readyState >= 1 && vid.videoWidth > 0) {
      const scaleX = vid.videoWidth / W;
      const scaleY = vid.videoHeight / H;
      const sx = Math.max(0, Math.min(bx * scaleX, vid.videoWidth - 10));
      const sy = Math.max(0, Math.min(by * scaleY, vid.videoHeight - 10));
      const sw = Math.max(10, Math.min(bw * scaleX, vid.videoWidth - sx));
      const sh = Math.max(10, Math.min(bh * scaleY, vid.videoHeight - sy));

      try {
        canvasCtx.filter = 'blur(12px)';
        canvasCtx.drawImage(vid, sx, sy, sw, sh, bx, by, bw, bh);
        canvasCtx.filter = 'none';

        canvasCtx.fillStyle = 'rgba(0, 0, 0, 0.20)';
        canvasCtx.fillRect(bx, by, bw, bh);
      } catch (err) {
        canvasCtx.globalAlpha = 0.7;
        canvasCtx.fillStyle = '#0f172a';
        canvasCtx.fillRect(bx, by, bw, bh);
        canvasCtx.globalAlpha = 1.0;
      }
    } else {
      canvasCtx.globalAlpha = 0.75;
      canvasCtx.fillStyle = '#0f172a';
      canvasCtx.fillRect(bx, by, bw, bh);
      canvasCtx.globalAlpha = 1.0;
    }

    // Blur box border
    canvasCtx.strokeStyle = (idx === activeBlurIndex) ? '#3B82F6' : '#6366F1';
    canvasCtx.lineWidth = (idx === activeBlurIndex) ? 2.0 : 1.2;
    canvasCtx.setLineDash([4, 3]);
    canvasCtx.strokeRect(bx, by, bw, bh);
    canvasCtx.setLineDash([]);

    // Draw drag handle labeled B1, B2, B3, B4, B5
    const handleColor = (idx === activeBlurIndex) ? '#2563EB' : '#4F46E5';
    drawDragHandle(slot.rx * W, slot.ry * H, handleColor, 'B' + (idx + 1));
    canvasCtx.restore();
  });

  // Draw logo
  const logoEnabled = document.getElementById('chkLogo') && document.getElementById('chkLogo').checked;
  if (logoEnabled && logoImg) {
    const logoScale = parseInt(document.getElementById('sliderLogoScale').value) / 100;
    const lw = W * logoScale;
    const lh = lw * logoImg.height / logoImg.width;
    const lx = logoPosX * W - lw / 2;
    const ly = logoPosY * H - lh / 2;
    canvasCtx.drawImage(logoImg, lx, ly, lw, lh);
    drawDragHandle(logoPosX * W, logoPosY * H, '#7C3AED', 'L');
  } else if (logoEnabled) {
    drawDragHandle(logoPosX * W, logoPosY * H, '#7C3AED', 'L');
  }

  // Text watermark
  const text = document.getElementById('textWatermark') && document.getElementById('textWatermark').value;
  if (text) {
    canvasCtx.save();
    canvasCtx.font = 'bold 22px Inter, sans-serif';
    canvasCtx.fillStyle = '#FFFFFF';
    canvasCtx.globalAlpha = 0.85;
    canvasCtx.textAlign = 'center';
    canvasCtx.fillText(text, W / 2, H - 40);
    canvasCtx.restore();
  }
}

function drawDragHandle(cx, cy, color, label) {
  const r = 16;
  canvasCtx.save();
  canvasCtx.beginPath();
  canvasCtx.arc(cx, cy, r, 0, Math.PI * 2);
  canvasCtx.fillStyle = color;
  canvasCtx.globalAlpha = 0.85;
  canvasCtx.fill();
  canvasCtx.globalAlpha = 1;
  canvasCtx.fillStyle = '#fff';
  canvasCtx.font = 'bold 12px Inter, sans-serif';
  canvasCtx.textAlign = 'center';
  canvasCtx.textBaseline = 'middle';
  canvasCtx.fillText(label, cx, cy);
  canvasCtx.restore();
}

function setupPreviewDrag() {
  const canvas = document.getElementById('previewCanvas');
  if (!canvas) return;

  canvas.style.pointerEvents = 'all';
  canvas.style.cursor = 'crosshair';

  canvas.addEventListener('mousedown', e => {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / rect.width;
    const my = (e.clientY - rect.top) / rect.height;

    const logoEnabled = document.getElementById('chkLogo') && document.getElementById('chkLogo').checked;

    // Check if near any enabled blur handle B1..B5
    let hitBlurIdx = -1;
    blurSlots.forEach((slot, idx) => {
      if (slot.enabled && hitBlurIdx === -1 && dist(mx, my, slot.rx, slot.ry) < 0.07) {
        hitBlurIdx = idx;
      }
    });

    const nearLogo = logoEnabled && dist(mx, my, logoPosX, logoPosY) < 0.06;

    if (hitBlurIdx !== -1) {
      draggingBlurIndex = hitBlurIdx;
      switchBlurSlot(hitBlurIdx);
      canvas.style.cursor = 'move';
    } else if (nearLogo) {
      isDraggingLogo = true;
      canvas.style.cursor = 'move';
    }
  });

  canvas.addEventListener('mousemove', e => {
    if (!isDraggingLogo && draggingBlurIndex === -1) return;
    const rect = canvas.getBoundingClientRect();
    const mx = Math.max(0.02, Math.min(0.98, (e.clientX - rect.left) / rect.width));
    const my = Math.max(0.02, Math.min(0.98, (e.clientY - rect.top) / rect.height));

    if (isDraggingLogo) { logoPosX = mx; logoPosY = my; State.logoRelX = mx; State.logoRelY = my; }
    if (draggingBlurIndex !== -1) {
      blurSlots[draggingBlurIndex].rx = mx;
      blurSlots[draggingBlurIndex].ry = my;
    }

    drawOverlay();
  });

  canvas.addEventListener('mouseup', () => {
    isDraggingLogo = false;
    draggingBlurIndex = -1;
    canvas.style.cursor = 'crosshair';
  });

  canvas.addEventListener('mouseleave', () => {
    isDraggingLogo = false;
    draggingBlurIndex = -1;
  });
}

function dist(ax, ay, bx, by) {
  return Math.sqrt((ax - bx) ** 2 + (ay - by) ** 2);
}

// ────────────────────────────────────────────────────────────
// QUEUE / UPLOAD TAB
// ────────────────────────────────────────────────────────────

function refreshQueueGrid() {
  if (!window.pywebview || !window.pywebview.api) return;
  window.pywebview.api.get_processed_videos().then(videos => {
    State.processedVideos = videos;
    renderVideoGrid('queueGrid', 'queueEmpty', videos, {
      showUpload: true, showDelete: true
    });
  }).catch(() => {});
}

function toggleChip(platform) {
  const chip = document.getElementById('chip-' + platform);
  const chk = document.getElementById('chk' + platform.charAt(0).toUpperCase() + platform.slice(1));
  if (chk.checked) {
    chip.classList.add('checked');
  } else {
    chip.classList.remove('checked');
  }
}

function getSelectedPlatforms() {
  return {
    instagram: document.getElementById('chkIg').checked,
    youtube:   document.getElementById('chkYt').checked,
    tiktok:    document.getElementById('chkTt').checked,
    threads:   document.getElementById('chkTh').checked,
    facebook:  document.getElementById('chkFb').checked
  };
}

function openUploadModal(videoPath, filename, caption, hashtagsStr) {
  State.uploadTargetPath = videoPath;
  document.getElementById('uploadVideoName').textContent = filename;

  let captionText = caption || '';
  if (hashtagsStr && !captionText.includes(hashtagsStr)) {
    captionText = captionText ? captionText + '\n\n' + hashtagsStr : hashtagsStr;
  }

  // Fetch cleaned metadata with channel name replacement
  if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.get_video_metadata === 'function') {
    window.pywebview.api.get_video_metadata(videoPath).then(meta => {
      if (meta && !meta.error) {
        let text = meta.description || meta.title || '';
        if (meta.tags_str && !text.includes(meta.tags_str)) {
          text = text ? text + '\n\n' + meta.tags_str : meta.tags_str;
        }
        document.getElementById('uploadCaptionInput').value = text;
      } else {
        document.getElementById('uploadCaptionInput').value = captionText;
      }
    }).catch(() => {
      document.getElementById('uploadCaptionInput').value = captionText;
    });
  } else {
    document.getElementById('uploadCaptionInput').value = captionText;
  }

  openModal('uploadModal');
}

function confirmUpload() {
  const videoPath = State.uploadTargetPath;
  if (!videoPath) return;

  const platforms = getSelectedPlatforms();
  const active = Object.keys(platforms).filter(k => platforms[k]);
  if (active.length === 0) {
    appendLog('⚠️ Lütfen en az bir platform seçin!', 'warning');
    return;
  }

  const caption = document.getElementById('uploadCaptionInput').value.trim();

  closeModal('uploadModal');
  appendLog('🚀 Yükleme başlatılıyor: ' + active.map(p => p.toUpperCase()).join(', '), 'info');

  const btn = document.getElementById('btnConfirmUpload');
  btn.disabled = true;

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.upload_video(videoPath, platforms, caption).then(res => {
      btn.disabled = false;
    }).catch(() => { btn.disabled = false; });
  }
}

window.onUploadComplete = function(results) {
  const btn = document.getElementById('btnConfirmUpload');
  if (btn) btn.disabled = false;

  let msg = '';
  Object.entries(results).forEach(([platform, result]) => {
    const icon = result.success ? '✅' : '❌';
    msg += icon + ' ' + platform.toUpperCase() + ': ' + (result.message || '').substring(0, 80) + '\n';
    appendLog(icon + ' ' + platform.toUpperCase() + ': ' + (result.success ? 'Başarılı' : result.message), result.success ? 'success' : 'error');
  });
};

// ────────────────────────────────────────────────────────────
// API KEYS TAB
// ────────────────────────────────────────────────────────────

function loadApiKeys() {
  if (!window.pywebview || !window.pywebview.api) return;
  window.pywebview.api.get_api_keys().then(keys => {
    if (!keys || keys.error) return;

    // Instagram
    const auth = keys.instagram_auth || {};
    safeSet('igAccountId', keys.instagram_account_id || '');
    safeSet('igAccessToken', keys.instagram_access_token || '');
    safeSet('igUsername', auth.username || '');
    safeSet('igPassword', auth.password || '');
    safeSet('igSessionId', auth.sessionid || '');
    safeCheck('chkHesapsiz', auth.use_hesapsiz || false);

    // YouTube
    safeSet('ytClientId', keys.youtube_client_id || '');
    safeSet('ytClientSecret', keys.youtube_client_secret || '');
    safeSet('ytRefreshToken', keys.youtube_refresh_token || '');
    safeSet('ytApiKey', keys.youtube_api_key || '');
    safeSet('ytDefaultTitle', keys.youtube_default_title || '');

    // TikTok
    safeSet('ttClientKey', keys.tiktok_client_key || '');
    safeSet('ttClientSecret', keys.tiktok_client_secret || '');
    safeSet('ttScope', keys.tiktok_scope || 'user.info.basic,video.publish');
    safeSet('ttOpenId', keys.tiktok_open_id || '');
    safeSet('ttAccessToken', keys.tiktok_access_token || '');

    // Facebook
    safeSet('fbPageId', keys.facebook_page_id || '');

    // Threads
    safeSet('thUserId', keys.threads_user_id || '');

    updateApiStatusDots(keys);
  }).catch(() => {});
}

function refreshApiKeysUI() {
  if (!window.pywebview || !window.pywebview.api) {
    appendLog('❌ API bağlantısı henüz hazır değil.', 'error');
    return;
  }
  appendLog('🔄 API Anahtarları diskten yeniden yükleniyor...', 'info');
  window.pywebview.api.get_api_keys().then(keys => {
    if (!keys || keys.error) {
      appendLog('❌ API anahtarları yüklenirken hata oluştu: ' + (keys ? (keys.error || '') : ''), 'error');
      return;
    }

    // Instagram
    const auth = keys.instagram_auth || {};
    safeSet('igAccountId', keys.instagram_account_id || '');
    safeSet('igAccessToken', keys.instagram_access_token || '');
    safeSet('igUsername', auth.username || '');
    safeSet('igPassword', auth.password || '');
    safeSet('igSessionId', auth.sessionid || '');
    safeCheck('chkHesapsiz', auth.use_hesapsiz || false);

    // YouTube
    safeSet('ytClientId', keys.youtube_client_id || '');
    safeSet('ytClientSecret', keys.youtube_client_secret || '');
    safeSet('ytRefreshToken', keys.youtube_refresh_token || '');
    safeSet('ytApiKey', keys.youtube_api_key || '');
    safeSet('ytDefaultTitle', keys.youtube_default_title || '');

    // TikTok
    safeSet('ttClientKey', keys.tiktok_client_key || '');
    safeSet('ttClientSecret', keys.tiktok_client_secret || '');
    safeSet('ttScope', keys.tiktok_scope || 'user.info.basic,video.publish');
    safeSet('ttOpenId', keys.tiktok_open_id || '');
    safeSet('ttAccessToken', keys.tiktok_access_token || '');

    // Facebook
    safeSet('fbPageId', keys.facebook_page_id || '');

    // Threads
    safeSet('thUserId', keys.threads_user_id || '');

    updateApiStatusDots(keys);
    appendLog('✅ API Anahtarları diskten başarıyla yenilendi.', 'success');
  }).catch(err => {
    appendLog('❌ API anahtarları yenileme hatası: ' + err, 'error');
  });
}

function safeSet(id, val) {
  const el = document.getElementById(id);
  console.log(`DEBUG [safeSet]: id='${id}', value='${val}', elementFound=${!!el}`);
  if (el) {
    el.value = val;
    console.log(`DEBUG [safeSet]: Set element '${id}' value to '${el.value}'`);
  }
}

function safeCheck(id, val) {
  const el = document.getElementById(id);
  if (el) el.checked = val;
}

function updateApiStatusDots(keys) {
  const setDot = (id, ok) => {
    const dot = document.getElementById(id);
    if (dot) {
      dot.className = 'status-dot ' + (ok ? 'ok' : 'unknown');
    }
  };
  setDot('dotIg', !!(keys.instagram_account_id && keys.instagram_access_token));
  setDot('dotYt', !!(keys.youtube_client_id && keys.youtube_refresh_token));
  setDot('dotTt', !!keys.tiktok_access_token);
  setDot('dotFb', !!keys.facebook_page_id);
  setDot('dotTh', !!(keys.threads_user_id || keys.instagram_account_id));
}

function saveApiKeys() {
  const data = {
    instagram_account_id: document.getElementById('igAccountId').value.trim(),
    instagram_access_token: document.getElementById('igAccessToken').value.trim(),
    instagram_auth: {
      username: document.getElementById('igUsername').value.trim(),
      password: document.getElementById('igPassword').value,
      sessionid: document.getElementById('igSessionId').value.trim(),
      use_hesapsiz: document.getElementById('chkHesapsiz').checked
    },
    youtube_client_id:     document.getElementById('ytClientId').value.trim(),
    youtube_client_secret: document.getElementById('ytClientSecret').value.trim(),
    youtube_refresh_token: document.getElementById('ytRefreshToken').value.trim(),
    youtube_api_key:       document.getElementById('ytApiKey').value.trim(),
    youtube_default_title: document.getElementById('ytDefaultTitle') ? document.getElementById('ytDefaultTitle').value.trim() : '',
    tiktok_client_key:     document.getElementById('ttClientKey').value.trim(),
    tiktok_client_secret:  document.getElementById('ttClientSecret').value.trim(),
    tiktok_scope:          document.getElementById('ttScope') ? document.getElementById('ttScope').value.trim() : 'user.info.basic,video.publish',
    tiktok_open_id:        document.getElementById('ttOpenId').value.trim(),
    tiktok_access_token:   document.getElementById('ttAccessToken').value.trim(),
    facebook_page_id:      document.getElementById('fbPageId').value.trim(),
    threads_user_id:       document.getElementById('thUserId').value.trim()
  };

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.save_api_keys(data).then(res => {
      if (res.success) {
        appendLog('✅ API anahtarları kaydedildi.', 'success');
        updateApiStatusDots(data);
      } else {
        appendLog('❌ Kaydetme hatası: ' + (res.error || ''), 'error');
      }
    });
  }
}

function startTikTokAuthWizard(mode = 'popup') {
  console.log('DEBUG [startTikTokAuthWizard]: Function triggered mode=', mode);
  const clientKey = document.getElementById('ttClientKey').value.trim();
  const clientSecret = document.getElementById('ttClientSecret') ? document.getElementById('ttClientSecret').value.trim() : '';
  const scope = (document.getElementById('ttScope') ? document.getElementById('ttScope').value.trim() : '') || 'user.info.basic,video.publish';

  if (!clientKey) {
    appendLog('❌ TikTok Client Key boş olamaz. Lütfen önce Client Key girin.', 'error');
    return;
  }

  // Show waiting status
  var statusEl = document.getElementById('ttAuthStatus');
  var btnEl = document.getElementById('btnTtAuth');
  var btnBr = document.getElementById('btnTtAuthBrowser');
  if (statusEl) statusEl.style.display = 'block';
  if (btnEl) btnEl.disabled = true;
  if (btnBr) btnBr.disabled = true;

  const modeMsg = mode === 'browser' ? 'Sistem tarayıcınız açılacak (Google girişi desteklenir).' : 'Uygulama içi pencere açılacak.';
  appendLog('🔐 TikTok Giriş Sihirbazı başlatılıyor... ' + modeMsg, 'info');

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.start_tiktok_auth_wizard(clientKey, clientSecret, scope, mode).then(res => {
      console.log('DEBUG [startTikTokAuthWizard]: Async wizard started:', res);
    }).catch(err => {
      appendLog('❌ Bağlantı hatası: ' + err, 'error');
      if (statusEl) statusEl.style.display = 'none';
      if (btnEl) btnEl.disabled = false;
      if (btnBr) btnBr.disabled = false;
    });
  } else {
    appendLog('❌ PyWebView API bağlantısı bulunamadı.', 'error');
    if (statusEl) statusEl.style.display = 'none';
    if (btnEl) btnEl.disabled = false;
    if (btnBr) btnBr.disabled = false;
  }
}

function testInstagramApi() {
  const resultEl = document.getElementById('igTestResult');
  if (resultEl) resultEl.textContent = '⏳ Test ediliyor...';

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.test_instagram_api().then(res => {
      if (resultEl) {
        resultEl.textContent = res.message;
        resultEl.style.color = res.success ? 'var(--text-green)' : 'var(--danger)';
      }
      appendLog(res.message, res.success ? 'success' : 'error');
    });
  }
}

function toggleApiSection(id) {
  const body = document.getElementById('body' + id.charAt(0).toUpperCase() + id.slice(1));
  const chevron = document.getElementById('chevron' + id.charAt(0).toUpperCase() + id.slice(1));
  if (!body) return;
  const collapsed = body.classList.toggle('collapsed');
  if (chevron) chevron.textContent = collapsed ? '▶' : '▼';
}

// ────────────────────────────────────────────────────────────
// SETTINGS TAB
// ────────────────────────────────────────────────────────────

function openFolder(folderType) {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.open_folder(folderType);
  }
}

function saveQualitySetting() {
  State.quality = document.getElementById('selQuality').value;
  appendLog('🎥 Video kalitesi: ' + State.quality, 'info');
}

// ────────────────────────────────────────────────────────────
// UTILITY
// ────────────────────────────────────────────────────────────

function deleteVideoConfirm(videoPath, cardEl) {
  if (!confirm('Bu videoyu silmek istediğinizden emin misiniz?\n' + videoPath.split(/[\\/]/).pop())) return;
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.delete_video(videoPath).then(res => {
      if (res.success && cardEl) {
        cardEl.style.opacity = '0';
        cardEl.style.transition = 'opacity 0.2s';
        setTimeout(() => cardEl.remove(), 200);
      }
    });
  }
}

function togglePasswordVisibility(inputId) {
  const el = document.getElementById(inputId);
  if (el) {
    el.type = el.type === 'password' ? 'text' : 'password';
  }
}

// ────────────────────────────────────────────────────────────
// FRAME TEMPLATE STUDIO JS MODULE
// ────────────────────────────────────────────────────────────

let currentFrameTemplates = [];
let selectedFrameTemplate = null;
let selectedFrameImageObj = null;

let wizardPngDataUrl = null;
let wizardPngImageObj = null;
let wizardVideoArea = { x: 40, y: 120, width: 190, height: 240 };
let wizardIsDragging = false;
let wizardDragMode = null;
let wizardStartMouse = { x: 0, y: 0 };
let wizardStartRect = { x: 0, y: 0, width: 0, height: 0 };

function openFrameStudioModal() {
  openModal('modalFrameStudio');
  loadFrameTemplates();
}

function switchFrameTab(tab) {
  const libTab = document.getElementById('frameTabLibrary');
  const wizTab = document.getElementById('frameTabWizard');
  const libBtn = document.getElementById('tabFrameLibBtn');
  const wizBtn = document.getElementById('tabFrameWizardBtn');

  if (tab === 'library') {
    if (libTab) libTab.style.display = 'block';
    if (wizTab) wizTab.style.display = 'none';
    if (libBtn) { libBtn.style.background = 'rgba(59,130,246,0.2)'; libBtn.style.borderColor = 'var(--accent-blue)'; }
    if (wizBtn) { wizBtn.style.background = 'transparent'; wizBtn.style.borderColor = 'transparent'; }
  } else {
    if (libTab) libTab.style.display = 'none';
    if (wizTab) wizTab.style.display = 'block';
    if (wizBtn) { wizBtn.style.background = 'rgba(59,130,246,0.2)'; wizBtn.style.borderColor = 'var(--accent-blue)'; }
    if (libBtn) { libBtn.style.background = 'transparent'; libBtn.style.borderColor = 'transparent'; }
    initWizardCanvasEvents();
  }
}

function loadFrameTemplates() {
  if (!window.pywebview || !window.pywebview.api) return;
  window.pywebview.api.get_frame_templates().then(templates => {
    currentFrameTemplates = templates || [];
    renderFrameLibrary();
  }).catch(err => console.error('loadFrameTemplates error:', err));
}

function renderFrameLibrary() {
  const grid = document.getElementById('frameLibraryGrid');
  const lblCount = document.getElementById('lblFrameCount');
  const search = document.getElementById('txtFrameSearch') ? document.getElementById('txtFrameSearch').value.toLowerCase() : '';
  if (!grid) return;

  grid.innerHTML = '';
  const filtered = currentFrameTemplates.filter(t => (t.name || '').toLowerCase().includes(search) || (t.category || '').toLowerCase().includes(search));
  if (lblCount) lblCount.textContent = `${filtered.length} Şablon`;

  if (filtered.length === 0) {
    grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:30px; color:var(--text-muted);">Henüz içe aktarılmış özel çerçeve yok.<br>"Yeni PNG Çerçeve Yükle" sekmesinden ilk şablonunuzu ekleyin.</div>';
    return;
  }

  filtered.forEach(tpl => {
    const card = document.createElement('div');
    card.style.cssText = 'background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:10px; display:flex; flex-direction:column; align-items:center; gap:8px; position:relative;';

    const isSelected = selectedFrameTemplate && selectedFrameTemplate.name === tpl.name;
    if (isSelected) {
      card.style.borderColor = '#3B82F6';
      card.style.boxShadow = '0 0 12px rgba(59,130,246,0.3)';
    }

    const img = document.createElement('img');
    img.src = tpl.png_b64 || '';
    img.style.cssText = 'width:100%; height:180px; object-fit:contain; background:#05080F; border-radius:6px; border:1px solid rgba(255,255,255,0.05);';

    const title = document.createElement('div');
    title.style.cssText = 'font-weight:600; font-size:12px; color:var(--text-main); text-align:center; width:100%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;';
    title.textContent = tpl.name;

    const btnRow = document.createElement('div');
    btnRow.style.cssText = 'display:flex; gap:6px; width:100%; margin-top:4px;';

    const btnApply = document.createElement('button');
    btnApply.className = 'btn btn-primary';
    btnApply.style.cssText = 'flex:1; padding:4px 8px; font-size:11px;';
    btnApply.textContent = isSelected ? '✓ Seçili' : 'Kullan';
    btnApply.onclick = () => selectFrameTemplate(tpl);

    const btnDel = document.createElement('button');
    btnDel.className = 'btn btn-secondary';
    btnDel.style.cssText = 'padding:4px 8px; font-size:11px; color:#EF4444; border-color:rgba(239,68,68,0.3);';
    btnDel.textContent = '🗑️';
    btnDel.onclick = (e) => {
      e.stopPropagation();
      if (confirm(`'${tpl.name}' şablonunu silmek istiyor musunuz?`)) {
        window.pywebview.api.delete_frame_template(tpl.name).then(res => {
          if (selectedFrameTemplate && selectedFrameTemplate.name === tpl.name) {
            clearSelectedFrameTemplate();
          }
          loadFrameTemplates();
        });
      }
    };

    btnRow.appendChild(btnApply);
    btnRow.appendChild(btnDel);
    card.appendChild(img);
    card.appendChild(title);
    card.appendChild(btnRow);
    grid.appendChild(card);
  });
}

function selectFrameTemplate(tpl) {
  selectedFrameTemplate = tpl;
  const lbl = document.getElementById('lblSelectedFrame');
  if (lbl) lbl.textContent = 'Seçili: ' + tpl.name;

  const chk = document.getElementById('chkFrame');
  if (chk) chk.checked = true;

  const wrap = document.getElementById('frameControlsWrap');
  if (wrap) wrap.style.display = 'flex';

  selectedFrameImageObj = new Image();
  selectedFrameImageObj.onload = () => {
    updatePreview();
  };
  selectedFrameImageObj.src = tpl.png_b64;

  closeModal('modalFrameStudio');
  appendLog(`🖼️ '${tpl.name}' çerçeve şablonu uygulandı.`, 'success');
}

function clearSelectedFrameTemplate() {
  selectedFrameTemplate = null;
  selectedFrameImageObj = null;
  const lbl = document.getElementById('lblSelectedFrame');
  if (lbl) lbl.textContent = 'Seçili: Varsayılan (Çerçevesiz)';

  const chk = document.getElementById('chkFrame');
  if (chk) chk.checked = false;

  const wrap = document.getElementById('frameControlsWrap');
  if (wrap) wrap.style.display = 'none';

  updatePreview();
}

function resetFrameVideoAdjustments() {
  const z = document.getElementById('sliderFrameZoom');
  const x = document.getElementById('sliderFrameOffX');
  const y = document.getElementById('sliderFrameOffY');
  if (z) { z.value = 100; document.getElementById('frameZoomVal').textContent = '100%'; }
  if (x) { x.value = 0; document.getElementById('frameOffXVal').textContent = '0px'; }
  if (y) { y.value = 0; document.getElementById('frameOffYVal').textContent = '0px'; }
  updatePreview();
}

// ────────────────────────────────────────────────────────────
// FRAME CREATOR WIZARD (Interactive Canvas)
// ────────────────────────────────────────────────────────────

function onFramePngSelected(e) {
  const file = e.target.files[0];
  if (!file) return;

  const nameInput = document.getElementById('txtFrameName');
  if (nameInput && !nameInput.value) {
    nameInput.value = file.name.replace(/\.[^/.]+$/, "");
  }

  const reader = new FileReader();
  reader.onload = function(evt) {
    wizardPngDataUrl = evt.target.result;
    wizardPngImageObj = new Image();
    wizardPngImageObj.onload = function() {
      const ph = document.getElementById('wizardPlaceholder');
      if (ph) ph.style.display = 'none';
      drawWizardCanvas();
    };
    wizardPngImageObj.src = wizardPngDataUrl;
  };
  reader.readAsDataURL(file);
}

function drawWizardCanvas() {
  const cvs = document.getElementById('wizardCanvas');
  if (!cvs) return;
  const ctx = cvs.getContext('2d');
  const W = cvs.width;  // 270
  const H = cvs.height; // 480

  ctx.clearRect(0, 0, W, H);

  // 1. Draw PNG frame if loaded
  if (wizardPngImageObj) {
    ctx.drawImage(wizardPngImageObj, 0, 0, W, H);
  }

  // 2. Draw videoArea selection rectangle (Red dashed box)
  const r = wizardVideoArea;
  ctx.save();
  ctx.fillStyle = 'rgba(239, 68, 68, 0.15)';
  ctx.fillRect(r.x, r.y, r.width, r.height);

  ctx.strokeStyle = '#EF4444';
  ctx.lineWidth = 2;
  ctx.setLineDash([5, 4]);
  ctx.strokeRect(r.x, r.y, r.width, r.height);
  ctx.setLineDash([]);

  // Handles
  drawSquareHandle(ctx, r.x, r.y, '#EF4444');
  drawSquareHandle(ctx, r.x + r.width, r.y, '#EF4444');
  drawSquareHandle(ctx, r.x, r.y + r.height, '#EF4444');
  drawSquareHandle(ctx, r.x + r.width, r.y + r.height, '#EF4444');

  ctx.fillStyle = '#EF4444';
  ctx.font = 'bold 11px Inter, sans-serif';
  ctx.fillText('🎬 Video Safe Area', r.x + 6, r.y + 16);
  ctx.restore();
}

function drawSquareHandle(ctx, x, y, color) {
  ctx.fillStyle = color;
  ctx.fillRect(x - 4, y - 4, 8, 8);
  ctx.strokeStyle = '#FFFFFF';
  ctx.lineWidth = 1;
  ctx.strokeRect(x - 4, y - 4, 8, 8);
}

function initWizardCanvasEvents() {
  const cvs = document.getElementById('wizardCanvas');
  if (!cvs || cvs.dataset.eventsBound) return;

  cvs.dataset.eventsBound = 'true';

  cvs.addEventListener('mousedown', function(e) {
    const rect = cvs.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (cvs.width / rect.width);
    const my = (e.clientY - rect.top) * (cvs.height / rect.height);

    const r = wizardVideoArea;
    const cornerSize = 12;

    if (Math.abs(mx - (r.x + r.width)) < cornerSize && Math.abs(my - (r.y + r.height)) < cornerSize) {
      wizardIsDragging = true;
      wizardDragMode = 'resize-se';
    } else if (mx >= r.x && mx <= r.x + r.width && my >= r.y && my <= r.y + r.height) {
      wizardIsDragging = true;
      wizardDragMode = 'move';
      wizardStartMouse = { x: mx, y: my };
      wizardStartRect = { ...r };
    }
  });

  window.addEventListener('mousemove', function(e) {
    if (!wizardIsDragging || !cvs) return;
    const rect = cvs.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (cvs.width / rect.width);
    const my = (e.clientY - rect.top) * (cvs.height / rect.height);

    const r = wizardVideoArea;
    if (wizardDragMode === 'move') {
      const dx = mx - wizardStartMouse.x;
      const dy = my - wizardStartMouse.y;
      r.x = Math.max(0, Math.min(cvs.width - r.width, wizardStartRect.x + dx));
      r.y = Math.max(0, Math.min(cvs.height - r.height, wizardStartRect.y + dy));
    } else if (wizardDragMode === 'resize-se') {
      r.width = Math.max(30, Math.min(cvs.width - r.x, mx - r.x));
      r.height = Math.max(30, Math.min(cvs.height - r.y, my - r.y));
    }
    drawWizardCanvas();
  });

  window.addEventListener('mouseup', function() {
    wizardIsDragging = false;
    wizardDragMode = null;
  });
}

function saveFrameTemplateFromWizard() {
  const txtName = document.getElementById('txtFrameName');
  const txtCat = document.getElementById('txtFrameCategory');

  const name = txtName ? txtName.value.trim() : '';
  const category = txtCat ? txtCat.value.trim() : 'Genel';

  if (!name) {
    alert('Lütfen şablon adını girin!');
    return;
  }
  if (!wizardPngDataUrl) {
    alert('Lütfen bir PNG/WebP çerçeve dosyası seçin!');
    return;
  }

  const scale = 1080 / 270;
  const configData = {
    name: name,
    category: category,
    canvasWidth: 1080,
    canvasHeight: 1920,
    videoArea: {
      x: Math.round(wizardVideoArea.x * scale),
      y: Math.round(wizardVideoArea.y * scale),
      width: Math.round(wizardVideoArea.width * scale),
      height: Math.round(wizardVideoArea.height * scale)
    }
  };

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.import_frame_template(name, category, wizardPngDataUrl, JSON.stringify(configData)).then(res => {
      if (res.success) {
        alert(`✅ '${name}' şablonu başarıyla kaydedildi!`);
        switchFrameTab('library');
        loadFrameTemplates();
      } else {
        alert('❌ Şablon kaydetme hatası: ' + (res.error || ''));
      }
    });
  }
}
