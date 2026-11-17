# lightmap float -> denoised, gamma-encoded JPEG for three.js (flipY=false)
import sys, json, numpy as np
from PIL import Image
src, dst, lmax = sys.argv[1], sys.argv[2], float(sys.argv[3])
a = np.load(src).astype(np.float32)
rgb = a[:, :, :3]
mask = (a[:, :, 3] > 0.5) if a.shape[2] == 4 else (rgb.max(2) > 0)
rgb = rgb * mask[..., None]
def box(img, r):
    # separable box filter via cumulative sums
    out = img
    for ax in (0, 1):
        c = np.cumsum(np.pad(out, [(r + 1, r) if i == ax else (0, 0) for i in range(out.ndim)]), axis=ax)
        hi = np.take(c, np.arange(2 * r + 1, c.shape[ax]), axis=ax)
        lo = np.take(c, np.arange(0, c.shape[ax] - 2 * r - 1), axis=ax)
        out = hi - lo
    return out
r = int(sys.argv[4]) if len(sys.argv) > 4 else 1
m = mask.astype(np.float32)
num = rgb
den = m
for _ in range(2):
    num = box(num, r); den = box(den, r)
den3 = np.maximum(den, 1e-6)[..., None]
sm = num / den3
sm = np.where(mask[..., None], sm, 0)
print('percentiles', np.percentile(sm[mask].max(1), [50, 90, 99, 99.9]))
enc = np.clip(sm / lmax, 0, 1) ** (1 / 2.2)
img = (enc * 255 + 0.5).astype(np.uint8)[::-1]   # blender rows are bottom-up
Image.fromarray(img).save(dst, quality=90)
