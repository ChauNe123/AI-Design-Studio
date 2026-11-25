import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { PNG } from 'pngjs';
import { createWorker } from 'tesseract.js';
import * as ort from 'onnxruntime-node';
import { env, pipeline, AutoModel, AutoProcessor, SamModel, RawImage } from '@huggingface/transformers';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const STUDIO_ROOT = path.dirname(__dirname);
const MODELS_DIR = path.join(STUDIO_ROOT, 'models');
const TESS_CACHE = path.join(MODELS_DIR, 'tessdata');
const HF_CACHE = path.join(MODELS_DIR, 'hf_cache');
const PROVIDERS_CFG_PATH = path.join(STUDIO_ROOT, 'ai_providers.json');
fs.mkdirSync(TESS_CACHE, { recursive: true });
fs.mkdirSync(HF_CACHE, { recursive: true });

function isLocalOnlyMode() {
  if (process.env.AI_STUDIO_FORCE_OFFLINE === '1') return true;
  try {
    if (fs.existsSync(PROVIDERS_CFG_PATH)) {
      const cfg = JSON.parse(fs.readFileSync(PROVIDERS_CFG_PATH, 'utf8'));
      return (cfg.mode || 'LOCAL_ONLY') === 'LOCAL_ONLY';
    }
  } catch (_) {
    // Fail closed to LOCAL_ONLY if config cannot be parsed
  }
  return true;
}

const LOCAL_ONLY = isLocalOnlyMode();
env.cacheDir = HF_CACHE;
env.allowLocalModels = true;
env.allowRemoteModels = !LOCAL_ONLY;

async function runOcr(imgPath, lang = 'vie+eng') {
  if (LOCAL_ONLY) {
    const langs = String(lang).split('+').map(s => s.trim()).filter(Boolean);
    for (const lg of langs) {
      const trainedPath = path.join(TESS_CACHE, `${lg}.traineddata`);
      if (!fs.existsSync(trainedPath)) {
        throw new Error(`LOCAL_ONLY mode blocked remote OCR download: missing local file ${trainedPath}`);
      }
    }
  }
  const workerOpts = {
    cachePath: TESS_CACHE,
    logger: () => {}
  };
  if (LOCAL_ONLY) {
    workerOpts.langPath = TESS_CACHE;
    workerOpts.gzip = false;
  }
  const worker = await createWorker(lang, 1, workerOpts);
  try {
    const ret = await worker.recognize(imgPath, {}, { blocks: true, text: true });
    const data = ret.data || {};
    const lines = [];
    // tesseract.js v7 returns blocks -> paragraphs -> lines OR top-level lines
    const rawLines = data.lines || [];
    if (!rawLines.length && data.blocks) {
      for (const blk of data.blocks) {
        for (const para of (blk.paragraphs || [])) {
          for (const ln of (para.lines || [])) {
            rawLines.push(ln);
          }
        }
      }
    }
    for (const ln of rawLines) {
      const txt = (ln.text || '').replace(/\s+/g, ' ').trim();
      if (!txt) continue;
      const b = ln.bbox || { x0: 0, y0: 0, x1: 0, y1: 0 };
      const bl = ln.baseline || { y0: b.y1, y1: b.y1 };
      lines.push({
        text: txt,
        confidence: Number(((ln.confidence || 0) / 100).toFixed(3)),
        bbox: [Math.round(b.x0), Math.round(b.y0), Math.max(1, Math.round(b.x1 - b.x0)), Math.max(1, Math.round(b.y1 - b.y0))],
        baseline_y: Math.round(((bl.y0 || b.y1) + (bl.y1 || b.y1)) / 2),
        words: (ln.words || []).map(w => ({
          text: (w.text || '').trim(),
          confidence: Number(((w.confidence || 0) / 100).toFixed(3)),
          bbox: w.bbox ? [Math.round(w.bbox.x0), Math.round(w.bbox.y0), Math.max(1, Math.round(w.bbox.x1 - w.bbox.x0)), Math.max(1, Math.round(w.bbox.y1 - w.bbox.y0))] : [0, 0, 1, 1]
        }))
      });
    }
    return { ok: true, engine: 'tesseract.js', lang, lines, full_text: (data.text || '').trim() };
  } finally {
    await worker.terminate();
  }
}

