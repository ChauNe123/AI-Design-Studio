let currentDoc = null;
let currentVersions = [];
let currentIntegrity = null;
let selectedLayerId = null;
let loadedImages = {};
let loadedOrigImages = {};
let localFonts = [];
let providersState = null;

let dragging = false;
let dragOffset = { x: 0, y: 0 };
let undoStack = [];
let redoStack = [];
let autosaveTimer = null;

// Interactive v1.2 canvas selection state
let editorTool = 'move'; // 'move' | 'point_pos' | 'point_neg' | 'box'
let segPoints = [];
let segLabels = [];
let segBox = null;
let boxDragStart = null;
let permModalResolve = null;

function setStatus(text, type = 'ok') {
  const el = document.getElementById('statusPill');
  el.textContent = text;
  el.className = 'status-pill ' + type;
}

function defaultAdj() {
  return { hue: 0, sat: 100, bright: 100, contrast: 100, exposure: 0, temperature: 0, shadow: 0, highlight: 0 };
}
function defaultEff() {
  return {
    feather: 0, blur: 0,
    glow: { enabled: false, color: [52, 211, 153], radius: 12, opacity: 0.7 },
    drop_shadow: { enabled: false, color: [0, 0, 0], dx: 6, dy: 8, blur: 10, opacity: 0.55 },
    color_overlay: { enabled: false, color: [16, 185, 129], opacity: 0.4 }
  };
}
function rgbToHex(c) {
  if (!Array.isArray(c) || c.length < 3) return '#ffffff';
  return '#' + [c[0], c[1], c[2]].map(v => Math.max(0, Math.min(255, Math.round(v || 0))).toString(16).padStart(2, '0')).join('');
}
function hexToRgb(hex) {
  return [parseInt(hex.slice(1, 3), 16) || 0, parseInt(hex.slice(3, 5), 16) || 0, parseInt(hex.slice(5, 7), 16) || 0];
}

function pushUndoSnapshot() {
  if (!currentDoc) return;
  undoStack.push(JSON.stringify(currentDoc.layers));
  if (undoStack.length > 30) undoStack.shift();
  redoStack = [];
  scheduleAutosave();
}

function undoEditor() {
  if (!currentDoc || !undoStack.length) return;
  redoStack.push(JSON.stringify(currentDoc.layers));
  currentDoc.layers = JSON.parse(undoStack.pop());
  if (!currentDoc.layers.some(l => l.id === selectedLayerId)) {
    selectedLayerId = currentDoc.layers.length ? currentDoc.layers[currentDoc.layers.length - 1].id : null;
  }
  renderEditor();
  scheduleAutosave();
  setStatus('Đã Undo', 'ok');
}

function redoEditor() {
  if (!currentDoc || !redoStack.length) return;
  undoStack.push(JSON.stringify(currentDoc.layers));
  currentDoc.layers = JSON.parse(redoStack.pop());
  renderEditor();
  scheduleAutosave();
  setStatus('Đã Redo', 'ok');
}

window.addEventListener('keydown', (e) => {
  if (!document.getElementById('view-editor').classList.contains('active')) return;
  if (e.target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
  if (e.ctrlKey && e.key.toLowerCase() === 'z') { e.preventDefault(); undoEditor(); }
  if (e.ctrlKey && e.key.toLowerCase() === 'y') { e.preventDefault(); redoEditor(); }
});

function scheduleAutosave() {
  if (!currentDoc) return;
  clearTimeout(autosaveTimer);
  autosaveTimer = setTimeout(async () => {
    if (!currentDoc) return;
    const res = await apiPost(`/api/project/${currentDoc.project_id}/autosave`, { layers: currentDoc.layers });
    if (res.ok) {
      const p = document.getElementById('autosavePill');
      p.style.display = 'inline-block';
      p.textContent = 'Autosaved ' + res.autosaved_at.slice(11, 19);
    }
  }, 1500);
}

function switchView(name) {
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.view === name));
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById('view-' + name).classList.add('active');
  if (name === 'dashboard') loadDashboard();
  if (name === 'assets' || name === 'generate') loadAssets();
  if (name === 'knowledge') loadKnowledge();
  if (name === 'history') loadHistory();
  if (name === 'export') renderExportView();
  if (name === 'settings') loadSettingsUI();
  if (name === 'editor') renderEditor();
}

function switchSideTab(tab) {
  document.querySelectorAll('.side-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  ['props', 'typo', 'semantic'].forEach(t => {
    document.getElementById('tab-' + t).style.display = (t === tab) ? 'block' : 'none';
  });
}

function setEditorTool(tool) {
  editorTool = tool;
  document.getElementById('toolMove').classList.toggle('active', tool === 'move');
  document.getElementById('toolPointPos').classList.toggle('active', tool === 'point_pos');
  document.getElementById('toolPointNeg').classList.toggle('active', tool === 'point_neg');
  document.getElementById('toolBox').classList.toggle('active', tool === 'box');
  const hints = {
    move: 'Click chọn hoặc kéo layer trên canvas',
    point_pos: 'Click Trái lên đối tượng cần GIỮ (+) • Click Phải = (-)',
    point_neg: 'Click lên vùng nền/vật thể lân cận cần LOẠI (-)',
    box: 'Kéo thả khung chữ nhật quanh đối tượng cần tách hoặc xóa'
  };
  document.getElementById('editorToolHint').textContent = hints[tool] || '';
  if (tool !== 'move') switchSideTab('semantic');
}

function clearInteractiveSelection() {
  segPoints = [];
  segLabels = [];
  segBox = null;
  updateSegPointStatus();
  renderEditor();
}

function updateSegPointStatus() {
  const el = document.getElementById('segPointStatus');
  if (!el) return;
  const posCnt = segLabels.filter(x => x === 1).length;
  const negCnt = segLabels.filter(x => x === 0).length;
  const boxTxt = segBox ? ` | Box: [${segBox.join(', ')}]` : '';
  el.textContent = (posCnt + negCnt === 0 && !segBox)
    ? 'Chưa chọn điểm/box. Chọn ➕ Điểm + hoặc 🔲 Kéo Box rồi thao tác trên ảnh.'
    : `Điểm: +${posCnt} / -${negCnt}${boxTxt}`;
}

document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.onclick = () => switchView(btn.dataset.view);
});

async function apiGet(url) { return (await fetch(url)).json(); }
async function apiPost(url, payload) {
  return (await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })).json();
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const rd = new FileReader();
    rd.onload = () => resolve(rd.result);
    rd.onerror = reject;
    rd.readAsDataURL(file);
  });
}

async function refreshPrivacyBadge() {
  const res = await apiGet('/api/providers');
  if (!res.ok) return;
  providersState = res.providers_state;
  const badge = document.getElementById('privacyBadge');
  const mode = providersState.mode || 'LOCAL_ONLY';
  badge.textContent = mode === 'LOCAL_ONLY' ? '🔒 LOCAL_ONLY' : '☁️ HYBRID (ASK)';
  badge.classList.toggle('hybrid', mode !== 'LOCAL_ONLY');
}

async function ensureFontsLoaded() {
  if (localFonts.length) return;
  const res = await apiGet('/api/fonts');
  if (res.ok) localFonts = res.fonts || [];
}

async function loadDashboard() {
  const [sys, proj] = await Promise.all([apiGet('/api/system'), apiGet('/api/projects'), refreshPrivacyBadge()]);
  if (sys.ok) {
    document.getElementById('sysStats').innerHTML = `
      <div class="card"><div class="stat-lbl">AI Design Studio ${sys.version || '1.2.0'}</div><div class="stat-val" style="font-size:15px;">${sys.studio_root}</div><div class="stat-lbl">Ổ D còn trống: ${sys.disk_d_free_gb} GB • Mode: ${sys.ai_mode}</div></div>
      <div class="card"><div class="stat-lbl">Local Vision AI (Offline)</div><div class="stat-val" style="font-size:18px;">${sys.cpu_cores} Cores</div><div class="stat-lbl">RMBG-1.4 · SlimSAM-77 · Tesseract vie+eng</div></div>
      <div class="card"><div class="stat-lbl">Photoshop & Dự án</div><div class="stat-val">${sys.projects_count} Dự án</div><div class="stat-lbl">Photoshop.exe: ${sys.photoshop_available ? 'Có file' : 'Chưa tìm thấy'}</div></div>
    `;
  }
  document.getElementById('dashProjects').innerHTML = (proj.projects || []).slice(0, 6).map(p => projectCardHtml(p)).join('') || '<p class="stat-lbl">Chưa có dự án nào.</p>';
}

function projectCardHtml(p) {
  return `
    <div class="card" style="margin-bottom:0;">
      ${p.composite_preview ? `<img src="${p.composite_preview}?t=${Date.now()}" style="width:100%;height:150px;object-fit:contain;background:#090b0e;border-radius:6px;margin-bottom:8px;">` : ''}
      <div style="font-weight:700;font-size:13px;">${p.title}</div>
      <div class="stat-lbl">${p.mode} • ${p.width}×${p.height} • ${p.layer_count} layers</div>
      <div class="btn-row" style="margin-top:8px;">
        <span class="qa-badge ${p.qa_passed ? 'qa-pass' : 'qa-fail'}">${p.qa_passed ? 'QA PASS' : 'CHECK QA'}</span>
        <button class="btn" style="padding:4px 10px;" onclick="openProject('${p.project_id}')">Mở Editor</button>
      </div>
    </div>
  `;
}

