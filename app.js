/* ===== Test Assist — app.js ===== */

/* ─── State ─── */
let currentTool = 'select';
let strokeColor = '#ff3b30';
let strokeSize  = 3;
let fillOpacity = 0.30;

let isDrawing   = false;
let startX = 0, startY = 0;
let lastX  = 0, lastY  = 0;
let penPath = [];

let annotations  = [];   // committed shapes
let undoStack    = [];
let redoStack    = [];

let selectedAnnotation = null;
let dragging = false;
let dragOffX = 0, dragOffY = 0;

let snapshots    = [];    // { id, label, baseDataUrl, annoDataUrl, annotations }

let mediaRecorder = null;
let recordedChunks = [];
let recInterval   = null;
let recSeconds    = 0;
let captureMode   = 'photo';

/* ─── Canvas setup ─── */
const baseCanvas = document.getElementById('baseCanvas');
const annoCanvas = document.getElementById('annoCanvas');
const baseCtx    = baseCanvas.getContext('2d');
const annoCtx    = annoCanvas.getContext('2d');
const container  = document.getElementById('canvasContainer');
const placeholder= document.getElementById('placeholder');
const body       = document.body;
const launcherStatus = document.getElementById('launcherStatus');
const editorStage = document.getElementById('editorStage');
const editorStageTitle = document.getElementById('editorStageTitle');
const editorStageText = document.getElementById('editorStageText');
const editorStageAction = document.getElementById('editorStageAction');
const editorStatePill = document.getElementById('editorStatePill');
const modePhotoBtn = document.getElementById('modePhoto');
const modeVideoBtn = document.getElementById('modeVideo');
const openEditorWindowBtn = document.getElementById('openEditorWindow');
const screenshotBtn = document.getElementById('btnScreenshot');
const recordBtn = document.getElementById('btnRecord');

function resizeCanvases(w, h) {
  baseCanvas.width  = annoCanvas.width  = w;
  baseCanvas.height = annoCanvas.height = h;
  container.style.width  = w + 'px';
  container.style.height = h + 'px';
}

/* ─── Tool selection ─── */
document.querySelectorAll('.tool-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentTool = btn.dataset.tool;
    annoCanvas.style.cursor = cursorForTool(currentTool);
  });
});

function cursorForTool(tool) {
  switch (tool) {
    case 'select': return 'default';
    case 'text':   return 'text';
    default:       return 'crosshair';
  }
}

/* ─── Tool options ─── */
document.getElementById('strokeColor').addEventListener('input', e => { strokeColor = e.target.value; });
document.getElementById('strokeSize').addEventListener('input', e => {
  strokeSize = parseInt(e.target.value);
  document.getElementById('strokeSizeLabel').textContent = strokeSize + 'px';
});
document.getElementById('fillOpacity').addEventListener('input', e => {
  fillOpacity = parseInt(e.target.value) / 100;
  document.getElementById('fillOpacityLabel').textContent = e.target.value + '%';
});

/* ─── Screenshot / Capture ─── */
screenshotBtn.addEventListener('click', captureScreen);
document.getElementById('btnCaptureTab').addEventListener('click', captureScreen);
modePhotoBtn.addEventListener('click', () => setCaptureMode('photo'));
modeVideoBtn.addEventListener('click', () => setCaptureMode('video'));
openEditorWindowBtn.addEventListener('click', () => setEditorState('active'));
editorStageAction.addEventListener('click', () => setEditorState('active'));

async function captureScreen() {
  try {
    if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: { cursor: 'always' }, audio: false });
      const track  = stream.getVideoTracks()[0];
      const capture= new ImageCapture(track);
      const bitmap = await capture.grabFrame();
      track.stop();
      loadImageBitmap(bitmap, 'background');
    } else {
      alert('Screen capture is not supported in this browser. Upload an image instead.');
    }
  } catch (err) {
    if (err.name !== 'NotAllowedError') {
      alert('Could not capture screen: ' + err.message);
    }
  }
}

function loadImageBitmap(bitmap, nextState = 'active') {
  resizeCanvases(bitmap.width, bitmap.height);
  baseCtx.drawImage(bitmap, 0, 0);
  placeholder.style.display = 'none';
  clearAnnotations(false);
  setEditorState(nextState);
}

function loadImageSrc(src, nextState = 'active') {
  const img = new Image();
  img.onload = () => {
    resizeCanvases(img.naturalWidth, img.naturalHeight);
    baseCtx.drawImage(img, 0, 0);
    placeholder.style.display = 'none';
    clearAnnotations(false);
    setEditorState(nextState);
  };
  img.src = src;
}

