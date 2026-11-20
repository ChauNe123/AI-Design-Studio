const fs = require('fs');
const path = require('path');
const { PNG } = require('pngjs');
const { writePsdBuffer, readPsd, initializeCanvas } = require('ag-psd');

// Lightweight pure-JS canvas/imageData shim so readPsd decodes full binary pixel buffers without node-canvas
initializeCanvas(
  (w, h) => ({
    width: w,
    height: h,
    getContext: () => ({
      createImageData: (cw, ch) => ({ width: cw, height: ch, data: new Uint8ClampedArray(cw * ch * 4) }),
      putImageData: () => {}
    })
  }),
  (w, h) => ({ width: w, height: h, data: new Uint8ClampedArray(w * h * 4) })
);

function loadPngAsImageData(absPath) {
  const buf = fs.readFileSync(absPath);
  const png = PNG.sync.read(buf);
  return {
    width: png.width,
    height: png.height,
    data: new Uint8ClampedArray(png.data)
  };
}

function loadMaskAsImageData(absPath) {
  const buf = fs.readFileSync(absPath);
  const png = PNG.sync.read(buf);
  const out = new Uint8ClampedArray(png.width * png.height * 4);
  for (let i = 0; i < out.length; i += 4) {
    const g = png.data[i]; // Red channel holds grayscale intensity (pngjs expands L/G to RGBA)
    out[i] = g;
    out[i + 1] = g;
    out[i + 2] = g;
    out[i + 3] = 255;
  }
  return {
    width: png.width,
    height: png.height,
    data: out
  };
}

function mapAdjustmentData(adj) {
  if (!adj || !adj.type) return undefined;
  const t = adj.type;
  if (t === 'curves') {
    return {
      type: 'curves',
      presetKind: typeof adj.presetKind === 'number' ? adj.presetKind : 2,
      presetFileName: adj.presetFileName || '',
      channels: Array.isArray(adj.channels) ? adj.channels : [[{ input: 0, output: 0 }, { input: 255, output: 255 }]]
    };
  }
  if (t === 'color balance') {
    const z = { cyanRed: 0, magentaGreen: 0, yellowBlue: 0 };
    return {
      type: 'color balance',
      shadows: { ...z, ...(adj.shadows || {}) },
      midtones: { ...z, ...(adj.midtones || {}) },
      highlights: { ...z, ...(adj.highlights || {}) },
      preserveLuminosity: adj.preserveLuminosity !== false
    };
  }
  if (t === 'hue/saturation') {
    const out = {
      type: 'hue/saturation',
      colorize: !!adj.colorize,
      colorization: adj.colorization || { hue: 0, saturation: 0, lightness: 0 },
      master: { hue: 0, saturation: 0, lightness: 0, ...(adj.master || {}) }
    };
    for (const ch of ['reds', 'yellows', 'greens', 'cyans', 'blues', 'magentas']) {
      if (adj[ch]) out[ch] = adj[ch];
    }
    return out;
  }
  if (t === 'vibrance') {
    return {
      type: 'vibrance',
      vibrance: Math.round(Number(adj.vibrance || 0)),
      saturation: Math.round(Number(adj.saturation || 0))
    };
  }
  if (t === 'selective color') {
    const z = { c: 0, m: 0, y: 0, k: 0 };
    return {
      type: 'selective color',
      mode: adj.mode === 'absolute' ? 'absolute' : 'relative',
      reds: { ...z, ...(adj.reds || {}) },
      yellows: { ...z, ...(adj.yellows || {}) },
      greens: { ...z, ...(adj.greens || {}) },
      cyans: { ...z, ...(adj.cyans || {}) },
      blues: { ...z, ...(adj.blues || {}) },
      magentas: { ...z, ...(adj.magentas || {}) },
      whites: { ...z, ...(adj.whites || {}) },
      neutrals: { ...z, ...(adj.neutrals || {}) },
      blacks: { ...z, ...(adj.blacks || {}) }
    };
  }
  if (t === 'brightness/contrast') {
    return {
      type: 'brightness/contrast',
      brightness: Number(adj.brightness || 0),
      contrast: Number(adj.contrast || 0),
      useLegacy: !!adj.useLegacy
    };
  }
  if (t === 'levels') {
    return {
      type: 'levels',
      presetKind: typeof adj.presetKind === 'number' ? adj.presetKind : 2,
      presetFileName: adj.presetFileName || '',
      channels: adj.channels || []
    };
  }
  return adj;
}