async function openProject(pid, goTo = 'editor') {
  setStatus('Đang tải dự án...', 'busy');
  await ensureFontsLoaded();
  const res = await apiGet('/api/project/' + pid);
  if (!res.ok) { setStatus('Lỗi tải dự án', 'err'); return; }
  currentDoc = res.document;
  currentVersions = res.versions || [];
  currentIntegrity = res.integrity || null;
  undoStack = []; redoStack = [];
  clearInteractiveSelection();
  if (res.autosave_recovery && res.autosave_recovery.has_recovery) {
    if (confirm(`Phát hiện bản Autosave lúc ${res.autosave_recovery.autosaved_at}. Khôi phục bản Autosave này?`)) {
      const rr = await apiPost(`/api/project/${pid}/restore`, { from_autosave: true });
      if (rr.ok) currentDoc = rr.document;
    }
  }
  selectedLayerId = currentDoc.layers.length ? currentDoc.layers[currentDoc.layers.length - 1].id : null;
  document.getElementById('activeProjectLabel').textContent = `${currentDoc.title} (${currentDoc.mode} • ${currentDoc.width}×${currentDoc.height})`;
  await preloadLayerImages();
  setStatus('Đã mở ' + currentDoc.project_id, 'ok');
  switchView(goTo);
}

async function preloadLayerImages() {
  loadedImages = {};
  loadedOrigImages = {};
  if (!currentDoc) return;
  const ts = Date.now();
  const jobs = [];
  for (const l of currentDoc.layers) {
    delete l._clientDirty;
    if (l.type === 'adjustment') {
      if (l.mask_file) {
        jobs.push(new Promise(res => {
          const im = new Image();
          im.onload = res; im.onerror = res;
          im.src = `/projects/${currentDoc.project_id}/${l.mask_file}?t=${ts}`;
          loadedImages[l.id] = im;
        }));
      }
      continue;
    }
    const renderRel = (l.metadata && l.metadata.export_override_file) || l.source_file;
    if (renderRel) {
      jobs.push(new Promise(res => {
        const im = new Image();
        im.onload = res; im.onerror = res;
        im.src = `/projects/${currentDoc.project_id}/${renderRel}?t=${ts}`;
        loadedImages[l.id] = im;
      }));
    }
    const origRel = l.source_file || l.original_source_file;
    if (origRel) {
      jobs.push(new Promise(res => {
        const im2 = new Image();
        im2.onload = res; im2.onerror = res;
        im2.src = `/projects/${currentDoc.project_id}/${origRel}?t=${ts}`;
        loadedOrigImages[l.id] = im2;
      }));
    }
  }
  const hasAdjLayers = currentDoc.layers.some(l => l.type === 'adjustment');
  if (hasAdjLayers) {
    const compRel = currentDoc.composite_preview || 'qa_composite.png';
    jobs.push(new Promise(res => {
      const cim = new Image();
      cim.onload = () => { currentDoc._qaCompositeImg = cim; res(); };
      cim.onerror = res;
      cim.src = `/projects/${currentDoc.project_id}/${compRel}?t=${ts}`;
    }));
  }
  await Promise.all(jobs);
}

async function submitRedesign() {
  const file = document.getElementById('rdFile').files[0];
  if (!file) return alert('Hãy chọn 1 file ảnh trước!');
  setStatus('Đang phân tích Semantic & tách layer bằng Local AI...', 'busy');
  await ensureFontsLoaded();
  const data_base64 = await fileToBase64(file);
  const res = await apiPost('/api/redesign', {
    title: document.getElementById('rdTitle').value,
    filename: file.name,
    semantic_mode: document.getElementById('rdSemantic').checked,
    use_rmbg: document.getElementById('rdRmbg').checked,
    use_ocr: document.getElementById('rdOcr').checked,
    upscale_2x: document.getElementById('rdUpscale').checked,
    data_base64
  });
  if (!res.ok) { setStatus('Lỗi: ' + res.error, 'err'); return alert(res.error); }
  currentDoc = res.document;
  currentVersions = res.versions || [];
  undoStack = []; redoStack = [];
  clearInteractiveSelection();
  selectedLayerId = currentDoc.layers.length ? currentDoc.layers[currentDoc.layers.length - 1].id : null;
  document.getElementById('activeProjectLabel').textContent = `${currentDoc.title} (${currentDoc.width}×${currentDoc.height})`;
  await preloadLayerImages();
  setStatus('Phân tích Semantic & QA hoàn tất!', 'ok');
  switchView('editor');
}

async function submitProductRetouch() {
  const file = document.getElementById('rdFile').files[0];
  if (!file) return alert('Hãy chọn 1 file ảnh sản phẩm trước!');
  setStatus('Đang chạy 4-Block Retouching, bóc tách Lid/MatSang/Luminosity & xuất PSD...', 'busy');
  await ensureFontsLoaded();
  const data_base64 = await fileToBase64(file);
  const res = await apiPost('/api/retouch', {
    title: document.getElementById('rdTitle').value,
    filename: file.name,
    data_base64
  });
  if (!res.ok) { setStatus('Lỗi Retouch: ' + res.error, 'err'); return alert(res.error); }
  currentDoc = res.document;
  currentVersions = res.versions || [];
  undoStack = []; redoStack = [];
  clearInteractiveSelection();
  selectedLayerId = currentDoc.layers.length ? currentDoc.layers[currentDoc.layers.length - 1].id : null;
  document.getElementById('activeProjectLabel').textContent = `${currentDoc.title} (${currentDoc.mode} • ${currentDoc.width}×${currentDoc.height})`;
  await preloadLayerImages();

  const qa3 = (res.qa && res.qa.qa3_psd) || {};
  const box = document.getElementById('retouchReportBox');
  if (box) {
    box.style.display = 'block';
    box.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
        <div>
          <h3 style="margin:0;">✅ Kết quả Retouch & Bóc Tách Ánh Sáng (${qa3.layer_count || currentDoc.layers.length} Layers)</h3>
          <div class="stat-lbl">${qa3.decoded_pixel_layers || 0} Pixel Layers • ${qa3.adjustment_layer_count || 0} Live Adjustment Layers • ${qa3.masked_layer_count || 0} Masks • ${qa3.clipped_layer_count || 0} Clipping</div>
        </div>
        <div class="btn-row" style="margin:0;">
          <a class="btn primary" href="${res.psd_url}" download>💾 Tải File PSD Editable</a>
          <button class="btn blue" onclick="switchView('editor')">🗂️ Mở Layer Editor</button>
        </div>
      </div>
      <div class="grid-2">
        <div>
          <div class="stat-lbl" style="margin-bottom:4px;">Before (Gốc) vs After (AI Live Retouch Stack)</div>
          <img src="${res.before_after_url}?t=${Date.now()}" style="width:100%;border-radius:8px;border:1px solid var(--border);">
        </div>
        <div>
          <div class="stat-lbl" style="margin-bottom:4px;">8-Mask Contact Sheet (Product · Luminosity · Top Lid · Mat Sang · Vignette)</div>
          <img src="${res.masks_sheet_url}?t=${Date.now()}" style="width:100%;border-radius:8px;border:1px solid var(--border);">
        </div>
      </div>
    `;
  }
  setStatus('Hoàn tất Pro Retouch & xuất PSD Live Adjustment Layers!', 'ok');
}

async function submitBannerDecompose() {
  const file = document.getElementById('rdFile').files[0];
  if (!file) return alert('Hãy chọn 1 file ảnh banner JPG/PNG trước!');
  setStatus('Đang chạy 5-Module Bóc Tách Banner Esports (LaMa BG · Podiums Amodal · SlimSAM Prizes · Dual Text LayerFX)...', 'busy');
  await ensureFontsLoaded();
  const data_base64 = await fileToBase64(file);
  const res = await apiPost('/api/banner_decompose', {
    title: document.getElementById('rdTitle').value,
    filename: file.name,
    data_base64
  });
  if (!res.ok) { setStatus('Lỗi Banner Decompose: ' + res.error, 'err'); return alert(res.error); }
  currentDoc = res.document;
  currentVersions = res.versions || [];
  undoStack = []; redoStack = [];
  clearInteractiveSelection();
  selectedLayerId = currentDoc.layers.length ? currentDoc.layers[currentDoc.layers.length - 1].id : null;
  document.getElementById('activeProjectLabel').textContent = `${currentDoc.title} (${currentDoc.mode} • ${currentDoc.width}×${currentDoc.height})`;
  await preloadLayerImages();

  const qa3 = (res.qa && res.qa.qa3_psd) || {};
  const box = document.getElementById('retouchReportBox');
  if (box) {
    box.style.display = 'block';
    box.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
        <div>
          <h3 style="margin:0;">🏆 Hoàn Tất Bóc Tách Banner 5-Module (${qa3.layer_count || currentDoc.layers.length} Layers)</h3>
          <div class="stat-lbl">${qa3.decoded_pixel_layers || 0} Pixel/Object Layers • ${qa3.text_layer_count || 0} Vector Editable TySh • ${qa3.fx_layer_count || 0} Live LayerFX (lmfx) • ${qa3.adjustment_layer_count || 0} Adjustment</div>
        </div>
        <div class="btn-row" style="margin:0;">
          <a class="btn primary" href="${res.psd_url}" download>💾 Tải File PSD Đa Layer</a>
          <button class="btn blue" onclick="switchView('editor')">🗂️ Mở Layer Editor</button>
        </div>
      </div>
      <div class="grid-2">
        <div>
          <div class="stat-lbl" style="margin-bottom:4px;">4-Step Progression Breakdown (Clean LaMa BG → Podiums/Prizes → Decor/Text → Composite)</div>
          <img src="${res.progression_url}?t=${Date.now()}" style="width:100%;border-radius:8px;border:1px solid var(--border);">
        </div>
        <div>
          <div class="stat-lbl" style="margin-bottom:4px;">Checkerboard Contact Sheet (Các Layer Đã Bóc Tách Độc Lập)</div>
          <img src="${res.layers_sheet_url}?t=${Date.now()}" style="width:100%;border-radius:8px;border:1px solid var(--border);">
        </div>
      </div>
    `;
  }
  setStatus('Hoàn tất bóc tách Banner đa layer & xuất PSD kèm LayerFX!', 'ok');
}