/* ─── Upload image ─── */
document.getElementById('uploadImage').addEventListener('change', e => {
  const file = e.target.files[0];
  if (!file) return;
  loadFromFile(file);
});

/* ─── Drag-and-drop onto canvas area ─── */
const canvasWrap = document.querySelector('.canvas-wrap');
canvasWrap.addEventListener('dragover', e => { e.preventDefault(); canvasWrap.style.outline = '3px dashed #7c83fd'; });
canvasWrap.addEventListener('dragleave', () => { canvasWrap.style.outline = ''; });
canvasWrap.addEventListener('drop', e => {
  e.preventDefault();
  canvasWrap.style.outline = '';
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) loadFromFile(file);
});

function loadFromFile(file) {
  const reader = new FileReader();
  reader.onload = e => loadImageSrc(e.target.result);
  reader.readAsDataURL(file);
}

/* ─── Video Recording ─── */
recordBtn.addEventListener('click', startRecording);
document.getElementById('btnStopRecord').addEventListener('click', stopRecording);

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
    recordedChunks = [];
    mediaRecorder = new MediaRecorder(stream, { mimeType: getSupportedMimeType() });
    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) recordedChunks.push(e.data); };
    mediaRecorder.onstop = saveRecording;
    mediaRecorder.start(200);

    recSeconds = 0;
    recInterval = setInterval(() => {
      recSeconds++;
      document.getElementById('recTime').textContent = formatTime(recSeconds);
    }, 1000);

    document.getElementById('recordingBadge').style.display = 'flex';
    recordBtn.textContent = '⏺ Recording…';
    recordBtn.disabled = true;
    launcherStatus.textContent = 'Recording is running from the floating control. Stop from the badge when you are done.';
  } catch (err) {
    if (err.name !== 'NotAllowedError') alert('Recording failed: ' + err.message);
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
  }
  clearInterval(recInterval);
  document.getElementById('recordingBadge').style.display = 'none';
  recordBtn.textContent = '⏺ Start Recording';
  recordBtn.disabled = false;
  if (captureMode === 'video') {
    launcherStatus.textContent = 'Record short clips from the launcher. Image capture is what stages the editor window in this mock.';
  }
}

function saveRecording() {
  const mimeType = getSupportedMimeType();
  const blob = new Blob(recordedChunks, { type: mimeType });
  const ext  = mimeType.includes('webm') ? 'webm' : 'mp4';
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `test-recording-${Date.now()}.${ext}`;
  a.click();
  URL.revokeObjectURL(url);
}

function getSupportedMimeType() {
  const types = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm', 'video/mp4'];
  return types.find(t => MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(t)) || 'video/webm';
}

function formatTime(s) {
  const m = Math.floor(s / 60).toString().padStart(2,'0');
  return m + ':' + (s % 60).toString().padStart(2,'0');
}

/* ─── Canvas Drawing ─── */
annoCanvas.addEventListener('mousedown', onMouseDown);
annoCanvas.addEventListener('mousemove', onMouseMove);
annoCanvas.addEventListener('mouseup',   onMouseUp);
annoCanvas.addEventListener('mouseleave',onMouseUp);

// Touch support
annoCanvas.addEventListener('touchstart', e => { e.preventDefault(); onMouseDown(touchToMouse(e)); }, { passive: false });
annoCanvas.addEventListener('touchmove',  e => { e.preventDefault(); onMouseMove(touchToMouse(e)); }, { passive: false });
annoCanvas.addEventListener('touchend',   e => { e.preventDefault(); onMouseUp(touchToMouse(e));   }, { passive: false });

function touchToMouse(e) {
  const t = e.touches[0] || e.changedTouches[0];
  return { clientX: t.clientX, clientY: t.clientY, preventDefault: () => {} };
}

function getPos(e) {
  const rect = annoCanvas.getBoundingClientRect();
  const scaleX = annoCanvas.width  / rect.width;
  const scaleY = annoCanvas.height / rect.height;
  return {
    x: (e.clientX - rect.left) * scaleX,
    y: (e.clientY - rect.top)  * scaleY
  };
}