function toRgbColor(c) {
  if (Array.isArray(c)) return { r: Number(c[0] || 0), g: Number(c[1] || 0), b: Number(c[2] || 0) };
  if (c && typeof c === 'object') return { r: Number(c.r || 0), g: Number(c.g || 0), b: Number(c.b || 0) };
  return { r: 0, g: 0, b: 0 };
}

function mapLayerEffects(lyr) {
  const pe = lyr.psd_effects;
  if (!pe || typeof pe !== 'object') return undefined;
  const out = { disabled: false, scale: 1 };
  let hasAny = false;

  if (Array.isArray(pe.dropShadow) && pe.dropShadow.length) {
    out.dropShadow = pe.dropShadow.map(s => ({
      enabled: s.enabled !== false,
      present: true,
      showInDialog: true,
      blendMode: s.blendMode || 'multiply',
      color: toRgbColor(s.color || [0, 0, 0]),
      opacity: typeof s.opacity === 'number' ? s.opacity : 0.75,
      useGlobalLight: !!s.useGlobalLight,
      angle: typeof s.angle === 'number' ? s.angle : 120,
      distance: { units: 'Pixels', value: Number(s.distance || 6) },
      choke: { units: 'Pixels', value: Number(s.choke || 0) },
      size: { units: 'Pixels', value: Number(s.size || 12) }
    }));
    hasAny = true;
  }

  if (Array.isArray(pe.innerShadow) && pe.innerShadow.length) {
    out.innerShadow = pe.innerShadow.map(s => ({
      enabled: s.enabled !== false,
      present: true,
      showInDialog: true,
      blendMode: s.blendMode || 'multiply',
      color: toRgbColor(s.color || [0, 0, 0]),
      opacity: typeof s.opacity === 'number' ? s.opacity : 0.5,
      useGlobalLight: !!s.useGlobalLight,
      angle: typeof s.angle === 'number' ? s.angle : 120,
      distance: { units: 'Pixels', value: Number(s.distance || 3) },
      choke: { units: 'Pixels', value: Number(s.choke || 0) },
      size: { units: 'Pixels', value: Number(s.size || 6) }
    }));
    hasAny = true;
  }

  if (Array.isArray(pe.stroke) && pe.stroke.length) {
    out.stroke = pe.stroke.map(s => ({
      enabled: s.enabled !== false,
      present: true,
      showInDialog: true,
      position: s.position || 'outside',
      fillType: 'color',
      blendMode: s.blendMode || 'normal',
      opacity: typeof s.opacity === 'number' ? s.opacity : 1,
      size: { units: 'Pixels', value: Number(s.size || 3) },
      color: toRgbColor(s.color || [255, 255, 255])
    }));
    hasAny = true;
  }

  if (Array.isArray(pe.solidFill) && pe.solidFill.length) {
    out.solidFill = pe.solidFill.map(s => ({
      enabled: s.enabled !== false,
      present: true,
      showInDialog: true,
      blendMode: s.blendMode || 'normal',
      opacity: typeof s.opacity === 'number' ? s.opacity : 1,
      color: toRgbColor(s.color || [255, 255, 255])
    }));
    hasAny = true;
  }

  if (Array.isArray(pe.gradientOverlay) && pe.gradientOverlay.length) {
    out.gradientOverlay = pe.gradientOverlay.map(g => ({
      enabled: g.enabled !== false,
      present: true,
      showInDialog: true,
      blendMode: g.blendMode || 'normal',
      opacity: typeof g.opacity === 'number' ? g.opacity : 1,
      angle: typeof g.angle === 'number' ? g.angle : 90,
      type: g.type || 'linear',
      align: true,
      scale: typeof g.scale === 'number' ? g.scale : 1,
      gradient: {
        name: g.name || 'Custom Gradient',
        type: 'solid',
        smoothness: 1,
        colorStops: (g.colorStops || [
          { color: [16, 185, 129], location: 0 },
          { color: [11, 43, 104], location: 1 }
        ]).map(st => ({
          color: toRgbColor(st.color),
          location: typeof st.location === 'number' ? st.location : 0,
          midpoint: 0.5
        })),
        opacityStops: [
          { opacity: 1, location: 0, midpoint: 0.5 },
          { opacity: 1, location: 1, midpoint: 0.5 }
        ]
      }
    }));
    hasAny = true;
  }

  if (pe.outerGlow && typeof pe.outerGlow === 'object') {
    const og = pe.outerGlow;
    out.outerGlow = {
      enabled: og.enabled !== false,
      present: true,
      showInDialog: true,
      blendMode: og.blendMode || 'screen',
      opacity: typeof og.opacity === 'number' ? og.opacity : 0.75,
      color: toRgbColor(og.color || [0, 255, 200]),
      size: { units: 'Pixels', value: Number(og.size || 15) }
    };
    hasAny = true;
  }

  return hasAny ? out : undefined;
}