function readGeneratePayload() {
  const prods = Array.from(document.getElementById('genProduct').selectedOptions).map(o => o.value);
  const refs = Array.from(document.getElementById('genRef').selectedOptions).map(o => o.value);
  const bulletsRaw = document.getElementById('genBullets').value || '';
  return {
    title: document.getElementById('genTitle').value,
    industry: document.getElementById('genIndustry').value,
    layout: document.getElementById('genLayout').value,
    art_movement: document.getElementById('genArtMovement') ? document.getElementById('genArtMovement').value : 'none',
    color_harmony: document.getElementById('genColorHarmony') ? document.getElementById('genColorHarmony').value : 'none',
    canvas_preset: document.getElementById('genPreset').value,
    headline: document.getElementById('genHeadline').value,
    subheadline: document.getElementById('genSub').value,
    bullets: bulletsRaw.split(',').map(s => s.trim()).filter(Boolean),
    cta_text: document.getElementById('genCta').value,
    bg_color: document.getElementById('genBg').value,
    accent_color: document.getElementById('genAcc').value,
    text_color: document.getElementById('genTxt').value,
    product_rel_paths: prods,
    logo_rel_path: document.getElementById('genLogo').value,
    reference_rel_paths: refs,
    remove_white_bg: document.getElementById('genRemoveWhite').checked
  };
}

async function submitGenerate() {
  setStatus('Đang thiết kế & xuất PSD...', 'busy');
  await ensureFontsLoaded();
  const res = await apiPost('/api/generate', readGeneratePayload());
  if (!res.ok) { setStatus('Lỗi: ' + res.error, 'err'); return alert(res.error); }
  currentDoc = res.document;
  currentVersions = res.versions || [];
  undoStack = []; redoStack = [];
  selectedLayerId = currentDoc.layers.length ? currentDoc.layers[currentDoc.layers.length - 1].id : null;
  document.getElementById('activeProjectLabel').textContent = `${currentDoc.title} (${currentDoc.width}×${currentDoc.height})`;
  await preloadLayerImages();
  setStatus('Tạo thiết kế & QA xong!', 'ok');
  switchView('editor');
}

async function submitGenerateVariants() {
  setStatus('Đang tạo 3 phương án bố cục...', 'busy');
  const res = await apiPost('/api/generate_variants', readGeneratePayload());
  if (!res.ok) { setStatus('Lỗi: ' + res.error, 'err'); return alert(res.error); }
  const box = document.getElementById('genVariantsBox');
  box.style.display = 'block';
  document.getElementById('genVariantsGrid').innerHTML = (res.variants || []).map(v => `
    <div class="card" style="margin-bottom:0;">
      <img src="${v.composite_preview}?t=${Date.now()}" style="width:100%;height:190px;object-fit:contain;background:#090b0e;border-radius:6px;margin-bottom:8px;">
      <div style="font-weight:700;font-size:13px;">${v.variant_label}</div>
      <div class="btn-row">
        <span class="qa-badge ${v.qa_passed ? 'qa-pass' : 'qa-fail'}">${v.qa_passed ? 'QA PASS' : 'FAIL'}</span>
        <button class="btn primary" style="padding:4px 10px;" onclick="openProject('${v.project_id}')">Chọn & Chỉnh PSD</button>
      </div>
    </div>
  `).join('');
  setStatus('Đã tạo xong 3 phương án!', 'ok');
}

function applyIndustryDefaults() {
  const v = document.getElementById('genIndustry').value;
  if (v === 'tech_automotive') {
    document.getElementById('genBg').value = '#071B14';
    document.getElementById('genAcc').value = '#10B981';
    document.getElementById('genTxt').value = '#FFFFFF';
  } else if (v === 'commercial_product') {
    document.getElementById('genBg').value = '#F8FAFC';
    document.getElementById('genAcc').value = '#2563EB';
    document.getElementById('genTxt').value = '#0F172A';
  } else {
    document.getElementById('genBg').value = '#0F172A';
    document.getElementById('genAcc').value = '#F59E0B';
    document.getElementById('genTxt').value = '#FFFFFF';
  }
}

/* Editor Render & Non-Destructive Preview */
function renderEditor() {
  const cvs = document.getElementById('editorCanvas');
  const ctx = cvs.getContext('2d');
  if (!currentDoc) { ctx.clearRect(0, 0, cvs.width, cvs.height); return; }
  cvs.width = currentDoc.width;
  cvs.height = currentDoc.height;
  ctx.clearRect(0, 0, cvs.width, cvs.height);

  const sorted = [...currentDoc.layers].sort((a, b) => a.z_index - b.z_index);
  const hasLiveAdj = sorted.some(l => l.type === 'adjustment');
  if (hasLiveAdj && currentDoc._qaCompositeImg && currentDoc._qaCompositeImg.complete) {
    ctx.drawImage(currentDoc._qaCompositeImg, 0, 0, cvs.width, cvs.height);
  }
  for (const l of sorted) {
    if (!l.visible) continue;
    if (l.type === 'adjustment') {
      if (l.id === selectedLayerId) {
        ctx.save();
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = Math.max(2, currentDoc.width / 420);
        ctx.setLineDash([8, 5]);
        ctx.strokeRect(4, 4, cvs.width - 8, cvs.height - 8);
        ctx.restore();
      }
      continue;
    }
    if (hasLiveAdj && currentDoc._qaCompositeImg && currentDoc._qaCompositeImg.complete && !l._clientDirty) {
      if (l.id === selectedLayerId) {
        const sc0 = (l.metadata && l.metadata.scale) || 1;
        ctx.save();
        ctx.strokeStyle = l.locked ? '#f59e0b' : '#10b981';
        ctx.lineWidth = Math.max(2, currentDoc.width / 420);
        ctx.setLineDash([8, 5]);
        ctx.strokeRect(l.x, l.y, l.width * sc0, l.height * sc0);
        ctx.restore();
      }
      continue;
    }
    const meta = l.metadata || {};
    const adj = { ...defaultAdj(), ...(l.adjustments || {}) };
    const eff = { ...defaultEff(), ...(l.effects || {}) };
    const sc = meta.scale || 1;
    const tr = l.text_reconstruction || {};
    const showRaster = !!tr.show_original_raster;
    const usePreRendered = !l._clientDirty && meta.export_override_file && loadedImages[l.id] && loadedImages[l.id].complete;
    const im = usePreRendered ? loadedImages[l.id] : (loadedOrigImages[l.id] || loadedImages[l.id]);
    const expOff = (usePreRendered && Array.isArray(meta.export_offset)) ? meta.export_offset : [0, 0];

    const dw = (usePreRendered && im && im.naturalWidth) ? im.naturalWidth : l.width * sc;
    const dh = (usePreRendered && im && im.naturalHeight) ? im.naturalHeight : l.height * sc;
    const drawX = l.x - (expOff[0] || 0);
    const drawY = l.y - (expOff[1] || 0);

    ctx.save();
    ctx.globalAlpha = l.opacity ?? 1;
    const bmMap = { normal: 'source-over', multiply: 'multiply', screen: 'screen', overlay: 'overlay', darken: 'darken', lighten: 'lighten' };
    ctx.globalCompositeOperation = bmMap[l.blend_mode || 'normal'] || 'source-over';

    if (l.rotation && !usePreRendered) {
      const cx = l.x + (l.width * sc) / 2;
      const cy = l.y + (l.height * sc) / 2;
      ctx.translate(cx, cy);
      ctx.rotate((l.rotation * Math.PI) / 180);
      ctx.translate(-cx, -cy);
    }

    if (!usePreRendered) {
      const bPct = (adj.bright ?? 100) * Math.pow(2, adj.exposure || 0);
      const blurPx = (eff.blur || 0) + (eff.feather || 0) * 0.4;
      ctx.filter = `hue-rotate(${adj.hue || 0}deg) saturate(${adj.sat ?? 100}%) brightness(${bPct.toFixed(0)}%) contrast(${adj.contrast ?? 100}%) blur(${blurPx}px)`;
      if (eff.drop_shadow && eff.drop_shadow.enabled) {
        const dc = eff.drop_shadow.color || [0, 0, 0];
        ctx.shadowColor = `rgba(${dc[0]},${dc[1]},${dc[2]},${eff.drop_shadow.opacity ?? 0.6})`;
        ctx.shadowBlur = eff.drop_shadow.blur ?? 10;
        ctx.shadowOffsetX = eff.drop_shadow.dx ?? 6;
        ctx.shadowOffsetY = eff.drop_shadow.dy ?? 8;
      } else if (eff.glow && eff.glow.enabled) {
        const gc = eff.glow.color || [52, 211, 153];
        ctx.shadowColor = `rgba(${gc[0]},${gc[1]},${gc[2]},${eff.glow.opacity ?? 0.7})`;
        ctx.shadowBlur = (eff.glow.radius ?? 12) * 1.5;
      }
    }

    if (l.type === 'text' && l.text_data && !showRaster && (meta.text_dirty || !im || !im.complete)) {
      const td = l.text_data;
      const fSize = (td.font_size || 42) * sc;
      ctx.font = `700 ${fSize}px "${td.font || 'Segoe UI'}", Arial, sans-serif`;
      const c = td.color || [255, 255, 255];
      ctx.textBaseline = 'top';
      if (td.stroke_enabled) {
        ctx.lineWidth = (td.stroke_width || 3) * 2;
        ctx.strokeStyle = rgbToHex(td.stroke_color || [0, 0, 0]);
        ctx.strokeText(td.text, l.x + 8, l.y + 8);
      }
      ctx.fillStyle = `rgb(${c[0]},${c[1]},${c[2]})`;
      ctx.fillText(td.text, l.x + 8, l.y + 8);
    } else if (im && im.complete && im.naturalWidth > 0) {
      if (!usePreRendered && Array.isArray(l.crop) && l.crop.length === 4) {
        const [cx0, cy0, cw, ch] = l.crop;
        ctx.drawImage(im, cx0, cy0, cw, ch, l.x, l.y, cw * sc, ch * sc);
      } else {
        ctx.drawImage(im, drawX, drawY, dw, dh);
      }
    }

    if (l.id === selectedLayerId) {
      ctx.filter = 'none';
      ctx.shadowBlur = 0; ctx.shadowOffsetX = 0; ctx.shadowOffsetY = 0;
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = l.locked ? '#f59e0b' : '#10b981';
      ctx.lineWidth = Math.max(2, currentDoc.width / 420);
      ctx.setLineDash([8, 5]);
      ctx.strokeRect(l.x, l.y, l.width * sc, l.height * sc);
    }
    ctx.restore();
  }

  // Interactive SlimSAM points & Box overlay
  if (segBox) {
    ctx.save();
    ctx.strokeStyle = '#fbbf24';
    ctx.lineWidth = Math.max(3, currentDoc.width / 350);
    ctx.setLineDash([10, 6]);
    ctx.strokeRect(segBox[0], segBox[1], segBox[2], segBox[3]);
    ctx.fillStyle = 'rgba(251,191,36,0.12)';
    ctx.fillRect(segBox[0], segBox[1], segBox[2], segBox[3]);
    ctx.restore();
  }
  const rad = Math.max(7, currentDoc.width / 140);
  segPoints.forEach((pt, idx) => {
    const lbl = segLabels[idx];
    ctx.save();
    ctx.beginPath();
    ctx.arc(pt[0], pt[1], rad, 0, Math.PI * 2);
    ctx.fillStyle = lbl === 1 ? '#10b981' : '#ef4444';
    ctx.fill();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = '#ffffff';
    ctx.stroke();
    ctx.restore();
  });

  renderEditorLayerList();
  renderSemanticPanel();
  syncEditorProps();
}