function onMouseDown(e) {
  if (placeholder.style.display !== 'none' && !baseCanvas.width) return;
  const { x, y } = getPos(e);

  if (currentTool === 'text') {
    showTextPopup(x, y);
    return;
  }
  if (currentTool === 'select') {
    // find topmost annotation under cursor
    selectedAnnotation = findAnnotation(x, y);
    if (selectedAnnotation) {
      dragging = true;
      dragOffX = x - selectedAnnotation.x;
      dragOffY = y - selectedAnnotation.y;
    }
    return;
  }

  isDrawing = true;
  startX = x; startY = y;
  lastX  = x; lastY  = y;
  penPath = [{ x, y }];
}

function onMouseMove(e) {
  const { x, y } = getPos(e);

  if (currentTool === 'select' && dragging && selectedAnnotation) {
    selectedAnnotation.x = x - dragOffX;
    selectedAnnotation.y = y - dragOffY;
    redrawAnnotations();
    return;
  }
  if (!isDrawing) return;

  if (currentTool === 'pen') {
    penPath.push({ x, y });
    // draw live stroke
    annoCtx.save();
    annoCtx.strokeStyle = strokeColor;
    annoCtx.lineWidth   = strokeSize;
    annoCtx.lineCap     = 'round';
    annoCtx.lineJoin    = 'round';
    annoCtx.beginPath();
    annoCtx.moveTo(lastX, lastY);
    annoCtx.lineTo(x, y);
    annoCtx.stroke();
    annoCtx.restore();
    lastX = x; lastY = y;
    return;
  }

  // Preview shape
  redrawAnnotations();
  drawShape(annoCtx, currentTool, startX, startY, x, y, strokeColor, strokeSize, fillOpacity, null, true);
  lastX = x; lastY = y;
}

function onMouseUp(e) {
  if (currentTool === 'select') {
    dragging = false;
    selectedAnnotation = null;
    return;
  }
  if (!isDrawing) return;
  isDrawing = false;
  const { x, y } = getPos(e);

  if (currentTool === 'pen') {
    pushAnnotation({ type:'pen', path: penPath, color: strokeColor, size: strokeSize });
    return;
  }

  const dx = x - startX, dy = y - startY;
  if (Math.abs(dx) < 3 && Math.abs(dy) < 3) return; // ignore tiny clicks

  pushAnnotation({ type: currentTool, x: startX, y: startY, x2: x, y2: y, color: strokeColor, size: strokeSize, fillOpacity });
}

function pushAnnotation(anno) {
  undoStack.push(JSON.parse(JSON.stringify(annotations)));
  annotations.push(anno);
  redoStack = [];
  redrawAnnotations();
}

function redrawAnnotations() {
  annoCtx.clearRect(0, 0, annoCanvas.width, annoCanvas.height);
  annotations.forEach(a => {
    if (a.type === 'pen') drawPen(annoCtx, a);
    else if (a.type === 'text') drawText(annoCtx, a);
    else drawShape(annoCtx, a.type, a.x, a.y, a.x2, a.y2, a.color, a.size, a.fillOpacity, a.text);
  });
}

/* ─── Drawing primitives ─── */
function drawShape(ctx, type, x1, y1, x2, y2, color, size, opacity, text, preview) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth   = size;
  ctx.lineCap     = 'round';
  const w = x2 - x1, h = y2 - y1;

  if (preview) ctx.setLineDash([5, 3]);

  switch (type) {
    case 'highlight': {
      const [r,g,b] = hexToRgb(color);
      ctx.fillStyle = `rgba(${r},${g},${b},${opacity})`;
      ctx.fillRect(x1, y1, w, h);
      ctx.strokeRect(x1, y1, w, h);
      break;
    }
    case 'rect':
      ctx.strokeRect(x1, y1, w, h);
      break;
    case 'circle': {
      const rx = w / 2, ry = h / 2;
      ctx.beginPath();
      ctx.ellipse(x1 + rx, y1 + ry, Math.abs(rx), Math.abs(ry), 0, 0, 2 * Math.PI);
      ctx.stroke();
      break;
    }
    case 'arrow': {
      const headLen = Math.max(14, size * 3);
      const angle   = Math.atan2(y2 - y1, x2 - x1);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
      // arrowhead
      ctx.beginPath();
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - headLen * Math.cos(angle - Math.PI / 6), y2 - headLen * Math.sin(angle - Math.PI / 6));
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - headLen * Math.cos(angle + Math.PI / 6), y2 - headLen * Math.sin(angle + Math.PI / 6));
      ctx.stroke();
      break;
    }
  }
  ctx.restore();
}

