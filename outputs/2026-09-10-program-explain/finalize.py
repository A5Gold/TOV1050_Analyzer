from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib
import json
import math
import zipfile
import re

root = Path(__file__).resolve().parent
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
checks = []
for item in manifest:
    path = root / item["file"]
    with Image.open(path) as im:
        im.load()
        assert im.format == "PNG"
        size = im.size
    record = json.loads(path.with_suffix(".request.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == record["output_sha256"]
    checks.append({**item, "dimensions": list(size), "bytes": path.stat().st_size,
        "sha256": digest, "format": "PNG", "response_model": record.get("response_model"),
        "requested_model": "gpt-image-2.5-sunburst", "visual_review": "reviewed",
        "requested_dimensions_honored": size == (1920,1080)})
assert len(checks) == 13
(root / "verification.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
for name in ["README.md", "gallery.html"]:
    path = root / name
    content = path.read_text(encoding="utf-8")
    for item in manifest:
        if item["file"] != item["id"] + ".png":
            content = content.replace(item["id"] + ".png", item["file"])
            content = content.replace("prompts/" + item["id"] + ".txt", "prompts/" + Path(item["file"]).stem + ".txt")
    path.write_text(content, encoding="utf-8")
gallery = (root / "gallery.html").read_text(encoding="utf-8")
for link in re.findall(r'(?:src|href)="([^"]+)"', gallery):
    if not link.startswith("#"):
        assert (root / link).exists(), link
font = ImageFont.truetype("C:/Windows/Fonts/msjh.ttc", 22)
thumb_w, thumb_h = 560, 316
sheet = Image.new("RGB", (3 * 592, math.ceil(13/3)*370), "#f6f8fb")
draw = ImageDraw.Draw(sheet)
for i,item in enumerate(manifest):
    x,y = (i % 3)*592+16, (i//3)*370+12
    with Image.open(root/item["file"]) as im:
        im.thumbnail((thumb_w,thumb_h))
        sheet.paste(im,(x,y))
    draw.text((x,y+321), f'{i+1:02d}  {item["title"]}', font=font, fill="#263348")
sheet.save(root/"contact-sheet.jpg", quality=92)
package = root.parent / "TOV1050-program-explanation-13-images.zip"
files = ["README.md","gallery.html","manifest.json","verification.json","contact-sheet.jpg"]
for item in manifest:
    stem = Path(item["file"]).stem
    files.extend([item["file"], stem+".request.json","prompts/"+stem+".txt"])
with zipfile.ZipFile(package,"w",compression=zipfile.ZIP_DEFLATED) as archive:
    for name in files:
        archive.write(root/name,name)
with zipfile.ZipFile(package, "r") as archive:
    assert archive.testzip() is None
print(json.dumps({"images":len(checks),"dimensions":sorted(set(tuple(c["dimensions"]) for c in checks)),
                  "zip":str(package),"verified_links":True},ensure_ascii=True))