function getAllGroups() {
  if (!currentDoc) return ['Main'];
  const s = new Set((currentDoc.brand && currentDoc.brand.custom_groups) || []);
  currentDoc.layers.forEach(l => s.add(l.group || 'Main'));
  return Array.from(s);
}

function renderEditorLayerList() {
  const box = document.getElementById('edLayerList');
  if (!currentDoc) { box.innerHTML = ''; return; }
  const sorted = [...currentDoc.layers].sort((a, b) => a.z_index - b.z_index);
  box.innerHTML = '';
  for (const l of sorted) {
    const row = document.createElement('div');
    row.className = 'lyr-row' + (l.id === selectedLayerId ? ' active' : '');
    row.onclick = () => {
      selectedLayerId = l.id;
      if (l.type === 'text') switchSideTab('typo');
      renderEditor();
    };

    const eye = document.createElement('button');
    eye.className = 'btn';
    eye.style.padding = '2px 5px';
    eye.textContent = l.visible ? '👁' : '—';
    eye.onclick = (e) => { e.stopPropagation(); pushUndoSnapshot(); l.visible = !l.visible; renderEditor(); };

    const thumb = document.createElement('img');
    if (loadedImages[l.id]) thumb.src = loadedImages[l.id].src;

    const nm = document.createElement('span');
    nm.className = 'lyr-name';
    const clipBadge = l.clipping ? '↳[CLIP] ' : '';
    const maskBadge = l.mask_file ? ' [MASK]' : '';
    const fxBadge = (l.psd_effects && Object.keys(l.psd_effects).length) ? ' [FX]' : '';
    nm.textContent = `${l.locked ? '🔒 ' : ''}${clipBadge}[${l.group || 'Main'}] ${l.name}${maskBadge}${fxBadge}`;

    const tag = document.createElement('span');
    const hasWarn = (l.warnings && l.warnings.length > 0) || (l.text_reconstruction && l.text_reconstruction.needs_user_confirmation && !l.text_reconstruction.user_confirmed);
    tag.className = 'tag' + (l.ai_reconstructed ? ' ai' : '') + (hasWarn ? ' warn' : '');
    if (l.type === 'adjustment' && l.adjustment_data && l.adjustment_data.type) {
      tag.textContent = l.adjustment_data.type.toUpperCase();
    } else {
      tag.textContent = l.ai_reconstructed ? 'AI-fill' : (hasWarn ? '!' : l.type);
    }

    row.append(eye, thumb, nm, tag);
    box.appendChild(row);
  }
}

function renderSemanticPanel() {
  if (!currentDoc) return;
  const layerOpts = currentDoc.layers.map(l => `<option value="${l.id}">${l.name} (${l.type})</option>`).join('');
  document.getElementById('segCarveParent').innerHTML = '<option value="">-- Giữ nguyên layer khác --</option>' + layerOpts;
  document.getElementById('reconTargetSel').innerHTML = layerOpts;
  document.getElementById('reconMaskSel').innerHTML = '<option value="">Dùng Kéo Box hiện tại trên canvas</option>' + layerOpts;

  const list = document.getElementById('semanticGraphList');
  const objs = currentDoc.semantic_objects || [];
  list.innerHTML = objs.length ? objs.map(o => {
    const rels = (o.overlap_relationships || []).map(r => `${r.relation}:${r.target}`).join(', ');
    return `
    <div class="sem-card" onclick="focusSemanticObject('${o.linked_layer_id || ''}', ${JSON.stringify(o.bounding_box || [])})">
      <div style="display:flex;justify-content:space-between;">
        <strong>${o.object_name}</strong>
        <span class="tag">${o.object_category} • ${(o.confidence_score * 100).toFixed(0)}%</span>
      </div>
      <div class="stat-lbl">z=${o.z_index} • ${o.editability_status || ''}${o.parent_object_id ? ' • parent=' + o.parent_object_id : ''}${rels ? ' • ' + rels : ''}</div>
    </div>
  `;
  }).join('') : '<div class="stat-lbl">Dự án chưa có Semantic Graph (hãy chạy MODE A v1.2 hoặc Tách đối tượng).</div>';
}

function focusSemanticObject(layerId, bbox) {
  if (layerId && currentDoc.layers.some(l => l.id === layerId)) {
    selectedLayerId = layerId;
  }
  if (Array.isArray(bbox) && bbox.length === 4) {
    segBox = bbox;
    updateSegPointStatus();
  }
  renderEditor();
}

function getSelLayer() { return currentDoc ? currentDoc.layers.find(l => l.id === selectedLayerId) : null; }

function syncEditorProps() {
  const l = getSelLayer();
  const gSel = document.getElementById('edGroupSel');
  gSel.innerHTML = getAllGroups().map(g => `<option value="${g}">${g}</option>`).join('');
  const fSel = document.getElementById('edFontSel');
  if (fSel && !fSel.options.length && localFonts.length) {
    fSel.innerHTML = localFonts.map(f => `<option value="${f.name}">${f.name} (${f.source})</option>`).join('');
  }
  if (!l) return;
  const m = l.metadata || {};
  const adj = { ...defaultAdj(), ...(l.adjustments || {}) };
  const eff = { ...defaultEff(), ...(l.effects || {}) };
  document.getElementById('edSelTitle').textContent = l.name;
  document.getElementById('edLockBtn').textContent = l.locked ? '🔒' : '🔓';
  const warnBox = document.getElementById('edLayerWarn');
  if (l.warnings && l.warnings.length) {
    warnBox.style.display = 'block';
    warnBox.textContent = '⚠ ' + l.warnings.join(' | ');
  } else {
    warnBox.style.display = 'none';
  }

  gSel.value = l.group || 'Main';
  document.getElementById('edBlend').value = l.blend_mode || 'normal';
  document.getElementById('edOp').value = Math.round((l.opacity ?? 1) * 100);
  document.getElementById('valOp').textContent = Math.round((l.opacity ?? 1) * 100) + '%';
  document.getElementById('edScale').value = Math.round((m.scale ?? 1) * 100);
  document.getElementById('valScale').textContent = Math.round((m.scale ?? 1) * 100) + '%';
  document.getElementById('edRot').value = Math.round(l.rotation || 0);
  document.getElementById('valRot').textContent = Math.round(l.rotation || 0) + '°';

  document.getElementById('edHue').value = adj.hue; document.getElementById('valHue').textContent = adj.hue;
  document.getElementById('edSat').value = adj.sat; document.getElementById('valSat').textContent = adj.sat;
  document.getElementById('edBright').value = adj.bright; document.getElementById('valBright').textContent = adj.bright;
  document.getElementById('edContrast').value = adj.contrast; document.getElementById('valContrast').textContent = adj.contrast;
  document.getElementById('edExp').value = Math.round((adj.exposure || 0) * 100); document.getElementById('valExp').textContent = Number(adj.exposure || 0).toFixed(2);
  document.getElementById('edTemp').value = adj.temperature; document.getElementById('valTemp').textContent = adj.temperature;
  document.getElementById('edShadowAdj').value = adj.shadow; document.getElementById('valShadowAdj').textContent = adj.shadow;
  document.getElementById('edHighAdj').value = adj.highlight; document.getElementById('valHighAdj').textContent = adj.highlight;

  document.getElementById('edFeather').value = eff.feather || 0; document.getElementById('valFeather').textContent = eff.feather || 0;
  document.getElementById('edBlur').value = eff.blur || 0; document.getElementById('valBlur').textContent = eff.blur || 0;
  document.getElementById('edDsEn').checked = !!(eff.drop_shadow && eff.drop_shadow.enabled);
  document.getElementById('edDsCol').value = rgbToHex((eff.drop_shadow || {}).color);
  document.getElementById('edDsBlur').value = (eff.drop_shadow || {}).blur ?? 10;
  document.getElementById('edDsDx').value = (eff.drop_shadow || {}).dx ?? 6;
  document.getElementById('edDsDy').value = (eff.drop_shadow || {}).dy ?? 8;
  document.getElementById('edGlEn').checked = !!(eff.glow && eff.glow.enabled);
  document.getElementById('edGlCol').value = rgbToHex((eff.glow || {}).color);
  document.getElementById('edGlRad').value = (eff.glow || {}).radius ?? 12;
  document.getElementById('edCoEn').checked = !!(eff.color_overlay && eff.color_overlay.enabled);
  document.getElementById('edCoCol').value = rgbToHex((eff.color_overlay || {}).color);
  document.getElementById('edCoOp').value = Math.round(((eff.color_overlay || {}).opacity ?? 0.4) * 100);
  document.getElementById('edCropStr').value = Array.isArray(l.crop) ? l.crop.join(',') : '';

  const tb = document.getElementById('edTextBox');
  const tnone = document.getElementById('edTypoNone');
  if (l.type === 'text' && l.text_data) {
    tb.style.display = 'block';
    tnone.style.display = 'none';
    const td = l.text_data;
    const tr = l.text_reconstruction || {};
    document.getElementById('edShowOrigRaster').checked = !!tr.show_original_raster;
    const tw = document.getElementById('edTypoWarn');
    if (tr.needs_user_confirmation && !tr.user_confirmed) {
      tw.style.display = 'block';
      tw.textContent = `⚠ Chữ OCR/Font xấp xỉ (${tr.is_exact_font_match ? 'Exact font' : 'Closest local font match'}). Kiểm tra dấu & font rồi bấm Xác nhận.`;
    } else {
      tw.style.display = 'none';
    }
    document.getElementById('edFontMatchNote').textContent = tr.is_exact_font_match ? 'Khớp font gốc' : 'Font gần nhất';
    document.getElementById('edTextVal').value = td.text || '';
    if (td.font) {
      if (!Array.from(fSel.options).some(o => o.value === td.font)) {
        fSel.add(new Option(td.font, td.font));
      }
      fSel.value = td.font;
    }
    document.getElementById('edFontSize').value = td.font_size || 42;
    document.getElementById('edTextAlign').value = td.align || 'left';
    document.getElementById('edTracking').value = td.tracking || 0;
    document.getElementById('edLeading').value = td.leading ?? 10;
    document.getElementById('edTextColor').value = rgbToHex(td.color || [255, 255, 255]);
    document.getElementById('edText3d').value = td.extrude_3d_depth || 0;
    document.getElementById('edStrokeEn').checked = !!td.stroke_enabled;
    document.getElementById('edStrokeCol').value = rgbToHex(td.stroke_color || [0, 0, 0]);
    document.getElementById('edStrokeW').value = td.stroke_width || 4;
    document.getElementById('edTxtShEn').checked = !!td.shadow_enabled;
    document.getElementById('edTxtShCol').value = rgbToHex(td.shadow_color || [0, 0, 0]);
    document.getElementById('edTxtShBlur').value = td.shadow_blur || 6;
    document.getElementById('edTxtGrEn').checked = !!td.gradient_enabled;
    document.getElementById('edTxtGrC2').value = rgbToHex(td.gradient_c2 || [187, 247, 208]);
    document.getElementById('edTxtRot').value = td.rotation || 0;
  } else {
    tb.style.display = 'none';
    tnone.style.display = 'block';
  }
}