function saveGrayMaskPng(maskData, width, height, outPath) {
  const png = new PNG({ width, height });
  for (let i = 0; i < width * height; i++) {
    const v = Math.max(0, Math.min(255, Math.round(maskData[i])));
    const p = i * 4;
    png.data[p] = v;
    png.data[p + 1] = v;
    png.data[p + 2] = v;
    png.data[p + 3] = 255;
  }
  fs.writeFileSync(outPath, PNG.sync.write(png));
}

async function runSlimSam(imgPath, pointsArg, outMaskPath) {
  const rawPts = (fs.existsSync(pointsArg) ? fs.readFileSync(pointsArg, 'utf8') : pointsArg).replace(/^\uFEFF/, '');
  const input = JSON.parse(rawPts);
  const pts = input.points || []; // [[x, y], ...]
  const lbls = input.labels || []; // [1, 0, ...]
  if (!pts.length) throw new Error('SlimSAM requires at least 1 point');

  const modelId = 'Xenova/slimsam-77-uniform';
  const model = await SamModel.from_pretrained(modelId, { dtype: 'q8' });
  const processor = await AutoProcessor.from_pretrained(modelId);

  const image = await RawImage.read(imgPath);
  const inputs = await processor(image, {
    input_points: [[pts]],
    input_labels: [[lbls]]
  });
  const outputs = await model(inputs);
  const masks = await processor.post_process_masks(
    outputs.pred_masks,
    inputs.original_sizes,
    inputs.reshaped_input_sizes
  );
  const scores = outputs.iou_scores.data;
  // Return best candidate mask (or specific mask_level: 0=subpart, 1=medium, 2=whole_object, default=highest IoU or largest when multi-point)
  const maskLevel = input.mask_level;
  let bestIdx = 0;
  if (typeof maskLevel === 'number' && maskLevel >= 0 && maskLevel < scores.length) {
    bestIdx = maskLevel;
  } else {
    for (let i = 1; i < scores.length; i++) {
      if (scores[i] > scores[bestIdx]) bestIdx = i;
    }
  }

  // masks[0] tensor shape: [1, 3, H, W]
  const mTensor = masks[0];
  const dims = mTensor.dims;
  const H = dims[dims.length - 2];
  const W = dims[dims.length - 1];
  const offset = bestIdx * H * W;
  const maskBytes = new Uint8Array(W * H);
  for (let i = 0; i < W * H; i++) {
    maskBytes[i] = mTensor.data[offset + i] ? 255 : 0;
  }
  saveGrayMaskPng(maskBytes, W, H, outMaskPath);
  return {
    ok: true,
    engine: 'slimsam-77-uniform',
    width: W,
    height: H,
    iou_score: Number(scores[bestIdx].toFixed(3)),
    mask_path: outMaskPath
  };
}

async function runRmbg(imgPath, outMaskPath) {
  const modelId = 'briaai/RMBG-1.4';
  const model = await AutoModel.from_pretrained(modelId, {
    config: { model_type: 'custom' },
    dtype: 'q8'
  });
  const processor = await AutoProcessor.from_pretrained(modelId, {
    config: {
      do_normalize: true,
      do_pad: false,
      do_rescale: true,
      do_resize: true,
      image_mean: [0.5, 0.5, 0.5],
      image_std: [1, 1, 1],
      resample: 2,
      rescale_factor: 0.00392156862745098,
      size: { width: 1024, height: 1024 }
    }
  });
  const image = await RawImage.read(imgPath);
  const { pixel_values } = await processor(image);
  const { output } = await model({ input: pixel_values });
  const maskRaw = await RawImage.fromTensor(output[0].mul(255).to('uint8')).resize(image.width, image.height);
  saveGrayMaskPng(maskRaw.data, image.width, image.height, outMaskPath);
  return { ok: true, engine: 'briaai/RMBG-1.4', width: image.width, height: image.height, mask_path: outMaskPath };
}

