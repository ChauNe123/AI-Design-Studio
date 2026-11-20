const fs = require('fs');
const path = require('path');
const { PNG } = require('pngjs');
const { writePsdBuffer } = require('ag-psd');

const DIR = path.join(__dirname, 'safedrive_fullhd');
const manifest = JSON.parse(fs.readFileSync(path.join(DIR, 'manifest.json'), 'utf8'));

function loadPng(relPath) {
  const buf = fs.readFileSync(path.join(DIR, relPath));
  const png = PNG.sync.read(buf);
  return {
    width: png.width,
    height: png.height,
    data: new Uint8ClampedArray(png.data)
  };
}

function makeImgLayer(item) {
  return {
    name: item.name,
    left: item.x,
    top: item.y,
    hidden: !!item.hidden,
    opacity: 1,
    blendMode: 'normal',
    imageData: loadPng(item.file)
  };
}

function makeTextLayer(name, text, left, top, fontSize, colorRgb) {
  return {
    name,
    left,
    top,
    opacity: 1,
    blendMode: 'normal',
    text: {
      text,
      transform: [1, 0, 0, 1, left, top + fontSize],
      style: {
        font: { name: 'Arial-BoldMT' },
        fontSize,
        fillColor: { r: colorRgb[0], g: colorRgb[1], b: colorRgb[2] },
        fauxBold: true
      }
    }
  };
}

const groups = {};
for (const item of manifest.layers) {
  if (!groups[item.group]) groups[item.group] = [];
  groups[item.group].push(makeImgLayer(item));
}

const psd = {
  width: manifest.width,
  height: manifest.height,
  channels: 4,
  bitsPerChannel: 8,
  colorMode: 3,
  children: [
    {
      name: '1_Background_FullHD',
      opened: true,
      children: groups['1_Background'] || []
    },
    {
      name: '2_Objects_&_FeatureCards_FullHD',
      opened: true,
      children: groups['2_Objects_&_Cards'] || []
    },
    {
      name: '3_Original_Texts_Hidden',
      opened: false,
      hidden: true,
      children: groups['3_Original_Texts_Hidden'] || []
    },
    {
      name: '4_Editable_Texts_FullHD',
      opened: true,
      children: [
        makeTextLayer('Text_TopRight_Tagline', 'CÔNG NGHỆ THÔNG MINH –\rHÀNH TRÌNH AN TOÀN', 905, 165, 36, [25, 35, 30]),
        makeTextLayer('Text_Hero_SAFE_DRIVE', 'SAFE DRIVE', 385, 340, 108, [22, 163, 74]),
        makeTextLayer('Text_Hero_Subtitle', 'BẠN ĐỒNG HÀNH TRÊN MỌI NẺO ĐƯỜNG\rTRẢI NGHIỆM LÁI XE AN TOÀN HƠN', 190, 465, 48, [18, 24, 22]),
        makeTextLayer('Text_Footer_Left', 'Tải ngay trên\rApp Store & Google Play', 180, 1875, 32, [255, 255, 255]),
        makeTextLayer('Text_Footer_Hotline', 'Hotline: (336) 502-5573 | safedrive.com', 820, 1905, 28, [255, 255, 255])
      ]
    }
  ]
};

const outPath = path.join(DIR, 'SafeDrive_FullHD_Editable.psd');
const buffer = writePsdBuffer(psd, { generateThumbnail: false });
fs.writeFileSync(outPath, buffer);
console.log('CREATED:', outPath, 'SIZE:', buffer.length, 'bytes');