function guardLocked(l) {
  if (l && l.locked) {
    setStatus(`Layer "${l.name}" đang bị khóa 🔒 — hãy bấm 🔓 trước khi sửa`, 'busy');
    return true;
  }
  return false;
}
function onPropChange(k, v) {
  const l = getSelLayer(); if (!l || guardLocked(l)) return;
  pushUndoSnapshot(); l[k] = v; l._clientDirty = true; renderEditor();
}
function onMetaChange(k, v) {
  const l = getSelLayer(); if (!l || guardLocked(l)) return;
  pushUndoSnapshot(); l.metadata = l.metadata || {}; l.metadata[k] = v; l._clientDirty = true; renderEditor();
}
function onAdjChange(k, v) {
  const l = getSelLayer(); if (!l || guardLocked(l)) return;
  pushUndoSnapshot();
  l.adjustments = { ...defaultAdj(), ...(l.adjustments || {}), [k]: v };
  l._clientDirty = true;
  renderEditor();
}
function onEffectChange(k, v) {
  const l = getSelLayer(); if (!l || guardLocked(l)) return;
  pushUndoSnapshot();
  l.effects = { ...defaultEff(), ...(l.effects || {}), [k]: v };
  l._clientDirty = true;
  renderEditor();
}
function onNestedEffectChange(grp, k, v) {
  const l = getSelLayer(); if (!l || guardLocked(l)) return;
  pushUndoSnapshot();
  l.effects = { ...defaultEff(), ...(l.effects || {}) };
  l.effects[grp] = { ...(l.effects[grp] || {}), [k]: v };
  l._clientDirty = true;
  renderEditor();
}
function onNestedEffectColor(grp, k, hex) { onNestedEffectChange(grp, k, hexToRgb(hex)); }
function onCropTextChange(val) {
  const l = getSelLayer(); if (!l || guardLocked(l)) return;
  pushUndoSnapshot();
  if (!val.trim()) { l.crop = null; }
  else {
    const pts = val.split(',').map(x => parseInt(x.trim(), 10)).filter(n => !isNaN(n));
    if (pts.length === 4 && pts[2] > 4 && pts[3] > 4) l.crop = pts;
  }
  l._clientDirty = true;
  renderEditor();
}
function onTextChange(k, v) {
  const l = getSelLayer(); if (!l || !l.text_data || guardLocked(l)) return;
  pushUndoSnapshot();
  l.text_data[k] = v;
  l.metadata = l.metadata || {};
  l.metadata.text_dirty = true;
  l.text_reconstruction = l.text_reconstruction || {};
  l.text_reconstruction.show_original_raster = false;
  l._clientDirty = true;
  renderEditor();
}
function onTextColorChange(field, hex) { onTextChange(field, hexToRgb(hex)); }
function toggleShowOriginalRaster(flag) {
  const l = getSelLayer(); if (!l) return;
  pushUndoSnapshot();
  l.text_reconstruction = l.text_reconstruction || {};
  l.text_reconstruction.show_original_raster = !!flag;
  renderEditor();
}
function confirmTypographyUI() {
  const l = getSelLayer(); if (!l) return;
  pushUndoSnapshot();
  l.text_reconstruction = l.text_reconstruction || {};
  l.text_reconstruction.user_confirmed = true;
  l.text_reconstruction.needs_user_confirmation = false;
  renderEditor();
  setStatus('Đã xác nhận Typography!', 'ok');
}

async function layerActionUI(action, extra = {}) {
  const l = getSelLayer();
  if (!currentDoc || !l) return;
  setStatus(`Đang thực thi ${action}...`, 'busy');
  const res = await apiPost(`/api/project/${currentDoc.project_id}/layer_action`, { action, layer_id: l.id, ...extra });
  if (!res.ok) { setStatus(res.error || 'Lỗi thao tác', 'err'); return; }
  currentDoc = res.document;
  currentVersions = res.versions || [];
  await preloadLayerImages();
  setStatus(`Đã ${action} layer`, 'ok');
  renderEditor();
}
function toggleLockUI() {
  const l = getSelLayer(); if (!l) return;
  layerActionUI(l.locked ? 'unlock' : 'lock');
}
function renameLayerUI() {
  const l = getSelLayer(); if (!l) return;
  const nm = prompt('Tên layer mới:', l.name);
  if (nm && nm.trim()) layerActionUI('rename', { new_name: nm.trim() });
}
async function replaceLayerAssetUI(inp) {
  const file = inp.files[0]; if (!file) return;
  const data_base64 = await fileToBase64(file);
  await layerActionUI('replace_asset', { data_base64 });
  inp.value = '';
}

async function createGroupPrompt() {
  if (!currentDoc) return;
  const nm = prompt('Nhập tên Group mới:');
  if (!nm) return;
  const res = await apiPost(`/api/project/${currentDoc.project_id}/group`, { action: 'create', group_name: nm });
  if (res.ok) { currentDoc = res.document; currentVersions = res.versions || []; renderEditor(); }
}

async function deleteGroupPrompt() {
  if (!currentDoc) return;
  const g = document.getElementById('edGroupSel').value;
  if (!confirm(`Xóa group "${g}"? Các layer bên trong sẽ chuyển về Main.`)) return;
  const res = await apiPost(`/api/project/${currentDoc.project_id}/group`, { action: 'delete', group_name: g });
  if (res.ok) { currentDoc = res.document; currentVersions = res.versions || []; renderEditor(); }
}

function assignSelectedGroup(gName) {
  const l = getSelLayer(); if (!l || !currentDoc || guardLocked(l)) return;
  pushUndoSnapshot(); l.group = gName; renderEditor();
}

function addNewTextLayer() {
  if (!currentDoc) return;
  pushUndoSnapshot();
  const id = 'lyr_txt_' + Date.now().toString(36);
  const maxZ = currentDoc.layers.reduce((m, l) => Math.max(m, l.z_index), 0);
  currentDoc.layers.push({
    id, name: 'Text_Moi', type: 'text', source_file: null,
    x: 80, y: 80, width: 320, height: 60, z_index: maxZ + 1,
    opacity: 1, visible: true, locked: false, rotation: 0, blend_mode: 'normal', group: '3_Logos_&_Typography',
    adjustments: defaultAdj(), effects: defaultEff(),
    text_data: { text: 'CHỮ MỚI', font: (localFonts[0] && localFonts[0].name) || 'Arial', font_size: 52, color: [255, 255, 255], align: 'left', tracking: 0, leading: 10 },
    metadata: { text_dirty: true }
  });
  selectedLayerId = id;
  switchSideTab('typo');
  renderEditor();
}

function deleteSelectedLayer() {
  const l = getSelLayer();
  if (!currentDoc || !l || guardLocked(l)) return;
  pushUndoSnapshot();
  currentDoc.layers = currentDoc.layers.filter(x => x.id !== l.id);
  selectedLayerId = currentDoc.layers.length ? currentDoc.layers[currentDoc.layers.length - 1].id : null;
  renderEditor();
}

function shiftLayerZ(dir) {
  const l = getSelLayer(); if (!l || !currentDoc) return;
  pushUndoSnapshot();
  const sorted = [...currentDoc.layers].sort((a, b) => a.z_index - b.z_index);
  const idx = sorted.findIndex(x => x.id === l.id);
  const tgt = idx + dir;
  if (tgt < 0 || tgt >= sorted.length) return;
  const tmp = sorted[idx].z_index;
  sorted[idx].z_index = sorted[tgt].z_index;
  sorted[tgt].z_index = tmp;
  renderEditor();
}

