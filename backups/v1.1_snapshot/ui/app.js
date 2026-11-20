let currentDoc = null;
let currentVersions = [];
let currentIntegrity = null;
let selectedLayerId = null;
let loadedImages = {};
let dragging = false;
let dragOffset = { x: 0, y: 0 };
let undoStack = [];
let redoStack = [];
let autosaveTimer = null;

function setStatus(text, type = 'ok') {
  const el = document.getElementById('statusPill');
  el.textContent = text;
  el.className = 'status-pill ' + type;
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
}

function redoEditor() {
  if (!currentDoc || !redoStack.length) return;
  undoStack.push(JSON.stringify(currentDoc.layers));
  currentDoc.layers = JSON.parse(redoStack.pop());
  renderEditor();
  scheduleAutosave();
}

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

async function loadDashboard() {
  const [sys, proj] = await Promise.all([apiGet('/api/system'), apiGet('/api/projects')]);
  if (sys.ok) {
    document.getElementById('sysStats').innerHTML = `
      <div class="card"><div class="stat-lbl">AI Design Studio ${sys.version || 'v1.1'}</div><div class="stat-val" style="font-size:15px;">${sys.studio_root}</div><div class="stat-lbl">Ổ D còn trống: ${sys.disk_d_free_gb} GB</div></div>
      <div class="card"><div class="stat-lbl">Phần cứng CPU / Python</div><div class="stat-val">${sys.cpu_cores} Cores</div><div class="stat-lbl">Python ${sys.python} • CPU Mode</div></div>
      <div class="card"><div class="stat-lbl">Photoshop & Dự án</div><div class="stat-val">${sys.projects_count} Dự án</div><div class="stat-lbl">Photoshop 2024: ${sys.photoshop_available ? 'Sẵn sàng' : 'Chưa tìm thấy'}</div></div>
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
  const res = await apiGet('/api/project/' + pid);
  if (!res.ok) { setStatus('Lỗi tải dự án', 'err'); return; }
  currentDoc = res.document;
  currentVersions = res.versions || [];
  currentIntegrity = res.integrity || null;
  undoStack = [];
  redoStack = [];
  if (res.autosave_recovery && res.autosave_recovery.has_recovery) {
    if (confirm(`Phát hiện bản Autosave lúc ${res.autosave_recovery.autosaved_at} chưa lưu chính thức. Khôi phục bản Autosave này?`)) {
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
  if (!currentDoc) return;
  for (const l of currentDoc.layers) {
    if (!l.source_file) continue;
    const im = new Image();
    im.src = `/projects/${currentDoc.project_id}/${l.source_file}?t=${Date.now()}`;
    await new Promise(res => { im.onload = res; im.onerror = res; });
    loadedImages[l.id] = im;
  }
}

async function submitRedesign() {
  const file = document.getElementById('rdFile').files[0];
  if (!file) return alert('Hãy chọn 1 file ảnh trước!');
  setStatus('Đang phân tích & tách layer...', 'busy');
  const data_base64 = await fileToBase64(file);
  const res = await apiPost('/api/redesign', {
    title: document.getElementById('rdTitle').value,
    filename: file.name,
    upscale_2x: document.getElementById('rdUpscale').checked,
    data_base64
  });
  if (!res.ok) { setStatus('Lỗi: ' + res.error, 'err'); return alert(res.error); }
  currentDoc = res.document;
  currentVersions = res.versions || [];
  undoStack = []; redoStack = [];
  selectedLayerId = currentDoc.layers.length ? currentDoc.layers[currentDoc.layers.length - 1].id : null;
  document.getElementById('activeProjectLabel').textContent = `${currentDoc.title} (${currentDoc.width}×${currentDoc.height})`;
  await preloadLayerImages();
  setStatus('Tách Layer & QA hoàn tất!', 'ok');
  switchView('editor');
}

function readGeneratePayload() {
  const prods = Array.from(document.getElementById('genProduct').selectedOptions).map(o => o.value);
  const refs = Array.from(document.getElementById('genRef').selectedOptions).map(o => o.value);
  const bulletsRaw = document.getElementById('genBullets').value || '';
  return {
    title: document.getElementById('genTitle').value,
    industry: document.getElementById('genIndustry').value,
    layout: document.getElementById('genLayout').value,
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

/* Editor Logic */
function renderEditor() {
  const cvs = document.getElementById('editorCanvas');
  const ctx = cvs.getContext('2d');
  if (!currentDoc) { ctx.clearRect(0,0,cvs.width,cvs.height); return; }
  cvs.width = currentDoc.width;
  cvs.height = currentDoc.height;
  ctx.clearRect(0, 0, cvs.width, cvs.height);

  const sorted = [...currentDoc.layers].sort((a,b) => a.z_index - b.z_index);
  for (const l of sorted) {
    if (!l.visible) continue;
    const im = loadedImages[l.id];
    const meta = l.metadata || {};
    const sc = meta.scale || 1;
    const dw = l.width * sc, dh = l.height * sc;
    ctx.save();
    ctx.globalAlpha = l.opacity ?? 1;
    ctx.filter = `hue-rotate(${meta.hue||0}deg) saturate(${meta.sat??100}%) brightness(${meta.bright??100}%)`;
    if (l.type === 'text' && l.text_data && meta.text_dirty) {
      // Live text preview immediately when user edits text before saving
      ctx.font = `700 ${(l.text_data.font_size||42)*sc}px "Segoe UI", Arial, sans-serif`;
      const c = l.text_data.color || [255,255,255];
      ctx.fillStyle = `rgb(${c[0]},${c[1]},${c[2]})`;
      ctx.textBaseline = 'top';
      ctx.fillText(l.text_data.text, l.x + 12, l.y + 12);
    } else if (im && im.complete) {
      ctx.drawImage(im, l.x, l.y, dw, dh);
    } else if (l.type === 'text' && l.text_data) {
      ctx.font = `700 ${(l.text_data.font_size||42)*sc}px "Segoe UI", Arial, sans-serif`;
      const c = l.text_data.color || [255,255,255];
      ctx.fillStyle = `rgb(${c[0]},${c[1]},${c[2]})`;
      ctx.textBaseline = 'top';
      ctx.fillText(l.text_data.text, l.x, l.y);
    }
    if (l.id === selectedLayerId) {
      ctx.filter = 'none';
      ctx.strokeStyle = '#10b981';
      ctx.lineWidth = Math.max(2, currentDoc.width / 400);
      ctx.setLineDash([8, 5]);
      ctx.strokeRect(l.x, l.y, dw, dh);
    }
    ctx.restore();
  }
  renderEditorLayerList();
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
  const sorted = [...currentDoc.layers].sort((a,b) => a.z_index - b.z_index);
  box.innerHTML = '';
  for (const l of sorted) {
    const row = document.createElement('div');
    row.className = 'lyr-row' + (l.id === selectedLayerId ? ' active' : '');
    row.onclick = () => { selectedLayerId = l.id; renderEditor(); };

    const eye = document.createElement('button');
    eye.className = 'btn';
    eye.style.padding = '2px 6px';
    eye.textContent = l.visible ? '👁' : '—';
    eye.onclick = (e) => { e.stopPropagation(); pushUndoSnapshot(); l.visible = !l.visible; renderEditor(); };

    const thumb = document.createElement('img');
    if (loadedImages[l.id]) thumb.src = loadedImages[l.id].src;

    const nm = document.createElement('span');
    nm.className = 'lyr-name';
    nm.textContent = `[${l.group || 'Main'}] ${l.name}`;

    const tag = document.createElement('span');
    tag.className = 'tag' + (l.ai_reconstructed ? ' ai' : '');
    tag.textContent = l.ai_reconstructed ? 'AI-fill' : l.type;

    row.append(eye, thumb, nm, tag);
    box.appendChild(row);
  }
}

function getSelLayer() { return currentDoc ? currentDoc.layers.find(l => l.id === selectedLayerId) : null; }

function syncEditorProps() {
  const l = getSelLayer();
  const gSel = document.getElementById('edGroupSel');
  gSel.innerHTML = getAllGroups().map(g => `<option value="${g}">${g}</option>`).join('');
  if (!l) return;
  const m = l.metadata || {};
  document.getElementById('edSelTitle').textContent = l.name;
  gSel.value = l.group || 'Main';
  document.getElementById('edOp').value = Math.round((l.opacity ?? 1) * 100);
  document.getElementById('edScale').value = Math.round((m.scale ?? 1) * 100);
  document.getElementById('edHue').value = m.hue ?? 0;
  document.getElementById('edSat').value = m.sat ?? 100;
  document.getElementById('edBright').value = m.bright ?? 100;
  const tb = document.getElementById('edTextBox');
  if (l.type === 'text' && l.text_data) {
    tb.style.display = 'block';
    document.getElementById('edTextVal').value = l.text_data.text || '';
    document.getElementById('edFontSize').value = l.text_data.font_size || 42;
    const c = l.text_data.color || [255,255,255];
    document.getElementById('edTextColor').value = '#' + c.map(x => x.toString(16).padStart(2,'0')).join('');
  } else {
    tb.style.display = 'none';
  }
}

function onPropChange(k, v) { const l = getSelLayer(); if (l) { pushUndoSnapshot(); l[k] = v; renderEditor(); } }
function onMetaChange(k, v) { const l = getSelLayer(); if (l) { pushUndoSnapshot(); l.metadata = l.metadata || {}; l.metadata[k] = v; renderEditor(); } }
function onTextChange(k, v) {
  const l = getSelLayer();
  if (l && l.text_data) {
    pushUndoSnapshot();
    l.text_data[k] = v;
    l.metadata = l.metadata || {};
    l.metadata.text_dirty = true;
    renderEditor();
  }
}
function onTextColorChange(hex) {
  const l = getSelLayer();
  if (l && l.text_data) {
    pushUndoSnapshot();
    l.text_data.color = [parseInt(hex.slice(1,3),16), parseInt(hex.slice(3,5),16), parseInt(hex.slice(5,7),16)];
    l.metadata = l.metadata || {};
    l.metadata.text_dirty = true;
    renderEditor();
  }
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

async function assignSelectedGroup(gName) {
  const l = getSelLayer();
  if (!l || !currentDoc) return;
  pushUndoSnapshot();
  l.group = gName;
  renderEditor();
}

function addNewTextLayer() {
  if (!currentDoc) return;
  pushUndoSnapshot();
  const id = 'lyr_txt_' + Date.now().toString(36);
  const maxZ = currentDoc.layers.reduce((m, l) => Math.max(m, l.z_index), 0);
  currentDoc.layers.push({
    id, name: 'Text_Moi', type: 'text', source_file: null,
    x: 80, y: 80, width: 320, height: 60, z_index: maxZ + 1,
    opacity: 1, visible: true, blend_mode: 'normal', group: '4_Typography',
    text_data: { text: 'CHỮ MỚI', font: 'FZPoppins-Bold', font_size: 52, color: [255, 255, 255] },
    metadata: { text_dirty: true }
  });
  selectedLayerId = id;
  renderEditor();
}

function deleteSelectedLayer() {
  if (!currentDoc || !selectedLayerId) return;
  pushUndoSnapshot();
  currentDoc.layers = currentDoc.layers.filter(l => l.id !== selectedLayerId);
  selectedLayerId = currentDoc.layers.length ? currentDoc.layers[currentDoc.layers.length - 1].id : null;
  renderEditor();
}

function shiftLayerZ(dir) {
  const l = getSelLayer();
  if (!l || !currentDoc) return;
  pushUndoSnapshot();
  const sorted = [...currentDoc.layers].sort((a,b) => a.z_index - b.z_index);
  const idx = sorted.findIndex(x => x.id === l.id);
  const tgt = idx + dir;
  if (tgt < 0 || tgt >= sorted.length) return;
  const tmp = sorted[idx].z_index;
  sorted[idx].z_index = sorted[tgt].z_index;
  sorted[tgt].z_index = tmp;
  renderEditor();
}

const edCvs = document.getElementById('editorCanvas');
edCvs.addEventListener('mousedown', (e) => {
  if (!currentDoc) return;
  const r = edCvs.getBoundingClientRect();
  const mx = (e.clientX - r.left) * (edCvs.width / r.width);
  const my = (e.clientY - r.top) * (edCvs.height / r.height);
  const sorted = [...currentDoc.layers].sort((a,b) => b.z_index - a.z_index);
  for (const l of sorted) {
    if (!l.visible) continue;
    const sc = (l.metadata && l.metadata.scale) || 1;
    if (mx >= l.x && mx <= l.x + l.width * sc && my >= l.y && my <= l.y + l.height * sc) {
      selectedLayerId = l.id;
      pushUndoSnapshot();
      dragging = true;
      dragOffset = { x: mx - l.x, y: my - l.y };
      renderEditor();
      return;
    }
  }
});
window.addEventListener('mousemove', (e) => {
  if (!dragging || !currentDoc) return;
  const l = getSelLayer();
  if (!l) return;
  const r = edCvs.getBoundingClientRect();
  const mx = (e.clientX - r.left) * (edCvs.width / r.width);
  const my = (e.clientY - r.top) * (edCvs.height / r.height);
  l.x = Math.round(mx - dragOffset.x);
  l.y = Math.round(my - dragOffset.y);
  renderEditor();
});
window.addEventListener('mouseup', () => { dragging = false; });

async function saveEditorAndExport() {
  if (!currentDoc) return;
  setStatus('Đang lưu Version, chạy QA & xuất PSD...', 'busy');
  const res = await apiPost(`/api/project/${currentDoc.project_id}/save`, { layers: currentDoc.layers });
  if (!res.ok) { setStatus('Lỗi lưu dự án', 'err'); return alert(res.error); }
  currentDoc = res.document;
  currentVersions = res.versions || [];
  currentIntegrity = res.integrity || null;
  document.getElementById('autosavePill').style.display = 'none';
  await preloadLayerImages();
  setStatus('Đã lưu Version & xuất PSD đạt chuẩn QA!', 'ok');
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

/* Assets, Knowledge, History, Export, Settings */
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
      <h3>${cat.toUpperCase()} (${(a[cat]||[]).length})</h3>
      <div class="asset-grid">
        ${(a[cat]||[]).map(item => `
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
  document.getElementById('kbContainer').innerHTML = `
    <div class="grid-2">
      <div class="card">
        <h3>Nguyên tắc thiết kế & Phân tích Tham khảo (${(kb.references_analyzed||[]).length})</h3>
        ${Object.values(kb.principles || {}).flat().map(p => `<p style="font-size:12px;margin-bottom:8px;"><strong>${p.name}:</strong> <span class="stat-lbl">${p.rule}</span></p>`).join('')}
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
        <div class="stat-lbl">Canvas: ${currentDoc.width}×${currentDoc.height} • ${currentDoc.layers.length} layers • Integrity: ${currentIntegrity ? (currentIntegrity.ok ? 'OK' : 'MISSING ASSETS') : 'Checked'}</div>
      </div>
      <div class="btn-row" style="margin:0;">
        <a class="btn primary" href="/projects/${pid}/${qa.psd_file}" download>⬇️ Tải file .PSD</a>
        <button class="btn blue" onclick="apiPost('/api/project/${pid}/open_photoshop', {})">🎨 Mở trong Photoshop 2024</button>
        <button class="btn" onclick="apiPost('/api/project/${pid}/open_folder', {})">📁 Mở thư mục</button>
      </div>
    </div>
    <div class="grid-3">
      <div class="card">
        <h4>QA 1 — Layer Inspection <span class="qa-badge ${q1.passed?'qa-pass':'qa-fail'}">${q1.passed?'PASS':'FAIL'}</span></h4>
        <p class="stat-lbl" style="margin:8px 0;">Đã kiểm tra ${q1.checked_count||0} layers. Lỗi: ${(q1.issues||[]).length}</p>
        ${q1.qa_sheet ? `<img src="/projects/${pid}/${q1.qa_sheet}?t=${Date.now()}" style="width:100%;border-radius:6px;">` : ''}
      </div>
      <div class="card">
        <h4>QA 2 — Composite Inspection <span class="qa-badge ${q2.passed?'qa-pass':'qa-fail'}">${q2.passed?'PASS':'FAIL'}</span></h4>
        <p class="stat-lbl" style="margin:8px 0;">Vùng thủng: ${q2.transparent_hole_pct ?? 0}% • MAE vs gốc: ${q2.mae_vs_source ?? 'N/A'}</p>
        ${q2.composite_file ? `<img src="/projects/${pid}/${q2.composite_file}?t=${Date.now()}" style="width:100%;border-radius:6px;">` : ''}
      </div>
      <div class="card">
        <h4>QA 3 — PSD Binary Verify <span class="qa-badge ${q3.passed?'qa-pass':'qa-fail'}">${q3.passed?'PASS':'FAIL'}</span></h4>
        <p class="stat-lbl" style="margin:8px 0;line-height:1.5;">
          Dung lượng: ${((q3.psd_bytes||0)/1024/1024).toFixed(2)} MB<br>
          Groups: ${q3.group_count||0} • Pixel Decoded: ${q3.decoded_pixel_layers||0}/${q3.layer_count||0}<br>
          Composite Decoded: ${q3.composite_decoded ? 'YES' : 'NO'} • Text Layers: ${q3.text_layer_count||0}<br>
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
  const res = await apiGet('/api/settings');
  if (!res.ok) return;
  const s = res.settings;
  document.getElementById('setPsExe').value = s.photoshop_exe || '';
  document.getElementById('setPsAltExe').value = s.photosop_exe || '';
  document.getElementById('setMaxDim').value = s.max_dim || 2048;
  document.getElementById('setUpscale').checked = !!s.upscale_2x;
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

loadDashboard();
