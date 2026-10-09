import sys
from PIL import Image
src = sys.argv[1]
dst = sys.argv[2]
im = Image.open(src).convert('RGB')
w, h = im.size
scale = min(1.0, 1100 / w)
if scale < 1.0:
    im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
im.save(dst, 'PNG')
print('converted', im.size)