function drawPen(ctx, a) {
  if (!a.path || a.path.length < 2) return;
  ctx.save();
  ctx.strokeStyle = a.color;
  ctx.lineWidth   = a.size;
  ctx.lineCap     = 'round';
  ctx.lineJoin    = 'round';
  ctx.beginPath();
  ctx.moveTo(a.path[0].x, a.path[0].y);
  a.path.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
  ctx.stroke();
  ctx.restore();
}

function drawText(ctx, a) {
  ctx.save();
  const fontSize = Math.max(14, a.size * 4);
  ctx.font      = `bold ${fontSize}px Segoe UI, sans-serif`;
  ctx.fillStyle = a.color;
  ctx.shadowColor= 'rgba(0,0,0,0.6)';
  ctx.shadowBlur = 3;
  // multi-line
  const lines = a.text.split('\n');
  lines.forEach((line, i) => ctx.fillText(line, a.x, a.y + fontSize * i));
  ctx.restore();
}

function findAnnotation(x, y) {
  for (let i = annotations.length - 1; i >= 0; i--) {
    const a = annotations[i];
    if (a.type === 'text') {
      if (x >= a.x - 10 && x <= a.x + 200 && y >= a.y - 20 && y <= a.y + 20) return a;
    } else if (a.type === 'pen') {
      for (const p of a.path) {
        if (Math.hypot(p.x - x, p.y - y) < 12) return a;
      }
    } else {
      const minX = Math.min(a.x, a.x2), maxX = Math.max(a.x, a.x2);
      const minY = Math.min(a.y, a.y2), maxY = Math.max(a.y, a.y2);
      if (x >= minX - 8 && x <= maxX + 8 && y >= minY - 8 && y <= maxY + 8) return a;
    }
  }
  return null;
}

/* ─── Text annotations ─── */
let pendingTextX = 0, pendingTextY = 0;

function showTextPopup(x, y) {
  pendingTextX = x; pendingTextY = y;
  document.getElementById('textInput').value = '';
  document.getElementById('textPopup').style.display = 'block';
  document.getElementById('textInput').focus();
}

document.getElementById('btnTextOk').addEventListener('click', () => {
  const text = document.getElementById('textInput').value.trim();
  if (text) pushAnnotation({ type:'text', x: pendingTextX, y: pendingTextY, text, color: strokeColor, size: strokeSize });
  document.getElementById('textPopup').style.display = 'none';
});
document.getElementById('btnTextCancel').addEventListener('click', () => {
  document.getElementById('textPopup').style.display = 'none';
});

/* ─── Undo / Redo ─── */
document.getElementById('btnUndo').addEventListener('click', () => {
  if (undoStack.length === 0) return;
  redoStack.push(JSON.parse(JSON.stringify(annotations)));
  annotations = undoStack.pop();
  redrawAnnotations();
});

document.getElementById('btnRedo').addEventListener('click', () => {
  if (redoStack.length === 0) return;
  undoStack.push(JSON.parse(JSON.stringify(annotations)));
  annotations = redoStack.pop();
  redrawAnnotations();
});

document.getElementById('btnClearAnno').addEventListener('click', () => {
  if (!confirm('Clear all annotations?')) return;
  clearAnnotations(true);
});

function clearAnnotations(pushUndo) {
  if (pushUndo && annotations.length) undoStack.push(JSON.parse(JSON.stringify(annotations)));
  annotations = [];
  redoStack   = [];
  annoCtx.clearRect(0, 0, annoCanvas.width, annoCanvas.height);
}

/* ─── Export ─── */
document.getElementById('btnExportPng').addEventListener('click', exportPng);
document.getElementById('btnExportJson').addEventListener('click', exportJson);

function exportPng() {
  const combined = document.createElement('canvas');
  combined.width  = baseCanvas.width;
  combined.height = baseCanvas.height;
  const ctx = combined.getContext('2d');
  ctx.drawImage(baseCanvas, 0, 0);
  ctx.drawImage(annoCanvas, 0, 0);
  const url = combined.toDataURL('image/png');
  const a   = document.createElement('a');
  a.href    = url;
  a.download= `test-assist-${Date.now()}.png`;
  a.click();

  // Save to snapshot list
  addSnapshot(url);
}

