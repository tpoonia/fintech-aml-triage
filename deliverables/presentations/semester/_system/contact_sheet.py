"""Tile rendered slide images into contact sheets for visual QA (2 columns).
Usage: python contact_sheet.py OUT_PREFIX img1.png img2.png ...  (4 slides per sheet)"""

import sys

from PIL import Image

out, files = sys.argv[1], sys.argv[2:]
for k in range(0, len(files), 4):
    ims = [Image.open(f) for f in files[k : k + 4]]
    w, h = ims[0].size
    sheet = Image.new(
        "RGB", (w * 2 + 10, h * ((len(ims) + 1) // 2) + 10 * ((len(ims) - 1) // 2)), "#888888"
    )
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % 2) * (w + 10), (i // 2) * (h + 10)))
    sheet.save(f"{out}-{k // 4 + 1}.png")
    print(f"{out}-{k // 4 + 1}.png")