/* Interactive Canvas Mouse Handlers */
const edCvs = document.getElementById('editorCanvas');
edCvs.addEventListener('contextmenu', (e) => {
  if (editorTool === 'point_pos' || editorTool === 'point_neg') {
    e.preventDefault();
    const r = edCvs.getBoundingClientRect();
    const mx = Math.round((e.clientX - r.left) * (edCvs.width / r.width));
    const my = Math.round((e.clientY - r.top) * (edCvs.height / r.height));
    segPoints.push([mx, my]);
    segLabels.push(0);
    updateSegPointStatus();
    renderEditor();
  }
});
edCvs.addEventListener('mousedown', (e) => {
  if (!currentDoc) return;
  const r = edCvs.getBoundingClientRect();
  const mx = Math.round((e.clientX - r.left) * (edCvs.width / r.width));
  const my = Math.round((e.clientY - r.top) * (edCvs.height / r.height));

  if (editorTool === 'point_pos' || editorTool === 'point_neg') {
    if (e.button === 0) {
      segPoints.push([mx, my]);
      segLabels.push(editorTool === 'point_pos' ? 1 : 0);
      updateSegPointStatus();
      renderEditor();
    }
    return;
  }
  if (editorTool === 'box') {
    boxDragStart = [mx, my];
    segBox = [mx, my, 1, 1];
    return;
  }

  const sorted = [...currentDoc.layers].sort((a, b) => b.z_index - a.z_index);
  for (const l of sorted) {
    if (!l.visible) continue;
    const sc = (l.metadata && l.metadata.scale) || 1;
    if (mx >= l.x && mx <= l.x + l.width * sc && my >= l.y && my <= l.y + l.height * sc) {
      selectedLayerId = l.id;
      if (!l.locked) {
        pushUndoSnapshot();
        dragging = true;
        dragOffset = { x: mx - l.x, y: my - l.y };
      }
      renderEditor();
      return;
    }
  }
});
window.addEventListener('mousemove', (e) => {
  if (!currentDoc) return;
  const r = edCvs.getBoundingClientRect();
  const mx = Math.round((e.clientX - r.left) * (edCvs.width / r.width));
  const my = Math.round((e.clientY - r.top) * (edCvs.height / r.height));
  if (editorTool === 'box' && boxDragStart) {
    const x0 = Math.min(boxDragStart[0], mx), y0 = Math.min(boxDragStart[1], my);
    segBox = [x0, y0, Math.max(4, Math.abs(mx - boxDragStart[0])), Math.max(4, Math.abs(my - boxDragStart[1]))];
    updateSegPointStatus();
    renderEditor();
    return;
  }
  if (!dragging) return;
  const l = getSelLayer();
  if (!l || l.locked) return;
  l.x = Math.round(mx - dragOffset.x);
  l.y = Math.round(my - dragOffset.y);
  renderEditor();
});
window.addEventListener('mouseup', () => {
  dragging = false;
  boxDragStart = null;
});

/* Interactive SlimSAM Segmentation & AI Reconstruction */
async function runInteractiveSegmentUI() {
  if (!currentDoc) return;
  if (!segPoints.length && !segBox) {
    return alert('Hãy chọn ít nhất 1 điểm (+ / -) hoặc kéo Box quanh đối tượng trên canvas trước!');
  }
  setStatus('Đang chạy SlimSAM / Refine Mask tách đối tượng...', 'busy');
  const res = await apiPost(`/api/project/${currentDoc.project_id}/segment`, {
    points: segPoints.length ? segPoints : undefined,
    labels: segLabels.length ? segLabels : undefined,
    box: segBox || undefined,
    mask_level: Number(document.getElementById('segLevel').value),
    use_sam: true,
    layer_name: document.getElementById('segLayerName').value.trim() || undefined,
    carve_from_layer_id: document.getElementById('segCarveParent').value || undefined,
    feather_px: Number(document.getElementById('segFeather').value || 1),
    expand_px: Number(document.getElementById('segExpand').value || 0),
  });
  if (!res.ok) { setStatus('Lỗi tách vật thể: ' + res.error, 'err'); return alert(res.error); }
  currentDoc = res.document;
  currentVersions = res.versions || [];
  selectedLayerId = res.layer.id;
  clearInteractiveSelection();
  setEditorTool('move');
  await preloadLayerImages();
  setStatus(`Đã tách ${res.layer.name} (${res.seg_result.engine})`, 'ok');
  renderEditor();
}

function askCloudPermissionModal(preview) {
  return new Promise((resolve) => {
    permModalResolve = resolve;
    document.getElementById('permModalBody').innerHTML = `
      <div><strong>Nhà cung cấp:</strong> ${preview.provider_name} (<code>${preview.model_name}</code>)</div>
      <div><strong>Tác vụ:</strong> ${preview.task || preview.task_name}</div>
      <div><strong>Dữ liệu sẽ gửi:</strong> ${preview.image_payload_summary}</div>
      <div><strong>Vùng / Tọa độ:</strong> ${preview.region_box ? JSON.stringify(preview.region_box) : 'Toàn vùng chọn'}</div>
      <div><strong>Chi phí ước tính:</strong> $${preview.estimated_cost_usd} USD (Đã dùng: $${preview.current_spent_usd} / $${preview.monthly_budget_usd})</div>
      <div><strong>Ngân sách:</strong> ${preview.budget_exceeded ? '❌ VƯỢT NGÂN SÁCH' : '✅ Trong giới hạn'}</div>
      <div style="margin-top:8px;color:#fcd34d;">Bạn có đồng ý gửi vùng ảnh này ra ngoài API thay vì xử lý Offline không?</div>
    `;
    document.getElementById('permModal').classList.add('open');
  });
}
function closePermModal(accepted) {
  document.getElementById('permModal').classList.remove('open');
  if (permModalResolve) { permModalResolve(accepted); permModalResolve = null; }
}

async function initiateReconstructUI() {
  if (!currentDoc) return;
  const targetId = document.getElementById('reconTargetSel').value;
  const maskLayerId = document.getElementById('reconMaskSel').value;
  if (!maskLayerId && !segBox) {
    return alert('Hãy chọn 1 Layer làm vùng xóa HOẶC dùng công cụ 🔲 Kéo Box trên canvas!');
  }
  const modeVal = document.getElementById('reconMode').value;
  let providerId = 'local_engine';
  let userConfirmed = false;
  let mode = 'algorithmic_inpaint';

  if (modeVal === 'cloud_ai') {
    await refreshPrivacyBadge();
    if ((providersState && providersState.mode) === 'LOCAL_ONLY') {
      return alert('Hệ thống đang ở chế độ LOCAL_ONLY. Vào Settings -> Chính sách AI để bật HYBRID nếu muốn dùng Cloud AI.');
    }
    const enabledCloud = Object.values((providersState && providersState.providers) || {}).find(p => p.provider_id !== 'local_engine' && p.enabled);
    if (!enabledCloud) {
      return alert('Chưa có Cloud AI Provider nào được bật trong Settings!');
    }
    providerId = enabledCloud.provider_id;
    const prevRes = await apiPost('/api/providers/preview_permission', {
      provider_id: providerId,
      task: 'region_reconstruction',
      image_desc: `Vùng sửa trên project ${currentDoc.title}`,
      region_box: segBox || null
    });
    const ok = await askCloudPermissionModal(prevRes.preview);
    if (!ok) { setStatus('Đã hủy gửi Cloud AI — giữ dữ liệu Local', 'ok'); return; }
    userConfirmed = true;
    mode = 'cloud_ai';
  }

  setStatus('Đang xóa vật thể & tái tạo nền...', 'busy');
  const res = await apiPost(`/api/project/${currentDoc.project_id}/reconstruct`, {
    target_layer_id: targetId,
    mask_layer_id: maskLayerId || undefined,
    box: (!maskLayerId && segBox) ? segBox : undefined,
    mode,
    provider_id: providerId,
    user_confirmed: userConfirmed,
    prompt: document.getElementById('reconPrompt').value.trim(),
  });
  if (!res.ok) { setStatus('Lỗi tái tạo: ' + res.error, 'err'); return alert(res.error); }
  currentDoc = res.document;
  clearInteractiveSelection();
  await preloadLayerImages();
  setStatus(`Tái tạo xong (${res.reconstruct.pixel_origin})`, 'ok');
  renderEditor();
}

async function saveEditorAndExport() {
  if (!currentDoc) return;
  setStatus('Đang render non-destructive, chạy QA & xuất PSD...', 'busy');
  const res = await apiPost(`/api/project/${currentDoc.project_id}/save`, { layers: currentDoc.layers });
  if (!res.ok) { setStatus('Lỗi lưu dự án', 'err'); return alert(res.error); }
  currentDoc = res.document;
  currentVersions = res.versions || [];
  currentIntegrity = res.integrity || null;
  document.getElementById('autosavePill').style.display = 'none';
  await preloadLayerImages();
  setStatus('Đã lưu Version & xuất PSD v1.2 đạt chuẩn!', 'ok');
  switchView('export');
}

async function restoreProjectVersion(vid) {
  if (!currentDoc) return;
  setStatus('Đang khôi phục phiên bản ' + vid + '...', 'busy');
  const res = await apiPost(`/api/project/${currentDoc.project_id}/restore`, { version_id: vid });
  if (res.ok) {
    currentDoc = res.document;
    currentVersions = res.versions || [];
    await preloadLayerImages();
    setStatus('Đã khôi phục ' + vid, 'ok');
    renderExportView();
  }
}