function exportJson() {
  const data = JSON.stringify({ annotations, timestamp: new Date().toISOString() }, null, 2);
  const blob = new Blob([data], { type: 'application/json' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `annotations-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

/* ─── Snapshot gallery ─── */
function addSnapshot(dataUrl) {
  const id    = Date.now().toString();
  const label = 'Snap ' + new Date().toLocaleTimeString();
  snapshots.unshift({ id, label, dataUrl });
  renderSnapshots();
}

function renderSnapshots() {
  const list = document.getElementById('snapshotList');
  list.innerHTML = snapshots.map(s => `
    <div class="snapshot-thumb" onclick="loadSnapshot('${s.id}')">
      <img src="${s.dataUrl}" alt="${escHtml(s.label)}" />
      <div class="snap-label">${escHtml(s.label)}</div>
      <button class="snap-del" onclick="event.stopPropagation();deleteSnapshot('${s.id}')">✕</button>
    </div>`).join('');
}

window.loadSnapshot = id => {
  const snap = snapshots.find(s => s.id === id);
  if (snap) loadImageSrc(snap.dataUrl);
};
window.deleteSnapshot = id => {
  snapshots = snapshots.filter(s => s.id !== id);
  renderSnapshots();
};

/* ─── Launcher / Editor window mock ─── */
function setCaptureMode(mode) {
  captureMode = mode;
  body.dataset.captureMode = mode;

  const isPhoto = mode === 'photo';
  modePhotoBtn.classList.toggle('active', isPhoto);
  modeVideoBtn.classList.toggle('active', !isPhoto);
  modePhotoBtn.setAttribute('aria-selected', String(isPhoto));
  modeVideoBtn.setAttribute('aria-selected', String(!isPhoto));
  screenshotBtn.hidden = !isPhoto;
  recordBtn.hidden = isPhoto;

  if (isPhoto) {
    launcherStatus.textContent = body.dataset.editorState === 'background'
      ? 'Another still capture will refresh the background editor window.'
      : 'Capture a still image to open the editor in the background. The launcher stays on top in this mock.';
  } else {
    launcherStatus.textContent = 'Record short clips from the launcher. Image capture is what stages the editor window in this mock.';
  }
}

function setEditorState(state) {
  body.dataset.editorState = state;

  if (state === 'idle') {
    editorStatePill.dataset.state = 'idle';
    editorStatePill.textContent = 'Editor parked';
    editorStageTitle.textContent = 'Editor is parked behind the launcher';
    editorStageText.textContent = 'Use the floating capture control to grab a screenshot. In this browser mock, the editor stays visually recessed until you choose to bring it forward.';
    editorStageAction.textContent = 'Bring Editor Forward';
    openEditorWindowBtn.disabled = true;
    return;
  }

  openEditorWindowBtn.disabled = false;

  if (state === 'background') {
    editorStatePill.dataset.state = 'background';
    editorStatePill.textContent = 'Editor opened in background';
    editorStageTitle.textContent = 'Capture loaded into the background editor';
    editorStageText.textContent = 'The screenshot is staged and ready for markup. Stay in the launcher workflow or bring the editor forward when you want to annotate.';
    editorStageAction.textContent = 'Bring Editor Forward';
    launcherStatus.textContent = 'Screenshot captured. The editor mock has opened in the background.';
    return;
  }

  editorStatePill.dataset.state = 'active';
  editorStatePill.textContent = 'Editor in front';
  launcherStatus.textContent = captureMode === 'photo'
    ? 'The editor is active. Capture again from the launcher whenever you want a new still.'
    : 'The editor is active. Switch back to Photo mode when you want to stage a new image.';
}

setCaptureMode('photo');
setEditorState('idle');

/* ─── Keyboard shortcuts ─── */
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;
  if ((e.ctrlKey || e.metaKey) && e.key === 'z') { e.preventDefault(); document.getElementById('btnUndo').click(); }
  if ((e.ctrlKey || e.metaKey) && e.key === 'y') { e.preventDefault(); document.getElementById('btnRedo').click(); }
  if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); exportPng(); }
  // Tool shortcuts
  const keys = { h:'highlight', t:'text', c:'circle', a:'arrow', r:'rect', p:'pen', s:'select' };
  if (keys[e.key]) {
    const btn = document.querySelector(`.tool-btn[data-tool="${keys[e.key]}"]`);
    if (btn) btn.click();
  }
});

/* ─── Utility ─── */
function hexToRgb(hex) {
  hex = hex.replace('#','');
  if (hex.length === 3) hex = hex.split('').map(c=>c+c).join('');
  const n = parseInt(hex, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
