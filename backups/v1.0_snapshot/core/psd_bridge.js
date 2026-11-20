const fs = require('fs');
const path = require('path');
const { PNG } = require('pngjs');
const { writePsdBuffer, readPsd } = require('ag-psd');

function loadPngAsImageData(absPath, targetW, targetH) {
  const buf = fs.readFileSync(absPath);
  const png = PNG.sync.read(buf);
  // If user scaled the layer in the editor, ag-psd expects pixel buffer matching actual PNG;
  // caller (Python export preparer) pre-renders scaled/tinted layers into export_cache if modified.
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
        psdLayer.imageData = loadPngAsImageData(absSrc, lyr.width, lyr.height);
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
  const parsed = readPsd(buf, { skipLayerImageData: true, skipCompositeImageData: true });
  const flatLayers = [];
  function walk(nodes, grp) {
    if (!nodes) return;
    for (const n of nodes) {
      if (n.children) {
        walk(n.children, n.name);
      } else {
        flatLayers.push({
          group: grp,
          name: n.name,
          left: n.left,
          top: n.top,
          right: n.right,
          bottom: n.bottom,
          hidden: !!n.hidden,
          hasText: !!n.text,
          textValue: n.text ? n.text.text : null
        });
      }
    }
  }
  walk(parsed.children, 'root');
  return {
    ok: true,
    width: parsed.width,
    height: parsed.height,
    channels: parsed.channels,
    bitsPerChannel: parsed.bitsPerChannel,
    colorMode: parsed.colorMode,
    layer_count: flatLayers.length,
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