function buildPsdFromDocument(projectDir, outPsdPath) {
  const docPath = path.join(projectDir, 'design_document.json');
  const doc = JSON.parse(fs.readFileSync(docPath, 'utf8'));

  const sortedLayers = [...(doc.layers || [])].sort((a, b) => (a.z_index || 0) - (b.z_index || 0));
  const rootChildren = [];
  const groupNodes = new Map();

  for (const lyr of sortedLayers) {
    const isAdj = lyr.type === 'adjustment' && !!lyr.adjustment_data;
    const expOff = (lyr.metadata && Array.isArray(lyr.metadata.export_offset)) ? lyr.metadata.export_offset : [0, 0];
    const psdLayer = {
      name: lyr.name || lyr.id,
      hidden: lyr.visible === false,
      opacity: typeof lyr.opacity === 'number' ? Math.max(0, Math.min(1, lyr.opacity)) : 1,
      blendMode: lyr.blend_mode || 'normal',
      clipping: !!lyr.clipping
    };

    if (isAdj) {
      psdLayer.top = 0;
      psdLayer.left = 0;
      psdLayer.bottom = 0;
      psdLayer.right = 0;
      psdLayer.adjustment = mapAdjustmentData(lyr.adjustment_data);
    } else {
      psdLayer.left = Math.round((lyr.x || 0) - (expOff[0] || 0));
      psdLayer.top = Math.round((lyr.y || 0) - (expOff[1] || 0));
      const srcRel = (lyr.metadata && lyr.metadata.export_override_file) || lyr.source_file;
      if (srcRel) {
        const absSrc = path.join(projectDir, srcRel);
        if (fs.existsSync(absSrc)) {
          psdLayer.imageData = loadPngAsImageData(absSrc);
        }
      }
    }

    if (lyr.mask_file) {
      const absMask = path.join(projectDir, lyr.mask_file);
      if (fs.existsSync(absMask)) {
        const maskImg = loadMaskAsImageData(absMask);
        const maskTop = isAdj ? 0 : Math.round(lyr.mask_y ?? 0);
        const maskLeft = isAdj ? 0 : Math.round(lyr.mask_x ?? 0);
        psdLayer.mask = {
          top: maskTop,
          left: maskLeft,
          bottom: maskTop + maskImg.height,
          right: maskLeft + maskImg.width,
          defaultColor: typeof lyr.mask_default_color === 'number' ? lyr.mask_default_color : 0,
          imageData: maskImg
        };
      }
    }

    if (lyr.type === 'text' && lyr.text_data && lyr.text_data.text) {
      const td = lyr.text_data;
      const col = Array.isArray(td.color) ? td.color : [255, 255, 255];
      const fontSize = Number(td.font_size) || 36;
      const fontName = td.font || 'Arial-BoldMT';
      psdLayer.text = {
        text: String(td.text).replace(/\r?\n/g, '\r'),
        transform: [1, 0, 0, 1, Math.round(lyr.x || 0), Math.round(lyr.y || 0) + fontSize],
        style: {
          font: { name: fontName },
          fontSize,
          fillColor: { r: col[0] || 0, g: col[1] || 0, b: col[2] || 0 }
        }
      };
    }

    const mappedFx = mapLayerEffects(lyr);
    if (mappedFx && !isAdj) {
      psdLayer.effects = mappedFx;
    }

    const gName = lyr.group;
    if (gName === 'Root' || gName === '') {
      rootChildren.push(psdLayer);
    } else {
      const grpKey = gName || 'Main';
      if (!groupNodes.has(grpKey)) {
        const grpNode = {
          name: grpKey,
          opened: true,
          blendMode: 'normal',
          children: []
        };
        groupNodes.set(grpKey, grpNode);
        rootChildren.push(grpNode);
      }
      const grp = groupNodes.get(grpKey);
      if (isAdj) grp.blendMode = 'pass through';
      grp.children.push(psdLayer);
    }
  }

  const psd = {
    width: doc.width,
    height: doc.height,
    channels: 4,
    bitsPerChannel: 8,
    colorMode: 3, // RGB
    children: rootChildren
  };

  // Attach pre-rendered full-resolution composite image when available
  const compCandidates = [
    doc.composite_preview,
    'composite_after.png',
    'qa_composite.png'
  ].filter(Boolean);
  for (const rel of compCandidates) {
    const absComp = path.join(projectDir, rel);
    if (fs.existsSync(absComp)) {
      const compImg = loadPngAsImageData(absComp);
      if (compImg.width === doc.width && compImg.height === doc.height) {
        psd.imageData = compImg;
        break;
      }
    }
  }

  const buffer = writePsdBuffer(psd, { generateThumbnail: false });
  fs.writeFileSync(outPsdPath, buffer);
  return {
    ok: true,
    psd_path: outPsdPath,
    bytes: buffer.length,
    width: doc.width,
    height: doc.height,
    groups: groupNodes.size,
    layers: sortedLayers.length,
    adjustment_layers: sortedLayers.filter(l => l.type === 'adjustment').length
  };
}

