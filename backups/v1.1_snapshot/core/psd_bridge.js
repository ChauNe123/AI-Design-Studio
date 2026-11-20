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

function buildPsdFromDocument(projectDir, outPsdPath) {
  const docPath = path.join(projectDir, 'design_document.json');
  const doc = JSON.parse(fs.readFileSync(docPath, 'utf8'));

  const sortedLayers = [...(doc.layers || [])].sort((a, b) => (a.z_index || 0) - (b.z_index || 0));
  const groupOrder = [];
  const groupMap = new Map();

  for (const lyr of sortedLayers) {
    const gName = lyr.group || 'Main';
    if (!groupMap.has(gName)) {
      groupMap.set(gName, []);
      groupOrder.push(gName);
    }

    const psdLayer = {
      name: lyr.name || lyr.id,
      left: Math.round(lyr.x || 0),
      top: Math.round(lyr.y || 0),
      hidden: lyr.visible === false,
      opacity: typeof lyr.opacity === 'number' ? Math.max(0, Math.min(1, lyr.opacity)) : 1,
      blendMode: lyr.blend_mode || 'normal'
    };

    const srcRel = (lyr.metadata && lyr.metadata.export_override_file) || lyr.source_file;
    if (srcRel) {
      const absSrc = path.join(projectDir, srcRel);
      if (fs.existsSync(absSrc)) {
        psdLayer.imageData = loadPngAsImageData(absSrc);
      }
    }

    if (lyr.type === 'text' && lyr.text_data && lyr.text_data.text) {
      const td = lyr.text_data;
      const col = Array.isArray(td.color) ? td.color : [255, 255, 255];
      const fontSize = Number(td.font_size) || 36;
      const fontName = td.font || 'Arial-BoldMT';
      psdLayer.text = {
        text: String(td.text).replace(/\r?\n/g, '\r'),
        transform: [1, 0, 0, 1, psdLayer.left, psdLayer.top + fontSize],
        style: {
          font: { name: fontName },
          fontSize,
          fillColor: { r: col[0] || 0, g: col[1] || 0, b: col[2] || 0 }
        }
      };
    }

    groupMap.get(gName).push(psdLayer);
  }

  const children = groupOrder.map(gName => ({
    name: gName,
    opened: true,
    children: groupMap.get(gName)
  }));

  const psd = {
    width: doc.width,
    height: doc.height,
    channels: 4,
    bitsPerChannel: 8,
    colorMode: 3, // RGB
    children
  };

  const buffer = writePsdBuffer(psd, { generateThumbnail: false });
  fs.writeFileSync(outPsdPath, buffer);
  return {
    ok: true,
    psd_path: outPsdPath,
    bytes: buffer.length,
    width: doc.width,
    height: doc.height,
    groups: groupOrder.length,
    layers: sortedLayers.length
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

  return {
    ok: compositeOk && flatLayers.length > 0 && decodedPixelLayers === flatLayers.length,
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
