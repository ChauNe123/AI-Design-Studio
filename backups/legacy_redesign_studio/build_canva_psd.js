const fs = require('fs');
const path = require('path');
const { PNG } = require('pngjs');
const { writePsdBuffer } = require('ag-psd');

const DIR = path.join(__dirname, 'canva_fullhd');
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
      name: '1_Background_&_Shapes_FullHD',
      opened: true,
      children: groups['1_Background'] || []
    },
    {
      name: '2_Photo_&_Logo_FullHD',
      opened: true,
      children: groups['2_Photo_&_Logo'] || []
    },
    {
      name: '3_Feature_Icons_FullHD',
      opened: true,
      children: groups['3_Feature_Icons'] || []
    },
    {
      name: '4_Texts_Visible_Sharp',
      opened: true,
      children: groups['4_Texts_Visible_Sharp'] || []
    },
    {
      name: '5_Editable_Texts_Template_Hidden',
      opened: false,
      hidden: true,
      children: [
        makeTextLayer('Text_Headline_1', 'MỘT HÀNH TRÌNH MỚI', 84, 285, 76, [0, 214, 91]),
        makeTextLayer('Text_Headline_2', 'SẮP BẮT ĐẦU', 84, 395, 118, [255, 255, 255]),
        makeTextLayer('Text_Subtitle', 'An toàn trên mọi hành trình.', 86, 580, 52, [255, 255, 255]),
        makeTextLayer('Text_Feature_1', 'CAMERA – QUAN SÁT PHÍA TRƯỚC', 182, 1300, 30, [10, 10, 10]),
        makeTextLayer('Text_Feature_2', 'SPEED – THEO DÕI TỐC ĐỘ', 182, 1410, 30, [10, 10, 10]),
        makeTextLayer('Text_Feature_3', 'DISTANCE – NHẬN BIẾT KHOẢNG CÁCH', 182, 1520, 30, [10, 10, 10]),
        makeTextLayer('Text_Feature_4', 'GPS – ĐỊNH VỊ VÀ DẪN ĐƯỜNG', 182, 1628, 30, [10, 10, 10])
      ]
    }
  ]
};

const outPath = path.join(DIR, 'Canva_SafeDrive_FullHD_Editable.psd');
const buffer = writePsdBuffer(psd, { generateThumbnail: false });
fs.writeFileSync(outPath, buffer);
console.log('CREATED:', outPath, 'SIZE:', buffer.length, 'bytes');
