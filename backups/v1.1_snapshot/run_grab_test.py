import json
import os
import sys

sys.path.insert(0, r"D:\AI_Design_Studio")
from core.image_analyzer import run_redesign
from core.qa_engine import export_and_qa_all
from core.reference_analyzer import analyze_reference_image

img = r"C:/Users/BUM/.gemini/antigravity/brain/7a3bd732-b5a7-4da2-8ae9-7603555447fd/.user_uploaded/media_1794977150476_12e90368.jpg"
pdir = r"D:\AI_Design_Studio\projects\grab_redesign_test"
os.makedirs(pdir, exist_ok=True)

doc = run_redesign(img, pdir, "grab_redesign_test", title="Grab Poster Redesign Test", upscale_2x=True, max_dim=2048)
qa = export_and_qa_all(r"D:\AI_Design_Studio", pdir)
ref = analyze_reference_image(img, "Grab_Poster_Ref")
with open(os.path.join(pdir, "ref_analysis.json"), "w", encoding="utf-8") as f:
    json.dump(ref, f, ensure_ascii=False, indent=2)

print("DOC SIZE:", doc["width"], "x", doc["height"], "| LAYERS:", len(doc["layers"]))
for l in doc["layers"]:
    print(f"  - {l['name']} ({l['type']}) [{l['x']},{l['y']} {l['width']}x{l['height']}] grp={l['group']}")
print("QA OVERALL:", qa["overall_passed"], "| MAE:", qa["qa2_composite"]["mae_vs_source"], "| PSD_BYTES:", qa["qa3_psd"]["psd_bytes"], "| DECODED:", qa["qa3_psd"]["decoded_pixel_layers"], "/", qa["qa3_psd"]["layer_count"])
print("REF LAYOUT:", ref["visual_hierarchy"]["suggested_layout"], "| BG:", ref["palette"]["bg_hex"], "| ACCENT:", ref["palette"]["accent_hex"])