/* Assets, Knowledge, History, Export, Settings & Providers */
async function loadAssets() {
  const res = await apiGet('/api/assets');
  if (!res.ok) return;
  const a = res.assets;
  const pSel = document.getElementById('genProduct');
  const lSel = document.getElementById('genLogo');
  const rSel = document.getElementById('genRef');
  if (pSel) pSel.innerHTML = a.products.concat(a.logos).map(x => `<option value="${x.rel_path}">${x.name}</option>`).join('');
  if (lSel) lSel.innerHTML = '<option value="">-- Không dùng logo --</option>' + a.logos.concat(a.products).map(x => `<option value="${x.rel_path}">${x.name}</option>`).join('');
  if (rSel) rSel.innerHTML = a.references.map(x => `<option value="${x.rel_path}">${x.name}</option>`).join('');

  const cont = document.getElementById('assetContainer');
  cont.innerHTML = ['products', 'logos', 'references', 'fonts'].map(cat => `
    <div class="card">
      <h3>${cat.toUpperCase()} (${(a[cat] || []).length})</h3>
      <div class="asset-grid">
        ${(a[cat] || []).map(item => `
          <div class="asset-card">
            ${cat === 'fonts' ? '<div style="height:100px;display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:700;">Aa</div>' : `<img src="/${item.rel_path}">`}
            <div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${item.name}</div>
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');
}

async function uploadAsset() {
  const file = document.getElementById('assetFile').files[0];
  if (!file) return alert('Chọn ảnh trước!');
  const data_base64 = await fileToBase64(file);
  const res = await apiPost('/api/assets/upload', {
    category: document.getElementById('assetCat').value,
    filename: file.name,
    data_base64
  });
  if (res.ok) { loadAssets(); setStatus('Đã thêm asset ' + file.name, 'ok'); }
}

async function analyzeReferenceUI() {
  const file = document.getElementById('refAnalyzeFile').files[0];
  if (!file) return alert('Hãy chọn 1 ảnh thiết kế tham khảo!');
  setStatus('Đang phân tích ảnh tham khảo...', 'busy');
  const data_base64 = await fileToBase64(file);
  const res = await apiPost('/api/knowledge/analyze_reference', { filename: file.name, data_base64 });
  if (res.ok) {
    const a = res.analysis;
    document.getElementById('refAnalyzeResult').innerHTML = `
      <div style="background:var(--panel2);padding:10px;border-radius:6px;font-size:12px;">
        <strong>${a.name}</strong> (${a.source_size}) • Đề xuất: <strong>${a.visual_hierarchy.suggested_layout}</strong> • Mood: <strong>${a.visual_hierarchy.mood}</strong> • Whitespace: <strong>${a.visual_hierarchy.whitespace_pct}%</strong>
        <ul style="margin:6px 0 0 18px;">${a.design_principles_extracted.map(p => `<li>${p}</li>`).join('')}</ul>
      </div>
    `;
    loadKnowledge();
    setStatus('Đã phân tích & lưu nguyên tắc thiết kế!', 'ok');
  }
}

async function loadKnowledge() {
  const res = await apiGet('/api/knowledge');
  if (!res.ok) return;
  const kb = res.knowledge;
  const pr = kb.principles || {};
  const visElems = pr.visual_elements || [];
  const artMovs = pr.art_movements || [];
  const colorPsy = kb.color_psychology || {};
  const coreRules = [].concat(pr.layout || [], pr.typography || [], pr.color_theory || [], pr.lighting_and_shadow || []);

  const colorRows = Object.values(colorPsy).map(c => `
    <tr>
      <td style="padding:7px;border-bottom:1px solid var(--border);white-space:nowrap;">
        <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:${c.hex || '#888'};vertical-align:middle;margin-right:6px;border:1px solid #444;"></span>
        <strong>${c.name}</strong>
      </td>
      <td style="padding:7px;border-bottom:1px solid var(--border);color:#34d399;">${c.positive || ''}</td>
      <td style="padding:7px;border-bottom:1px solid var(--border);color:#fca5a5;">${c.negative || ''}</td>
      <td style="padding:7px;border-bottom:1px solid var(--border);color:var(--muted);">${c.best_for || ''}</td>
    </tr>
  `).join('');

  document.getElementById('kbContainer').innerHTML = `
    <div class="card">
      <h3>🎨 Yếu tố Thị giác (DVF Visual Elements — ${visElems.length})</h3>
      <div class="grid-3">
        ${visElems.map(e => `
          <div style="background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:10px;font-size:12px;">
            <strong style="color:var(--accent);">${e.name}</strong>
            <p class="stat-lbl" style="margin-top:5px;line-height:1.45;">${e.rule}</p>
          </div>
        `).join('')}
      </div>
    </div>

    <div class="card">
      <h3>🏛️ Phong trào Nghệ thuật Lịch sử (Art Movements — ${artMovs.length})</h3>
      <div class="grid-2">
        ${artMovs.map(m => `
          <div style="background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:10px;font-size:12px;">
            <strong style="color:#93c5fd;">${m.name}</strong>
            <p class="stat-lbl" style="margin-top:5px;line-height:1.45;">${m.style || m.rule || ''}</p>
          </div>
        `).join('')}
      </div>
    </div>

    <div class="card">
      <h3>🌈 Bảng Tra cứu Tâm lý học Màu sắc (${Object.keys(colorPsy).length} Màu — Tích cực vs Tiêu cực)</h3>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:12px;text-align:left;">
          <thead>
            <tr style="border-bottom:1px solid var(--border);color:var(--muted);">
              <th style="padding:7px;">Màu sắc</th>
              <th style="padding:7px;">Cảm xúc Tích cực (Positive)</th>
              <th style="padding:7px;">Cảm xúc Tiêu cực (Negative)</th>
              <th style="padding:7px;">Ứng dụng (Best For)</th>
            </tr>
          </thead>
          <tbody>${colorRows || '<tr><td colspan="4" class="stat-lbl" style="padding:8px;">Chưa có dữ liệu tâm lý màu.</td></tr>'}</tbody>
        </table>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <h3>Nguyên tắc Bố cục, Typo & Phân tích Tham khảo (${(kb.references_analyzed || []).length})</h3>
        ${coreRules.map(p => `<p style="font-size:12px;margin-bottom:8px;"><strong>${p.name}:</strong> <span class="stat-lbl">${p.rule}</span></p>`).join('')}
        ${(kb.references_analyzed || []).map(r => `<p style="font-size:12px;margin-top:8px;border-top:1px solid var(--border);padding-top:6px;">📐 <strong>${r.name}:</strong> ${r.visual_hierarchy.suggested_layout}, focal=${r.visual_hierarchy.focal_zone}, bg=${r.palette.bg_hex}</p>`).join('')}
      </div>
      <div class="card">
        <h3>Bài học QA đã ghi nhận</h3>
        ${(kb.qa_lessons || []).map(l => `<p style="font-size:12px;margin-bottom:8px;"><span class="qa-badge qa-pass">${l.status}</span> <strong>${l.issue}</strong> → <span class="stat-lbl">${l.fix}</span></p>`).join('')}
      </div>
    </div>
  `;
}

async function addKbLesson() {
  const issue = document.getElementById('kbIssue').value.trim();
  const fix = document.getElementById('kbFix').value.trim();
  if (!issue || !fix) return alert('Nhập đủ vấn đề và cách khắc phục!');
  await apiPost('/api/knowledge/lesson', { status: 'LEARNED', issue, fix });
  document.getElementById('kbIssue').value = '';
  document.getElementById('kbFix').value = '';
  loadKnowledge();
}

async function loadHistory() {
  const res = await apiGet('/api/projects');
  document.getElementById('historyGrid').innerHTML = (res.projects || []).map(p => projectCardHtml(p)).join('') || '<p class="stat-lbl">Chưa có dự án nào.</p>';
}

function renderExportView() {
  const box = document.getElementById('exportContainer');
  if (!currentDoc) { box.innerHTML = 'Chưa có dự án nào được chọn.'; return; }
  const qa = currentDoc.qa_status || {};
  const q1 = qa.qa1_layers || {}, q2 = qa.qa2_composite || {}, q3 = qa.qa3_psd || {};
  const pid = currentDoc.project_id;
  box.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <div>
        <h3>${currentDoc.title} — ${qa.psd_file || ''}</h3>
        <div class="stat-lbl">Schema v${currentDoc.schema_version || '1.2.0'} • ${currentDoc.width}×${currentDoc.height} • ${currentDoc.layers.length} layers • Semantic Objects: ${(currentDoc.semantic_objects || []).length} • Integrity: ${currentIntegrity ? (currentIntegrity.ok ? 'OK' : 'MISSING') : 'Checked'}</div>
      </div>
      <div class="btn-row" style="margin:0;">
        <a class="btn primary" href="/projects/${pid}/${qa.psd_file}" download>⬇️ Tải file .PSD</a>
        <button class="btn blue" onclick="apiPost('/api/project/${pid}/open_photoshop', {})">🎨 Mở trong Photoshop 2024</button>
        <button class="btn" onclick="apiPost('/api/project/${pid}/open_folder', {})">📁 Mở thư mục</button>
      </div>
    </div>
    <div class="grid-3">
      <div class="card">
        <h4>QA 1 — Layer Inspection <span class="qa-badge ${q1.passed ? 'qa-pass' : 'qa-fail'}">${q1.passed ? 'PASS' : 'FAIL'}</span></h4>
        <p class="stat-lbl" style="margin:8px 0;">Đã kiểm tra ${q1.checked_count || 0} layers. Lỗi: ${(q1.issues || []).length}</p>
        ${q1.qa_sheet ? `<img src="/projects/${pid}/${q1.qa_sheet}?t=${Date.now()}" style="width:100%;border-radius:6px;">` : ''}
      </div>
      <div class="card">
        <h4>QA 2 — Composite Inspection <span class="qa-badge ${q2.passed ? 'qa-pass' : 'qa-fail'}">${q2.passed ? 'PASS' : 'FAIL'}</span></h4>
        <p class="stat-lbl" style="margin:8px 0;">Vùng thủng: ${q2.transparent_hole_pct ?? 0}% • MAE vs gốc: ${q2.mae_vs_source ?? 'N/A'}</p>
        ${q2.composite_file ? `<img src="/projects/${pid}/${q2.composite_file}?t=${Date.now()}" style="width:100%;border-radius:6px;">` : ''}
      </div>
      <div class="card">
        <h4>QA 3 — PSD Binary Verify <span class="qa-badge ${q3.passed ? 'qa-pass' : 'qa-fail'}">${q3.passed ? 'PASS' : 'FAIL'}</span></h4>
        <p class="stat-lbl" style="margin:8px 0;line-height:1.5;">
          Dung lượng: ${((q3.psd_bytes || 0) / 1024 / 1024).toFixed(2)} MB<br>
          Groups: ${q3.group_count || 0} • Pixel Decoded: ${q3.decoded_pixel_layers || 0}/${q3.layer_count || 0}<br>
          Composite Decoded: ${q3.composite_decoded ? 'YES' : 'NO'} • Text Layers: ${q3.text_layer_count || 0}<br>
          <em>${q3.photoshop_note || ''}</em>
        </p>
      </div>
    </div>
    <div class="card" style="margin-top:14px;">
      <h4>Version History (${currentVersions.length})</h4>
      ${(currentVersions || []).slice().reverse().map(v => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border);font-size:12px;">
          <span><strong>${v.version_id}</strong> • ${v.created_at} • ${v.note} (${v.layer_count} layers)</span>
          <button class="btn" style="padding:3px 10px;" onclick="restoreProjectVersion('${v.version_id}')">Khôi phục</button>
        </div>
      `).join('') || '<p class="stat-lbl">Chưa có lịch sử phiên bản.</p>'}
    </div>
  `;
}

async function loadSettingsUI() {
  const [res, provRes] = await Promise.all([apiGet('/api/settings'), apiGet('/api/providers')]);
  if (res.ok) {
    const s = res.settings;
    document.getElementById('setPsExe').value = s.photoshop_exe || '';
    document.getElementById('setPsAltExe').value = s.photosop_exe || '';
    document.getElementById('setMaxDim').value = s.max_dim || 2048;
    document.getElementById('setUpscale').checked = !!s.upscale_2x;
  }
  if (provRes.ok) {
    providersState = provRes.providers_state;
    document.getElementById('aiModeSel').value = providersState.mode || 'LOCAL_ONLY';
    document.getElementById('aiBudgetInput').value = providersState.monthly_budget_usd ?? 10;
    const u = providersState.usage || {};
    document.getElementById('aiUsageSummary').innerHTML = `
      <div>Đã sử dụng: <strong>$${Number(u.total_est_cost_usd || 0).toFixed(4)}</strong> / $${providersState.monthly_budget_usd} USD • Tổng API calls: <strong>${u.total_calls || 0}</strong></div>
      <div style="margin-top:4px;">Storage API Key: <strong>Windows Credential Manager</strong> (không lưu plaintext trong JSON/source).</div>
    `;
    const grid = document.getElementById('aiProvidersContainer');
    grid.innerHTML = Object.values(providersState.providers || {}).map(p => `
      <div class="card" style="margin-bottom:0;background:var(--panel2);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
          <strong>${p.provider_name}</strong>
          <span class="qa-badge ${p.has_credential ? 'qa-pass' : 'qa-fail'}">${!p.is_cloud ? 'OFFLINE READY' : (p.has_credential ? 'KEY: ' + p.credential_hint : 'NO KEY')}</span>
        </div>
        <div class="stat-lbl">${p.privacy_note || ''} • Cost/req: $${p.est_cost_per_call_usd ?? 0}</div>
        <label style="font-size:12px;display:flex;align-items:center;gap:6px;margin-top:8px;">
          <input type="checkbox" id="provEn_${p.provider_id}" ${p.enabled ? 'checked' : ''} ${!p.is_cloud ? 'disabled' : ''}> Bật Provider này trong chế độ HYBRID
        </label>
        <label class="fld">Model Name</label>
        <input type="text" id="provModel_${p.provider_id}" value="${p.model_name || ''}">
        ${p.is_cloud ? `
          <label class="fld">API Key mới (để trống nếu giữ nguyên key cũ)</label>
          <input type="password" id="provKey_${p.provider_id}" placeholder="sk-... / AIza... (lưu vào Windows Credential Manager)">
        ` : ''}
        <div class="btn-row">
          <button class="btn primary" onclick="saveProviderUI('${p.provider_id}')">💾 Lưu Provider</button>
          <button class="btn blue" onclick="testProviderUI('${p.provider_id}')">🔌 Test Connection</button>
        </div>
      </div>
    `).join('');
  }
  await refreshPrivacyBadge();
}

async function saveSettingsUI() {
  await apiPost('/api/settings', {
    photoshop_exe: document.getElementById('setPsExe').value,
    photosop_exe: document.getElementById('setPsAltExe').value,
    max_dim: Number(document.getElementById('setMaxDim').value),
    upscale_2x: document.getElementById('setUpscale').checked
  });
  setStatus('Đã lưu Settings', 'ok');
}

async function saveAiPolicyUI() {
  const mode = document.getElementById('aiModeSel').value;
  const budget = Number(document.getElementById('aiBudgetInput').value || 10);
  await apiPost('/api/providers/update', { provider_id: 'local_engine', mode, monthly_budget_usd: budget });
  setStatus(`Đã cập nhật chế độ ${mode}`, 'ok');
  await loadSettingsUI();
}

async function saveProviderUI(pid) {
  const payload = {
    provider_id: pid,
    enabled: document.getElementById('provEn_' + pid).checked,
    model_name: document.getElementById('provModel_' + pid).value.trim(),
  };
  const keyInp = document.getElementById('provKey_' + pid);
  if (keyInp && keyInp.value.trim()) payload.api_key = keyInp.value.trim();
  const res = await apiPost('/api/providers/update', payload);
  if (res.ok) {
    if (keyInp) keyInp.value = '';
    setStatus(`Đã lưu cấu hình ${pid}`, 'ok');
    loadSettingsUI();
  }
}

async function testProviderUI(pid) {
  setStatus(`Đang test kết nối ${pid}...`, 'busy');
  const res = await apiPost('/api/providers/test', { provider_id: pid });
  const msg = res.message || res.error || (res.status_code ? `HTTP ${res.status_code}` : 'Done');
  alert(res.ok ? `✅ ${pid}: ${msg}` : `❌ ${pid}: ${msg}`);
  setStatus(res.ok ? `${pid} OK` : `${pid} FAIL`, res.ok ? 'ok' : 'err');
  loadSettingsUI();
}

let remixCatalogCache = [];
async function openRemixModal() {
  if (!currentDoc) return alert('Hãy mở hoặc tạo một dự án trong Layer Editor trước!');
  setStatus('Đang tải danh sách dự án cũ để Remix...', 'busy');
  const res = await apiGet('/api/projects/remix_catalog');
  if (!res.ok) { setStatus('Lỗi tải Remix catalog', 'err'); return; }
  remixCatalogCache = (res.catalog || []).filter(c => c.project_id !== currentDoc.project_id);
  const sel = document.getElementById('remixProjSel');
  if (!remixCatalogCache.length) {
    alert('Chưa có dự án cũ nào khác để lấy ý tưởng!');
    setStatus('Sẵn sàng', 'ok');
    return;
  }
  sel.innerHTML = remixCatalogCache.map(c => `<option value="${c.project_id}">${c.title} (${c.mode} • ${c.layers.length} layers)</option>`).join('');
  onRemixProjectChange();
  document.getElementById('remixModal').classList.add('open');
  setStatus('Sẵn sàng Remix', 'ok');
}
function closeRemixModal() { document.getElementById('remixModal').classList.remove('open'); }
function onRemixProjectChange() {
  const pid = document.getElementById('remixProjSel').value;
  const src = remixCatalogCache.find(c => c.project_id === pid);
  if (!src) return;
  const swatches = (src.palette || []).map(hx => `<span style="display:inline-block;width:16px;height:16px;border-radius:4px;background:${hx};vertical-align:middle;border:1px solid #444;" title="${hx}"></span>`).join(' ');
  document.getElementById('remixPaletteInfo').innerHTML = `Bảng màu: ${swatches || 'N/A'} &nbsp;|&nbsp; Font: <strong>${(src.fonts || []).join(', ') || 'Chưa có'}</strong>`;
  document.getElementById('remixLayersGrid').innerHTML = src.layers.map(l => `
    <label style="display:flex;flex-direction:column;gap:4px;background:var(--bg);padding:6px;border-radius:6px;border:1px solid var(--border);font-size:11px;cursor:pointer;">
      <img src="${l.thumb}" style="width:100%;height:70px;object-fit:contain;background:#000;border-radius:4px;">
      <span><input type="checkbox" class="remix-lyr-chk" value="${l.id}"> ${l.name}</span>
      <span class="stat-lbl">${l.type} (${l.width}×${l.height})</span>
    </label>
  `).join('') || '<div class="stat-lbl">Không có layer ảnh có thể chép.</div>';
}
async function applyRemixFromOldProject() {
  if (!currentDoc) return;
  const srcPid = document.getElementById('remixProjSel').value;
  const layerIds = Array.from(document.querySelectorAll('.remix-lyr-chk:checked')).map(cb => cb.value);
  const applyStyle = document.getElementById('remixApplyStyle').checked;
  if (!layerIds.length && !applyStyle) {
    return alert('Hãy chọn ít nhất 1 Layer hoặc tick áp dụng Font & Màu chữ!');
  }
  setStatus('Đang đưa layer & ý tưởng từ dự án cũ vào...', 'busy');
  const res = await apiPost(`/api/project/${currentDoc.project_id}/import_remix`, {
    src_project_id: srcPid,
    layer_ids: layerIds,
    apply_palette_style: applyStyle
  });
  if (!res.ok) { setStatus(res.error || 'Lỗi Remix', 'err'); return alert(res.error); }
  currentDoc = res.document;
  currentVersions = res.versions || [];
  closeRemixModal();
  await preloadLayerImages();
  setStatus(`Đã đưa ${res.imported_count} layer từ dự án cũ vào!`, 'ok');
  renderEditor();
}

loadDashboard();