async function runDetect(imgPath, thresholdArg) {
  const threshold = Number(thresholdArg) || 0.60;
  const det = await pipeline('object-detection', 'Xenova/detr-resnet-50', { dtype: 'q8' });
  const raw = await det(imgPath, { threshold });
  const objects = (raw || []).map(item => {
    const b = item.box || {};
    const x1 = Math.max(0, Math.round(b.xmin || 0));
    const y1 = Math.max(0, Math.round(b.ymin || 0));
    const x2 = Math.max(x1 + 1, Math.round(b.xmax || 1));
    const y2 = Math.max(y1 + 1, Math.round(b.ymax || 1));
    return {
      label: String(item.label || 'object'),
      score: Number((item.score || 0).toFixed(3)),
      bbox: [x1, y1, x2 - x1, y2 - y1]
    };
  });
  return { ok: true, engine: 'Xenova/detr-resnet-50', objects };
}

async function runLamaInpaint(imgPath, maskPath, outPath) {
  const lamaPath = path.join(MODELS_DIR, 'lama', 'inpainting_lama_2025jan.onnx');
  if (!fs.existsSync(lamaPath)) throw new Error('LaMa ONNX model not found at ' + lamaPath);
  const sess = await ort.InferenceSession.create(lamaPath, { logSeverityLevel: 3 });

  const img512 = (await (await RawImage.read(imgPath)).resize(512, 512)).rgb();
  const msk512 = (await (await RawImage.read(maskPath)).grayscale().resize(512, 512));

  const N = 512 * 512;
  const imData = new Float32Array(3 * N);
  const mData = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    imData[i] = img512.data[i * 3] / 255.0;
    imData[N + i] = img512.data[i * 3 + 1] / 255.0;
    imData[2 * N + i] = img512.data[i * 3 + 2] / 255.0;
    mData[i] = msk512.data[i] > 120 ? 1.0 : 0.0;
  }

  const out = await sess.run({
    image: new ort.Tensor('float32', imData, [1, 3, 512, 512]),
    mask: new ort.Tensor('float32', mData, [1, 1, 512, 512])
  });
  const arr = out[sess.outputNames[0]].data;
  let maxVal = 0;
  for (let i = 0; i < Math.min(2000, arr.length); i++) if (arr[i] > maxVal) maxVal = arr[i];
  const scale = maxVal <= 1.5 ? 255.0 : 1.0;

  const outBytes = new Uint8ClampedArray(N * 3);
  for (let i = 0; i < N; i++) {
    outBytes[i * 3]     = Math.max(0, Math.min(255, Math.round(arr[i] * scale)));
    outBytes[i * 3 + 1] = Math.max(0, Math.min(255, Math.round(arr[N + i] * scale)));
    outBytes[i * 3 + 2] = Math.max(0, Math.min(255, Math.round(arr[2 * N + i] * scale)));
  }
  await new RawImage(outBytes, 512, 512, 3).save(outPath);
  return { ok: true, engine: 'lama-2025jan-onnx', out_path: outPath };
}

const [, , cmd, arg1, arg2, arg3] = process.argv;
(async () => {
  try {
    if (cmd === 'ocr') {
      const res = await runOcr(arg1, arg2 || 'vie+eng');
      console.log(JSON.stringify(res));
    } else if (cmd === 'slimsam') {
      const res = await runSlimSam(arg1, arg2, arg3);
      console.log(JSON.stringify(res));
    } else if (cmd === 'rmbg') {
      const res = await runRmbg(arg1, arg2);
      console.log(JSON.stringify(res));
    } else if (cmd === 'detect') {
      const res = await runDetect(arg1, arg2);
      console.log(JSON.stringify(res));
    } else if (cmd === 'lama_inpaint') {
      const res = await runLamaInpaint(arg1, arg2, arg3);
      console.log(JSON.stringify(res));
    } else {
      console.error('Unknown cmd');
      process.exit(1);
    }
  } catch (err) {
    console.error(JSON.stringify({ ok: false, error: err.message }));
    process.exit(1);
  }
})();
