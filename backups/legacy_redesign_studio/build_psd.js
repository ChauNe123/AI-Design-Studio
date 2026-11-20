const fs = require('fs');
const path = require('path');
const { PNG } = require('pngjs');
const { writePsdBuffer } = require('ag-psd');

const STUDIO_DIR = __dirname;
const manifest = JSON.parse(fs.readFileSync(path.join(STUDIO_DIR, 'manifest_ai.json'), 'utf8'));

function loadPngAsImageData(relPath) {
  const buf = fs.readFileSync(path.join(STUDIO_DIR, relPath));
  const png = PNG.sync.read(buf);
  return {
    width: png.width,
    height: png.height,
    data: new Uint8ClampedArray(png.data)
  };
}

function makeImgLayer(item, hidden = false) {
  return {
    name: item.name,
    left: item.x,
    top: item.y,
    hidden,
    opacity: 1,
    blendMode: 'normal',
    imageData: loadPngAsImageData(item.file)
  };
}

function makeTextLayer(name, text, left, top, fontSize, colorRgb, fontName = 'Arial-BoldMT') {
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
        font: { name: fontName },
        fontSize,
        fillColor: { r: colorRgb[0], g: colorRgb[1], b: colorRgb[2] },
        fauxBold: true
      }
    }
  };
}

const byName = Object.fromEntries(manifest.layers.map(l => [l.name, l]));

const psd = {
  width: manifest.width,
  height: manifest.height,
  channels: 4,
  bitsPerChannel: 8,
  colorMode: 3, // RGB
  children: [
    {
      name: '1_Background_&_Decor',
      opened: true,
      children: [
        byName['01_Background_Clean'] && makeImgLayer(byName['01_Background_Clean']),
        byName['02_Decor_Pin_TopRight'] && makeImgLayer(byName['02_Decor_Pin_TopRight']),
        byName['03_Decor_Emoji_Left'] && makeImgLayer(byName['03_Decor_Emoji_Left'])
      ].filter(Boolean)
    },
    {
      name: '2_Products_&_Objects',
      opened: true,
      children: [
        byName['04_Object_Road_3D'] && makeImgLayer(byName['04_Object_Road_3D']),
        byName['05_Object_Taxi_Car'] && makeImgLayer(byName['05_Object_Taxi_Car']),
        byName['06_Object_Hand_Phone'] && makeImgLayer(byName['06_Object_Hand_Phone']),
        byName['10_Icon_Phone_Bottom'] && makeImgLayer(byName['10_Icon_Phone_Bottom'])
      ].filter(Boolean)
    },
    {
      name: '3_Original_Texts_Hidden',
      opened: false,
      hidden: true,
      children: [
        byName['07_Logo_ONEWAY_Orig'] && makeImgLayer(byName['07_Logo_ONEWAY_Orig'], true),
        byName['08_Text_Top_Arabic_Orig'] && makeImgLayer(byName['08_Text_Top_Arabic_Orig'], true),
        byName['09_Text_Mid_Arabic_Orig'] && makeImgLayer(byName['09_Text_Mid_Arabic_Orig'], true),
        byName['11_Text_Phone_Orig'] && makeImgLayer(byName['11_Text_Phone_Orig'], true)
      ].filter(Boolean)
    },
    {
      name: '4_Editable_Texts_Redesign',
      opened: true,
      children: [
        makeTextLayer('Text_Top_Tagline', 'TỪ HÔM NAY', 392, 24, 34, [20, 20, 20]),
        makeTextLayer('Logo_Brand_Editable', 'ONEWAY', 88, 95, 76, [255, 224, 0]),
        makeTextLayer('Text_Mid_Subline', 'ỨNG DỤNG ĐẶT XE NHANH', 28, 215, 28, [20, 20, 20]),
        makeTextLayer('Text_Hotline_Editable', '+84 123 456 78', 485, 670, 28, [20, 20, 20])
      ]
    }
  ]
};

const outPath = path.join(STUDIO_DIR, 'OneWay_AI_QA_Passed.psd');
const buffer = writePsdBuffer(psd, { generateThumbnail: false });
fs.writeFileSync(outPath, buffer);
console.log('CREATED:', outPath, 'SIZE:', buffer.length, 'bytes');