function verifyPsdFile(psdPath) {
  const buf = fs.readFileSync(psdPath);
  if (buf.length < 26 || buf.slice(0, 4).toString('ascii') !== '8BPS') {
    throw new Error('Invalid PSD header (missing 8BPS signature)');
  }
  const parsed = readPsd(buf, { useImageData: true });
  const flatLayers = [];
  const groupNames = [];
  let decodedPixelLayers = 0;
  let adjustmentLayerCount = 0;
  let maskedLayerCount = 0;
  let clippedLayerCount = 0;
  let fxLayerCount = 0;

  function walk(nodes, grp) {
    if (!nodes) return;
    for (const n of nodes) {
      if (n.children) {
        groupNames.push(n.name);
        walk(n.children, n.name);
      } else {
        let pixelOk = false;
        let nonZeroPixels = false;
        if (n.imageData && n.imageData.data && n.imageData.width > 0 && n.imageData.height > 0) {
          pixelOk = n.imageData.data.length === n.imageData.width * n.imageData.height * 4;
          for (let i = 3; i < n.imageData.data.length; i += 4) {
            if (n.imageData.data[i] > 0) {
              nonZeroPixels = true;
              break;
            }
          }
          if (pixelOk) decodedPixelLayers++;
        }
        const hasAdjustment = !!n.adjustment;
        if (hasAdjustment) adjustmentLayerCount++;
        const maskOk = !!(n.mask && n.mask.imageData && n.mask.imageData.width > 0 && n.mask.imageData.height > 0);
        if (maskOk) maskedLayerCount++;
        const isClipping = !!n.clipping;
        if (isClipping) clippedLayerCount++;
        const hasEffects = !!(n.effects && !n.effects.disabled);
        if (hasEffects) fxLayerCount++;

        flatLayers.push({
          group: grp,
          name: n.name,
          left: n.left,
          top: n.top,
          right: n.right,
          bottom: n.bottom,
          opacity: n.opacity,
          hidden: !!n.hidden,
          blendMode: n.blendMode || 'normal',
          clipping: isClipping,
          hasMask: !!n.mask,
          maskOk,
          hasEffects,
          hasAdjustment,
          adjustmentType: n.adjustment ? n.adjustment.type : null,
          pixelOk,
          nonZeroPixels,
          hasText: !!n.text,
          textValue: n.text ? n.text.text.replace(/\r/g, '\n') : null
        });
      }
    }
  }
  walk(parsed.children, 'root');

  const compositeOk = !!(
    parsed.imageData &&
    parsed.imageData.width === parsed.width &&
    parsed.imageData.height === parsed.height &&
    parsed.imageData.data.length === parsed.width * parsed.height * 4
  );

  const allLayersValid = flatLayers.every(l => l.pixelOk || l.hasAdjustment);

  return {
    ok: compositeOk && flatLayers.length > 0 && allLayersValid,
    width: parsed.width,
    height: parsed.height,
    channels: parsed.channels,
    bitsPerChannel: parsed.bitsPerChannel,
    colorMode: parsed.colorMode,
    composite_decoded: compositeOk,
    group_count: groupNames.length,
    groups: groupNames,
    layer_count: flatLayers.length,
    decoded_pixel_layers: decodedPixelLayers,
    adjustment_layer_count: adjustmentLayerCount,
    masked_layer_count: maskedLayerCount,
    clipped_layer_count: clippedLayerCount,
    fx_layer_count: fxLayerCount,
    text_layer_count: flatLayers.filter(l => l.hasText).length,
    layers: flatLayers
  };
}

const [, , cmd, arg1, arg2] = process.argv;
try {
  if (cmd === 'export') {
    const res = buildPsdFromDocument(arg1, arg2);
    console.log(JSON.stringify(res));
  } else if (cmd === 'verify') {
    const res = verifyPsdFile(arg1);
    console.log(JSON.stringify(res));
  } else {
    console.error('Usage: node psd_bridge.js <export projectDir outPsd | verify psdPath>');
    process.exit(1);
  }
} catch (err) {
  console.error(JSON.stringify({ ok: false, error: err.message }));
  process.exit(1);
}
