import os, glob
from PIL import Image
for p in sorted(glob.glob('out/pano/*.png')):
    n = os.path.splitext(os.path.basename(p))[0]
    o = 'tour/pano/%s.jpg' % n
    if os.path.exists(o) and os.path.getmtime(o) > os.path.getmtime(p):
        continue
    Image.open(p).convert('RGB').save(o, quality=86, optimize=True, progressive=True)
    print(n, os.path.getsize(o) // 1024, 'KB')
